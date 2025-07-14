"""
Vault Manager routes for secure document storage and retrieval
"""
import os
import json
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, send_file
from google.cloud import storage
from google.cloud import kms
import io
import tempfile

vault_bp = Blueprint('vault', __name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VaultManager:
    def __init__(self):
        self.storage_client = storage.Client()
        self.kms_client = kms.KeyManagementServiceClient()
        self.project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
        self.vault_bucket_name = os.environ.get('VAULT_BUCKET', 'drive-scanner-vault')
        self.kms_key_name = os.environ.get('KMS_KEY_NAME')
        
        # Initialize vault bucket
        self._ensure_vault_bucket_exists()
    
    def _ensure_vault_bucket_exists(self):
        """Ensure the vault bucket exists with proper security settings"""
        try:
            bucket = self.storage_client.bucket(self.vault_bucket_name)
            if not bucket.exists():
                # Create bucket with security settings
                bucket = self.storage_client.create_bucket(
                    self.vault_bucket_name,
                    location='US'  # or your preferred location
                )
                
                # Set bucket-level IAM policy for restricted access
                policy = bucket.get_iam_policy(requested_policy_version=3)
                
                # Remove public access
                policy.bindings = [
                    binding for binding in policy.bindings 
                    if 'allUsers' not in binding.get('members', []) and 
                       'allAuthenticatedUsers' not in binding.get('members', [])
                ]
                
                bucket.set_iam_policy(policy)
                
                # Enable uniform bucket-level access
                bucket.iam_configuration.uniform_bucket_level_access_enabled = True
                bucket.patch()
                
                logger.info(f"Created secure vault bucket: {self.vault_bucket_name}")
            
        except Exception as e:
            logger.error(f"Error ensuring vault bucket exists: {e}")
            raise
    
    def encrypt_data(self, data):
        """Encrypt data using Cloud KMS (if configured)"""
        if not self.kms_key_name:
            logger.warning("No KMS key configured, storing data without additional encryption")
            return data, None
        
        try:
            # Convert string data to bytes if necessary
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            # Encrypt the data
            encrypt_response = self.kms_client.encrypt(
                request={
                    "name": self.kms_key_name,
                    "plaintext": data
                }
            )
            
            return encrypt_response.ciphertext, self.kms_key_name
            
        except Exception as e:
            logger.error(f"Error encrypting data: {e}")
            raise
    
    def decrypt_data(self, encrypted_data, key_name):
        """Decrypt data using Cloud KMS"""
        if not key_name:
            return encrypted_data
        
        try:
            decrypt_response = self.kms_client.decrypt(
                request={
                    "name": key_name,
                    "ciphertext": encrypted_data
                }
            )
            
            return decrypt_response.plaintext
            
        except Exception as e:
            logger.error(f"Error decrypting data: {e}")
            raise
    
    def store_document(self, file_id, file_name, content, metadata=None):
        """Store a document in the secure vault"""
        try:
            bucket = self.storage_client.bucket(self.vault_bucket_name)
            
            # Create a unique blob name
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            blob_name = f"documents/{file_id}_{timestamp}_{file_name}"
            
            # Encrypt content if KMS is configured
            encrypted_content, key_name = self.encrypt_data(content)
            
            # Create blob and upload
            blob = bucket.blob(blob_name)
            
            # Set metadata
            blob_metadata = {
                'original_file_id': file_id,
                'original_file_name': file_name,
                'storage_timestamp': datetime.utcnow().isoformat(),
                'encrypted': 'true' if key_name else 'false',
                'kms_key_name': key_name or '',
                'content_type': 'application/octet-stream' if key_name else 'text/plain'
            }
            
            if metadata:
                blob_metadata.update(metadata)
            
            blob.metadata = blob_metadata
            
            # Upload the content
            if isinstance(encrypted_content, bytes):
                blob.upload_from_string(encrypted_content, content_type='application/octet-stream')
            else:
                blob.upload_from_string(encrypted_content)
            
            logger.info(f"Document stored in vault: {blob_name}")
            
            return {
                'vault_path': blob_name,
                'encrypted': bool(key_name),
                'storage_timestamp': blob_metadata['storage_timestamp']
            }
            
        except Exception as e:
            logger.error(f"Error storing document in vault: {e}")
            raise
    
    def retrieve_document(self, vault_path):
        """Retrieve a document from the vault"""
        try:
            bucket = self.storage_client.bucket(self.vault_bucket_name)
            blob = bucket.blob(vault_path)
            
            if not blob.exists():
                raise FileNotFoundError(f"Document not found in vault: {vault_path}")
            
            # Download content
            content = blob.download_as_bytes()
            metadata = blob.metadata or {}
            
            # Decrypt if necessary
            if metadata.get('encrypted') == 'true':
                key_name = metadata.get('kms_key_name')
                if key_name:
                    content = self.decrypt_data(content, key_name)
            
            return {
                'content': content,
                'metadata': metadata,
                'size': blob.size,
                'created': blob.time_created.isoformat() if blob.time_created else None,
                'updated': blob.updated.isoformat() if blob.updated else None
            }
            
        except Exception as e:
            logger.error(f"Error retrieving document from vault: {e}")
            raise
    
    def list_vault_documents(self, prefix=None, limit=100):
        """List documents in the vault"""
        try:
            bucket = self.storage_client.bucket(self.vault_bucket_name)
            
            blobs = bucket.list_blobs(
                prefix=prefix or 'documents/',
                max_results=limit
            )
            
            documents = []
            for blob in blobs:
                metadata = blob.metadata or {}
                documents.append({
                    'vault_path': blob.name,
                    'original_file_id': metadata.get('original_file_id'),
                    'original_file_name': metadata.get('original_file_name'),
                    'size': blob.size,
                    'encrypted': metadata.get('encrypted') == 'true',
                    'storage_timestamp': metadata.get('storage_timestamp'),
                    'created': blob.time_created.isoformat() if blob.time_created else None
                })
            
            return documents
            
        except Exception as e:
            logger.error(f"Error listing vault documents: {e}")
            raise
    
    def delete_document(self, vault_path):
        """Delete a document from the vault"""
        try:
            bucket = self.storage_client.bucket(self.vault_bucket_name)
            blob = bucket.blob(vault_path)
            
            if not blob.exists():
                raise FileNotFoundError(f"Document not found in vault: {vault_path}")
            
            blob.delete()
            logger.info(f"Document deleted from vault: {vault_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document from vault: {e}")
            raise
    
    def get_vault_statistics(self):
        """Get statistics about the vault"""
        try:
            bucket = self.storage_client.bucket(self.vault_bucket_name)
            
            # Count documents and calculate total size
            total_documents = 0
            total_size = 0
            encrypted_count = 0
            
            for blob in bucket.list_blobs(prefix='documents/'):
                total_documents += 1
                total_size += blob.size or 0
                
                metadata = blob.metadata or {}
                if metadata.get('encrypted') == 'true':
                    encrypted_count += 1
            
            return {
                'total_documents': total_documents,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'encrypted_documents': encrypted_count,
                'unencrypted_documents': total_documents - encrypted_count,
                'encryption_percentage': round((encrypted_count / total_documents * 100), 2) if total_documents > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting vault statistics: {e}")
            raise

# Initialize vault manager instance
vault_manager = VaultManager()

@vault_bp.route('/store', methods=['POST'])
def store_document():
    """Store a document in the vault"""
    try:
        data = request.get_json()
        file_id = data.get('file_id')
        file_name = data.get('file_name')
        content = data.get('content')
        metadata = data.get('metadata', {})
        
        if not all([file_id, file_name, content]):
            return jsonify({'error': 'file_id, file_name, and content are required'}), 400
        
        result = vault_manager.store_document(file_id, file_name, content, metadata)
        
        return jsonify({
            'status': 'success',
            'message': 'Document stored in vault',
            **result
        })
        
    except Exception as e:
        logger.error(f"Error in store_document: {e}")
        return jsonify({'error': str(e)}), 500

@vault_bp.route('/retrieve/<path:vault_path>', methods=['GET'])
def retrieve_document(vault_path):
    """Retrieve a document from the vault"""
    try:
        result = vault_manager.retrieve_document(vault_path)
        
        # Return as file download or JSON based on request
        download = request.args.get('download', 'false').lower() == 'true'
        
        if download:
            # Create a temporary file for download
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                tmp_file.write(result['content'])
                tmp_file_path = tmp_file.name
            
            original_name = result['metadata'].get('original_file_name', 'document')
            
            return send_file(
                tmp_file_path,
                as_attachment=True,
                download_name=original_name,
                mimetype='application/octet-stream'
            )
        else:
            # Return metadata and content info
            return jsonify({
                'status': 'success',
                'metadata': result['metadata'],
                'size': result['size'],
                'created': result['created'],
                'updated': result['updated'],
                'content_preview': str(result['content'][:200]) + '...' if len(result['content']) > 200 else str(result['content'])
            })
        
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error in retrieve_document: {e}")
        return jsonify({'error': str(e)}), 500

@vault_bp.route('/list', methods=['GET'])
def list_documents():
    """List documents in the vault"""
    try:
        prefix = request.args.get('prefix')
        limit = int(request.args.get('limit', 100))
        
        documents = vault_manager.list_vault_documents(prefix=prefix, limit=limit)
        
        return jsonify({
            'status': 'success',
            'documents': documents,
            'total': len(documents)
        })
        
    except Exception as e:
        logger.error(f"Error in list_documents: {e}")
        return jsonify({'error': str(e)}), 500

@vault_bp.route('/delete/<path:vault_path>', methods=['DELETE'])
def delete_document(vault_path):
    """Delete a document from the vault"""
    try:
        vault_manager.delete_document(vault_path)
        
        return jsonify({
            'status': 'success',
            'message': 'Document deleted from vault'
        })
        
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error in delete_document: {e}")
        return jsonify({'error': str(e)}), 500

@vault_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """Get vault statistics"""
    try:
        stats = vault_manager.get_vault_statistics()
        
        return jsonify({
            'status': 'success',
            'statistics': stats
        })
        
    except Exception as e:
        logger.error(f"Error in get_statistics: {e}")
        return jsonify({'error': str(e)}), 500

@vault_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Vault Manager',
        'timestamp': datetime.utcnow().isoformat()
    })

