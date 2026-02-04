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


def get_outstanding_requirements(onboarding_id: str, session_data) -> List[Dict[str, str]]:
    """
    Get list of outstanding JFSC requirements.

    Returns:
        List of requirements with category and description
    """
    requirements = []

    # Get documents from session
    documents = session_data.get('kyc_documents', {})
    onboarding_docs = [d for d in documents.values() if d.get('onboarding_id') == onboarding_id]

    # Check sponsor entity documents
    required_sponsor_docs = [
        'certificate_of_incorporation',
        'memorandum_articles',
        'register_of_directors',
        'register_of_shareholders'
    ]

    verified_types = [d.get('analysis', {}).get('detected_type') for d in onboarding_docs if d.get('analysis', {}).get('overall_status') == 'pass']

    for doc_type in required_sponsor_docs:
        if doc_type not in verified_types:
            requirements.append({
                'category': 'Sponsor Entity',
                'description': f'Missing: {doc_type.replace("_", " ").title()}'
            })

    # Check for passport and address proof (at least one of each)
    has_passport = 'passport' in verified_types
    has_address_proof = 'address_proof' in verified_types

    if not has_passport:
        requirements.append({
            'category': 'Key Party',
            'description': 'Requires certified passport for at least one principal'
        })

    if not has_address_proof:
        requirements.append({
            'category': 'Key Party',
            'description': 'Requires certified address proof for at least one principal'
        })

    return requirements
