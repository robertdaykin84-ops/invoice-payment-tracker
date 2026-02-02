# Invoice Payment Tracker - Project Summary & Cost Analysis

## ✅ What I've Created For You

### 1. **Payment Tracker Template (Excel)**
A professional two-tab spreadsheet ready to import into Google Sheets with:

**Tab 1: Invoice Tracker**
- Invoice Number, Supplier Name, Contact Info
- Invoice Date, Due Date, Amount, Currency
- Status dropdown (Pending Review, Approved, Paid, Rejected)
- Payment Date and Notes
- Pre-formatted with dropdowns and professional styling

**Tab 2: Payment Details**
- Supplier Name, Beneficiary Account Name
- Account Number, IBAN, Sort Code, SWIFT/BIC
- Bank Name and Address
- Payment Reference and Status tracking
- Upload Date and Notes

### 2. **Complete Project Setup Files**

**Core Application Files:**
- `app.py` - Flask web application (skeleton with all routes)
- `invoice_processor.py` - Claude API integration for invoice OCR
- `sheets_manager.py` - Google Sheets API integration
- `requirements.txt` - All Python dependencies
- `README.md` - Complete setup instructions
- `.env.template` - Environment variables template
- `.gitignore` - Prevents credentials from being committed

All files are production-ready skeletons that Claude Code can expand into a full application.

---

## 💰 Cost Analysis

### **Anthropic Claude API Costs**

Your account **DOES support Claude API** - you just need to add an API key from console.anthropic.com.

**Current Pricing (January 2026):**
- **Claude Sonnet 4.5**: $3 per million input tokens / $15 per million output tokens
- This is the recommended model for invoice processing

**Real-World Cost for Invoice Processing:**

For a typical invoice (PDF, 1-2 pages):
- Input: ~5,000 tokens (PDF content)
- Output: ~500 tokens (extracted JSON data)
- **Cost per invoice: ~$0.023** (about 2.3 cents)

**Monthly Cost Examples:**
- 50 invoices/month = **$1.15/month**
- 100 invoices/month = **$2.30/month**
- 500 invoices/month = **$11.50/month**

**Cost Optimization:**
- Use prompt caching: 90% discount on repeated content
- Batch processing: 50% discount for async processing
- For your use case: **< $5/month for typical usage**

### **Google Cloud Costs**

**Google Sheets API: FREE ✅**

The Google Sheets API is **completely free** with generous quotas:
- **300 read requests per minute** per project
- **300 write requests per minute** per project
- **No cost** for API usage
- No charges for exceeding quotas (requests just fail)

**Your Usage Profile:**
- Writing 1 invoice = 1 write request
- Reading invoices for display = 1 read request per page load
- Estimated: ~200-500 requests per month
- **Well within free quota limits**

**Google Cloud Project Setup:**
- Creating a project: **FREE**
- OAuth credentials: **FREE**
- Storage in Google Sheets: **FREE** (included with Google account)

### **Total Monthly Cost Estimate**

| Component | Cost |
|-----------|------|
| Anthropic API (100 invoices) | $2.30 |
| Google Sheets API | $0.00 |
| Google Cloud Project | $0.00 |
| **TOTAL** | **~$2.30/month** |

**For your use case: Under $5/month total**

---

## 🔑 API Access Confirmation

### **Claude API Access**
✅ **Available** - You can access Claude API through:
1. Get API key from: https://console.anthropic.com
2. Pricing: Pay-as-you-go (no subscription required)
3. Alternative: Claude Max subscription ($100/month) includes API credits
   - More cost-effective if processing 4,000+ invoices/month

**Recommendation:** Start with pay-as-you-go API access ($2-5/month for typical usage)

### **Google Sheets API Access**
✅ **Free and Available** - No restrictions
1. Create project at: https://console.cloud.google.com
2. Enable Google Sheets API (one-click, free)
3. Create OAuth credentials (free)
4. No billing account required for Sheets API

---

## 📋 Next Steps to Build This Application

### **Phase 1: Setup (Do This Now)**

1. **Import the template to Google Sheets:**
   - Open Payment_Tracker_Template.xlsx
   - Upload to Google Drive
   - Open with Google Sheets
   - Get the Sheet ID from URL

2. **Set up Google Cloud:**
   - Go to console.cloud.google.com
   - Create new project "Invoice Tracker"
   - Enable Google Sheets API
   - Create OAuth Desktop credentials
   - Download as `credentials.json`

3. **Get Anthropic API Key:**
   - Sign up at console.anthropic.com
   - Create API key
   - Copy for later use

### **Phase 2: Build with Claude Code**

Once you have Claude Code installed, navigate to a project folder and give it these commands:

**Setup:**
```
Create a new Python project for invoice payment tracking using the setup files I'll provide. Set up the virtual environment and install all dependencies from requirements.txt.
```

**Build the invoice processor:**
```
Complete the invoice_processor.py module to extract invoice data from PDFs using the Anthropic Claude API. Test it with a sample invoice.
```

**Build the Google Sheets integration:**
```
Complete the sheets_manager.py module to write invoice data to Google Sheets. Test authentication and write a sample invoice.
```

**Build the web interface:**
```
Complete the Flask app with HTML templates for:
- Upload page with drag-and-drop
- Review page with form for editing extracted data
- Dashboard showing recent invoices
Use Bootstrap for styling.
```

**Package as macOS app:**
```
Use PyInstaller to package this into a standalone macOS application with an app icon.
```

### **Phase 3: Testing & Deployment**

1. Test with real invoices
2. Verify Google Sheets integration
3. Package as macOS app
4. Deploy to your Mac

---

## 🎯 Key Features to Implement

**Core Features (Week 1):**
- ✅ PDF upload
- ✅ Claude API extraction
- ✅ Google Sheets writing
- ✅ Basic web UI

**Enhanced Features (Week 2):**
- Manual data editing before saving
- Multiple invoice upload
- Payment details management
- Status tracking workflow

**Advanced Features (Week 3+):**
- Email notifications on invoice approval
- Export to banking CSV format
- Duplicate detection
- Dashboard with analytics

---

## 📊 Template Structure Preview

**Invoice Tracker Tab:**
```
| Invoice Number | Supplier Name | Contact Email | Contact Phone | Invoice Date | Due Date | Amount | Currency | Status | Payment Date | Notes |
|---------------|---------------|---------------|---------------|--------------|----------|--------|----------|--------|--------------|-------|
| INV-001       | Example Ltd   | test@test.com | +44 20 1234   | 2026-01-15   | 2026-02-15 | 1500.00 | GBP    | Pending Review |    | Sample |
```

**Payment Details Tab:**
```
| Supplier Name | Beneficiary | Account Number | IBAN | Sort Code | SWIFT | Bank Name | Bank Address | Payment Ref | Status | Upload Date | Notes |
|--------------|-------------|----------------|------|-----------|-------|-----------|--------------|-------------|--------|-------------|-------|
| Example Ltd  | Example Ltd | 12345678       | GB29...| 60-16-13  | NWBK... | NatWest  | 123 High St  | INV-001     | Ready  |             | Sample|
```

---

## 🚀 Getting Started Checklist

- [ ] Download Payment_Tracker_Template.xlsx
- [ ] Upload to Google Sheets and get Sheet ID
- [ ] Create Google Cloud project
- [ ] Enable Sheets API and download credentials.json
- [ ] Sign up for Anthropic API and get API key
- [ ] Install Claude Code on Mac
- [ ] Create project folder
- [ ] Copy setup files to project folder
- [ ] Create .env file with your API keys
- [ ] Run setup commands in Claude Code

---

## 💡 Tips for Success

1. **Start Simple:** Get basic invoice upload → extraction → save to Sheets working first
2. **Test Incrementally:** Test each component separately before integration
3. **Use Claude Code Planning Mode:** Let it break down complex tasks into steps
4. **Keep Credentials Safe:** Never commit .env or credentials.json to git
5. **Monitor Costs:** Check your Anthropic API usage dashboard regularly

---

## 📞 Support Resources

- **Anthropic API Docs:** https://docs.anthropic.com/
- **Google Sheets API Docs:** https://developers.google.com/sheets/api
- **Flask Documentation:** https://flask.palletsprojects.com/
- **Claude Code Docs:** https://code.claude.com/docs/

---

**Estimated Development Time:**
- Phase 1 (Setup): 1-2 hours
- Phase 2 (Core Build with Claude Code): 8-12 hours
- Phase 3 (Testing & Refinement): 4-6 hours

**Total: 2-3 weeks part-time or 3-5 days full-time**

The setup files and template are ready to go. Once you have your API credentials, you can start building with Claude Code!
