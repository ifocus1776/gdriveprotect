#!/bin/bash

# 🏢 GDriveProtect Enterprise OAuth Setup for ifocusinnovations.com
# This script helps you create and configure OAuth client ID for your domain

echo "🔐 Setting up OAuth Client ID for ifocusinnovations.com domain"
echo "================================================================"

# Check if we're in the right project
CURRENT_PROJECT=$(gcloud config get-value project)
echo "📋 Current Google Cloud Project: $CURRENT_PROJECT"

if [ "$CURRENT_PROJECT" != "ifocus-innovations" ]; then
    echo "⚠️  Warning: You're not in the ifocus-innovations project"
    echo "   Run: gcloud config set project ifocus-innovations"
    echo ""
fi

echo ""
echo "📝 Manual Steps Required:"
echo "=========================="
echo ""
echo "1. 🌐 Go to Google Cloud Console:"
echo "   https://console.cloud.google.com/apis/credentials"
echo ""
echo "2. 🔧 Create OAuth Client ID:"
echo "   - Click '+ CREATE CREDENTIALS' → 'OAuth client ID'"
echo "   - Application type: Web application"
echo "   - Name: 'GDriveProtect Enterprise - ifocusinnovations.com'"
echo ""
echo "3. 🌍 Configure Authorized Origins:"
echo "   - http://localhost:5000 (development)"
echo "   - https://your-production-domain.com (production)"
echo ""
echo "4. 🔗 Configure Redirect URIs:"
echo "   - http://localhost:5000/oauth2callback (development)"
echo "   - https://your-production-domain.com/oauth2callback (production)"
echo ""
echo "5. 💾 Download Configuration:"
echo "   - Download the JSON file"
echo "   - Save as 'ifocusinnovations-oauth-client.json'"
echo ""
echo "6. 🏢 Google Workspace Admin Setup:"
echo "   - Go to admin.google.com"
echo "   - Security → API Controls"
echo "   - Enable Domain-wide Delegation"
echo "   - Add the new client ID"
echo ""
echo "7. 🔑 Configure OAuth Scopes:"
echo "   Add these scopes to the client ID:"
echo "   - https://www.googleapis.com/auth/drive"
echo "   - https://www.googleapis.com/auth/drive.readonly"
echo "   - https://www.googleapis.com/auth/drive.metadata.readonly"
echo "   - https://www.googleapis.com/auth/drive.file"
echo "   - https://www.googleapis.com/auth/cloud-platform"
echo ""

# Check if we have the current OAuth credentials
if [ -f "oauth_credentials.json" ]; then
    echo "📄 Current OAuth credentials found:"
    echo "   - File: oauth_credentials.json"
    echo "   - This is for personal use, not enterprise"
    echo ""
fi

# Check if we have the enterprise service account
if [ -f "enterprise-service-account-key.json" ]; then
    echo "✅ Enterprise service account found:"
    echo "   - File: enterprise-service-account-key.json"
    echo "   - Service Account: gdriveprotect-enterprise@ifocus-innovations.iam.gserviceaccount.com"
    echo ""
fi

echo "🚀 After completing the manual steps above:"
echo "=========================================="
echo ""
echo "1. Test the new OAuth client:"
echo "   curl -s 'http://localhost:5000/api/drive/files' | jq ."
echo ""
echo "2. Update the application configuration:"
echo "   - Replace oauth_credentials.json with ifocusinnovations-oauth-client.json"
echo "   - Update Dockerfile if needed"
echo ""
echo "3. Rebuild and test:"
echo "   docker build -t gdriveprotect-ifocusinnovations ."
echo "   docker run -d --name gdriveprotect-ifocusinnovations -p 5000:5000 gdriveprotect-ifocusinnovations"
echo ""

echo "📞 Need help? Check the ENTERPRISE_SETUP_GUIDE.md for detailed instructions."

