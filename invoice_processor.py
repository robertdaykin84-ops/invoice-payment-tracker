"""
Invoice Processor - Extracts data from invoice PDFs and images using Claude API
"""

import os
import json
import re
import base64
from pathlib import Path
from datetime import datetime
from typing import Optional
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()


class InvoiceProcessor:
    """Process invoices using Claude API for OCR and data extraction"""

    # Supported file extensions
    SUPPORTED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg'}

    # Media type mapping
    MEDIA_TYPE_MAP = {
        '.pdf': 'application/pdf',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg'
    }

    def __init__(self):
        """Initialize the processor with API key"""
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        self.client = Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"

    def _validate_file(self, file_path: str) -> Path:
        """
        Validate the file exists and is a supported type

        Args:
            file_path: Path to the file

        Returns:
            Path object

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file type not supported
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type: {path.suffix}. "
                f"Supported types: {', '.join(self.SUPPORTED_EXTENSIONS)}"
            )

        return path

    def _encode_file(self, file_path: Path) -> tuple[str, str]:
        """
        Read and encode file to base64

        Args:
            file_path: Path to the file

        Returns:
            Tuple of (base64_data, media_type)
        """
        with open(file_path, 'rb') as f:
            file_data = f.read()

        media_type = self.MEDIA_TYPE_MAP.get(
            file_path.suffix.lower(),
            'application/pdf'
        )
        file_base64 = base64.b64encode(file_data).decode('utf-8')

        return file_base64, media_type

    def _build_extraction_prompt(self) -> str:
        """Build the extraction prompt for Claude"""
        return """Analyze this invoice document and extract the following information. Return a JSON object with these exact fields:

{
  "invoice_number": "The invoice/reference number",
  "supplier_name": "The supplier/vendor company name",
  "contact_email": "Supplier's email address",
  "contact_phone": "Supplier's phone number",
  "invoice_date": "Invoice date in YYYY-MM-DD format",
  "due_date": "Payment due date in YYYY-MM-DD format",
  "amount": 0.00,
  "currency": "GBP",
  "line_items": [
    {
      "description": "Item description",
      "quantity": 1,
      "unit_price": 0.00,
      "total": 0.00
    }
  ],
  "subtotal": 0.00,
  "tax_amount": 0.00,
  "tax_rate": "e.g., 20% VAT",
  "notes": "Any payment terms or special instructions",
  "payment_details": {
    "beneficiary_account_name": "Name on the bank account to pay",
    "account_number": "Bank account number",
    "iban": "IBAN if provided",
    "sort_code": "Sort code (UK) or routing number",
    "swift_code": "SWIFT/BIC code for international payments",
    "bank_name": "Name of the bank",
    "bank_address": "Bank branch address if provided",
    "payment_reference": "Reference to use when making payment"
  },
  "confidence": {
    "invoice_number": "high/medium/low",
    "supplier_name": "high/medium/low",
    "amount": "high/medium/low",
    "dates": "high/medium/low",
    "payment_details": "high/medium/low"
  }
}

Important instructions:
1. For dates: Convert to YYYY-MM-DD format. If only partial date visible, make reasonable assumptions based on context.
2. For amounts: Extract as numbers without currency symbols. Use the grand total/amount due, not subtotal.
3. For currency: Detect from symbols (£=GBP, $=USD, €=EUR) or text. Default to GBP if unclear.
4. For phone numbers: Include country code if visible.
5. For confidence: Rate as "high" if clearly visible, "medium" if partially visible or inferred, "low" if guessed.
6. If a field is not found, use empty string "" for text, 0 for numbers, or empty array [] for line_items.
7. For payment_details: Look for bank details, remittance information, "Pay to", account details sections. Extract all banking information found.

Return ONLY the JSON object, no additional text or markdown formatting."""

    def _parse_response(self, response_text: str) -> dict:
        """
        Parse the Claude response into a dictionary

        Args:
            response_text: Raw response from Claude

        Returns:
            Parsed dictionary
        """
        # Clean up the response
        text = response_text.strip()

        # Remove markdown code blocks if present
        if text.startswith('```json'):
            text = text[7:]
        elif text.startswith('```'):
            text = text[3:]

        if text.endswith('```'):
            text = text[:-3]

        text = text.strip()

        # Parse JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            # Try to extract JSON from the response
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError(f"Failed to parse JSON response: {e}")

    def _validate_and_clean_data(self, data: dict) -> dict:
        """
        Validate and clean the extracted data

        Args:
            data: Raw extracted data

        Returns:
            Cleaned and validated data
        """
        # Define default values
        defaults = {
            'invoice_number': '',
            'supplier_name': '',
            'contact_email': '',
            'contact_phone': '',
            'invoice_date': '',
            'due_date': '',
            'amount': 0.0,
            'currency': 'GBP',
            'line_items': [],
            'subtotal': 0.0,
            'tax_amount': 0.0,
            'tax_rate': '',
            'notes': '',
            'payment_details': {
                'beneficiary_account_name': '',
                'account_number': '',
                'iban': '',
                'sort_code': '',
                'swift_code': '',
                'bank_name': '',
                'bank_address': '',
                'payment_reference': ''
            },
            'confidence': {
                'invoice_number': 'low',
                'supplier_name': 'low',
                'amount': 'low',
                'dates': 'low',
                'payment_details': 'low'
            }
        }

        # Merge with defaults
        result = {**defaults, **data}

        # Clean and validate specific fields

        # Clean amount - ensure it's a float
        try:
            amount = result.get('amount', 0)
            if isinstance(amount, str):
                # Remove currency symbols and commas
                amount = re.sub(r'[£$€,\s]', '', amount)
            result['amount'] = float(amount) if amount else 0.0
        except (ValueError, TypeError):
            result['amount'] = 0.0

        # Clean subtotal and tax
        for field in ['subtotal', 'tax_amount']:
            try:
                value = result.get(field, 0)
                if isinstance(value, str):
                    value = re.sub(r'[£$€,\s]', '', value)
                result[field] = float(value) if value else 0.0
            except (ValueError, TypeError):
                result[field] = 0.0

        # Validate and format dates
        for date_field in ['invoice_date', 'due_date']:
            date_value = result.get(date_field, '')
            if date_value:
                result[date_field] = self._normalize_date(date_value)

        # Clean currency
        currency = result.get('currency', 'GBP').upper().strip()
        valid_currencies = {'GBP', 'USD', 'EUR', 'CAD', 'AUD', 'JPY', 'CHF', 'CNY', 'INR', 'MXN'}
        if currency not in valid_currencies:
            # Try to detect from symbols in the original data
            if '£' in str(data.get('amount', '')):
                currency = 'GBP'
            elif '$' in str(data.get('amount', '')):
                currency = 'USD'
            elif '€' in str(data.get('amount', '')):
                currency = 'EUR'
            else:
                currency = 'GBP'  # Default
        result['currency'] = currency

        # Clean phone number
        phone = result.get('contact_phone', '')
        if phone:
            # Remove extra spaces but keep formatting
            result['contact_phone'] = ' '.join(phone.split())

        # Clean email
        email = result.get('contact_email', '')
        if email:
            result['contact_email'] = email.lower().strip()

        # Validate line items
        line_items = result.get('line_items', [])
        if isinstance(line_items, list):
            cleaned_items = []
            for item in line_items:
                if isinstance(item, dict):
                    cleaned_item = {
                        'description': str(item.get('description', '')),
                        'quantity': float(item.get('quantity', 1) or 1),
                        'unit_price': float(item.get('unit_price', 0) or 0),
                        'total': float(item.get('total', 0) or 0)
                    }
                    cleaned_items.append(cleaned_item)
            result['line_items'] = cleaned_items
        else:
            result['line_items'] = []

        # Clean and validate payment_details
        payment_details = result.get('payment_details', {})
        if isinstance(payment_details, dict):
            cleaned_payment = {
                'beneficiary_account_name': str(payment_details.get('beneficiary_account_name', '')).strip(),
                'account_number': str(payment_details.get('account_number', '')).strip(),
                'iban': str(payment_details.get('iban', '')).strip().upper(),
                'sort_code': str(payment_details.get('sort_code', '')).strip(),
                'swift_code': str(payment_details.get('swift_code', '')).strip().upper(),
                'bank_name': str(payment_details.get('bank_name', '')).strip(),
                'bank_address': str(payment_details.get('bank_address', '')).strip(),
                'payment_reference': str(payment_details.get('payment_reference', '')).strip()
            }
            result['payment_details'] = cleaned_payment
        else:
            result['payment_details'] = defaults['payment_details']

        # Ensure confidence is properly structured
        if not isinstance(result.get('confidence'), dict):
            result['confidence'] = defaults['confidence']

        return result

    def _normalize_date(self, date_str: str) -> str:
        """
        Normalize date string to YYYY-MM-DD format

        Args:
            date_str: Date string in various formats

        Returns:
            Date in YYYY-MM-DD format or empty string
        """
        if not date_str:
            return ''

        # Common date formats to try
        formats = [
            '%Y-%m-%d',      # 2024-01-15
            '%d/%m/%Y',      # 15/01/2024
            '%m/%d/%Y',      # 01/15/2024
            '%d-%m-%Y',      # 15-01-2024
            '%d %B %Y',      # 15 January 2024
            '%d %b %Y',      # 15 Jan 2024
            '%B %d, %Y',     # January 15, 2024
            '%b %d, %Y',     # Jan 15, 2024
            '%Y/%m/%d',      # 2024/01/15
        ]

        # Clean the date string
        date_str = date_str.strip()

        for fmt in formats:
            try:
                parsed = datetime.strptime(date_str, fmt)
                return parsed.strftime('%Y-%m-%d')
            except ValueError:
                continue

        # If no format matched, return as-is if it looks like YYYY-MM-DD
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return date_str

        return ''

    def process_invoice(self, file_path: str) -> dict:
        """
        Extract invoice data from a PDF or image file

        Args:
            file_path: Path to the invoice file

        Returns:
            dict: Extracted invoice data with fields:
                - invoice_number
                - supplier_name
                - contact_email
                - contact_phone
                - invoice_date
                - due_date
                - amount
                - currency
                - line_items
                - subtotal
                - tax_amount
                - tax_rate
                - notes
                - confidence
                - file_path (added for reference)
                - processed_at (timestamp)
        """
        try:
            # Validate file
            path = self._validate_file(file_path)

            # Encode file
            file_base64, media_type = self._encode_file(path)

            # Build prompt
            prompt = self._build_extraction_prompt()

            # Build message content based on file type
            if media_type == 'application/pdf':
                content = [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": file_base64
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            else:
                # For images
                content = [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": file_base64
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]

            # Call Claude API
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": content
                    }
                ]
            )

            # Parse response
            response_text = message.content[0].text
            extracted_data = self._parse_response(response_text)

            # Validate and clean
            cleaned_data = self._validate_and_clean_data(extracted_data)

            # Add metadata
            cleaned_data['file_path'] = str(path.absolute())
            cleaned_data['processed_at'] = datetime.now().isoformat()
            cleaned_data['status'] = 'pending'  # Default status for new invoices

            return cleaned_data

        except FileNotFoundError as e:
            return self._error_response(str(e), file_path, 'file_not_found')
        except ValueError as e:
            return self._error_response(str(e), file_path, 'validation_error')
        except json.JSONDecodeError as e:
            return self._error_response(f"Failed to parse API response: {e}", file_path, 'parse_error')
        except Exception as e:
            return self._error_response(f"Processing failed: {e}", file_path, 'processing_error')

    def _error_response(self, error_message: str, file_path: str, error_type: str) -> dict:
        """
        Generate a standardized error response

        Args:
            error_message: The error message
            file_path: Path to the file that caused the error
            error_type: Type of error

        Returns:
            Error response dictionary
        """
        return {
            'invoice_number': '',
            'supplier_name': '',
            'contact_email': '',
            'contact_phone': '',
            'invoice_date': '',
            'due_date': '',
            'amount': 0.0,
            'currency': 'GBP',
            'line_items': [],
            'subtotal': 0.0,
            'tax_amount': 0.0,
            'tax_rate': '',
            'notes': '',
            'confidence': {
                'invoice_number': 'low',
                'supplier_name': 'low',
                'amount': 'low',
                'dates': 'low'
            },
            'file_path': str(file_path),
            'processed_at': datetime.now().isoformat(),
            'status': 'error',
            'error': error_message,
            'error_type': error_type
        }

    def process_multiple(self, file_paths: list[str]) -> list[dict]:
        """
        Process multiple invoice files

        Args:
            file_paths: List of file paths

        Returns:
            List of extracted data dictionaries
        """
        results = []
        for path in file_paths:
            result = self.process_invoice(path)
            results.append(result)
        return results


def process_invoice(file_path: str) -> dict:
    """
    Convenience function to process a single invoice

    Args:
        file_path: Path to invoice file

    Returns:
        Extracted invoice data
    """
    processor = InvoiceProcessor()
    return processor.process_invoice(file_path)


def process_invoices(file_paths: list[str]) -> list[dict]:
    """
    Convenience function to process multiple invoices

    Args:
        file_paths: List of invoice file paths

    Returns:
        List of extracted invoice data
    """
    processor = InvoiceProcessor()
    return processor.process_multiple(file_paths)


if __name__ == '__main__':
    import sys

    print("Invoice Processor - Claude API Integration")
    print("=" * 50)

    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        print(f"\nProcessing: {test_file}")
        print("-" * 50)

        try:
            result = process_invoice(test_file)

            if result.get('error'):
                print(f"\nError: {result['error']}")
                print(f"Error Type: {result.get('error_type', 'unknown')}")
            else:
                print("\nExtracted Data:")
                print(json.dumps(result, indent=2, default=str))

                # Summary
                print("\n" + "=" * 50)
                print("Summary:")
                print(f"  Invoice #:    {result.get('invoice_number', 'N/A')}")
                print(f"  Supplier:     {result.get('supplier_name', 'N/A')}")
                print(f"  Amount:       {result.get('currency', '')} {result.get('amount', 0):.2f}")
                print(f"  Invoice Date: {result.get('invoice_date', 'N/A')}")
                print(f"  Due Date:     {result.get('due_date', 'N/A')}")
                print(f"  Line Items:   {len(result.get('line_items', []))}")

                # Confidence scores
                confidence = result.get('confidence', {})
                print("\nConfidence Scores:")
                for field, score in confidence.items():
                    print(f"  {field}: {score}")

        except Exception as e:
            print(f"\nFatal error: {e}")
            sys.exit(1)
    else:
        print("\nUsage: python invoice_processor.py <path_to_invoice>")
        print("\nSupported file types:")
        for ext in InvoiceProcessor.SUPPORTED_EXTENSIONS:
            print(f"  - {ext}")
        print("\nExample:")
        print("  python invoice_processor.py invoice.pdf")
        print("  python invoice_processor.py receipt.png")
