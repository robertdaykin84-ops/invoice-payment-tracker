"""
AI Document Review Service
Uses Claude API to analyze uploaded documents for JFSC compliance
"""

import os
import base64
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import Anthropic SDK
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic SDK not available - document review will use demo mode")


# JFSC-compliant certification requirements
CERTIFICATION_REQUIREMENTS = {
    'acceptable_certifiers': [
        'lawyer', 'solicitor', 'barrister', 'attorney',
        'notary', 'notary public',
        'accountant', 'chartered accountant', 'certified accountant', 'cpa',
    ],
    'required_wording': [
        'certify this is a true copy',
        'certified true copy',
        'true copy of the original',
        'certified copy of the original',
    ],
    'required_elements': [
        'signature',
        'printed name',
        'qualification',
        'date',
    ]
}

# Document type detection patterns
DOCUMENT_TYPES = {
    'passport': ['passport', 'travel document', 'laissez-passer'],
    'address_proof': ['utility bill', 'bank statement', 'council tax', 'electricity', 'gas bill', 'water bill'],
    'certificate_of_incorporation': ['certificate of incorporation', 'incorporation certificate'],
    'certificate_of_registration': ['certificate of registration', 'registration certificate'],
    'memorandum_articles': ['memorandum', 'articles of association', 'm&a', 'constitution'],
    'llp_agreement': ['llp agreement', 'limited liability partnership agreement', 'partnership deed'],
    'register_of_directors': ['register of directors', 'directors register', 'list of directors'],
    'register_of_shareholders': ['register of shareholders', 'shareholders register', 'register of members'],
    'register_of_members': ['register of members', 'members register'],
    'structure_chart': ['structure chart', 'ownership structure', 'org chart', 'organisational structure'],
    'trust_deed': ['trust deed', 'deed of trust', 'trust instrument'],
    'regulatory_license': ['license', 'licence', 'authorisation', 'authorization', 'registration certificate'],
}


class DocumentReviewService:
    """Service for AI-powered document review"""

    def __init__(self):
        self.demo_mode = not ANTHROPIC_AVAILABLE or not os.environ.get('ANTHROPIC_API_KEY')
        self.client = None

        if not self.demo_mode:
            try:
                self.client = anthropic.Anthropic()
                logger.info("Document Review Service initialized with Claude API")
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic client: {e}")
                self.demo_mode = True

        if self.demo_mode:
            logger.info("Document Review Service running in DEMO MODE")

    def analyze_document(
        self,
        file_content: bytes,
        file_name: str,
        mime_type: str,
        expected_type: Optional[str] = None,
        expected_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze a single document using Claude API.

        Args:
            file_content: Raw file bytes
            file_name: Original filename
            mime_type: MIME type of the file
            expected_type: Expected document type (e.g., 'passport')
            expected_name: Expected name to match (for ID documents)

        Returns:
            Analysis results with checks and extracted data
        """
        if self.demo_mode:
            return self._demo_analysis(file_name, expected_type, expected_name)

        try:
            # Encode file for Claude
            file_b64 = base64.standard_b64encode(file_content).decode('utf-8')

            # Build the analysis prompt
            prompt = self._build_analysis_prompt(expected_type, expected_name)

            # Determine media type for Claude
            media_type = self._get_claude_media_type(mime_type)

            # Call Claude API with vision
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": file_b64
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )

            # Parse Claude's response
            return self._parse_analysis_response(response.content[0].text, expected_type, expected_name)

        except Exception as e:
            logger.error(f"Document analysis failed: {e}")
            return {
                'overall_status': 'error',
                'error': str(e),
                'checks': {},
                'extracted_data': {}
            }

    def analyze_batch(
        self,
        documents: List[Dict],
        key_parties: List[Dict],
        sponsor_name: str
    ) -> List[Dict]:
        """
        Analyze a batch of documents and auto-assign to checklist items.

        Args:
            documents: List of {'content': bytes, 'filename': str, 'mime_type': str}
            key_parties: List of key parties with names
            sponsor_name: Sponsor entity name

        Returns:
            List of analysis results with suggested assignments
        """
        results = []

        for doc in documents:
            # First, detect the document type
            analysis = self.analyze_document(
                file_content=doc['content'],
                file_name=doc['filename'],
                mime_type=doc['mime_type']
            )

            # Try to match to a key party if it's an ID document
            suggested_assignment = self._suggest_assignment(
                analysis,
                key_parties,
                sponsor_name
            )

            results.append({
                'filename': doc['filename'],
                'analysis': analysis,
                'suggested_assignment': suggested_assignment
            })

        return results

    def _build_analysis_prompt(self, expected_type: Optional[str], expected_name: Optional[str]) -> str:
        """Build the analysis prompt for Claude"""
        prompt = """Analyze this document and provide a JSON response with the following structure:

{
    "detected_type": "passport|address_proof|certificate_of_incorporation|...",
    "confidence": 0.95,
    "extracted_data": {
        "name": "Full name if visible",
        "date_of_birth": "YYYY-MM-DD if visible",
        "document_number": "If visible",
        "expiry_date": "YYYY-MM-DD if visible",
        "address": "Full address if visible",
        "issuing_authority": "If visible"
    },
    "certification": {
        "is_certified": true|false,
        "certification_wording": "Exact wording found",
        "certifier_name": "Name of certifier",
        "certifier_qualification": "e.g., Solicitor, Notary Public",
        "certification_date": "YYYY-MM-DD",
        "has_signature": true|false
    },
    "quality": {
        "is_legible": true|false,
        "is_complete": true|false,
        "issues": ["List any quality issues"]
    }
}

IMPORTANT JFSC Requirements for certification:
- Must include wording like "I certify this is a true copy of the original"
- Must be certified by a lawyer, notary public, or chartered accountant
- Must include certifier's signature, printed name, qualification, and date
- Certification should be within 12 months for ID documents, 3 months for address proof

Respond ONLY with valid JSON, no additional text."""

        if expected_type:
            prompt += f"\n\nExpected document type: {expected_type}"
        if expected_name:
            prompt += f"\nExpected name to match: {expected_name}"

        return prompt

    def _get_claude_media_type(self, mime_type: str) -> str:
        """Convert MIME type to Claude-supported media type"""
        supported = {
            'application/pdf': 'application/pdf',
            'image/jpeg': 'image/jpeg',
            'image/jpg': 'image/jpeg',
            'image/png': 'image/png',
            'image/gif': 'image/gif',
            'image/webp': 'image/webp',
        }
        return supported.get(mime_type.lower(), 'application/pdf')

    def _parse_analysis_response(
        self,
        response_text: str,
        expected_type: Optional[str],
        expected_name: Optional[str]
    ) -> Dict[str, Any]:
        """Parse Claude's response and run validation checks"""
        try:
            # Extract JSON from response
            data = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to find JSON in the response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                return {
                    'overall_status': 'error',
                    'error': 'Could not parse AI response',
                    'checks': {},
                    'extracted_data': {}
                }

        # Run validation checks
        checks = {}

        # Document type check
        detected_type = data.get('detected_type', 'unknown')
        if expected_type:
            type_match = detected_type.lower() == expected_type.lower()
            checks['document_type_match'] = {
                'status': 'pass' if type_match else 'fail',
                'detail': f"Detected: {detected_type}" + ("" if type_match else f", Expected: {expected_type}")
            }
        else:
            checks['document_type_match'] = {
                'status': 'pass',
                'detail': f"Detected: {detected_type}"
            }

        # Certification checks
        cert = data.get('certification', {})

        if cert.get('is_certified'):
            # Check wording
            wording = (cert.get('certification_wording') or '').lower()
            wording_ok = any(req in wording for req in CERTIFICATION_REQUIREMENTS['required_wording'])
            checks['certification_wording'] = {
                'status': 'pass' if wording_ok else 'review_needed',
                'detail': cert.get('certification_wording', 'No certification wording found')
            }

            # Check certifier qualification
            qualification = (cert.get('certifier_qualification') or '').lower()
            qual_ok = any(q in qualification for q in CERTIFICATION_REQUIREMENTS['acceptable_certifiers'])
            checks['certifier_details'] = {
                'status': 'pass' if qual_ok else 'review_needed',
                'detail': f"{cert.get('certifier_name', 'Unknown')}, {cert.get('certifier_qualification', 'Unknown')}, {cert.get('certification_date', 'No date')}"
            }

            # Check certification date
            cert_date = cert.get('certification_date')
            if cert_date:
                from datetime import datetime, timedelta
                try:
                    cert_dt = datetime.strptime(cert_date, '%Y-%m-%d')
                    months_old = (datetime.now() - cert_dt).days / 30
                    max_months = 3 if detected_type == 'address_proof' else 12
                    date_ok = months_old <= max_months
                    checks['certification_date'] = {
                        'status': 'pass' if date_ok else 'review_needed',
                        'detail': f"{cert_date} ({int(months_old)} months old)"
                    }
                except ValueError:
                    checks['certification_date'] = {
                        'status': 'review_needed',
                        'detail': f"Could not parse date: {cert_date}"
                    }
            else:
                checks['certification_date'] = {
                    'status': 'review_needed',
                    'detail': 'No certification date found'
                }
        else:
            checks['certification_wording'] = {
                'status': 'fail',
                'detail': 'Document does not appear to be certified'
            }
            checks['certifier_details'] = {
                'status': 'fail',
                'detail': 'No certifier details found'
            }
            checks['certification_date'] = {
                'status': 'fail',
                'detail': 'No certification date found'
            }

        # Document expiry check (for passports/IDs)
        extracted = data.get('extracted_data', {})
        if extracted.get('expiry_date'):
            try:
                expiry_dt = datetime.strptime(extracted['expiry_date'], '%Y-%m-%d')
                from datetime import timedelta
                min_valid = datetime.now() + timedelta(days=90)
                expiry_ok = expiry_dt >= min_valid
                checks['document_expiry'] = {
                    'status': 'pass' if expiry_ok else 'review_needed',
                    'detail': f"Expires: {extracted['expiry_date']}"
                }
            except ValueError:
                pass

        # Name matching check
        if expected_name and extracted.get('name'):
            name_match = self._fuzzy_name_match(extracted['name'], expected_name)
            checks['name_match'] = {
                'status': 'pass' if name_match['match'] else 'review_needed',
                'detail': f"Document: '{extracted['name']}' vs Expected: '{expected_name}'" +
                         ("" if name_match['match'] else f" ({name_match['reason']})")
            }

        # Image quality check
        quality = data.get('quality', {})
        quality_ok = quality.get('is_legible', True) and quality.get('is_complete', True)
        checks['image_quality'] = {
            'status': 'pass' if quality_ok else 'review_needed',
            'detail': 'Clear and legible' if quality_ok else ', '.join(quality.get('issues', ['Quality issues detected']))
        }

        # Determine overall status
        statuses = [c['status'] for c in checks.values()]
        if 'fail' in statuses:
            overall = 'fail'
        elif 'review_needed' in statuses:
            overall = 'review_needed'
        else:
            overall = 'pass'

        return {
            'overall_status': overall,
            'confidence': data.get('confidence', 0.0),
            'detected_type': detected_type,
            'checks': checks,
            'extracted_data': extracted,
            'certification': cert
        }

    def _fuzzy_name_match(self, name1: str, name2: str) -> Dict:
        """Check if two names match (allowing for middle names, etc.)"""
        n1_parts = set(name1.lower().split())
        n2_parts = set(name2.lower().split())

        # Check if at least first and last name match
        common = n1_parts & n2_parts

        if len(common) >= 2:
            return {'match': True, 'reason': 'Names match'}
        elif len(common) >= 1:
            return {'match': False, 'reason': 'Partial match - verify manually'}
        else:
            return {'match': False, 'reason': 'Names do not match'}

    def _suggest_assignment(
        self,
        analysis: Dict,
        key_parties: List[Dict],
        sponsor_name: str
    ) -> Dict:
        """Suggest checklist assignment based on analysis"""
        detected_type = analysis.get('detected_type', 'unknown')
        extracted_name = analysis.get('extracted_data', {}).get('name')

        # Check if it's a personal ID document
        personal_doc_types = ['passport', 'address_proof']
        if detected_type in personal_doc_types and extracted_name:
            # Try to match to a key party
            for party in key_parties:
                party_name = party.get('name', '')
                match = self._fuzzy_name_match(extracted_name, party_name)
                if match['match']:
                    return {
                        'type': 'key_party',
                        'person_id': party.get('person_id'),
                        'person_name': party_name,
                        'document_type': detected_type,
                        'confidence': analysis.get('confidence', 0.5)
                    }

        # Check if it's an entity document
        entity_doc_types = [
            'certificate_of_incorporation', 'certificate_of_registration',
            'memorandum_articles', 'llp_agreement', 'register_of_directors',
            'register_of_shareholders', 'register_of_members', 'structure_chart',
            'trust_deed', 'regulatory_license'
        ]
        if detected_type in entity_doc_types:
            return {
                'type': 'sponsor',
                'document_type': detected_type,
                'confidence': analysis.get('confidence', 0.5)
            }

        return {
            'type': 'unassigned',
            'detected_type': detected_type,
            'confidence': analysis.get('confidence', 0.0)
        }

    def _detect_type_from_filename(self, filename: str) -> str:
        """Detect document type from filename keywords."""
        # Normalize filename: convert hyphens and underscores to spaces
        filename_lower = filename.lower().replace('-', ' ').replace('_', ' ')

        for doc_type, keywords in DOCUMENT_TYPES.items():
            for keyword in keywords:
                if keyword in filename_lower:
                    return doc_type

        return 'unassigned'

    def _calculate_realistic_confidence(self, filename: str, detected_type: str) -> float:
        """Calculate realistic confidence based on filename match quality."""
        # Normalize filename: convert hyphens and underscores to spaces, remove extension
        filename_lower = filename.lower().replace('-', ' ').replace('_', ' ').replace('.pdf', '').replace('.png', '').replace('.jpg', '').replace('.jpeg', '')

        if detected_type == 'unassigned':
            return 0.0

        # Check for exact keyword match
        keywords = DOCUMENT_TYPES.get(detected_type, [])
        for keyword in keywords:
            if keyword in filename_lower:
                # Exact match: high confidence
                if keyword == filename_lower.strip():
                    return 0.95
                # Contains keyword: medium-high confidence
                confidence = 0.75 + (len(keyword) / 50.0)
                return min(confidence, 0.95)  # Cap at 0.95

        return 0.60  # Low confidence fallback

    def _demo_analysis(
        self,
        file_name: str,
        expected_type: Optional[str],
        expected_name: Optional[str]
    ) -> Dict[str, Any]:
        """Return demo analysis results"""
        logger.info(f"[DEMO] Analyzing document: {file_name}")

        # Use realistic detection based on filename
        detected_type = self._detect_type_from_filename(file_name)
        confidence = self._calculate_realistic_confidence(file_name, detected_type)

        return {
            'overall_status': 'pass',
            'confidence': confidence,
            'detected_type': detected_type,
            'checks': {
                'document_type_match': {'status': 'pass', 'detail': f'Detected: {detected_type}'},
                'certification_wording': {'status': 'pass', 'detail': 'I certify this is a true copy of the original'},
                'certifier_details': {'status': 'pass', 'detail': 'J. Smith, Solicitor, 15 Jan 2026'},
                'certification_date': {'status': 'pass', 'detail': '2026-01-15 (within 3 months)'},
                'image_quality': {'status': 'pass', 'detail': 'Clear and legible'}
            },
            'extracted_data': {
                'name': expected_name or 'John Smith',
                'document_number': 'AB123456',
                'expiry_date': '2030-06-20'
            },
            'certification': {
                'is_certified': True,
                'certification_wording': 'I certify this is a true copy of the original',
                'certifier_name': 'J. Smith',
                'certifier_qualification': 'Solicitor',
                'certification_date': '2026-01-15',
                'has_signature': True
            }
        }


# Singleton instance
_service = None


def get_service() -> DocumentReviewService:
    """Get or create document review service instance"""
    global _service
    if _service is None:
        _service = DocumentReviewService()
    return _service


def analyze_document(file_content: bytes, file_name: str, mime_type: str, **kwargs) -> Dict:
    """Convenience function to analyze a document"""
    return get_service().analyze_document(file_content, file_name, mime_type, **kwargs)


def analyze_batch(documents: List[Dict], key_parties: List[Dict], sponsor_name: str) -> List[Dict]:
    """Convenience function to analyze a batch of documents"""
    return get_service().analyze_batch(documents, key_parties, sponsor_name)
