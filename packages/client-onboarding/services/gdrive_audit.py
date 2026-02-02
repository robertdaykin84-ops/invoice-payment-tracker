"""
Google Drive Audit Trail Service
Saves all onboarding documents to Google Drive for JFSC-compliant audit trail

Supports both live mode (with OAuth credentials) and demo mode (without credentials)
for PoC demonstrations.
"""

import os
import json
import logging
import mimetypes
from datetime import datetime
from typing import Dict, List, Optional, Any
from io import BytesIO

logger = logging.getLogger(__name__)

# Try to import Google API libraries
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
    GOOGLE_LIBS_AVAILABLE = True
except ImportError:
    GOOGLE_LIBS_AVAILABLE = False
    logger.warning("Google API libraries not available - running in demo mode")

# Configuration paths
CREDENTIALS_PATH = os.environ.get(
    'GDRIVE_CREDENTIALS_PATH',
    os.path.expanduser('~/.config/mcp/gdrive-credentials.json')
)
TOKEN_PATH = os.environ.get(
    'GDRIVE_TOKEN_PATH',
    os.path.expanduser('~/.config/mcp/gdrive-token.json')
)

# Google Drive API scope
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Root folder name for all onboarding documents
ROOT_FOLDER_NAME = 'Client-Onboarding'

# Subfolder structure
FOLDER_STRUCTURE = {
    '_COMPLIANCE': 'Key compliance documents (easy access)',
    'Phase-1-Enquiry': 'Initial enquiry forms and intake documents',
    'Phase-2-Sponsor': 'Sponsor entity and principals documentation',
    'Phase-3-Fund': 'Fund structure and vehicle documentation',
    'Phase-4-Screening': 'Sanctions, PEP, and risk screening results',
    'Phase-5-EDD': 'Enhanced due diligence documents (if required)',
    'Phase-6-Approval': 'Approval records and sign-off documents',
    'Phase-7-Commercial': 'Engagement letters and commercial terms',
    'API-Responses': 'Raw API responses for audit purposes',
    'Screenshots': 'Browser screenshots and visual evidence'
}


class GoogleDriveAuditClient:
    """Client for Google Drive audit trail operations"""

    def __init__(self, credentials_path: str = None, token_path: str = None):
        self.credentials_path = credentials_path or CREDENTIALS_PATH
        self.token_path = token_path or TOKEN_PATH
        self.demo_mode = not GOOGLE_LIBS_AVAILABLE or not os.path.exists(self.credentials_path)
        self.service = None
        self._folder_cache = {}  # Cache folder IDs to avoid repeated lookups

        if self.demo_mode:
            logger.info("Google Drive Audit running in DEMO MODE - documents will be logged but not uploaded")
        else:
            self._initialize_service()

    def _initialize_service(self):
        """Initialize the Google Drive API service with OAuth"""
        creds = None

        # Load existing token if available
        if os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            except Exception as e:
                logger.warning(f"Could not load existing token: {e}")

        # Check if credentials need refresh
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.warning(f"Could not refresh credentials: {e}")
                creds = None

        # If no valid credentials, run OAuth flow
        if not creds or not creds.valid:
            if not os.path.exists(self.credentials_path):
                logger.warning(f"Credentials file not found at {self.credentials_path}")
                self.demo_mode = True
                return

            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)

                # Save the token for future use
                with open(self.token_path, 'w') as token:
                    token.write(creds.to_json())
                logger.info(f"OAuth token saved to {self.token_path}")

            except Exception as e:
                logger.error(f"OAuth flow failed: {e}")
                self.demo_mode = True
                return

        try:
            self.service = build('drive', 'v3', credentials=creds)
            logger.info("Google Drive service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to build Drive service: {e}")
            self.demo_mode = True

    def _get_or_create_folder(
        self,
        folder_name: str,
        parent_id: str = None
    ) -> Optional[str]:
        """Get existing folder or create new one, return folder ID"""
        if self.demo_mode:
            # Return mock folder ID in demo mode
            mock_id = f"demo-folder-{folder_name.lower().replace(' ', '-')}"
            logger.info(f"[DEMO] Would create/get folder: {folder_name} -> {mock_id}")
            return mock_id

        cache_key = f"{parent_id or 'root'}:{folder_name}"
        if cache_key in self._folder_cache:
            return self._folder_cache[cache_key]

        try:
            # Search for existing folder
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            if parent_id:
                query += f" and '{parent_id}' in parents"

            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()

            files = results.get('files', [])
            if files:
                folder_id = files[0]['id']
                self._folder_cache[cache_key] = folder_id
                return folder_id

            # Create new folder
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_id:
                file_metadata['parents'] = [parent_id]

            folder = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()

            folder_id = folder.get('id')
            self._folder_cache[cache_key] = folder_id
            logger.info(f"Created folder: {folder_name} ({folder_id})")
            return folder_id

        except Exception as e:
            logger.error(f"Error creating/getting folder {folder_name}: {e}")
            return None

    def ensure_client_folder_structure(
        self,
        sponsor_name: str,
        fund_name: str
    ) -> Dict[str, str]:
        """
        Create the full folder structure for a client onboarding

        Returns:
            Dict mapping folder names to their IDs
        """
        folder_ids = {}
        client_folder_name = f"{sponsor_name} - {fund_name}"

        if self.demo_mode:
            logger.info(f"[DEMO] Would create folder structure for: {client_folder_name}")
            folder_ids['root'] = 'demo-root'
            folder_ids['client'] = f'demo-{client_folder_name}'
            for subfolder in FOLDER_STRUCTURE:
                folder_ids[subfolder] = f'demo-{subfolder}'
            return folder_ids

        try:
            # Get or create root folder
            root_id = self._get_or_create_folder(ROOT_FOLDER_NAME)
            folder_ids['root'] = root_id

            # Get or create client folder
            client_id = self._get_or_create_folder(client_folder_name, root_id)
            folder_ids['client'] = client_id

            # Create all subfolders
            for subfolder_name in FOLDER_STRUCTURE:
                subfolder_id = self._get_or_create_folder(subfolder_name, client_id)
                folder_ids[subfolder_name] = subfolder_id

            logger.info(f"Folder structure ready for: {client_folder_name}")
            return folder_ids

        except Exception as e:
            logger.error(f"Error creating folder structure: {e}")
            return folder_ids

    def upload_file(
        self,
        file_path: str,
        sponsor_name: str,
        fund_name: str,
        subfolder: str = None,
        custom_filename: str = None
    ) -> Dict[str, Any]:
        """
        Upload a file to the client's Google Drive folder

        Args:
            file_path: Local path to the file
            sponsor_name: Sponsor/client name
            fund_name: Fund name
            subfolder: Target subfolder (e.g., '_COMPLIANCE', 'Phase-4-Screening')
            custom_filename: Optional custom filename (default: original filename)

        Returns:
            Dict with upload status and file info
        """
        filename = custom_filename or os.path.basename(file_path)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        timestamped_filename = f"{timestamp}_{filename}"

        if self.demo_mode:
            logger.info(f"[DEMO] Would upload file: {timestamped_filename} to {subfolder or 'client root'}")
            return {
                'status': 'demo',
                'filename': timestamped_filename,
                'folder': subfolder,
                'file_id': f'demo-file-{timestamp}',
                'message': 'File logged in demo mode (not actually uploaded)'
            }

        try:
            # Ensure folder structure exists
            folders = self.ensure_client_folder_structure(sponsor_name, fund_name)

            # Determine target folder
            if subfolder and subfolder in folders:
                parent_id = folders[subfolder]
            else:
                parent_id = folders.get('client')

            if not parent_id:
                return {
                    'status': 'error',
                    'message': 'Could not determine target folder'
                }

            # Detect MIME type
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = 'application/octet-stream'

            # Upload file
            file_metadata = {
                'name': timestamped_filename,
                'parents': [parent_id]
            }

            media = MediaFileUpload(file_path, mimetype=mime_type)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink'
            ).execute()

            logger.info(f"Uploaded file: {timestamped_filename} ({file.get('id')})")
            return {
                'status': 'success',
                'filename': timestamped_filename,
                'file_id': file.get('id'),
                'web_link': file.get('webViewLink'),
                'folder': subfolder
            }

        except Exception as e:
            logger.error(f"Error uploading file {filename}: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def upload_content(
        self,
        content: bytes,
        filename: str,
        sponsor_name: str,
        fund_name: str,
        subfolder: str = None,
        mime_type: str = 'application/octet-stream'
    ) -> Dict[str, Any]:
        """
        Upload content (bytes) to Google Drive

        Args:
            content: File content as bytes
            filename: Filename to use
            sponsor_name: Sponsor/client name
            fund_name: Fund name
            subfolder: Target subfolder
            mime_type: MIME type of the content

        Returns:
            Dict with upload status and file info
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        timestamped_filename = f"{timestamp}_{filename}"

        if self.demo_mode:
            logger.info(f"[DEMO] Would upload content: {timestamped_filename} ({len(content)} bytes)")
            return {
                'status': 'demo',
                'filename': timestamped_filename,
                'folder': subfolder,
                'file_id': f'demo-file-{timestamp}',
                'size': len(content),
                'message': 'Content logged in demo mode (not actually uploaded)'
            }

        try:
            # Ensure folder structure exists
            folders = self.ensure_client_folder_structure(sponsor_name, fund_name)

            # Determine target folder
            if subfolder and subfolder in folders:
                parent_id = folders[subfolder]
            else:
                parent_id = folders.get('client')

            if not parent_id:
                return {
                    'status': 'error',
                    'message': 'Could not determine target folder'
                }

            # Upload content
            file_metadata = {
                'name': timestamped_filename,
                'parents': [parent_id]
            }

            media = MediaIoBaseUpload(BytesIO(content), mimetype=mime_type)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink'
            ).execute()

            logger.info(f"Uploaded content: {timestamped_filename} ({file.get('id')})")
            return {
                'status': 'success',
                'filename': timestamped_filename,
                'file_id': file.get('id'),
                'web_link': file.get('webViewLink'),
                'folder': subfolder
            }

        except Exception as e:
            logger.error(f"Error uploading content {filename}: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def save_json_audit(
        self,
        data: Dict,
        filename: str,
        sponsor_name: str,
        fund_name: str,
        subfolder: str = 'API-Responses'
    ) -> Dict[str, Any]:
        """
        Save JSON data as audit record

        Args:
            data: Dictionary to save as JSON
            filename: Base filename (without extension)
            sponsor_name: Sponsor/client name
            fund_name: Fund name
            subfolder: Target subfolder (default: API-Responses)

        Returns:
            Dict with upload status
        """
        # Add audit metadata
        audit_data = {
            'audit_timestamp': datetime.now().isoformat(),
            'sponsor_name': sponsor_name,
            'fund_name': fund_name,
            'data': data
        }

        content = json.dumps(audit_data, indent=2, default=str).encode('utf-8')
        return self.upload_content(
            content=content,
            filename=f"{filename}.json",
            sponsor_name=sponsor_name,
            fund_name=fund_name,
            subfolder=subfolder,
            mime_type='application/json'
        )

    def save_screening_results(
        self,
        screening_results: Dict,
        sponsor_name: str,
        fund_name: str,
        is_compliance_doc: bool = True
    ) -> Dict[str, Any]:
        """
        Save sanctions/PEP screening results

        Args:
            screening_results: Results from OpenSanctions screening
            sponsor_name: Sponsor/client name
            fund_name: Fund name
            is_compliance_doc: If True, also save to _COMPLIANCE folder

        Returns:
            Dict with upload status
        """
        results = []

        # Save to Phase-4-Screening
        result = self.save_json_audit(
            data=screening_results,
            filename='screening-results',
            sponsor_name=sponsor_name,
            fund_name=fund_name,
            subfolder='Phase-4-Screening'
        )
        results.append(result)

        # Also save to _COMPLIANCE for easy access
        if is_compliance_doc:
            compliance_result = self.save_json_audit(
                data=screening_results,
                filename='screening-results',
                sponsor_name=sponsor_name,
                fund_name=fund_name,
                subfolder='_COMPLIANCE'
            )
            results.append(compliance_result)

        return {
            'status': 'success' if all(r.get('status') != 'error' for r in results) else 'partial',
            'results': results
        }

    def save_form_submission(
        self,
        form_data: Dict,
        phase: int,
        sponsor_name: str,
        fund_name: str
    ) -> Dict[str, Any]:
        """
        Save form submission data for audit

        Args:
            form_data: Form data dictionary
            phase: Onboarding phase number
            sponsor_name: Sponsor/client name
            fund_name: Fund name

        Returns:
            Dict with upload status
        """
        subfolder = f"Phase-{phase}-{self._get_phase_name(phase)}"
        return self.save_json_audit(
            data=form_data,
            filename=f'phase-{phase}-form-data',
            sponsor_name=sponsor_name,
            fund_name=fund_name,
            subfolder=subfolder if subfolder in FOLDER_STRUCTURE else None
        )

    def _get_phase_name(self, phase: int) -> str:
        """Get phase name from number"""
        phase_names = {
            1: 'Enquiry',
            2: 'Sponsor',
            3: 'Fund',
            4: 'Screening',
            5: 'EDD',
            6: 'Approval',
            7: 'Commercial',
            8: 'Complete'
        }
        return phase_names.get(phase, 'Unknown')


# Singleton instance
_client = None


def get_client() -> GoogleDriveAuditClient:
    """Get or create Google Drive audit client instance"""
    global _client
    if _client is None:
        _client = GoogleDriveAuditClient()
    return _client


# Convenience functions

def save_screening_results(screening_results: Dict, sponsor_name: str, fund_name: str) -> Dict:
    """Save screening results to audit trail"""
    return get_client().save_screening_results(screening_results, sponsor_name, fund_name)


def save_form_data(form_data: Dict, phase: int, sponsor_name: str, fund_name: str) -> Dict:
    """Save form submission to audit trail"""
    return get_client().save_form_submission(form_data, phase, sponsor_name, fund_name)


def upload_document(
    file_path: str,
    sponsor_name: str,
    fund_name: str,
    subfolder: str = None
) -> Dict:
    """Upload a document to audit trail"""
    return get_client().upload_file(file_path, sponsor_name, fund_name, subfolder)


def save_api_response(
    api_name: str,
    response_data: Dict,
    sponsor_name: str,
    fund_name: str
) -> Dict:
    """Save API response for audit"""
    return get_client().save_json_audit(
        data=response_data,
        filename=f'api-{api_name}',
        sponsor_name=sponsor_name,
        fund_name=fund_name,
        subfolder='API-Responses'
    )


def ensure_folder_structure(sponsor_name: str, fund_name: str) -> Dict[str, str]:
    """Ensure folder structure exists for a client"""
    return get_client().ensure_client_folder_structure(sponsor_name, fund_name)
