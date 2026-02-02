"""
Services module for Client Onboarding
"""

from .opensanctions import (
    OpenSanctionsClient,
    get_client as get_opensanctions_client,
    screen_person,
    screen_company,
    batch_screen
)

from .gdrive_audit import (
    GoogleDriveAuditClient,
    get_client as get_gdrive_client,
    save_screening_results,
    save_form_data,
    upload_document,
    save_api_response,
    ensure_folder_structure
)

from .sheets_db import (
    SheetsDB,
    get_client as get_sheets_client
)

__all__ = [
    # OpenSanctions
    'OpenSanctionsClient',
    'get_opensanctions_client',
    'screen_person',
    'screen_company',
    'batch_screen',
    # Google Drive Audit
    'GoogleDriveAuditClient',
    'get_gdrive_client',
    'save_screening_results',
    'save_form_data',
    'upload_document',
    'save_api_response',
    'ensure_folder_structure',
    # Google Sheets DB
    'SheetsDB',
    'get_sheets_client',
]
