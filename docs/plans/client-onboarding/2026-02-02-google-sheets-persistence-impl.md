# Google Sheets Persistence Layer - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace mock data in app.py with Google Sheets persistence using gspread.

**Architecture:** Service-oriented layer (sheets_db.py) with demo mode fallback. All routes call service methods. Seed existing mock data on first run.

**Tech Stack:** gspread, google-auth, Flask, Google Sheets API v4

---

## Task 1: Add gspread dependency

**Files:**
- Modify: `packages/client-onboarding/requirements.txt`

**Step 1: Add gspread to requirements**

Add after the existing Google APIs section:

```
# Google Sheets (gspread)
gspread==6.0.0
```

**Step 2: Verify requirements file is valid**

Run: `cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && pip install -r requirements.txt --dry-run 2>&1 | head -20`

Expected: No errors, shows packages to install

**Step 3: Install dependencies**

Run: `cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && pip install gspread==6.0.0`

Expected: Successfully installed gspread-6.0.0

**Step 4: Commit**

```bash
git add packages/client-onboarding/requirements.txt
git commit -m "feat(client-onboarding): add gspread dependency for Sheets persistence"
```

---

## Task 2: Create SheetsDB service - connection and demo mode

**Files:**
- Create: `packages/client-onboarding/services/sheets_db.py`

**Step 1: Create the service file with connection logic**

```python
"""
Google Sheets Database Service
Provides CRUD operations for client onboarding data with demo mode fallback.
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Singleton instance
_client: Optional['SheetsDB'] = None


class SheetsDB:
    """Google Sheets database service with demo mode fallback."""

    # Tab names
    TAB_CONFIG = 'Config'
    TAB_ENQUIRIES = 'Enquiries'
    TAB_SPONSORS = 'Sponsors'
    TAB_ONBOARDINGS = 'Onboardings'
    TAB_PERSONS = 'Persons'
    TAB_PERSON_ROLES = 'PersonRoles'
    TAB_SCREENINGS = 'Screenings'
    TAB_RISK_ASSESSMENTS = 'RiskAssessments'
    TAB_AUDIT_LOG = 'AuditLog'

    # Column headers for each tab
    SCHEMA = {
        TAB_CONFIG: ['key', 'value', 'updated_at'],
        TAB_ENQUIRIES: [
            'enquiry_id', 'sponsor_name', 'fund_name', 'contact_name', 'contact_email',
            'entity_type', 'jurisdiction', 'registration_number', 'regulatory_status',
            'investment_strategy', 'target_size', 'status', 'notes',
            'created_at', 'created_by'
        ],
        TAB_SPONSORS: [
            'sponsor_id', 'legal_name', 'entity_type', 'jurisdiction',
            'registration_number', 'regulated_status', 'cdd_status', 'created_at'
        ],
        TAB_ONBOARDINGS: [
            'onboarding_id', 'enquiry_id', 'sponsor_id', 'fund_name',
            'current_phase', 'status', 'risk_level', 'assigned_to',
            'is_existing_sponsor', 'created_at', 'updated_at'
        ],
        TAB_PERSONS: [
            'person_id', 'full_name', 'nationality', 'dob',
            'country_of_residence', 'pep_status', 'id_verified', 'created_at'
        ],
        TAB_PERSON_ROLES: [
            'role_id', 'person_id', 'sponsor_id', 'onboarding_id',
            'role_type', 'ownership_pct', 'is_ubo'
        ],
        TAB_SCREENINGS: [
            'screening_id', 'person_id', 'onboarding_id', 'screening_type',
            'result', 'match_details', 'risk_level', 'screened_at', 'screened_by'
        ],
        TAB_RISK_ASSESSMENTS: [
            'assessment_id', 'onboarding_id', 'risk_score', 'risk_rating',
            'risk_factors', 'edd_triggered', 'assessed_at'
        ],
        TAB_AUDIT_LOG: [
            'log_id', 'timestamp', 'user', 'action',
            'entity_type', 'entity_id', 'details'
        ]
    }

    def __init__(self):
        """Initialize the Sheets database connection."""
        self.demo_mode = True
        self.client = None
        self.workbook = None
        self._sheets_cache = {}
        self._connect()

    def _connect(self) -> None:
        """Establish connection to Google Sheets."""
        try:
            import gspread
            from google.oauth2.service_account import Credentials

            # Check for credentials
            creds_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
            creds_file = os.environ.get('GOOGLE_SHEETS_CREDENTIALS_FILE')
            sheet_id = os.environ.get('GOOGLE_SHEET_ID')

            if not (creds_json or creds_file):
                logger.info("SheetsDB: No credentials found, running in demo mode")
                return

            # Load credentials
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]

            if creds_json:
                # Credentials from environment variable (base64 or raw JSON)
                import base64
                try:
                    creds_data = json.loads(base64.b64decode(creds_json))
                except Exception:
                    creds_data = json.loads(creds_json)
                credentials = Credentials.from_service_account_info(creds_data, scopes=scopes)
            else:
                # Credentials from file
                credentials = Credentials.from_service_account_file(creds_file, scopes=scopes)

            self.client = gspread.authorize(credentials)

            # Open or create workbook
            if sheet_id:
                self.workbook = self.client.open_by_key(sheet_id)
                logger.info(f"SheetsDB: Connected to existing workbook: {self.workbook.title}")
            else:
                # Create new workbook
                self.workbook = self.client.create('Client_Onboarding_DB')
                logger.info(f"SheetsDB: Created new workbook: {self.workbook.id}")
                logger.info(f"SheetsDB: Set GOOGLE_SHEET_ID={self.workbook.id} to reuse this workbook")

            self.demo_mode = False
            logger.info("SheetsDB: Connected successfully")

        except ImportError as e:
            logger.warning(f"SheetsDB: gspread not installed: {e}")
        except Exception as e:
            logger.warning(f"SheetsDB: Connection failed, running in demo mode: {e}")

    def _get_sheet(self, tab_name: str):
        """Get or create a worksheet by name."""
        if self.demo_mode:
            return None

        if tab_name in self._sheets_cache:
            return self._sheets_cache[tab_name]

        try:
            sheet = self.workbook.worksheet(tab_name)
        except Exception:
            # Create the sheet with headers
            sheet = self.workbook.add_worksheet(title=tab_name, rows=1000, cols=20)
            headers = self.SCHEMA.get(tab_name, [])
            if headers:
                sheet.update('A1', [headers])
            logger.info(f"SheetsDB: Created tab '{tab_name}' with headers")

        self._sheets_cache[tab_name] = sheet
        return sheet

    def _generate_id(self, prefix: str, sheet) -> str:
        """Generate next ID for a table (e.g., ENQ-001, ONB-002)."""
        if self.demo_mode:
            return f"{prefix}-{datetime.now().strftime('%H%M%S')}"

        try:
            all_values = sheet.col_values(1)  # First column (IDs)
            existing_ids = [v for v in all_values[1:] if v.startswith(prefix)]
            if not existing_ids:
                return f"{prefix}-001"

            # Extract numbers and find max
            nums = [int(id.split('-')[1]) for id in existing_ids if '-' in id]
            next_num = max(nums) + 1 if nums else 1
            return f"{prefix}-{next_num:03d}"
        except Exception:
            return f"{prefix}-{datetime.now().strftime('%H%M%S')}"

    def _row_to_dict(self, headers: list, row: list) -> dict:
        """Convert a row list to a dictionary using headers."""
        result = {}
        for i, header in enumerate(headers):
            result[header] = row[i] if i < len(row) else ''
        return result

    def _dict_to_row(self, headers: list, data: dict) -> list:
        """Convert a dictionary to a row list using headers."""
        return [str(data.get(h, '')) for h in headers]


def get_client() -> SheetsDB:
    """Get or create the singleton SheetsDB instance."""
    global _client
    if _client is None:
        _client = SheetsDB()
    return _client
```

**Step 2: Verify syntax is valid**

Run: `cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && python -c "from services.sheets_db import SheetsDB, get_client; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add packages/client-onboarding/services/sheets_db.py
git commit -m "feat(client-onboarding): add SheetsDB service with connection and demo mode"
```

---

## Task 3: Add Enquiries CRUD methods

**Files:**
- Modify: `packages/client-onboarding/services/sheets_db.py`

**Step 1: Add enquiry methods to SheetsDB class**

Add after `_dict_to_row` method:

```python
    # ==================== ENQUIRIES ====================

    def get_enquiries(self, status: str = None) -> list[dict]:
        """Get all enquiries, optionally filtered by status."""
        if self.demo_mode:
            logger.debug("SheetsDB demo: get_enquiries()")
            return []

        sheet = self._get_sheet(self.TAB_ENQUIRIES)
        records = sheet.get_all_records()

        if status:
            records = [r for r in records if r.get('status') == status]

        return records

    def get_enquiry(self, enquiry_id: str) -> Optional[dict]:
        """Get a single enquiry by ID."""
        if self.demo_mode:
            logger.debug(f"SheetsDB demo: get_enquiry({enquiry_id})")
            return None

        sheet = self._get_sheet(self.TAB_ENQUIRIES)
        records = sheet.get_all_records()

        for record in records:
            if record.get('enquiry_id') == enquiry_id:
                return record
        return None

    def create_enquiry(self, data: dict) -> str:
        """Create a new enquiry. Returns the enquiry_id."""
        sheet = self._get_sheet(self.TAB_ENQUIRIES)
        enquiry_id = self._generate_id('ENQ', sheet)

        data['enquiry_id'] = enquiry_id
        data['created_at'] = datetime.now().isoformat()
        data['status'] = data.get('status', 'pending')

        if self.demo_mode:
            logger.info(f"SheetsDB demo: create_enquiry({enquiry_id})")
            return enquiry_id

        headers = self.SCHEMA[self.TAB_ENQUIRIES]
        row = self._dict_to_row(headers, data)
        sheet.append_row(row)

        self._log_action('create', 'enquiry', enquiry_id, data)
        logger.info(f"SheetsDB: Created enquiry {enquiry_id}")
        return enquiry_id

    def update_enquiry(self, enquiry_id: str, data: dict) -> bool:
        """Update an existing enquiry."""
        if self.demo_mode:
            logger.info(f"SheetsDB demo: update_enquiry({enquiry_id})")
            return True

        sheet = self._get_sheet(self.TAB_ENQUIRIES)

        # Find the row
        cell = sheet.find(enquiry_id, in_column=1)
        if not cell:
            logger.warning(f"SheetsDB: Enquiry {enquiry_id} not found")
            return False

        # Get current row and update
        headers = self.SCHEMA[self.TAB_ENQUIRIES]
        current_row = sheet.row_values(cell.row)
        current_data = self._row_to_dict(headers, current_row)
        current_data.update(data)

        new_row = self._dict_to_row(headers, current_data)
        sheet.update(f'A{cell.row}', [new_row])

        self._log_action('update', 'enquiry', enquiry_id, data)
        logger.info(f"SheetsDB: Updated enquiry {enquiry_id}")
        return True
```

**Step 2: Verify syntax**

Run: `cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && python -c "from services.sheets_db import get_client; c = get_client(); print('Methods:', hasattr(c, 'get_enquiries'), hasattr(c, 'create_enquiry'))"`

Expected: `Methods: True True`

**Step 3: Commit**

```bash
git add packages/client-onboarding/services/sheets_db.py
git commit -m "feat(client-onboarding): add Enquiries CRUD methods to SheetsDB"
```

---

## Task 4: Add Sponsors CRUD methods

**Files:**
- Modify: `packages/client-onboarding/services/sheets_db.py`

**Step 1: Add sponsor methods after enquiry methods**

```python
    # ==================== SPONSORS ====================

    def get_sponsors(self) -> list[dict]:
        """Get all sponsors."""
        if self.demo_mode:
            logger.debug("SheetsDB demo: get_sponsors()")
            return []

        sheet = self._get_sheet(self.TAB_SPONSORS)
        return sheet.get_all_records()

    def get_sponsor(self, sponsor_id: str) -> Optional[dict]:
        """Get a single sponsor by ID."""
        if self.demo_mode:
            logger.debug(f"SheetsDB demo: get_sponsor({sponsor_id})")
            return None

        sheet = self._get_sheet(self.TAB_SPONSORS)
        records = sheet.get_all_records()

        for record in records:
            if record.get('sponsor_id') == sponsor_id:
                return record
        return None

    def get_sponsor_by_name(self, legal_name: str) -> Optional[dict]:
        """Get a sponsor by legal name (for deduplication)."""
        if self.demo_mode:
            return None

        sheet = self._get_sheet(self.TAB_SPONSORS)
        records = sheet.get_all_records()

        for record in records:
            if record.get('legal_name', '').lower() == legal_name.lower():
                return record
        return None

    def create_sponsor(self, data: dict) -> str:
        """Create a new sponsor. Returns the sponsor_id."""
        sheet = self._get_sheet(self.TAB_SPONSORS)
        sponsor_id = self._generate_id('SPO', sheet)

        data['sponsor_id'] = sponsor_id
        data['created_at'] = datetime.now().isoformat()
        data['cdd_status'] = data.get('cdd_status', 'pending')

        if self.demo_mode:
            logger.info(f"SheetsDB demo: create_sponsor({sponsor_id})")
            return sponsor_id

        headers = self.SCHEMA[self.TAB_SPONSORS]
        row = self._dict_to_row(headers, data)
        sheet.append_row(row)

        self._log_action('create', 'sponsor', sponsor_id, data)
        logger.info(f"SheetsDB: Created sponsor {sponsor_id}")
        return sponsor_id

    def update_sponsor(self, sponsor_id: str, data: dict) -> bool:
        """Update an existing sponsor."""
        if self.demo_mode:
            logger.info(f"SheetsDB demo: update_sponsor({sponsor_id})")
            return True

        sheet = self._get_sheet(self.TAB_SPONSORS)
        cell = sheet.find(sponsor_id, in_column=1)
        if not cell:
            return False

        headers = self.SCHEMA[self.TAB_SPONSORS]
        current_row = sheet.row_values(cell.row)
        current_data = self._row_to_dict(headers, current_row)
        current_data.update(data)

        new_row = self._dict_to_row(headers, current_data)
        sheet.update(f'A{cell.row}', [new_row])

        self._log_action('update', 'sponsor', sponsor_id, data)
        return True
```

**Step 2: Verify syntax**

Run: `cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && python -c "from services.sheets_db import get_client; c = get_client(); print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add packages/client-onboarding/services/sheets_db.py
git commit -m "feat(client-onboarding): add Sponsors CRUD methods to SheetsDB"
```

---

## Task 5: Add Onboardings CRUD methods

**Files:**
- Modify: `packages/client-onboarding/services/sheets_db.py`

**Step 1: Add onboarding methods after sponsor methods**

```python
    # ==================== ONBOARDINGS ====================

    def get_onboardings(self, filters: dict = None) -> list[dict]:
        """Get all onboardings, optionally filtered."""
        if self.demo_mode:
            logger.debug("SheetsDB demo: get_onboardings()")
            return []

        sheet = self._get_sheet(self.TAB_ONBOARDINGS)
        records = sheet.get_all_records()

        if filters:
            for key, value in filters.items():
                records = [r for r in records if r.get(key) == value]

        return records

    def get_onboarding(self, onboarding_id: str) -> Optional[dict]:
        """Get a single onboarding by ID."""
        if self.demo_mode:
            logger.debug(f"SheetsDB demo: get_onboarding({onboarding_id})")
            return None

        sheet = self._get_sheet(self.TAB_ONBOARDINGS)
        records = sheet.get_all_records()

        for record in records:
            if record.get('onboarding_id') == onboarding_id:
                return record
        return None

    def create_onboarding(self, data: dict) -> str:
        """Create a new onboarding. Returns the onboarding_id."""
        sheet = self._get_sheet(self.TAB_ONBOARDINGS)
        onboarding_id = self._generate_id('ONB', sheet)

        now = datetime.now().isoformat()
        data['onboarding_id'] = onboarding_id
        data['current_phase'] = data.get('current_phase', 1)
        data['status'] = data.get('status', 'in_progress')
        data['created_at'] = now
        data['updated_at'] = now

        if self.demo_mode:
            logger.info(f"SheetsDB demo: create_onboarding({onboarding_id})")
            return onboarding_id

        headers = self.SCHEMA[self.TAB_ONBOARDINGS]
        row = self._dict_to_row(headers, data)
        sheet.append_row(row)

        self._log_action('create', 'onboarding', onboarding_id, data)
        logger.info(f"SheetsDB: Created onboarding {onboarding_id}")
        return onboarding_id

    def update_onboarding(self, onboarding_id: str, data: dict) -> bool:
        """Update an existing onboarding."""
        data['updated_at'] = datetime.now().isoformat()

        if self.demo_mode:
            logger.info(f"SheetsDB demo: update_onboarding({onboarding_id})")
            return True

        sheet = self._get_sheet(self.TAB_ONBOARDINGS)
        cell = sheet.find(onboarding_id, in_column=1)
        if not cell:
            return False

        headers = self.SCHEMA[self.TAB_ONBOARDINGS]
        current_row = sheet.row_values(cell.row)
        current_data = self._row_to_dict(headers, current_row)
        current_data.update(data)

        new_row = self._dict_to_row(headers, current_data)
        sheet.update(f'A{cell.row}', [new_row])

        self._log_action('update', 'onboarding', onboarding_id, data)
        return True
```

**Step 2: Verify syntax**

Run: `cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && python -c "from services.sheets_db import get_client; c = get_client(); print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add packages/client-onboarding/services/sheets_db.py
git commit -m "feat(client-onboarding): add Onboardings CRUD methods to SheetsDB"
```

---

## Task 6: Add Persons, Screenings, and Risk Assessment methods

**Files:**
- Modify: `packages/client-onboarding/services/sheets_db.py`

**Step 1: Add remaining entity methods**

```python
    # ==================== PERSONS ====================

    def get_persons_for_onboarding(self, onboarding_id: str) -> list[dict]:
        """Get all persons linked to an onboarding via roles."""
        if self.demo_mode:
            return []

        # Get roles for this onboarding
        roles_sheet = self._get_sheet(self.TAB_PERSON_ROLES)
        roles = roles_sheet.get_all_records()
        person_ids = [r['person_id'] for r in roles if r.get('onboarding_id') == onboarding_id]

        if not person_ids:
            return []

        # Get person details
        persons_sheet = self._get_sheet(self.TAB_PERSONS)
        persons = persons_sheet.get_all_records()

        result = []
        for person in persons:
            if person.get('person_id') in person_ids:
                # Add role info
                person_roles = [r for r in roles if r.get('person_id') == person.get('person_id')]
                person['roles'] = person_roles
                result.append(person)

        return result

    def create_person(self, data: dict) -> str:
        """Create a new person. Returns the person_id."""
        sheet = self._get_sheet(self.TAB_PERSONS)
        person_id = self._generate_id('PER', sheet)

        data['person_id'] = person_id
        data['created_at'] = datetime.now().isoformat()

        if self.demo_mode:
            logger.info(f"SheetsDB demo: create_person({person_id})")
            return person_id

        headers = self.SCHEMA[self.TAB_PERSONS]
        row = self._dict_to_row(headers, data)
        sheet.append_row(row)

        self._log_action('create', 'person', person_id, data)
        return person_id

    def add_person_role(self, person_id: str, onboarding_id: str, role_data: dict) -> str:
        """Add a role linking a person to an onboarding."""
        sheet = self._get_sheet(self.TAB_PERSON_ROLES)
        role_id = self._generate_id('ROL', sheet)

        role_data['role_id'] = role_id
        role_data['person_id'] = person_id
        role_data['onboarding_id'] = onboarding_id

        if self.demo_mode:
            logger.info(f"SheetsDB demo: add_person_role({role_id})")
            return role_id

        headers = self.SCHEMA[self.TAB_PERSON_ROLES]
        row = self._dict_to_row(headers, role_data)
        sheet.append_row(row)

        self._log_action('create', 'person_role', role_id, role_data)
        return role_id

    # ==================== SCREENINGS ====================

    def get_screenings(self, onboarding_id: str) -> list[dict]:
        """Get all screenings for an onboarding."""
        if self.demo_mode:
            return []

        sheet = self._get_sheet(self.TAB_SCREENINGS)
        records = sheet.get_all_records()
        return [r for r in records if r.get('onboarding_id') == onboarding_id]

    def save_screening(self, data: dict) -> str:
        """Save a screening result. Returns the screening_id."""
        sheet = self._get_sheet(self.TAB_SCREENINGS)
        screening_id = self._generate_id('SCR', sheet)

        data['screening_id'] = screening_id
        data['screened_at'] = datetime.now().isoformat()

        # Serialize match_details if it's a dict/list
        if 'match_details' in data and not isinstance(data['match_details'], str):
            data['match_details'] = json.dumps(data['match_details'])

        if self.demo_mode:
            logger.info(f"SheetsDB demo: save_screening({screening_id})")
            return screening_id

        headers = self.SCHEMA[self.TAB_SCREENINGS]
        row = self._dict_to_row(headers, data)
        sheet.append_row(row)

        self._log_action('create', 'screening', screening_id, data)
        return screening_id

    # ==================== RISK ASSESSMENTS ====================

    def get_risk_assessment(self, onboarding_id: str) -> Optional[dict]:
        """Get the latest risk assessment for an onboarding."""
        if self.demo_mode:
            return None

        sheet = self._get_sheet(self.TAB_RISK_ASSESSMENTS)
        records = sheet.get_all_records()

        assessments = [r for r in records if r.get('onboarding_id') == onboarding_id]
        if not assessments:
            return None

        # Return most recent
        return sorted(assessments, key=lambda x: x.get('assessed_at', ''), reverse=True)[0]

    def save_risk_assessment(self, data: dict) -> str:
        """Save a risk assessment. Returns the assessment_id."""
        sheet = self._get_sheet(self.TAB_RISK_ASSESSMENTS)
        assessment_id = self._generate_id('RSK', sheet)

        data['assessment_id'] = assessment_id
        data['assessed_at'] = datetime.now().isoformat()

        # Serialize risk_factors if it's a dict/list
        if 'risk_factors' in data and not isinstance(data['risk_factors'], str):
            data['risk_factors'] = json.dumps(data['risk_factors'])

        if self.demo_mode:
            logger.info(f"SheetsDB demo: save_risk_assessment({assessment_id})")
            return assessment_id

        headers = self.SCHEMA[self.TAB_RISK_ASSESSMENTS]
        row = self._dict_to_row(headers, data)
        sheet.append_row(row)

        self._log_action('create', 'risk_assessment', assessment_id, data)
        return assessment_id
```

**Step 2: Verify syntax**

Run: `cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && python -c "from services.sheets_db import get_client; c = get_client(); print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add packages/client-onboarding/services/sheets_db.py
git commit -m "feat(client-onboarding): add Persons, Screenings, RiskAssessments methods"
```

---

## Task 7: Add audit logging and schema setup methods

**Files:**
- Modify: `packages/client-onboarding/services/sheets_db.py`

**Step 1: Add audit and setup methods**

```python
    # ==================== AUDIT LOG ====================

    def _log_action(self, action: str, entity_type: str, entity_id: str, details: dict) -> None:
        """Log an action to the audit trail."""
        if self.demo_mode:
            logger.debug(f"SheetsDB audit: {action} {entity_type} {entity_id}")
            return

        try:
            sheet = self._get_sheet(self.TAB_AUDIT_LOG)
            log_id = self._generate_id('LOG', sheet)

            log_entry = {
                'log_id': log_id,
                'timestamp': datetime.now().isoformat(),
                'user': 'system',  # TODO: Get from Flask session
                'action': action,
                'entity_type': entity_type,
                'entity_id': entity_id,
                'details': json.dumps(details) if details else ''
            }

            headers = self.SCHEMA[self.TAB_AUDIT_LOG]
            row = self._dict_to_row(headers, log_entry)
            sheet.append_row(row)
        except Exception as e:
            logger.error(f"SheetsDB: Failed to log action: {e}")

    # ==================== SCHEMA SETUP ====================

    def ensure_schema(self) -> None:
        """Ensure all tabs exist with proper headers."""
        if self.demo_mode:
            logger.info("SheetsDB demo: ensure_schema() - skipped")
            return

        for tab_name in self.SCHEMA.keys():
            self._get_sheet(tab_name)  # Creates if not exists

        logger.info("SheetsDB: Schema verified/created")

    def _get_config(self, key: str) -> Optional[str]:
        """Get a config value."""
        if self.demo_mode:
            return None

        sheet = self._get_sheet(self.TAB_CONFIG)
        records = sheet.get_all_records()

        for record in records:
            if record.get('key') == key:
                return record.get('value')
        return None

    def _set_config(self, key: str, value: str) -> None:
        """Set a config value."""
        if self.demo_mode:
            return

        sheet = self._get_sheet(self.TAB_CONFIG)

        # Check if key exists
        cell = sheet.find(key, in_column=1)
        if cell:
            sheet.update(f'B{cell.row}', value)
            sheet.update(f'C{cell.row}', datetime.now().isoformat())
        else:
            sheet.append_row([key, value, datetime.now().isoformat()])

    def is_seeded(self) -> bool:
        """Check if initial data has been seeded."""
        return self._get_config('data_seeded') == 'true'

    def mark_seeded(self) -> None:
        """Mark that initial data has been seeded."""
        self._set_config('data_seeded', 'true')
```

**Step 2: Verify syntax**

Run: `cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && python -c "from services.sheets_db import get_client; c = get_client(); print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add packages/client-onboarding/services/sheets_db.py
git commit -m "feat(client-onboarding): add audit logging and schema setup methods"
```

---

## Task 8: Add seed_initial_data method

**Files:**
- Modify: `packages/client-onboarding/services/sheets_db.py`

**Step 1: Add seed method with mock data**

```python
    def seed_initial_data(self) -> bool:
        """Seed initial mock data. Only runs once."""
        if self.demo_mode:
            logger.info("SheetsDB demo: seed_initial_data() - skipped")
            return False

        if self.is_seeded():
            logger.info("SheetsDB: Data already seeded, skipping")
            return False

        logger.info("SheetsDB: Seeding initial data...")

        # Seed enquiries
        enquiries = [
            {
                'sponsor_name': 'Granite Capital Partners LLP',
                'fund_name': 'Granite Capital Fund III LP',
                'contact_name': 'John Smith',
                'contact_email': 'john.smith@granitecapital.com',
                'entity_type': 'llp',
                'jurisdiction': 'UK',
                'registration_number': 'OC123456',
                'regulatory_status': 'FCA Regulated',
                'investment_strategy': 'Mid-market buyout investments in UK and European technology and healthcare sectors.',
                'target_size': '500,000,000',
                'status': 'converted',
                'created_by': 'system'
            },
            {
                'sponsor_name': 'Evergreen Capital Management Ltd',
                'fund_name': 'Evergreen Sustainable Growth Fund LP',
                'contact_name': 'Elizabeth Chen',
                'contact_email': 'e.chen@evergreencap.com',
                'entity_type': 'company',
                'jurisdiction': 'UK',
                'registration_number': '12345678',
                'regulatory_status': 'FCA Regulated',
                'investment_strategy': 'ESG-focused growth equity investments in renewable energy.',
                'target_size': '250,000,000',
                'status': 'pending',
                'created_by': 'system'
            },
            {
                'sponsor_name': 'Nordic Ventures AS',
                'fund_name': 'Nordic Technology Opportunities Fund LP',
                'contact_name': 'Erik Larsson',
                'contact_email': 'erik@nordicventures.no',
                'entity_type': 'company',
                'jurisdiction': 'Norway',
                'registration_number': 'NO 912 345 678',
                'regulatory_status': 'FSA Norway Regulated',
                'investment_strategy': 'Early-stage investments in Nordic technology companies.',
                'target_size': '150,000,000',
                'status': 'pending',
                'created_by': 'system'
            }
        ]

        enquiry_ids = {}
        for enq in enquiries:
            enq_id = self.create_enquiry(enq)
            enquiry_ids[enq['sponsor_name']] = enq_id

        # Seed sponsors
        sponsors = [
            {
                'legal_name': 'Granite Capital Partners LLP',
                'entity_type': 'llp',
                'jurisdiction': 'UK',
                'registration_number': 'OC123456',
                'regulated_status': 'FCA Regulated',
                'cdd_status': 'in_progress'
            },
            {
                'legal_name': 'Ashford Capital Advisors Ltd',
                'entity_type': 'company',
                'jurisdiction': 'UK',
                'registration_number': '98765432',
                'regulated_status': 'FCA Regulated',
                'cdd_status': 'in_progress'
            },
            {
                'legal_name': 'Bluewater Asset Management',
                'entity_type': 'company',
                'jurisdiction': 'UK',
                'registration_number': '11223344',
                'regulated_status': 'FCA Regulated',
                'cdd_status': 'complete'
            }
        ]

        sponsor_ids = {}
        for spo in sponsors:
            spo_id = self.create_sponsor(spo)
            sponsor_ids[spo['legal_name']] = spo_id

        # Seed onboardings
        onboardings = [
            {
                'sponsor_id': sponsor_ids.get('Granite Capital Partners LLP'),
                'fund_name': 'Granite Capital Fund III LP',
                'current_phase': 4,
                'status': 'in_progress',
                'risk_level': 'low',
                'assigned_to': 'James Smith',
                'is_existing_sponsor': 'false'
            },
            {
                'sponsor_id': sponsor_ids.get('Ashford Capital Advisors Ltd'),
                'fund_name': 'Ashford Growth Fund I LP',
                'current_phase': 6,
                'status': 'pending_mlro',
                'risk_level': 'medium',
                'assigned_to': 'James Smith',
                'is_existing_sponsor': 'false'
            },
            {
                'sponsor_id': sponsor_ids.get('Bluewater Asset Management'),
                'fund_name': 'Bluewater Real Estate Fund LP',
                'current_phase': 7,
                'status': 'approved',
                'risk_level': 'medium',
                'assigned_to': 'Sarah Johnson',
                'is_existing_sponsor': 'false'
            },
            {
                'sponsor_id': sponsor_ids.get('Granite Capital Partners LLP'),
                'fund_name': 'Granite Capital Fund IV LP',
                'current_phase': 2,
                'status': 'in_progress',
                'risk_level': 'low',
                'assigned_to': 'James Smith',
                'is_existing_sponsor': 'true'
            }
        ]

        for onb in onboardings:
            self.create_onboarding(onb)

        self.mark_seeded()
        logger.info("SheetsDB: Initial data seeded successfully")
        return True
```

**Step 2: Verify syntax**

Run: `cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && python -c "from services.sheets_db import get_client; c = get_client(); print('seed_initial_data:', hasattr(c, 'seed_initial_data'))"`

Expected: `seed_initial_data: True`

**Step 3: Commit**

```bash
git add packages/client-onboarding/services/sheets_db.py
git commit -m "feat(client-onboarding): add seed_initial_data method with mock data migration"
```

---

## Task 9: Export SheetsDB from services module

**Files:**
- Modify: `packages/client-onboarding/services/__init__.py`

**Step 1: Add SheetsDB exports**

Add to imports section:

```python
from .sheets_db import (
    SheetsDB,
    get_client as get_sheets_client
)
```

Add to `__all__` list:

```python
    # Google Sheets DB
    'SheetsDB',
    'get_sheets_client',
```

**Step 2: Verify import works**

Run: `cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && python -c "from services import SheetsDB, get_sheets_client; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add packages/client-onboarding/services/__init__.py
git commit -m "feat(client-onboarding): export SheetsDB from services module"
```

---

## Task 10: Integrate SheetsDB into app.py - initialization

**Files:**
- Modify: `packages/client-onboarding/app.py`

**Step 1: Add import and initialization after existing imports (around line 15)**

After `from dotenv import load_dotenv`, add:

```python
from services.sheets_db import get_client as get_sheets_client
```

**Step 2: Initialize sheets_db after app creation (around line 38, after DEMO_MODE)**

```python
# Initialize Google Sheets database
sheets_db = get_sheets_client()
```

**Step 3: Add startup hook at the end of file (before `if __name__ == '__main__':`)**

```python
# ========== Startup ==========

def init_app():
    """Initialize application - ensure schema and seed data."""
    sheets_db.ensure_schema()
    sheets_db.seed_initial_data()
    logger.info(f"App initialized - Sheets demo_mode: {sheets_db.demo_mode}")

# Run initialization
init_app()
```

**Step 4: Verify app starts**

Run: `cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && python -c "import app; print('App loaded OK')"`

Expected: `App loaded OK` (may show initialization logs)

**Step 5: Commit**

```bash
git add packages/client-onboarding/app.py
git commit -m "feat(client-onboarding): initialize SheetsDB on app startup"
```

---

## Task 11: Replace MOCK_ENQUIRIES with SheetsDB calls

**Files:**
- Modify: `packages/client-onboarding/app.py`

**Step 1: Update enquiries route (around line 523)**

Replace:
```python
@app.route('/enquiries')
@login_required
def pending_enquiries():
    """View pending enquiries (internal staff)"""
    enquiries = list(MOCK_ENQUIRIES.values())
    # Sort by submission date, newest first
    enquiries.sort(key=lambda x: x['submitted_at'], reverse=True)
    return render_template('enquiries.html', enquiries=enquiries)
```

With:
```python
@app.route('/enquiries')
@login_required
def pending_enquiries():
    """View pending enquiries (internal staff)"""
    # Get enquiries from Sheets (or empty list in demo mode)
    enquiries = sheets_db.get_enquiries()

    # Fallback to mock data if Sheets is empty/demo mode
    if not enquiries:
        enquiries = list(MOCK_ENQUIRIES.values())

    # Sort by submission date, newest first
    enquiries.sort(key=lambda x: x.get('submitted_at', x.get('created_at', '')), reverse=True)
    return render_template('enquiries.html', enquiries=enquiries)
```

**Step 2: Update view_enquiry route (around line 533)**

Replace:
```python
@app.route('/enquiry/<enquiry_id>/view')
@login_required
def view_enquiry(enquiry_id):
    """View details of a submitted enquiry"""
    enquiry = MOCK_ENQUIRIES.get(enquiry_id)
    if not enquiry:
        flash('Enquiry not found.', 'danger')
        return redirect(url_for('pending_enquiries'))
    return render_template('enquiry_detail.html', enquiry=enquiry)
```

With:
```python
@app.route('/enquiry/<enquiry_id>/view')
@login_required
def view_enquiry(enquiry_id):
    """View details of a submitted enquiry"""
    # Try Sheets first, fall back to mock
    enquiry = sheets_db.get_enquiry(enquiry_id)
    if not enquiry:
        enquiry = MOCK_ENQUIRIES.get(enquiry_id)

    if not enquiry:
        flash('Enquiry not found.', 'danger')
        return redirect(url_for('pending_enquiries'))
    return render_template('enquiry_detail.html', enquiry=enquiry)
```

**Step 3: Update start_onboarding_from_enquiry route (around line 544)**

Replace:
```python
@app.route('/enquiry/<enquiry_id>/start-onboarding')
@login_required
def start_onboarding_from_enquiry(enquiry_id):
    """Start onboarding process from a submitted enquiry"""
    enquiry = MOCK_ENQUIRIES.get(enquiry_id)
    if not enquiry:
        flash('Enquiry not found.', 'danger')
        return redirect(url_for('pending_enquiries'))

    # Redirect to Phase 1 with enquiry data
    flash(f'Starting onboarding for {enquiry["sponsor_name"]}. Form pre-populated from enquiry.', 'success')
    return redirect(url_for('onboarding_phase', onboarding_id='NEW', phase=1, enquiry_id=enquiry_id))
```

With:
```python
@app.route('/enquiry/<enquiry_id>/start-onboarding')
@login_required
def start_onboarding_from_enquiry(enquiry_id):
    """Start onboarding process from a submitted enquiry"""
    # Try Sheets first, fall back to mock
    enquiry = sheets_db.get_enquiry(enquiry_id)
    if not enquiry:
        enquiry = MOCK_ENQUIRIES.get(enquiry_id)

    if not enquiry:
        flash('Enquiry not found.', 'danger')
        return redirect(url_for('pending_enquiries'))

    # Redirect to Phase 1 with enquiry data
    flash(f'Starting onboarding for {enquiry.get("sponsor_name")}. Form pre-populated from enquiry.', 'success')
    return redirect(url_for('onboarding_phase', onboarding_id='NEW', phase=1, enquiry_id=enquiry_id))
```

**Step 4: Verify app still works**

Run: `cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && python -c "import app; print('OK')"`

Expected: `OK`

**Step 5: Commit**

```bash
git add packages/client-onboarding/app.py
git commit -m "feat(client-onboarding): integrate SheetsDB for enquiries routes"
```

---

## Task 12: Replace mock_onboardings with SheetsDB calls in dashboard

**Files:**
- Modify: `packages/client-onboarding/app.py`

**Step 1: Update dashboard route (around line 258)**

Replace the entire dashboard function:

```python
@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard - role-specific view"""
    user = get_current_user()

    # Get onboardings from Sheets
    onboardings = sheets_db.get_onboardings()

    # Fallback to mock data if Sheets is empty/demo mode
    if not onboardings:
        onboardings = [
            {
                'onboarding_id': 'ONB-001',
                'sponsor_name': 'Granite Capital Partners LLP',
                'fund_name': 'Granite Capital Fund III LP',
                'current_phase': 4,
                'status': 'in_progress',
                'risk_level': 'low',
                'assigned_to': 'James Smith',
                'is_existing_sponsor': False,
                'created_at': '2026-01-15',
                'updated_at': '2026-02-01'
            },
            {
                'onboarding_id': 'ONB-002',
                'sponsor_name': 'Ashford Capital Advisors Ltd',
                'fund_name': 'Ashford Growth Fund I LP',
                'current_phase': 6,
                'status': 'pending_mlro',
                'risk_level': 'medium',
                'assigned_to': 'James Smith',
                'is_existing_sponsor': False,
                'created_at': '2026-01-10',
                'updated_at': '2026-02-02'
            },
            {
                'onboarding_id': 'ONB-003',
                'sponsor_name': 'Bluewater Asset Management',
                'fund_name': 'Bluewater Real Estate Fund LP',
                'current_phase': 7,
                'status': 'approved',
                'risk_level': 'medium',
                'assigned_to': 'Sarah Johnson',
                'is_existing_sponsor': False,
                'created_at': '2026-01-05',
                'updated_at': '2026-02-02'
            },
            {
                'onboarding_id': 'ONB-004',
                'sponsor_name': 'Granite Capital Partners LLP',
                'fund_name': 'Granite Capital Fund IV LP',
                'current_phase': 2,
                'status': 'in_progress',
                'risk_level': 'low',
                'assigned_to': 'James Smith',
                'is_existing_sponsor': True,
                'created_at': '2026-01-28',
                'updated_at': '2026-02-01'
            }
        ]
    else:
        # Enrich onboardings with sponsor names if not present
        for onb in onboardings:
            if not onb.get('sponsor_name') and onb.get('sponsor_id'):
                sponsor = sheets_db.get_sponsor(onb['sponsor_id'])
                if sponsor:
                    onb['sponsor_name'] = sponsor.get('legal_name', 'Unknown')
            # Convert string booleans
            if isinstance(onb.get('is_existing_sponsor'), str):
                onb['is_existing_sponsor'] = onb['is_existing_sponsor'].lower() == 'true'
            # Ensure phase is int
            if isinstance(onb.get('current_phase'), str):
                onb['current_phase'] = int(onb['current_phase'])

    # Calculate stats
    stats = {
        'in_progress': sum(1 for o in onboardings if o.get('status') == 'in_progress'),
        'pending_approval': sum(1 for o in onboardings if o.get('status') == 'pending_mlro'),
        'approved_this_month': sum(1 for o in onboardings if o.get('status') == 'approved'),
        'on_hold': 0
    }

    # Filter by role
    if user['role'] == 'bd':
        # BD sees their own cases
        onboardings = [o for o in onboardings if o.get('assigned_to') == user['name'] or o.get('current_phase', 0) <= 2]
    elif user['role'] == 'mlro':
        # MLRO sees approval queue prominently
        onboardings = sorted(onboardings, key=lambda x: (x.get('status') != 'pending_mlro', x.get('updated_at', '')))

    # Add phase_name for display
    phases = get_phases()
    for onb in onboardings:
        phase_num = onb.get('current_phase', 1)
        if 1 <= phase_num <= len(phases):
            onb['phase_name'] = phases[phase_num - 1]['name']
            onb['phase'] = phase_num
        # Use onboarding_id as id for template compatibility
        if 'id' not in onb:
            onb['id'] = onb.get('onboarding_id', '')

    return render_template('dashboard.html',
                         onboardings=onboardings,
                         stats=stats,
                         phases=phases)
```

**Step 2: Verify app still works**

Run: `cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && python -c "import app; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add packages/client-onboarding/app.py
git commit -m "feat(client-onboarding): integrate SheetsDB for dashboard onboardings"
```

---

## Task 13: Update context processor to show Sheets status

**Files:**
- Modify: `packages/client-onboarding/app.py`

**Step 1: Update inject_globals context processor (around line 165)**

Replace:
```python
@app.context_processor
def inject_globals():
    """Inject global variables into all templates"""
    user = get_current_user()
    return {
        'demo_mode': DEMO_MODE,
        'current_user': user,
        'current_role': ROLES.get(user['role']) if user else None,
        'roles': ROLES,
        'now': datetime.now()
    }
```

With:
```python
@app.context_processor
def inject_globals():
    """Inject global variables into all templates"""
    user = get_current_user()
    return {
        'demo_mode': DEMO_MODE,
        'sheets_demo_mode': sheets_db.demo_mode,
        'current_user': user,
        'current_role': ROLES.get(user['role']) if user else None,
        'roles': ROLES,
        'now': datetime.now()
    }
```

**Step 2: Verify app still works**

Run: `cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && python -c "import app; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add packages/client-onboarding/app.py
git commit -m "feat(client-onboarding): expose sheets_demo_mode to templates"
```

---

## Task 14: Update API routes to use SheetsDB

**Files:**
- Modify: `packages/client-onboarding/app.py`

**Step 1: Update api_onboardings route (around line 818)**

Replace:
```python
@app.route('/api/onboardings')
@login_required
def api_onboardings():
    """API: Get onboardings list"""
    # Will integrate with Google Sheets
    return jsonify({'onboardings': [], 'status': 'ok'})
```

With:
```python
@app.route('/api/onboardings')
@login_required
def api_onboardings():
    """API: Get onboardings list"""
    onboardings = sheets_db.get_onboardings()
    return jsonify({'onboardings': onboardings, 'status': 'ok', 'demo_mode': sheets_db.demo_mode})
```

**Step 2: Update api_onboarding_detail route (around line 826)**

Replace:
```python
@app.route('/api/onboarding/<onboarding_id>')
@login_required
def api_onboarding_detail(onboarding_id):
    """API: Get onboarding details"""
    return jsonify({'onboarding': {}, 'status': 'ok'})
```

With:
```python
@app.route('/api/onboarding/<onboarding_id>')
@login_required
def api_onboarding_detail(onboarding_id):
    """API: Get onboarding details"""
    onboarding = sheets_db.get_onboarding(onboarding_id)
    if onboarding and onboarding.get('sponsor_id'):
        onboarding['sponsor'] = sheets_db.get_sponsor(onboarding['sponsor_id'])
        onboarding['persons'] = sheets_db.get_persons_for_onboarding(onboarding_id)
        onboarding['screenings'] = sheets_db.get_screenings(onboarding_id)
        onboarding['risk_assessment'] = sheets_db.get_risk_assessment(onboarding_id)
    return jsonify({'onboarding': onboarding or {}, 'status': 'ok'})
```

**Step 3: Add new API endpoint for Sheets status**

Add after api_audit_status:
```python
@app.route('/api/sheets/status')
@login_required
def api_sheets_status():
    """API: Get Google Sheets database status"""
    return jsonify({
        'status': 'ok',
        'demo_mode': sheets_db.demo_mode,
        'message': 'Sheets running in demo mode - data not persisted' if sheets_db.demo_mode else 'Sheets connected'
    })
```

**Step 4: Verify app still works**

Run: `cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && python -c "import app; print('OK')"`

Expected: `OK`

**Step 5: Commit**

```bash
git add packages/client-onboarding/app.py
git commit -m "feat(client-onboarding): update API routes to use SheetsDB"
```

---

## Task 15: Update .env.example with new variables

**Files:**
- Modify: `packages/client-onboarding/.env.example` (create if not exists)

**Step 1: Create or update .env.example**

```bash
# Flask
SECRET_KEY=your-secret-key-here
FLASK_ENV=development

# Demo Mode
DEMO_MODE=true

# Google Sheets Database
# Option 1: Service account JSON (base64 encoded)
# GOOGLE_SHEETS_CREDENTIALS=base64-encoded-json-here
# Option 2: Path to credentials file
# GOOGLE_SHEETS_CREDENTIALS_FILE=/path/to/credentials.json
# Workbook ID (from URL: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit)
# GOOGLE_SHEET_ID=your-sheet-id

# Google Drive Audit Trail (existing)
# GOOGLE_DRIVE_CREDENTIALS=base64-encoded-json-here
# GOOGLE_DRIVE_FOLDER_ID=your-folder-id

# OpenSanctions API (optional - uses mock in demo mode)
# OPENSANCTIONS_API_KEY=your-api-key
```

**Step 2: Commit**

```bash
git add packages/client-onboarding/.env.example
git commit -m "docs(client-onboarding): add Sheets env vars to .env.example"
```

---

## Task 16: Final verification and test

**Step 1: Run the application**

Run: `cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && python app.py`

Expected: App starts, shows initialization logs including "Sheets demo_mode: True"

**Step 2: Test in browser**

Open: http://localhost:5001

Verify:
- Dashboard loads with mock data
- Enquiries page shows enquiries
- Navigation works

**Step 3: Check logs for Sheets initialization**

Look for:
- "SheetsDB: No credentials found, running in demo mode"
- "App initialized - Sheets demo_mode: True"

**Step 4: Final commit (if any cleanup needed)**

```bash
git status
# If clean, skip. If changes:
git add -A
git commit -m "chore(client-onboarding): final cleanup for Sheets integration"
```

---

## Summary

**Files created:**
- `services/sheets_db.py` - Full CRUD service with demo mode

**Files modified:**
- `requirements.txt` - Added gspread
- `services/__init__.py` - Export SheetsDB
- `app.py` - Integrated SheetsDB for enquiries, onboardings, API routes
- `.env.example` - Documented new env vars

**To enable live mode:**
1. Create Google Cloud service account
2. Enable Google Sheets API
3. Share a Google Sheet with the service account email
4. Set `GOOGLE_SHEETS_CREDENTIALS` or `GOOGLE_SHEETS_CREDENTIALS_FILE`
5. Optionally set `GOOGLE_SHEET_ID` to use existing workbook

---

*End of Implementation Plan*
