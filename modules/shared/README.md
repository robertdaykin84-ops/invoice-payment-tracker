# Shared Utilities

Common utilities and components shared across all fund administration tools.

## Planned Components

- **Authentication**: Google OAuth and API authentication helpers
- **Google Sheets**: Common Sheets integration utilities
- **AI Processing**: Shared AI/Claude integration code
- **Data Models**: Common data structures for fund administration
- **Utilities**: Date formatting, currency handling, validation

## Usage

```python
from shared.auth import get_google_credentials
from shared.sheets import SheetsClient
from shared.utils import format_currency
```

## Structure

```
shared/
├── __init__.py
├── auth.py          # Authentication utilities
├── sheets.py        # Google Sheets helpers
├── ai.py            # AI processing utilities
├── models.py        # Common data models
└── utils.py         # General utilities
```
