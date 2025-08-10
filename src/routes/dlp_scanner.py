"""
DLP Scanner routes for Google Drive Sensitive Data Scanner
"""
import os
import json
import logging
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, send_file
from google.cloud import dlp_v2, storage
from google.oauth2 import service_account
from google.auth import default
from googleapiclient.discovery import build
import tempfile
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
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
    
    def get_custom_info_types(self):
        """Get custom info types for company-specific sensitive data"""
        return [
            {
                "info_type": {
                    "name": "CUSTOM_EMPLOYEE_ID"
                },
                "likelihood": "POSSIBLE",
                "detection_rule": {
                    "hotword_rule": {
                        "hotword_regex": {
                            "pattern": r"EMP-\d{6}"
                        },
                        "proximity": {
                            "window_before": 10,
                            "window_after": 10
                        }
                    }
                }
            },
            {
                "info_type": {
                    "name": "CUSTOM_INTERNAL_REFERENCE"
                },
                "likelihood": "POSSIBLE",
                "detection_rule": {
                    "hotword_rule": {
                        "hotword_regex": {
                            "pattern": r"REF-\d{4}-\d{4}"
                        },
                        "proximity": {
                            "window_before": 10,
                            "window_after": 10
                        }
                    }
                }
            },
            {
                "info_type": {
                    "name": "CUSTOM_API_KEY"
                },
                "likelihood": "LIKELY",
                "detection_rule": {
                    "hotword_rule": {
                        "hotword_regex": {
                            "pattern": r"[a-zA-Z0-9]{32,}"
                        },
                        "proximity": {
                            "window_before": 5,
                            "window_after": 5
                        }
                    }
                }
            },
            {
                "info_type": {
                    "name": "CUSTOM_IP_ADDRESS"
                },
                "likelihood": "POSSIBLE",
                "detection_rule": {
                    "hotword_rule": {
                        "hotword_regex": {
                            "pattern": r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
                        }
                    }
                }
            },
            {
                "info_type": {
                    "name": "CUSTOM_DATABASE_CONNECTION"
                },
                "likelihood": "LIKELY",
                "detection_rule": {
                    "hotword_rule": {
                        "hotword_regex": {
                            "pattern": r"(?:jdbc|mysql|postgresql|mongodb)://[^\s]+"
                        }
                    }
                }
            }
        ]
    
    def get_dlp_config(self, include_custom_types=True, custom_patterns=None):
        """Get comprehensive DLP configuration with custom types and patterns"""
        config = {
            "inspectConfig": {
                "infoTypes": self.get_sensitive_info_types(),
                "minLikelihood": "POSSIBLE",
                "limits": {
                    "maxFindingsPerRequest": 100
                }
            }
        }
        
        # Add custom info types if requested
        if include_custom_types:
            custom_types = self.get_custom_info_types()
            
            # Add user-provided custom patterns
            if custom_patterns:
                for pattern_name, pattern_config in custom_patterns.items():
                    custom_types.append({
                        "info_type": {
                            "name": f"CUSTOM_{pattern_name.upper()}"
                        },
                        "likelihood": pattern_config.get("likelihood", "POSSIBLE"),
                        "detection_rule": {
                            "hotword_rule": {
                                "hotword_regex": {
                                    "pattern": pattern_config["pattern"]
                                },
                                "proximity": {
                                    "window_before": pattern_config.get("window_before", 10),
                                    "window_after": pattern_config.get("window_after", 10)
                                }
                            }
                        }
                    })
            
            config["inspectConfig"]["customInfoTypes"] = custom_types
        
        return config
    
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
    
    def inspect_content(self, content, file_info, custom_patterns=None, include_custom_types=True):
        """Inspect content using Google Cloud DLP API with customizable configuration"""
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
            
            # Get DLP configuration
            dlp_config = self.get_dlp_config(include_custom_types, custom_patterns)
            
            # Convert config to DLP API format
            inspect_config = {
                "info_types": [{"name": info_type["name"]} for info_type in dlp_config["inspectConfig"]["infoTypes"]],
                "min_likelihood": dlp_v2.Likelihood.POSSIBLE,
                "limits": {"max_findings_per_request": 100},
                "include_quote": True
            }
            
            # Add custom info types if enabled
            if include_custom_types and "customInfoTypes" in dlp_config["inspectConfig"]:
                # Convert custom info types to proper DLP API format
                custom_info_types = []
                for custom_type in dlp_config["inspectConfig"]["customInfoTypes"]:
                    # Ensure proper structure for DLP API
                    if "info_type" in custom_type:
                        custom_info_types.append({
                            "info_type": custom_type["info_type"],
                            "likelihood": custom_type.get("likelihood", "POSSIBLE"),
                            "detection_rule": custom_type.get("detection_rule", {})
                        })
                if custom_info_types:
                    inspect_config["custom_info_types"] = custom_info_types
            
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
                "total_findings": len(findings),
                "config_used": {
                    "include_custom_types": include_custom_types,
                    "custom_patterns_count": len(custom_patterns) if custom_patterns else 0
                }
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
            
            # Try to get the bucket, create it if it doesn't exist
            try:
                bucket = self.storage_client.bucket(bucket_name)
                bucket.reload()  # This will raise an exception if bucket doesn't exist
            except Exception:
                logger.info(f"Creating bucket: {bucket_name}")
                bucket = self.storage_client.create_bucket(bucket_name)
                logger.info(f"Bucket created successfully: {bucket_name}")
            
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

@dlp_bp.route('/status', methods=['GET'])
def get_scan_status():
    """Get scan status for all files"""
    try:
        bucket_name = os.environ.get('SCAN_RESULTS_BUCKET', 'drive-scanner-results')
        
        # Try to get the bucket, return empty results if it doesn't exist
        try:
            bucket = scanner.storage_client.bucket(bucket_name)
            bucket.reload()  # This will raise an exception if bucket doesn't exist
        except Exception:
            logger.info(f"Bucket {bucket_name} does not exist yet, returning empty results")
            return jsonify({
                'status': 'success',
                'statistics': {
                    'total_files_scanned': 0,
                    'files_with_sensitive_data': 0,
                    'clean_files': 0
                },
                'scan_results': []
            })
        
        # List all scan result blobs
        blobs = list(bucket.list_blobs(prefix="scan_results/"))
        
        scan_status = []
        for blob in blobs:
            try:
                # Extract file_id from blob name (format: scan_results/{file_id}_{timestamp}.json)
                blob_name = blob.name
                if blob_name.startswith("scan_results/") and blob_name.endswith(".json"):
                    # Extract file_id from the blob name
                    parts = blob_name.replace("scan_results/", "").replace(".json", "").split("_")
                    if len(parts) >= 2:
                        file_id = parts[0]
                        timestamp = "_".join(parts[1:])
                        
                        # Download and parse the scan result
                        content = blob.download_as_text()
                        scan_result = json.loads(content)
                        
                        scan_status.append({
                            'file_id': file_id,
                            'file_name': scan_result.get('file_info', {}).get('name', 'Unknown'),
                            'scan_timestamp': scan_result.get('scan_timestamp'),
                            'findings_count': scan_result.get('total_findings', 0),
                            'status': 'sensitive_data_found' if scan_result.get('total_findings', 0) > 0 else 'clean',
                            'results_stored_at': blob_name,
                            'last_modified': blob.updated.isoformat() if blob.updated else None
                        })
            except Exception as e:
                logger.error(f"Error processing scan result {blob.name}: {e}")
                continue
        
        # Sort by scan timestamp (most recent first)
        scan_status.sort(key=lambda x: x.get('scan_timestamp', ''), reverse=True)
        
        # Calculate statistics
        total_scanned = len(scan_status)
        files_with_findings = len([s for s in scan_status if s['findings_count'] > 0])
        clean_files = total_scanned - files_with_findings
        
        return jsonify({
            'status': 'success',
            'statistics': {
                'total_files_scanned': total_scanned,
                'files_with_sensitive_data': files_with_findings,
                'clean_files': clean_files
            },
            'scan_results': scan_status
        })
        
    except Exception as e:
        logger.error(f"Error getting scan status: {e}")
        return jsonify({'error': str(e)}), 500

@dlp_bp.route('/status/<file_id>', methods=['GET'])
def get_file_scan_status(file_id):
    """Get scan status for a specific file"""
    try:
        bucket_name = os.environ.get('SCAN_RESULTS_BUCKET', 'drive-scanner-results')
        bucket = scanner.storage_client.bucket(bucket_name)
        
        # List blobs with the file_id prefix
        blobs = list(bucket.list_blobs(prefix=f"scan_results/{file_id}_"))
        
        if not blobs:
            return jsonify({
                'file_id': file_id,
                'status': 'not_scanned',
                'message': 'This file has not been scanned yet'
            })
        
        # Get the most recent result
        latest_blob = max(blobs, key=lambda b: b.time_created)
        content = latest_blob.download_as_text()
        scan_result = json.loads(content)
        
        return jsonify({
            'file_id': file_id,
            'file_name': scan_result.get('file_info', {}).get('name', 'Unknown'),
            'scan_timestamp': scan_result.get('scan_timestamp'),
            'findings_count': scan_result.get('total_findings', 0),
            'status': 'sensitive_data_found' if scan_result.get('total_findings', 0) > 0 else 'clean',
            'results_stored_at': latest_blob.name,
            'last_modified': latest_blob.updated.isoformat() if latest_blob.updated else None,
            'findings': scan_result.get('findings', []) if scan_result.get('total_findings', 0) > 0 else []
        })
        
    except Exception as e:
        logger.error(f"Error getting file scan status: {e}")
        return jsonify({'error': str(e)}), 500

@dlp_bp.route('/dashboard', methods=['GET'])
def get_scan_dashboard():
    """Get comprehensive scan dashboard with statistics and recent activity"""
    try:
        bucket_name = os.environ.get('SCAN_RESULTS_BUCKET', 'drive-scanner-results')
        
        # Try to get the bucket, return empty dashboard if it doesn't exist
        try:
            bucket = scanner.storage_client.bucket(bucket_name)
            bucket.reload()  # This will raise an exception if bucket doesn't exist
        except Exception:
            logger.info(f"Bucket {bucket_name} does not exist yet, returning empty dashboard")
            return jsonify({
                'status': 'success',
                'dashboard': {
                    'overview': {
                        'total_files_scanned': 0,
                        'files_with_sensitive_data': 0,
                        'clean_files': 0,
                        'scan_success_rate': 0
                    },
                    'recent_activity': {
                        'scans_last_7_days': 0,
                        'recent_scans': []
                    },
                    'top_concerns': {
                        'files_with_most_findings': []
                    },
                    'scan_trends': {
                        'total_findings': 0,
                        'average_findings_per_file': 0
                    }
                }
            })
        
        # List all scan result blobs
        blobs = list(bucket.list_blobs(prefix="scan_results/"))
        
        scan_data = []
        for blob in blobs:
            try:
                content = blob.download_as_text()
                scan_result = json.loads(content)
                
                scan_data.append({
                    'file_id': scan_result.get('file_info', {}).get('file_id'),
                    'file_name': scan_result.get('file_info', {}).get('name', 'Unknown'),
                    'scan_timestamp': scan_result.get('scan_timestamp'),
                    'findings_count': scan_result.get('total_findings', 0),
                    'status': 'sensitive_data_found' if scan_result.get('total_findings', 0) > 0 else 'clean',
                    'last_modified': blob.updated.isoformat() if blob.updated else None
                })
            except Exception as e:
                logger.error(f"Error processing scan result {blob.name}: {e}")
                continue
        
        # Calculate comprehensive statistics
        total_scanned = len(scan_data)
        files_with_findings = len([s for s in scan_data if s['findings_count'] > 0])
        clean_files = total_scanned - files_with_findings
        
        # Get recent activity (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_scans = [s for s in scan_data if s.get('scan_timestamp') and 
                       datetime.fromisoformat(s['scan_timestamp'].replace('Z', '+00:00')) > week_ago]
        
        # Get files with most findings
        files_with_most_findings = sorted(scan_data, key=lambda x: x['findings_count'], reverse=True)[:5]
        
        # Get recent scans (last 10)
        recent_activity = sorted(scan_data, key=lambda x: x.get('scan_timestamp', ''), reverse=True)[:10]
        
        return jsonify({
            'status': 'success',
            'dashboard': {
                'overview': {
                    'total_files_scanned': total_scanned,
                    'files_with_sensitive_data': files_with_findings,
                    'clean_files': clean_files,
                    'scan_success_rate': round((total_scanned - files_with_findings) / total_scanned * 100, 2) if total_scanned > 0 else 0
                },
                'recent_activity': {
                    'scans_last_7_days': len(recent_scans),
                    'recent_scans': recent_activity
                },
                'top_concerns': {
                    'files_with_most_findings': files_with_most_findings
                },
                'scan_trends': {
                    'total_findings': sum(s['findings_count'] for s in scan_data),
                    'average_findings_per_file': round(sum(s['findings_count'] for s in scan_data) / total_scanned, 2) if total_scanned > 0 else 0
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting scan dashboard: {e}")
        return jsonify({'error': str(e)}), 500

@dlp_bp.route('/report/generate', methods=['POST'])
def generate_scan_report():
    """Generate a comprehensive PDF scan report"""
    try:
        data = request.get_json() or {}
        report_type = data.get('type', 'comprehensive')  # comprehensive, summary, detailed
        include_findings = data.get('include_findings', True)
        
        # Get scan data directly from storage
        try:
            bucket_name = os.environ.get('SCAN_RESULTS_BUCKET', 'drive-scanner-results')
            bucket = scanner.storage_client.bucket(bucket_name)
            
            # Get all scan result files
            blobs = bucket.list_blobs(prefix='scan_results/')
            scan_data = []
            
            for blob in blobs:
                if blob.name.endswith('.json'):
                    try:
                        content = blob.download_as_text()
                        scan_result = json.loads(content)
                        scan_data.append(scan_result)
                    except Exception as e:
                        logger.warning(f"Error reading scan result {blob.name}: {e}")
                        continue
            
            if not scan_data:
                return jsonify({'error': 'No scan data available'}), 404
            
            # Calculate statistics
            total_files = len(scan_data)
            files_with_findings = len([s for s in scan_data if s.get('total_findings', 0) > 0])
            clean_files = total_files - files_with_findings
            total_findings = sum(s.get('total_findings', 0) for s in scan_data)
            
            # Sort by scan timestamp
            scan_data.sort(key=lambda x: x.get('scan_timestamp', ''), reverse=True)
            
        except Exception as e:
            logger.error(f"Error retrieving scan data: {e}")
            return jsonify({'error': 'Unable to retrieve scan data'}), 500
        
        # Create PDF report
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
        story = []
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.darkblue
        )
        normal_style = styles['Normal']
        
        # Title page
        story.append(Paragraph("Google Drive Security Scan Report", title_style))
        story.append(Spacer(1, 20))
        story.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", normal_style))
        story.append(Spacer(1, 30))
        
        # Executive Summary
        story.append(Paragraph("Executive Summary", heading_style))
        
        summary_data = [
            ['Metric', 'Value'],
            ['Total Files Scanned', str(total_files)],
            ['Files with Sensitive Data', str(files_with_findings)],
            ['Clean Files', str(clean_files)],
            ['Scan Success Rate', f"{(total_files - len([s for s in scan_data if s.get('error')])) / total_files * 100:.1f}%" if total_files > 0 else "0.0%"],
            ['Total Findings', str(total_findings)]
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 1.5*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        # Risk Assessment
        story.append(Paragraph("Risk Assessment", heading_style))
        risk_percentage = (files_with_findings / total_files * 100) if total_files > 0 else 0
        
        if risk_percentage > 50:
            risk_level = "HIGH"
            risk_color = colors.red
        elif risk_percentage > 25:
            risk_level = "MEDIUM"
            risk_color = colors.orange
        else:
            risk_level = "LOW"
            risk_color = colors.green
        
        risk_data = [
            ['Risk Level', 'Percentage', 'Description'],
            [risk_level, f"{risk_percentage:.1f}%", f"{files_with_findings} out of {total_files} files contain sensitive data"]
        ]
        
        risk_table = Table(risk_data, colWidths=[1.5*inch, 1*inch, 3*inch])
        risk_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (0, 1), risk_color),
            ('TEXTCOLOR', (0, 1), (0, 1), colors.white),
            ('FONTNAME', (0, 1), (0, 1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(risk_table)
        story.append(Spacer(1, 20))
        
        # Top Concerns
        story.append(Paragraph("Top Security Concerns", heading_style))
        
        # Get top files with most findings
        files_with_findings = [s for s in scan_data if s.get('total_findings', 0) > 0]
        files_with_findings.sort(key=lambda x: x.get('total_findings', 0), reverse=True)
        
        if files_with_findings:
            concerns_data = [['File Name', 'Findings', 'Scanned']]
            for concern in files_with_findings[:10]:  # Top 10
                scan_date = concern.get('scan_timestamp', '').split('T')[0] if concern.get('scan_timestamp') else 'Unknown'
                file_name = concern.get('file_info', {}).get('name', 'Unknown')
                concerns_data.append([
                    file_name[:40] + '...' if len(file_name) > 40 else file_name,
                    str(concern.get('total_findings', 0)),
                    scan_date
                ])
            
            concerns_table = Table(concerns_data, colWidths=[3*inch, 1*inch, 1.5*inch])
            concerns_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9)
            ]))
            story.append(concerns_table)
        else:
            story.append(Paragraph("No high-risk files identified.", normal_style))
        
        story.append(Spacer(1, 20))
        
        # Recent Activity
        story.append(Paragraph("Recent Scan Activity", heading_style))
        
        if scan_data:
            activity_data = [['File Name', 'Status', 'Findings', 'Scanned']]
            for activity in scan_data[:15]:  # Recent 15
                status_icon = "⚠️" if activity.get('total_findings', 0) > 0 else "✅"
                status_text = "sensitive_data_found" if activity.get('total_findings', 0) > 0 else "clean"
                scan_date = activity.get('scan_timestamp', '').split('T')[0] if activity.get('scan_timestamp') else 'Unknown'
                file_name = activity.get('file_info', {}).get('name', 'Unknown')
                activity_data.append([
                    file_name[:35] + '...' if len(file_name) > 35 else file_name,
                    f"{status_icon} {status_text}",
                    str(activity.get('total_findings', 0)),
                    scan_date
                ])
            
            activity_table = Table(activity_data, colWidths=[2.5*inch, 1.5*inch, 1*inch, 1*inch])
            activity_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 8)
            ]))
            story.append(activity_table)
        else:
            story.append(Paragraph("No recent scan activity.", normal_style))
        
        story.append(Spacer(1, 20))
        
        # Recommendations
        story.append(Paragraph("Security Recommendations", heading_style))
        recommendations = []
        
        if risk_percentage > 50:
            recommendations.append("🔴 **HIGH PRIORITY**: Implement immediate data protection measures")
            recommendations.append("• Review and secure files with sensitive data")
            recommendations.append("• Implement access controls and encryption")
            recommendations.append("• Conduct security awareness training")
        elif risk_percentage > 25:
            recommendations.append("🟡 **MEDIUM PRIORITY**: Enhance security posture")
            recommendations.append("• Review files with sensitive data")
            recommendations.append("• Implement data classification")
            recommendations.append("• Consider encryption for sensitive files")
        else:
            recommendations.append("🟢 **LOW RISK**: Maintain current security practices")
            recommendations.append("• Continue regular security monitoring")
            recommendations.append("• Implement preventive measures")
            recommendations.append("• Regular security assessments")
        
        recommendations.append("")
        recommendations.append("**General Recommendations:**")
        recommendations.append("• Regular security scans and monitoring")
        recommendations.append("• Implement data loss prevention (DLP) policies")
        recommendations.append("• Employee security training and awareness")
        recommendations.append("• Regular backup and disaster recovery planning")
        
        for rec in recommendations:
            story.append(Paragraph(rec, normal_style))
        
        # Build PDF
        doc.build(story)
        pdf_buffer.seek(0)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"drive_security_scan_report_{timestamp}.pdf"
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        logger.error(f"Error generating scan report: {e}")
        return jsonify({'error': f'Failed to generate report: {str(e)}'}), 500

@dlp_bp.route('/config', methods=['GET'])
def get_dlp_config():
    """Get current DLP configuration"""
    try:
        config = scanner.get_dlp_config()
        return jsonify({
            'status': 'success',
            'config': config
        })
    except Exception as e:
        logger.error(f"Error getting DLP config: {e}")
        return jsonify({'error': str(e)}), 500

@dlp_bp.route('/config/custom-patterns', methods=['POST'])
def add_custom_pattern():
    """Add a custom detection pattern"""
    try:
        data = request.get_json()
        pattern_name = data.get('name')
        pattern = data.get('pattern')
        likelihood = data.get('likelihood', 'POSSIBLE')
        window_before = data.get('window_before', 10)
        window_after = data.get('window_after', 10)
        
        if not pattern_name or not pattern:
            return jsonify({'error': 'Pattern name and pattern are required'}), 400
        
        # Validate likelihood
        valid_likelihoods = ['VERY_UNLIKELY', 'UNLIKELY', 'POSSIBLE', 'LIKELY', 'VERY_LIKELY']
        if likelihood not in valid_likelihoods:
            return jsonify({'error': f'Invalid likelihood. Must be one of: {valid_likelihoods}'}), 400
        
        # Test the pattern
        try:
            import re
            re.compile(pattern)
        except re.error as e:
            return jsonify({'error': f'Invalid regex pattern: {str(e)}'}), 400
        
        # Store the custom pattern (in a real app, you'd store this in a database)
        custom_patterns = {
            pattern_name: {
                'pattern': pattern,
                'likelihood': likelihood,
                'window_before': window_before,
                'window_after': window_after
            }
        }
        
        return jsonify({
            'status': 'success',
            'message': f'Custom pattern "{pattern_name}" added successfully',
            'pattern': custom_patterns[pattern_name]
        })
        
    except Exception as e:
        logger.error(f"Error adding custom pattern: {e}")
        return jsonify({'error': str(e)}), 500

@dlp_bp.route('/config/info-types', methods=['GET'])
def get_available_info_types():
    """Get list of available info types"""
    try:
        # Standard Google DLP info types
        standard_types = [
            "PERSON_NAME", "EMAIL_ADDRESS", "PHONE_NUMBER", "US_SOCIAL_SECURITY_NUMBER",
            "CREDIT_CARD_NUMBER", "US_DRIVERS_LICENSE_NUMBER", "US_PASSPORT", "DATE_OF_BIRTH",
            "MEDICAL_RECORD_NUMBER", "US_BANK_ROUTING_MICR", "IBAN_CODE", "SWIFT_CODE",
            "US_INDIVIDUAL_TAXPAYER_IDENTIFICATION_NUMBER", "US_EMPLOYER_IDENTIFICATION_NUMBER",
            "US_ADDRESS", "US_TOLL_FREE_PHONE_NUMBER", "US_PHONE_NUMBER", "US_DRIVERS_LICENSE",
            "US_PASSPORT_NUMBER", "US_SSN", "US_CPT_CODE", "US_HCPCS_CODE", "US_ICD9_CODE",
            "US_ICD10_CODE", "US_NPI", "US_DEA_NUMBER", "US_NATIONAL_DRUG_CODE",
            "US_MEDICARE_BENEFICIARY_IDENTIFIER", "US_NATIONAL_PROVIDER_IDENTIFIER",
            "US_CPT_CODE", "US_HCPCS_CODE", "US_ICD9_CODE", "US_ICD10_CODE"
        ]
        
        # Custom info types
        custom_types = [
            "CUSTOM_EMPLOYEE_ID", "CUSTOM_INTERNAL_REFERENCE", "CUSTOM_API_KEY",
            "CUSTOM_IP_ADDRESS", "CUSTOM_DATABASE_CONNECTION"
        ]
        
        return jsonify({
            'status': 'success',
            'standard_types': standard_types,
            'custom_types': custom_types,
            'total_types': len(standard_types) + len(custom_types)
        })
        
    except Exception as e:
        logger.error(f"Error getting info types: {e}")
        return jsonify({'error': str(e)}), 500

@dlp_bp.route('/config/sensitivity', methods=['POST'])
def update_sensitivity_level():
    """Update DLP sensitivity level"""
    try:
        data = request.get_json()
        min_likelihood = data.get('min_likelihood', 'POSSIBLE')
        
        valid_levels = ['VERY_UNLIKELY', 'UNLIKELY', 'POSSIBLE', 'LIKELY', 'VERY_LIKELY']
        if min_likelihood not in valid_levels:
            return jsonify({'error': f'Invalid sensitivity level. Must be one of: {valid_levels}'}), 400
        
        # In a real app, you'd store this in a database
        # For now, we'll return the updated config
        config = scanner.get_dlp_config()
        config['inspectConfig']['minLikelihood'] = min_likelihood
        
        return jsonify({
            'status': 'success',
            'message': f'Sensitivity level updated to: {min_likelihood}',
            'config': config
        })
        
    except Exception as e:
        logger.error(f"Error updating sensitivity level: {e}")
        return jsonify({'error': str(e)}), 500

@dlp_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'DLP Scanner',
        'timestamp': datetime.utcnow().isoformat()
    })

