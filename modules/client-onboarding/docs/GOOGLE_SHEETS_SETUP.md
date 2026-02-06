# Google Sheets Setup Guide

This guide explains how to configure Google Sheets for persistent data storage in the Client Onboarding application.

## Overview

The application uses Google Sheets as a lightweight database for storing:
- Enquiries
- Sponsors
- Onboardings
- Persons & Person Roles
- Screenings
- Risk Assessments
- Audit Log

## Prerequisites

1. Google Cloud Platform (GCP) account
2. A Google Sheets spreadsheet to use as the database
3. GCP project with Google Sheets API enabled

## Step 1: Create a GCP Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Note your project ID

## Step 2: Enable Google Sheets API

1. In the GCP Console, go to **APIs & Services > Library**
2. Search for "Google Sheets API"
3. Click **Enable**

## Step 3: Create a Service Account

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > Service Account**
3. Enter a name (e.g., "client-onboarding-sheets")
4. Click **Create and Continue**
5. Skip role assignment (not needed for Sheets)
6. Click **Done**

## Step 4: Generate Service Account Key

1. In the Credentials page, click on your new service account
2. Go to the **Keys** tab
3. Click **Add Key > Create new key**
4. Select **JSON** format
5. Click **Create**
6. Save the downloaded JSON file securely

## Step 5: Create the Spreadsheet

1. Go to [Google Sheets](https://sheets.google.com/)
2. Create a new blank spreadsheet
3. Name it (e.g., "Client Onboarding Database")
4. Note the spreadsheet ID from the URL:
   ```
   https://docs.google.com/spreadsheets/d/[SPREADSHEET_ID]/edit
   ```

## Step 6: Share Spreadsheet with Service Account

1. Open your spreadsheet
2. Click **Share**
3. Add the service account email (found in the JSON key file, looks like `name@project-id.iam.gserviceaccount.com`)
4. Set permission to **Editor**
5. Click **Share**

## Step 7: Configure Environment Variables

Set the following environment variables:

### Option A: Base64-encoded credentials (Recommended for deployment)

```bash
# Encode the JSON key file
cat path/to/service-account-key.json | base64 -w 0 > encoded_creds.txt

# Set environment variable
export GOOGLE_SHEETS_CREDENTIALS=$(cat encoded_creds.txt)
export GOOGLE_SHEET_ID=your_spreadsheet_id_here
```

### Option B: File path (For local development)

```bash
export GOOGLE_SHEETS_CREDENTIALS_FILE=/path/to/service-account-key.json
export GOOGLE_SHEET_ID=your_spreadsheet_id_here
```

## Step 8: Verify Setup

Run the application and check the logs:

```bash
python app.py
```

If configured correctly, you should see:
```
INFO - SheetsDB initialized with spreadsheet ID: your_spreadsheet_id
INFO - Google Sheets connection established
```

If credentials are missing, you'll see:
```
INFO - SheetsDB running in DEMO MODE - no credentials configured
```

## Schema Initialization

On first run with valid credentials, the application automatically:
1. Creates all required sheets (tabs) if they don't exist
2. Adds header rows with column definitions
3. Optionally seeds initial demo data

### Sheet Structure

| Sheet | Columns |
|-------|---------|
| Config | key, value, updated_at |
| Enquiries | enquiry_id, sponsor_name, fund_name, contact_name, contact_email, ... |
| Sponsors | sponsor_id, legal_name, entity_type, jurisdiction, registration_number, ... |
| Onboardings | onboarding_id, enquiry_id, sponsor_id, fund_name, current_phase, status, ... |
| Persons | person_id, full_name, nationality, dob, country_of_residence, ... |
| PersonRoles | role_id, person_id, sponsor_id, onboarding_id, role_type, ... |
| Screenings | screening_id, person_id, onboarding_id, screening_type, result, ... |
| RiskAssessments | assessment_id, onboarding_id, risk_score, risk_rating, ... |
| AuditLog | log_id, timestamp, user, action, entity_type, entity_id, details |

## Troubleshooting

### "Demo Mode" message despite credentials

- Verify the service account email has Editor access to the spreadsheet
- Check that the spreadsheet ID is correct
- Ensure the JSON key file is valid and not expired

### "Permission denied" errors

- Re-share the spreadsheet with the service account email
- Verify the service account has the correct role in GCP

### "API not enabled" errors

- Go to GCP Console and enable the Google Sheets API
- Wait a few minutes for the change to propagate

## Security Best Practices

1. **Never commit credentials** to version control
2. **Use environment variables** for all sensitive configuration
3. **Rotate keys regularly** - delete and create new service account keys periodically
4. **Limit access** - only share spreadsheets with necessary service accounts
5. **Monitor access** - review GCP audit logs for unusual activity

## Production Deployment

For production deployments:

1. Use a dedicated GCP project
2. Enable audit logging
3. Set up monitoring and alerts
4. Consider using Secret Manager for credentials
5. Implement regular backups of the spreadsheet data
