# Google Sheets Persistence Layer - Design Document

**Project:** Client Onboarding - Google Sheets Database
**Date:** 2026-02-02
**Status:** Approved

---

## Overview

Add Google Sheets as the persistence layer for the client onboarding POC, replacing in-memory mock data with actual CRUD operations.

## Decisions

- **Library:** gspread (most popular, simple API)
- **Auth:** Service Account (JSON credentials)
- **Migration:** Seed existing mock data on first run
- **Fallback:** Demo mode when credentials unavailable (matches GDrive pattern)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      app.py (Flask)                          │
│                                                              │
│   Routes call service methods instead of mock data          │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│               services/sheets_db.py                          │
│                                                              │
│   SheetsDB class:                                           │
│   - get_enquiries() / create_enquiry() / update_enquiry()   │
│   - get_sponsors() / create_sponsor() / update_sponsor()    │
│   - get_onboardings() / create_onboarding() / update_...()  │
│   - get_screenings() / save_screening()                     │
│   - get_risk_assessments() / save_risk_assessment()         │
│   - seed_initial_data() - one-time mock data migration      │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    gspread + OAuth2                          │
│            (Service Account credentials.json)                │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│              Google Sheets: Client_Onboarding_DB             │
│                                                              │
│   Tabs: Enquiries | Sponsors | Onboardings | Persons |      │
│         PersonRoles | Screenings | RiskAssessments |        │
│         AuditLog | Config                                   │
└─────────────────────────────────────────────────────────────┘
```

**Key principles:**
- Same demo mode pattern as GDrive - works without credentials, logs operations
- Service account JSON stored as env var or file (not committed)
- All writes also logged to AuditLog tab for compliance trail

---

## Google Sheets Schema

**Workbook:** `Client_Onboarding_DB`

### Tab: Config
| Column | Type | Description |
|--------|------|-------------|
| key | string | Setting name |
| value | string | Setting value |
| updated_at | timestamp | Last update |

### Tab: Enquiries
| Column | Type | Description |
|--------|------|-------------|
| enquiry_id | string | PK (ENQ-001) |
| sponsor_name | string | Prospective sponsor name |
| fund_name | string | Proposed fund name |
| contact_name | string | Contact person |
| contact_email | string | Contact email |
| entity_type | string | Company/LP/Trust/etc |
| jurisdiction | string | Country |
| status | string | new/in_review/converted/declined |
| notes | string | Free text notes |
| created_at | timestamp | Creation date |
| created_by | string | User who created |

### Tab: Sponsors
| Column | Type | Description |
|--------|------|-------------|
| sponsor_id | string | PK (SPO-001) |
| legal_name | string | Legal entity name |
| entity_type | string | Company/LLP/LP/etc |
| jurisdiction | string | Country of formation |
| registration_number | string | Company reg number |
| regulated_status | string | Regulated/Not Regulated |
| cdd_status | string | Pending/In Progress/Complete |
| created_at | timestamp | Creation date |

### Tab: Onboardings
| Column | Type | Description |
|--------|------|-------------|
| onboarding_id | string | PK (ONB-001) |
| enquiry_id | string | FK to Enquiries |
| sponsor_id | string | FK to Sponsors |
| fund_name | string | Fund name |
| current_phase | integer | 1-8 |
| status | string | in_progress/pending_approval/approved/declined |
| risk_level | string | low/medium/high |
| assigned_to | string | User assigned |
| created_at | timestamp | Creation date |
| updated_at | timestamp | Last update |

### Tab: Persons
| Column | Type | Description |
|--------|------|-------------|
| person_id | string | PK (PER-001) |
| full_name | string | Full legal name |
| nationality | string | Primary nationality |
| dob | date | Date of birth |
| country_of_residence | string | Current residence |
| pep_status | string | Not PEP/Domestic PEP/Foreign PEP |
| id_verified | boolean | ID verification complete |
| created_at | timestamp | Creation date |

### Tab: PersonRoles
| Column | Type | Description |
|--------|------|-------------|
| role_id | string | PK (ROL-001) |
| person_id | string | FK to Persons |
| sponsor_id | string | FK to Sponsors (nullable) |
| onboarding_id | string | FK to Onboardings |
| role_type | string | Director/Partner/UBO/etc |
| ownership_pct | decimal | Ownership percentage |
| is_ubo | boolean | Is this person a UBO? |

### Tab: Screenings
| Column | Type | Description |
|--------|------|-------------|
| screening_id | string | PK (SCR-001) |
| person_id | string | FK to Persons |
| onboarding_id | string | FK to Onboardings |
| screening_type | string | PEP/Sanctions/Adverse Media |
| result | string | clear/match/review_required |
| match_details | json | Match details if applicable |
| risk_level | string | low/medium/high/critical |
| screened_at | timestamp | When screened |
| screened_by | string | User who ran screening |

### Tab: RiskAssessments
| Column | Type | Description |
|--------|------|-------------|
| assessment_id | string | PK (RSK-001) |
| onboarding_id | string | FK to Onboardings |
| risk_score | integer | 0-100 |
| risk_rating | string | Low/Medium/High |
| risk_factors | json | Risk factors identified |
| edd_triggered | boolean | Triggers EDD? |
| assessed_at | timestamp | Assessment date |

### Tab: AuditLog
| Column | Type | Description |
|--------|------|-------------|
| log_id | string | PK (LOG-001) |
| timestamp | timestamp | Action time |
| user | string | User who performed action |
| action | string | create/update/delete/view |
| entity_type | string | enquiry/sponsor/onboarding/etc |
| entity_id | string | ID of affected entity |
| details | json | Action details |

---

## Service Interface

```python
class SheetsDB:
    """Google Sheets database service with demo mode fallback."""

    def __init__(self):
        self.demo_mode = True
        self.client = None
        self.workbook = None
        self._connect()

    # Connection
    def _connect(self) -> None
    def _get_sheet(self, tab_name: str) -> gspread.Worksheet

    # Enquiries
    def get_enquiries(self, status: str = None) -> list[dict]
    def get_enquiry(self, enquiry_id: str) -> dict | None
    def create_enquiry(self, data: dict) -> str  # returns enquiry_id
    def update_enquiry(self, enquiry_id: str, data: dict) -> bool

    # Sponsors
    def get_sponsors(self) -> list[dict]
    def get_sponsor(self, sponsor_id: str) -> dict | None
    def create_sponsor(self, data: dict) -> str

    # Onboardings
    def get_onboardings(self, filters: dict = None) -> list[dict]
    def get_onboarding(self, onboarding_id: str) -> dict | None
    def create_onboarding(self, data: dict) -> str
    def update_onboarding(self, onboarding_id: str, data: dict) -> bool

    # Persons & Roles
    def get_persons_for_onboarding(self, onboarding_id: str) -> list[dict]
    def create_person(self, data: dict) -> str
    def add_person_role(self, person_id: str, role_data: dict) -> str

    # Screenings
    def get_screenings(self, onboarding_id: str) -> list[dict]
    def save_screening(self, data: dict) -> str

    # Risk
    def get_risk_assessment(self, onboarding_id: str) -> dict | None
    def save_risk_assessment(self, data: dict) -> str

    # Audit
    def _log_action(self, action: str, entity_type: str, entity_id: str, details: dict)

    # Setup
    def ensure_schema(self) -> None  # Creates tabs if missing
    def seed_initial_data(self) -> None  # One-time mock data migration
```

---

## Demo Mode Behavior

Matches existing GDrive pattern:

- If no credentials configured: `demo_mode = True`
- All reads return empty lists or None
- All writes log to console but don't persist
- UI shows "Demo Mode" indicator
- Allows full app testing without Google account

---

## Integration Points

### app.py Changes

1. Import and initialize:
```python
from services.sheets_db import SheetsDB
sheets_db = SheetsDB()
```

2. Replace mock data:
- `MOCK_ENQUIRIES` → `sheets_db.get_enquiries()`
- `MOCK_ONBOARDINGS` → `sheets_db.get_onboardings()`

3. Phase completion:
```python
sheets_db.update_onboarding(id, {'current_phase': phase + 1})
gdrive_audit.save_form_data(...)  # Keep existing audit
```

4. Startup:
```python
with app.app_context():
    sheets_db.ensure_schema()
    sheets_db.seed_initial_data()
```

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_SHEETS_CREDENTIALS` | Service account JSON (base64 or path) | No (demo mode if missing) |
| `GOOGLE_SHEET_ID` | Workbook ID from URL | No (creates new if missing) |

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `services/sheets_db.py` | Create - new service |
| `app.py` | Modify - integrate service |
| `requirements.txt` | Add gspread, google-auth |
| `templates/base.html` | Modify - add Sheets demo mode indicator |
| `.env.example` | Add new env vars |

---

## Seed Data

Migrate existing mock data from `app.py`:

**Enquiries (3):**
- Granite Capital Partners - Fund III
- Evergreen Capital - Growth Fund I
- Nordic Ventures - Tech Fund II

**Onboardings (4):**
- Granite Capital - Phase 4 (Screening)
- Ashford Capital - Phase 5 (EDD)
- Bluewater AM - Phase 6 (Approval)
- Existing sponsor trigger review

---

*End of Design Document*
