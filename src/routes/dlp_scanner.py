"""
DLP Scanner routes for Google Drive Sensitive Data Scanner
"""
import os
import json
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from google.cloud import dlp_v2
from google.cloud import storage
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.auth import default
import io

dlp_bp = Blueprint('dlp', __name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DLPScanner:
    def __init__(self):
        self.dlp_client = None
        self.storage_client = None
        self.project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
        
        # Initialize clients
        self._init_clients()
    
    def _init_clients(self):
        """Initialize Google Cloud clients with fallback authentication"""
        try:
            # Initialize DLP client
            self.dlp_client = dlp_v2.DlpServiceClient()
            logger.info("DLP client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DLP client: {e}")
            self.dlp_client = None
        
        try:
            # Initialize Storage client
            self.storage_client = storage.Client()
            logger.info("Storage client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Storage client: {e}")
            self.storage_client = None
        
        # Initialize Drive API client
        self.drive_service = None
        self._init_drive_service()
    
    def _init_drive_service(self):
        """Initialize Google Drive API service with fallback authentication"""
        try:
            # First try service account credentials
            credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if credentials_path and os.path.exists(credentials_path):
                logger.info("Using service account credentials")
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path,
                    scopes=['https://www.googleapis.com/auth/drive.readonly']
                )
                self.drive_service = build('drive', 'v3', credentials=credentials)
            else:
                # Fallback to user credentials (application default)
                logger.info("Using application default credentials")
                credentials, project = default(scopes=['https://www.googleapis.com/auth/drive.readonly'])
                self.drive_service = build('drive', 'v3', credentials=credentials)
                logger.info(f"Authenticated as user for project: {project}")
        except Exception as e:
            logger.error(f"Failed to initialize Drive service: {e}")
            logger.info("Drive service will not be available. Please set up authentication.")
    
    def get_sensitive_info_types(self):
        """Get the list of infoTypes to scan for sensitive data"""
        return [
            {"name": "PERSON_NAME"},
            {"name": "EMAIL_ADDRESS"},
            {"name": "PHONE_NUMBER"},
            {"name": "US_SOCIAL_SECURITY_NUMBER"},
            {"name": "CREDIT_CARD_NUMBER"},
            {"name": "US_DRIVERS_LICENSE_NUMBER"},
            {"name": "US_PASSPORT"},
            {"name": "DATE_OF_BIRTH"},
            {"name": "MEDICAL_RECORD_NUMBER"},
            {"name": "US_BANK_ROUTING_MICR"},
            {"name": "IBAN_CODE"},
            {"name": "SWIFT_CODE"}
        ]
    
    def download_file_content(self, file_id):
        """Download file content from Google Drive"""
        try:
            if not self.drive_service:
                raise Exception("Drive service not initialized")
            
            # Get file metadata
            file_metadata = self.drive_service.files().get(fileId=file_id).execute()
            file_name = file_metadata.get('name', 'unknown')
            mime_type = file_metadata.get('mimeType', '')
            
            # Download file content based on MIME type
            if 'google-apps' in mime_type:
                # Handle Google Workspace files (Docs, Sheets, Slides)
                if 'document' in mime_type:
                    export_mime_type = 'text/plain'
                elif 'spreadsheet' in mime_type:
                    export_mime_type = 'text/csv'
                elif 'presentation' in mime_type:
                    export_mime_type = 'text/plain'
                else:
                    export_mime_type = 'application/pdf'
                
                request = self.drive_service.files().export_media(
                    fileId=file_id, 
                    mimeType=export_mime_type
                )
            else:
                # Handle regular files
                request = self.drive_service.files().get_media(fileId=file_id)
            
            file_content = request.execute()
            
            return {
                'content': file_content,
                'name': file_name,
                'mime_type': mime_type,
                'size': len(file_content)
            }
            
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {e}")
            raise
    
    def inspect_content(self, content, file_info):
        """Inspect content using Google Cloud DLP API"""
        try:
            # Prepare the content item
            if isinstance(content, bytes):
                content_item = {
                    "byte_item": {
                        "type_": dlp_v2.ByteContentItem.BytesType.BYTES_TYPE_UNSPECIFIED,
                        "data": content
                    }
                }
            else:
                content_item = {
                    "value": content
                }
            
            # Configure inspection
            inspect_config = {
                "info_types": self.get_sensitive_info_types(),
                "min_likelihood": dlp_v2.Likelihood.POSSIBLE,
                "limits": {"max_findings_per_request": 100},
                "include_quote": True
            }
            
            # Create the request
            parent = f"projects/{self.project_id}"
            request = {
                "parent": parent,
                "inspect_config": inspect_config,
                "item": content_item
            }
            
            # Call the DLP API
            response = self.dlp_client.inspect_content(request=request)
            
            # Process findings
            findings = []
            if response.result.findings:
                for finding in response.result.findings:
                    finding_dict = {
                        "info_type": finding.info_type.name,
                        "likelihood": finding.likelihood.name,
                        "quote": finding.quote,
                        "location": {
                            "byte_range": {
                                "start": finding.location.byte_range.start,
                                "end": finding.location.byte_range.end
                            }
                        }
                    }
                    findings.append(finding_dict)
            
            return {
                "file_info": file_info,
                "findings": findings,
                "scan_timestamp": datetime.utcnow().isoformat(),
                "total_findings": len(findings)
            }
            
        except Exception as e:
            logger.error(f"Error inspecting content: {e}")
            raise
    
    def store_scan_results(self, scan_results, file_id):
        """Store scan results in Cloud Storage"""
        try:
            if not self.storage_client:
                logger.warning("Storage client not initialized, skipping result storage")
                return None
                
            bucket_name = os.environ.get('SCAN_RESULTS_BUCKET', 'drive-scanner-results')
            bucket = self.storage_client.bucket(bucket_name)
            
            # Create a unique filename for the results
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            blob_name = f"scan_results/{file_id}_{timestamp}.json"
            
            blob = bucket.blob(blob_name)
            blob.upload_from_string(
                json.dumps(scan_results, indent=2),
                content_type='application/json'
            )
            
            logger.info(f"Scan results stored: {blob_name}")
            return blob_name
            
        except Exception as e:
            logger.error(f"Error storing scan results: {e}")
            raise
    
    def move_to_vault(self, file_id, scan_results):
        """Move sensitive documents to secure vault"""
        try:
            if scan_results['total_findings'] == 0:
                logger.info(f"No sensitive data found in {file_id}, skipping vault storage")
                return None
            
            # Download the original file
            file_data = self.download_file_content(file_id)
            
            # Store in vault bucket
            vault_bucket_name = os.environ.get('VAULT_BUCKET', 'drive-scanner-vault')
            bucket = self.storage_client.bucket(vault_bucket_name)
            
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            blob_name = f"vault/{file_id}_{timestamp}_{file_data['name']}"
            
            blob = bucket.blob(blob_name)
            blob.upload_from_string(
                file_data['content'] if isinstance(file_data['content'], str) else file_data['content'],
                content_type=file_data['mime_type']
            )
            
            # Add metadata
            blob.metadata = {
                'original_file_id': file_id,
                'scan_timestamp': scan_results['scan_timestamp'],
                'findings_count': str(scan_results['total_findings']),
                'file_name': file_data['name']
            }
            blob.patch()
            
            logger.info(f"File moved to vault: {blob_name}")
            return blob_name
            
        except Exception as e:
            logger.error(f"Error moving file to vault: {e}")
            raise

# Initialize scanner instance
scanner = DLPScanner()

@dlp_bp.route('/scan', methods=['POST'])
def scan_file():
    """Scan a Google Drive file for sensitive data"""
    try:
        data = request.get_json()
        file_id = data.get('file_id')
        
        if not file_id:
            return jsonify({'error': 'file_id is required'}), 400
        
        # Download file content
        logger.info(f"Downloading file: {file_id}")
        file_data = scanner.download_file_content(file_id)
        
        # Inspect content for sensitive data
        logger.info(f"Inspecting file: {file_data['name']}")
        scan_results = scanner.inspect_content(file_data['content'], {
            'file_id': file_id,
            'name': file_data['name'],
            'mime_type': file_data['mime_type'],
            'size': file_data['size']
        })
        
        # Store scan results
        results_path = scanner.store_scan_results(scan_results, file_id)
        
        # Move to vault if sensitive data found
        vault_path = scanner.move_to_vault(file_id, scan_results)
        
        response = {
            'status': 'success',
            'file_id': file_id,
            'file_name': file_data['name'],
            'findings_count': scan_results['total_findings'],
            'results_stored_at': results_path,
            'vault_path': vault_path,
            'scan_timestamp': scan_results['scan_timestamp']
        }
        
        if scan_results['total_findings'] > 0:
            response['findings'] = scan_results['findings']
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in scan_file: {e}")
        return jsonify({'error': str(e)}), 500

@dlp_bp.route('/scan/batch', methods=['POST'])
def scan_batch():
    """Scan multiple Google Drive files for sensitive data"""
    try:
        data = request.get_json()
        file_ids = data.get('file_ids', [])
        
        if not file_ids:
            return jsonify({'error': 'file_ids array is required'}), 400
        
        results = []
        for file_id in file_ids:
            try:
                # Download and scan each file
                file_data = scanner.download_file_content(file_id)
                scan_results = scanner.inspect_content(file_data['content'], {
                    'file_id': file_id,
                    'name': file_data['name'],
                    'mime_type': file_data['mime_type'],
                    'size': file_data['size']
                })
                
                # Store results and move to vault if needed
                results_path = scanner.store_scan_results(scan_results, file_id)
                vault_path = scanner.move_to_vault(file_id, scan_results)
                
                results.append({
                    'file_id': file_id,
                    'file_name': file_data['name'],
                    'findings_count': scan_results['total_findings'],
                    'results_stored_at': results_path,
                    'vault_path': vault_path,
                    'status': 'success'
                })
                
            except Exception as e:
                logger.error(f"Error scanning file {file_id}: {e}")
                results.append({
                    'file_id': file_id,
                    'status': 'error',
                    'error': str(e)
                })
        
        return jsonify({
            'status': 'completed',
            'total_files': len(file_ids),
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error in scan_batch: {e}")
        return jsonify({'error': str(e)}), 500

@dlp_bp.route('/results/<file_id>', methods=['GET'])
def get_scan_results(file_id):
    """Get scan results for a specific file"""
    try:
        bucket_name = os.environ.get('SCAN_RESULTS_BUCKET', 'drive-scanner-results')
        bucket = scanner.storage_client.bucket(bucket_name)
        
        # List blobs with the file_id prefix
        blobs = list(bucket.list_blobs(prefix=f"scan_results/{file_id}_"))
        
        if not blobs:
            return jsonify({'error': 'No scan results found for this file'}), 404
        
        # Get the most recent result
        latest_blob = max(blobs, key=lambda b: b.time_created)
        content = latest_blob.download_as_text()
        scan_results = json.loads(content)
        
        return jsonify(scan_results)
        
    except Exception as e:
        logger.error(f"Error getting scan results: {e}")
        return jsonify({'error': str(e)}), 500

@dlp_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'DLP Scanner',
        'timestamp': datetime.utcnow().isoformat()
    })

