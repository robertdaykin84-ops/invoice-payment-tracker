"""
PDF Report Generation Service for Client Onboarding

Generates compliance reports in three formats:
- Compliance Report: Full detail for MLRO/Analyst
- Board Summary: Executive overview for Board/Committee
- Audit Pack: Complete record for external auditors
"""

import io
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

logger = logging.getLogger(__name__)

# Report types
REPORT_TYPES = ['compliance', 'board', 'audit']

# Risk rating colors
RISK_COLORS = {
    'low': colors.HexColor('#198754'),      # Bootstrap success green
    'medium': colors.HexColor('#ffc107'),   # Bootstrap warning yellow
    'high': colors.HexColor('#dc3545'),     # Bootstrap danger red
}


def gather_report_data(onboarding_id: str) -> Dict[str, Any]:
    """
    Gather all data needed for report generation.

    In demo mode, returns mock data. In production, pulls from SheetsDB.

    Args:
        onboarding_id: The onboarding record ID

    Returns:
        Dict containing all report data
    """
    # Try to get real data from SheetsDB
    try:
        from . import get_sheets_client
        sheets = get_sheets_client()

        if not sheets.demo_mode:
            # Get onboarding record
            onboardings = sheets.get_onboardings()
            onboarding = next(
                (o for o in onboardings if o.get('onboarding_id') == onboarding_id),
                None
            )

            if onboarding:
                # Get related data
                screenings = sheets.get_screenings(onboarding_id)
                risk_assessments = [
                    r for r in sheets.get_all('RiskAssessments')
                    if r.get('onboarding_id') == onboarding_id
                ]

                return {
                    'onboarding': onboarding,
                    'screenings': screenings,
                    'risk_assessment': risk_assessments[-1] if risk_assessments else None,
                    'generated_at': datetime.now().isoformat(),
                    'demo_mode': False
                }
    except Exception as e:
        logger.warning(f"Could not fetch from SheetsDB: {e}")

    # Return demo data
    return _get_demo_data(onboarding_id)


def _get_demo_data(onboarding_id: str) -> Dict[str, Any]:
    """Return demo data for report generation."""
    return {
        'onboarding': {
            'onboarding_id': onboarding_id or 'ONB-DEMO-001',
            'enquiry_id': 'ENQ-001',
            'sponsor_name': 'Granite Capital Partners LLP',
            'fund_name': 'Granite Capital Fund III LP',
            'entity_type': 'lp',
            'jurisdiction': 'GB',
            'status': 'in_progress',
            'current_phase': 4,
            'created_at': '2026-02-01T10:00:00Z'
        },
        'persons': [
            {'name': 'John Smith', 'role': 'Managing Partner', 'nationality': 'British'},
            {'name': 'Sarah Johnson', 'role': 'Partner', 'nationality': 'British'},
            {'name': 'Michael Brown', 'role': 'Partner', 'nationality': 'British'},
        ],
        'screenings': [
            {
                'name': 'John Smith',
                'entity_type': 'person',
                'has_pep_hit': False,
                'has_sanctions_hit': False,
                'has_adverse_media': False,
                'risk_level': 'clear',
                'screened_at': '2026-02-02T14:30:00Z'
            },
            {
                'name': 'Sarah Johnson',
                'entity_type': 'person',
                'has_pep_hit': False,
                'has_sanctions_hit': False,
                'has_adverse_media': False,
                'risk_level': 'clear',
                'screened_at': '2026-02-02T14:30:00Z'
            },
            {
                'name': 'Michael Brown',
                'entity_type': 'person',
                'has_pep_hit': False,
                'has_sanctions_hit': False,
                'has_adverse_media': False,
                'risk_level': 'clear',
                'screened_at': '2026-02-02T14:30:00Z'
            },
            {
                'name': 'Granite Capital Partners LLP',
                'entity_type': 'company',
                'has_pep_hit': False,
                'has_sanctions_hit': False,
                'has_adverse_media': False,
                'risk_level': 'clear',
                'screened_at': '2026-02-02T14:30:00Z'
            },
        ],
        'risk_assessment': {
            'score': 5.0,
            'rating': 'low',
            'edd_required': False,
            'approval_level': 'compliance',
            'factors': {
                'jurisdiction': {'score': 0, 'weight': 25, 'contribution': 0, 'reason': 'United Kingdom - Established Relationship (Low Risk)'},
                'pep_status': {'score': 0, 'weight': 25, 'contribution': 0, 'reason': 'No PEP matches found'},
                'sanctions': {'score': 0, 'weight': 30, 'contribution': 0, 'reason': 'Sanctions screening clear'},
                'adverse_media': {'score': 0, 'weight': 10, 'contribution': 0, 'reason': 'No adverse media found'},
                'entity_structure': {'score': 20, 'weight': 10, 'contribution': 2, 'reason': 'Limited Partnership - Moderate complexity'},
            },
            'assessed_at': '2026-02-02T14:35:00Z'
        },
        'audit_log': [
            {'timestamp': '2026-02-01T10:00:00Z', 'action': 'Onboarding created', 'user': 'System'},
            {'timestamp': '2026-02-02T14:30:00Z', 'action': 'Screening completed', 'user': 'Analyst'},
            {'timestamp': '2026-02-02T14:35:00Z', 'action': 'Risk assessment calculated', 'user': 'System'},
        ],
        'generated_at': datetime.now().isoformat(),
        'demo_mode': True
    }
