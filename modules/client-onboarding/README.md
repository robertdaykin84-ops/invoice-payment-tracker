# Client Onboarding System

JFSC-compliant client onboarding for Jersey fund administration, powered by CoreWorker AI.

## Overview

This application provides a workflow-driven onboarding system for PE House sponsors setting up Jersey Private Funds (JPFs). It ensures compliance with JFSC AML/CFT requirements while streamlining the client experience.

## Features

- **8-Phase Wizard Workflow**: Enquiry → Sponsor → Fund Structure → Screening → EDD → Approval → Commercial → Complete
- **Multi-Entity Support**: Individual, Company, LP, Trust, Foundation
- **Existing Sponsor Detection**: Streamlined trigger event review for approved sponsors
- **Role-Based Access**: BD, Compliance, MLRO, Admin
- **AI-Powered Features**: Document extraction, risk scoring, memo generation
- **JFSC Compliance**: Built-in compliance mapping and audit trail

## Quick Start

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Run the application
python app.py
```

The application will be available at `http://localhost:5001`

## Demo Mode

The application runs in demo mode by default (`DEMO_MODE=true`), which:
- Provides sample user accounts for each role
- Includes mock onboarding data
- Allows quick role switching for testing

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key | Auto-generated |
| `DEMO_MODE` | Enable demo mode | `true` |
| `PORT` | Application port | `5001` |
| `FLASK_ENV` | Environment (development/production) | `development` |
| `GOOGLE_SHEET_ID` | Google Sheets database ID | - |
| `ANTHROPIC_API_KEY` | Claude API key for AI features | - |

## Project Structure

```
client-onboarding/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── Procfile              # Render deployment config
├── templates/
│   ├── base.html         # Base template with CoreWorker branding
│   ├── dashboard.html    # Main dashboard
│   ├── login.html        # User login/role selection
│   ├── approvals.html    # MLRO approval queue
│   ├── onboarding/
│   │   ├── new.html      # New/Existing sponsor selection
│   │   ├── phase1.html   # Initial enquiry form
│   │   └── trigger_review.html  # Existing sponsor review
│   └── errors/
│       ├── 404.html
│       └── 500.html
├── static/
│   ├── css/
│   │   └── style.css     # CoreWorker design system
│   └── js/
│       └── main.js       # Client-side functionality
├── services/             # Service modules (Google Sheets, AI)
├── routes/               # Route blueprints
└── utils/                # Utility functions
```

## User Roles

| Role | Description | Capabilities |
|------|-------------|--------------|
| Business Development | Client acquisition | Intake, enquiries, commercial |
| Compliance Analyst | Due diligence | CDD, screening, standard approvals |
| MLRO | Compliance oversight | All approvals, high-risk review |
| Admin | System management | Configuration, user management |

## JFSC Compliance

This system is designed to comply with:
- Money Laundering (Jersey) Order 2008
- JFSC AML/CFT/CPF Handbook
- Fund Services Business Code of Practice
- Jersey Private Fund requirements

## Documentation

See the [design document](../../docs/plans/2026-02-02-client-onboarding-design.md) for detailed specifications.

## License

Private - All rights reserved.
