#!/bin/bash

# Local Development Runner Script
# This script sets up environment variables for local testing

echo "🚀 Starting GDriveProtect for Local Development..."

# Set test environment variables
export GOOGLE_CLOUD_PROJECT="test-project-id"
export SCAN_RESULTS_BUCKET="test-scan-results-bucket"
export VAULT_BUCKET="test-vault-bucket"
export KMS_KEY_NAME="projects/test-project/locations/global/keyRings/test-ring/cryptoKeys/test-key"

# Vault configuration
export VAULT_STORAGE_PREFERENCE="hybrid"
export DRIVE_VAULT_FOLDER_NAME="Test Secure Vault"
export USER_TYPE="individual"
export INDIVIDUAL_USER_EMAIL="test@example.com"

# OAuth test credentials
export GOOGLE_CLIENT_ID="test-client-id"
export GOOGLE_CLIENT_SECRET="test-client-secret"

# Flask configuration
export FLASK_ENV="development"
export FLASK_DEBUG="true"
export SECRET_KEY="test-secret-key-for-local-development"

# Logging
export LOG_LEVEL="DEBUG"

# Create test credentials file if it doesn't exist
if [ ! -f "test-credentials.json" ]; then
    echo "📝 Creating test credentials file..."
    cat > test-credentials.json << EOF
{
  "type": "service_account",
  "project_id": "test-project-id",
  "private_key_id": "test-key-id",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...\n-----END PRIVATE KEY-----\n",
  "client_email": "test-service@test-project-id.iam.gserviceaccount.com",
  "client_id": "123456789",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/test-service%40test-project-id.iam.gserviceaccount.com"
}
EOF
fi

echo "✅ Environment variables set for local testing"
echo "🌐 Starting Flask application..."
echo "📊 Health check available at: http://localhost:5000/health"
echo "🔗 Main application at: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop the application"
echo ""

# Run the Flask application
python -m flask run --host=0.0.0.0 --port=5000 --debug
