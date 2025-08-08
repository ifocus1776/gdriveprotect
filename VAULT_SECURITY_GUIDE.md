# Vault Security Guide - FIPS-140-2 Compliant Storage

## Overview

The Google Drive Protect vault system provides enterprise-grade security for sensitive documents with FIPS-140-2 compliant encryption, automatic migration, and comprehensive audit logging.

## 🛡️ Security Features

### FIPS-140-2 Compliance
- **AES-256-GCM Encryption**: FIPS-140-2 validated cryptographic algorithm
- **PBKDF2 Key Derivation**: NIST-recommended key derivation with 100,000 iterations
- **Secure Random Generation**: FIPS-compliant random number generation
- **Authentication Tags**: GCM mode provides integrity and authenticity verification

### Enhanced Security Controls
- **Uniform Bucket-Level Access**: Prevents public access
- **Versioning Enabled**: Maintains file integrity and audit trail
- **Lifecycle Policies**: 7-year retention for compliance
- **Audit Logging**: Comprehensive access tracking
- **Restricted IAM Policies**: No public access allowed

## 🔧 Vault Management

### Create FIPS-Compliant Vault Bucket

```bash
curl -X POST "http://localhost:5000/api/vault/create-bucket" \
  -H "Content-Type: application/json" \
  -d '{
    "bucket_name": "my-fips-vault",
    "location": "US"
  }'
```

### Check Vault Security Status

```bash
curl "http://localhost:5000/api/vault/security-status"
```

### Auto-Migrate Sensitive Files

```bash
curl -X POST "http://localhost:5000/api/vault/auto-migrate" \
  -H "Content-Type: application/json" \
  -d '{
    "source_bucket": "drive-scanner-results",
    "min_findings": 1
  }'
```

## 📊 Security Status Response

```json
{
  "security_status": {
    "bucket_name": "drive-scanner-vault",
    "encryption_enabled": true,
    "fips_compliant": true,
    "kms_enabled": false,
    "versioning_enabled": true,
    "uniform_bucket_access": true,
    "lifecycle_policies": true,
    "compliance_level": "FIPS_140_2",
    "retention_policy": "7_years",
    "audit_logging": true,
    "access_controls": "RESTRICTED"
  }
}
```

## 🔐 Encryption Details

### FIPS-140-2 Compliant Encryption

```python
# AES-256-GCM with FIPS-compliant key derivation
def encrypt_data_fips(self, data, password=None):
    # Generate FIPS-compliant key using PBKDF2
    key, salt = self.generate_fips_compliant_key(password)
    
    # Generate random IV (96 bits for GCM)
    iv = secrets.token_bytes(12)
    
    # Create AES-256-GCM cipher
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv))
    encryptor = cipher.encryptor()
    
    # Encrypt and get authentication tag
    ciphertext = encryptor.update(data) + encryptor.finalize()
    tag = encryptor.tag
    
    # Combine salt, IV, tag, and ciphertext
    return base64.b64encode(salt + iv + tag + ciphertext)
```

### Key Features
- **AES-256**: 256-bit key strength
- **GCM Mode**: Provides both encryption and authentication
- **96-bit IV**: Optimal for GCM mode
- **Authentication Tag**: 128-bit integrity verification
- **Salt**: 256-bit random salt for key derivation

## 📋 Migration Process

### Automatic Migration Workflow

1. **Scan Detection**: DLP scanner identifies sensitive files
2. **Risk Assessment**: Files with findings ≥ threshold are flagged
3. **Secure Migration**: Files are encrypted and moved to vault
4. **Audit Logging**: All access is logged for compliance
5. **Source Cleanup**: Original files can be removed (optional)

### Migration API

```bash
curl -X POST "http://localhost:5000/api/vault/migrate-sensitive" \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "1abc123def456",
    "file_name": "sensitive_document.pdf",
    "content": "encrypted_file_content",
    "scan_results": {
      "total_findings": 5,
      "findings": [...]
    },
    "source_bucket": "drive-scanner-results"
  }'
```

## 📈 Audit Logging

### Access Log Format

```json
{
  "timestamp": "2025-08-08T18:30:00.000Z",
  "file_id": "1abc123def456",
  "action": "MIGRATION",
  "user_id": "AUTO",
  "ip_address": "192.168.1.100"
}
```

### Retrieve Audit Logs

```bash
curl "http://localhost:5000/api/vault/audit-logs"
```

## 🔒 Compliance Features

### FIPS-140-2 Requirements Met

✅ **Cryptographic Module**: AES-256-GCM implementation  
✅ **Key Management**: Secure key generation and storage  
✅ **Random Number Generation**: FIPS-compliant entropy  
✅ **Authentication**: GCM mode provides integrity  
✅ **Access Control**: Restricted bucket policies  
✅ **Audit Trail**: Comprehensive logging  

### Additional Compliance

- **7-Year Retention**: Lifecycle policies for long-term storage
- **Versioning**: File integrity and rollback capability
- **Encryption at Rest**: All data encrypted in storage
- **Access Logging**: Complete audit trail
- **No Public Access**: Restricted IAM policies

## 🚀 Environment Configuration

### Enable FIPS Mode

```bash
export FIPS_ENABLED=true
export VAULT_BUCKET=my-fips-vault
export GOOGLE_CLOUD_PROJECT=your-project-id
```

### Optional KMS Integration

```bash
export KMS_KEY_NAME=projects/your-project/locations/global/keyRings/vault/cryptoKeys/vault-key
```

## 📊 Monitoring and Alerts

### Security Metrics

- **Encryption Rate**: Percentage of encrypted documents
- **Migration Success Rate**: Successful sensitive file migrations
- **Audit Log Volume**: Access attempt monitoring
- **Compliance Status**: FIPS-140-2 validation status

### Health Checks

```bash
curl "http://localhost:5000/api/vault/health"
```

## 🔧 Advanced Configuration

### Custom Encryption Settings

```python
# In vault_manager.py
self.fips_enabled = os.environ.get('FIPS_ENABLED', 'true').lower() == 'true'
self.kms_key_name = os.environ.get('KMS_KEY_NAME')
self.vault_bucket_name = os.environ.get('VAULT_BUCKET', 'drive-scanner-vault')
```

### Lifecycle Policy Customization

```python
lifecycle_rule = {
    "action": {"type": "Delete"},
    "condition": {
        "age": 2555,  # 7 years
        "isLive": True
    }
}
```

## 🛡️ Security Best Practices

### 1. Key Management
- Use strong passwords for key derivation
- Rotate encryption keys regularly
- Store keys securely (KMS recommended)

### 2. Access Control
- Implement least-privilege access
- Monitor vault access patterns
- Review audit logs regularly

### 3. Compliance Monitoring
- Regular FIPS validation checks
- Audit log review and analysis
- Retention policy enforcement

### 4. Incident Response
- Monitor for unusual access patterns
- Implement alerting for security events
- Maintain incident response procedures

## 📞 Support and Troubleshooting

### Common Issues

1. **Encryption Failures**: Check FIPS_ENABLED environment variable
2. **Migration Errors**: Verify source bucket permissions
3. **Audit Log Issues**: Check bucket write permissions
4. **KMS Integration**: Verify key permissions and configuration

### Debug Commands

```bash
# Check vault security status
curl "http://localhost:5000/api/vault/security-status"

# View audit logs
curl "http://localhost:5000/api/vault/audit-logs"

# Test vault health
curl "http://localhost:5000/api/vault/health"
```

## 🔐 Production Deployment

### Security Checklist

- [ ] FIPS-140-2 mode enabled
- [ ] KMS key configured (optional)
- [ ] Audit logging enabled
- [ ] Lifecycle policies configured
- [ ] Access controls implemented
- [ ] Monitoring and alerting configured
- [ ] Incident response procedures documented

### Compliance Validation

- [ ] FIPS-140-2 cryptographic validation
- [ ] Audit log completeness verification
- [ ] Access control effectiveness testing
- [ ] Retention policy enforcement validation
- [ ] Encryption coverage verification

---

*This vault system provides enterprise-grade security with FIPS-140-2 compliance for sensitive document storage and management.*
