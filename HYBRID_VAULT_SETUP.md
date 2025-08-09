# 🔐 Hybrid Vault Setup Guide
## FIPS-140-2 Compliant Storage with Google Drive Integration

This guide covers setting up the enhanced vault system that supports both Cloud Storage buckets and Google Drive folders, with options for both Enterprise Google Workspace organizations and individual users.

## 🏗️ Architecture Overview

The hybrid vault system provides three storage options:

1. **Cloud Storage Bucket** - Maximum security with FIPS-140-2 encryption
2. **Google Drive Folder** - User-friendly access with FIPS-140-2 encrypted files
3. **Hybrid Storage** - Best of both worlds (recommended)

### User Types Supported

- **Enterprise Users** - Google Workspace organizations with domain-wide delegation
- **Individual Users** - Personal Google accounts with OAuth authentication

## 🚀 Quick Setup

### 1. Environment Configuration

Set the following environment variables:

```bash
# Core Configuration
export GOOGLE_CLOUD_PROJECT="your-project-id"
export VAULT_STORAGE_PREFERENCE="hybrid"  # bucket, drive, or hybrid
export FIPS_ENABLED="true"

# User Type Configuration
export USER_TYPE="enterprise"  # enterprise or individual

# Enterprise Configuration (if USER_TYPE=enterprise)
export ENTERPRISE_DOMAIN="yourcompany.com"
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account.json"

# Individual Configuration (if USER_TYPE=individual)
export INDIVIDUAL_USER_EMAIL="user@gmail.com"
export GOOGLE_CLIENT_ID="your-oauth-client-id"
export GOOGLE_CLIENT_SECRET="your-oauth-client-secret"

# Storage Configuration
export VAULT_BUCKET="your-vault-bucket"
export DRIVE_VAULT_FOLDER_NAME="Secure Vault - FIPS Encrypted"
export KMS_KEY_NAME="projects/your-project/locations/global/keyRings/your-ring/cryptoKeys/your-key"
```

### 2. Enterprise Setup

#### Step 1: Create Service Account
```bash
gcloud iam service-accounts create vault-manager \
    --display-name="Vault Manager Service Account" \
    --description="Service account for hybrid vault operations"
```

#### Step 2: Enable Domain-Wide Delegation
```bash
# Get the service account email
SERVICE_ACCOUNT="vault-manager@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com"

# Create service account key
gcloud iam service-accounts keys create vault-credentials.json \
    --iam-account=$SERVICE_ACCOUNT

# In Google Workspace Admin Console:
# 1. Go to Security > API Controls > Domain-wide Delegation
# 2. Add new API client
# 3. Client ID: [from service account key]
# 4. OAuth Scopes: https://www.googleapis.com/auth/drive
```

#### Step 3: Grant Permissions
```bash
gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/cloudkms.cryptoKeyEncrypterDecrypter"
```

### 3. Individual User Setup

#### Step 1: Create OAuth 2.0 Credentials
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to APIs & Services > Credentials
3. Create OAuth 2.0 Client ID
4. Set authorized redirect URIs: `http://localhost:5000/oauth2callback`
5. Download `client_secrets.json`

#### Step 2: Configure OAuth Scopes
The application requires the following scopes:
- `https://www.googleapis.com/auth/drive` - Full access to Google Drive

## 🔧 API Endpoints

### Storage Management

#### Get Storage Options
```bash
GET /api/vault/storage-options
```
Returns available storage options and current configuration.

#### Set Storage Preference
```bash
POST /api/vault/set-storage-preference
Content-Type: application/json

{
  "preference": "hybrid"  // bucket, drive, or hybrid
}
```

#### Get Storage Status
```bash
GET /api/vault/storage-status
```
Returns detailed status of all storage systems.

### User Management

#### Get User Information
```bash
GET /api/vault/user-info
```
Returns current user information and permissions.

#### Set User Type
```bash
POST /api/vault/set-user-type
Content-Type: application/json

{
  "user_type": "enterprise",  // enterprise or individual
  "enterprise_domain": "yourcompany.com"  // for enterprise
}
```

#### Get OAuth URL (Individual Users)
```bash
GET /api/vault/auth-url
```
Returns OAuth URL for individual user authentication.

#### Get User Vault
```bash
GET /api/vault/user-vault
# For enterprise users, include user email:
GET /api/vault/user-vault?user_email=user@company.com
# Or in headers:
GET /api/vault/user-vault
X-User-Email: user@company.com
```

### Document Operations

#### Store Document
```bash
POST /api/vault/store
Content-Type: application/json

{
  "file_id": "1234567890",
  "file_name": "sensitive_document.pdf",
  "content": "base64_encoded_content",
  "metadata": {
    "scan_results": {...},
    "risk_level": "high"
  }
}
```

#### Retrieve Document
```bash
GET /api/vault/retrieve/bucket://documents/1234567890_20250101_120000_sensitive_document.pdf
GET /api/vault/retrieve/drive://folder_id/document_name.pdf
```

#### List Documents
```bash
GET /api/vault/list?limit=50
```

## 🔒 Security Features

### FIPS-140-2 Compliance
- **AES-256-GCM encryption** for all sensitive data
- **PBKDF2 with SHA-256** for key derivation
- **100,000 iterations** (NIST recommended minimum)
- **Hardware security modules** for key storage (when using Cloud KMS)

### Access Controls
- **Enterprise**: Domain-wide delegation with admin oversight
- **Individual**: OAuth 2.0 with user consent
- **Folder-level permissions** for Google Drive vaults
- **Bucket-level IAM** for Cloud Storage vaults

### Audit Trail
- **Comprehensive logging** of all vault operations
- **Access tracking** with user identification
- **Encryption status** monitoring
- **Compliance reporting** capabilities

## 📊 Storage Comparison

| Feature | Cloud Storage Bucket | Google Drive Folder | Hybrid |
|---------|---------------------|-------------------|---------|
| **FIPS-140-2 Compliance** | ✅ Full | ✅ File-level | ✅ Full |
| **User Accessibility** | ⚠️ API only | ✅ Native Drive | ✅ Both |
| **Admin Controls** | ✅ Advanced | ✅ Standard | ✅ Advanced |
| **Mobile Access** | ❌ No | ✅ Yes | ✅ Yes |
| **Audit Trail** | ✅ Comprehensive | ✅ Basic | ✅ Comprehensive |
| **Cost** | 💰 Low | 💰 Free tier | 💰 Low |
| **Setup Complexity** | 🔧 Medium | 🔧 Easy | 🔧 Medium |

## 🧪 Testing Scenarios

### Enterprise Testing
```bash
# Set enterprise mode
curl -X POST http://localhost:5000/api/vault/set-user-type \
  -H "Content-Type: application/json" \
  -d '{"user_type": "enterprise", "enterprise_domain": "testcompany.com"}'

# Check storage options
curl http://localhost:5000/api/vault/storage-options

# Get user vault for specific user
curl "http://localhost:5000/api/vault/user-vault?user_email=test@testcompany.com"
```

### Individual Testing
```bash
# Set individual mode
curl -X POST http://localhost:5000/api/vault/set-user-type \
  -H "Content-Type: application/json" \
  -d '{"user_type": "individual"}'

# Get OAuth URL
curl http://localhost:5000/api/vault/auth-url

# After OAuth, get user vault
curl http://localhost:5000/api/vault/user-vault
```

### Hybrid Storage Testing
```bash
# Set hybrid preference
curl -X POST http://localhost:5000/api/vault/set-storage-preference \
  -H "Content-Type: application/json" \
  -d '{"preference": "hybrid"}'

# Store document (will use both storage systems)
curl -X POST http://localhost:5000/api/vault/store \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "test123",
    "file_name": "test_document.txt",
    "content": "VGhpcyBpcyBhIHRlc3QgZG9jdW1lbnQ="
  }'
```

## 🔍 Troubleshooting

### Common Issues

#### Enterprise Domain-Wide Delegation
**Issue**: "Access denied" errors for user operations
**Solution**: 
1. Verify domain-wide delegation is enabled in Google Workspace Admin Console
2. Check that the service account has the correct client ID
3. Ensure the user email is in the correct domain

#### Individual OAuth
**Issue**: OAuth flow fails
**Solution**:
1. Verify `client_secrets.json` is in the correct location
2. Check redirect URI matches exactly
3. Ensure OAuth consent screen is configured

#### Drive API Quotas
**Issue**: "Quota exceeded" errors
**Solution**:
1. Implement rate limiting in your application
2. Request quota increases from Google Cloud Console
3. Use batch operations for multiple files

### Health Checks
```bash
# Check vault health
curl http://localhost:5000/api/vault/health

# Check storage status
curl http://localhost:5000/api/vault/storage-status

# Check security status
curl http://localhost:5000/api/vault/security-status
```

## 📈 Best Practices

### For Enterprise Organizations
1. **Use hybrid storage** for maximum flexibility
2. **Implement regular audits** of vault access
3. **Set up monitoring** for unusual access patterns
4. **Train users** on secure document handling

### For Individual Users
1. **Use Drive storage** for ease of access
2. **Enable 2FA** on your Google account
3. **Regularly review** vault contents
4. **Use strong passwords** for additional security

### General Recommendations
1. **Start with hybrid mode** to test both storage types
2. **Monitor storage costs** and usage patterns
3. **Regularly update** encryption keys
4. **Backup vault metadata** for disaster recovery

## 🆘 Support

For additional support:
- Check the main [README.md](README.md) for general setup
- Review [TESTING.md](TESTING.md) for testing procedures
- Consult [docs/](docs/) for detailed documentation
- Open an issue on GitHub for bug reports
