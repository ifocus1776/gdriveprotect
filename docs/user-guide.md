# User Guide and Setup Instructions
## Google Drive Sensitive Data Scanner (GDriveProtect)

**Version:** 1.0  
**Last Updated:** January 2025  
**Audience:** System Administrators, Security Teams, Compliance Officers

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Prerequisites](#2-prerequisites)
3. [Installation and Setup](#3-installation-and-setup)
4. [Configuration](#4-configuration)
5. [Using the Application](#5-using-the-application)
6. [API Reference](#6-api-reference)
7. [Monitoring and Maintenance](#7-monitoring-and-maintenance)
8. [Troubleshooting](#8-troubleshooting)
9. [Best Practices](#9-best-practices)
10. [Support and Resources](#10-support-and-resources)

---

## 1. Introduction

Welcome to Google Drive Sensitive Data Scanner (GDriveProtect), a comprehensive solution for automatically detecting and protecting sensitive data in your Google Drive environment. This user guide provides step-by-step instructions for installing, configuring, and using GDriveProtect to enhance your organization's data security and compliance posture.

### 1.1 What is GDriveProtect?

GDriveProtect is a cloud-native application that leverages Google Cloud Platform's Data Loss Prevention (DLP) API to automatically scan Google Drive files for sensitive information such as:

- **Personal Identifiable Information (PII)**: Names, email addresses, phone numbers
- **Government Identifiers**: Social Security Numbers, driver's license numbers, passport numbers
- **Financial Information**: Credit card numbers, bank account numbers, routing numbers
- **Healthcare Data**: Medical record numbers, dates of birth
- **Custom Patterns**: Organization-specific sensitive data patterns

When sensitive data is detected, GDriveProtect can automatically move files to a secure, encrypted vault with customer-managed encryption keys and comprehensive audit logging.

### 1.2 Key Benefits

- **Automated Discovery**: Continuously scan Google Drive for sensitive data without manual intervention
- **Regulatory Compliance**: Support for GDPR, HIPAA, and other data protection regulations
- **Secure Storage**: Encrypted vault storage with customer-managed keys
- **Real-time Monitoring**: Immediate detection of new or modified files containing sensitive data
- **Comprehensive Reporting**: Detailed analytics and compliance reports
- **API Integration**: RESTful API for integration with existing security and compliance systems

### 1.3 Architecture Overview

GDriveProtect follows a serverless, event-driven architecture that includes:

- **Drive Monitor**: Monitors Google Drive for file changes and triggers scans
- **DLP Scanner**: Analyzes file content using Google Cloud DLP API
- **Vault Manager**: Securely stores sensitive documents with encryption
- **Web Dashboard**: User interface for monitoring and management
- **RESTful API**: Programmatic access to all functionality

## 2. Prerequisites

Before installing GDriveProtect, ensure you have the following prerequisites in place:

### 2.1 Google Cloud Platform Requirements

**Google Cloud Project**: You need an active Google Cloud Platform project with billing enabled. The project should have sufficient quotas for the services you plan to use.

**Required APIs**: The following Google Cloud APIs must be enabled in your project:
- Google Drive API
- Cloud Data Loss Prevention (DLP) API
- Cloud Storage API
- Cloud Key Management Service (KMS) API
- Cloud Pub/Sub API
- Cloud IAM API
- Cloud Logging API
- Cloud Monitoring API

**Service Account**: Create a service account with the following roles:
- DLP User (`roles/dlp.user`)
- Storage Admin (`roles/storage.admin`)
- Cloud KMS CryptoKey Encrypter/Decrypter (`roles/cloudkms.cryptoKeyEncrypterDecrypter`)
- Pub/Sub Editor (`roles/pubsub.editor`)
- Logging Writer (`roles/logging.logWriter`)
- Monitoring Metric Writer (`roles/monitoring.metricWriter`)

### 2.2 Google Workspace Requirements

**Google Workspace Admin Access**: You need Google Workspace administrator privileges to:
- Enable the Google Drive API for your domain
- Configure OAuth consent and scopes
- Set up domain-wide delegation for the service account

**Drive API Scopes**: The following OAuth scopes are required:
- `https://www.googleapis.com/auth/drive.readonly`
- `https://www.googleapis.com/auth/drive.metadata.readonly`

### 2.3 Technical Requirements

**Python Environment**: Python 3.11 or higher with pip package manager
**Network Access**: Outbound HTTPS access to Google Cloud APIs
**Storage Requirements**: Sufficient Cloud Storage quota for scan results and vault storage
**Compute Resources**: Adequate compute quotas for Cloud Functions or Cloud Run instances

### 2.4 Security Requirements

**Encryption Keys**: Customer-managed encryption keys (CMEK) through Cloud KMS for enhanced security
**Network Security**: VPC networks and firewall rules for network isolation
**Access Controls**: IAM policies implementing least-privilege access principles
**Audit Logging**: Cloud Audit Logs enabled for all relevant services

## 3. Installation and Setup

### 3.1 Environment Preparation

**Step 1: Clone the Repository**
```bash
git clone https://github.com/ifocus1776/gdriveprotect.git
cd gdriveprotect
```

**Step 2: Set Up Python Environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Step 3: Configure Google Cloud SDK**
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud auth application-default login
```

### 3.2 Google Cloud Setup

**Step 1: Enable Required APIs**
```bash
gcloud services enable drive.googleapis.com
gcloud services enable dlp.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable cloudkms.googleapis.com
gcloud services enable pubsub.googleapis.com
gcloud services enable iam.googleapis.com
gcloud services enable logging.googleapis.com
gcloud services enable monitoring.googleapis.com
```

**Step 2: Create Service Account**
```bash
gcloud iam service-accounts create drive-scanner \
    --display-name="Drive Scanner Service Account" \
    --description="Service account for GDriveProtect application"
```

**Step 3: Grant Required Permissions**
```bash
PROJECT_ID=$(gcloud config get-value project)
SERVICE_ACCOUNT="drive-scanner@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/dlp.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/cloudkms.cryptoKeyEncrypterDecrypter"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/pubsub.editor"
```

**Step 4: Create Service Account Key**
```bash
gcloud iam service-accounts keys create credentials.json \
    --iam-account=$SERVICE_ACCOUNT
```

### 3.3 Storage Setup

**Step 1: Create Storage Buckets**
```bash
# Create bucket for scan results
gsutil mb -p $PROJECT_ID -c STANDARD -l US gs://${PROJECT_ID}-scan-results

# Create bucket for secure vault
gsutil mb -p $PROJECT_ID -c STANDARD -l US gs://${PROJECT_ID}-vault

# Enable uniform bucket-level access for security
gsutil uniformbucketlevelaccess set on gs://${PROJECT_ID}-scan-results
gsutil uniformbucketlevelaccess set on gs://${PROJECT_ID}-vault
```

**Step 2: Configure Bucket Permissions**
```bash
# Grant service account access to buckets
gsutil iam ch serviceAccount:${SERVICE_ACCOUNT}:objectAdmin gs://${PROJECT_ID}-scan-results
gsutil iam ch serviceAccount:${SERVICE_ACCOUNT}:objectAdmin gs://${PROJECT_ID}-vault
```

### 3.4 Encryption Setup (Optional but Recommended)

**Step 1: Create KMS Key Ring and Key**
```bash
# Create key ring
gcloud kms keyrings create drive-scanner-keys \
    --location=global

# Create encryption key
gcloud kms keys create vault-encryption-key \
    --location=global \
    --keyring=drive-scanner-keys \
    --purpose=encryption
```

**Step 2: Grant Service Account Access to KMS Key**
```bash
gcloud kms keys add-iam-policy-binding vault-encryption-key \
    --location=global \
    --keyring=drive-scanner-keys \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/cloudkms.cryptoKeyEncrypterDecrypter"
```

### 3.5 Pub/Sub Setup

**Step 1: Create Pub/Sub Topics and Subscriptions**
```bash
# Create topic for scan requests
gcloud pubsub topics create drive-scan-requests

# Create subscription for scan processing
gcloud pubsub subscriptions create drive-scan-processor \
    --topic=drive-scan-requests

# Grant service account access
gcloud pubsub topics add-iam-policy-binding drive-scan-requests \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/pubsub.publisher"

gcloud pubsub subscriptions add-iam-policy-binding drive-scan-processor \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/pubsub.subscriber"
```

## 4. Configuration

### 4.1 Environment Variables

Create a `.env` file in the project root with the following configuration:

```bash
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=./credentials.json

# Storage Configuration
SCAN_RESULTS_BUCKET=your-project-id-scan-results
VAULT_BUCKET=your-project-id-vault

# KMS Configuration (optional)
KMS_KEY_NAME=projects/your-project-id/locations/global/keyRings/drive-scanner-keys/cryptoKeys/vault-encryption-key

# Pub/Sub Configuration
SCAN_REQUEST_TOPIC=drive-scan-requests
SCAN_SUBSCRIPTION=drive-scan-processor

# Application Configuration
FLASK_ENV=production
FLASK_DEBUG=false
SECRET_KEY=your-secret-key-here

# Logging Configuration
LOG_LEVEL=INFO
```

### 4.2 Google Workspace Configuration

**Step 1: Configure OAuth Consent Screen**
1. Go to the Google Cloud Console
2. Navigate to APIs & Services > OAuth consent screen
3. Configure the consent screen with your organization details
4. Add the required scopes:
   - `https://www.googleapis.com/auth/drive.readonly`
   - `https://www.googleapis.com/auth/drive.metadata.readonly`

**Step 2: Enable Domain-Wide Delegation**
1. Go to the Google Workspace Admin Console
2. Navigate to Security > API Controls > Domain-wide Delegation
3. Add the service account client ID with the required scopes
4. Authorize the service account for domain-wide delegation

### 4.3 Application Configuration

**Step 1: Configure DLP Detection Rules**

Edit the DLP configuration in `src/routes/dlp_scanner.py` to customize the types of sensitive data to detect:

```python
def get_sensitive_info_types(self):
    """Customize the list of infoTypes to scan for"""
    return [
        {"name": "PERSON_NAME"},
        {"name": "EMAIL_ADDRESS"},
        {"name": "PHONE_NUMBER"},
        {"name": "US_SOCIAL_SECURITY_NUMBER"},
        {"name": "CREDIT_CARD_NUMBER"},
        {"name": "US_DRIVERS_LICENSE_NUMBER"},
        # Add custom infoTypes as needed
    ]
```

**Step 2: Configure File Type Filters**

Customize the supported file types in `src/routes/drive_monitor.py`:

```python
def get_supported_mime_types(self):
    """Customize supported MIME types for scanning"""
    return [
        'application/pdf',
        'text/plain',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        # Add additional MIME types as needed
    ]
```

## 5. Using the Application

### 5.1 Starting the Application

**Development Mode**
```bash
source venv/bin/activate
python src/main.py
```

The application will be available at `http://localhost:5000`

**Production Deployment**
For production deployment, use a WSGI server such as Gunicorn:
```bash
pip install gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 4 src.main:app
```

### 5.2 Web Dashboard

The web dashboard provides a user-friendly interface for monitoring and managing GDriveProtect:

**Dashboard Features:**
- System health monitoring
- Quick action buttons for common tasks
- Real-time status indicators
- Vault statistics and analytics
- File scanning controls

**Accessing the Dashboard:**
1. Open your web browser
2. Navigate to the application URL
3. Use the dashboard to monitor system status and trigger scans

### 5.3 Scanning Google Drive Files

**Manual Scan Trigger:**
Use the web dashboard or API to trigger manual scans:

```bash
# Scan all eligible files
curl -X POST http://localhost:5000/api/drive/scan/trigger \
  -H "Content-Type: application/json" \
  -d '{"scan_all": true}'

# Scan specific files
curl -X POST http://localhost:5000/api/drive/scan/trigger \
  -H "Content-Type: application/json" \
  -d '{"file_ids": ["file_id_1", "file_id_2"]}'
```

**Automated Scanning:**
Set up automated scanning using Google Drive push notifications:

```bash
# Set up push notifications
curl -X POST http://localhost:5000/api/drive/setup-notifications \
  -H "Content-Type: application/json" \
  -d '{"webhook_url": "https://your-domain.com/api/drive/webhook"}'
```

### 5.4 Managing the Secure Vault

**Viewing Vault Contents:**
```bash
# List documents in vault
curl http://localhost:5000/api/vault/list

# Get vault statistics
curl http://localhost:5000/api/vault/statistics
```

**Retrieving Documents:**
```bash
# Get document metadata
curl http://localhost:5000/api/vault/retrieve/vault_path

# Download document
curl "http://localhost:5000/api/vault/retrieve/vault_path?download=true" \
  -o downloaded_document.pdf
```

### 5.5 Monitoring and Alerts

**Health Checks:**
Regular health checks ensure all components are functioning properly:

```bash
# Check DLP scanner health
curl http://localhost:5000/api/dlp/health

# Check drive monitor health
curl http://localhost:5000/api/drive/health

# Check vault manager health
curl http://localhost:5000/api/vault/health
```

**Log Monitoring:**
Monitor application logs for security events and system status:

```bash
# View application logs
gcloud logging read "resource.type=gce_instance AND logName=projects/YOUR_PROJECT/logs/gdriveprotect"
```

## 6. API Reference

### 6.1 Authentication

All API requests require proper authentication. Use service account credentials or OAuth tokens for authentication.

**Service Account Authentication:**
```python
from google.oauth2 import service_account
import requests

credentials = service_account.Credentials.from_service_account_file(
    'credentials.json'
)
# Use credentials for API requests
```

### 6.2 DLP Scanner API

**Scan Single File:**
```http
POST /api/dlp/scan
Content-Type: application/json

{
  "file_id": "google_drive_file_id"
}
```

**Batch Scan Files:**
```http
POST /api/dlp/scan/batch
Content-Type: application/json

{
  "file_ids": ["file_id_1", "file_id_2", "file_id_3"]
}
```

**Get Scan Results:**
```http
GET /api/dlp/results/{file_id}
```

### 6.3 Drive Monitor API

**List Drive Files:**
```http
GET /api/drive/files?query=trashed=false&max_results=100
```

**Get File Information:**
```http
GET /api/drive/files/{file_id}
```

**Trigger Manual Scan:**
```http
POST /api/drive/scan/trigger
Content-Type: application/json

{
  "scan_all": true,
  "query": "mimeType='application/pdf'"
}
```

### 6.4 Vault Manager API

**Store Document:**
```http
POST /api/vault/store
Content-Type: application/json

{
  "file_id": "original_file_id",
  "file_name": "document.pdf",
  "content": "base64_encoded_content",
  "metadata": {
    "classification": "confidential",
    "retention_period": "7_years"
  }
}
```

**List Vault Documents:**
```http
GET /api/vault/list?limit=50&prefix=documents/
```

**Delete Document:**
```http
DELETE /api/vault/delete/{vault_path}
```

## 7. Monitoring and Maintenance

### 7.1 System Monitoring

**Performance Metrics:**
Monitor key performance indicators:
- Scan processing time
- API response times
- Error rates
- Storage usage
- Network throughput

**Google Cloud Monitoring:**
Set up monitoring dashboards and alerts:

```bash
# Create monitoring policy for high error rates
gcloud alpha monitoring policies create --policy-from-file=monitoring-policy.yaml
```

### 7.2 Log Management

**Centralized Logging:**
All application logs are sent to Google Cloud Logging for centralized management:

```python
import logging
from google.cloud import logging as cloud_logging

# Configure Cloud Logging
client = cloud_logging.Client()
client.setup_logging()

# Use standard Python logging
logging.info("Application started successfully")
```

**Log Analysis:**
Use Cloud Logging queries to analyze application behavior:

```sql
-- Find all scan operations in the last 24 hours
resource.type="gce_instance"
logName="projects/YOUR_PROJECT/logs/gdriveprotect"
jsonPayload.operation="scan"
timestamp >= "2025-01-01T00:00:00Z"
```

### 7.3 Backup and Recovery

**Data Backup:**
Implement regular backups of critical data:

```bash
# Backup vault contents
gsutil -m cp -r gs://your-vault-bucket gs://your-backup-bucket/vault-backup-$(date +%Y%m%d)

# Backup scan results
gsutil -m cp -r gs://your-scan-results-bucket gs://your-backup-bucket/results-backup-$(date +%Y%m%d)
```

**Disaster Recovery:**
Maintain disaster recovery procedures:
1. Document recovery time objectives (RTO) and recovery point objectives (RPO)
2. Test recovery procedures regularly
3. Maintain offsite backups
4. Document emergency contact procedures

## 8. Troubleshooting

### 8.1 Common Issues

**Authentication Errors:**
```
Error: google.auth.exceptions.DefaultCredentialsError
```
Solution: Ensure service account credentials are properly configured and accessible.

**Permission Denied Errors:**
```
Error: 403 Forbidden - Insufficient permissions
```
Solution: Verify that the service account has all required IAM roles and permissions.

**API Quota Exceeded:**
```
Error: 429 Too Many Requests - Quota exceeded
```
Solution: Check API quotas in Google Cloud Console and request increases if needed.

**File Not Found Errors:**
```
Error: 404 Not Found - File not found in Google Drive
```
Solution: Verify that the file exists and the service account has access to it.

### 8.2 Debugging Steps

**Step 1: Check Service Health**
```bash
# Verify all services are healthy
curl http://localhost:5000/api/dlp/health
curl http://localhost:5000/api/drive/health
curl http://localhost:5000/api/vault/health
```

**Step 2: Review Logs**
```bash
# Check application logs
tail -f logs/application.log

# Check Google Cloud logs
gcloud logging read "resource.type=gce_instance" --limit=50
```

**Step 3: Verify Configuration**
```bash
# Check environment variables
env | grep GOOGLE_

# Verify service account permissions
gcloud projects get-iam-policy YOUR_PROJECT_ID
```

**Step 4: Test API Connectivity**
```bash
# Test Google Drive API access
curl -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  "https://www.googleapis.com/drive/v3/files"

# Test DLP API access
curl -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  "https://dlp.googleapis.com/v2/projects/YOUR_PROJECT_ID/inspectTemplates"
```

### 8.3 Performance Optimization

**Scan Performance:**
- Implement parallel processing for batch scans
- Use appropriate file size limits
- Optimize DLP inspection configurations
- Monitor and adjust API quotas

**Storage Optimization:**
- Implement lifecycle policies for old scan results
- Use appropriate storage classes for different data types
- Monitor storage costs and usage patterns
- Implement data compression where appropriate

**Network Optimization:**
- Use regional resources to minimize latency
- Implement caching for frequently accessed data
- Optimize API request patterns
- Monitor network usage and costs

## 9. Best Practices

### 9.1 Security Best Practices

**Access Control:**
- Implement least-privilege access principles
- Use service accounts for automated processes
- Regularly review and audit access permissions
- Enable multi-factor authentication for administrative access

**Data Protection:**
- Use customer-managed encryption keys (CMEK)
- Implement data classification and handling procedures
- Regular backup and test recovery procedures
- Monitor for unauthorized access attempts

**Network Security:**
- Use VPC networks for network isolation
- Implement firewall rules with least-privilege access
- Monitor network traffic for anomalies
- Use private Google Access where possible

### 9.2 Operational Best Practices

**Monitoring and Alerting:**
- Set up comprehensive monitoring dashboards
- Configure alerts for critical system events
- Monitor performance metrics and trends
- Implement automated incident response procedures

**Change Management:**
- Use version control for all configuration changes
- Test changes in development environments first
- Document all changes and their impact
- Implement rollback procedures for failed changes

**Documentation:**
- Maintain up-to-date system documentation
- Document all procedures and processes
- Keep contact information current
- Regular review and update documentation

### 9.3 Compliance Best Practices

**Data Governance:**
- Implement data classification schemes
- Define data retention and disposal policies
- Regular compliance assessments and audits
- Maintain comprehensive audit trails

**Privacy Protection:**
- Implement privacy by design principles
- Provide mechanisms for data subject rights
- Regular privacy impact assessments
- Maintain privacy policy and procedures

**Regulatory Compliance:**
- Stay current with regulatory requirements
- Implement required technical and organizational measures
- Regular compliance training for staff
- Maintain relationships with regulatory bodies

## 10. Support and Resources

### 10.1 Getting Help

**Documentation:**
- User Guide (this document)
- API Documentation: `/api/docs` when running the application
- Security Assessment: `docs/security-assessment.md`
- Privacy Policy: `docs/privacy-policy.md`

**Community Support:**
- GitHub Issues: Report bugs and request features
- Community Forums: Discuss best practices and get help
- Stack Overflow: Tag questions with `gdriveprotect`

**Professional Support:**
- Email Support: support@gdriveprotect.com
- Priority Support: Available for enterprise customers
- Consulting Services: Implementation and optimization assistance

### 10.2 Additional Resources

**Google Cloud Documentation:**
- [Google Cloud DLP API Documentation](https://cloud.google.com/dlp/docs)
- [Google Drive API Documentation](https://developers.google.com/drive/api)
- [Google Cloud Storage Documentation](https://cloud.google.com/storage/docs)
- [Google Cloud KMS Documentation](https://cloud.google.com/kms/docs)

**Compliance Resources:**
- [GDPR Compliance Guide](https://gdpr.eu/)
- [HIPAA Compliance Resources](https://www.hhs.gov/hipaa/)
- [SOC 2 Compliance Framework](https://www.aicpa.org/interestareas/frc/assuranceadvisoryservices/sorhome.html)

**Security Resources:**
- [OWASP Security Guidelines](https://owasp.org/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [Cloud Security Alliance](https://cloudsecurityalliance.org/)

### 10.3 Training and Certification

**Administrator Training:**
- GDriveProtect Administrator Certification
- Google Cloud Security Certification
- Data Protection and Privacy Training

**Developer Training:**
- API Integration Workshop
- Secure Development Practices
- Cloud Security Best Practices

**End User Training:**
- Data Classification Training
- Security Awareness Training
- Incident Response Training

---

This user guide provides comprehensive instructions for implementing and using GDriveProtect in your organization. For additional assistance or questions not covered in this guide, please contact our support team or consult the additional resources listed above.

