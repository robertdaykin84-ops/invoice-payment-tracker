"""
Google Sheets Database Service
Persistent storage layer using Google Sheets for the Client Onboarding system.

Supports both live mode (with OAuth credentials) and demo mode (without credentials)
for PoC demonstrations.
"""

import os
import json
import base64
import logging
from datetime import datetime
from typing import Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import gspread and OAuth libraries
try:
    import gspread
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False
    logger.warning("gspread or google-auth-oauthlib not available - running in demo mode")

# Google Sheets API scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]

# Schema definition - Tab names and column headers
SCHEMA = {
    'Config': ['key', 'value', 'updated_at'],
    'Enquiries': [
        'enquiry_id', 'sponsor_name', 'trading_name', 'fund_name', 'contact_name', 'contact_email',
        'entity_type', 'jurisdiction', 'registration_number', 'date_incorporated',
        'registered_address', 'business_address',
        'regulatory_status', 'regulator', 'license_number',
        'business_activities', 'source_of_wealth',
        'fund_type', 'legal_structure',
        'investment_strategy', 'target_size', 'status', 'notes', 'created_at', 'created_by'
    ],
    'Sponsors': [
        'sponsor_id', 'legal_name', 'trading_name', 'entity_type', 'jurisdiction',
        'registration_number', 'date_incorporated', 'registered_address', 'business_address',
        'business_activities', 'source_of_wealth',
        'regulated_status', 'cdd_status', 'created_at'
    ],
    'Onboardings': [
        'onboarding_id', 'enquiry_id', 'sponsor_id', 'fund_name', 'current_phase',
        'status', 'risk_level', 'assigned_to', 'is_existing_sponsor', 'created_at', 'updated_at'
    ],
    'Persons': [
        'person_id', 'full_name', 'former_names', 'nationality', 'dob', 'country_of_residence',
        'residential_address', 'pep_status', 'id_verified', 'created_at'
    ],
    'PersonRoles': [
        'role_id', 'person_id', 'sponsor_id', 'onboarding_id', 'role_type',
        'ownership_pct', 'is_ubo'
    ],
    'Screenings': [
        'screening_id', 'person_id', 'onboarding_id', 'screening_type', 'result',
        'match_details', 'risk_level', 'screened_at', 'screened_by'
    ],
    'RiskAssessments': [
        'assessment_id', 'onboarding_id', 'risk_score', 'risk_rating',
        'risk_factors', 'edd_triggered', 'assessed_at'
    ],
    'AuditLog': [
        'log_id', 'timestamp', 'user', 'action', 'entity_type', 'entity_id', 'details'
    ]
}

# ID prefixes for each entity type
ID_PREFIXES = {
    'Enquiries': 'ENQ',
    'Sponsors': 'SPO',
    'Onboardings': 'ONB',
    'Persons': 'PER',
    'PersonRoles': 'ROL',
    'Screenings': 'SCR',
    'RiskAssessments': 'RSK',
    'AuditLog': 'LOG'
}


class SheetsDB:
    """Google Sheets database client for persistent storage"""

    def __init__(self):
        self.demo_mode = True
        self.client = None
        self.spreadsheet = None
        self._sheet_cache: dict[str, Any] = {}

        if not GSPREAD_AVAILABLE:
            logger.info("SheetsDB running in DEMO MODE - gspread not available")
            return

        # Try to load credentials
        credentials = self._load_credentials()
        if not credentials:
            logger.info("SheetsDB running in DEMO MODE - no credentials configured")
            return

        try:
            self.client = gspread.authorize(credentials)
            self._open_or_create_spreadsheet()
            self.demo_mode = False
            logger.info("SheetsDB connected to Google Sheets successfully")
        except Exception as e:
            logger.error(f"Failed to initialize SheetsDB: {e}")
            logger.info("SheetsDB falling back to DEMO MODE")

    def _load_credentials(self) -> Optional[Credentials]:
        """Load Google OAuth credentials (same as Google Drive)"""
        # Default paths (same as gdrive_audit.py)
        default_creds_path = Path.home() / '.config' / 'mcp' / 'gdrive-credentials.json'
        default_token_path = Path.home() / '.config' / 'mcp' / 'gdrive-token.json'

        creds_path = Path(os.environ.get('GDRIVE_CREDENTIALS_PATH', default_creds_path))
        token_path = Path(os.environ.get('GDRIVE_TOKEN_PATH', default_token_path))

        creds = None

        # Check for existing token
        if token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
                logger.info(f"Loaded existing token from {token_path}")
            except Exception as e:
                logger.warning(f"Failed to load existing token: {e}")

        # If no valid credentials, check if we can refresh or need new auth
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Refreshed expired token")
                except Exception as e:
                    logger.warning(f"Failed to refresh token: {e}")
                    creds = None

            if not creds:
                # Need to run OAuth flow
                if not creds_path.exists():
                    logger.warning(f"No credentials file at {creds_path}")
                    return None

                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(creds_path), SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                    logger.info("Completed OAuth flow successfully")
                except Exception as e:
                    logger.error(f"OAuth flow failed: {e}")
                    return None

            # Save token for future use
            if creds:
                try:
                    token_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(token_path, 'w') as f:
                        f.write(creds.to_json())
                    logger.info(f"Saved token to {token_path}")
                except Exception as e:
                    logger.warning(f"Failed to save token: {e}")

        return creds

    def _open_or_create_spreadsheet(self):
        """Open existing spreadsheet or create new one"""
        sheet_id = os.environ.get('GOOGLE_SHEET_ID')

        if sheet_id:
            try:
                self.spreadsheet = self.client.open_by_key(sheet_id)
                logger.info(f"Opened existing spreadsheet: {self.spreadsheet.title}")
                return
            except Exception as e:
                logger.error(f"Failed to open spreadsheet {sheet_id}: {e}")

        # Create new spreadsheet
        try:
            self.spreadsheet = self.client.create('Client Onboarding Database')
            logger.info(f"Created new spreadsheet: {self.spreadsheet.title} (ID: {self.spreadsheet.id})")
            logger.info(f"Set GOOGLE_SHEET_ID={self.spreadsheet.id} to use this spreadsheet")
        except Exception as e:
            logger.error(f"Failed to create spreadsheet: {e}")
            raise

    def _get_sheet(self, tab_name: str) -> Optional[Any]:
        """Get or create worksheet with headers"""
        if self.demo_mode:
            return None

        if tab_name in self._sheet_cache:
            return self._sheet_cache[tab_name]

        if tab_name not in SCHEMA:
            logger.error(f"Unknown tab name: {tab_name}")
            return None

        try:
            # Try to get existing worksheet
            try:
                worksheet = self.spreadsheet.worksheet(tab_name)
            except gspread.WorksheetNotFound:
                # Create new worksheet with headers
                worksheet = self.spreadsheet.add_worksheet(
                    title=tab_name,
                    rows=1000,
                    cols=len(SCHEMA[tab_name])
                )
                # Add headers
                worksheet.update('A1', [SCHEMA[tab_name]])
                logger.info(f"Created worksheet: {tab_name}")

            self._sheet_cache[tab_name] = worksheet
            return worksheet
        except Exception as e:
            logger.error(f"Error getting/creating worksheet {tab_name}: {e}")
            return None

    def _generate_id(self, prefix: str, sheet: Optional[Any]) -> str:
        """Generate unique ID like ENQ-001, SPO-002, etc."""
        if self.demo_mode or sheet is None:
            # In demo mode, generate based on timestamp
            timestamp = datetime.now().strftime('%H%M%S')
            return f"{prefix}-{timestamp}"

        try:
            # Get all values in first column (IDs)
            all_values = sheet.col_values(1)
            # Filter to only IDs with this prefix
            existing_ids = [v for v in all_values if v.startswith(prefix + '-')]

            if not existing_ids:
                return f"{prefix}-001"

            # Extract numbers and find max
            max_num = 0
            for id_val in existing_ids:
                try:
                    num = int(id_val.split('-')[1])
                    max_num = max(max_num, num)
                except (IndexError, ValueError):
                    continue

            return f"{prefix}-{max_num + 1:03d}"
        except Exception as e:
            logger.error(f"Error generating ID for {prefix}: {e}")
            timestamp = datetime.now().strftime('%H%M%S')
            return f"{prefix}-{timestamp}"

    def _row_to_dict(self, headers: list[str], row: list[str]) -> dict[str, Any]:
        """Convert a row to a dictionary using headers"""
        result = {}
        for i, header in enumerate(headers):
            value = row[i] if i < len(row) else ''
            # Try to parse JSON for complex fields
            if header in ('match_details', 'risk_factors', 'details'):
                try:
                    value = json.loads(value) if value else {}
                except json.JSONDecodeError:
                    pass
            # Parse booleans
            elif header in ('is_ubo', 'id_verified', 'edd_triggered', 'is_existing_sponsor'):
                value = value.lower() == 'true' if isinstance(value, str) else bool(value)
            result[header] = value
        return result

    def _dict_to_row(self, headers: list[str], data: dict[str, Any]) -> list[str]:
        """Convert a dictionary to a row based on headers"""
        row = []
        for header in headers:
            value = data.get(header, '')
            # JSON serialize complex fields
            if header in ('match_details', 'risk_factors', 'details') and isinstance(value, (dict, list)):
                value = json.dumps(value)
            # Convert booleans to strings
            elif isinstance(value, bool):
                value = str(value).lower()
            row.append(str(value) if value is not None else '')
        return row

    def _log_action(self, action: str, entity_type: str, entity_id: str, details: Optional[dict] = None):
        """Log action to AuditLog sheet"""
        if self.demo_mode:
            logger.info(f"[DEMO] Audit log: {action} on {entity_type} {entity_id}")
            return

        try:
            sheet = self._get_sheet('AuditLog')
            if not sheet:
                return

            log_id = self._generate_id('LOG', sheet)
            timestamp = datetime.now().isoformat()
            # Try to get current user from context (simplified for now)
            user = 'system'

            row = self._dict_to_row(SCHEMA['AuditLog'], {
                'log_id': log_id,
                'timestamp': timestamp,
                'user': user,
                'action': action,
                'entity_type': entity_type,
                'entity_id': entity_id,
                'details': details or {}
            })
            sheet.append_row(row)
        except Exception as e:
            logger.error(f"Failed to log audit action: {e}")

    # ========== Setup Methods ==========

    def ensure_schema(self):
        """Create all tabs with headers if missing"""
        if self.demo_mode:
            logger.info("[DEMO] Would ensure schema for all tabs")
            return

        for tab_name in SCHEMA:
            self._get_sheet(tab_name)
        logger.info("Schema ensured for all tabs")

    def _get_config(self, key: str) -> Optional[str]:
        """Get a config value from the Config sheet"""
        if self.demo_mode:
            return None

        try:
            sheet = self._get_sheet('Config')
            if not sheet:
                return None

            # Find row with matching key
            all_values = sheet.get_all_values()
            for row in all_values[1:]:  # Skip header
                if row and row[0] == key:
                    return row[1] if len(row) > 1 else None
            return None
        except Exception as e:
            logger.error(f"Error getting config {key}: {e}")
            return None

    def _set_config(self, key: str, value: str):
        """Set a config value in the Config sheet"""
        if self.demo_mode:
            logger.info(f"[DEMO] Would set config {key}={value}")
            return

        try:
            sheet = self._get_sheet('Config')
            if not sheet:
                return

            timestamp = datetime.now().isoformat()

            # Find existing row with this key
            all_values = sheet.get_all_values()
            for i, row in enumerate(all_values[1:], start=2):  # Skip header, 1-indexed
                if row and row[0] == key:
                    # Update existing row
                    sheet.update(f'B{i}:C{i}', [[value, timestamp]])
                    return

            # Add new row
            sheet.append_row([key, value, timestamp])
        except Exception as e:
            logger.error(f"Error setting config {key}: {e}")

    def is_seeded(self) -> bool:
        """Check if initial data has been seeded"""
        return self._get_config('data_seeded') == 'true'

    def mark_seeded(self):
        """Mark that initial data has been seeded"""
        self._set_config('data_seeded', 'true')

    # ========== Enquiries CRUD ==========

    def get_enquiries(self, status: Optional[str] = None) -> list[dict]:
        """Get all enquiries, optionally filtered by status"""
        if self.demo_mode:
            logger.info(f"[DEMO] Would get enquiries (status={status})")
            return []

        try:
            sheet = self._get_sheet('Enquiries')
            if not sheet:
                return []

            all_values = sheet.get_all_values()
            if len(all_values) <= 1:
                return []

            headers = all_values[0]
            enquiries = []
            for row in all_values[1:]:
                if not row or not row[0]:
                    continue
                enquiry = self._row_to_dict(headers, row)
                if status is None or enquiry.get('status') == status:
                    enquiries.append(enquiry)
            return enquiries
        except Exception as e:
            logger.error(f"Error getting enquiries: {e}")
            return []

    def get_enquiry(self, enquiry_id: str) -> Optional[dict]:
        """Get a single enquiry by ID"""
        if self.demo_mode:
            logger.info(f"[DEMO] Would get enquiry {enquiry_id}")
            return None

        try:
            sheet = self._get_sheet('Enquiries')
            if not sheet:
                return None

            all_values = sheet.get_all_values()
            if len(all_values) <= 1:
                return None

            headers = all_values[0]
            for row in all_values[1:]:
                if row and row[0] == enquiry_id:
                    return self._row_to_dict(headers, row)
            return None
        except Exception as e:
            logger.error(f"Error getting enquiry {enquiry_id}: {e}")
            return None

    def create_enquiry(self, data: dict) -> str:
        """Create a new enquiry"""
        sheet = self._get_sheet('Enquiries')
        enquiry_id = self._generate_id('ENQ', sheet)

        if self.demo_mode:
            logger.info(f"[DEMO] Would create enquiry {enquiry_id}: {data}")
            return enquiry_id

        try:
            data['enquiry_id'] = enquiry_id
            data['created_at'] = data.get('created_at', datetime.now().isoformat())
            row = self._dict_to_row(SCHEMA['Enquiries'], data)
            sheet.append_row(row)
            self._log_action('create', 'Enquiries', enquiry_id, data)
            logger.info(f"Created enquiry {enquiry_id}")
            return enquiry_id
        except Exception as e:
            logger.error(f"Error creating enquiry: {e}")
            return enquiry_id

    def update_enquiry(self, enquiry_id: str, data: dict) -> bool:
        """Update an existing enquiry"""
        if self.demo_mode:
            logger.info(f"[DEMO] Would update enquiry {enquiry_id}: {data}")
            return True

        try:
            sheet = self._get_sheet('Enquiries')
            if not sheet:
                return False

            all_values = sheet.get_all_values()
            headers = all_values[0]

            for i, row in enumerate(all_values[1:], start=2):
                if row and row[0] == enquiry_id:
                    # Merge existing data with updates
                    existing = self._row_to_dict(headers, row)
                    existing.update(data)
                    new_row = self._dict_to_row(headers, existing)
                    sheet.update(f'A{i}:{chr(65 + len(headers) - 1)}{i}', [new_row])
                    self._log_action('update', 'Enquiries', enquiry_id, data)
                    logger.info(f"Updated enquiry {enquiry_id}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Error updating enquiry {enquiry_id}: {e}")
            return False

    # ========== Sponsors CRUD ==========

    def get_sponsors(self) -> list[dict]:
        """Get all sponsors"""
        if self.demo_mode:
            logger.info("[DEMO] Would get sponsors")
            return []

        try:
            sheet = self._get_sheet('Sponsors')
            if not sheet:
                return []

            all_values = sheet.get_all_values()
            if len(all_values) <= 1:
                return []

            headers = all_values[0]
            sponsors = []
            for row in all_values[1:]:
                if not row or not row[0]:
                    continue
                sponsors.append(self._row_to_dict(headers, row))
            return sponsors
        except Exception as e:
            logger.error(f"Error getting sponsors: {e}")
            return []

    def get_sponsor(self, sponsor_id: str) -> Optional[dict]:
        """Get a single sponsor by ID"""
        if self.demo_mode:
            logger.info(f"[DEMO] Would get sponsor {sponsor_id}")
            return None

        try:
            sheet = self._get_sheet('Sponsors')
            if not sheet:
                return None

            all_values = sheet.get_all_values()
            if len(all_values) <= 1:
                return None

            headers = all_values[0]
            for row in all_values[1:]:
                if row and row[0] == sponsor_id:
                    return self._row_to_dict(headers, row)
            return None
        except Exception as e:
            logger.error(f"Error getting sponsor {sponsor_id}: {e}")
            return None

    def get_sponsor_by_name(self, name: str) -> Optional[dict]:
        """Get a sponsor by legal name"""
        if self.demo_mode:
            logger.info(f"[DEMO] Would get sponsor by name {name}")
            return None

        try:
            sheet = self._get_sheet('Sponsors')
            if not sheet:
                return None

            all_values = sheet.get_all_values()
            if len(all_values) <= 1:
                return None

            headers = all_values[0]
            name_idx = headers.index('legal_name') if 'legal_name' in headers else 1
            for row in all_values[1:]:
                if row and len(row) > name_idx and row[name_idx].lower() == name.lower():
                    return self._row_to_dict(headers, row)
            return None
        except Exception as e:
            logger.error(f"Error getting sponsor by name {name}: {e}")
            return None

    def create_sponsor(self, data: dict) -> str:
        """Create a new sponsor"""
        sheet = self._get_sheet('Sponsors')
        sponsor_id = self._generate_id('SPO', sheet)

        if self.demo_mode:
            logger.info(f"[DEMO] Would create sponsor {sponsor_id}: {data}")
            return sponsor_id

        try:
            data['sponsor_id'] = sponsor_id
            data['created_at'] = data.get('created_at', datetime.now().isoformat())
            row = self._dict_to_row(SCHEMA['Sponsors'], data)
            sheet.append_row(row)
            self._log_action('create', 'Sponsors', sponsor_id, data)
            logger.info(f"Created sponsor {sponsor_id}")
            return sponsor_id
        except Exception as e:
            logger.error(f"Error creating sponsor: {e}")
            return sponsor_id

    def update_sponsor(self, sponsor_id: str, data: dict) -> bool:
        """Update an existing sponsor"""
        if self.demo_mode:
            logger.info(f"[DEMO] Would update sponsor {sponsor_id}: {data}")
            return True

        try:
            sheet = self._get_sheet('Sponsors')
            if not sheet:
                return False

            all_values = sheet.get_all_values()
            headers = all_values[0]

            for i, row in enumerate(all_values[1:], start=2):
                if row and row[0] == sponsor_id:
                    existing = self._row_to_dict(headers, row)
                    existing.update(data)
                    new_row = self._dict_to_row(headers, existing)
                    sheet.update(f'A{i}:{chr(65 + len(headers) - 1)}{i}', [new_row])
                    self._log_action('update', 'Sponsors', sponsor_id, data)
                    logger.info(f"Updated sponsor {sponsor_id}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Error updating sponsor {sponsor_id}: {e}")
            return False

    # ========== Onboardings CRUD ==========

    def get_onboardings(self, filters: Optional[dict] = None) -> list[dict]:
        """Get all onboardings, optionally filtered"""
        if self.demo_mode:
            logger.info(f"[DEMO] Would get onboardings (filters={filters})")
            return []

        try:
            sheet = self._get_sheet('Onboardings')
            if not sheet:
                return []

            all_values = sheet.get_all_values()
            if len(all_values) <= 1:
                return []

            headers = all_values[0]
            onboardings = []
            for row in all_values[1:]:
                if not row or not row[0]:
                    continue
                onboarding = self._row_to_dict(headers, row)

                # Apply filters
                if filters:
                    match = True
                    for key, value in filters.items():
                        if onboarding.get(key) != value:
                            match = False
                            break
                    if not match:
                        continue

                onboardings.append(onboarding)
            return onboardings
        except Exception as e:
            logger.error(f"Error getting onboardings: {e}")
            return []

    def get_onboarding(self, onboarding_id: str) -> Optional[dict]:
        """Get a single onboarding by ID"""
        if self.demo_mode:
            logger.info(f"[DEMO] Would get onboarding {onboarding_id}")
            # Return mock data for demo onboardings
            demo_onboardings = {
                'ONB-001': {'onboarding_id': 'ONB-001', 'sponsor_name': 'Granite Capital Partners LLP', 'status': 'in_progress', 'current_phase': 4, 'assigned_to': 'James Smith'},
                'ONB-002': {'onboarding_id': 'ONB-002', 'sponsor_name': 'Ashford Capital Advisors Ltd', 'status': 'pending_mlro', 'current_phase': 6, 'assigned_to': 'James Smith'},
                'ONB-003': {'onboarding_id': 'ONB-003', 'sponsor_name': 'Bluewater Asset Management', 'status': 'approved', 'current_phase': 7, 'assigned_to': 'Sarah Johnson'},
                'ONB-004': {'onboarding_id': 'ONB-004', 'sponsor_name': 'Granite Capital Partners LLP', 'status': 'in_progress', 'current_phase': 2, 'assigned_to': 'James Smith'},
            }
            return demo_onboardings.get(onboarding_id)

        try:
            sheet = self._get_sheet('Onboardings')
            if not sheet:
                return None

            all_values = sheet.get_all_values()
            if len(all_values) <= 1:
                return None

            headers = all_values[0]
            for row in all_values[1:]:
                if row and row[0] == onboarding_id:
                    return self._row_to_dict(headers, row)
            return None
        except Exception as e:
            logger.error(f"Error getting onboarding {onboarding_id}: {e}")
            return None

    def create_onboarding(self, data: dict) -> str:
        """Create a new onboarding"""
        sheet = self._get_sheet('Onboardings')
        onboarding_id = self._generate_id('ONB', sheet)

        if self.demo_mode:
            logger.info(f"[DEMO] Would create onboarding {onboarding_id}: {data}")
            return onboarding_id

        try:
            now = datetime.now().isoformat()
            data['onboarding_id'] = onboarding_id
            data['created_at'] = data.get('created_at', now)
            data['updated_at'] = data.get('updated_at', now)
            row = self._dict_to_row(SCHEMA['Onboardings'], data)
            sheet.append_row(row)
            self._log_action('create', 'Onboardings', onboarding_id, data)
            logger.info(f"Created onboarding {onboarding_id}")
            return onboarding_id
        except Exception as e:
            logger.error(f"Error creating onboarding: {e}")
            return onboarding_id

    def update_onboarding(self, onboarding_id: str, data: dict) -> bool:
        """Update an existing onboarding"""
        if self.demo_mode:
            logger.info(f"[DEMO] Would update onboarding {onboarding_id}: {data}")
            return True

        try:
            sheet = self._get_sheet('Onboardings')
            if not sheet:
                return False

            all_values = sheet.get_all_values()
            headers = all_values[0]

            for i, row in enumerate(all_values[1:], start=2):
                if row and row[0] == onboarding_id:
                    existing = self._row_to_dict(headers, row)
                    existing.update(data)
                    existing['updated_at'] = datetime.now().isoformat()
                    new_row = self._dict_to_row(headers, existing)
                    sheet.update(f'A{i}:{chr(65 + len(headers) - 1)}{i}', [new_row])
                    self._log_action('update', 'Onboardings', onboarding_id, data)
                    logger.info(f"Updated onboarding {onboarding_id}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Error updating onboarding {onboarding_id}: {e}")
            return False

    def delete_onboarding(self, onboarding_id: str) -> bool:
        """Delete an onboarding and its related data"""
        if self.demo_mode:
            logger.info(f"[DEMO] Would delete onboarding {onboarding_id}")
            return True

        try:
            # Delete from Onboardings sheet
            sheet = self._get_sheet('Onboardings')
            if not sheet:
                return False

            all_values = sheet.get_all_values()

            for i, row in enumerate(all_values[1:], start=2):
                if row and row[0] == onboarding_id:
                    sheet.delete_rows(i)
                    self._log_action('delete', 'Onboardings', onboarding_id, {})
                    logger.info(f"Deleted onboarding {onboarding_id}")

                    # Also clean up related data in other sheets
                    self._delete_related_data(onboarding_id)
                    return True

            return False
        except Exception as e:
            logger.error(f"Error deleting onboarding {onboarding_id}: {e}")
            return False

    def _delete_related_data(self, onboarding_id: str):
        """Delete data related to an onboarding from other sheets"""
        related_sheets = ['PersonRoles', 'Screenings', 'RiskAssessments']

        for sheet_name in related_sheets:
            try:
                sheet = self._get_sheet(sheet_name)
                if not sheet:
                    continue

                all_values = sheet.get_all_values()
                if len(all_values) <= 1:
                    continue

                headers = all_values[0]
                # Find onboarding_id column index
                try:
                    id_col = headers.index('onboarding_id')
                except ValueError:
                    continue

                # Delete rows matching this onboarding (in reverse to preserve indices)
                rows_to_delete = []
                for i, row in enumerate(all_values[1:], start=2):
                    if len(row) > id_col and row[id_col] == onboarding_id:
                        rows_to_delete.append(i)

                # Delete in reverse order
                for row_idx in reversed(rows_to_delete):
                    sheet.delete_rows(row_idx)
                    logger.info(f"Deleted row {row_idx} from {sheet_name} for onboarding {onboarding_id}")

            except Exception as e:
                logger.error(f"Error cleaning up {sheet_name} for {onboarding_id}: {e}")

    # ========== Persons CRUD ==========

    def get_persons_for_onboarding(self, onboarding_id: str) -> list[dict]:
        """Get all persons associated with an onboarding via PersonRoles"""
        if self.demo_mode:
            logger.info(f"[DEMO] Would get persons for onboarding {onboarding_id}")
            return []

        try:
            # First get person IDs from PersonRoles
            roles_sheet = self._get_sheet('PersonRoles')
            persons_sheet = self._get_sheet('Persons')
            if not roles_sheet or not persons_sheet:
                return []

            # Get all roles for this onboarding
            roles_values = roles_sheet.get_all_values()
            if len(roles_values) <= 1:
                return []

            roles_headers = roles_values[0]
            onboarding_idx = roles_headers.index('onboarding_id') if 'onboarding_id' in roles_headers else 3
            person_id_idx = roles_headers.index('person_id') if 'person_id' in roles_headers else 1

            person_ids = set()
            for row in roles_values[1:]:
                if row and len(row) > onboarding_idx and row[onboarding_idx] == onboarding_id:
                    if len(row) > person_id_idx:
                        person_ids.add(row[person_id_idx])

            # Get person details
            persons_values = persons_sheet.get_all_values()
            if len(persons_values) <= 1:
                return []

            persons_headers = persons_values[0]
            persons = []
            for row in persons_values[1:]:
                if row and row[0] in person_ids:
                    person = self._row_to_dict(persons_headers, row)
                    # Add roles for this person
                    person['roles'] = []
                    for role_row in roles_values[1:]:
                        if (role_row and len(role_row) > person_id_idx and
                            role_row[person_id_idx] == row[0] and
                            len(role_row) > onboarding_idx and
                            role_row[onboarding_idx] == onboarding_id):
                            person['roles'].append(self._row_to_dict(roles_headers, role_row))
                    persons.append(person)
            return persons
        except Exception as e:
            logger.error(f"Error getting persons for onboarding {onboarding_id}: {e}")
            return []

    def create_person(self, data: dict) -> str:
        """Create a new person"""
        sheet = self._get_sheet('Persons')
        person_id = self._generate_id('PER', sheet)

        if self.demo_mode:
            logger.info(f"[DEMO] Would create person {person_id}: {data}")
            return person_id

        try:
            data['person_id'] = person_id
            data['created_at'] = data.get('created_at', datetime.now().isoformat())
            row = self._dict_to_row(SCHEMA['Persons'], data)
            sheet.append_row(row)
            self._log_action('create', 'Persons', person_id, data)
            logger.info(f"Created person {person_id}")
            return person_id
        except Exception as e:
            logger.error(f"Error creating person: {e}")
            return person_id

    def add_person_role(self, person_id: str, onboarding_id: str, role_data: dict) -> str:
        """Add a role for a person on an onboarding"""
        sheet = self._get_sheet('PersonRoles')
        role_id = self._generate_id('ROL', sheet)

        if self.demo_mode:
            logger.info(f"[DEMO] Would add role {role_id} for person {person_id}: {role_data}")
            return role_id

        try:
            role_data['role_id'] = role_id
            role_data['person_id'] = person_id
            role_data['onboarding_id'] = onboarding_id
            row = self._dict_to_row(SCHEMA['PersonRoles'], role_data)
            sheet.append_row(row)
            self._log_action('create', 'PersonRoles', role_id, role_data)
            logger.info(f"Added role {role_id} for person {person_id}")
            return role_id
        except Exception as e:
            logger.error(f"Error adding person role: {e}")
            return role_id

    def create_person_role(self, data: dict) -> str:
        """Create a person role linking a person to an entity (sponsor or fund)"""
        sheet = self._get_sheet('PersonRoles')
        role_id = self._generate_id('ROL', sheet)

        if self.demo_mode:
            logger.info(f"[DEMO] Would create person role {role_id}: {data}")
            return role_id

        try:
            data['role_id'] = role_id
            # Map 'role' to 'role_type' if present
            if 'role' in data and 'role_type' not in data:
                data['role_type'] = data.pop('role')
            # Map 'entity_id' to 'sponsor_id' if entity_type is Sponsor
            if data.get('entity_type') == 'Sponsor' and 'entity_id' in data:
                data['sponsor_id'] = data.pop('entity_id')
                data.pop('entity_type', None)
            row = self._dict_to_row(SCHEMA['PersonRoles'], data)
            sheet.append_row(row)
            self._log_action('create', 'PersonRoles', role_id, data)
            logger.info(f"Created person role {role_id}")
            return role_id
        except Exception as e:
            logger.error(f"Error creating person role: {e}")
            return role_id

    # ========== Screenings CRUD ==========

    def get_screenings(self, onboarding_id: str) -> list[dict]:
        """Get all screenings for an onboarding"""
        if self.demo_mode:
            logger.info(f"[DEMO] Would get screenings for onboarding {onboarding_id}")
            return []

        try:
            sheet = self._get_sheet('Screenings')
            if not sheet:
                return []

            all_values = sheet.get_all_values()
            if len(all_values) <= 1:
                return []

            headers = all_values[0]
            onboarding_idx = headers.index('onboarding_id') if 'onboarding_id' in headers else 2

            screenings = []
            for row in all_values[1:]:
                if row and len(row) > onboarding_idx and row[onboarding_idx] == onboarding_id:
                    screenings.append(self._row_to_dict(headers, row))
            return screenings
        except Exception as e:
            logger.error(f"Error getting screenings for onboarding {onboarding_id}: {e}")
            return []

    def save_screening(self, data: dict) -> str:
        """Save a screening result"""
        sheet = self._get_sheet('Screenings')
        screening_id = self._generate_id('SCR', sheet)

        if self.demo_mode:
            logger.info(f"[DEMO] Would save screening {screening_id}: {data}")
            return screening_id

        try:
            data['screening_id'] = screening_id
            data['screened_at'] = data.get('screened_at', datetime.now().isoformat())
            row = self._dict_to_row(SCHEMA['Screenings'], data)
            sheet.append_row(row)
            self._log_action('create', 'Screenings', screening_id, data)
            logger.info(f"Saved screening {screening_id}")
            return screening_id
        except Exception as e:
            logger.error(f"Error saving screening: {e}")
            return screening_id

    # ========== Risk Assessments CRUD ==========

    def get_risk_assessment(self, onboarding_id: str) -> Optional[dict]:
        """Get the latest risk assessment for an onboarding"""
        if self.demo_mode:
            logger.info(f"[DEMO] Would get risk assessment for onboarding {onboarding_id}")
            return None

        try:
            sheet = self._get_sheet('RiskAssessments')
            if not sheet:
                return None

            all_values = sheet.get_all_values()
            if len(all_values) <= 1:
                return None

            headers = all_values[0]
            onboarding_idx = headers.index('onboarding_id') if 'onboarding_id' in headers else 1

            # Find most recent assessment for this onboarding
            latest = None
            for row in all_values[1:]:
                if row and len(row) > onboarding_idx and row[onboarding_idx] == onboarding_id:
                    assessment = self._row_to_dict(headers, row)
                    if latest is None or assessment.get('assessed_at', '') > latest.get('assessed_at', ''):
                        latest = assessment
            return latest
        except Exception as e:
            logger.error(f"Error getting risk assessment for onboarding {onboarding_id}: {e}")
            return None

    def save_risk_assessment(self, data: dict) -> str:
        """Save a risk assessment"""
        sheet = self._get_sheet('RiskAssessments')
        assessment_id = self._generate_id('RSK', sheet)

        if self.demo_mode:
            logger.info(f"[DEMO] Would save risk assessment {assessment_id}: {data}")
            return assessment_id

        try:
            data['assessment_id'] = assessment_id
            data['assessed_at'] = data.get('assessed_at', datetime.now().isoformat())
            row = self._dict_to_row(SCHEMA['RiskAssessments'], data)
            sheet.append_row(row)
            self._log_action('create', 'RiskAssessments', assessment_id, data)
            logger.info(f"Saved risk assessment {assessment_id}")
            return assessment_id
        except Exception as e:
            logger.error(f"Error saving risk assessment: {e}")
            return assessment_id

    # ========== Seed Data ==========

    def seed_initial_data(self):
        """One-time migration of mock data"""
        if self.demo_mode:
            logger.info("[DEMO] Would seed initial data")
            return

        if self.is_seeded():
            logger.info("Data already seeded, skipping")
            return

        logger.info("Seeding initial data...")

        # Create 3 enquiries with enhanced fields
        enquiries = [
            {
                'sponsor_name': 'Granite Capital Partners LLP',
                'trading_name': '',
                'fund_name': 'Granite Capital Fund III LP',
                'contact_name': 'John Smith',
                'contact_email': 'john.smith@granitecapital.com',
                'entity_type': 'llp',
                'jurisdiction': 'UK',
                'registration_number': 'OC123456',
                'date_incorporated': '2015-03-15',
                'registered_address': '10 Fleet Street\nLondon\nEC4Y 1AU\nUnited Kingdom',
                'business_address': '',
                'regulatory_status': 'regulated',
                'regulator': 'FCA',
                'license_number': '789012',
                'business_activities': 'Private equity fund management focused on mid-market buyouts in technology and healthcare sectors.',
                'source_of_wealth': 'Management fees from existing funds (Funds I and II totaling $800M AUM), carried interest from successful exits.',
                'fund_type': 'jpf',
                'legal_structure': 'lp',
                'investment_strategy': 'Mid-market buyout investments in UK and European technology and healthcare sectors.',
                'target_size': '500000000',
                'status': 'pending',
                'created_by': 'system'
            },
            {
                'sponsor_name': 'Evergreen Capital Management Ltd',
                'trading_name': 'Evergreen Capital',
                'fund_name': 'Evergreen Sustainable Growth Fund LP',
                'contact_name': 'Elizabeth Chen',
                'contact_email': 'e.chen@evergreencap.com',
                'entity_type': 'company',
                'jurisdiction': 'UK',
                'registration_number': '12345678',
                'date_incorporated': '2018-07-20',
                'registered_address': '25 Old Broad Street\nLondon\nEC2N 1HQ\nUnited Kingdom',
                'business_address': '25 Old Broad Street\nLondon\nEC2N 1HQ\nUnited Kingdom',
                'regulatory_status': 'regulated',
                'regulator': 'FCA',
                'license_number': '823456',
                'business_activities': 'ESG-focused investment management specializing in renewable energy infrastructure.',
                'source_of_wealth': 'Seed capital from founding partners, subsequently grown through management and performance fees from Fund I.',
                'fund_type': 'jpf',
                'legal_structure': 'lp',
                'investment_strategy': 'ESG-focused growth equity investments in renewable energy infrastructure.',
                'target_size': '250000000',
                'status': 'pending',
                'created_by': 'system'
            },
            {
                'sponsor_name': 'Nordic Ventures AS',
                'trading_name': '',
                'fund_name': 'Nordic Technology Opportunities Fund LP',
                'contact_name': 'Erik Larsson',
                'contact_email': 'erik@nordicventures.no',
                'entity_type': 'company',
                'jurisdiction': 'Other',
                'registration_number': 'NO 912 345 678',
                'date_incorporated': '2012-01-10',
                'registered_address': 'Aker Brygge 1\nOslo 0250\nNorway',
                'business_address': 'Aker Brygge 1\nOslo 0250\nNorway',
                'regulatory_status': 'regulated',
                'regulator': 'Other',
                'license_number': 'NOR-2012-0456',
                'business_activities': 'Venture capital and growth equity investments in Nordic technology companies.',
                'source_of_wealth': 'Founding partners successful exits from previous ventures, combined with institutional LP commitments.',
                'fund_type': 'expert',
                'legal_structure': 'lp',
                'investment_strategy': 'Early-stage and growth investments in Nordic technology companies.',
                'target_size': '150000000',
                'status': 'pending',
                'created_by': 'system'
            }
        ]

        enquiry_ids = {}
        for enq in enquiries:
            enq_id = self.create_enquiry(enq)
            enquiry_ids[enq['sponsor_name']] = enq_id

        # Create 3 sponsors with enhanced fields
        sponsors = [
            {
                'legal_name': 'Granite Capital Partners LLP',
                'trading_name': '',
                'entity_type': 'llp',
                'jurisdiction': 'UK',
                'registration_number': 'OC123456',
                'date_incorporated': '2015-03-15',
                'registered_address': '10 Fleet Street\nLondon\nEC4Y 1AU\nUnited Kingdom',
                'business_address': '',
                'business_activities': 'Private equity fund management focused on mid-market buyouts.',
                'source_of_wealth': 'Management fees and carried interest from successful fund exits.',
                'regulated_status': 'regulated',
                'cdd_status': 'verified'
            },
            {
                'legal_name': 'Ashford Capital Advisors Ltd',
                'trading_name': 'Ashford Capital',
                'entity_type': 'company',
                'jurisdiction': 'UK',
                'registration_number': '87654321',
                'date_incorporated': '2019-05-10',
                'registered_address': '50 Berkeley Square\nLondon\nW1J 5BA\nUnited Kingdom',
                'business_address': '50 Berkeley Square\nLondon\nW1J 5BA\nUnited Kingdom',
                'business_activities': 'Multi-strategy investment management.',
                'source_of_wealth': 'Capital from institutional investors and family offices.',
                'regulated_status': 'regulated',
                'cdd_status': 'verified'
            },
            {
                'legal_name': 'Bluewater Asset Management',
                'trading_name': 'Bluewater',
                'entity_type': 'company',
                'jurisdiction': 'UK',
                'registration_number': '11223344',
                'date_incorporated': '2017-11-22',
                'registered_address': '30 Moorgate\nLondon\nEC2R 6PJ\nUnited Kingdom',
                'business_address': '30 Moorgate\nLondon\nEC2R 6PJ\nUnited Kingdom',
                'business_activities': 'Real estate investment and asset management.',
                'source_of_wealth': 'Successful property development and investment returns.',
                'regulated_status': 'regulated',
                'cdd_status': 'verified'
            }
        ]

        sponsor_ids = {}
        for spo in sponsors:
            spo_id = self.create_sponsor(spo)
            sponsor_ids[spo['legal_name']] = spo_id

        # Create 4 onboardings at various phases (7 phases total now)
        onboardings = [
            {
                'enquiry_id': enquiry_ids.get('Granite Capital Partners LLP', 'ENQ-001'),
                'sponsor_id': sponsor_ids.get('Granite Capital Partners LLP', 'SPO-001'),
                'fund_name': 'Granite Capital Fund III LP',
                'current_phase': '3',  # Screening (formerly phase 4)
                'status': 'in_progress',
                'risk_level': 'low',
                'assigned_to': 'James Smith',
                'is_existing_sponsor': False
            },
            {
                'sponsor_id': sponsor_ids.get('Ashford Capital Advisors Ltd', 'SPO-002'),
                'fund_name': 'Ashford Growth Fund I LP',
                'current_phase': '5',  # Approval (formerly phase 6)
                'status': 'pending_mlro',
                'risk_level': 'medium',
                'assigned_to': 'James Smith',
                'is_existing_sponsor': False
            },
            {
                'sponsor_id': sponsor_ids.get('Bluewater Asset Management', 'SPO-003'),
                'fund_name': 'Bluewater Real Estate Fund LP',
                'current_phase': '6',  # Commercial (formerly phase 7)
                'status': 'approved',
                'risk_level': 'medium',
                'assigned_to': 'Sarah Johnson',
                'is_existing_sponsor': False
            },
            {
                'sponsor_id': sponsor_ids.get('Granite Capital Partners LLP', 'SPO-001'),
                'fund_name': 'Granite Capital Fund IV LP',
                'current_phase': '2',  # Fund (formerly phase 3)
                'status': 'in_progress',
                'risk_level': 'low',
                'assigned_to': 'James Smith',
                'is_existing_sponsor': True
            }
        ]

        for onb in onboardings:
            self.create_onboarding(onb)

        # Create sample persons (principals) for Granite Capital
        granite_sponsor_id = sponsor_ids.get('Granite Capital Partners LLP', 'SPO-001')
        persons = [
            {
                'full_name': 'John Edward Smith',
                'former_names': '',
                'nationality': 'British',
                'dob': '1975-06-12',
                'country_of_residence': 'UK',
                'residential_address': '42 Kensington Gardens\nLondon\nW8 4PX\nUnited Kingdom',
                'pep_status': 'not_pep',
                'id_verified': True
            },
            {
                'full_name': 'Sarah Jane Johnson',
                'former_names': 'Sarah Jane Mitchell',
                'nationality': 'British',
                'dob': '1978-09-23',
                'country_of_residence': 'UK',
                'residential_address': '15 Chelsea Embankment\nLondon\nSW3 4LG\nUnited Kingdom',
                'pep_status': 'not_pep',
                'id_verified': True
            },
            {
                'full_name': 'Michael James Brown',
                'former_names': '',
                'nationality': 'British',
                'dob': '1980-02-08',
                'country_of_residence': 'UK',
                'residential_address': '8 Richmond Hill\nRichmond\nTW10 6QX\nUnited Kingdom',
                'pep_status': 'not_pep',
                'id_verified': True
            }
        ]

        person_roles = [
            {'role_type': 'partner', 'ownership_pct': 40, 'is_ubo': True},
            {'role_type': 'partner', 'ownership_pct': 35, 'is_ubo': True},
            {'role_type': 'partner', 'ownership_pct': 25, 'is_ubo': True}
        ]

        for i, person in enumerate(persons):
            person_id = self.create_person(person)
            role_data = person_roles[i].copy()
            role_data['person_id'] = person_id
            role_data['sponsor_id'] = granite_sponsor_id
            self.create_person_role(role_data)

        self.mark_seeded()
        logger.info("Initial data seeded successfully")


# Singleton instance
_client: Optional[SheetsDB] = None


def get_client() -> SheetsDB:
    """Get or create SheetsDB client instance"""
    global _client
    if _client is None:
        _client = SheetsDB()
    return _client
