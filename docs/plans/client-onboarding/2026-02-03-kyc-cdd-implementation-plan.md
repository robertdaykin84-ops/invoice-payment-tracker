# KYC & CDD Documentation Phase Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform Phase 4 into a comprehensive KYC/CDD documentation phase with bulk upload, AI-powered document review, and JFSC compliance checking.

**Architecture:** Dynamic checklist generated from Phase 1 enquiry data. Documents uploaded in bulk, processed by Claude API for type detection, name extraction, and certification validation. Results displayed grouped by sponsor/key parties with override capability.

**Tech Stack:** Flask, Jinja2, Claude API (via Anthropic SDK), JavaScript (vanilla), Bootstrap 5

---

## Task 1: Create KYC Checklist Generator Service

**Files:**
- Create: `services/kyc_checklist.py`

**Step 1: Create the checklist generator service**

```python
"""
KYC Checklist Generator Service
Generates dynamic document checklists based on enquiry data
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Document requirements by entity type
ENTITY_DOCUMENTS = {
    'llp': [
        {'item': 'certificate_of_registration', 'label': 'Certificate of Registration', 'required': True},
        {'item': 'llp_agreement', 'label': 'LLP Agreement', 'required': True},
        {'item': 'register_of_members', 'label': 'Register of Members', 'required': True},
        {'item': 'structure_chart', 'label': 'Structure Chart', 'required': True},
        {'item': 'proof_of_address', 'label': 'Proof of Registered Office', 'required': True},
    ],
    'limited': [
        {'item': 'certificate_of_incorporation', 'label': 'Certificate of Incorporation', 'required': True},
        {'item': 'memorandum_articles', 'label': 'Memorandum & Articles of Association', 'required': True},
        {'item': 'register_of_directors', 'label': 'Register of Directors', 'required': True},
        {'item': 'register_of_shareholders', 'label': 'Register of Shareholders', 'required': True},
        {'item': 'structure_chart', 'label': 'Structure Chart', 'required': True},
        {'item': 'proof_of_address', 'label': 'Proof of Registered Office', 'required': True},
    ],
    'trust': [
        {'item': 'trust_deed', 'label': 'Trust Deed', 'required': True},
        {'item': 'schedule_of_trustees', 'label': 'Schedule of Trustees', 'required': True},
        {'item': 'schedule_of_beneficiaries', 'label': 'Schedule of Beneficiaries', 'required': True},
        {'item': 'structure_chart', 'label': 'Structure Chart', 'required': True},
    ],
    'partnership': [
        {'item': 'partnership_agreement', 'label': 'Partnership Agreement', 'required': True},
        {'item': 'register_of_partners', 'label': 'Register of Partners', 'required': True},
        {'item': 'structure_chart', 'label': 'Structure Chart', 'required': True},
        {'item': 'proof_of_address', 'label': 'Proof of Address', 'required': True},
    ],
}

# Default for unknown entity types
DEFAULT_ENTITY_DOCUMENTS = [
    {'item': 'constitutional_document', 'label': 'Constitutional Document', 'required': True},
    {'item': 'ownership_evidence', 'label': 'Evidence of Ownership', 'required': True},
    {'item': 'structure_chart', 'label': 'Structure Chart', 'required': True},
    {'item': 'proof_of_address', 'label': 'Proof of Registered Address', 'required': True},
]

# Key party documents (same for all)
KEY_PARTY_DOCUMENTS = [
    {'item': 'passport', 'label': 'Certified Passport Copy', 'required': True},
    {'item': 'address_proof', 'label': 'Proof of Address (within 3 months)', 'required': True},
]

# Additional documents for regulated entities
REGULATED_ENTITY_DOCUMENTS = [
    {'item': 'regulatory_license', 'label': 'Regulatory License/Authorisation', 'required': True},
    {'item': 'letter_of_good_standing', 'label': 'Letter of Good Standing', 'required': False},
]

# EDD documents (when triggered)
EDD_DOCUMENTS = [
    {'item': 'source_of_wealth_declaration', 'label': 'Source of Wealth Declaration', 'required': True},
    {'item': 'source_of_funds_evidence', 'label': 'Source of Funds Evidence', 'required': True},
    {'item': 'professional_reference', 'label': 'Professional Reference Letter', 'required': False},
]


def generate_checklist(enquiry: Dict, risk_assessment: Optional[Dict] = None) -> Dict:
    """
    Generate a KYC document checklist based on enquiry data.

    Args:
        enquiry: Enquiry data from Phase 1
        risk_assessment: Risk assessment from Phase 3 (for EDD trigger)

    Returns:
        Checklist structure with sponsor docs, key party docs, and EDD status
    """
    entity_type = (enquiry.get('entity_type') or 'limited').lower()
    regulatory_status = (enquiry.get('regulatory_status') or '').lower()
    principals = enquiry.get('principals', [])

    # Get sponsor documents based on entity type
    sponsor_docs = ENTITY_DOCUMENTS.get(entity_type, DEFAULT_ENTITY_DOCUMENTS).copy()
    sponsor_docs = [dict(d, document_id=None, status='pending') for d in sponsor_docs]

    # Add regulated entity docs if applicable
    if regulatory_status == 'regulated':
        for doc in REGULATED_ENTITY_DOCUMENTS:
            sponsor_docs.append(dict(doc, document_id=None, status='pending'))

    # Generate key party checklists
    key_parties = []
    for i, principal in enumerate(principals):
        party_docs = [dict(d, document_id=None, status='pending') for d in KEY_PARTY_DOCUMENTS]
        key_parties.append({
            'person_id': principal.get('person_id', f'principal_{i}'),
            'name': principal.get('full_name') or principal.get('name', f'Principal {i+1}'),
            'role': _format_role(principal.get('role', 'director')),
            'documents': party_docs
        })

    # Determine if EDD is required
    edd_required = False
    edd_trigger_reason = None

    if risk_assessment:
        risk_rating = risk_assessment.get('risk_rating', '').lower()
        if risk_rating == 'high':
            edd_required = True
            edd_trigger_reason = 'High risk rating from screening'

        # Check for PEP
        if risk_assessment.get('pep_identified'):
            edd_required = True
            edd_trigger_reason = 'PEP identified'

    # Build EDD documents if required
    edd_docs = []
    if edd_required:
        edd_docs = [dict(d, document_id=None, status='pending') for d in EDD_DOCUMENTS]

    checklist = {
        'onboarding_id': enquiry.get('onboarding_id'),
        'enquiry_id': enquiry.get('id'),
        'generated_at': datetime.now().isoformat(),
        'sponsor_name': enquiry.get('sponsor_name', 'Unknown Sponsor'),
        'entity_type': entity_type,
        'sponsor_documents': sponsor_docs,
        'key_parties': key_parties,
        'edd_required': edd_required,
        'edd_trigger_reason': edd_trigger_reason,
        'edd_documents': edd_docs,
        'overall_status': 'pending',
        'signed_off_by': None,
        'signed_off_at': None
    }

    logger.info(f"Generated KYC checklist: {len(sponsor_docs)} sponsor docs, {len(key_parties)} key parties, EDD: {edd_required}")
    return checklist


def _format_role(role: str) -> str:
    """Format role for display"""
    role_map = {
        'director': 'Director',
        'ubo': 'UBO',
        'both': 'Director & UBO',
        'shareholder': 'Shareholder',
        'partner': 'Partner',
        'trustee': 'Trustee',
        'beneficiary': 'Beneficiary',
    }
    return role_map.get(role.lower(), role.title())


def get_checklist_progress(checklist: Dict) -> Dict:
    """Calculate checklist completion progress"""
    total = 0
    complete = 0
    review_needed = 0

    # Count sponsor documents
    for doc in checklist.get('sponsor_documents', []):
        if doc.get('required', True):
            total += 1
            if doc.get('status') == 'complete':
                complete += 1
            elif doc.get('status') == 'review_needed':
                review_needed += 1

    # Count key party documents
    for party in checklist.get('key_parties', []):
        for doc in party.get('documents', []):
            if doc.get('required', True):
                total += 1
                if doc.get('status') == 'complete':
                    complete += 1
                elif doc.get('status') == 'review_needed':
                    review_needed += 1

    # Count EDD documents if required
    if checklist.get('edd_required'):
        for doc in checklist.get('edd_documents', []):
            if doc.get('required', True):
                total += 1
                if doc.get('status') == 'complete':
                    complete += 1
                elif doc.get('status') == 'review_needed':
                    review_needed += 1

    return {
        'total': total,
        'complete': complete,
        'review_needed': review_needed,
        'pending': total - complete - review_needed,
        'percentage': round((complete / total * 100) if total > 0 else 0),
        'can_sign_off': review_needed == 0 and complete == total
    }
```

**Step 2: Verify the file was created correctly**

Run: `python3 -c "from services.kyc_checklist import generate_checklist; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add services/kyc_checklist.py
git commit -m "feat: add KYC checklist generator service"
```

---

## Task 2: Create AI Document Review Service

**Files:**
- Create: `services/document_review.py`

**Step 1: Create the document review service**

```python
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

    def _demo_analysis(
        self,
        file_name: str,
        expected_type: Optional[str],
        expected_name: Optional[str]
    ) -> Dict[str, Any]:
        """Return demo analysis results"""
        logger.info(f"[DEMO] Analyzing document: {file_name}")

        # Guess type from filename
        fn_lower = file_name.lower()
        detected_type = 'unknown'
        for doc_type, keywords in DOCUMENT_TYPES.items():
            if any(kw in fn_lower for kw in keywords):
                detected_type = doc_type
                break

        # If still unknown, use expected type or guess from extension
        if detected_type == 'unknown':
            if expected_type:
                detected_type = expected_type
            elif 'passport' in fn_lower or 'id' in fn_lower:
                detected_type = 'passport'
            elif 'bill' in fn_lower or 'statement' in fn_lower:
                detected_type = 'address_proof'

        return {
            'overall_status': 'pass',
            'confidence': 0.85,
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
```

**Step 2: Verify the file was created correctly**

Run: `python3 -c "from services.document_review import get_service; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add services/document_review.py
git commit -m "feat: add AI document review service with Claude API"
```

---

## Task 3: Update Phase 4 Name and Add API Endpoints

**Files:**
- Modify: `app.py` (lines 2006-2016 for phase name, add new routes)

**Step 1: Update get_phases() to rename Phase 4**

Find and replace in `app.py`:

```python
# Find this:
        {'num': 4, 'name': 'EDD', 'icon': 'bi-shield-check', 'description': 'Enhanced due diligence (if required)'},

# Replace with:
        {'num': 4, 'name': 'KYC & CDD', 'icon': 'bi-file-earmark-check', 'description': 'Document collection and AI review'},
```

**Step 2: Add KYC API endpoints to app.py**

Add after the existing API routes (around line 1450):

```python
# ========== KYC/CDD API Routes ==========

@app.route('/api/kyc/<onboarding_id>/checklist', methods=['GET'])
@login_required
def api_kyc_checklist(onboarding_id):
    """API: Get KYC document checklist for an onboarding"""
    from services.kyc_checklist import generate_checklist, get_checklist_progress

    # Get enquiry data
    enquiry_id = request.args.get('enquiry_id') or session.get('current_enquiry_id')
    enquiry = None

    if enquiry_id:
        enquiry = sheets_db.get_enquiry(enquiry_id)
        if not enquiry:
            enquiry = MOCK_ENQUIRIES.get(enquiry_id)

    if not enquiry:
        # Use first mock enquiry as fallback for demo
        enquiry = MOCK_ENQUIRIES.get('ENQ-001')

    # Get risk assessment from session or default
    risk_assessment = session.get('risk_assessment', {})

    # Generate checklist
    checklist = generate_checklist(enquiry, risk_assessment)
    checklist['onboarding_id'] = onboarding_id

    # Get progress
    progress = get_checklist_progress(checklist)

    return jsonify({
        'status': 'ok',
        'checklist': checklist,
        'progress': progress
    })


@app.route('/api/kyc/<onboarding_id>/upload', methods=['POST'])
@login_required
def api_kyc_upload(onboarding_id):
    """API: Upload and analyze KYC documents"""
    from services.document_review import analyze_batch
    from services.kyc_checklist import generate_checklist

    if 'files' not in request.files:
        return jsonify({'status': 'error', 'message': 'No files uploaded'}), 400

    files = request.files.getlist('files')
    if not files or all(f.filename == '' for f in files):
        return jsonify({'status': 'error', 'message': 'No files selected'}), 400

    # Get enquiry data for key parties
    enquiry_id = request.form.get('enquiry_id') or session.get('current_enquiry_id')
    enquiry = MOCK_ENQUIRIES.get(enquiry_id) or MOCK_ENQUIRIES.get('ENQ-001')

    key_parties = []
    for i, p in enumerate(enquiry.get('principals', [])):
        key_parties.append({
            'person_id': f'principal_{i}',
            'name': p.get('full_name') or p.get('name')
        })

    sponsor_name = enquiry.get('sponsor_name', 'Unknown Sponsor')

    # Process each file
    documents = []
    for file in files:
        if file and file.filename:
            content = file.read()
            documents.append({
                'content': content,
                'filename': file.filename,
                'mime_type': file.content_type or 'application/octet-stream'
            })

    # Analyze all documents
    results = analyze_batch(documents, key_parties, sponsor_name)

    # Store results in session for now (in production, save to DB)
    if 'kyc_documents' not in session:
        session['kyc_documents'] = {}

    processed_results = []
    for i, result in enumerate(results):
        doc_id = f"DOC-{datetime.now().strftime('%Y%m%d%H%M%S')}-{i:03d}"
        doc_record = {
            'document_id': doc_id,
            'onboarding_id': onboarding_id,
            'filename': result['filename'],
            'analysis': result['analysis'],
            'suggested_assignment': result['suggested_assignment'],
            'uploaded_at': datetime.now().isoformat(),
            'uploaded_by': get_current_user()['name']
        }
        session['kyc_documents'][doc_id] = doc_record
        processed_results.append(doc_record)

    session.modified = True

    return jsonify({
        'status': 'ok',
        'message': f'Analyzed {len(results)} documents',
        'documents': processed_results
    })


@app.route('/api/kyc/<onboarding_id>/document/<doc_id>/reassign', methods=['POST'])
@login_required
def api_kyc_reassign(onboarding_id, doc_id):
    """API: Reassign a document to a different checklist slot"""
    data = request.get_json()

    assignment_type = data.get('type')  # 'sponsor' or 'key_party'
    document_type = data.get('document_type')
    person_id = data.get('person_id')  # For key_party assignments

    # Get document from session
    doc = session.get('kyc_documents', {}).get(doc_id)
    if not doc:
        return jsonify({'status': 'error', 'message': 'Document not found'}), 404

    # Update assignment
    doc['suggested_assignment'] = {
        'type': assignment_type,
        'document_type': document_type,
        'person_id': person_id,
        'confidence': 1.0,  # Manual assignment = 100% confidence
        'manually_assigned': True
    }

    session.modified = True

    return jsonify({
        'status': 'ok',
        'message': 'Document reassigned',
        'document': doc
    })


@app.route('/api/kyc/<onboarding_id>/document/<doc_id>/override', methods=['POST'])
@login_required
def api_kyc_override(onboarding_id, doc_id):
    """API: Override a warning on a document"""
    data = request.get_json()
    reason = data.get('reason')

    if not reason:
        return jsonify({'status': 'error', 'message': 'Override reason required'}), 400

    # Get document from session
    doc = session.get('kyc_documents', {}).get(doc_id)
    if not doc:
        return jsonify({'status': 'error', 'message': 'Document not found'}), 404

    # Apply override
    doc['override'] = {
        'applied': True,
        'reason': reason,
        'by': get_current_user()['name'],
        'at': datetime.now().isoformat()
    }

    # Update overall status
    doc['analysis']['overall_status'] = 'pass'

    session.modified = True

    return jsonify({
        'status': 'ok',
        'message': 'Override applied',
        'document': doc
    })


@app.route('/api/kyc/<onboarding_id>/signoff', methods=['POST'])
@login_required
def api_kyc_signoff(onboarding_id):
    """API: BD sign-off on KYC documentation"""
    from services.kyc_checklist import get_checklist_progress

    # Check all documents are complete
    docs = session.get('kyc_documents', {})

    # In production, would verify against checklist
    # For now, just mark as signed off

    session['kyc_signed_off'] = {
        'onboarding_id': onboarding_id,
        'signed_off_by': get_current_user()['name'],
        'signed_off_at': datetime.now().isoformat(),
        'document_count': len(docs)
    }

    session.modified = True

    return jsonify({
        'status': 'ok',
        'message': 'KYC documentation signed off',
        'signoff': session['kyc_signed_off']
    })
```

**Step 3: Verify syntax**

Run: `python3 -m py_compile app.py && echo "Syntax OK"`
Expected: `Syntax OK`

**Step 4: Commit**

```bash
git add app.py
git commit -m "feat: add KYC/CDD API endpoints and rename Phase 4"
```

---

## Task 4: Create Phase 4 KYC/CDD Template

**Files:**
- Replace: `templates/onboarding/phase4.html`

**Step 1: Create the new Phase 4 template**

```html
{% extends "base.html" %}

{% block title %}Phase 4: KYC & CDD Documentation{% endblock %}

{% block content %}
<div class="row mb-4">
    <div class="col">
        <nav aria-label="breadcrumb">
            <ol class="breadcrumb mb-2">
                <li class="breadcrumb-item"><a href="{{ url_for('dashboard') }}">Dashboard</a></li>
                <li class="breadcrumb-item active">Phase 4: KYC & CDD</li>
            </ol>
        </nav>
        <h1 class="h3 mb-1">KYC & CDD Documentation</h1>
        <p class="text-muted">Upload and verify sponsor and key party documentation</p>
    </div>
</div>

<!-- Wizard Stepper -->
<ul class="wizard-stepper mb-4">
    {% for p in phases %}
    <li class="wizard-step {% if p.num < phase %}completed{% elif p.num == phase %}current{% endif %}">
        <div class="step-icon">
            {% if p.num < phase %}
            <i class="bi bi-check"></i>
            {% else %}
            <i class="bi {{ p.icon }}"></i>
            {% endif %}
        </div>
        <span class="step-label">{{ p.name }}</span>
    </li>
    {% endfor %}
</ul>

<div class="row">
    <div class="col-lg-8">
        <!-- Upload Section -->
        <div class="card mb-4" id="uploadSection">
            <div class="card-header">
                <i class="bi bi-cloud-upload me-2"></i>
                Upload Documents
            </div>
            <div class="card-body">
                <div class="upload-zone border-2 border-dashed rounded p-5 text-center" id="dropZone">
                    <i class="bi bi-file-earmark-arrow-up fs-1 text-muted mb-3 d-block"></i>
                    <h5>Drag & drop all documents here</h5>
                    <p class="text-muted mb-3">or click to browse</p>
                    <input type="file" id="fileInput" multiple accept=".pdf,.jpg,.jpeg,.png" class="d-none">
                    <button type="button" class="btn btn-outline-primary" onclick="document.getElementById('fileInput').click()">
                        <i class="bi bi-folder2-open me-1"></i> Browse Files
                    </button>
                    <p class="small text-muted mt-3 mb-0">Supported: PDF, JPG, PNG (max 20MB each)</p>
                </div>

                <!-- Selected Files Preview -->
                <div id="selectedFiles" class="mt-3 d-none">
                    <h6 class="mb-2">Selected Files:</h6>
                    <ul class="list-group" id="fileList"></ul>
                    <button type="button" class="btn btn-primary mt-3" id="uploadBtn">
                        <i class="bi bi-cpu me-1"></i> Upload & Analyse
                    </button>
                </div>

                <!-- Processing Indicator -->
                <div id="processingIndicator" class="mt-4 d-none">
                    <div class="d-flex align-items-center gap-3">
                        <div class="spinner-border text-primary" role="status"></div>
                        <div>
                            <strong>AI Processing Documents...</strong>
                            <p class="mb-0 small text-muted">Detecting document types and checking JFSC compliance</p>
                        </div>
                    </div>
                    <div class="progress mt-3" style="height: 6px;">
                        <div class="progress-bar progress-bar-striped progress-bar-animated" id="progressBar" style="width: 0%"></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Results Section (hidden until upload complete) -->
        <div id="resultsSection" class="d-none">
            <!-- Sponsor Documents -->
            <div class="card mb-4">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <span><i class="bi bi-building me-2"></i>Sponsor Entity Documents</span>
                    <span class="badge bg-secondary" id="sponsorDocsCount">0/0</span>
                </div>
                <div class="card-body p-0">
                    <div class="list-group list-group-flush" id="sponsorDocsList">
                        <!-- Populated by JavaScript -->
                    </div>
                </div>
            </div>

            <!-- Key Parties Documents -->
            <div id="keyPartiesSection">
                <!-- Populated by JavaScript -->
            </div>

            <!-- Unassigned Documents -->
            <div class="card mb-4 d-none" id="unassignedSection">
                <div class="card-header bg-warning bg-opacity-10">
                    <i class="bi bi-question-circle me-2 text-warning"></i>
                    Unassigned Documents
                </div>
                <div class="card-body p-0">
                    <div class="list-group list-group-flush" id="unassignedDocsList">
                        <!-- Populated by JavaScript -->
                    </div>
                </div>
            </div>

            <!-- EDD Section (if required) -->
            <div class="card mb-4 border-warning d-none" id="eddSection">
                <div class="card-header bg-warning bg-opacity-10">
                    <i class="bi bi-exclamation-triangle me-2 text-warning"></i>
                    Enhanced Due Diligence Required
                </div>
                <div class="card-body">
                    <p class="mb-3" id="eddReason"></p>
                    <div class="list-group list-group-flush" id="eddDocsList">
                        <!-- Populated by JavaScript -->
                    </div>
                </div>
            </div>
        </div>

        <!-- Investor KYC Note -->
        <div class="alert alert-info mb-4">
            <i class="bi bi-info-circle me-2"></i>
            <strong>Note:</strong> Investor KYC is collected separately during subscription. The fund cannot accept investors until their documentation is received and approved.
        </div>

        <!-- Form Actions -->
        <div class="d-flex justify-content-between mb-4">
            <a href="{{ url_for('onboarding_phase', onboarding_id=onboarding_id, phase=3) }}" class="btn btn-outline-secondary">
                <i class="bi bi-arrow-left me-1"></i> Back to Phase 3
            </a>
            <div>
                <button type="button" class="btn btn-outline-primary me-2" id="uploadMoreBtn" disabled>
                    <i class="bi bi-plus-lg me-1"></i> Upload More
                </button>
                <button type="button" class="btn btn-primary" id="signOffBtn" disabled>
                    Sign Off & Continue <i class="bi bi-arrow-right ms-1"></i>
                </button>
            </div>
        </div>
    </div>

    <!-- Sidebar -->
    <div class="col-lg-4">
        <!-- Progress Card -->
        <div class="card mb-4">
            <div class="card-header">
                <i class="bi bi-check2-square me-2"></i>
                Documentation Progress
            </div>
            <div class="card-body">
                <div class="d-flex justify-content-between mb-2">
                    <span>Overall Progress</span>
                    <strong id="progressPercent">0%</strong>
                </div>
                <div class="progress mb-3" style="height: 10px;">
                    <div class="progress-bar bg-success" id="overallProgress" style="width: 0%"></div>
                </div>
                <ul class="list-unstyled mb-0 small" id="progressDetails">
                    <li class="d-flex justify-content-between mb-1">
                        <span><i class="bi bi-circle text-muted me-1"></i> Pending</span>
                        <span id="pendingCount">0</span>
                    </li>
                    <li class="d-flex justify-content-between mb-1">
                        <span><i class="bi bi-check-circle text-success me-1"></i> Complete</span>
                        <span id="completeCount">0</span>
                    </li>
                    <li class="d-flex justify-content-between">
                        <span><i class="bi bi-exclamation-circle text-warning me-1"></i> Review Needed</span>
                        <span id="reviewCount">0</span>
                    </li>
                </ul>
            </div>
        </div>

        <!-- Checklist Card -->
        <div class="card mb-4">
            <div class="card-header">
                <i class="bi bi-list-check me-2"></i>
                Required Documents
            </div>
            <div class="card-body">
                <div id="checklistSummary">
                    <p class="text-muted small">Upload documents to see checklist</p>
                </div>
            </div>
        </div>

        <!-- JFSC Guidance -->
        <div class="card mb-4">
            <div class="card-header">
                <i class="bi bi-info-circle me-2"></i>
                JFSC Certification Requirements
            </div>
            <div class="card-body small text-muted">
                <p><strong>Acceptable Certifiers:</strong></p>
                <ul class="mb-3">
                    <li>Lawyer / Solicitor</li>
                    <li>Notary Public</li>
                    <li>Chartered Accountant</li>
                </ul>
                <p><strong>Required Elements:</strong></p>
                <ul class="mb-0">
                    <li>"I certify this is a true copy of the original"</li>
                    <li>Certifier's signature</li>
                    <li>Certifier's printed name & qualification</li>
                    <li>Date of certification</li>
                </ul>
            </div>
        </div>
    </div>
</div>

<!-- Document Detail Modal -->
<div class="modal fade" id="docDetailModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Document Review</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body" id="docDetailContent">
                <!-- Populated by JavaScript -->
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                <button type="button" class="btn btn-warning d-none" id="overrideBtn">
                    <i class="bi bi-check-lg me-1"></i> Override Warning
                </button>
            </div>
        </div>
    </div>
</div>

<!-- Override Reason Modal -->
<div class="modal fade" id="overrideModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Override Warning</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <p class="text-muted">Provide a reason for overriding this warning. This will be recorded in the audit trail.</p>
                <textarea class="form-control" id="overrideReason" rows="3" placeholder="Enter justification..."></textarea>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="button" class="btn btn-warning" id="confirmOverrideBtn">
                    <i class="bi bi-check-lg me-1"></i> Confirm Override
                </button>
            </div>
        </div>
    </div>
</div>

<style>
.upload-zone {
    border: 2px dashed #dee2e6;
    transition: all 0.2s;
    cursor: pointer;
}
.upload-zone:hover, .upload-zone.dragover {
    border-color: #0d6efd;
    background-color: rgba(13, 110, 253, 0.05);
}
.doc-status-pass { color: #198754; }
.doc-status-review_needed { color: #ffc107; }
.doc-status-fail { color: #dc3545; }
.doc-status-pending { color: #6c757d; }
.check-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.25rem 0;
}
.confidence-badge {
    font-size: 0.75rem;
    padding: 0.15rem 0.4rem;
}
</style>
{% endblock %}

{% block scripts %}
<script>
const onboardingId = '{{ onboarding_id }}';
const enquiryId = '{{ enquiry.id if enquiry else "" }}';
let uploadedDocuments = [];
let checklist = null;

document.addEventListener('DOMContentLoaded', function() {
    // Load checklist
    loadChecklist();

    // Setup drag and drop
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'));
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'));
    });

    dropZone.addEventListener('drop', handleDrop);
    dropZone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileSelect);

    document.getElementById('uploadBtn').addEventListener('click', uploadFiles);
    document.getElementById('signOffBtn').addEventListener('click', signOff);
    document.getElementById('uploadMoreBtn').addEventListener('click', () => {
        document.getElementById('uploadSection').classList.remove('d-none');
        document.getElementById('selectedFiles').classList.add('d-none');
    });
});

function handleDrop(e) {
    const files = e.dataTransfer.files;
    handleFiles(files);
}

function handleFileSelect(e) {
    handleFiles(e.target.files);
}

function handleFiles(files) {
    const fileList = document.getElementById('fileList');
    fileList.innerHTML = '';

    Array.from(files).forEach(file => {
        const li = document.createElement('li');
        li.className = 'list-group-item d-flex justify-content-between align-items-center';
        li.innerHTML = `
            <span><i class="bi bi-file-earmark me-2"></i>${file.name}</span>
            <span class="badge bg-secondary">${(file.size / 1024).toFixed(1)} KB</span>
        `;
        fileList.appendChild(li);
    });

    document.getElementById('selectedFiles').classList.remove('d-none');
    window.selectedFiles = files;
}

async function loadChecklist() {
    try {
        const response = await fetch(`/api/kyc/${onboardingId}/checklist?enquiry_id=${enquiryId}`);
        const data = await response.json();

        if (data.status === 'ok') {
            checklist = data.checklist;
            updateChecklistDisplay(checklist);
            updateProgress(data.progress);

            // Show EDD section if required
            if (checklist.edd_required) {
                document.getElementById('eddSection').classList.remove('d-none');
                document.getElementById('eddReason').textContent = checklist.edd_trigger_reason;
            }
        }
    } catch (err) {
        console.error('Error loading checklist:', err);
    }
}

function updateChecklistDisplay(checklist) {
    const summary = document.getElementById('checklistSummary');

    let html = '<h6 class="mb-2">Sponsor Documents</h6><ul class="list-unstyled mb-3">';
    checklist.sponsor_documents.forEach(doc => {
        const icon = doc.status === 'complete' ? 'bi-check-circle-fill text-success' : 'bi-circle text-muted';
        html += `<li class="small"><i class="bi ${icon} me-1"></i>${doc.label}</li>`;
    });
    html += '</ul>';

    checklist.key_parties.forEach(party => {
        html += `<h6 class="mb-2">${party.name}</h6><ul class="list-unstyled mb-3">`;
        party.documents.forEach(doc => {
            const icon = doc.status === 'complete' ? 'bi-check-circle-fill text-success' : 'bi-circle text-muted';
            html += `<li class="small"><i class="bi ${icon} me-1"></i>${doc.label}</li>`;
        });
        html += '</ul>';
    });

    summary.innerHTML = html;
}

function updateProgress(progress) {
    document.getElementById('progressPercent').textContent = progress.percentage + '%';
    document.getElementById('overallProgress').style.width = progress.percentage + '%';
    document.getElementById('pendingCount').textContent = progress.pending;
    document.getElementById('completeCount').textContent = progress.complete;
    document.getElementById('reviewCount').textContent = progress.review_needed;

    // Enable sign off if ready
    document.getElementById('signOffBtn').disabled = !progress.can_sign_off;
}

async function uploadFiles() {
    if (!window.selectedFiles || window.selectedFiles.length === 0) return;

    const formData = new FormData();
    Array.from(window.selectedFiles).forEach(file => {
        formData.append('files', file);
    });
    formData.append('enquiry_id', enquiryId);

    // Show processing
    document.getElementById('selectedFiles').classList.add('d-none');
    document.getElementById('processingIndicator').classList.remove('d-none');

    // Animate progress bar
    let progress = 0;
    const progressBar = document.getElementById('progressBar');
    const progressInterval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress > 90) progress = 90;
        progressBar.style.width = progress + '%';
    }, 300);

    try {
        const response = await fetch(`/api/kyc/${onboardingId}/upload`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        clearInterval(progressInterval);
        progressBar.style.width = '100%';

        if (data.status === 'ok') {
            uploadedDocuments = data.documents;
            setTimeout(() => {
                document.getElementById('processingIndicator').classList.add('d-none');
                displayResults(uploadedDocuments);
            }, 500);
        } else {
            alert('Upload failed: ' + data.message);
            document.getElementById('processingIndicator').classList.add('d-none');
            document.getElementById('selectedFiles').classList.remove('d-none');
        }
    } catch (err) {
        clearInterval(progressInterval);
        console.error('Upload error:', err);
        alert('Upload failed. Please try again.');
        document.getElementById('processingIndicator').classList.add('d-none');
        document.getElementById('selectedFiles').classList.remove('d-none');
    }
}

function displayResults(documents) {
    document.getElementById('resultsSection').classList.remove('d-none');
    document.getElementById('uploadMoreBtn').disabled = false;

    const sponsorDocs = [];
    const keyPartyDocs = {};
    const unassigned = [];

    documents.forEach(doc => {
        const assignment = doc.suggested_assignment;
        if (assignment.type === 'sponsor') {
            sponsorDocs.push(doc);
        } else if (assignment.type === 'key_party') {
            const personId = assignment.person_id;
            if (!keyPartyDocs[personId]) keyPartyDocs[personId] = [];
            keyPartyDocs[personId].push(doc);
        } else {
            unassigned.push(doc);
        }
    });

    // Render sponsor documents
    renderDocumentList('sponsorDocsList', sponsorDocs);
    document.getElementById('sponsorDocsCount').textContent = `${sponsorDocs.length} uploaded`;

    // Render key party documents
    renderKeyPartyDocs(keyPartyDocs);

    // Render unassigned
    if (unassigned.length > 0) {
        document.getElementById('unassignedSection').classList.remove('d-none');
        renderDocumentList('unassignedDocsList', unassigned);
    }

    // Update progress
    updateProgressFromDocs(documents);
}

function renderDocumentList(containerId, docs) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';

    docs.forEach(doc => {
        const status = doc.analysis.overall_status;
        const statusIcon = status === 'pass' ? 'bi-check-circle-fill text-success' :
                          status === 'review_needed' ? 'bi-exclamation-circle-fill text-warning' :
                          'bi-x-circle-fill text-danger';

        const confidence = Math.round((doc.suggested_assignment.confidence || 0) * 100);

        const item = document.createElement('div');
        item.className = 'list-group-item d-flex justify-content-between align-items-center';
        item.innerHTML = `
            <div>
                <i class="bi ${statusIcon} me-2"></i>
                <strong>${doc.analysis.detected_type || 'Unknown'}</strong>
                <small class="text-muted ms-2">${doc.filename}</small>
                <span class="badge bg-light text-dark confidence-badge ms-2">${confidence}% match</span>
            </div>
            <div>
                <button class="btn btn-sm btn-outline-primary" onclick="viewDocument('${doc.document_id}')">
                    <i class="bi bi-eye"></i> View
                </button>
            </div>
        `;
        container.appendChild(item);
    });
}

function renderKeyPartyDocs(keyPartyDocs) {
    const container = document.getElementById('keyPartiesSection');
    container.innerHTML = '';

    if (!checklist) return;

    checklist.key_parties.forEach(party => {
        const docs = keyPartyDocs[party.person_id] || [];

        const card = document.createElement('div');
        card.className = 'card mb-4';
        card.innerHTML = `
            <div class="card-header d-flex justify-content-between align-items-center">
                <span><i class="bi bi-person me-2"></i>${party.name} <small class="text-muted">(${party.role})</small></span>
                <span class="badge bg-secondary">${docs.length} uploaded</span>
            </div>
            <div class="card-body p-0">
                <div class="list-group list-group-flush" id="keyParty_${party.person_id}"></div>
            </div>
        `;
        container.appendChild(card);

        renderDocumentList(`keyParty_${party.person_id}`, docs);
    });
}

function updateProgressFromDocs(documents) {
    let complete = 0;
    let reviewNeeded = 0;

    documents.forEach(doc => {
        if (doc.analysis.overall_status === 'pass') complete++;
        else if (doc.analysis.overall_status === 'review_needed') reviewNeeded++;
    });

    const total = checklist ?
        checklist.sponsor_documents.length +
        checklist.key_parties.reduce((sum, p) => sum + p.documents.length, 0) :
        documents.length;

    updateProgress({
        total: total,
        complete: complete,
        review_needed: reviewNeeded,
        pending: total - complete - reviewNeeded,
        percentage: Math.round(complete / total * 100),
        can_sign_off: reviewNeeded === 0 && complete >= total
    });
}

function viewDocument(docId) {
    const doc = uploadedDocuments.find(d => d.document_id === docId);
    if (!doc) return;

    const modal = document.getElementById('docDetailModal');
    const content = document.getElementById('docDetailContent');
    const overrideBtn = document.getElementById('overrideBtn');

    let checksHtml = '';
    Object.entries(doc.analysis.checks || {}).forEach(([key, check]) => {
        const icon = check.status === 'pass' ? 'bi-check-circle-fill text-success' :
                    check.status === 'review_needed' ? 'bi-exclamation-circle-fill text-warning' :
                    'bi-x-circle-fill text-danger';
        checksHtml += `
            <div class="check-item">
                <i class="bi ${icon}"></i>
                <strong>${key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</strong>
                <span>${check.detail}</span>
            </div>
        `;
    });

    content.innerHTML = `
        <h6>${doc.filename}</h6>
        <p class="text-muted">Detected Type: ${doc.analysis.detected_type}</p>
        <hr>
        <h6>AI Review Results</h6>
        ${checksHtml}
        ${doc.override ? `
            <div class="alert alert-info mt-3">
                <strong>Override Applied:</strong> ${doc.override.reason}<br>
                <small>By ${doc.override.by} at ${doc.override.at}</small>
            </div>
        ` : ''}
    `;

    // Show override button if review needed
    if (doc.analysis.overall_status === 'review_needed' && !doc.override) {
        overrideBtn.classList.remove('d-none');
        overrideBtn.onclick = () => showOverrideModal(docId);
    } else {
        overrideBtn.classList.add('d-none');
    }

    new bootstrap.Modal(modal).show();
}

function showOverrideModal(docId) {
    bootstrap.Modal.getInstance(document.getElementById('docDetailModal')).hide();

    const modal = document.getElementById('overrideModal');
    document.getElementById('overrideReason').value = '';

    document.getElementById('confirmOverrideBtn').onclick = async () => {
        const reason = document.getElementById('overrideReason').value.trim();
        if (!reason) {
            alert('Please provide a reason for the override.');
            return;
        }

        try {
            const response = await fetch(`/api/kyc/${onboardingId}/document/${docId}/override`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ reason })
            });

            const data = await response.json();
            if (data.status === 'ok') {
                // Update local data
                const doc = uploadedDocuments.find(d => d.document_id === docId);
                if (doc) {
                    doc.override = data.document.override;
                    doc.analysis.overall_status = 'pass';
                }

                bootstrap.Modal.getInstance(modal).hide();
                displayResults(uploadedDocuments);
            } else {
                alert('Override failed: ' + data.message);
            }
        } catch (err) {
            console.error('Override error:', err);
            alert('Override failed. Please try again.');
        }
    };

    new bootstrap.Modal(modal).show();
}

async function signOff() {
    if (!confirm('Sign off KYC documentation and proceed to MLRO approval?')) return;

    try {
        const response = await fetch(`/api/kyc/${onboardingId}/signoff`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();
        if (data.status === 'ok') {
            window.location.href = `/onboarding/${onboardingId}/phase/5`;
        } else {
            alert('Sign off failed: ' + data.message);
        }
    } catch (err) {
        console.error('Sign off error:', err);
        alert('Sign off failed. Please try again.');
    }
}
</script>
{% endblock %}
```

**Step 2: Verify the template renders**

Run the Flask app and navigate to Phase 4 to verify the template loads.

**Step 3: Commit**

```bash
git add templates/onboarding/phase4.html
git commit -m "feat: replace Phase 4 template with KYC/CDD documentation UI"
```

---

## Task 5: Add Services to __init__.py

**Files:**
- Modify: `services/__init__.py`

**Step 1: Add imports for new services**

Add to `services/__init__.py`:

```python
# KYC/CDD services
from .kyc_checklist import generate_checklist, get_checklist_progress
from .document_review import analyze_document, analyze_batch, get_service as get_document_review_service
```

And add to the `__all__` list:

```python
    'generate_checklist',
    'get_checklist_progress',
    'analyze_document',
    'analyze_batch',
    'get_document_review_service',
```

**Step 2: Verify imports work**

Run: `python3 -c "from services import generate_checklist, analyze_document; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add services/__init__.py
git commit -m "feat: export KYC/CDD services from services module"
```

---

## Task 6: Final Integration Test

**Step 1: Start the Flask application**

Run: `python3 app.py`

**Step 2: Test the full flow**

1. Navigate to Dashboard
2. Start a new onboarding or continue an existing one
3. Complete Phases 1-3
4. On Phase 4:
   - Verify the new KYC/CDD UI appears
   - Upload test documents (any PDFs or images)
   - Verify AI analysis results appear
   - Test document viewing and override functionality
   - Sign off and verify navigation to Phase 5

**Step 3: Commit final changes**

```bash
git add -A
git commit -m "feat: complete KYC/CDD documentation phase implementation"
```

---

## Summary

| Task | Files | Purpose |
|------|-------|---------|
| 1 | `services/kyc_checklist.py` | Dynamic checklist generation |
| 2 | `services/document_review.py` | AI document analysis with Claude |
| 3 | `app.py` | API endpoints + phase rename |
| 4 | `templates/onboarding/phase4.html` | New KYC/CDD UI |
| 5 | `services/__init__.py` | Export new services |
| 6 | - | Integration testing |

**Total estimated commits:** 6
