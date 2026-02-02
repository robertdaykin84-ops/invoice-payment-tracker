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

from .risk_scoring import (
    calculate_risk,
    get_jurisdiction_score,
    JURISDICTION_PROHIBITED,
    JURISDICTION_HIGH,
    THRESHOLD_LOW,
    THRESHOLD_MEDIUM
)

from .pdf_report import (
    generate_report,
    gather_report_data,
    REPORT_TYPES
)

from .email_notify import (
    notify_edd_triggered,
    notify_approval_required,
    notify_screening_complete,
    notify_phase_completed,
    notify_onboarding_decision,
    get_demo_sent_emails,
    DEMO_MODE as EMAIL_DEMO_MODE
)

from .documents import (
    upload_document as upload_kyc_document,
    get_documents,
    get_document,
    delete_document,
    DOCUMENT_TYPES,
    ALLOWED_EXTENSIONS
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
    # Risk Scoring
    'calculate_risk',
    'get_jurisdiction_score',
    'JURISDICTION_PROHIBITED',
    'JURISDICTION_HIGH',
    'THRESHOLD_LOW',
    'THRESHOLD_MEDIUM',
    # PDF Reports
    'generate_report',
    'gather_report_data',
    'REPORT_TYPES',
    # Email Notifications
    'notify_edd_triggered',
    'notify_approval_required',
    'notify_screening_complete',
    'notify_phase_completed',
    'notify_onboarding_decision',
    'get_demo_sent_emails',
    'EMAIL_DEMO_MODE',
    # Documents
    'upload_kyc_document',
    'get_documents',
    'get_document',
    'delete_document',
    'DOCUMENT_TYPES',
    'ALLOWED_EXTENSIONS',
]
