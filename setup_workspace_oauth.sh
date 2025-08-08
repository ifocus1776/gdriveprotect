#!/bin/bash

# 🏢 GDriveProtect Workspace OAuth Setup
# This script helps you integrate the new OAuth client ID for ifocusinnovations.com

echo "🔐 Setting up Workspace OAuth Client for ifocusinnovations.com"
echo "================================================================"

# Check current files
echo "📁 Current OAuth files:"
ls -la *oauth*.json 2>/dev/null || echo "No OAuth files found"

echo ""
echo "🔧 Steps to complete the setup:"
echo "================================"
echo ""

echo "1. 📥 Download OAuth Client Credentials:"
echo "   - Go to: https://console.cloud.google.com/apis/credentials"
echo "   - Find your OAuth client ID for 'GDriveProtect Enterprise - ifocusinnovations.com'"
echo "   - Download the JSON file"
echo ""

echo "2. 💾 Save the credentials:"
echo "   - Save the downloaded file as 'ifocusinnovations-oauth-client.json'"
echo "   - Replace the template with real values"
echo ""

echo "3. 🏢 Configure Google Workspace Admin:"
echo "   - Go to: https://admin.google.com"
echo "   - Security → API Controls → Domain-wide Delegation"
echo "   - Add your OAuth client ID (not service account ID)"
echo "   - Configure OAuth scopes:"
echo "     https://www.googleapis.com/auth/drive"
echo "     https://www.googleapis.com/auth/drive.readonly"
echo "     https://www.googleapis.com/auth/drive.metadata.readonly"
echo "     https://www.googleapis.com/auth/drive.file"
echo "     https://www.googleapis.com/auth/cloud-platform"
echo ""

echo "4. 🔄 Update Application:"
echo "   - The Dockerfile is already configured to use the new OAuth client"
echo "   - The application code supports OAuth client credentials"
echo ""

echo "5. 🚀 Rebuild and Test:"
echo "   - Stop current container: docker stop gdriveprotect-enterprise"
echo "   - Remove old container: docker rm gdriveprotect-enterprise"
echo "   - Build new image: docker build -t gdriveprotect-workspace ."
echo "   - Run new container: docker run -d --name gdriveprotect-workspace -p 5000:5000 gdriveprotect-workspace"
echo ""

# Check if we have the real OAuth client file
if [ -f "ifocusinnovations-oauth-client.json" ]; then
    echo "📄 Current ifocusinnovations-oauth-client.json content:"
    echo "=================================================="
    cat ifocusinnovations-oauth-client.json | head -10
    echo ""
    
    # Check if it has real values or template values
    if grep -q "YOUR_NEW_CLIENT_ID" ifocusinnovations-oauth-client.json; then
        echo "⚠️  WARNING: Still using template values!"
        echo "   Please replace with real OAuth client credentials"
        echo ""
    else
        echo "✅ OAuth client file appears to have real values"
        echo ""
    fi
fi

echo "🔍 Current container status:"
docker ps -a | grep gdriveprotect || echo "No gdriveprotect containers found"

echo ""
echo "📞 Ready to proceed? Run this script again after updating the OAuth client file."
