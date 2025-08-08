# Scan Status Guide

## Overview

The GDriveProtect application now includes comprehensive scan status tracking to help you monitor which files have been scanned for sensitive data and their results.

## Scan Status Features

### 1. File Listing with Scan Status

When you list files from your Google Drive, each file now includes scan status information:

```json
{
  "name": "Google Cloud OAuth",
  "scan_eligible": true,
  "scan_reason": "File eligible for scanning",
  "scan_status": {
    "status": "not_scanned",  // or "clean", "sensitive_data_found", "error"
    "findings_count": 0,
    "scan_timestamp": null,
    "last_scan": null
  }
}
```

**Scan Status Values:**
- `not_scanned`: File has not been scanned yet
- `clean`: File was scanned and no sensitive data was found
- `sensitive_data_found`: File was scanned and sensitive data was detected
- `error`: Error occurred while checking scan status

### 2. Scan Status Endpoints

#### Get All Scan Status
```bash
GET /api/dlp/status
```

Returns comprehensive scan status for all scanned files with statistics.

#### Get Specific File Scan Status
```bash
GET /api/dlp/status/{file_id}
```

Returns detailed scan status for a specific file.

#### Get Scan Dashboard
```bash
GET /api/dlp/dashboard
```

Returns comprehensive dashboard with:
- Overview statistics
- Recent activity (last 7 days)
- Files with most findings
- Scan trends

### 3. Scan a File

To scan a file for sensitive data:

```bash
POST /api/dlp/scan
Content-Type: application/json

{
  "file_id": "your_file_id_here"
}
```

### 4. Batch Scan Multiple Files

```bash
POST /api/dlp/scan/batch
Content-Type: application/json

{
  "file_ids": ["file_id_1", "file_id_2", "file_id_3"]
}
```

## How to Use

### 1. Check File Scan Status

1. **List your Drive files** with scan status:
   ```bash
   curl "http://localhost:5000/api/drive/files?max_results=10"
   ```

2. **Check specific file scan status**:
   ```bash
   curl "http://localhost:5000/api/dlp/status/{file_id}"
   ```

### 2. Scan Files for Sensitive Data

1. **Scan a single file**:
   ```bash
   curl -X POST "http://localhost:5000/api/dlp/scan" \
     -H "Content-Type: application/json" \
     -d '{"file_id": "your_file_id"}'
   ```

2. **Scan multiple files**:
   ```bash
   curl -X POST "http://localhost:5000/api/dlp/scan/batch" \
     -H "Content-Type: application/json" \
     -d '{"file_ids": ["file1", "file2", "file3"]}'
   ```

### 3. Monitor Scan Activity

1. **View scan dashboard**:
   ```bash
   curl "http://localhost:5000/api/dlp/dashboard"
   ```

2. **Get all scan status**:
   ```bash
   curl "http://localhost:5000/api/dlp/status"
   ```

## Sensitive Data Types Detected

The scanner looks for:
- Person names
- Email addresses
- Phone numbers
- US Social Security numbers
- Credit card numbers
- US Driver's license numbers
- US Passport numbers
- Date of birth
- Medical record numbers
- Bank routing numbers
- IBAN codes
- SWIFT codes

## Scan Results Storage

Scan results are stored in Google Cloud Storage and include:
- File metadata
- Scan timestamp
- Findings count
- Detailed findings with locations
- Risk assessment

## Web Interface

Access the web interface at `http://localhost:5000` to:
- View your Drive files with scan status
- Trigger scans manually
- Monitor scan activity
- View scan results and statistics

## Troubleshooting

### No Scan Results Bucket Error
If you see "bucket does not exist" errors, this is normal when no files have been scanned yet. The bucket will be created automatically when you scan your first file.

### Authentication Issues
Make sure your application default credentials have the necessary scopes:
- `https://www.googleapis.com/auth/drive`
- `https://www.googleapis.com/auth/cloud-platform`

### File Access Issues
Ensure the files you're trying to scan are accessible and in supported formats (Google Docs, PDF, Word, Excel, etc.).
