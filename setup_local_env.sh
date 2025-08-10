#!/bin/bash

# Manual Environment Variable Setup for Local Testing
# Run this script to set up environment variables, then run the app manually

echo "🔧 Setting up local environment variables..."

# Google Cloud Configuration
export GOOGLE_CLOUD_PROJECT="test-project-id"
export SCAN_RESULTS_BUCKET="test-scan-results-bucket"
export VAULT_BUCKET="test-vault-bucket"
export KMS_KEY_NAME="projects/test-project/locations/global/keyRings/test-ring/cryptoKeys/test-key"

# Vault Configuration
export VAULT_STORAGE_PREFERENCE="hybrid"
export DRIVE_VAULT_FOLDER_NAME="Test Secure Vault"
export USER_TYPE="individual"
export INDIVIDUAL_USER_EMAIL="test@example.com"

# OAuth Configuration
export GOOGLE_CLIENT_ID="test-client-id"
export GOOGLE_CLIENT_SECRET="test-client-secret"

# Flask Configuration
export FLASK_ENV="development"
export FLASK_DEBUG="true"
export SECRET_KEY="test-secret-key-for-local-development"

# Logging
export LOG_LEVEL="DEBUG"

echo "✅ Environment variables set!"
echo ""
echo "Now you can run the application with:"
echo "  python -m flask run --host=0.0.0.0 --port=5000 --debug"
echo ""
echo "Or use the automated script:"
echo "  ./run_local.sh"
echo ""
echo "Health check will be available at: http://localhost:5000/health"
