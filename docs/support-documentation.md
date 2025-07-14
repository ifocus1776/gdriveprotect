# Support Documentation and Troubleshooting Guide
## Google Drive Sensitive Data Scanner (GDriveProtect)

**Version:** 1.0  
**Last Updated:** January 2025  
**Support Level:** Enterprise

---

## Table of Contents

1. [Support Overview](#1-support-overview)
2. [Getting Help](#2-getting-help)
3. [Common Issues and Solutions](#3-common-issues-and-solutions)
4. [Troubleshooting Procedures](#4-troubleshooting-procedures)
5. [Error Codes and Messages](#5-error-codes-and-messages)
6. [Performance Optimization](#6-performance-optimization)
7. [Maintenance and Updates](#7-maintenance-and-updates)
8. [Escalation Procedures](#8-escalation-procedures)
9. [Knowledge Base](#9-knowledge-base)
10. [Contact Information](#10-contact-information)

---

## 1. Support Overview

### 1.1 Support Philosophy

At GDriveProtect, we are committed to providing exceptional support to ensure your organization can effectively protect sensitive data and maintain compliance. Our support team consists of experienced security professionals, cloud architects, and compliance experts who understand the critical nature of data protection.

### 1.2 Support Tiers

**Basic Support (Included with all plans)**
- Email support during business hours (9 AM - 5 PM local time)
- Access to documentation and knowledge base
- Community forum access
- Response time: 24-48 hours for non-critical issues

**Priority Support (Professional and Enterprise plans)**
- Email and phone support during extended hours (7 AM - 7 PM local time)
- Priority queue for faster response times
- Access to senior support engineers
- Response time: 4-8 hours for critical issues, 12-24 hours for non-critical

**Premium Support (Enterprise plans only)**
- 24/7 phone and email support
- Dedicated customer success manager
- Proactive monitoring and health checks
- Emergency escalation procedures
- Response time: 1-2 hours for critical issues, 4-8 hours for non-critical

### 1.3 Support Scope

**Covered Support Areas:**
- Application installation and configuration
- API integration assistance
- Performance optimization guidance
- Security best practices consultation
- Compliance framework implementation
- Troubleshooting technical issues
- Feature usage and configuration

**Not Covered (Professional Services Required):**
- Custom development and integrations
- Extensive configuration consulting
- Training and certification programs
- Third-party software integration
- Infrastructure design and implementation

## 2. Getting Help

### 2.1 Before Contacting Support

**Step 1: Check System Status**
Visit our status page at https://status.gdriveprotect.com to check for known issues or maintenance activities.

**Step 2: Review Documentation**
- User Guide: Comprehensive setup and usage instructions
- API Documentation: Complete API reference with examples
- Knowledge Base: Common issues and solutions
- Security Assessment: Security and compliance information

**Step 3: Check Logs**
Review application logs for error messages and diagnostic information:
```bash
# Application logs
tail -f logs/application.log

# Google Cloud logs
gcloud logging read "resource.type=gce_instance AND logName=projects/YOUR_PROJECT/logs/gdriveprotect" --limit=50
```

**Step 4: Gather Information**
Collect the following information before contacting support:
- Application version and deployment method
- Error messages and timestamps
- Steps to reproduce the issue
- System configuration details
- Recent changes or updates

### 2.2 Support Channels

**Email Support**
- **General Support**: support@gdriveprotect.com
- **Technical Issues**: technical@gdriveprotect.com
- **Security Concerns**: security@gdriveprotect.com
- **Billing Questions**: billing@gdriveprotect.com

**Phone Support** (Priority and Premium Support only)
- **US/Canada**: 1-800-GDRIVE-1 (1-800-437-4831)
- **International**: +1-555-123-4567
- **Emergency Hotline**: +1-555-911-HELP (Premium Support only)

**Online Resources**
- **Knowledge Base**: https://help.gdriveprotect.com
- **Community Forum**: https://community.gdriveprotect.com
- **Status Page**: https://status.gdriveprotect.com
- **Documentation**: https://docs.gdriveprotect.com

### 2.3 Creating Effective Support Requests

**Subject Line Format:**
`[PRIORITY] Brief description of issue - [Environment]`

Example: `[HIGH] DLP scanning fails for PDF files - Production`

**Required Information:**
- **Issue Description**: Clear, concise description of the problem
- **Environment**: Production, staging, development
- **Priority Level**: Critical, high, medium, low
- **Steps to Reproduce**: Detailed steps to recreate the issue
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Error Messages**: Complete error messages and stack traces
- **System Information**: Version, configuration, environment details
- **Impact Assessment**: Business impact and affected users

**Priority Levels:**
- **Critical**: System down, data loss, security breach
- **High**: Major functionality impaired, significant user impact
- **Medium**: Minor functionality issues, workaround available
- **Low**: Questions, feature requests, documentation issues

## 3. Common Issues and Solutions

### 3.1 Authentication and Authorization Issues

**Issue: Service Account Authentication Failure**
```
Error: google.auth.exceptions.DefaultCredentialsError: Could not automatically determine credentials
```

**Solution:**
1. Verify service account key file exists and is accessible
2. Check GOOGLE_APPLICATION_CREDENTIALS environment variable
3. Ensure service account has required permissions
4. Test authentication manually:
```bash
gcloud auth activate-service-account --key-file=credentials.json
gcloud auth list
```

**Issue: Insufficient Permissions**
```
Error: 403 Forbidden - The caller does not have permission
```

**Solution:**
1. Review required IAM roles in documentation
2. Check current service account permissions:
```bash
gcloud projects get-iam-policy YOUR_PROJECT_ID --flatten="bindings[].members" --filter="bindings.members:YOUR_SERVICE_ACCOUNT"
```
3. Grant missing permissions:
```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:YOUR_SERVICE_ACCOUNT" \
    --role="roles/dlp.user"
```

### 3.2 API and Connectivity Issues

**Issue: API Quota Exceeded**
```
Error: 429 Too Many Requests - Quota exceeded for quota metric 'Requests' and limit 'Requests per minute'
```

**Solution:**
1. Check current quota usage in Google Cloud Console
2. Implement exponential backoff in API calls
3. Request quota increase if needed
4. Optimize API usage patterns

**Issue: Network Connectivity Problems**
```
Error: requests.exceptions.ConnectionError: Failed to establish a new connection
```

**Solution:**
1. Check network connectivity to Google APIs
2. Verify firewall rules allow outbound HTTPS traffic
3. Test connectivity manually:
```bash
curl -I https://dlp.googleapis.com/
curl -I https://www.googleapis.com/drive/v3/about
```
4. Check proxy settings if applicable

### 3.3 Scanning and Processing Issues

**Issue: Files Not Being Scanned**

**Possible Causes and Solutions:**
1. **File type not supported**: Check supported MIME types in configuration
2. **File too large**: DLP API has size limits (10MB for most file types)
3. **Permissions issue**: Service account lacks access to file
4. **File corrupted**: File cannot be processed by DLP API

**Diagnostic Steps:**
```bash
# Check file metadata
curl -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  "https://www.googleapis.com/drive/v3/files/FILE_ID?fields=id,name,mimeType,size,permissions"

# Test DLP API directly
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -d '{"item":{"value":"test content"},"inspectConfig":{"infoTypes":[{"name":"EMAIL_ADDRESS"}]}}' \
  "https://dlp.googleapis.com/v2/projects/YOUR_PROJECT_ID/content:inspect"
```

**Issue: False Positives in Scan Results**

**Solution:**
1. Adjust DLP detection likelihood thresholds
2. Implement custom detection rules
3. Use exclusion patterns for known false positives
4. Fine-tune infoType configurations

### 3.4 Storage and Vault Issues

**Issue: Vault Storage Failures**
```
Error: google.cloud.exceptions.Forbidden: 403 Access denied
```

**Solution:**
1. Verify bucket exists and is accessible
2. Check bucket permissions for service account
3. Ensure bucket location matches application region
4. Test bucket access manually:
```bash
gsutil ls gs://your-vault-bucket
gsutil cp test-file.txt gs://your-vault-bucket/
```

**Issue: Encryption Key Access Denied**
```
Error: google.cloud.exceptions.Forbidden: Permission denied on Cloud KMS key
```

**Solution:**
1. Verify KMS key exists and is enabled
2. Check service account has cryptoKeyEncrypterDecrypter role
3. Test key access:
```bash
gcloud kms keys list --location=global --keyring=your-keyring
gcloud kms encrypt --key=your-key --location=global --keyring=your-keyring --plaintext-file=test.txt --ciphertext-file=test.enc
```

## 4. Troubleshooting Procedures

### 4.1 System Health Check

**Step 1: Verify Service Status**
```bash
# Check application health endpoints
curl http://localhost:5000/api/dlp/health
curl http://localhost:5000/api/drive/health
curl http://localhost:5000/api/vault/health
```

**Step 2: Check Google Cloud Services**
```bash
# Verify API enablement
gcloud services list --enabled --filter="name:dlp.googleapis.com OR name:drive.googleapis.com OR name:storage.googleapis.com"

# Check service account status
gcloud iam service-accounts describe YOUR_SERVICE_ACCOUNT
```

**Step 3: Review System Resources**
```bash
# Check disk space
df -h

# Check memory usage
free -h

# Check CPU usage
top -n 1
```

### 4.2 Log Analysis

**Application Logs:**
```bash
# View recent application logs
tail -f logs/application.log

# Search for specific errors
grep -i "error\|exception\|failed" logs/application.log | tail -20

# Filter logs by timestamp
awk '/2025-01-01 10:00:00/,/2025-01-01 11:00:00/' logs/application.log
```

**Google Cloud Logs:**
```bash
# View recent Cloud Logging entries
gcloud logging read "resource.type=gce_instance" --limit=50 --format="table(timestamp,severity,textPayload)"

# Filter by severity
gcloud logging read "resource.type=gce_instance AND severity>=ERROR" --limit=20

# Search for specific errors
gcloud logging read "resource.type=gce_instance AND textPayload:\"authentication failed\"" --limit=10
```

### 4.3 Performance Diagnostics

**API Performance Testing:**
```bash
# Test DLP API response time
time curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -d '{"item":{"value":"test@example.com"},"inspectConfig":{"infoTypes":[{"name":"EMAIL_ADDRESS"}]}}' \
  "https://dlp.googleapis.com/v2/projects/YOUR_PROJECT_ID/content:inspect"

# Test Drive API response time
time curl -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  "https://www.googleapis.com/drive/v3/files?pageSize=10"
```

**Database Performance:**
```bash
# Check database connection
python3 -c "
from src.models.user import db
from src.main import app
with app.app_context():
    try:
        db.engine.execute('SELECT 1')
        print('Database connection successful')
    except Exception as e:
        print(f'Database connection failed: {e}')
"
```

### 4.4 Network Diagnostics

**Connectivity Testing:**
```bash
# Test Google API connectivity
nslookup dlp.googleapis.com
ping -c 4 dlp.googleapis.com
telnet dlp.googleapis.com 443

# Test specific endpoints
curl -I https://dlp.googleapis.com/
curl -I https://www.googleapis.com/drive/v3/about
curl -I https://storage.googleapis.com/
```

**Firewall and Proxy Testing:**
```bash
# Check outbound connectivity
curl -v https://www.google.com
curl -v --proxy your-proxy:port https://dlp.googleapis.com/

# Test specific ports
nc -zv dlp.googleapis.com 443
nc -zv www.googleapis.com 443
```

## 5. Error Codes and Messages

### 5.1 HTTP Error Codes

**400 Bad Request**
- **Cause**: Invalid request parameters or malformed JSON
- **Solution**: Validate request format and parameters
- **Example**: Missing required fields in API request

**401 Unauthorized**
- **Cause**: Invalid or missing authentication credentials
- **Solution**: Check authentication tokens and service account permissions
- **Example**: Expired OAuth token or missing Authorization header

**403 Forbidden**
- **Cause**: Insufficient permissions for requested operation
- **Solution**: Review and grant required IAM permissions
- **Example**: Service account lacks DLP API access

**404 Not Found**
- **Cause**: Requested resource does not exist
- **Solution**: Verify resource IDs and paths
- **Example**: Google Drive file ID not found

**429 Too Many Requests**
- **Cause**: API quota exceeded or rate limiting
- **Solution**: Implement backoff strategies and request quota increases
- **Example**: DLP API requests per minute limit exceeded

**500 Internal Server Error**
- **Cause**: Server-side error or service unavailability
- **Solution**: Check service status and retry request
- **Example**: Temporary Google Cloud service outage

### 5.2 Application-Specific Errors

**DLP_SCAN_FAILED**
```json
{
  "error": "DLP_SCAN_FAILED",
  "message": "Failed to scan file content",
  "details": {
    "file_id": "1234567890",
    "error_code": "INVALID_ARGUMENT",
    "description": "File content could not be processed"
  }
}
```
**Solution**: Check file format, size, and content validity

**VAULT_STORAGE_ERROR**
```json
{
  "error": "VAULT_STORAGE_ERROR",
  "message": "Failed to store document in vault",
  "details": {
    "bucket": "vault-bucket",
    "error_code": "PERMISSION_DENIED",
    "description": "Insufficient permissions to write to bucket"
  }
}
```
**Solution**: Verify bucket permissions and KMS key access

**DRIVE_ACCESS_DENIED**
```json
{
  "error": "DRIVE_ACCESS_DENIED",
  "message": "Cannot access Google Drive file",
  "details": {
    "file_id": "1234567890",
    "error_code": "FORBIDDEN",
    "description": "Service account lacks file access"
  }
}
```
**Solution**: Check file permissions and service account access

### 5.3 Google Cloud API Errors

**INVALID_ARGUMENT**
- **Description**: Request contains invalid parameters
- **Common Causes**: Malformed file content, unsupported file type, invalid infoType
- **Solution**: Validate input parameters and file formats

**PERMISSION_DENIED**
- **Description**: Insufficient permissions for operation
- **Common Causes**: Missing IAM roles, disabled APIs, quota restrictions
- **Solution**: Review and grant required permissions

**RESOURCE_EXHAUSTED**
- **Description**: Quota or rate limits exceeded
- **Common Causes**: API quota exceeded, concurrent request limits
- **Solution**: Implement rate limiting and request quota increases

**UNAVAILABLE**
- **Description**: Service temporarily unavailable
- **Common Causes**: Service outage, maintenance, network issues
- **Solution**: Implement retry logic with exponential backoff

## 6. Performance Optimization

### 6.1 Scanning Performance

**Optimize File Processing:**
- Implement parallel processing for batch scans
- Use appropriate file size limits (10MB for DLP API)
- Filter files by type and modification date
- Implement caching for frequently scanned files

**DLP API Optimization:**
```python
# Optimize DLP inspection configuration
inspect_config = {
    "info_types": [{"name": "EMAIL_ADDRESS"}, {"name": "PHONE_NUMBER"}],
    "min_likelihood": "POSSIBLE",  # Adjust based on accuracy needs
    "limits": {"max_findings_per_request": 100},
    "include_quote": False  # Disable if not needed
}
```

**Batch Processing:**
```python
# Process files in batches
batch_size = 10
for i in range(0, len(file_ids), batch_size):
    batch = file_ids[i:i + batch_size]
    process_batch(batch)
    time.sleep(1)  # Rate limiting
```

### 6.2 Storage Optimization

**Lifecycle Policies:**
```bash
# Create lifecycle policy for scan results
cat > lifecycle.json << EOF
{
  "rule": [
    {
      "action": {"type": "Delete"},
      "condition": {"age": 365}
    }
  ]
}
EOF

gsutil lifecycle set lifecycle.json gs://your-scan-results-bucket
```

**Storage Class Optimization:**
```bash
# Use appropriate storage classes
gsutil defstorageclass set STANDARD gs://your-vault-bucket
gsutil defstorageclass set NEARLINE gs://your-archive-bucket
```

### 6.3 Network Optimization

**Regional Deployment:**
- Deploy application in same region as data
- Use regional Google Cloud services
- Implement CDN for static content
- Optimize API request patterns

**Connection Pooling:**
```python
# Implement connection pooling
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
```

## 7. Maintenance and Updates

### 7.1 Regular Maintenance Tasks

**Daily Tasks:**
- Monitor system health and performance metrics
- Review error logs and alerts
- Check API quota usage
- Verify backup completion

**Weekly Tasks:**
- Review scan results and false positives
- Update detection rules and patterns
- Check storage usage and costs
- Review access logs and permissions

**Monthly Tasks:**
- Update application dependencies
- Review and rotate service account keys
- Conduct security assessments
- Update documentation and procedures

**Quarterly Tasks:**
- Review compliance reports and audits
- Update disaster recovery procedures
- Conduct penetration testing
- Review and update security policies

### 7.2 Update Procedures

**Application Updates:**
1. Review release notes and breaking changes
2. Test updates in development environment
3. Schedule maintenance window
4. Create backup of current configuration
5. Deploy updates using blue-green deployment
6. Verify functionality and rollback if needed

**Dependency Updates:**
```bash
# Update Python dependencies
pip list --outdated
pip install --upgrade package-name

# Update requirements.txt
pip freeze > requirements.txt

# Test application after updates
python -m pytest tests/
```

**Security Updates:**
- Apply security patches immediately
- Update service account keys regularly
- Rotate encryption keys according to policy
- Review and update access permissions

### 7.3 Backup and Recovery

**Backup Procedures:**
```bash
# Backup application configuration
tar -czf config-backup-$(date +%Y%m%d).tar.gz config/

# Backup database
sqlite3 src/database/app.db ".backup backup-$(date +%Y%m%d).db"

# Backup vault contents
gsutil -m cp -r gs://your-vault-bucket gs://your-backup-bucket/vault-backup-$(date +%Y%m%d)
```

**Recovery Procedures:**
1. Assess scope and impact of failure
2. Restore from most recent backup
3. Verify data integrity and completeness
4. Test application functionality
5. Document lessons learned and improve procedures

## 8. Escalation Procedures

### 8.1 Internal Escalation

**Level 1: Support Engineer**
- Initial triage and basic troubleshooting
- Documentation and knowledge base consultation
- Standard issue resolution

**Level 2: Senior Support Engineer**
- Complex technical issues
- API integration problems
- Performance optimization
- Security configuration issues

**Level 3: Engineering Team**
- Product bugs and defects
- Feature requests and enhancements
- Architecture and design issues
- Critical system failures

**Level 4: Management Escalation**
- Customer satisfaction issues
- Service level agreement breaches
- Security incidents
- Business impact assessment

### 8.2 External Escalation

**Google Cloud Support:**
- Infrastructure and platform issues
- API service problems
- Quota and billing issues
- Security and compliance questions

**Emergency Contacts:**
- **Security Incidents**: security@gdriveprotect.com
- **Service Outages**: operations@gdriveprotect.com
- **Executive Escalation**: executive@gdriveprotect.com

### 8.3 Escalation Criteria

**Automatic Escalation Triggers:**
- Critical system failures affecting all users
- Security breaches or data loss incidents
- Service level agreement violations
- Customer satisfaction scores below threshold

**Time-Based Escalation:**
- Level 1 to Level 2: 4 hours for critical issues
- Level 2 to Level 3: 8 hours for critical issues
- Level 3 to Management: 24 hours for critical issues

## 9. Knowledge Base

### 9.1 Frequently Asked Questions

**Q: How long does it take to scan a typical Google Drive?**
A: Scanning time depends on the number and size of files. Typical rates are 100-500 files per minute, depending on file types and content complexity.

**Q: What file types are supported for scanning?**
A: We support PDF, Microsoft Office files, Google Workspace files, text files, and many other common formats. See the user guide for a complete list.

**Q: How secure is the vault storage?**
A: Vault storage uses customer-managed encryption keys (CMEK) with AES-256 encryption, stored in Google Cloud Storage with comprehensive access controls and audit logging.

**Q: Can I customize the types of sensitive data detected?**
A: Yes, you can configure custom detection patterns and adjust sensitivity levels for different data types through the API or configuration files.

**Q: How do I handle false positives?**
A: You can adjust detection thresholds, implement exclusion patterns, and fine-tune detection rules to reduce false positives while maintaining security.

### 9.2 Best Practices

**Security Best Practices:**
- Use customer-managed encryption keys (CMEK)
- Implement least-privilege access controls
- Enable comprehensive audit logging
- Regular security assessments and updates

**Performance Best Practices:**
- Implement batch processing for large file sets
- Use appropriate API rate limiting
- Monitor and optimize resource usage
- Implement caching where appropriate

**Compliance Best Practices:**
- Regular compliance assessments and audits
- Maintain comprehensive documentation
- Implement data retention policies
- Provide user training and awareness

### 9.3 Troubleshooting Checklists

**Pre-Deployment Checklist:**
- [ ] Google Cloud APIs enabled
- [ ] Service account created with proper permissions
- [ ] Storage buckets created and configured
- [ ] KMS keys created and accessible
- [ ] Network connectivity verified
- [ ] Application configuration validated

**Post-Deployment Checklist:**
- [ ] Health checks passing
- [ ] Authentication working correctly
- [ ] Sample scans completing successfully
- [ ] Vault storage functioning
- [ ] Monitoring and alerting configured
- [ ] Documentation updated

**Incident Response Checklist:**
- [ ] Incident severity assessed
- [ ] Stakeholders notified
- [ ] Initial containment measures implemented
- [ ] Root cause analysis initiated
- [ ] Communication plan activated
- [ ] Recovery procedures executed

## 10. Contact Information

### 10.1 Support Contacts

**Primary Support**
- **Email**: support@gdriveprotect.com
- **Phone**: 1-800-GDRIVE-1 (1-800-437-4831)
- **Hours**: Monday-Friday, 9 AM - 5 PM local time

**Technical Support**
- **Email**: technical@gdriveprotect.com
- **Phone**: 1-800-GDRIVE-1 ext. 2
- **Hours**: Monday-Friday, 7 AM - 7 PM local time (Priority Support)

**Emergency Support** (Premium Support only)
- **Phone**: +1-555-911-HELP
- **Email**: emergency@gdriveprotect.com
- **Hours**: 24/7/365

### 10.2 Specialized Support

**Security Team**
- **Email**: security@gdriveprotect.com
- **Phone**: 1-800-GDRIVE-1 ext. 3
- **Scope**: Security incidents, compliance questions, vulnerability reports

**Professional Services**
- **Email**: services@gdriveprotect.com
- **Phone**: 1-800-GDRIVE-1 ext. 4
- **Scope**: Implementation consulting, custom development, training

**Customer Success**
- **Email**: success@gdriveprotect.com
- **Phone**: 1-800-GDRIVE-1 ext. 5
- **Scope**: Account management, optimization consulting, strategic planning

### 10.3 Online Resources

**Documentation Portal**
- **URL**: https://docs.gdriveprotect.com
- **Content**: User guides, API documentation, best practices

**Community Forum**
- **URL**: https://community.gdriveprotect.com
- **Content**: User discussions, tips and tricks, feature requests

**Status Page**
- **URL**: https://status.gdriveprotect.com
- **Content**: Service status, maintenance notifications, incident reports

**Knowledge Base**
- **URL**: https://help.gdriveprotect.com
- **Content**: FAQs, troubleshooting guides, how-to articles

---

This support documentation provides comprehensive guidance for resolving issues and optimizing your GDriveProtect deployment. For additional assistance not covered in this guide, please contact our support team using the information provided above.

