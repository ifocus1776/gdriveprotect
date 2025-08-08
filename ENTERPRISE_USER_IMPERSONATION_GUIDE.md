# 🏢 Enterprise User Impersonation Guide
## How to Target Specific End Users in Google Workspace

### Overview
When you have many users in your Google Workspace domain, you need to specify which user's Drive you want to access. There are several approaches:

## 🔧 **Method 1: User Impersonation (Recommended)**

### Step 1: Configure Domain-Wide Delegation
1. **Google Workspace Admin Console**:
   - Go to [admin.google.com](https://admin.google.com)
   - Navigate to **Security** → **API Controls** → **Domain-wide Delegation**
   - Add your service account client ID: `113021175819574837213`
   - Configure these OAuth scopes:
   ```
   https://www.googleapis.com/auth/drive
   https://www.googleapis.com/auth/drive.readonly
   https://www.googleapis.com/auth/drive.metadata.readonly
   https://www.googleapis.com/auth/drive.file
   https://www.googleapis.com/auth/cloud-platform
   ```

### Step 2: Implement User Impersonation in Code
The service account can impersonate any user in your domain. Here's how to modify the code:

```python
# In src/routes/drive_monitor.py
def _init_drive_service(self, target_user=None):
    """Initialize Google Drive API service with user impersonation"""
    try:
        credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if credentials_path and os.path.exists(credentials_path):
            with open(credentials_path, 'r') as f:
                cred_data = json.load(f)
            
            if 'type' in cred_data and cred_data['type'] == 'service_account':
                # Create base service account credentials
                base_credentials = service_account.Credentials.from_service_account_file(
                    credentials_path,
                    scopes=[
                        'https://www.googleapis.com/auth/drive',
                        'https://www.googleapis.com/auth/drive.readonly',
                        'https://www.googleapis.com/auth/drive.metadata.readonly',
                        'https://www.googleapis.com/auth/drive.file'
                    ]
                )
                
                # If target user is specified, impersonate that user
                if target_user:
                    from google.auth import impersonated_credentials
                    target_credentials = impersonated_credentials.Credentials(
                        source_credentials=base_credentials,
                        target_principal=target_user,
                        target_scopes=[
                            'https://www.googleapis.com/auth/drive',
                            'https://www.googleapis.com/auth/drive.readonly',
                            'https://www.googleapis.com/auth/drive.metadata.readonly',
                            'https://www.googleapis.com/auth/drive.file'
                        ]
                    )
                    self.drive_service = build('drive', 'v3', credentials=target_credentials)
                    logger.info(f"Impersonating user: {target_user}")
                else:
                    # Use service account directly (for admin operations)
                    self.drive_service = build('drive', 'v3', credentials=base_credentials)
                    logger.info("Using service account directly")
```

### Step 3: Add User Selection API Endpoints
```python
@drive_bp.route('/users', methods=['GET'])
def list_domain_users():
    """List all users in the domain"""
    try:
        # Use Admin SDK to list users
        admin_service = build('admin', 'directory_v1', credentials=base_credentials)
        users = admin_service.users().list(domain='ifocusinnovations.com').execute()
        return jsonify({
            'users': users.get('users', []),
            'status': 'success'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@drive_bp.route('/files/<user_email>', methods=['GET'])
def list_user_files(user_email):
    """List files for a specific user"""
    try:
        # Initialize drive service with user impersonation
        drive_monitor = DriveMonitor()
        drive_monitor._init_drive_service(target_user=user_email)
        
        files = drive_monitor.list_drive_files()
        return jsonify(files)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

## 🔧 **Method 2: Admin Console User Selection**

### Step 1: Create Admin Interface
Add an admin interface to select which user to scan:

```html
<!-- In src/static/index.html -->
<div class="admin-panel">
    <h3>Enterprise User Selection</h3>
    <select id="userSelect">
        <option value="">Select User</option>
        <option value="kevin@ifocusinnovations.com">kevin@ifocusinnovations.com</option>
        <option value="admin@ifocusinnovations.com">admin@ifocusinnovations.com</option>
        <!-- More users -->
    </select>
    <button onclick="scanUserDrive()">Scan User Drive</button>
</div>

<script>
async function scanUserDrive() {
    const userEmail = document.getElementById('userSelect').value;
    if (!userEmail) {
        alert('Please select a user');
        return;
    }
    
    const response = await fetch(`/api/drive/files/${userEmail}`, {
        method: 'GET'
    });
    const data = await response.json();
    displayFiles(data);
}
</script>
```

## 🔧 **Method 3: Bulk User Scanning**

### Step 1: Implement Bulk Scanning
```python
@drive_bp.route('/scan/bulk', methods=['POST'])
def bulk_user_scan():
    """Scan multiple users' drives"""
    try:
        data = request.get_json()
        users = data.get('users', [])
        results = {}
        
        for user_email in users:
            try:
                # Initialize drive service for this user
                drive_monitor = DriveMonitor()
                drive_monitor._init_drive_service(target_user=user_email)
                
                # Get user's files
                files = drive_monitor.list_drive_files()
                
                # Scan each file
                scan_results = []
                for file in files.get('files', []):
                    scan_result = scan_file_with_dlp(file, user_email)
                    scan_results.append(scan_result)
                
                results[user_email] = {
                    'files_found': len(files.get('files', [])),
                    'sensitive_files': len([r for r in scan_results if r.get('findings_count', 0) > 0]),
                    'scan_results': scan_results
                }
                
            except Exception as e:
                results[user_email] = {'error': str(e)}
        
        return jsonify({
            'bulk_scan_results': results,
            'status': 'success'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

## 🔧 **Method 4: Automated User Discovery**

### Step 1: Implement User Discovery
```python
@drive_bp.route('/users/discover', methods=['GET'])
def discover_active_users():
    """Discover active users in the domain"""
    try:
        admin_service = build('admin', 'directory_v1', credentials=base_credentials)
        
        # Get all users
        users = admin_service.users().list(
            domain='ifocusinnovations.com',
            maxResults=500
        ).execute()
        
        active_users = []
        for user in users.get('users', []):
            if user.get('suspended') != True:  # Only active users
                active_users.append({
                    'email': user.get('primaryEmail'),
                    'name': user.get('name', {}).get('fullName'),
                    'lastLoginTime': user.get('lastLoginTime'),
                    'creationTime': user.get('creationTime')
                })
        
        return jsonify({
            'active_users': active_users,
            'total_users': len(active_users),
            'status': 'success'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

## 🔧 **Method 5: Scheduled User Scanning**

### Step 1: Implement Scheduled Scanning
```python
@drive_bp.route('/schedule/scan', methods=['POST'])
def schedule_user_scan():
    """Schedule scanning for specific users"""
    try:
        data = request.get_json()
        users = data.get('users', [])
        schedule = data.get('schedule', 'daily')  # daily, weekly, monthly
        
        # Store schedule in database or Cloud Scheduler
        for user_email in users:
            schedule_scan_job(user_email, schedule)
        
        return jsonify({
            'message': f'Scheduled scanning for {len(users)} users',
            'schedule': schedule,
            'status': 'success'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def schedule_scan_job(user_email, schedule):
    """Schedule a Cloud Scheduler job for user scanning"""
    # Implementation for Google Cloud Scheduler
    pass
```

## 🔧 **Method 6: User Permission-Based Access**

### Step 1: Implement Permission Checking
```python
@drive_bp.route('/users/permissions', methods=['GET'])
def check_user_permissions():
    """Check what users the service account can access"""
    try:
        admin_service = build('admin', 'directory_v1', credentials=base_credentials)
        
        # Get users with specific criteria
        users = admin_service.users().list(
            domain='ifocusinnovations.com',
            query='isAdmin=false'  # Only non-admin users
        ).execute()
        
        accessible_users = []
        for user in users.get('users', []):
            try:
                # Test if we can access this user's drive
                drive_monitor = DriveMonitor()
                drive_monitor._init_drive_service(target_user=user.get('primaryEmail'))
                
                # Try to list files (this will fail if no access)
                files = drive_monitor.list_drive_files()
                
                accessible_users.append({
                    'email': user.get('primaryEmail'),
                    'name': user.get('name', {}).get('fullName'),
                    'accessible': True,
                    'files_count': len(files.get('files', []))
                })
                
            except Exception:
                # User not accessible
                accessible_users.append({
                    'email': user.get('primaryEmail'),
                    'name': user.get('name', {}).get('fullName'),
                    'accessible': False,
                    'files_count': 0
                })
        
        return jsonify({
            'accessible_users': accessible_users,
            'total_accessible': len([u for u in accessible_users if u['accessible']]),
            'status': 'success'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

## 🚀 **Implementation Steps:**

### 1. **Update the Application Code**
Add the user impersonation functionality to your existing code.

### 2. **Configure Google Workspace Admin**
Set up domain-wide delegation with the correct scopes.

### 3. **Test with a Single User**
Start by testing with one user to ensure impersonation works.

### 4. **Scale to Multiple Users**
Implement bulk scanning and user management features.

### 5. **Add Monitoring and Logging**
Track which users are being scanned and when.

## 📊 **Best Practices:**

1. **User Consent**: Ensure users are aware their drives are being scanned
2. **Rate Limiting**: Implement rate limiting to avoid API quotas
3. **Error Handling**: Handle cases where users don't exist or are suspended
4. **Audit Logging**: Log all access attempts for compliance
5. **Security**: Ensure only authorized admins can trigger scans

## 🔒 **Security Considerations:**

- **Principle of Least Privilege**: Only scan users who need to be scanned
- **Audit Trails**: Log all scanning activities
- **User Notification**: Inform users about scanning policies
- **Data Retention**: Define how long scan results are kept
- **Access Controls**: Limit who can trigger scans

Would you like me to implement any of these methods in your current application?
