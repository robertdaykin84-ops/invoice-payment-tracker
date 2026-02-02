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


def _get_styles() -> Dict[str, ParagraphStyle]:
    """Get custom paragraph styles for reports."""
    styles = getSampleStyleSheet()

    custom_styles = {
        'Title': ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=18,
            spaceAfter=6*mm,
            textColor=colors.HexColor('#212529')
        ),
        'Subtitle': ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#6c757d'),
            spaceAfter=4*mm
        ),
        'Heading1': ParagraphStyle(
            'CustomH1',
            parent=styles['Heading1'],
            fontSize=14,
            spaceBefore=6*mm,
            spaceAfter=3*mm,
            textColor=colors.HexColor('#212529')
        ),
        'Heading2': ParagraphStyle(
            'CustomH2',
            parent=styles['Heading2'],
            fontSize=12,
            spaceBefore=4*mm,
            spaceAfter=2*mm,
            textColor=colors.HexColor('#495057')
        ),
        'Normal': ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#212529')
        ),
        'Small': ParagraphStyle(
            'Small',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#6c757d')
        ),
        'Footer': ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#6c757d'),
            alignment=TA_CENTER
        ),
    }

    return custom_styles


def _create_header(data: Dict[str, Any], report_type: str, styles: Dict) -> List:
    """Create report header elements."""
    elements = []

    # Report title based on type
    titles = {
        'compliance': 'Compliance Risk Report',
        'board': 'Board Risk Summary',
        'audit': 'Audit Pack - Full Risk Assessment'
    }

    onboarding = data.get('onboarding', {})

    elements.append(Paragraph(titles.get(report_type, 'Risk Report'), styles['Title']))
    elements.append(Paragraph(
        f"{onboarding.get('sponsor_name', 'Unknown')} / {onboarding.get('fund_name', 'Unknown')}",
        styles['Subtitle']
    ))

    # Report metadata table
    generated_at = datetime.fromisoformat(data['generated_at'].replace('Z', '+00:00'))
    meta_data = [
        ['Report ID:', f"{onboarding.get('onboarding_id', 'N/A')}-{report_type.upper()}-{generated_at.strftime('%Y%m%d')}"],
        ['Generated:', generated_at.strftime('%d %B %Y at %H:%M')],
        ['Onboarding ID:', onboarding.get('onboarding_id', 'N/A')],
    ]

    if data.get('demo_mode'):
        meta_data.append(['Mode:', 'DEMO - Not for production use'])

    meta_table = Table(meta_data, colWidths=[30*mm, 80*mm])
    meta_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#6c757d')),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 6*mm))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#dee2e6')))
    elements.append(Spacer(1, 4*mm))

    return elements


def _create_risk_summary(data: Dict[str, Any], styles: Dict) -> List:
    """Create risk assessment summary section."""
    elements = []
    risk = data.get('risk_assessment', {})

    elements.append(Paragraph('Risk Assessment Summary', styles['Heading1']))

    # Risk score box
    rating = risk.get('rating', 'unknown')
    score = risk.get('score', 0)
    risk_color = RISK_COLORS.get(rating, colors.gray)

    summary_data = [
        ['Overall Risk Score', 'Risk Rating', 'EDD Required', 'Approval Level'],
        [
            str(round(score)),
            rating.upper(),
            'Yes' if risk.get('edd_required') else 'No',
            risk.get('approval_level', 'N/A').upper()
        ]
    ]

    summary_table = Table(summary_data, colWidths=[40*mm, 40*mm, 35*mm, 40*mm])
    summary_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#6c757d')),
        # Data row
        ('FONTSIZE', (0, 1), (-1, 1), 14),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        # Risk rating color
        ('TEXTCOLOR', (1, 1), (1, 1), risk_color),
        # General
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 4*mm))

    return elements


def _create_factor_breakdown(data: Dict[str, Any], styles: Dict) -> List:
    """Create risk factor breakdown section."""
    elements = []
    risk = data.get('risk_assessment', {})
    factors = risk.get('factors', {})

    elements.append(Paragraph('Risk Factor Breakdown', styles['Heading2']))

    factor_labels = {
        'jurisdiction': 'Jurisdiction',
        'pep_status': 'PEP Status',
        'sanctions': 'Sanctions',
        'adverse_media': 'Adverse Media',
        'entity_structure': 'Entity Structure'
    }

    table_data = [['Factor', 'Weight', 'Score', 'Contribution', 'Assessment']]

    for key in ['jurisdiction', 'pep_status', 'sanctions', 'adverse_media', 'entity_structure']:
        f = factors.get(key, {})
        table_data.append([
            factor_labels.get(key, key),
            f"{f.get('weight', 0)}%",
            str(f.get('score', 0)),
            f"{f.get('contribution', 0)} pts",
            f.get('reason', 'N/A')[:50]  # Truncate long reasons
        ])

    factor_table = Table(table_data, colWidths=[30*mm, 18*mm, 15*mm, 22*mm, 70*mm])
    factor_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (3, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
    ]))
    elements.append(factor_table)
    elements.append(Spacer(1, 4*mm))

    return elements