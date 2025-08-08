# 🔧 Enable Enterprise APIs for User Management

## Required APIs to Enable

To use the enterprise user management features, you need to enable these APIs in your Google Cloud project:

### 1. **Admin SDK API** (Required for user listing)
- **API Name**: Admin SDK API
- **Enable URL**: https://console.developers.google.com/apis/api/admin.googleapis.com/overview?project=336289541710
- **Purpose**: List users in your Google Workspace domain

### 2. **Google Drive API** (Already enabled)
- **API Name**: Google Drive API
- **Purpose**: Access user Drive files

### 3. **Google Cloud DLP API** (Already enabled)
- **API Name**: Cloud Data Loss Prevention API
- **Purpose**: Scan files for sensitive data

### 4. **Google Cloud Storage API** (Already enabled)
- **API Name**: Cloud Storage API
- **Purpose**: Store scan results

## 🔧 **Step-by-Step API Enablement:**

### Step 1: Enable Admin SDK API
1. Go to: https://console.developers.google.com/apis/api/admin.googleapis.com/overview?project=336289541710
2. Click **"Enable"**
3. Wait 2-3 minutes for the API to be fully activated

### Step 2: Verify API Enablement
```bash
# Test the user discovery endpoint
curl -s http://localhost:5000/api/drive/users/discover | jq .
```

### Step 3: Configure Domain-Wide Delegation
1. Go to [admin.google.com](https://admin.google.com)
2. Navigate to **Security** → **API Controls** → **Domain-wide Delegation**
3. Add your service account client ID: `113021175819574837213`
4. Configure these OAuth scopes:
   ```
   https://www.googleapis.com/auth/drive
   https://www.googleapis.com/auth/drive.readonly
   https://www.googleapis.com/auth/drive.metadata.readonly
   https://www.googleapis.com/auth/drive.file
   https://www.googleapis.com/auth/admin.directory.user.readonly
   https://www.googleapis.com/auth/cloud-platform
   ```

## 🧪 **Testing the Enterprise Features:**

### Test 1: Discover Active Users
```bash
curl -s http://localhost:5000/api/drive/users/discover | jq .
```

### Test 2: List Domain Users
```bash
curl -s http://localhost:5000/api/drive/users | jq .
```

### Test 3: Access Specific User's Files
```bash
# Replace with actual user email
curl -s "http://localhost:5000/api/drive/files/kevin@ifocusinnovations.com" | jq .
```

### Test 4: Bulk User Scan
```bash
curl -X POST http://localhost:5000/api/drive/scan/bulk \
  -H "Content-Type: application/json" \
  -d '{"users": ["kevin@ifocusinnovations.com"]}' | jq .
```

## 📊 **Expected Results:**

After enabling the APIs and configuring domain-wide delegation, you should see:

### User Discovery Response:
```json
{
  "active_users": [
    {
      "email": "kevin@ifocusinnovations.com",
      "name": "Kevin Griesmar",
      "lastLoginTime": "2025-08-08T22:00:00.000Z",
      "creationTime": "2023-01-01T00:00:00.000Z"
    }
  ],
  "total_users": 1,
  "status": "success"
}
```

### User Files Response:
```json
{
  "files": [
    {
      "id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
      "name": "Sample Document",
      "mimeType": "application/vnd.google-apps.document"
    }
  ],
  "total": 1
}
```

## 🚀 **Next Steps:**

1. **Enable the Admin SDK API** using the link above
2. **Wait 2-3 minutes** for the API to activate
3. **Test the endpoints** using the curl commands above
4. **Configure domain-wide delegation** in Google Workspace Admin
5. **Test user impersonation** with specific user emails

## 🔒 **Security Notes:**

- **Admin SDK Access**: Requires super admin privileges in Google Workspace
- **User Consent**: Users should be informed about scanning policies
- **Audit Logging**: All access attempts are logged for compliance
- **Rate Limiting**: Implement rate limiting to avoid API quotas

## 📞 **Need Help?**

If you encounter issues:
1. Check that the Admin SDK API is enabled
2. Verify domain-wide delegation is configured
3. Ensure the service account has the correct permissions
4. Check the application logs for detailed error messages
