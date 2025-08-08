# DLP Scanner Customization Guide

## Overview

The Google Drive Protect DLP scanner can be customized to detect various types of sensitive data. This guide explains how to modify what the scanner searches for and what is considered sensitive data.

## 🔧 Current Configuration

### Standard Info Types
The scanner currently detects these standard Google DLP info types:

- **Personal Information**: `PERSON_NAME`, `EMAIL_ADDRESS`, `PHONE_NUMBER`, `DATE_OF_BIRTH`
- **Financial Data**: `CREDIT_CARD_NUMBER`, `US_BANK_ROUTING_MICR`, `IBAN_CODE`, `SWIFT_CODE`
- **Government IDs**: `US_SOCIAL_SECURITY_NUMBER`, `US_DRIVERS_LICENSE_NUMBER`, `US_PASSPORT`
- **Medical Data**: `MEDICAL_RECORD_NUMBER`
- **Tax Information**: `US_INDIVIDUAL_TAXPAYER_IDENTIFICATION_NUMBER`, `US_EMPLOYER_IDENTIFICATION_NUMBER`

### Custom Info Types
The scanner also includes custom detection patterns:

- **Employee IDs**: `CUSTOM_EMPLOYEE_ID` - Detects patterns like `EMP-123456`
- **Internal References**: `CUSTOM_INTERNAL_REFERENCE` - Detects patterns like `REF-1234-5678`
- **API Keys**: `CUSTOM_API_KEY` - Detects 32+ character alphanumeric strings
- **IP Addresses**: `CUSTOM_IP_ADDRESS` - Detects IPv4 addresses
- **Database Connections**: `CUSTOM_DATABASE_CONNECTION` - Detects connection strings

## 🛠️ How to Customize

### 1. Add Custom Detection Patterns

Use the API to add custom patterns:

```bash
curl -X POST "http://localhost:5000/api/dlp/config/custom-patterns" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "company_project_code",
    "pattern": "PROJ-[A-Z]{2}-\\d{4}",
    "likelihood": "LIKELY",
    "window_before": 10,
    "window_after": 10
  }'
```

### 2. Modify Sensitivity Levels

Change the minimum likelihood threshold:

```bash
curl -X POST "http://localhost:5000/api/dlp/config/sensitivity" \
  -H "Content-Type: application/json" \
  -d '{
    "min_likelihood": "LIKELY"
  }'
```

Available levels: `VERY_UNLIKELY`, `UNLIKELY`, `POSSIBLE`, `LIKELY`, `VERY_LIKELY`

### 3. View Current Configuration

Check the current DLP settings:

```bash
curl "http://localhost:5000/api/dlp/config"
```

### 4. View Available Info Types

See all available detection types:

```bash
curl "http://localhost:5000/api/dlp/config/info-types"
```

## 📝 Custom Pattern Examples

### Company-Specific Patterns

```json
{
  "name": "employee_badge",
  "pattern": "BADGE-\\d{6}",
  "likelihood": "LIKELY"
}
```

```json
{
  "name": "project_id",
  "pattern": "PRJ-[A-Z]{3}-\\d{4}",
  "likelihood": "POSSIBLE"
}
```

```json
{
  "name": "internal_api_key",
  "pattern": "sk-[a-zA-Z0-9]{32,}",
  "likelihood": "VERY_LIKELY"
}
```

### Financial Patterns

```json
{
  "name": "account_number",
  "pattern": "\\b\\d{10,12}\\b",
  "likelihood": "LIKELY"
}
```

```json
{
  "name": "swift_code",
  "pattern": "[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?",
  "likelihood": "LIKELY"
}
```

### Technical Patterns

```json
{
  "name": "aws_access_key",
  "pattern": "AKIA[0-9A-Z]{16}",
  "likelihood": "VERY_LIKELY"
}
```

```json
{
  "name": "private_key",
  "pattern": "-----BEGIN PRIVATE KEY-----",
  "likelihood": "VERY_LIKELY"
}
```

## 🔍 Pattern Validation

All custom patterns are validated as valid regex expressions. The system will reject invalid patterns with helpful error messages.

## 📊 Configuration Management

### Web Interface
- Click "⚙️ DLP Config" button to view current settings
- See available info types and custom patterns
- Monitor configuration changes

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/dlp/config` | GET | Get current DLP configuration |
| `/api/dlp/config/custom-patterns` | POST | Add custom detection pattern |
| `/api/dlp/config/info-types` | GET | List available info types |
| `/api/dlp/config/sensitivity` | POST | Update sensitivity level |

## 🎯 Best Practices

### 1. Start Conservative
- Begin with `POSSIBLE` likelihood
- Test patterns thoroughly before production
- Monitor false positives

### 2. Use Specific Patterns
- Avoid overly broad patterns that cause false positives
- Include context words when possible
- Use proximity rules for better accuracy

### 3. Regular Review
- Periodically review detection results
- Adjust patterns based on findings
- Remove obsolete patterns

### 4. Security Considerations
- Don't include actual sensitive data in patterns
- Use test data for pattern development
- Log pattern changes for audit purposes

## 🔧 Advanced Customization

### Modify Source Code

To add permanent custom patterns, edit `src/routes/dlp_scanner.py`:

```python
def get_custom_info_types(self):
    return [
        # Add your custom patterns here
        {
            "infoType": {"name": "YOUR_CUSTOM_TYPE"},
            "likelihood": "LIKELY",
            "detectionRule": {
                "hotwordRule": {
                    "hotwordRegex": {"pattern": r"YOUR_PATTERN"},
                    "proximity": {
                        "windowBefore": 10,
                        "windowAfter": 10
                    }
                }
            }
        }
    ]
```

### Environment Variables

Set custom configuration via environment variables:

```bash
export DLP_MIN_LIKELIHOOD=LIKELY
export DLP_MAX_FINDINGS=200
export DLP_INCLUDE_CUSTOM_TYPES=true
```

## 🚀 Testing Custom Patterns

### 1. Test with Sample Data
Create test files with your patterns and scan them:

```bash
# Create test file
echo "Employee ID: EMP-123456" > test_file.txt

# Scan the file
curl -X POST "http://localhost:5000/api/dlp/scan" \
  -H "Content-Type: application/json" \
  -d '{"file_id": "your_file_id"}'
```

### 2. Monitor Results
Check scan results to verify pattern detection:

```bash
curl "http://localhost:5000/api/dlp/status"
```

### 3. Adjust as Needed
Fine-tune patterns based on results and feedback.

## 📈 Performance Considerations

- More patterns = slower scanning
- Complex regex patterns use more CPU
- Consider pattern priority and likelihood levels
- Monitor scan performance and adjust accordingly

## 🔒 Security Notes

- Custom patterns are stored in memory (not persistent)
- For production, implement proper storage and management
- Consider encryption for sensitive pattern definitions
- Implement access controls for pattern management

## 📞 Support

For questions about DLP customization:
1. Check the web interface configuration view
2. Review scan results and patterns
3. Test patterns with sample data
4. Adjust sensitivity levels as needed

---

*This guide covers the basic customization options. For advanced features, refer to the Google Cloud DLP API documentation.*
