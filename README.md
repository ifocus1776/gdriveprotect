# Google Drive Sensitive Data Scanner (GDriveProtect)

A comprehensive Google Cloud application that automatically scans Google Drive files for sensitive data types (PII, SPII, SSN, credit card numbers) and securely stores identified sensitive documents in an encrypted vault.

## 🔍 Features

- **Automated Sensitive Data Detection**: Uses Google Cloud DLP API to identify PII, SSN, credit card numbers, and other sensitive data
- **Secure Vault Storage**: Automatically moves sensitive documents to encrypted Cloud Storage with customer-managed keys
- **Real-time Monitoring**: Monitors Google Drive changes and triggers automatic scans
- **Compliance Ready**: Built with GDPR and HIPAA compliance considerations
- **Comprehensive API**: RESTful API for integration with existing systems
- **Web Dashboard**: Simple web interface for monitoring and management

## 🏗️ Architecture

The application follows a serverless, event-driven architecture using Google Cloud Platform services:

- **Google Drive API**: File access and change monitoring
- **Google Cloud DLP API**: Sensitive data detection and classification
- **Cloud Storage**: Secure vault for sensitive documents
- **Cloud KMS**: Customer-managed encryption keys
- **Flask Application**: RESTful API and web interface

## 🚀 Quick Start

### Prerequisites

1. Google Cloud Project with billing enabled
2. Service account with appropriate permissions
3. Python 3.11+ and pip

### Installation

1. Clone the repository:
```bash
git clone https://github.com/ifocus1776/gdriveprotect.git
cd gdriveprotect
```

2. Set up virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account.json"
export SCAN_RESULTS_BUCKET="your-scan-results-bucket"
export VAULT_BUCKET="your-vault-bucket"
export KMS_KEY_NAME="projects/your-project/locations/global/keyRings/your-ring/cryptoKeys/your-key"
```

5. Run the application:
```bash
python src/main.py
```

The application will be available at `http://localhost:5000`

## 📚 API Documentation

### DLP Scanner Endpoints

- `POST /api/dlp/scan` - Scan a specific file for sensitive data
- `POST /api/dlp/scan/batch` - Scan multiple files
- `GET /api/dlp/results/{file_id}` - Get scan results for a file
- `GET /api/dlp/health` - Health check

### Drive Monitor Endpoints

- `POST /api/drive/scan/trigger` - Trigger manual scan
- `GET /api/drive/files` - List Google Drive files
- `GET /api/drive/files/{file_id}` - Get file information
- `POST /api/drive/setup-notifications` - Set up push notifications
- `GET /api/drive/health` - Health check

### Vault Manager Endpoints

- `POST /api/vault/store` - Store document in vault
- `GET /api/vault/retrieve/{vault_path}` - Retrieve document from vault
- `GET /api/vault/list` - List vault documents
- `DELETE /api/vault/delete/{vault_path}` - Delete document from vault
- `GET /api/vault/statistics` - Get vault statistics
- `GET /api/vault/health` - Health check

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_CLOUD_PROJECT` | Google Cloud Project ID | Yes |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON | Yes |
| `SCAN_RESULTS_BUCKET` | Bucket for storing scan results | Yes |
| `VAULT_BUCKET` | Bucket for secure document storage | Yes |
| `KMS_KEY_NAME` | Cloud KMS key for encryption | Optional |
| `SCAN_REQUEST_TOPIC` | Pub/Sub topic for scan requests | Optional |

### Google Cloud Setup

1. **Enable APIs**:
   - Google Drive API
   - Cloud Data Loss Prevention (DLP) API
   - Cloud Storage API
   - Cloud Key Management Service (KMS) API
   - Cloud Pub/Sub API

2. **Create Service Account**:
   ```bash
   gcloud iam service-accounts create drive-scanner \
     --display-name="Drive Scanner Service Account"
   ```

3. **Grant Permissions**:
   ```bash
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:drive-scanner@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/dlp.user"
   
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:drive-scanner@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/storage.admin"
   ```

4. **Create Storage Buckets**:
   ```bash
   gsutil mb gs://your-scan-results-bucket
   gsutil mb gs://your-vault-bucket
   ```

## 🔒 Security Features

- **Encryption at Rest**: All vault documents encrypted with customer-managed keys
- **Encryption in Transit**: TLS/SSL for all communications
- **Access Control**: IAM-based permissions with principle of least privilege
- **Audit Logging**: Comprehensive logging of all access and operations
- **Data Retention**: Configurable retention policies for compliance

## 📊 Supported Data Types

The application can detect the following types of sensitive data:

- **Personal Information**: Names, email addresses, phone numbers
- **Government IDs**: Social Security Numbers, Driver's License Numbers, Passport Numbers
- **Financial Data**: Credit card numbers, bank routing numbers, IBAN codes
- **Healthcare Data**: Medical record numbers, dates of birth
- **Custom Patterns**: Configurable detection patterns

## 🧪 Testing

Run the test suite:
```bash
python -m pytest tests/
```

## 📈 Monitoring and Logging

The application provides comprehensive monitoring through:

- Health check endpoints for all services
- Structured logging with Google Cloud Logging
- Metrics and monitoring through Google Cloud Monitoring
- Audit trails for all sensitive data operations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:

- Create an issue in the GitHub repository
- Check the documentation in the `/docs` folder
- Review the API documentation at `/api/docs` when running the application

## 🔄 Deployment

### Google Cloud Run

1. Build and deploy:
```bash
gcloud run deploy drive-scanner \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Docker

1. Build image:
```bash
docker build -t drive-scanner .
```

2. Run container:
```bash
docker run -p 5000:5000 \
  -e GOOGLE_CLOUD_PROJECT=your-project \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json \
  -v /path/to/credentials.json:/app/credentials.json \
  drive-scanner
```

## 📋 Roadmap

- [ ] Advanced de-identification options
- [ ] Integration with more cloud storage providers
- [ ] Machine learning-based custom pattern detection
- [ ] Advanced reporting and analytics dashboard
- [ ] Multi-tenant support
- [ ] API rate limiting and throttling
- [ ] Webhook notifications for scan results

---

**Note**: This application handles sensitive data. Ensure proper security measures and compliance with relevant regulations in your jurisdiction.

