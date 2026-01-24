# Invoice Payment Tracker

macOS application for automated invoice processing and payment tracking with Google Sheets integration.

## Features

1. **Invoice Processing**
   - PDF invoice upload and OCR extraction
   - Automated data extraction (supplier, amounts, dates)
   - Manual review and editing interface

2. **Google Sheets Integration**
   - Two-tab tracker: Invoice Tracker + Payment Details
   - Automatic data synchronization
   - Real-time updates

3. **Payment Management**
   - Banking information tracking
   - Export-ready format for banking platforms
   - Status tracking and workflow management

## Tech Stack

- **Backend**: Python 3.9+, Flask
- **Invoice OCR**: Anthropic Claude API
- **Google Integration**: Google Sheets API v4
- **Frontend**: HTML/CSS/JavaScript (Bootstrap)
- **Packaging**: PyInstaller (for macOS app)

## Prerequisites

### 1. Python Environment
- Python 3.9 or higher
- pip package manager

### 2. Google Cloud Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project
3. Enable Google Sheets API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download credentials as `credentials.json`

### 3. Anthropic API
1. Sign up at [Anthropic Console](https://console.anthropic.com)
2. Create an API key
3. Note: Pay-as-you-go pricing applies

## Installation

### 1. Clone/Download Project
```bash
mkdir invoice-tracker
cd invoice-tracker
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure API Keys

Create `.env` file:
```bash
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GOOGLE_SHEET_ID=your_google_sheet_id_here
```

Place your `credentials.json` file in the project root.

### 4. Initialize Google Sheets
```bash
python setup_sheets.py
```

This will:
- Authenticate with Google
- Create or verify your Payment Tracker spreadsheet
- Set up the two-tab structure

## Development Usage

### Run Development Server
```bash
python app.py
```

Access at: http://localhost:5000

### Process an Invoice
1. Upload PDF invoice via web interface
2. Review extracted data
3. Edit if needed
4. Save to Google Sheets

## Project Structure

```
invoice-tracker/
├── app.py                  # Main Flask application
├── invoice_processor.py    # Invoice OCR logic
├── sheets_manager.py       # Google Sheets integration
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (not in git)
├── credentials.json        # Google OAuth credentials (not in git)
├── token.json             # Google auth token (auto-generated)
├── templates/             # HTML templates
│   ├── index.html
│   ├── upload.html
│   └── review.html
├── static/                # CSS, JS, images
│   ├── css/
│   └── js/
└── README.md             # This file
```

## Building macOS App

```bash
pyinstaller --onefile --windowed --name "Invoice Tracker" app.py
```

The app will be in `dist/Invoice Tracker.app`

## Cost Estimates

### Anthropic API
- ~$0.003 per invoice (Claude Sonnet 4)
- 100 invoices/month = ~$0.30/month

### Google Cloud
- Sheets API: Free for up to 60 queries/minute
- Storage: Free for small datasets

Total estimated cost: **< $1/month** for typical usage

## Security Notes

- Never commit `.env`, `credentials.json`, or `token.json` to git
- Store credentials securely
- Use environment variables for production
- Restrict Google OAuth scopes to minimum required

## Troubleshooting

### "Module not found" error
```bash
pip install -r requirements.txt
```

### Google authentication fails
- Delete `token.json`
- Re-run authentication flow
- Check credentials.json is valid

### Invoice extraction inaccurate
- Ensure PDF is text-based (not scanned image)
- Try higher quality scan if using images
- Manually review and edit extracted data

## Support

For issues or questions:
- Check the troubleshooting section above
- Review Google Sheets API documentation
- Check Anthropic API status

## License

Private use only
