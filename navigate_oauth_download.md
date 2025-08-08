# 🔍 How to Download OAuth Client Credentials from Google Cloud Console

## Step-by-Step Navigation Guide

### 1. 🌐 Access Google Cloud Console
- Go to: https://console.cloud.google.com
- Make sure you're signed in with your `ifocusinnovations.com` account
- Select the `ifocus-innovations` project

### 2. 📍 Navigate to Credentials
- In the left sidebar, click **"APIs & Services"**
- Click **"Credentials"**
- You should see a list of all your credentials

### 3. 🔍 Find Your OAuth Client ID
- Look for an entry named: **"GDriveProtect Enterprise - ifocusinnovations.com"**
- If you don't see it, you may need to create it first

### 4. 📥 Download the JSON File
- Click on the **OAuth client ID** name (it will be a clickable link)
- In the details page, look for **"Download JSON"** button
- If you don't see a download button, try these alternatives:

#### Alternative 1: Create New OAuth Client ID
1. Click **"+ CREATE CREDENTIALS"** at the top
2. Select **"OAuth client ID"**
3. Choose **"Web application"** as application type
4. Name it: **"GDriveProtect Enterprise - ifocusinnovations.com"**
5. Add authorized origins: `http://localhost:5000`
6. Add redirect URIs: `http://localhost:5000/oauth2callback`
7. Click **"Create"**
8. You should see a popup with the client ID and secret
9. Click **"Download JSON"** in the popup

#### Alternative 2: Check Different Sections
- Look in the **"OAuth 2.0 Client IDs"** section
- Check if there are multiple pages of credentials
- Use the search box to find "GDriveProtect" or "ifocusinnovations"

### 5. 💾 Save the File
- Save the downloaded file as: `ifocusinnovations-oauth-client.json`
- Replace the existing template file

## 🔧 If You Can't Find the Download Button

### Option A: Manual Creation
If you can't find the download button, you can manually create the JSON file:

```json
{
  "web": {
    "client_id": "YOUR_ACTUAL_CLIENT_ID.apps.googleusercontent.com",
    "project_id": "ifocus-innovations",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "YOUR_ACTUAL_CLIENT_SECRET",
    "redirect_uris": [
      "http://localhost:5000/oauth2callback"
    ],
    "javascript_origins": [
      "http://localhost:5000"
    ]
  }
}
```

### Option B: Use gcloud CLI
```bash
# List OAuth clients
gcloud auth list

# Get application default credentials
gcloud auth application-default login
```

## 🆘 Still Having Trouble?

If you can't find the download button or the OAuth client ID:

1. **Check if you're in the right project**: Look at the project selector at the top
2. **Check if you have the right permissions**: You need "Editor" or "Owner" role
3. **Try creating a new OAuth client ID**: Sometimes it's easier to create fresh
4. **Check the browser console**: Press F12 and look for any errors

## 📞 Need More Help?

Let me know:
- What you see in the Credentials page
- Any error messages
- Whether you can see the OAuth client ID
- What happens when you click on it
