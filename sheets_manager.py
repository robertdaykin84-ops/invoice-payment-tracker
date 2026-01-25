"""
Google Sheets Manager - Handles all interactions with Google Sheets API
"""

import os
import json
import base64
import logging
from typing import Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Sheets API scopes
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Column definitions for each sheet
INVOICE_COLUMNS = [
    'Invoice Number', 'Supplier Name', 'Contact Email', 'Contact Phone',
    'Invoice Date', 'Due Date', 'Amount', 'Currency', 'Status',
    'Payment Date', 'Notes'
]

PAYMENT_COLUMNS = [
    'Invoice Number', 'Supplier Name', 'Beneficiary Account Name', 'Account Number', 'IBAN',
    'Sort Code', 'SWIFT/BIC', 'Bank Name', 'Bank Address',
    'Payment Reference', 'Status', 'Upload Date', 'Notes'
]


def excel_date_to_string(excel_date):
    """
    Convert Excel serial date to DD/MM/YYYY string format.

    Args:
        excel_date: Excel serial date number or string date

    Returns:
        Date string in DD/MM/YYYY format, or original value if already a string
    """
    if excel_date is None or excel_date == '':
        return ''

    # If it's already a string that looks like a date, return it
    if isinstance(excel_date, str):
        # Check if it's a numeric string (Excel serial)
        try:
            num = float(excel_date)
            if num > 1000:  # Likely an Excel serial date
                date = datetime(1899, 12, 30) + timedelta(days=int(num))
                return date.strftime('%d/%m/%Y')
        except ValueError:
            pass
        return excel_date

    # If it's a number, convert from Excel serial
    if isinstance(excel_date, (int, float)):
        try:
            date = datetime(1899, 12, 30) + timedelta(days=int(excel_date))
            return date.strftime('%d/%m/%Y')
        except (ValueError, OverflowError):
            return str(excel_date)

    return str(excel_date)


class SheetsManagerError(Exception):
    """Custom exception for SheetsManager errors"""
    pass


class AuthenticationError(SheetsManagerError):
    """Authentication related errors"""
    pass


class SheetNotFoundError(SheetsManagerError):
    """Sheet not found errors"""
    pass


class SheetsManager:
    """Manage Google Sheets operations for invoice and payment tracking"""

    def __init__(self, credentials_path: str = 'credentials.json', token_path: str = 'token.pickle'):
        """
        Initialize the sheets manager and authenticate

        Args:
            credentials_path: Path to Google OAuth credentials file
            token_path: Path to store/load authentication token
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.spreadsheet_id = os.getenv('GOOGLE_SHEET_ID')

        if not self.spreadsheet_id:
            raise ValueError("GOOGLE_SHEET_ID not found in environment variables")

        self.creds = None
        self.service = None

        # Sheet names (can be customized)
        self.invoice_sheet = 'Invoice Tracker'
        self.payment_sheet = 'Payment Details'

        # Authenticate on initialization
        self._authenticate()

    def _authenticate(self) -> None:
        """
        Authenticate with Google Sheets API

        Supports multiple methods for flexibility:
        - GOOGLE_TOKEN env var (base64 encoded pickle) for production
        - token.pickle file for local development
        - GOOGLE_CREDENTIALS env var for OAuth flow
        - credentials.json file for OAuth flow

        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # Try to load existing token from environment variable first (for Render/production)
            google_token_b64 = os.environ.get('GOOGLE_TOKEN')

            if google_token_b64:
                # Load from base64 encoded environment variable
                logger.info("Loading token from GOOGLE_TOKEN environment variable")
                token_bytes = base64.b64decode(google_token_b64)
                self.creds = pickle.loads(token_bytes)
            elif os.path.exists(self.token_path):
                # Fall back to token file (for local development)
                with open(self.token_path, 'rb') as token:
                    self.creds = pickle.load(token)
                logger.info("Loaded existing credentials from token file")

            # Check if credentials need refresh or new login
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    logger.info("Refreshing expired credentials")
                    self.creds.refresh(Request())

                    # Update GOOGLE_TOKEN env var if running in production
                    if google_token_b64:
                        logger.info("Token refreshed - update GOOGLE_TOKEN env var with new value")
                else:
                    # Try environment variable first (for Render/production)
                    google_creds_json = os.environ.get('GOOGLE_CREDENTIALS')

                    if google_creds_json:
                        # Load from environment variable
                        logger.info("Loading credentials from GOOGLE_CREDENTIALS environment variable")
                        creds_dict = json.loads(google_creds_json)
                        flow = InstalledAppFlow.from_client_config(creds_dict, SCOPES)
                    elif os.path.exists(self.credentials_path):
                        # Fall back to file (for local development)
                        logger.info("Loading credentials from credentials.json file")
                        flow = InstalledAppFlow.from_client_secrets_file(
                            self.credentials_path, SCOPES
                        )
                    else:
                        raise AuthenticationError(
                            "No Google credentials found. "
                            "Set GOOGLE_CREDENTIALS env var or provide credentials.json"
                        )

                    logger.info("Starting OAuth flow for new credentials")
                    self.creds = flow.run_local_server(port=0)

                # Save credentials for future use (local development only)
                if not google_token_b64:
                    with open(self.token_path, 'wb') as token:
                        pickle.dump(self.creds, token)
                    logger.info("Saved new credentials to token file")

            # Build the service
            self.service = build('sheets', 'v4', credentials=self.creds)
            logger.info("Successfully authenticated with Google Sheets API")

        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise AuthenticationError(f"Failed to authenticate: {e}")

    def _ensure_authenticated(self) -> None:
        """Ensure we have valid authentication"""
        if not self.service:
            self._authenticate()

    def _safe_get(self, data: dict, key: str, default='') -> any:
        """Safely get a value from a dictionary"""
        value = data.get(key, default)
        return value if value is not None else default

    # ========== Invoice Operations ==========

    def add_invoice(self, invoice_data: dict) -> dict:
        """
        Add a new invoice to the Invoice Tracker sheet

        Args:
            invoice_data: Invoice data dictionary with keys:
                - invoice_number (required)
                - supplier_name (required)
                - contact_email
                - contact_phone
                - invoice_date
                - due_date
                - amount
                - currency (defaults to 'GBP')
                - status (defaults to 'Pending Review')
                - payment_date
                - notes

        Returns:
            dict: Result with 'success', 'message', and optionally 'row_number'

        Raises:
            SheetsManagerError: If the operation fails
        """
        self._ensure_authenticated()

        try:
            # Prepare row data in column order
            row = [
                self._safe_get(invoice_data, 'invoice_number'),
                self._safe_get(invoice_data, 'supplier_name'),
                self._safe_get(invoice_data, 'contact_email'),
                self._safe_get(invoice_data, 'contact_phone'),
                self._safe_get(invoice_data, 'invoice_date'),
                self._safe_get(invoice_data, 'due_date'),
                self._safe_get(invoice_data, 'amount', 0),
                self._safe_get(invoice_data, 'currency', 'GBP'),
                self._safe_get(invoice_data, 'status', 'Pending Review'),
                self._safe_get(invoice_data, 'payment_date'),
                self._safe_get(invoice_data, 'notes')
            ]

            # Append to sheet
            range_name = f"'{self.invoice_sheet}'!A:K"
            body = {'values': [row]}

            result = self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()

            updated_range = result.get('updates', {}).get('updatedRange', '')
            updated_cells = result.get('updates', {}).get('updatedCells', 0)

            logger.info(f"Added invoice '{invoice_data.get('invoice_number')}': {updated_cells} cells updated")

            return {
                'success': True,
                'message': f"Invoice added successfully",
                'updated_range': updated_range,
                'cells_updated': updated_cells
            }

        except HttpError as e:
            error_msg = f"Failed to add invoice: {e}"
            logger.error(error_msg)
            return {'success': False, 'message': error_msg, 'error': str(e)}

    def get_all_invoices(self) -> list[dict]:
        """
        Get all invoices from the Invoice Tracker sheet

        Returns:
            List of invoice dictionaries
        """
        self._ensure_authenticated()

        try:
            range_name = f"'{self.invoice_sheet}'!A2:K"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()

            rows = result.get('values', [])
            invoices = []

            for idx, row in enumerate(rows):
                # Pad row to ensure all columns exist
                while len(row) < 11:
                    row.append('')

                # Parse amount safely (handle comma-formatted numbers like "10,000.00")
                try:
                    amount_str = str(row[6]).replace(',', '') if row[6] else '0'
                    amount = float(amount_str)
                except (ValueError, TypeError):
                    amount = 0.0

                invoice = {
                    'id': idx + 2,  # Row number (1-indexed, +1 for header)
                    'invoice_number': row[0],
                    'supplier_name': row[1],
                    'contact_email': row[2],
                    'contact_phone': row[3],
                    'invoice_date': excel_date_to_string(row[4]),
                    'due_date': excel_date_to_string(row[5]),
                    'amount': amount,
                    'currency': row[7] or 'GBP',
                    'status': row[8] or 'Pending Review',
                    'payment_date': excel_date_to_string(row[9]),
                    'notes': row[10]
                }
                invoices.append(invoice)

            logger.info(f"Retrieved {len(invoices)} invoices")
            return invoices

        except HttpError as e:
            logger.error(f"Failed to get invoices: {e}")
            return []

    def get_invoice_by_number(self, invoice_number: str) -> Optional[dict]:
        """
        Get a specific invoice by its invoice number

        Args:
            invoice_number: The invoice number to search for

        Returns:
            Invoice dictionary or None if not found
        """
        invoices = self.get_all_invoices()
        for invoice in invoices:
            if invoice.get('invoice_number') == invoice_number:
                return invoice
        return None

    def delete_invoice(self, invoice_number: str) -> dict:
        """
        Delete an invoice by its invoice number

        Args:
            invoice_number: The invoice number to delete

        Returns:
            dict: Result with 'success' and 'message'
        """
        self._ensure_authenticated()

        try:
            # Find the row number for this invoice
            range_name = f"'{self.invoice_sheet}'!A:A"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()

            values = result.get('values', [])
            row_to_delete = None

            for i, row in enumerate(values):
                if row and row[0] == invoice_number:
                    row_to_delete = i + 1  # 1-indexed
                    break

            if row_to_delete is None:
                return {
                    'success': False,
                    'message': f'Invoice {invoice_number} not found'
                }

            # Delete the row using batchUpdate
            requests = [{
                'deleteDimension': {
                    'range': {
                        'sheetId': self._get_sheet_id(self.invoice_sheet),
                        'dimension': 'ROWS',
                        'startIndex': row_to_delete - 1,  # 0-indexed
                        'endIndex': row_to_delete
                    }
                }
            }]

            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={'requests': requests}
            ).execute()

            logger.info(f"Deleted invoice {invoice_number} from row {row_to_delete}")
            return {
                'success': True,
                'message': f'Invoice {invoice_number} deleted successfully'
            }

        except HttpError as e:
            logger.error(f"HTTP error deleting invoice: {e}")
            raise SheetsManagerError(f"Failed to delete invoice: {e}")
        except Exception as e:
            logger.error(f"Error deleting invoice: {e}")
            raise SheetsManagerError(f"Failed to delete invoice: {e}")

    def _get_sheet_id(self, sheet_name: str) -> int:
        """Get the sheet ID for a given sheet name"""
        spreadsheet = self.service.spreadsheets().get(
            spreadsheetId=self.spreadsheet_id
        ).execute()

        for sheet in spreadsheet.get('sheets', []):
            if sheet['properties']['title'] == sheet_name:
                return sheet['properties']['sheetId']

        raise SheetsManagerError(f"Sheet '{sheet_name}' not found")

    def delete_payment_by_invoice(self, invoice_number: str) -> dict:
        """
        Delete payment details by invoice number

        Args:
            invoice_number: The invoice number to delete

        Returns:
            dict: Result with 'success' and 'message'
        """
        self._ensure_authenticated()

        try:
            # Find the row number for this invoice in payment sheet (column A is Invoice Number)
            range_name = f"'{self.payment_sheet}'!A:A"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()

            values = result.get('values', [])
            row_to_delete = None

            for i, row in enumerate(values):
                if row and row[0] == invoice_number:
                    row_to_delete = i + 1  # 1-indexed
                    break

            if row_to_delete is None:
                return {
                    'success': False,
                    'message': f'Payment details for invoice {invoice_number} not found'
                }

            # Delete the row using batchUpdate
            requests = [{
                'deleteDimension': {
                    'range': {
                        'sheetId': self._get_sheet_id(self.payment_sheet),
                        'dimension': 'ROWS',
                        'startIndex': row_to_delete - 1,  # 0-indexed
                        'endIndex': row_to_delete
                    }
                }
            }]

            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={'requests': requests}
            ).execute()

            logger.info(f"Deleted payment details for invoice {invoice_number} from row {row_to_delete}")
            return {
                'success': True,
                'message': f'Payment details for invoice {invoice_number} deleted successfully'
            }

        except HttpError as e:
            logger.error(f"HTTP error deleting payment details: {e}")
            raise SheetsManagerError(f"Failed to delete payment details: {e}")
        except Exception as e:
            logger.error(f"Error deleting payment details: {e}")
            raise SheetsManagerError(f"Failed to delete payment details: {e}")

    def delete_payment_by_supplier(self, supplier_name: str) -> dict:
        """
        Delete payment details by supplier name

        Args:
            supplier_name: The supplier name to delete

        Returns:
            dict: Result with 'success' and 'message'
        """
        self._ensure_authenticated()

        try:
            # Find the row number for this supplier in payment sheet (column B since column A is Invoice Number)
            range_name = f"'{self.payment_sheet}'!B:B"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()

            values = result.get('values', [])
            row_to_delete = None

            for i, row in enumerate(values):
                if row and row[0] == supplier_name:
                    row_to_delete = i + 1  # 1-indexed
                    break

            if row_to_delete is None:
                return {
                    'success': False,
                    'message': f'Payment details for {supplier_name} not found'
                }

            # Delete the row using batchUpdate
            requests = [{
                'deleteDimension': {
                    'range': {
                        'sheetId': self._get_sheet_id(self.payment_sheet),
                        'dimension': 'ROWS',
                        'startIndex': row_to_delete - 1,  # 0-indexed
                        'endIndex': row_to_delete
                    }
                }
            }]

            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={'requests': requests}
            ).execute()

            logger.info(f"Deleted payment details for {supplier_name} from row {row_to_delete}")
            return {
                'success': True,
                'message': f'Payment details for {supplier_name} deleted successfully'
            }

        except HttpError as e:
            logger.error(f"HTTP error deleting payment details: {e}")
            raise SheetsManagerError(f"Failed to delete payment details: {e}")
        except Exception as e:
            logger.error(f"Error deleting payment details: {e}")
            raise SheetsManagerError(f"Failed to delete payment details: {e}")

    def update_invoice(self, row_number: int, invoice_data: dict) -> dict:
        """
        Update an existing invoice

        Args:
            row_number: The row number to update (1-indexed)
            invoice_data: Updated invoice data

        Returns:
            dict: Result with 'success' and 'message'
        """
        self._ensure_authenticated()

        try:
            row = [
                self._safe_get(invoice_data, 'invoice_number'),
                self._safe_get(invoice_data, 'supplier_name'),
                self._safe_get(invoice_data, 'contact_email'),
                self._safe_get(invoice_data, 'contact_phone'),
                self._safe_get(invoice_data, 'invoice_date'),
                self._safe_get(invoice_data, 'due_date'),
                self._safe_get(invoice_data, 'amount', 0),
                self._safe_get(invoice_data, 'currency', 'GBP'),
                self._safe_get(invoice_data, 'status', 'Pending Review'),
                self._safe_get(invoice_data, 'payment_date'),
                self._safe_get(invoice_data, 'notes')
            ]

            range_name = f"'{self.invoice_sheet}'!A{row_number}:K{row_number}"
            body = {'values': [row]}

            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()

            logger.info(f"Updated invoice at row {row_number}")
            return {
                'success': True,
                'message': f"Invoice updated successfully",
                'updated_cells': result.get('updatedCells', 0)
            }

        except HttpError as e:
            error_msg = f"Failed to update invoice: {e}"
            logger.error(error_msg)
            return {'success': False, 'message': error_msg}

    def update_invoice_status(self, invoice_number: str, new_status: str, payment_date: str = '') -> dict:
        """
        Update the status of an invoice

        Args:
            invoice_number: The invoice number
            new_status: New status value
            payment_date: Payment date (optional, for paid invoices)

        Returns:
            dict: Result with 'success' and 'message'
        """
        invoice = self.get_invoice_by_number(invoice_number)
        if not invoice:
            return {'success': False, 'message': f"Invoice '{invoice_number}' not found"}

        invoice['status'] = new_status
        if payment_date:
            invoice['payment_date'] = payment_date

        return self.update_invoice(invoice['id'], invoice)

    def get_recent_invoices(self, limit: int = 10) -> list[dict]:
        """
        Get the most recent invoices

        Args:
            limit: Maximum number of invoices to return

        Returns:
            List of recent invoice dictionaries
        """
        invoices = self.get_all_invoices()
        # Return last N invoices (most recently added)
        return invoices[-limit:] if len(invoices) > limit else invoices

    def get_invoices_by_status(self, status: str) -> list[dict]:
        """
        Get invoices filtered by status

        Args:
            status: Status to filter by

        Returns:
            List of matching invoices
        """
        invoices = self.get_all_invoices()
        return [inv for inv in invoices if inv.get('status', '').lower() == status.lower()]

    def get_invoice_stats(self) -> dict:
        """
        Get statistics about invoices

        Returns:
            Dictionary with invoice statistics
        """
        invoices = self.get_all_invoices()

        stats = {
            'total_invoices': len(invoices),
            'paid': 0,
            'approved': 0,
            'pending': 0,
            'overdue': 0,
            'rejected': 0,
            'total_amount': 0.0,
            'paid_amount': 0.0,
            'approved_amount': 0.0,
            'pending_amount': 0.0
        }

        today = datetime.now().date()

        for invoice in invoices:
            amount = invoice.get('amount', 0)
            status = invoice.get('status', '').lower()
            due_date_str = invoice.get('due_date', '')

            stats['total_amount'] += amount

            # Parse due date for overdue check (handles DD/MM/YYYY format)
            due_date = None
            if due_date_str:
                try:
                    # Try DD/MM/YYYY format first
                    if '/' in due_date_str:
                        parts = due_date_str.split('/')
                        if len(parts) == 3:
                            due_date = datetime(int(parts[2]), int(parts[1]), int(parts[0])).date()
                    # Try YYYY-MM-DD format
                    elif '-' in due_date_str and len(due_date_str) == 10:
                        due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                except (ValueError, IndexError):
                    due_date = None

            if 'paid' in status:
                stats['paid'] += 1
                stats['paid_amount'] += amount
            elif 'reject' in status:
                stats['rejected'] += 1
            elif 'approved' in status:
                stats['approved'] += 1
                stats['approved_amount'] += amount
            elif 'overdue' in status:
                # Only count as overdue if explicitly marked as overdue
                stats['overdue'] += 1
                stats['pending_amount'] += amount
            elif 'pending' in status or 'review' in status:
                # Pending or pending review stays pending
                stats['pending'] += 1
                stats['pending_amount'] += amount
            else:
                # No explicit status - count as pending
                stats['pending'] += 1
                stats['pending_amount'] += amount

        return stats

    # ========== Payment Details Operations ==========

    def add_payment_details(self, payment_data: dict) -> dict:
        """
        Add payment details to the Payment Details sheet

        Args:
            payment_data: Payment data dictionary with keys:
                - invoice_number (optional, links to invoice)
                - supplier_name (required)
                - beneficiary_account_name
                - account_number
                - iban
                - sort_code
                - swift_code
                - bank_name
                - bank_address
                - payment_reference
                - status (defaults to 'Ready for Upload')
                - upload_date
                - notes

        Returns:
            dict: Result with 'success' and 'message'
        """
        self._ensure_authenticated()

        try:
            row = [
                self._safe_get(payment_data, 'invoice_number'),
                self._safe_get(payment_data, 'supplier_name'),
                self._safe_get(payment_data, 'beneficiary_account_name'),
                self._safe_get(payment_data, 'account_number'),
                self._safe_get(payment_data, 'iban'),
                self._safe_get(payment_data, 'sort_code'),
                self._safe_get(payment_data, 'swift_code'),
                self._safe_get(payment_data, 'bank_name'),
                self._safe_get(payment_data, 'bank_address'),
                self._safe_get(payment_data, 'payment_reference'),
                self._safe_get(payment_data, 'status', 'Ready for Upload'),
                self._safe_get(payment_data, 'upload_date'),
                self._safe_get(payment_data, 'notes')
            ]

            range_name = f"'{self.payment_sheet}'!A:M"
            body = {'values': [row]}

            result = self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()

            updated_cells = result.get('updates', {}).get('updatedCells', 0)
            logger.info(f"Added payment details for '{payment_data.get('supplier_name')}': {updated_cells} cells")

            return {
                'success': True,
                'message': "Payment details added successfully",
                'cells_updated': updated_cells
            }

        except HttpError as e:
            error_msg = f"Failed to add payment details: {e}"
            logger.error(error_msg)
            return {'success': False, 'message': error_msg}

    def get_all_payment_details(self) -> list[dict]:
        """
        Get all payment details from the Payment Details sheet

        Returns:
            List of payment detail dictionaries
        """
        self._ensure_authenticated()

        try:
            range_name = f"'{self.payment_sheet}'!A2:M"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()

            rows = result.get('values', [])
            payments = []

            for idx, row in enumerate(rows):
                while len(row) < 13:
                    row.append('')

                payment = {
                    'id': idx + 2,
                    'invoice_number': row[0],
                    'supplier_name': row[1],
                    'beneficiary_account_name': row[2],
                    'account_number': row[3],
                    'iban': row[4],
                    'sort_code': row[5],
                    'swift_code': row[6],
                    'bank_name': row[7],
                    'bank_address': row[8],
                    'payment_reference': row[9],
                    'status': row[10] or 'Ready for Upload',
                    'upload_date': excel_date_to_string(row[11]),
                    'notes': row[12]
                }
                payments.append(payment)

            logger.info(f"Retrieved {len(payments)} payment details")
            return payments

        except HttpError as e:
            logger.error(f"Failed to get payment details: {e}")
            return []

    def get_payment_by_supplier(self, supplier_name: str) -> Optional[dict]:
        """
        Get payment details for a specific supplier

        Args:
            supplier_name: The supplier name to search for

        Returns:
            Payment details dictionary or None if not found
        """
        payments = self.get_all_payment_details()
        for payment in payments:
            if payment.get('supplier_name', '').lower() == supplier_name.lower():
                return payment
        return None

    def update_payment_details(self, row_number: int, payment_data: dict) -> dict:
        """
        Update existing payment details

        Args:
            row_number: The row number to update (1-indexed)
            payment_data: Updated payment data

        Returns:
            dict: Result with 'success' and 'message'
        """
        self._ensure_authenticated()

        try:
            row = [
                self._safe_get(payment_data, 'invoice_number'),
                self._safe_get(payment_data, 'supplier_name'),
                self._safe_get(payment_data, 'beneficiary_account_name'),
                self._safe_get(payment_data, 'account_number'),
                self._safe_get(payment_data, 'iban'),
                self._safe_get(payment_data, 'sort_code'),
                self._safe_get(payment_data, 'swift_code'),
                self._safe_get(payment_data, 'bank_name'),
                self._safe_get(payment_data, 'bank_address'),
                self._safe_get(payment_data, 'payment_reference'),
                self._safe_get(payment_data, 'status', 'Ready for Upload'),
                self._safe_get(payment_data, 'upload_date'),
                self._safe_get(payment_data, 'notes')
            ]

            range_name = f"'{self.payment_sheet}'!A{row_number}:M{row_number}"
            body = {'values': [row]}

            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()

            logger.info(f"Updated payment details at row {row_number}")
            return {
                'success': True,
                'message': "Payment details updated successfully",
                'updated_cells': result.get('updatedCells', 0)
            }

        except HttpError as e:
            error_msg = f"Failed to update payment details: {e}"
            logger.error(error_msg)
            return {'success': False, 'message': error_msg}

    # ========== Utility Methods ==========

    def get_unique_suppliers(self) -> list[str]:
        """
        Get a list of unique supplier names from both sheets

        Returns:
            Sorted list of unique supplier names
        """
        suppliers = set()

        # Get suppliers from invoices
        invoices = self.get_all_invoices()
        for inv in invoices:
            name = inv.get('supplier_name', '').strip()
            if name:
                suppliers.add(name)

        # Get suppliers from payment details
        payments = self.get_all_payment_details()
        for pay in payments:
            name = pay.get('supplier_name', '').strip()
            if name:
                suppliers.add(name)

        return sorted(list(suppliers))

    def initialize_sheets(self) -> dict:
        """
        Initialize sheets with headers if they don't exist

        Returns:
            dict: Result with 'success' and 'message'
        """
        self._ensure_authenticated()

        results = {'invoice_sheet': None, 'payment_sheet': None}

        try:
            # Check and initialize Invoice Tracker sheet
            try:
                range_name = f"'{self.invoice_sheet}'!A1:K1"
                result = self.service.spreadsheets().values().get(
                    spreadsheetId=self.spreadsheet_id,
                    range=range_name
                ).execute()

                if not result.get('values'):
                    # Add headers
                    body = {'values': [INVOICE_COLUMNS]}
                    self.service.spreadsheets().values().update(
                        spreadsheetId=self.spreadsheet_id,
                        range=range_name,
                        valueInputOption='USER_ENTERED',
                        body=body
                    ).execute()
                    results['invoice_sheet'] = 'Headers added'
                    logger.info("Added headers to Invoice Tracker sheet")
                else:
                    results['invoice_sheet'] = 'Already initialized'

            except HttpError as e:
                results['invoice_sheet'] = f'Error: {e}'

            # Check and initialize Payment Details sheet
            try:
                range_name = f"'{self.payment_sheet}'!A1:M1"
                result = self.service.spreadsheets().values().get(
                    spreadsheetId=self.spreadsheet_id,
                    range=range_name
                ).execute()

                if not result.get('values'):
                    body = {'values': [PAYMENT_COLUMNS]}
                    self.service.spreadsheets().values().update(
                        spreadsheetId=self.spreadsheet_id,
                        range=range_name,
                        valueInputOption='USER_ENTERED',
                        body=body
                    ).execute()
                    results['payment_sheet'] = 'Headers added'
                    logger.info("Added headers to Payment Details sheet")
                else:
                    results['payment_sheet'] = 'Already initialized'

            except HttpError as e:
                results['payment_sheet'] = f'Error: {e}'

            return {
                'success': True,
                'message': 'Sheets initialized',
                'details': results
            }

        except Exception as e:
            return {'success': False, 'message': f'Initialization failed: {e}'}

    def test_connection(self) -> dict:
        """
        Test the connection to Google Sheets

        Returns:
            dict: Result with connection status
        """
        self._ensure_authenticated()

        try:
            # Try to get spreadsheet metadata
            result = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()

            sheet_names = [s['properties']['title'] for s in result.get('sheets', [])]

            return {
                'success': True,
                'message': 'Connection successful',
                'spreadsheet_title': result.get('properties', {}).get('title'),
                'sheets': sheet_names,
                'spreadsheet_id': self.spreadsheet_id
            }

        except HttpError as e:
            return {
                'success': False,
                'message': f'Connection failed: {e}',
                'spreadsheet_id': self.spreadsheet_id
            }


# ========== Convenience Functions ==========

def save_to_sheets(invoice_data: dict) -> dict:
    """
    Convenience function to save invoice data

    Args:
        invoice_data: Invoice data dictionary

    Returns:
        dict: Result of the operation
    """
    manager = SheetsManager()
    return manager.add_invoice(invoice_data)


def save_payment_details(payment_data: dict) -> dict:
    """
    Convenience function to save payment details

    Args:
        payment_data: Payment data dictionary

    Returns:
        dict: Result of the operation
    """
    manager = SheetsManager()
    return manager.add_payment_details(payment_data)


def get_invoices() -> list[dict]:
    """
    Convenience function to get all invoices

    Returns:
        List of invoice dictionaries
    """
    manager = SheetsManager()
    return manager.get_all_invoices()


def get_payments() -> list[dict]:
    """
    Convenience function to get all payment details

    Returns:
        List of payment detail dictionaries
    """
    manager = SheetsManager()
    return manager.get_all_payment_details()


# ========== Test Functions ==========

def run_tests():
    """Run comprehensive tests on the SheetsManager"""
    print("=" * 60)
    print("Google Sheets Manager - Test Suite")
    print("=" * 60)

    try:
        # Initialize manager
        print("\n1. Initializing SheetsManager...")
        manager = SheetsManager()
        print("   SUCCESS: Manager initialized")

        # Test connection
        print("\n2. Testing connection...")
        conn_result = manager.test_connection()
        if conn_result['success']:
            print(f"   SUCCESS: Connected to '{conn_result.get('spreadsheet_title')}'")
            print(f"   Sheets found: {conn_result.get('sheets')}")
        else:
            print(f"   FAILED: {conn_result.get('message')}")
            return

        # Initialize sheets (add headers if needed)
        print("\n3. Initializing sheets...")
        init_result = manager.initialize_sheets()
        print(f"   Invoice Tracker: {init_result['details'].get('invoice_sheet')}")
        print(f"   Payment Details: {init_result['details'].get('payment_sheet')}")

        # Create test invoice
        print("\n4. Adding test invoice...")
        test_invoice = {
            'invoice_number': f'TEST-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'supplier_name': 'Test Supplier Ltd',
            'contact_email': 'accounts@testsupplier.com',
            'contact_phone': '+44 20 7123 4567',
            'invoice_date': datetime.now().strftime('%Y-%m-%d'),
            'due_date': '2026-02-28',
            'amount': 1250.00,
            'currency': 'GBP',
            'status': 'Pending Review',
            'notes': 'Test invoice created by sheets_manager.py'
        }

        add_result = manager.add_invoice(test_invoice)
        if add_result['success']:
            print(f"   SUCCESS: {add_result.get('message')}")
            print(f"   Invoice Number: {test_invoice['invoice_number']}")
        else:
            print(f"   FAILED: {add_result.get('message')}")

        # Read back invoices
        print("\n5. Reading invoices...")
        invoices = manager.get_all_invoices()
        print(f"   Found {len(invoices)} invoice(s)")

        # Find our test invoice
        test_found = manager.get_invoice_by_number(test_invoice['invoice_number'])
        if test_found:
            print(f"   SUCCESS: Retrieved test invoice")
            print(f"   - Supplier: {test_found.get('supplier_name')}")
            print(f"   - Amount: {test_found.get('currency')} {test_found.get('amount')}")
        else:
            print("   WARNING: Could not find test invoice")

        # Get invoice statistics
        print("\n6. Getting invoice statistics...")
        stats = manager.get_invoice_stats()
        print(f"   Total Invoices: {stats.get('total_invoices')}")
        print(f"   Paid: {stats.get('paid')}")
        print(f"   Pending: {stats.get('pending')}")
        print(f"   Overdue: {stats.get('overdue')}")
        print(f"   Total Amount: GBP {stats.get('total_amount', 0):.2f}")

        # Add test payment details
        print("\n7. Adding test payment details...")
        test_payment = {
            'supplier_name': 'Test Supplier Ltd',
            'beneficiary_account_name': 'Test Supplier Ltd',
            'account_number': '12345678',
            'iban': 'GB29NWBK60161331926819',
            'sort_code': '60-16-13',
            'swift_code': 'NWBKGB2L',
            'bank_name': 'NatWest',
            'bank_address': '250 Bishopsgate, London EC2M 4AA',
            'payment_reference': test_invoice['invoice_number'],
            'status': 'Ready for Upload',
            'notes': 'Test payment details'
        }

        pay_result = manager.add_payment_details(test_payment)
        if pay_result['success']:
            print(f"   SUCCESS: {pay_result.get('message')}")
        else:
            print(f"   FAILED: {pay_result.get('message')}")

        # Read payment details
        print("\n8. Reading payment details...")
        payments = manager.get_all_payment_details()
        print(f"   Found {len(payments)} payment record(s)")

        # Get unique suppliers
        print("\n9. Getting unique suppliers...")
        suppliers = manager.get_unique_suppliers()
        print(f"   Found {len(suppliers)} unique supplier(s)")
        for s in suppliers[:5]:  # Show first 5
            print(f"   - {s}")
        if len(suppliers) > 5:
            print(f"   ... and {len(suppliers) - 5} more")

        print("\n" + "=" * 60)
        print("All tests completed successfully!")
        print("=" * 60)

    except AuthenticationError as e:
        print(f"\nAuthentication Error: {e}")
        print("Please ensure credentials.json is in the project directory")
        print("and run the script again to complete OAuth flow.")

    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    run_tests()
