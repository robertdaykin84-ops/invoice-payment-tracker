# Fund Admin Tools

A suite of tools for fund administration operations, featuring AI-powered automation and Google Sheets integration.

## Overview

This monorepo contains multiple tools designed to streamline fund administration workflows:

| Tool | Description | Status |
|------|-------------|--------|
| [Invoice Tracker](./packages/invoice-tracker/) | Automated invoice processing with AI extraction and Google Sheets sync | ✅ Active |
| [Shared Utilities](./packages/shared/) | Common utilities across all tools | 🚧 In Progress |

## Repository Structure

```
fund-admin-tools/
├── packages/
│   ├── invoice-tracker/     # Invoice processing application
│   └── shared/              # Shared utilities and components
├── docs/                    # Documentation and process flows
│   └── fund_admin_processes.drawio
├── .gitignore
└── README.md
```

## Quick Start

### Invoice Tracker

```bash
cd packages/invoice-tracker
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

See [Invoice Tracker README](./packages/invoice-tracker/README.md) for detailed setup instructions.

## Planned Tools

Based on our [fund administration process flows](./docs/fund_admin_processes.drawio):

- **Capital Call Manager** - Automate capital call calculations and investor notifications
- **Distribution Processor** - Handle fund distributions with waterfall calculations
- **NAV Calculator** - Net Asset Value calculations and capital account statements
- **KYC/AML Tracker** - Investor onboarding and compliance tracking
- **Static Data Manager** - Centralized investor and fund data management

## Tech Stack

- **Backend**: Python, Flask
- **AI**: Claude API for document processing
- **Integration**: Google Sheets API
- **Deployment**: Render

## Documentation

Process flow diagrams are available in the `docs/` folder and can be viewed with [draw.io](https://app.diagrams.net/).

## Contributing

1. Create a feature branch from `main`
2. Make changes in the appropriate package
3. Submit a pull request

## License

Private - All rights reserved.
