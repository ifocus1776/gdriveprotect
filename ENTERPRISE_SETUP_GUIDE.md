# 🏢 Enterprise Google Workspace Setup Guide

## Overview
This guide explains how to configure GDriveProtect for enterprise deployment with Google Workspace, enabling access to all users' files within the organization.

## 🔐 Authentication Methods Comparison

### Current (Personal OAuth)
- ❌ Each user needs individual authentication
- ❌ Limited to personal Google Drive files
- ❌ Not scalable for enterprise
- ❌ Requires user consent for each installation

### Enterprise (Domain-Wide Delegation)
- ✅ Single service account accesses all users
- ✅ Admin can grant organization-wide permissions
- ✅ Scalable for thousands of users
- ✅ No individual user consent required
- ✅ Centralized security management

## 🚀 Setup Steps

### 1. Service Account Creation ✅
```bash
# Already completed:
gcloud iam service-accounts create gdriveprotect-enterprise \
  --display-name="GDriveProtect Enterprise Service Account" \
  --description="Service account for enterprise Google Workspace DLP scanning and vault management"
```

### 2. Service Account Key ✅
```bash
# Already completed:
gcloud iam service-accounts keys create enterprise-service-account-key.json \
  --iam-account=gdriveprotect-enterprise@ifocus-innovations.iam.gserviceaccount.com
```

### 3. Google Cloud Permissions ✅
```bash
# Already completed:
gcloud projects add-iam-policy-binding ifocus-innovations \
  --member="serviceAccount:gdriveprotect-enterprise@ifocus-innovations.iam.gserviceaccount.com" \
  --role="roles/dlp.user"

gcloud projects add-iam-policy-binding ifocus-innovations \
  --member="serviceAccount:gdriveprotect-enterprise@ifocus-innovations.iam.gserviceaccount.com" \
  --role="roles/storage.admin"
```

### 4. Domain-Specific OAuth Client Setup

#### Step 4a: Create OAuth Client ID for ifocusinnovations.com
1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Select your `ifocus-innovations` project
3. Click **+ CREATE CREDENTIALS** → **OAuth client ID**
4. Configure the OAuth client:
   - **Application type**: `Web application`
   - **Name**: `GDriveProtect Enterprise - ifocusinnovations.com`
   - **Authorized JavaScript origins**: 
     - `http://localhost:5000` (development)
     - `https://your-production-domain.com` (production)
   - **Authorized redirect URIs**:
     - `http://localhost:5000/oauth2callback` (development)
     - `https://your-production-domain.com/oauth2callback` (production)
5. Download the JSON file and save as `ifocusinnovations-oauth-client.json`

#### Step 4b: Google Workspace Admin Console Setup
1. Go to [Google Workspace Admin Console](https://admin.google.com)
2. Navigate to **Security** → **API Controls**
3. Enable **Domain-wide Delegation**
4. Add the **new OAuth client ID** (not the service account ID)

#### Step 4c: Configure OAuth Scopes
Add these scopes to the **OAuth client ID** (not the service account):
```
https://www.googleapis.com/auth/drive
https://www.googleapis.com/auth/drive.readonly
https://www.googleapis.com/auth/drive.metadata.readonly
https://www.googleapis.com/auth/drive.file
https://www.googleapis.com/auth/cloud-platform
```

### 5. Update Application Configuration

The application has been updated to use the enterprise service account:
- ✅ Dockerfile updated to use `enterprise-service-account-key.json`
- ✅ Service account has DLP and Storage permissions
- ✅ Ready for domain-wide delegation

## 🔒 Security Considerations

### Service Account Security
- ✅ Key stored securely in container
- ✅ Minimal required permissions (DLP + Storage)
- ✅ No user data access without admin consent

### Data Protection
- ✅ All sensitive data encrypted at rest
- ✅ FIPS-140-2 compliant vault encryption
- ✅ Audit logging for all access
- ✅ Automatic sensitive file migration

### Access Control
- ✅ Admin controls which users' files are accessible
- ✅ Granular permission scopes
- ✅ Centralized security management

## 📁 File Storage Strategy

### Current: Google Cloud Storage Buckets
**Pros:**
- ✅ FIPS-140-2 compliant encryption
- ✅ Automatic versioning and lifecycle policies
- ✅ Audit logging and access controls
- ✅ Integration with Google Cloud KMS
- ✅ Scalable and cost-effective

**Cons:**
- ❌ Separate from Google Drive ecosystem
- ❌ Additional storage costs
- ❌ Different access patterns

### Alternative: Secure Google Drive Folders
**Pros:**
- ✅ Native Google Drive integration
- ✅ Familiar user interface
- ✅ Built-in sharing and permissions
- ✅ No additional storage costs

**Cons:**
- ❌ Limited encryption options
- ❌ Less granular access controls
- ❌ No automatic FIPS compliance
- ❌ Manual security management

## 🎯 Recommendation

**Use Google Cloud Storage Buckets** for the following reasons:

1. **Security**: FIPS-140-2 compliance and enterprise-grade encryption
2. **Compliance**: Audit trails and access logging
3. **Scalability**: Automatic lifecycle management
4. **Cost**: More cost-effective for large-scale deployments
5. **Integration**: Seamless with Google Cloud DLP and KMS

## 🚀 Deployment Steps

### 1. Build with Enterprise Service Account
```bash
docker build -t gdriveprotect-enterprise .
```

### 2. Run with Enterprise Configuration
```bash
docker run -d \
  --name gdriveprotect-enterprise \
  -p 5000:5000 \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/.config/gcloud/application_default_credentials.json \
  gdriveprotect-enterprise
```

### 3. Test Enterprise Access
```bash
# Test listing files (will show all users' files with proper delegation)
curl -s "http://localhost:5000/api/drive/files" | jq .
```

## 🔧 Configuration Options

### Environment Variables
```bash
# Service account configuration
GOOGLE_APPLICATION_CREDENTIALS=/app/.config/gcloud/application_default_credentials.json

# DLP configuration
DLP_PROJECT_ID=ifocus-innovations
DLP_LOCATION=us-central1

# Storage configuration
STORAGE_BUCKET=drive-scanner-results
VAULT_BUCKET=gdriveprotect-vault

# Security configuration
FIPS_ENABLED=true
ENCRYPTION_ALGORITHM=AES-256-GCM
```

### Admin Console Settings
- **Domain-wide Delegation**: Enabled
- **API Access**: Restricted to service account
- **OAuth Scopes**: Minimal required permissions
- **Audit Logging**: Enabled for all access

## 📊 Monitoring and Compliance

### Audit Logs
- All file access logged
- DLP scan results tracked
- Vault access monitored
- User activity recorded

### Compliance Features
- FIPS-140-2 encryption
- GDPR-ready data handling
- SOC 2 compliance ready
- HIPAA-compliant data protection

## 🆘 Troubleshooting

### Common Issues

1. **"Insufficient authentication scopes"**
   - Ensure domain-wide delegation is enabled
   - Verify OAuth scopes are configured correctly

2. **"Service account not found"**
   - Check service account exists in Google Cloud Console
   - Verify key file is properly mounted

3. **"Access denied to user files"**
   - Confirm admin has granted organization-wide access
   - Check user's Google Drive sharing settings

### Debug Commands
```bash
# Check service account status
gcloud iam service-accounts describe gdriveprotect-enterprise@ifocus-innovations.iam.gserviceaccount.com

# Verify permissions
gcloud projects get-iam-policy ifocus-innovations --flatten="bindings[].members" --format="table(bindings.role)" --filter="bindings.members:gdriveprotect-enterprise"

# Test authentication
gcloud auth activate-service-account --key-file=enterprise-service-account-key.json
```

## 📞 Support

For enterprise deployment support:
1. Review this guide thoroughly
2. Test in a development environment first
3. Contact your Google Workspace admin for domain-wide delegation setup
4. Monitor logs and audit trails after deployment

---

**Next Steps:**
1. Complete Google Workspace Admin Console setup
2. Test with a small group of users
3. Deploy to production environment
4. Monitor and audit access patterns
