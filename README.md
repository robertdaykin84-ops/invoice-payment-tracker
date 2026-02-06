# CoreWorker Tools

A modular platform for fund administration operations, featuring AI-powered automation and Google Sheets integration.

## Modules

| Module | Description | Status |
|--------|-------------|--------|
| [Invoice Tracker](./modules/invoice-tracker/) | Automated invoice processing with AI extraction and Google Sheets sync | Live (Render) |
| [Client Onboarding](./modules/client-onboarding/) | JFSC-compliant 7-phase client onboarding with KYC/CDD document review | Development |
| [Welcome Terminal](./modules/welcome-terminal/) | Visitor management and reception system | Planning |
| [Shared](./modules/shared/) | Common utilities across all modules | Planned |

## Repository Structure

```
coreworker-tools/
├── docs/
│   ├── design/              # Architecture diagrams (draw.io)
│   ├── guides/              # Setup guides (Google Drive, Sheets)
│   ├── plans/               # Design & implementation plans per module
│   └── testing/             # Test reports and summaries
├── modules/
│   ├── invoice-tracker/     # Flask app - deployed on Render
│   ├── client-onboarding/   # Flask app - 7-phase onboarding workflow
│   ├── shared/              # Shared Python utilities
│   └── welcome-terminal/    # Planned module
└── README.md
```

## Quick Start

### Invoice Tracker

```bash
cd modules/invoice-tracker
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

See [Invoice Tracker README](./modules/invoice-tracker/README.md) for full setup.

### Client Onboarding

```bash
cd modules/client-onboarding
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
DEMO_MODE=true python app.py
```

See [Client Onboarding README](./modules/client-onboarding/README.md) for full setup.

## Tech Stack

- **Backend**: Python, Flask
- **AI**: Claude API (document processing, risk analysis)
- **Database**: Google Sheets API
- **Storage**: Google Drive API (audit trail)
- **Deployment**: Render

## Documentation

- [Design diagrams](./docs/design/) - Process flows viewable with [draw.io](https://app.diagrams.net/)
- [Setup guides](./docs/guides/) - Google Drive and Sheets configuration
- [Implementation plans](./docs/plans/) - Design and implementation docs per module

## Contributing

1. Create a feature branch from `main`
2. Make changes in the appropriate module
3. Submit a pull request

## License

Private - All rights reserved.
