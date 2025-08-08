"""
Google Drive monitoring routes for detecting file changes
"""
import os
import json
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.auth import default
from google.cloud import pubsub_v1
import requests

drive_bp = Blueprint('drive', __name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DriveMonitor:
    def __init__(self):
        self.drive_service = None
        self.publisher = None
        self.project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
        self.topic_name = os.environ.get('SCAN_REQUEST_TOPIC', 'drive-scan-requests')
        self.topic_path = None
        
        self._init_clients()
        self._init_drive_service()
    
    def _init_clients(self):
        """Initialize Google Cloud clients with fallback authentication"""
        try:
            # Initialize PubSub client
            self.publisher = pubsub_v1.PublisherClient()
            self.topic_path = self.publisher.topic_path(self.project_id, self.topic_name)
            logger.info("PubSub client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PubSub client: {e}")
            self.publisher = None
            self.topic_path = None
    
    def _init_drive_service(self):
        """Initialize Google Drive API service with fallback authentication"""
        try:
            # First try service account credentials
            credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if credentials_path and os.path.exists(credentials_path):
                # Check if it's a service account file, OAuth client credentials, or application default credentials
                try:
                    with open(credentials_path, 'r') as f:
                        cred_data = json.load(f)
                    
                    # If it has service account fields, use service account auth
                    if 'type' in cred_data and cred_data['type'] == 'service_account':
                        logger.info("Using service account credentials")
                        credentials = service_account.Credentials.from_service_account_file(
                            credentials_path,
                            scopes=[
                                'https://www.googleapis.com/auth/drive',
                                'https://www.googleapis.com/auth/drive.readonly',
                                'https://www.googleapis.com/auth/drive.metadata.readonly',
                                'https://www.googleapis.com/auth/drive.file'
                            ]
                        )
                        self.drive_service = build('drive', 'v3', credentials=credentials)
                    # If it has OAuth client credentials format, use application default credentials
                    elif 'installed' in cred_data or 'web' in cred_data:
                        logger.info("OAuth client credentials detected, using application default credentials")
                        credentials, project = default(scopes=[
                            'https://www.googleapis.com/auth/drive',
                            'https://www.googleapis.com/auth/drive.readonly',
                            'https://www.googleapis.com/auth/drive.metadata.readonly',
                            'https://www.googleapis.com/auth/drive.file'
                        ])
                        self.drive_service = build('drive', 'v3', credentials=credentials)
                        logger.info(f"Authenticated as user for project: {project}")
                    else:
                        # It's application default credentials, use default auth
                        logger.info("Using application default credentials")
                        credentials, project = default(scopes=[
                            'https://www.googleapis.com/auth/drive',
                            'https://www.googleapis.com/auth/drive.readonly',
                            'https://www.googleapis.com/auth/drive.metadata.readonly',
                            'https://www.googleapis.com/auth/drive.file'
                        ])
                        self.drive_service = build('drive', 'v3', credentials=credentials)
                        logger.info(f"Authenticated as user for project: {project}")
                except (json.JSONDecodeError, KeyError):
                    # If we can't parse it as JSON, try application default credentials
                    logger.info("Using application default credentials")
                    credentials, project = default(scopes=[
                        'https://www.googleapis.com/auth/drive',
                        'https://www.googleapis.com/auth/drive.readonly',
                        'https://www.googleapis.com/auth/drive.metadata.readonly',
                        'https://www.googleapis.com/auth/drive.file'
                    ])
                    self.drive_service = build('drive', 'v3', credentials=credentials)
                    logger.info(f"Authenticated as user for project: {project}")
            else:
                # Fallback to user credentials (application default)
                logger.info("Using application default credentials")
                credentials, project = default(scopes=[
                    'https://www.googleapis.com/auth/drive',
                    'https://www.googleapis.com/auth/drive.readonly',
                    'https://www.googleapis.com/auth/drive.metadata.readonly',
                    'https://www.googleapis.com/auth/drive.file'
                ])
                self.drive_service = build('drive', 'v3', credentials=credentials)
                logger.info(f"Authenticated as user for project: {project}")
        except Exception as e:
            logger.error(f"Failed to initialize Drive service: {e}")
            logger.info("Drive service will not be available. Please set up authentication.")
    
    def get_supported_mime_types(self):
        """Get list of supported MIME types for scanning"""
        return [
            'application/pdf',
            'text/plain',
            'text/csv',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'application/vnd.google-apps.document',
            'application/vnd.google-apps.spreadsheet',
            'application/vnd.google-apps.presentation',
            'application/rtf',
            'text/html'
        ]
    
    def should_scan_file(self, file_metadata):
        """Determine if a file should be scanned based on its properties"""
        mime_type = file_metadata.get('mimeType', '')
        size = int(file_metadata.get('size', 0))
        name = file_metadata.get('name', '')
        
        # Check MIME type
        if mime_type not in self.get_supported_mime_types():
            return False, f"Unsupported MIME type: {mime_type}"
        
        # Check file size (limit to 10MB for DLP API)
        max_size = 10 * 1024 * 1024  # 10MB
        if size > max_size:
            return False, f"File too large: {size} bytes (max: {max_size})"
        
        # Skip system files
        if name.startswith('.') or name.startswith('~'):
            return False, "System file"
        
        return True, "File eligible for scanning"
    
    def publish_scan_request(self, file_metadata):
        """Publish a scan request to Pub/Sub"""
        try:
            if not self.publisher or not self.topic_path:
                logger.warning("PubSub client not initialized, skipping scan request")
                return None
                
            message_data = {
                'file_id': file_metadata['id'],
                'file_name': file_metadata['name'],
                'mime_type': file_metadata['mimeType'],
                'size': file_metadata.get('size', 0),
                'modified_time': file_metadata.get('modifiedTime'),
                'owner': file_metadata.get('owners', [{}])[0].get('emailAddress', 'unknown'),
                'request_timestamp': datetime.utcnow().isoformat()
            }
            
            message_json = json.dumps(message_data)
            future = self.publisher.publish(self.topic_path, message_json.encode('utf-8'))
            message_id = future.result()
            logger.info(f"Published scan request for file {file_metadata['id']}: {message_id}")
            return message_id
        except Exception as e:
            logger.error(f"Failed to publish scan request: {e}")
            return None
    
    def list_drive_files(self, query=None, max_results=100):
        """List files in Google Drive"""
        try:
            if not self.drive_service:
                return {
                    'files': [],
                    'total': 0,
                    'error': 'Drive service not initialized',
                    'message': 'Please set up Google Drive authentication to access files'
                }
            
            # Default query to exclude trashed files
            if not query:
                query = "trashed=false"
            
            results = self.drive_service.files().list(
                q=query,
                pageSize=max_results,
                fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, owners, parents)"
            ).execute()
            
            files = results.get('files', [])
            
            # Add scan eligibility information
            for file in files:
                should_scan, reason = self.should_scan_file(file)
                file['scan_eligible'] = should_scan
                file['scan_reason'] = reason
            
            return {
                'files': files,
                'total': len(files)
            }
            
        except Exception as e:
            logger.error(f"Error listing Drive files: {e}")
            return {
                'files': [],
                'total': 0,
                'error': str(e),
                'message': 'Failed to list Drive files'
            }
    
    def get_file_metadata(self, file_id):
        """Get metadata for a specific file"""
        try:
            if not self.drive_service:
                raise Exception("Drive service not initialized")
            
            file_metadata = self.drive_service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, size, modifiedTime, owners, parents, permissions"
            ).execute()
            
            return file_metadata
            
        except Exception as e:
            logger.error(f"Error getting file metadata: {e}")
            raise
    
    def setup_push_notifications(self, webhook_url):
        """Set up push notifications for Drive changes"""
        try:
            if not self.drive_service:
                raise Exception("Drive service not initialized")
            
            # Create a channel for push notifications
            channel_body = {
                'id': f'drive-monitor-{datetime.utcnow().strftime("%Y%m%d%H%M%S")}',
                'type': 'web_hook',
                'address': webhook_url,
                'expiration': str(int((datetime.utcnow().timestamp() + 86400) * 1000))  # 24 hours
            }
            
            response = self.drive_service.files().watch(
                body=channel_body
            ).execute()
            
            logger.info(f"Push notification channel created: {response['id']}")
            return response
            
        except Exception as e:
            logger.error(f"Error setting up push notifications: {e}")
            raise

# Initialize monitor instance
monitor = DriveMonitor()

@drive_bp.route('/webhook', methods=['POST'])
def drive_webhook():
    """Handle Google Drive push notifications"""
    try:
        # Verify the request is from Google
        channel_id = request.headers.get('X-Goog-Channel-ID')
        resource_id = request.headers.get('X-Goog-Resource-ID')
        resource_state = request.headers.get('X-Goog-Resource-State')
        
        logger.info(f"Received webhook: channel={channel_id}, resource={resource_id}, state={resource_state}")
        
        if resource_state in ['update', 'add']:
            # Get the changed file information
            # Note: Google Drive webhooks don't include file details, so we need to query for recent changes
            try:
                # Get recent changes (this is a simplified approach)
                changes = monitor.drive_service.changes().list(
                    pageToken='1',  # Start from beginning for demo
                    fields="changes(file(id, name, mimeType, size, modifiedTime, owners))"
                ).execute()
                
                for change in changes.get('changes', []):
                    file_metadata = change.get('file')
                    if file_metadata:
                        should_scan, reason = monitor.should_scan_file(file_metadata)
                        if should_scan:
                            monitor.publish_scan_request(file_metadata)
                        else:
                            logger.info(f"Skipping file {file_metadata['id']}: {reason}")
                
            except Exception as e:
                logger.error(f"Error processing webhook: {e}")
        
        return '', 200
        
    except Exception as e:
        logger.error(f"Error in drive_webhook: {e}")
        return jsonify({'error': str(e)}), 500

@drive_bp.route('/scan/trigger', methods=['POST'])
def trigger_scan():
    """Manually trigger a scan for specific files or all files"""
    try:
        data = request.get_json()
        file_ids = data.get('file_ids', [])
        scan_all = data.get('scan_all', False)
        query = data.get('query')
        
        scanned_files = []
        skipped_files = []
        
        if scan_all or query:
            # Scan all files or files matching query
            files_result = monitor.list_drive_files(query=query)
            
            # Check if list_drive_files returned an error
            if isinstance(files_result, dict) and 'error' in files_result:
                return jsonify({
                    'error': files_result['error'],
                    'message': files_result.get('message', 'Drive service not available')
                }), 500
            
            # Handle the new return format
            if isinstance(files_result, dict) and 'files' in files_result:
                files = files_result['files']
            else:
                files = files_result  # Backward compatibility
            
            for file_metadata in files:
                should_scan, reason = monitor.should_scan_file(file_metadata)
                if should_scan:
                    message_id = monitor.publish_scan_request(file_metadata)
                    scanned_files.append({
                        'file_id': file_metadata['id'],
                        'file_name': file_metadata['name'],
                        'message_id': message_id
                    })
                else:
                    skipped_files.append({
                        'file_id': file_metadata['id'],
                        'file_name': file_metadata['name'],
                        'reason': reason
                    })
        
        elif file_ids:
            # Scan specific files
            for file_id in file_ids:
                try:
                    file_metadata = monitor.get_file_metadata(file_id)
                    should_scan, reason = monitor.should_scan_file(file_metadata)
                    if should_scan:
                        message_id = monitor.publish_scan_request(file_metadata)
                        scanned_files.append({
                            'file_id': file_id,
                            'file_name': file_metadata['name'],
                            'message_id': message_id
                        })
                    else:
                        skipped_files.append({
                            'file_id': file_id,
                            'file_name': file_metadata['name'],
                            'reason': reason
                        })
                except Exception as e:
                    skipped_files.append({
                        'file_id': file_id,
                        'file_name': 'unknown',
                        'reason': f"Error: {str(e)}"
                    })
        
        else:
            return jsonify({'error': 'Either file_ids, scan_all=true, or query must be provided'}), 400
        
        return jsonify({
            'status': 'success',
            'scanned_files': len(scanned_files),
            'skipped_files': len(skipped_files),
            'details': {
                'scanned': scanned_files,
                'skipped': skipped_files
            }
        })
        
    except Exception as e:
        logger.error(f"Error in trigger_scan: {e}")
        return jsonify({'error': str(e)}), 500

@drive_bp.route('/scan/direct', methods=['POST'])
def direct_scan():
    """Directly scan files without using Pub/Sub"""
    try:
        data = request.get_json()
        file_ids = data.get('file_ids', [])
        scan_all = data.get('scan_all', False)
        query = data.get('query')
        
        scanned_files = []
        skipped_files = []
        
        # Import the DLP scanner
        from src.routes.dlp_scanner import scanner
        
        if scan_all or query:
            # Scan all files or files matching query
            files_result = monitor.list_drive_files(query=query)
            
            # Check if list_drive_files returned an error
            if isinstance(files_result, dict) and 'error' in files_result:
                return jsonify({
                    'error': files_result['error'],
                    'message': files_result.get('message', 'Drive service not available')
                }), 500
            
            # Handle the new return format
            if isinstance(files_result, dict) and 'files' in files_result:
                files = files_result['files']
            else:
                files = files_result  # Backward compatibility
            
            for file_metadata in files:
                should_scan, reason = monitor.should_scan_file(file_metadata)
                if should_scan:
                    try:
                        # Directly scan the file using DLP scanner
                        scan_response = scanner.download_file_content(file_metadata['id'])
                        scan_results = scanner.inspect_content(scan_response['content'], {
                            'file_id': file_metadata['id'],
                            'name': scan_response['name'],
                            'mime_type': scan_response['mime_type'],
                            'size': scan_response['size']
                        })
                        
                        # Store scan results
                        results_path = scanner.store_scan_results(scan_results, file_metadata['id'])
                        
                        scanned_files.append({
                            'file_id': file_metadata['id'],
                            'file_name': file_metadata['name'],
                            'findings_count': scan_results.get('total_findings', 0),
                            'status': 'sensitive_data_found' if scan_results.get('total_findings', 0) > 0 else 'clean',
                            'results_stored_at': results_path
                        })
                        
                        logger.info(f"Scanned file {file_metadata['name']}: {scan_results.get('total_findings', 0)} findings")
                        
                    except Exception as e:
                        logger.error(f"Error scanning file {file_metadata['id']}: {e}")
                        scanned_files.append({
                            'file_id': file_metadata['id'],
                            'file_name': file_metadata['name'],
                            'status': 'error',
                            'error': str(e)
                        })
                else:
                    skipped_files.append({
                        'file_id': file_metadata['id'],
                        'file_name': file_metadata['name'],
                        'reason': reason
                    })
        
        elif file_ids:
            # Scan specific files
            for file_id in file_ids:
                try:
                    file_metadata = monitor.get_file_metadata(file_id)
                    should_scan, reason = monitor.should_scan_file(file_metadata)
                    if should_scan:
                        # Directly scan the file using DLP scanner
                        scan_response = scanner.download_file_content(file_id)
                        scan_results = scanner.inspect_content(scan_response['content'], {
                            'file_id': file_id,
                            'name': scan_response['name'],
                            'mime_type': scan_response['mime_type'],
                            'size': scan_response['size']
                        })
                        
                        # Store scan results
                        results_path = scanner.store_scan_results(scan_results, file_id)
                        
                        scanned_files.append({
                            'file_id': file_id,
                            'file_name': file_metadata['name'],
                            'findings_count': scan_results.get('total_findings', 0),
                            'status': 'sensitive_data_found' if scan_results.get('total_findings', 0) > 0 else 'clean',
                            'results_stored_at': results_path
                        })
                        
                        logger.info(f"Scanned file {file_metadata['name']}: {scan_results.get('total_findings', 0)} findings")
                        
                    else:
                        skipped_files.append({
                            'file_id': file_id,
                            'file_name': file_metadata['name'],
                            'reason': reason
                        })
                        
                except Exception as e:
                    logger.error(f"Error scanning file {file_id}: {e}")
                    scanned_files.append({
                        'file_id': file_id,
                        'file_name': 'unknown',
                        'status': 'error',
                        'error': str(e)
                    })
        
        else:
            return jsonify({'error': 'Either file_ids, scan_all=true, or query must be provided'}), 400
        
        return jsonify({
            'status': 'success',
            'scanned_files': len(scanned_files),
            'skipped_files': len(skipped_files),
            'details': {
                'scanned': scanned_files,
                'skipped': skipped_files
            }
        })
        
    except Exception as e:
        logger.error(f"Error in direct_scan: {e}")
        return jsonify({'error': str(e)}), 500

@drive_bp.route('/files', methods=['GET'])
def list_files():
    """List Google Drive files"""
    try:
        query = request.args.get('query', 'trashed=false')
        max_results = int(request.args.get('max_results', 100))
        
        result = monitor.list_drive_files(query=query, max_results=max_results)
        
        # Check if there was an error
        if 'error' in result:
            return jsonify(result), 500
        
        files = result.get('files', [])
        
        # Add scan eligibility information and scan status
        for file_metadata in files:
            should_scan, reason = monitor.should_scan_file(file_metadata)
            file_metadata['scan_eligible'] = should_scan
            file_metadata['scan_reason'] = reason
            
            # Get scan status for this file
            try:
                from src.routes.dlp_scanner import scanner
                bucket_name = os.environ.get('SCAN_RESULTS_BUCKET', 'drive-scanner-results')
                bucket = scanner.storage_client.bucket(bucket_name)
                blobs = list(bucket.list_blobs(prefix=f"scan_results/{file_metadata['id']}_"))
                
                if blobs:
                    # File has been scanned
                    latest_blob = max(blobs, key=lambda b: b.time_created)
                    content = latest_blob.download_as_text()
                    scan_result = json.loads(content)
                    
                    file_metadata['scan_status'] = {
                        'status': 'sensitive_data_found' if scan_result.get('total_findings', 0) > 0 else 'clean',
                        'findings_count': scan_result.get('total_findings', 0),
                        'scan_timestamp': scan_result.get('scan_timestamp'),
                        'last_scan': latest_blob.updated.isoformat() if latest_blob.updated else None
                    }
                else:
                    # File has not been scanned
                    file_metadata['scan_status'] = {
                        'status': 'not_scanned',
                        'findings_count': 0,
                        'scan_timestamp': None,
                        'last_scan': None
                    }
            except Exception as e:
                logger.error(f"Error getting scan status for file {file_metadata['id']}: {e}")
                file_metadata['scan_status'] = {
                    'status': 'error',
                    'findings_count': 0,
                    'scan_timestamp': None,
                    'last_scan': None,
                    'error': str(e)
                }
        
        return jsonify({
            'files': files,
            'total': len(files)
        })
        
    except Exception as e:
        logger.error(f"Error in list_files: {e}")
        return jsonify({'error': str(e)}), 500

@drive_bp.route('/files/<file_id>', methods=['GET'])
def get_file_info(file_id):
    """Get information about a specific file"""
    try:
        file_metadata = monitor.get_file_metadata(file_id)
        should_scan, reason = monitor.should_scan_file(file_metadata)
        
        file_metadata['scan_eligible'] = should_scan
        file_metadata['scan_reason'] = reason
        
        return jsonify(file_metadata)
        
    except Exception as e:
        logger.error(f"Error in get_file_info: {e}")
        return jsonify({'error': str(e)}), 500

@drive_bp.route('/setup-notifications', methods=['POST'])
def setup_notifications():
    """Set up push notifications for Drive changes"""
    try:
        data = request.get_json()
        webhook_url = data.get('webhook_url')
        
        if not webhook_url:
            return jsonify({'error': 'webhook_url is required'}), 400
        
        response = monitor.setup_push_notifications(webhook_url)
        
        return jsonify({
            'status': 'success',
            'channel_id': response['id'],
            'resource_id': response['resourceId'],
            'expiration': response['expiration']
        })
        
    except Exception as e:
        logger.error(f"Error in setup_notifications: {e}")
        return jsonify({'error': str(e)}), 500

@drive_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Drive Monitor',
        'timestamp': datetime.utcnow().isoformat()
    })

