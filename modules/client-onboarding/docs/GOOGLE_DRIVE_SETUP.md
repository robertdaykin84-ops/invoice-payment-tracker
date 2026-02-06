# Google Drive Setup Guide

This guide explains how to configure Google Drive for document storage and audit trail in the Client Onboarding application.

## Overview

The application uses Google Drive to store:
- Form submissions (JSON audit records)
- Screening results
- Generated PDF reports
- Uploaded documents (certificates, IDs, etc.)
- Compliance documentation

## Prerequisites

1. Google Cloud Platform (GCP) account
2. GCP project with Google Drive API enabled
3. OAuth 2.0 credentials (Desktop application type)

## Step 1: Enable Google Drive API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (or create one)
3. Go to **APIs & Services > Library**
4. Search for "Google Drive API"
5. Click **Enable**

## Step 2: Create OAuth 2.0 Credentials

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth client ID**
3. If prompted, configure the OAuth consent screen:
   - User Type: Internal (for organization) or External (for testing)
   - App name: "Client Onboarding"
   - Support email: your email
   - Scopes: Add `https://www.googleapis.com/auth/drive.file`
4. For Application type, select **Desktop app**
5. Name it (e.g., "Client Onboarding Drive")
6. Click **Create**
7. Download the JSON credentials file

## Step 3: Configure Credentials Path

Place the credentials file in one of these locations:

### Default Path (Recommended)
```bash
mkdir -p ~/.config/mcp
cp downloaded-credentials.json ~/.config/mcp/gdrive-credentials.json
```

### Custom Path (via environment variable)
```bash
export GDRIVE_CREDENTIALS_PATH=/path/to/your/credentials.json
export GDRIVE_TOKEN_PATH=/path/to/store/token.json
```

## Step 4: First-Time Authorization

On first run, the application will:
1. Detect missing token
2. Open a browser window for Google OAuth consent
3. Ask you to sign in and grant access
4. Save the token for future use

```bash
python app.py
# Browser opens automatically
# Sign in and click "Allow"
# Token saved to ~/.config/mcp/gdrive-token.json
```

## Step 5: Verify Setup

Check the logs for successful connection:

```
INFO - GoogleDriveAuditClient initialized
INFO - Google Drive connection established
```

If credentials are missing:
```
INFO - GoogleDriveAuditClient running in DEMO MODE
```

## Folder Structure

The application automatically creates this folder hierarchy:

```
Client-Onboarding/
└── [Sponsor Name] - [Fund Name]/
    ├── _COMPLIANCE/          # Key compliance documents
    ├── Phase-1-Enquiry/      # Phase 1 form data
    ├── Phase-2-Sponsor/      # Phase 2 CDD documents
    ├── Phase-3-Fund/         # Fund structure documents
    ├── Phase-4-Screening/    # Screening results
    ├── Phase-5-EDD/          # Enhanced due diligence
    ├── Phase-6-Approval/     # Approval records
    ├── Phase-7-Commercial/   # Commercial terms
    ├── API-Responses/        # API call logs
    └── Screenshots/          # Evidence screenshots
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GDRIVE_CREDENTIALS_PATH` | `~/.config/mcp/gdrive-credentials.json` | OAuth client secrets |
| `GDRIVE_TOKEN_PATH` | `~/.config/mcp/gdrive-token.json` | OAuth token storage |

## OAuth Scopes

The application requests minimal scopes:
- `https://www.googleapis.com/auth/drive.file` - Access only files created by the app

This means the application can only:
- Create new files and folders
- Read/modify files it created
- Cannot access your other Drive files

## Troubleshooting

### "Demo Mode" despite credentials

1. Verify credentials file exists at the configured path
2. Check file permissions: `chmod 600 ~/.config/mcp/gdrive-*.json`
3. Delete token file and re-authorize: `rm ~/.config/mcp/gdrive-token.json`

### "Access blocked" during authorization

1. If using "External" user type, add your email as a test user
2. Go to OAuth consent screen > Test users > Add users

### Token expired

The application automatically refreshes tokens. If issues persist:
```bash
rm ~/.config/mcp/gdrive-token.json
# Restart app and re-authorize
```

### "Quota exceeded" errors

1. Check API quotas in GCP Console
2. Implement exponential backoff (already built-in)
3. Consider upgrading to a paid tier

## Security Best Practices

1. **Protect credentials files**
   ```bash
   chmod 600 ~/.config/mcp/gdrive-*.json
   ```

2. **Use separate accounts** for development and production

3. **Regularly audit access** - review which files the app has created

4. **Enable audit logging** in GCP for production deployments

5. **Don't share tokens** - each user should authorize separately

## Production Deployment

For server deployments without interactive browser:

### Option 1: Pre-authorize locally
1. Run authorization on a local machine
2. Copy the token file to the server
3. Ensure token file has correct permissions

### Option 2: Service Account (Advanced)
1. Create a service account with Drive API access
2. Share a specific Drive folder with the service account
3. Use service account credentials instead of OAuth
4. Note: Requires code modification to use service account auth

### Option 3: Use Google Workspace domain-wide delegation
1. Configure domain-wide delegation in GCP
2. Allow the service account to impersonate users
3. Best for enterprise deployments

## Demo Mode Behavior

When running in demo mode (no credentials):
- File uploads return mock folder/file IDs
- Operations are logged but not persisted
- Useful for development and testing
- No actual files created in Drive

## API Reference

The application provides these Drive operations:

| Function | Description |
|----------|-------------|
| `ensure_folder_structure()` | Create client folder hierarchy |
| `save_form_data()` | Save form submission as JSON |
| `save_screening_results()` | Save screening results |
| `save_json_audit()` | Save arbitrary JSON audit record |
| `upload_document()` | Upload binary file (PDF, images) |
