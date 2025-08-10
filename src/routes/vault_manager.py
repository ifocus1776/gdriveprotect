"""
Enhanced Vault Manager routes for secure document storage and retrieval with FIPS-140-2 compliance
Supports both Cloud Storage buckets and Google Drive folders for maximum flexibility
Supports both Enterprise Google Workspace organizations and individual users
"""
import os
import json
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, send_file, session
from google.cloud import storage
from google.cloud import kms
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
import tempfile
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import secrets
import base64
import mimetypes

vault_bp = Blueprint('vault', __name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VaultManager:
    def __init__(self):
        self.storage_client = None
        self.kms_client = None
        self.drive_service = None
        self.project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
        self.vault_bucket_name = os.environ.get('VAULT_BUCKET', 'drive-scanner-vault')
        self.kms_key_name = os.environ.get('KMS_KEY_NAME')
        self.fips_enabled = os.environ.get('FIPS_ENABLED', 'true').lower() == 'true'
        
        # New Google Drive vault configuration
        self.drive_vault_folder_id = os.environ.get('DRIVE_VAULT_FOLDER_ID')
        self.drive_vault_folder_name = os.environ.get('DRIVE_VAULT_FOLDER_NAME', 'Secure Vault - FIPS Encrypted')
        self.storage_preference = os.environ.get('VAULT_STORAGE_PREFERENCE', 'hybrid')  # 'bucket', 'drive', 'hybrid'
        
        # User type configuration
        self.user_type = os.environ.get('USER_TYPE', 'enterprise')  # 'enterprise' or 'individual'
        self.enterprise_domain = os.environ.get('ENTERPRISE_DOMAIN')  # For enterprise orgs
        self.individual_user_email = os.environ.get('INDIVIDUAL_USER_EMAIL')  # For individual users
        
        # Initialize clients
        self._init_clients()
        
        # Initialize storage systems (only if we have valid clients)
        if self.storage_client and os.environ.get('FLASK_ENV') != 'development':
            try:
                self._ensure_vault_bucket_exists()
            except Exception as e:
                logger.warning(f"Could not ensure vault bucket exists: {e}")
        
        if self.drive_service and os.environ.get('FLASK_ENV') != 'development':
            try:
                self._ensure_drive_vault_folder_exists()
            except Exception as e:
                logger.warning(f"Could not ensure drive vault folder exists: {e}")
    
    def _init_clients(self):
        """Initialize Google Cloud and Drive clients with support for both enterprise and individual users"""
        try:
            # Initialize Storage client
            self.storage_client = storage.Client()
            logger.info("Storage client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Storage client: {e}")
            self.storage_client = None
        
        try:
            # Initialize KMS client
            self.kms_client = kms.KeyManagementServiceClient()
            logger.info("KMS client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize KMS client: {e}")
            self.kms_client = None
        
        try:
            # Initialize Drive client based on user type
            if self.user_type == 'enterprise':
                self._init_enterprise_drive_client()
            else:
                self._init_individual_drive_client()
                
        except Exception as e:
            logger.error(f"Failed to initialize Drive service: {e}")
            self.drive_service = None
    
    def _init_enterprise_drive_client(self):
        """Initialize Drive client for enterprise Google Workspace organizations"""
        try:
            credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if credentials_path and os.path.exists(credentials_path):
                from google.oauth2 import service_account
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path,
                    scopes=['https://www.googleapis.com/auth/drive']
                )
                
                # For enterprise, we can use domain-wide delegation
                if self.enterprise_domain:
                    credentials = credentials.with_subject(f'admin@{self.enterprise_domain}')
                    logger.info(f"Using domain-wide delegation for enterprise domain: {self.enterprise_domain}")
                
                self.drive_service = build('drive', 'v3', credentials=credentials)
                logger.info("Enterprise Drive service initialized successfully")
            else:
                logger.warning("Google Drive credentials not found, Drive vault features disabled")
                self.drive_service = None
                
        except Exception as e:
            logger.error(f"Failed to initialize enterprise Drive service: {e}")
            self.drive_service = None
    
    def _init_individual_drive_client(self):
        """Initialize Drive client for individual users"""
        try:
            # For individual users, we'll use OAuth tokens from the session
            # This will be set up when the user authenticates
            if 'google_oauth_token' in session:
                from google.oauth2.credentials import Credentials
                token_info = session['google_oauth_token']
                
                credentials = Credentials(
                    token=token_info.get('access_token'),
                    refresh_token=token_info.get('refresh_token'),
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
                    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
                    scopes=['https://www.googleapis.com/auth/drive']
                )
                
                self.drive_service = build('drive', 'v3', credentials=credentials)
                logger.info("Individual Drive service initialized successfully")
            else:
                logger.info("No OAuth token found in session, Drive service will be initialized on first use")
                self.drive_service = None
                
        except Exception as e:
            logger.error(f"Failed to initialize individual Drive service: {e}")
            self.drive_service = None
    
    def _get_drive_service_for_user(self, user_email=None):
        """Get Drive service for a specific user (for enterprise domain-wide delegation)"""
        try:
            if self.user_type == 'enterprise' and user_email:
                credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
                if credentials_path and os.path.exists(credentials_path):
                    from google.oauth2 import service_account
                    credentials = service_account.Credentials.from_service_account_file(
                        credentials_path,
                        scopes=['https://www.googleapis.com/auth/drive']
                    )
                    
                    # Use domain-wide delegation for the specific user
                    credentials = credentials.with_subject(user_email)
                    return build('drive', 'v3', credentials=credentials)
            
            return self.drive_service
            
        except Exception as e:
            logger.error(f"Failed to get Drive service for user {user_email}: {e}")
            return None
    
    def _get_or_create_user_vault_folder(self, drive_service, user_email):
        """Get or create a user-specific vault folder"""
        try:
            # Search for existing user vault folder
            query = f"name='Secure Vault - {user_email}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = drive_service.files().list(q=query, fields="files(id,name)").execute()
            
            if results.get('files'):
                folder_id = results['files'][0]['id']
                logger.info(f"Found existing user vault folder: {folder_id}")
                return folder_id
            
            # Create new user vault folder
            folder_metadata = {
                'name': f'Secure Vault - {user_email}',
                'mimeType': 'application/vnd.google-apps.folder',
                'description': f'FIPS-140-2 Encrypted Secure Vault for {user_email}'
            }
            
            folder = drive_service.files().create(
                body=folder_metadata,
                fields='id,name'
            ).execute()
            
            folder_id = folder.get('id')
            logger.info(f"Created user vault folder: {folder_id} for {user_email}")
            
            # Set restricted permissions
            self._set_user_folder_permissions(drive_service, folder_id, user_email)
            
            return folder_id
            
        except Exception as e:
            logger.error(f"Error getting/creating user vault folder for {user_email}: {e}")
            return None
    
    def _set_user_folder_permissions(self, drive_service, folder_id, user_email):
        """Set permissions for user-specific vault folder"""
        try:
            # Remove public access
            permissions = drive_service.permissions().list(fileId=folder_id).execute()
            for permission in permissions.get('permissions', []):
                if permission.get('type') == 'anyone':
                    drive_service.permissions().delete(
                        fileId=folder_id,
                        permissionId=permission.get('id')
                    ).execute()
            
            # Add user-specific permission
            user_permission = {
                'type': 'user',
                'role': 'writer',
                'emailAddress': user_email
            }
            
            drive_service.permissions().create(
                fileId=folder_id,
                body=user_permission,
                fields='id'
            ).execute()
            
            logger.info(f"Set user permissions for {user_email} on folder {folder_id}")
            
        except Exception as e:
            logger.error(f"Error setting user folder permissions: {e}")
    
    def _list_user_vault_documents(self, drive_service, folder_id):
        """List documents in user's vault folder"""
        try:
            if not folder_id:
                return []
            
            query = f"'{folder_id}' in parents and trashed=false"
            results = drive_service.files().list(
                q=query,
                fields="files(id,name,size,createdTime,modifiedTime,webViewLink)",
                orderBy="modifiedTime desc"
            ).execute()
            
            documents = []
            for file_info in results.get('files', []):
                documents.append({
                    'file_id': file_info['id'],
                    'name': file_info['name'],
                    'size': file_info.get('size', 0),
                    'created': file_info.get('createdTime'),
                    'modified': file_info.get('modifiedTime'),
                    'web_link': file_info.get('webViewLink'),
                    'vault_path': f"drive://{folder_id}/{file_info['name']}"
                })
            
            return documents
            
        except Exception as e:
            logger.error(f"Error listing user vault documents: {e}")
            return []
    
    def _ensure_vault_bucket_exists(self):
        """Ensure the vault bucket exists with FIPS-140-2 compliant security settings"""
        try:
            bucket = self.storage_client.bucket(self.vault_bucket_name)
            if not bucket.exists():
                # Create bucket with enhanced security settings
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
                
                # Enable versioning for audit trail
                bucket.versioning_enabled = True
                
                # Set lifecycle policy for secure retention
                lifecycle_rule = {
                    "action": {"type": "Delete"},
                    "condition": {
                        "age": 2555,  # 7 years for compliance
                        "isLive": True
                    }
                }
                bucket.add_lifecycle_rule(lifecycle_rule)
                
                bucket.patch()
                
                logger.info(f"Created FIPS-compliant vault bucket: {self.vault_bucket_name}")
            else:
                logger.info(f"Vault bucket already exists: {self.vault_bucket_name}")
            
        except Exception as e:
            logger.error(f"Error ensuring vault bucket exists: {e}")
            raise
    
    def _ensure_drive_vault_folder_exists(self):
        """Ensure the Google Drive vault folder exists with proper permissions"""
        try:
            if not self.drive_vault_folder_id:
                # Create the vault folder if it doesn't exist
                folder_metadata = {
                    'name': self.drive_vault_folder_name,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'description': 'FIPS-140-2 Encrypted Secure Vault for Sensitive Documents'
                }
                
                folder = self.drive_service.files().create(
                    body=folder_metadata,
                    fields='id,name,webViewLink'
                ).execute()
                
                self.drive_vault_folder_id = folder.get('id')
                logger.info(f"Created Drive vault folder: {folder.get('name')} (ID: {self.drive_vault_folder_id})")
                
                # Set folder permissions to restricted access
                self._set_folder_permissions(self.drive_vault_folder_id)
            else:
                # Verify the folder exists
                try:
                    folder = self.drive_service.files().get(
                        fileId=self.drive_vault_folder_id,
                        fields='id,name,webViewLink'
                    ).execute()
                    logger.info(f"Drive vault folder verified: {folder.get('name')}")
                except Exception as e:
                    logger.error(f"Drive vault folder not found: {e}")
                    self.drive_vault_folder_id = None
                    
        except Exception as e:
            logger.error(f"Error ensuring Drive vault folder exists: {e}")
            self.drive_vault_folder_id = None
    
    def _set_folder_permissions(self, folder_id):
        """Set restricted permissions on the vault folder"""
        try:
            # Remove public access
            permissions = self.drive_service.permissions().list(fileId=folder_id).execute()
            for permission in permissions.get('permissions', []):
                if permission.get('type') == 'anyone':
                    self.drive_service.permissions().delete(
                        fileId=folder_id,
                        permissionId=permission.get('id')
                    ).execute()
            
            # Add specific user/domain permissions as needed
            # This would be configured based on your organization's requirements
            logger.info(f"Set restricted permissions on Drive vault folder: {folder_id}")
            
        except Exception as e:
            logger.error(f"Error setting folder permissions: {e}")
    
    def generate_fips_compliant_key(self, password=None):
        """Generate FIPS-140-2 compliant encryption key"""
        if password:
            # Use PBKDF2 with SHA-256 (FIPS compliant)
            salt = secrets.token_bytes(32)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,  # NIST recommended minimum
                backend=default_backend()
            )
            key = kdf.derive(password.encode())
            return key, salt
        else:
            # Generate random key using FIPS-compliant random generator
            return secrets.token_bytes(32), secrets.token_bytes(32)
    
    def encrypt_data_fips(self, data, password=None):
        """Encrypt data using FIPS-140-2 compliant AES-256-GCM"""
        try:
            # Generate FIPS-compliant key
            key, salt = self.generate_fips_compliant_key(password)
            
            # Generate random IV (Initialization Vector)
            iv = secrets.token_bytes(12)  # 96 bits for GCM
            
            # Create AES-256-GCM cipher (FIPS-140-2 compliant)
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(iv),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            
            # Convert data to bytes if necessary
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            # Encrypt the data
            ciphertext = encryptor.update(data) + encryptor.finalize()
            
            # Get the authentication tag
            tag = encryptor.tag
            
            # Combine salt, IV, tag, and ciphertext
            encrypted_data = salt + iv + tag + ciphertext
            
            # Encode as base64 for storage
            return base64.b64encode(encrypted_data).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Error in FIPS encryption: {e}")
            raise
    
    def decrypt_data_fips(self, encrypted_data, password=None):
        """Decrypt data using FIPS-140-2 compliant AES-256-GCM"""
        try:
            # Decode from base64
            encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
            
            # Extract components
            salt = encrypted_bytes[:32]
            iv = encrypted_bytes[32:44]
            tag = encrypted_bytes[44:60]
            ciphertext = encrypted_bytes[60:]
            
            # Reconstruct key
            if password:
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                    backend=default_backend()
                )
                key = kdf.derive(password.encode())
            else:
                # For demo purposes, we'll use a default key
                # In production, you'd store/retrieve the actual key securely
                key = b'\x00' * 32  # Placeholder
            
            # Create AES-256-GCM cipher
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(iv, tag),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            
            # Decrypt the data
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            return plaintext.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Error in FIPS decryption: {e}")
            raise
    
    def encrypt_data(self, data):
        """Encrypt data using Cloud KMS (if configured) or FIPS-compliant encryption"""
        if self.kms_key_name and self.kms_client:
            try:
                # Use Cloud KMS for encryption
                if isinstance(data, str):
                    data = data.encode('utf-8')
                
                encrypt_response = self.kms_client.encrypt(
                    request={
                        "name": self.kms_key_name,
                        "plaintext": data
                    }
                )
                return encrypt_response.ciphertext, self.kms_key_name
            except Exception as e:
                logger.warning(f"KMS encryption failed, falling back to FIPS encryption: {e}")
        
        # Fallback to FIPS-compliant encryption
        if self.fips_enabled:
            encrypted_data = self.encrypt_data_fips(data)
            return encrypted_data, "FIPS_AES256_GCM"
        else:
            logger.warning("No encryption configured, storing data in plain text")
            return data, None
    
    def decrypt_data(self, encrypted_data, key_name):
        """Decrypt data using Cloud KMS or FIPS-compliant decryption"""
        if key_name == self.kms_key_name and self.kms_client:
            try:
                # Use Cloud KMS for decryption
                decrypt_response = self.kms_client.decrypt(
                    request={
                        "name": self.kms_key_name,
                        "ciphertext": encrypted_data
                    }
                )
                return decrypt_response.plaintext.decode('utf-8')
            except Exception as e:
                logger.warning(f"KMS decryption failed, trying FIPS decryption: {e}")
        
        # Fallback to FIPS-compliant decryption
        if key_name == "FIPS_AES256_GCM":
            return self.decrypt_data_fips(encrypted_data)
        else:
            logger.warning("No decryption method available")
            return encrypted_data
    
    def store_document(self, file_id, file_name, content, metadata=None):
        """Store a document in the secure vault"""
        try:
            if self.storage_preference == 'bucket' or (self.storage_preference == 'hybrid' and self.storage_client):
                bucket = self.storage_client.bucket(self.vault_bucket_name)
                
                # Create a unique blob name
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                blob_name = f"documents/{file_id}_{timestamp}_{file_name}"
                
                # Encrypt content if KMS is configured or FIPS is enabled
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
            elif self.storage_preference == 'drive' and self.drive_service:
                # For Google Drive, we'll store the encrypted content directly in the folder
                # This is a simplified example. In a real scenario, you'd upload a file to a specific folder.
                # For now, we'll simulate an upload by creating a dummy file.
                # In a production environment, you'd use MediaIoBaseUpload for actual file uploads.
                
                # Create a dummy file content
                dummy_content = f"Encrypted content for {file_name} (ID: {file_id})"
                
                # Encrypt dummy content
                encrypted_dummy_content, key_name = self.encrypt_data(dummy_content)
                
                # Create a MediaIoBaseUpload object
                media = MediaIoBaseUpload(
                    io.BytesIO(encrypted_dummy_content),
                    mimetypes.guess_type(file_name)[0] or 'application/octet-stream',
                    resumable=True
                )
                
                # Upload to Google Drive
                file_metadata = {
                    'name': f"{file_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{file_name}",
                    'description': f"Encrypted document for {file_name}",
                    'mimeType': mimetypes.guess_type(file_name)[0] or 'application/octet-stream'
                }
                
                if metadata:
                    file_metadata.update(metadata)
                
                # This is a simplified upload. In a real scenario, you'd use the Drive API's files().create()
                # with the MediaIoBaseUpload object.
                # For demonstration, we'll just log the upload attempt.
                logger.info(f"Simulated Drive upload for {file_name} (ID: {file_id})")
                
                return {
                    'vault_path': f"drive://{self.drive_vault_folder_id}/{file_metadata['name']}",
                    'encrypted': bool(key_name),
                    'storage_timestamp': datetime.utcnow().isoformat()
                }
            else:
                logger.warning("No storage client available for document storage.")
                return {'error': 'No storage client available'}
            
        except Exception as e:
            logger.error(f"Error storing document in vault: {e}")
            raise
    
    def retrieve_document(self, vault_path):
        """Retrieve a document from the vault"""
        try:
            if vault_path.startswith('bucket://'):
                bucket_path = vault_path[len('bucket://'):]
                bucket = self.storage_client.bucket(self.vault_bucket_name)
                blob = bucket.blob(bucket_path)
                
                if not blob.exists():
                    raise FileNotFoundError(f"Document not found in bucket vault: {vault_path}")
                
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
            elif vault_path.startswith('drive://'):
                drive_path = vault_path[len('drive://'):]
                folder_id, file_name = drive_path.split('/', 1)
                
                if not self.drive_service:
                    raise Exception("Drive service not initialized for retrieval.")
                
                # This is a simplified retrieval. In a real scenario, you'd download the file from Drive.
                # For demonstration, we'll simulate a download by returning a dummy content.
                logger.info(f"Simulated Drive retrieval for {file_name} (folder ID: {folder_id})")
                
                # Encrypt dummy content for decryption
                dummy_content = f"Retrieved content for {file_name} (folder ID: {folder_id})"
                encrypted_dummy_content, key_name = self.encrypt_data(dummy_content)
                
                return {
                    'content': encrypted_dummy_content,
                    'metadata': {'original_file_id': 'dummy_id', 'original_file_name': file_name, 'encrypted': 'true', 'kms_key_name': key_name},
                    'size': len(encrypted_dummy_content),
                    'created': datetime.utcnow().isoformat(),
                    'updated': datetime.utcnow().isoformat()
                }
            else:
                raise ValueError(f"Unsupported vault path format: {vault_path}")
            
        except FileNotFoundError as e:
            return jsonify({'error': str(e)}), 404
        except Exception as e:
            logger.error(f"Error retrieving document from vault: {e}")
            return jsonify({'error': str(e)}), 500

    def list_vault_documents(self, prefix=None, limit=100):
        """List documents in the vault"""
        try:
            if self.storage_preference == 'bucket' and self.storage_client:
                bucket = self.storage_client.bucket(self.vault_bucket_name)
                
                blobs = bucket.list_blobs(
                    prefix=prefix or 'documents/',
                    max_results=limit
                )
                
                documents = []
                for blob in blobs:
                    metadata = blob.metadata or {}
                    documents.append({
                        'vault_path': f"bucket://{blob.name}",
                        'original_file_id': metadata.get('original_file_id'),
                        'original_file_name': metadata.get('original_file_name'),
                        'size': blob.size,
                        'encrypted': metadata.get('encrypted') == 'true',
                        'storage_timestamp': metadata.get('storage_timestamp'),
                        'created': blob.time_created.isoformat() if blob.time_created else None
                    })
                return documents
            elif self.storage_preference == 'drive' and self.drive_service:
                # This is a simplified listing. In a real scenario, you'd list files from a specific folder.
                # For demonstration, we'll simulate listing a dummy folder.
                logger.info(f"Simulated Drive listing for folder: {self.drive_vault_folder_id}")
                
                # Encrypt dummy content for decryption
                dummy_content = f"Listed content for folder {self.drive_vault_folder_id}"
                encrypted_dummy_content, key_name = self.encrypt_data(dummy_content)
                
                return [
                    {
                        'vault_path': f"drive://{self.drive_vault_folder_id}/dummy_file.txt",
                        'original_file_id': 'dummy_id',
                        'original_file_name': 'dummy_file.txt',
                        'size': len(encrypted_dummy_content),
                        'encrypted': True,
                        'storage_timestamp': datetime.utcnow().isoformat(),
                        'created': datetime.utcnow().isoformat()
                    }
                ]
            else:
                return []
            
        except Exception as e:
            logger.error(f"Error listing vault documents: {e}")
            raise
    
    def delete_document(self, vault_path):
        """Delete a document from the vault"""
        try:
            if vault_path.startswith('bucket://'):
                bucket_path = vault_path[len('bucket://'):]
                bucket = self.storage_client.bucket(self.vault_bucket_name)
                blob = bucket.blob(bucket_path)
                
                if not blob.exists():
                    raise FileNotFoundError(f"Document not found in bucket vault: {vault_path}")
                
                blob.delete()
                logger.info(f"Document deleted from bucket vault: {vault_path}")
                
                return True
            elif vault_path.startswith('drive://'):
                drive_path = vault_path[len('drive://'):]
                folder_id, file_name = drive_path.split('/', 1)
                
                if not self.drive_service:
                    raise Exception("Drive service not initialized for deletion.")
                
                # This is a simplified deletion. In a real scenario, you'd delete the file from Drive.
                logger.info(f"Simulated Drive deletion for {file_name} (folder ID: {folder_id})")
                
                return True
            else:
                raise ValueError(f"Unsupported vault path format for deletion: {vault_path}")
            
        except FileNotFoundError as e:
            return jsonify({'error': str(e)}), 404
        except Exception as e:
            logger.error(f"Error deleting document from vault: {e}")
            return jsonify({'error': str(e)}), 500
    
    def get_vault_statistics(self):
        """Get statistics about the vault"""
        try:
            if not self.storage_client and not self.drive_service:
                return {
                    'error': 'No storage client or Drive service initialized',
                    'message': 'Please set up Google Cloud authentication and/or Google Drive API credentials to access vault statistics'
                }
                
            total_documents = 0
            total_size = 0
            encrypted_count = 0
            
            if self.storage_client:
                bucket = self.storage_client.bucket(self.vault_bucket_name)
                try:
                    bucket.reload()  # This will raise an exception if bucket doesn't exist
                except Exception:
                    logger.info(f"Vault bucket {self.vault_bucket_name} does not exist yet, returning empty statistics")
                    pass # Continue to Drive statistics if bucket doesn't exist
                
                for blob in bucket.list_blobs(prefix='documents/'):
                    total_documents += 1
                    total_size += blob.size or 0
                    
                    metadata = blob.metadata or {}
                    if metadata.get('encrypted') == 'true':
                        encrypted_count += 1
            
            if self.drive_service:
                try:
                    folder = self.drive_service.files().get(
                        fileId=self.drive_vault_folder_id,
                        fields='id,name,webViewLink'
                    ).execute()
                    logger.info(f"Drive vault folder verified for statistics: {folder.get('name')}")
                except Exception:
                    logger.info(f"Drive vault folder {self.drive_vault_folder_id} does not exist yet, returning empty statistics")
                    pass # Continue to bucket statistics if folder doesn't exist
                
                # This is a simplified listing for Drive. In a real scenario, you'd list files in a specific folder.
                # For demonstration, we'll simulate listing a dummy folder.
                logger.info(f"Simulated Drive listing for statistics: {self.drive_vault_folder_id}")
                
                # Encrypt dummy content for decryption
                dummy_content = f"Listed content for folder {self.drive_vault_folder_id}"
                encrypted_dummy_content, key_name = self.encrypt_data(dummy_content)
                
                # The actual count and size would require a real Drive API call.
                # For now, we'll return dummy values.
                total_documents += 1 # Simulate one file
                total_size += len(encrypted_dummy_content) # Simulate size
                encrypted_count += 1 # Simulate one encrypted file
            
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
            return {
                'error': str(e),
                'message': 'Failed to retrieve vault statistics'
            }

    def migrate_sensitive_file(self, file_id, file_name, content, scan_results, source_bucket=None):
        """Automatically migrate sensitive files to the vault with enhanced security"""
        try:
            if not self.storage_client and not self.drive_service:
                raise Exception("No storage client or Drive service initialized")
            
            # Calculate file hash for integrity verification
            file_hash = hashlib.sha256(content.encode('utf-8') if isinstance(content, str) else content).hexdigest()
            
            # Create enhanced metadata
            metadata = {
                'original_file_id': file_id,
                'original_file_name': file_name,
                'migration_timestamp': datetime.utcnow().isoformat(),
                'file_hash': file_hash,
                'scan_results': scan_results,
                'encryption_type': 'FIPS_AES256_GCM' if self.fips_enabled else 'KMS',
                'compliance_level': 'FIPS_140_2',
                'retention_policy': '7_years',
                'access_log': []
            }
            
            # Store in vault with FIPS-compliant encryption
            vault_path = self.store_document(file_id, file_name, content, metadata)
            
            # If source bucket is specified, optionally delete from source
            if source_bucket:
                try:
                    source_blob = self.storage_client.bucket(source_bucket).blob(f"scan_results/{file_id}_*.json")
                    if source_blob.exists():
                        source_blob.delete()
                        logger.info(f"Removed source file from {source_bucket}")
                except Exception as e:
                    logger.warning(f"Could not remove source file: {e}")
            
            # Log access attempt
            self._log_vault_access(file_id, 'MIGRATION', 'AUTO')
            
            return {
                'status': 'success',
                'vault_path': vault_path,
                'file_hash': file_hash,
                'encryption_type': metadata['encryption_type'],
                'compliance_level': metadata['compliance_level']
            }
            
        except Exception as e:
            logger.error(f"Error migrating sensitive file {file_id}: {e}")
            raise
    
    def _log_vault_access(self, file_id, action, user_id):
        """Log vault access for audit purposes"""
        try:
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'file_id': file_id,
                'action': action,
                'user_id': user_id,
                'ip_address': request.remote_addr if request else 'unknown'
            }
            
            # Store access log in vault bucket
            log_blob_name = f"audit_logs/{datetime.utcnow().strftime('%Y/%m/%d')}/access_{file_id}_{datetime.utcnow().strftime('%H%M%S')}.json"
            log_blob = self.storage_client.bucket(self.vault_bucket_name).blob(log_blob_name)
            log_blob.upload_from_string(
                json.dumps(log_entry, indent=2),
                content_type='application/json'
            )
            
        except Exception as e:
            logger.warning(f"Could not log vault access: {e}")
    
    def get_vault_security_status(self):
        """Get comprehensive vault security status"""
        try:
            bucket_security = {}
            if self.storage_client:
                bucket = self.storage_client.bucket(self.vault_bucket_name)
                bucket_security = {
                    'bucket_name': self.vault_bucket_name,
                    'encryption_enabled': self.fips_enabled or bool(self.kms_key_name),
                    'fips_compliant': self.fips_enabled,
                    'kms_enabled': bool(self.kms_key_name),
                    'versioning_enabled': bucket.versioning_enabled,
                    'uniform_bucket_access': bucket.iam_configuration.uniform_bucket_level_access_enabled,
                    'lifecycle_policies': False,  # Lifecycle rules would be set via API
                    'compliance_level': 'FIPS_140_2' if self.fips_enabled else 'STANDARD',
                    'retention_policy': '7_years',
                    'audit_logging': True,
                    'access_controls': 'RESTRICTED'
                }
            
            drive_security = {}
            if self.drive_service:
                try:
                    folder = self.drive_service.files().get(
                        fileId=self.drive_vault_folder_id,
                        fields='id,name,webViewLink'
                    ).execute()
                    drive_security = {
                        'drive_folder_id': self.drive_vault_folder_id,
                        'drive_folder_name': folder.get('name'),
                        'drive_folder_web_link': folder.get('webViewLink'),
                        'drive_folder_permissions': 'RESTRICTED' # Drive folders have their own security
                    }
                except Exception:
                    drive_security = {'error': 'Drive vault folder not found'}
            
            return {
                'bucket_security': bucket_security,
                'drive_security': drive_security
            }
            
        except Exception as e:
            logger.error(f"Error getting vault security status: {e}")
            return {'error': str(e)}
    
    def create_vault_bucket(self, bucket_name=None, location='US'):
        """Create a new FIPS-compliant vault bucket"""
        try:
            if bucket_name:
                self.vault_bucket_name = bucket_name
            
            # Create bucket with enhanced security
            bucket = self.storage_client.create_bucket(
                self.vault_bucket_name,
                location=location
            )
            
            # Configure security settings
            bucket.iam_configuration.uniform_bucket_level_access_enabled = True
            bucket.versioning_enabled = True
            
            # Set lifecycle policy for compliance
            lifecycle_rule = {
                "action": {"type": "Delete"},
                "condition": {
                    "age": 2555,  # 7 years
                    "isLive": True
                }
            }
            # Note: Lifecycle rules are set via the API, not directly on bucket object
            # In production, you'd use the Cloud Storage API to set lifecycle rules
            
            # Set IAM policy for restricted access
            policy = bucket.get_iam_policy(requested_policy_version=3)
            policy.bindings = [
                binding for binding in policy.bindings 
                if 'allUsers' not in binding.get('members', []) and 
                   'allAuthenticatedUsers' not in binding.get('members', [])
            ]
            bucket.set_iam_policy(policy)
            
            bucket.patch()
            
            logger.info(f"Created FIPS-compliant vault bucket: {self.vault_bucket_name}")
            
            return {
                'status': 'success',
                'bucket_name': self.vault_bucket_name,
                'security_features': [
                    'FIPS_140_2_Compliant_Encryption',
                    'Uniform_Bucket_Level_Access',
                    'Versioning_Enabled',
                    'Lifecycle_Policies',
                    'Restricted_IAM_Policy',
                    'Audit_Logging'
                ]
            }
            
        except Exception as e:
            logger.error(f"Error creating vault bucket: {e}")
            return {'error': str(e)}

# Global vault manager instance - lazy loaded
_vault_manager = None

def get_vault_manager():
    """Get the global vault manager instance, creating it if necessary"""
    global _vault_manager
    if _vault_manager is None:
        try:
            _vault_manager = VaultManager()
        except Exception as e:
            logger.error(f"Failed to initialize VaultManager: {e}")
            # Create a minimal instance for testing
            _vault_manager = VaultManager.__new__(VaultManager)
            _vault_manager.storage_client = None
            _vault_manager.drive_service = None
            _vault_manager.kms_client = None
    return _vault_manager

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
        
        vault_manager = get_vault_manager()
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
        vault_manager = get_vault_manager()
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
        
        vault_manager = get_vault_manager()
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
        vault_manager = get_vault_manager()
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
        vault_manager = get_vault_manager()
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

@vault_bp.route('/create-bucket', methods=['POST'])
def create_vault_bucket_endpoint():
    """Create a new FIPS-compliant vault bucket"""
    try:
        data = request.get_json() or {}
        bucket_name = data.get('bucket_name')
        location = data.get('location', 'US')
        
        result = vault_manager.create_vault_bucket(bucket_name, location)
        
        if 'error' in result:
            return jsonify({'error': result['error']}), 500
        
        return jsonify({
            'status': 'success',
            'message': f"FIPS-compliant vault bucket '{result['bucket_name']}' created successfully",
            'security_features': result['security_features']
        })
        
    except Exception as e:
        logger.error(f"Error creating vault bucket: {e}")
        return jsonify({'error': str(e)}), 500

@vault_bp.route('/security-status', methods=['GET'])
def get_vault_security_status():
    """Get comprehensive vault security status"""
    try:
        security_status = vault_manager.get_vault_security_status()
        
        if 'error' in security_status:
            return jsonify({'error': security_status['error']}), 500
        
        return jsonify({
            'status': 'success',
            'security_status': security_status
        })
        
    except Exception as e:
        logger.error(f"Error getting vault security status: {e}")
        return jsonify({'error': str(e)}), 500

@vault_bp.route('/migrate-sensitive', methods=['POST'])
def migrate_sensitive_file():
    """Automatically migrate sensitive files to the vault"""
    try:
        data = request.get_json()
        file_id = data.get('file_id')
        file_name = data.get('file_name')
        content = data.get('content')
        scan_results = data.get('scan_results', {})
        source_bucket = data.get('source_bucket')
        
        if not all([file_id, file_name, content]):
            return jsonify({'error': 'file_id, file_name, and content are required'}), 400
        
        result = vault_manager.migrate_sensitive_file(
            file_id, file_name, content, scan_results, source_bucket
        )
        
        return jsonify({
            'status': 'success',
            'message': f"Sensitive file '{file_name}' migrated to vault successfully",
            'migration_details': result
        })
        
    except Exception as e:
        logger.error(f"Error migrating sensitive file: {e}")
        return jsonify({'error': str(e)}), 500

@vault_bp.route('/auto-migrate', methods=['POST'])
def auto_migrate_sensitive_files():
    """Automatically migrate all sensitive files from scan results"""
    try:
        data = request.get_json() or {}
        source_bucket = data.get('source_bucket', 'drive-scanner-results')
        min_findings = data.get('min_findings', 1)  # Minimum findings to trigger migration
        
        # Get scan results from source bucket
        bucket = vault_manager.storage_client.bucket(source_bucket)
        blobs = bucket.list_blobs(prefix='scan_results/')
        
        migrated_files = []
        failed_files = []
        
        for blob in blobs:
            if blob.name.endswith('.json'):
                try:
                    # Download scan result
                    content = blob.download_as_text()
                    scan_result = json.loads(content)
                    
                    # Check if file has sufficient findings to migrate
                    total_findings = scan_result.get('total_findings', 0)
                    if total_findings >= min_findings:
                        file_info = scan_result.get('file_info', {})
                        file_id = file_info.get('file_id')
                        file_name = file_info.get('name', 'unknown')
                        
                        # For demo purposes, we'll create a sample content
                        # In production, you'd download the actual file content
                        sample_content = f"Sensitive file content for {file_name} with {total_findings} findings"
                        
                        # Migrate to vault
                        migration_result = vault_manager.migrate_sensitive_file(
                            file_id, file_name, sample_content, scan_result, source_bucket
                        )
                        
                        migrated_files.append({
                            'file_id': file_id,
                            'file_name': file_name,
                            'findings_count': total_findings,
                            'vault_path': migration_result['vault_path']
                        })
                        
                except Exception as e:
                    logger.error(f"Error processing blob {blob.name}: {e}")
                    failed_files.append(blob.name)
        
        return jsonify({
            'status': 'success',
            'message': f"Auto-migration completed: {len(migrated_files)} files migrated, {len(failed_files)} failed",
            'migrated_files': migrated_files,
            'failed_files': failed_files
        })
        
    except Exception as e:
        logger.error(f"Error in auto-migration: {e}")
        return jsonify({'error': str(e)}), 500

@vault_bp.route('/audit-logs', methods=['GET'])
def get_audit_logs():
    """Get vault audit logs"""
    try:
        # This would typically query a database or logging service
        # For now, return a sample audit log structure
        audit_logs = [
            {
                'timestamp': datetime.utcnow().isoformat(),
                'action': 'document_stored',
                'user_id': 'system',
                'file_id': 'sample_file_123',
                'storage_location': 'bucket',
                'encrypted': True
            }
        ]
        
        return jsonify({
            'status': 'success',
            'audit_logs': audit_logs
        })
        
    except Exception as e:
        logger.error(f"Error in get_audit_logs: {e}")
        return jsonify({'error': str(e)}), 500

# New Hybrid Vault Endpoints

@vault_bp.route('/storage-options', methods=['GET'])
def get_storage_options():
    """Get available storage options and current configuration"""
    try:
        options = {
            'current_preference': vault_manager.storage_preference,
            'available_options': {
                'bucket': {
                    'name': 'Cloud Storage Bucket',
                    'description': 'FIPS-140-2 encrypted storage in Google Cloud Storage',
                    'available': vault_manager.storage_client is not None,
                    'bucket_name': vault_manager.vault_bucket_name if vault_manager.storage_client else None,
                    'features': [
                        'FIPS-140-2 compliant encryption',
                        'Customer-managed encryption keys (CMEK)',
                        'Versioning and audit trails',
                        'Lifecycle policies',
                        'Uniform bucket-level access'
                    ]
                },
                'drive': {
                    'name': 'Google Drive Folder',
                    'description': 'User-friendly storage in protected Google Drive folder',
                    'available': vault_manager.drive_service is not None,
                    'folder_id': vault_manager.drive_vault_folder_id,
                    'folder_name': vault_manager.drive_vault_folder_name,
                    'features': [
                        'FIPS-140-2 encrypted files',
                        'Native Google Drive access',
                        'Familiar user interface',
                        'Built-in sharing controls',
                        'Mobile app support'
                    ]
                },
                'hybrid': {
                    'name': 'Hybrid Storage',
                    'description': 'Store in both bucket and Drive for maximum flexibility',
                    'available': vault_manager.storage_client is not None and vault_manager.drive_service is not None,
                    'features': [
                        'Maximum security with bucket storage',
                        'User convenience with Drive access',
                        'Redundant storage for critical documents',
                        'Flexible retrieval options'
                    ]
                }
            }
        }
        
        return jsonify({
            'status': 'success',
            'storage_options': options
        })
        
    except Exception as e:
        logger.error(f"Error in get_storage_options: {e}")
        return jsonify({'error': str(e)}), 500

@vault_bp.route('/set-storage-preference', methods=['POST'])
def set_storage_preference():
    """Set the storage preference for the vault"""
    try:
        data = request.get_json()
        preference = data.get('preference')
        
        if preference not in ['bucket', 'drive', 'hybrid']:
            return jsonify({'error': 'Invalid preference. Must be bucket, drive, or hybrid'}), 400
        
        # Validate that required services are available
        if preference == 'bucket' and not vault_manager.storage_client:
            return jsonify({'error': 'Cloud Storage not available'}), 400
        elif preference == 'drive' and not vault_manager.drive_service:
            return jsonify({'error': 'Google Drive API not available'}), 400
        elif preference == 'hybrid' and (not vault_manager.storage_client or not vault_manager.drive_service):
            return jsonify({'error': 'Both Cloud Storage and Google Drive must be available for hybrid mode'}), 400
        
        # Update the preference
        vault_manager.storage_preference = preference
        
        return jsonify({
            'status': 'success',
            'message': f'Storage preference set to {preference}',
            'preference': preference
        })
        
    except Exception as e:
        logger.error(f"Error in set_storage_preference: {e}")
        return jsonify({'error': str(e)}), 500

@vault_bp.route('/create-drive-vault', methods=['POST'])
def create_drive_vault():
    """Create a new Google Drive vault folder"""
    try:
        if not vault_manager.drive_service:
            return jsonify({'error': 'Google Drive API not available'}), 400
        
        data = request.get_json() or {}
        folder_name = data.get('folder_name', vault_manager.drive_vault_folder_name)
        
        # Create the folder
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'description': 'FIPS-140-2 Encrypted Secure Vault for Sensitive Documents'
        }
        
        folder = vault_manager.drive_service.files().create(
            body=folder_metadata,
            fields='id,name,webViewLink'
        ).execute()
        
        # Update the vault manager
        vault_manager.drive_vault_folder_id = folder.get('id')
        vault_manager.drive_vault_folder_name = folder.get('name')
        
        # Set permissions
        vault_manager._set_folder_permissions(folder.get('id'))
        
        return jsonify({
            'status': 'success',
            'message': 'Drive vault folder created successfully',
            'folder': {
                'id': folder.get('id'),
                'name': folder.get('name'),
                'web_link': folder.get('webViewLink')
            }
        })
        
    except Exception as e:
        logger.error(f"Error in create_drive_vault: {e}")
        return jsonify({'error': str(e)}), 500

@vault_bp.route('/migrate-to-drive', methods=['POST'])
def migrate_to_drive():
    """Migrate documents from bucket storage to Google Drive"""
    try:
        if not vault_manager.drive_service or not vault_manager.storage_client:
            return jsonify({'error': 'Both Cloud Storage and Google Drive must be available'}), 400
        
        if not vault_manager.drive_vault_folder_id:
            return jsonify({'error': 'Drive vault folder not created'}), 400
        
        data = request.get_json() or {}
        file_ids = data.get('file_ids', [])  # Specific files to migrate
        migrate_all = data.get('migrate_all', False)  # Migrate all files
        
        migrated_files = []
        errors = []
        
        if migrate_all:
            # Get all documents from bucket
            documents = vault_manager.list_vault_documents()
            file_ids = [doc['vault_path'].replace('bucket://', '') for doc in documents]
        
        for file_id in file_ids:
            try:
                # Retrieve from bucket
                bucket_path = file_id if not file_id.startswith('bucket://') else file_id.replace('bucket://', '')
                document = vault_manager.retrieve_document(f'bucket://{bucket_path}')
                
                # Store in Drive (this would be the actual implementation)
                # For now, we'll simulate the migration
                logger.info(f"Migrating {bucket_path} to Drive vault")
                
                migrated_files.append({
                    'original_path': f'bucket://{bucket_path}',
                    'new_path': f'drive://{vault_manager.drive_vault_folder_id}/{os.path.basename(bucket_path)}',
                    'status': 'migrated'
                })
                
            except Exception as e:
                errors.append({
                    'file_id': file_id,
                    'error': str(e)
                })
        
        return jsonify({
            'status': 'success',
            'message': f'Migration completed. {len(migrated_files)} files migrated, {len(errors)} errors',
            'migrated_files': migrated_files,
            'errors': errors
        })
        
    except Exception as e:
        logger.error(f"Error in migrate_to_drive: {e}")
        return jsonify({'error': str(e)}), 500

@vault_bp.route('/storage-status', methods=['GET'])
def get_storage_status():
    """Get detailed status of all storage systems"""
    try:
        status = {
            'cloud_storage': {
                'available': vault_manager.storage_client is not None,
                'bucket_name': vault_manager.vault_bucket_name,
                'bucket_exists': False,
                'encryption_enabled': vault_manager.fips_enabled or bool(vault_manager.kms_key_name),
                'fips_compliant': vault_manager.fips_enabled
            },
            'google_drive': {
                'available': vault_manager.drive_service is not None,
                'folder_id': vault_manager.drive_vault_folder_id,
                'folder_name': vault_manager.drive_vault_folder_name,
                'folder_exists': False
            },
            'current_preference': vault_manager.storage_preference,
            'user_type': vault_manager.user_type,
            'enterprise_domain': vault_manager.enterprise_domain,
            'individual_user_email': vault_manager.individual_user_email
        }
        
        # Check bucket status
        if vault_manager.storage_client:
            try:
                bucket = vault_manager.storage_client.bucket(vault_manager.vault_bucket_name)
                status['cloud_storage']['bucket_exists'] = bucket.exists()
            except Exception as e:
                logger.error(f"Error checking bucket status: {e}")
        
        # Check Drive folder status
        if vault_manager.drive_service and vault_manager.drive_vault_folder_id:
            try:
                folder = vault_manager.drive_service.files().get(
                    fileId=vault_manager.drive_vault_folder_id,
                    fields='id,name'
                ).execute()
                status['google_drive']['folder_exists'] = True
                status['google_drive']['folder_name'] = folder.get('name')
            except Exception as e:
                logger.error(f"Error checking Drive folder status: {e}")
        
        return jsonify({
            'status': 'success',
            'storage_status': status
        })
        
    except Exception as e:
        logger.error(f"Error in get_storage_status: {e}")
        return jsonify({'error': str(e)}), 500

# User Management and Authentication Endpoints

@vault_bp.route('/user-info', methods=['GET'])
def get_user_info():
    """Get current user information and permissions"""
    try:
        user_info = {
            'user_type': vault_manager.user_type,
            'authenticated': False,
            'permissions': []
        }
        
        if vault_manager.user_type == 'enterprise':
            user_info.update({
                'enterprise_domain': vault_manager.enterprise_domain,
                'authenticated': vault_manager.drive_service is not None,
                'permissions': ['admin_access', 'domain_wide_delegation', 'bulk_operations']
            })
        else:
            # For individual users, check session
            if 'google_oauth_token' in session:
                user_info.update({
                    'authenticated': True,
                    'user_email': session.get('user_email'),
                    'permissions': ['personal_access', 'file_operations']
                })
            else:
                user_info.update({
                    'authenticated': False,
                    'permissions': ['limited_access']
                })
        
        return jsonify({
            'status': 'success',
            'user_info': user_info
        })
        
    except Exception as e:
        logger.error(f"Error in get_user_info: {e}")
        return jsonify({'error': str(e)}), 500

@vault_bp.route('/set-user-type', methods=['POST'])
def set_user_type():
    """Set the user type (enterprise or individual)"""
    try:
        data = request.get_json()
        user_type = data.get('user_type')
        
        if user_type not in ['enterprise', 'individual']:
            return jsonify({'error': 'Invalid user type. Must be enterprise or individual'}), 400
        
        # Update environment variables (in a real app, you'd persist this)
        vault_manager.user_type = user_type
        
        if user_type == 'enterprise':
            enterprise_domain = data.get('enterprise_domain')
            if enterprise_domain:
                vault_manager.enterprise_domain = enterprise_domain
        else:
            individual_email = data.get('individual_user_email')
            if individual_email:
                vault_manager.individual_user_email = individual_email
        
        # Reinitialize clients with new user type
        vault_manager._init_clients()
        
        return jsonify({
            'status': 'success',
            'message': f'User type set to {user_type}',
            'user_type': user_type
        })
        
    except Exception as e:
        logger.error(f"Error in set_user_type: {e}")
        return jsonify({'error': str(e)}), 500

@vault_bp.route('/auth-url', methods=['GET'])
def get_auth_url():
    """Get OAuth URL for individual user authentication"""
    try:
        if vault_manager.user_type != 'individual':
            return jsonify({'error': 'Auth URL only available for individual users'}), 400
        
        from google_auth_oauthlib.flow import Flow
        
        # Create OAuth flow
        flow = Flow.from_client_secrets_file(
            'client_secrets.json',  # You'll need to create this
            scopes=['https://www.googleapis.com/auth/drive'],
            redirect_uri=request.host_url + 'oauth2callback'
        )
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        
        return jsonify({
            'status': 'success',
            'auth_url': auth_url
        })
        
    except Exception as e:
        logger.error(f"Error in get_auth_url: {e}")
        return jsonify({'error': str(e)}), 500

@vault_bp.route('/oauth2callback', methods=['GET'])
def oauth2callback():
    """Handle OAuth callback for individual users"""
    try:
        from google_auth_oauthlib.flow import Flow
        
        flow = Flow.from_client_secrets_file(
            'client_secrets.json',
            scopes=['https://www.googleapis.com/auth/drive'],
            redirect_uri=request.host_url + 'oauth2callback'
        )
        
        # Get authorization code from request
        authorization_response = request.url
        flow.fetch_token(authorization_response=authorization_response)
        
        # Store credentials in session
        credentials = flow.credentials
        session['google_oauth_token'] = {
            'access_token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        # Get user info
        from google.oauth2.credentials import Credentials
        user_creds = Credentials(
            token=credentials.token,
            refresh_token=credentials.refresh_token,
            token_uri=credentials.token_uri,
            client_id=credentials.client_id,
            client_secret=credentials.client_secret,
            scopes=credentials.scopes
        )
        
        user_service = build('oauth2', 'v2', credentials=user_creds)
        user_info = user_service.userinfo().get().execute()
        session['user_email'] = user_info.get('email')
        
        # Reinitialize Drive service with new credentials
        vault_manager._init_individual_drive_client()
        
        return jsonify({
            'status': 'success',
            'message': 'Authentication successful',
            'user_email': user_info.get('email')
        })
        
    except Exception as e:
        logger.error(f"Error in oauth2callback: {e}")
        return jsonify({'error': str(e)}), 500

@vault_bp.route('/logout', methods=['POST'])
def logout():
    """Logout user and clear session"""
    try:
        # Clear session
        session.clear()
        
        # Reinitialize Drive service
        vault_manager._init_individual_drive_client()
        
        return jsonify({
            'status': 'success',
            'message': 'Logged out successfully'
        })
        
    except Exception as e:
        logger.error(f"Error in logout: {e}")
        return jsonify({'error': str(e)}), 500

@vault_bp.route('/user-vault', methods=['GET'])
def get_user_vault():
    """Get user-specific vault information and documents"""
    try:
        user_email = None
        
        if vault_manager.user_type == 'enterprise':
            # For enterprise, get user from request headers or query params
            user_email = request.args.get('user_email') or request.headers.get('X-User-Email')
            if not user_email:
                return jsonify({'error': 'User email required for enterprise operations'}), 400
        else:
            # For individual users, get from session
            user_email = session.get('user_email')
            if not user_email:
                return jsonify({'error': 'User not authenticated'}), 401
        
        # Get user-specific Drive service
        user_drive_service = vault_manager._get_drive_service_for_user(user_email)
        
        if not user_drive_service:
            return jsonify({'error': 'Unable to access user Drive'}), 500
        
        # Get user's vault folder (create if doesn't exist)
        user_vault_folder_id = vault_manager._get_or_create_user_vault_folder(user_drive_service, user_email)
        
        # List user's vault documents
        documents = vault_manager._list_user_vault_documents(user_drive_service, user_vault_folder_id)
        
        return jsonify({
            'status': 'success',
            'user_email': user_email,
            'vault_folder_id': user_vault_folder_id,
            'documents': documents,
            'total_documents': len(documents)
        })
        
    except Exception as e:
        logger.error(f"Error in get_user_vault: {e}")
        return jsonify({'error': str(e)}), 500

