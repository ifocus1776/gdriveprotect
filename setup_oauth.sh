#!/bin/bash

echo "Setting up OAuth 2.0 for Google Drive access..."
echo ""

echo "1. Go to Google Cloud Console: https://console.cloud.google.com/"
echo "2. Navigate to APIs & Services > Credentials"
echo "3. Click 'Create Credentials' > 'OAuth 2.0 Client IDs'"
echo "4. Choose 'Desktop application'"
echo "5. Download the JSON file"
echo ""

echo "Once you have the OAuth 2.0 credentials JSON file:"
echo "1. Place it in this directory as 'oauth_credentials.json'"
echo "2. Run: docker run -p 5000:5000 \\"
echo "   -e GOOGLE_CLOUD_PROJECT=ifocus-innovations \\"
echo "   -v \$(pwd)/oauth_credentials.json:/app/oauth_credentials.json:ro \\"
echo "   -e GOOGLE_APPLICATION_CREDENTIALS=/app/oauth_credentials.json \\"
echo "   gdriveprotect"
echo ""

echo "This will allow the application to access your personal Google Drive files."
