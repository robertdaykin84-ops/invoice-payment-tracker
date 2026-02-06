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
REPORT_TYPES = ['compliance', 'board', 'audit', 'admin_agreement', 'screening']

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


def _create_screening_results(data: Dict[str, Any], styles: Dict, detailed: bool = True) -> List:
    """Create screening results section."""
    elements = []
    screenings = data.get('screenings', [])

    elements.append(Paragraph('Screening Results', styles['Heading1']))

    # Summary counts
    clear = sum(1 for s in screenings if s.get('risk_level') == 'clear')
    review = sum(1 for s in screenings if s.get('risk_level') in ['review', 'medium'])
    hits = sum(1 for s in screenings if s.get('risk_level') in ['high', 'critical'])

    summary_data = [
        ['Total Screened', 'Clear', 'Review Required', 'Hits'],
        [str(len(screenings)), str(clear), str(review), str(hits)]
    ]

    colors_row = [colors.HexColor('#212529'), colors.HexColor('#198754'),
                  colors.HexColor('#ffc107'), colors.HexColor('#dc3545')]

    summary_table = Table(summary_data, colWidths=[38*mm, 38*mm, 38*mm, 38*mm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTSIZE', (0, 1), (-1, 1), 16),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 1), (0, 1), colors_row[0]),
        ('TEXTCOLOR', (1, 1), (1, 1), colors_row[1]),
        ('TEXTCOLOR', (2, 1), (2, 1), colors_row[2]),
        ('TEXTCOLOR', (3, 1), (3, 1), colors_row[3]),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 4*mm))

    if detailed and screenings:
        elements.append(Paragraph('Individual Screening Results', styles['Heading2']))

        detail_data = [['Entity', 'Type', 'PEP', 'Sanctions', 'Adverse Media', 'Result']]
        for s in screenings:
            pep = 'Hit' if s.get('has_pep_hit') else 'Clear'
            sanctions = 'Hit' if s.get('has_sanctions_hit') else 'Clear'
            adverse = 'Found' if s.get('has_adverse_media') else 'Clear'
            result = s.get('risk_level', 'unknown').upper()

            detail_data.append([
                s.get('name', 'Unknown')[:25],
                s.get('entity_type', 'N/A').capitalize(),
                pep,
                sanctions,
                adverse,
                result
            ])

        detail_table = Table(detail_data, colWidths=[45*mm, 20*mm, 18*mm, 22*mm, 28*mm, 22*mm])
        detail_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ]))
        elements.append(detail_table)

    elements.append(Spacer(1, 4*mm))
    return elements


def _create_signature_block(styles: Dict) -> List:
    """Create signature block for compliance sign-off."""
    elements = []

    elements.append(Paragraph('Sign-Off', styles['Heading1']))

    sig_data = [
        ['Reviewed By:', '_' * 40, 'Date:', '_' * 20],
        ['', '', '', ''],
        ['Signature:', '_' * 40, '', ''],
        ['', '', '', ''],
        ['Approved By:', '_' * 40, 'Date:', '_' * 20],
        ['', '', '', ''],
        ['Signature:', '_' * 40, '', ''],
    ]

    sig_table = Table(sig_data, colWidths=[25*mm, 60*mm, 15*mm, 55*mm])
    sig_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(sig_table)

    return elements


def _create_audit_trail(data: Dict[str, Any], styles: Dict) -> List:
    """Create audit trail section for audit pack."""
    elements = []
    audit_log = data.get('audit_log', [])

    elements.append(Paragraph('Audit Trail', styles['Heading1']))

    if not audit_log:
        elements.append(Paragraph('No audit log entries available.', styles['Normal']))
        return elements

    audit_data = [['Timestamp', 'Action', 'User']]
    for entry in audit_log:
        ts = entry.get('timestamp', '')
        if ts:
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                ts = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass
        audit_data.append([
            ts,
            entry.get('action', 'N/A'),
            entry.get('user', 'N/A')
        ])

    audit_table = Table(audit_data, colWidths=[45*mm, 80*mm, 30*mm])
    audit_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
    ]))
    elements.append(audit_table)

    return elements


def _create_methodology_notes(styles: Dict) -> List:
    """Create methodology notes for audit pack."""
    elements = []

    elements.append(Paragraph('Methodology Notes', styles['Heading1']))

    notes = """
    <b>Risk Scoring Methodology</b><br/>
    Risk scores are calculated using a weighted formula based on five factors:
    Jurisdiction (25%), PEP Status (25%), Sanctions (30%), Adverse Media (10%),
    and Entity Structure (10%). Scores range from 0-100 with thresholds at 40 (Medium)
    and 70 (High).<br/><br/>

    <b>Jurisdiction Risk Tiers</b><br/>
    Based on JFSC Appendix D1/D2 and FATF High-Risk Jurisdictions list.
    Prohibited: FATF Black List (score 100). High: FATF Grey List (score 80).
    Elevated: Offshore Financial Centers (score 50). Standard: Most jurisdictions (score 20).
    Low: UK, Jersey, Ireland (score 0).<br/><br/>

    <b>Data Sources</b><br/>
    Screening performed via OpenSanctions API which aggregates: UN Security Council Sanctions,
    EU Financial Sanctions, US OFAC SDN List, UK HMT Sanctions, PEP databases,
    Interpol Notices, and National Crime Databases.<br/><br/>

    <b>Regulatory Framework</b><br/>
    Assessment performed in accordance with JFSC AML/CFT Handbook requirements and
    FATF Recommendations for customer due diligence.
    """

    elements.append(Paragraph(notes, styles['Normal']))

    return elements


def _build_compliance_report(data: Dict[str, Any]) -> List:
    """Build compliance report elements (full detail for MLRO/Analyst)."""
    styles = _get_styles()
    elements = []

    elements.extend(_create_header(data, 'compliance', styles))
    elements.extend(_create_risk_summary(data, styles))
    elements.extend(_create_factor_breakdown(data, styles))
    elements.extend(_create_screening_results(data, styles, detailed=True))
    elements.extend(_create_signature_block(styles))

    return elements


def _build_board_report(data: Dict[str, Any]) -> List:
    """Build board summary report (executive overview - 1 page)."""
    styles = _get_styles()
    elements = []

    elements.extend(_create_header(data, 'board', styles))
    elements.extend(_create_risk_summary(data, styles))

    # Brief recommendation
    risk = data.get('risk_assessment', {})
    rating = risk.get('rating', 'unknown')

    elements.append(Paragraph('Recommendation', styles['Heading1']))

    if rating == 'high':
        rec = """
        <b>HIGH RISK - Enhanced Due Diligence Required</b><br/>
        This client presents elevated risk factors requiring enhanced due diligence
        procedures before onboarding can proceed. Board approval is required.
        """
    elif rating == 'medium':
        rec = """
        <b>MEDIUM RISK - Enhanced Due Diligence Recommended</b><br/>
        This client presents some risk factors that warrant additional scrutiny.
        MLRO approval is required before proceeding.
        """
    else:
        rec = """
        <b>LOW RISK - Standard Onboarding Pathway</b><br/>
        This client presents a low risk profile suitable for standard onboarding
        procedures. Compliance approval is sufficient.
        """

    elements.append(Paragraph(rec, styles['Normal']))
    elements.append(Spacer(1, 6*mm))

    # Screening summary only (not detailed)
    elements.extend(_create_screening_results(data, styles, detailed=False))

    # Compact signature
    elements.append(Spacer(1, 10*mm))
    elements.append(Paragraph('Board Approval: _________________ Date: _________', styles['Normal']))

    return elements


def _build_audit_report(data: Dict[str, Any]) -> List:
    """Build audit pack report (complete record for external auditors)."""
    styles = _get_styles()
    elements = []

    elements.extend(_create_header(data, 'audit', styles))
    elements.extend(_create_risk_summary(data, styles))
    elements.extend(_create_factor_breakdown(data, styles))
    elements.append(PageBreak())

    elements.extend(_create_screening_results(data, styles, detailed=True))
    elements.extend(_create_audit_trail(data, styles))
    elements.append(PageBreak())

    elements.extend(_create_methodology_notes(styles))
    elements.extend(_create_signature_block(styles))

    return elements


def generate_report(
    onboarding_id: str,
    report_type: str = 'compliance',
    save_to_drive: bool = True,
    sponsor_name: str = None,
    fund_name: str = None
) -> Dict[str, Any]:
    """
    Generate a PDF risk report.

    Args:
        onboarding_id: The onboarding record ID
        report_type: Type of report ('compliance', 'board', 'audit')
        save_to_drive: Whether to save the PDF to Google Drive
        sponsor_name: Override sponsor name (for GDrive folder)
        fund_name: Override fund name (for GDrive folder)

    Returns:
        Dict containing:
            - pdf_bytes: The generated PDF as bytes
            - filename: Generated filename
            - drive_result: GDrive upload result (if save_to_drive=True)
            - demo_mode: Whether running in demo mode
    """
    if report_type not in REPORT_TYPES:
        raise ValueError(f"Invalid report type: {report_type}. Must be one of {REPORT_TYPES}")

    # Gather data
    data = gather_report_data(onboarding_id)

    # Use provided names or fall back to data
    onboarding = data.get('onboarding', {})
    sponsor = sponsor_name or onboarding.get('sponsor_name', 'Unknown')
    fund = fund_name or onboarding.get('fund_name', 'Unknown')

    # Build report elements
    builders = {
        'compliance': _build_compliance_report,
        'board': _build_board_report,
        'audit': _build_audit_report
    }
    elements = builders[report_type](data)

    # Generate PDF to buffer
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15*mm,
        leftMargin=15*mm,
        topMargin=15*mm,
        bottomMargin=20*mm
    )

    # Add page number footer
    def add_page_number(canvas, doc):
        canvas.saveState()
        page_num = canvas.getPageNumber()
        text = f"Page {page_num} | Confidential | Generated by Client Onboarding System"
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#6c757d'))
        canvas.drawCentredString(A4[0] / 2, 10*mm, text)
        canvas.restoreState()

    doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)

    # Get PDF bytes
    pdf_bytes = buffer.getvalue()
    buffer.close()

    # Generate filename
    timestamp = datetime.now().strftime('%Y-%m-%d')
    filename = f"{onboarding_id}-{report_type}-{timestamp}.pdf"

    result = {
        'pdf_bytes': pdf_bytes,
        'filename': filename,
        'report_type': report_type,
        'demo_mode': data.get('demo_mode', True),
        'drive_result': None
    }

    # Save to Google Drive if requested
    if save_to_drive:
        try:
            from . import get_gdrive_client
            gdrive = get_gdrive_client()

            # Save PDF bytes to temp file for upload
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp.write(pdf_bytes)
                tmp_path = tmp.name

            try:
                drive_result = gdrive.upload_file(
                    file_path=tmp_path,
                    sponsor_name=sponsor,
                    fund_name=fund,
                    subfolder='_COMPLIANCE',
                    custom_filename=filename
                )
                result['drive_result'] = drive_result
            finally:
                import os
                os.unlink(tmp_path)

        except Exception as e:
            logger.warning(f"Could not save to Google Drive: {e}")
            result['drive_result'] = {'status': 'error', 'message': str(e)}

    logger.info(f"Generated {report_type} report: {filename} ({len(pdf_bytes)} bytes)")
    return result


def _get_screening_demo_data(onboarding_id: str) -> Dict[str, Any]:
    """Return demo data for screening report generation."""
    return {
        'onboarding_id': onboarding_id or 'ONB-DEMO-001',
        'fund_name': 'Granite Capital Fund III LP',
        'sponsor_name': 'Granite Capital Partners LLP',
        'screening_provider': 'OpenSanctions',
        'screened_by': 'Demo Analyst',
        'screened_at': datetime.now().isoformat(),
        'demo_mode': True,
        'entities': [
            {
                'name': 'John Edward Smith',
                'type': 'person',
                'dob': '1975-03-15',
                'nationality': 'British',
                'role': 'Managing Partner',
                'result': 'Clear',
                'has_pep_hit': False,
                'has_sanctions_hit': False,
                'has_adverse_media': False,
                'match_details': None,
            },
            {
                'name': 'Sarah Jane Johnson',
                'type': 'person',
                'dob': '1980-07-22',
                'nationality': 'British',
                'role': 'Partner',
                'result': 'Clear',
                'has_pep_hit': False,
                'has_sanctions_hit': False,
                'has_adverse_media': False,
                'match_details': None,
            },
            {
                'name': 'Michael David Brown',
                'type': 'person',
                'dob': '1968-11-30',
                'nationality': 'British',
                'role': 'Partner',
                'result': 'Clear',
                'has_pep_hit': False,
                'has_sanctions_hit': False,
                'has_adverse_media': False,
                'match_details': None,
            },
            {
                'name': 'Robert James Jones',
                'type': 'person',
                'dob': '1982-05-10',
                'nationality': 'British',
                'role': 'Fund Principal',
                'result': 'Clear',
                'has_pep_hit': False,
                'has_sanctions_hit': False,
                'has_adverse_media': False,
                'match_details': None,
            },
            {
                'name': 'Granite Capital Partners LLP',
                'type': 'company',
                'dob': None,
                'nationality': None,
                'role': 'Sponsor Entity',
                'result': 'Clear',
                'has_pep_hit': False,
                'has_sanctions_hit': False,
                'has_adverse_media': False,
                'match_details': None,
            },
        ],
        'datasets_checked': [
            'OFAC Specially Designated Nationals (SDN)',
            'EU Consolidated Sanctions List',
            'UN Security Council Consolidated List',
            'UK HMT Financial Sanctions',
            'Politically Exposed Persons (PEP) Lists',
            'Interpol Red Notices',
            'National Crime Agency (NCA)',
        ],
    }


def generate_screening_report(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a Sanctions & PEP Screening Report PDF.

    Args:
        data: Screening report data dict containing entities, results, metadata.
              If None or empty, demo data is used.

    Returns:
        Dict containing:
            - pdf_bytes: The generated PDF as bytes
            - filename: Generated filename
            - demo_mode: Whether running in demo mode
    """
    styles = _get_styles()
    elements = []

    onboarding_id = data.get('onboarding_id', 'UNKNOWN')
    fund_name = data.get('fund_name', 'Unknown Fund')
    sponsor_name = data.get('sponsor_name', 'Unknown Sponsor')
    screening_provider = data.get('screening_provider', 'OpenSanctions')
    screened_by = data.get('screened_by', 'System')
    screened_at_raw = data.get('screened_at', datetime.now().isoformat())
    demo_mode = data.get('demo_mode', False)
    entities = data.get('entities', [])
    datasets_checked = data.get('datasets_checked', [])

    try:
        screened_at = datetime.fromisoformat(screened_at_raw.replace('Z', '+00:00'))
    except Exception:
        screened_at = datetime.now()

    # ---- Title ----
    elements.append(Paragraph('Sanctions &amp; PEP Screening Report', styles['Title']))
    elements.append(Spacer(1, 2 * mm))

    # ---- Header metadata table ----
    header_data = [
        ['Fund Name:', fund_name],
        ['Sponsor Name:', sponsor_name],
        ['Onboarding ID:', onboarding_id],
        ['Report Date:', screened_at.strftime('%d %B %Y at %H:%M')],
        ['Screening Provider:', screening_provider],
    ]
    if demo_mode:
        header_data.append(['Mode:', 'DEMO - Not for production use'])

    header_table = Table(header_data, colWidths=[35 * mm, 120 * mm])
    header_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#6c757d')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 4 * mm))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#dee2e6')))
    elements.append(Spacer(1, 4 * mm))

    # ---- Summary section ----
    elements.append(Paragraph('Screening Summary', styles['Heading1']))

    total = len(entities)
    clear_count = sum(1 for e in entities if e.get('result', '').lower() == 'clear')
    match_count = sum(1 for e in entities if e.get('result', '').lower() == 'match')
    possible_count = sum(1 for e in entities if e.get('result', '').lower() == 'possible match')

    if match_count > 0:
        overall_risk = 'HIGH'
        risk_color = RISK_COLORS['high']
    elif possible_count > 0:
        overall_risk = 'MEDIUM'
        risk_color = RISK_COLORS['medium']
    else:
        overall_risk = 'LOW'
        risk_color = RISK_COLORS['low']

    summary_data = [
        ['Total Entities Screened', 'Clear', 'Matches Found', 'Possible Matches', 'Overall Risk'],
        [str(total), str(clear_count), str(match_count), str(possible_count), overall_risk],
    ]

    summary_table = Table(summary_data, colWidths=[35 * mm, 25 * mm, 30 * mm, 32 * mm, 30 * mm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#6c757d')),
        ('FONTSIZE', (0, 1), (-1, 1), 14),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (1, 1), (1, 1), RISK_COLORS['low']),
        ('TEXTCOLOR', (2, 1), (2, 1), RISK_COLORS['high']),
        ('TEXTCOLOR', (3, 1), (3, 1), RISK_COLORS['medium']),
        ('TEXTCOLOR', (4, 1), (4, 1), risk_color),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 6 * mm))

    # ---- Per-entity results ----
    elements.append(Paragraph('Individual Screening Results', styles['Heading1']))

    for entity in entities:
        entity_name = entity.get('name', 'Unknown')
        entity_type = entity.get('type', 'person').capitalize()
        dob = entity.get('dob')
        nationality = entity.get('nationality')
        role = entity.get('role', '')
        result_text = entity.get('result', 'Clear')
        has_pep = entity.get('has_pep_hit', False)
        has_sanctions = entity.get('has_sanctions_hit', False)
        has_adverse = entity.get('has_adverse_media', False)
        match_details = entity.get('match_details')

        # Result color
        if result_text.lower() == 'clear':
            result_color = RISK_COLORS['low']
        elif result_text.lower() == 'match':
            result_color = RISK_COLORS['high']
        else:
            result_color = RISK_COLORS['medium']

        # Entity header
        elements.append(Paragraph(
            f'<b>{entity_name}</b> <font color="#6c757d">({entity_type} - {role})</font>',
            styles['Heading2']
        ))

        # Entity details table
        detail_rows = []
        if dob:
            detail_rows.append(['Date of Birth:', dob])
        if nationality:
            detail_rows.append(['Nationality:', nationality])
        detail_rows.append(['Screening Result:', result_text])
        detail_rows.append(['PEP Check:', 'Match' if has_pep else 'Clear'])
        detail_rows.append(['Sanctions Check:', 'Match' if has_sanctions else 'Clear'])
        detail_rows.append(['Adverse Media:', 'Found' if has_adverse else 'Clear'])

        if detail_rows:
            detail_table = Table(detail_rows, colWidths=[35 * mm, 120 * mm])
            detail_table.setStyle(TableStyle([
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#6c757d')),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            elements.append(detail_table)

        # Match details if any
        if match_details:
            elements.append(Spacer(1, 2 * mm))
            elements.append(Paragraph(
                f'<b>Match Details:</b> {match_details}',
                styles['Small']
            ))

        elements.append(Spacer(1, 2 * mm))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#e9ecef')))
        elements.append(Spacer(1, 2 * mm))

    # ---- Datasets Checked ----
    elements.append(Paragraph('Datasets Checked', styles['Heading1']))

    if datasets_checked:
        ds_data = [['#', 'Dataset']]
        for idx, ds in enumerate(datasets_checked, 1):
            ds_data.append([str(idx), ds])

        ds_table = Table(ds_data, colWidths=[10 * mm, 145 * mm])
        ds_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ]))
        elements.append(ds_table)
    else:
        elements.append(Paragraph('No dataset information available.', styles['Normal']))

    elements.append(Spacer(1, 6 * mm))

    # ---- Declaration ----
    elements.append(Paragraph('Declaration', styles['Heading1']))

    ds_names = ', '.join(datasets_checked) if datasets_checked else 'standard sanctions and PEP databases'
    declaration_text = (
        f'This screening was conducted against the {screening_provider} consolidated dataset '
        f'covering: {ds_names}. '
        f'All entities listed above were screened on {screened_at.strftime("%d %B %Y at %H:%M")} '
        f'by {screened_by}. '
        f'Results are valid as of the screening date and should be refreshed periodically '
        f'in accordance with JFSC AML/CFT Handbook requirements.'
    )
    elements.append(Paragraph(declaration_text, styles['Normal']))
    elements.append(Spacer(1, 6 * mm))

    # ---- Timestamp and screened by ----
    footer_data = [
        ['Screened By:', screened_by],
        ['Screening Date:', screened_at.strftime('%d %B %Y at %H:%M')],
        ['Report Generated:', datetime.now().strftime('%d %B %Y at %H:%M')],
    ]
    footer_table = Table(footer_data, colWidths=[35 * mm, 120 * mm])
    footer_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#6c757d')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(footer_table)

    # ---- Build PDF ----
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=20 * mm,
    )

    def add_page_number(canvas, doc):
        canvas.saveState()
        page_num = canvas.getPageNumber()
        text = f"Page {page_num} | Confidential | Sanctions & PEP Screening Report"
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#6c757d'))
        canvas.drawCentredString(A4[0] / 2, 10 * mm, text)
        canvas.restoreState()

    doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    timestamp = datetime.now().strftime('%Y-%m-%d')
    filename = f"{onboarding_id}-screening-report-{timestamp}.pdf"

    logger.info(f"Generated screening report: {filename} ({len(pdf_bytes)} bytes)")

    return {
        'pdf_bytes': pdf_bytes,
        'filename': filename,
        'report_type': 'screening',
        'demo_mode': demo_mode,
    }


def generate_admin_agreement(data: Dict[str, Any]) -> bytes:
    """
    Generate an Administration Agreement PDF.

    Args:
        data: Dict containing:
            - fund_name: Name of the fund
            - sponsor_name: Name of the sponsor
            - services: List of service dicts with name, description, fee_type, annual_fee
            - setup_fees: List of setup fee dicts with name, amount, description
            - annual_total: Total annual fees
            - setup_total: Total setup fees
            - effective_bps: Effective basis points on AUM
            - fund_size_formatted: Formatted fund size string
            - complexity: Complexity rating string
            - generated_at: ISO timestamp

    Returns:
        PDF file contents as bytes
    """
    styles = _get_styles()

    # Add a right-aligned style for currency columns
    styles['RightAligned'] = ParagraphStyle(
        'RightAligned',
        parent=styles['Normal'],
        alignment=TA_RIGHT,
        fontSize=10,
        leading=14,
    )

    elements = []

    fund_name = data.get('fund_name', 'Unknown Fund')
    sponsor_name = data.get('sponsor_name', 'Unknown Sponsor')
    generated_at = data.get('generated_at', datetime.now().isoformat())

    try:
        gen_dt = datetime.fromisoformat(generated_at.replace('Z', '+00:00'))
    except Exception:
        gen_dt = datetime.now()

    # ── Title ──
    elements.append(Paragraph('Administration Agreement', styles['Title']))
    elements.append(Spacer(1, 2 * mm))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#dee2e6')))
    elements.append(Spacer(1, 6 * mm))

    # ── Parties ──
    elements.append(Paragraph('1. Parties', styles['Heading1']))

    parties_data = [
        ['The Fund:', fund_name],
        ['The Sponsor:', sponsor_name],
        ['The Administrator:', 'ABC Fund Services (Jersey) Limited'],
    ]
    parties_table = Table(parties_data, colWidths=[40 * mm, 120 * mm])
    parties_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#495057')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(parties_table)
    elements.append(Spacer(1, 4 * mm))

    elements.append(Paragraph(
        f'Date: {gen_dt.strftime("%d %B %Y")}',
        styles['Normal']
    ))
    elements.append(Spacer(1, 6 * mm))

    # ── Appointment ──
    elements.append(Paragraph('2. Appointment', styles['Heading1']))
    appointment_text = (
        f'The Fund hereby appoints ABC Fund Services (Jersey) Limited '
        f'("the Administrator") to provide fund administration services to '
        f'{fund_name} ("the Fund") as set out in the Schedule of Services below. '
        f'The Administrator accepts such appointment and agrees to perform the '
        f'services in accordance with the terms and conditions of this Agreement, '
        f'applicable law, and the regulations of the Jersey Financial Services Commission.'
    )
    elements.append(Paragraph(appointment_text, styles['Normal']))
    elements.append(Spacer(1, 6 * mm))

    # ── Schedule of Services ──
    elements.append(Paragraph('3. Schedule of Services', styles['Heading1']))

    services = data.get('services', [])
    if services:
        svc_header = [
            Paragraph('<b>Service</b>', styles['Normal']),
            Paragraph('<b>Description</b>', styles['Normal']),
        ]
        svc_data = [svc_header]
        for svc in services:
            svc_data.append([
                Paragraph(svc.get('name', 'N/A'), styles['Normal']),
                Paragraph(svc.get('description', ''), styles['Small']),
            ])

        svc_table = Table(svc_data, colWidths=[55 * mm, 105 * mm])
        svc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ]))
        elements.append(svc_table)
    else:
        elements.append(Paragraph('No services selected.', styles['Normal']))

    elements.append(Spacer(1, 6 * mm))

    # ── Fee Schedule ──
    elements.append(Paragraph('4. Fee Schedule', styles['Heading1']))
    elements.append(Paragraph(
        f'Based on a target fund size of {data.get("fund_size_formatted", "N/A")} '
        f'and a structural complexity rating of {data.get("complexity", "low").capitalize()}, '
        f'the following fee schedule shall apply:',
        styles['Normal']
    ))
    elements.append(Spacer(1, 3 * mm))

    # Annual fees table
    elements.append(Paragraph('Annual Fees', styles['Heading2']))

    fee_header = [
        Paragraph('<b>Service</b>', styles['Normal']),
        Paragraph('<b>Fee Type</b>', styles['Normal']),
        Paragraph('<b>Annual Fee</b>', styles['RightAligned']),
    ]
    fee_data = [fee_header]

    for svc in services:
        fee_type = svc.get('fee_type', 'Fixed annual')
        annual_fee = svc.get('annual_fee', 0)
        fee_data.append([
            Paragraph(svc.get('name', 'N/A'), styles['Normal']),
            Paragraph(fee_type, styles['Small']),
            Paragraph(f"\u00a3{annual_fee:,.0f}", styles['RightAligned']),
        ])

    # Totals row
    annual_total = data.get('annual_total', 0)
    fee_data.append([
        Paragraph('<b>Total Annual Fee</b>', styles['Normal']),
        Paragraph('', styles['Normal']),
        Paragraph(f"<b>\u00a3{annual_total:,.0f}</b>", styles['RightAligned']),
    ])

    fee_table = Table(fee_data, colWidths=[60 * mm, 50 * mm, 50 * mm])
    fee_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        # Bold totals row
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e9ecef')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    elements.append(fee_table)
    elements.append(Spacer(1, 4 * mm))

    # Effective rate note
    effective_bps = data.get('effective_bps', 0)
    elements.append(Paragraph(
        f'Effective rate on NAV at target fund size: <b>{effective_bps} bps</b>',
        styles['Small']
    ))
    elements.append(Spacer(1, 4 * mm))

    # Setup fees table
    setup_fees = data.get('setup_fees', [])
    if setup_fees:
        elements.append(Paragraph('One-Time Setup Fees', styles['Heading2']))

        setup_header = [
            Paragraph('<b>Item</b>', styles['Normal']),
            Paragraph('<b>Description</b>', styles['Normal']),
            Paragraph('<b>Amount</b>', styles['RightAligned']),
        ]
        setup_data = [setup_header]

        for sf in setup_fees:
            amount = sf.get('amount', 0)
            amount_str = f"\u00a3{amount:,.0f}" if amount > 0 else 'Included'
            setup_data.append([
                Paragraph(sf.get('name', 'N/A'), styles['Normal']),
                Paragraph(sf.get('description', ''), styles['Small']),
                Paragraph(amount_str, styles['RightAligned']),
            ])

        # Setup total
        setup_total = data.get('setup_total', 0)
        setup_data.append([
            Paragraph('<b>Total Setup Fee</b>', styles['Normal']),
            Paragraph('', styles['Normal']),
            Paragraph(f"<b>\u00a3{setup_total:,.0f}</b>", styles['RightAligned']),
        ])

        setup_table = Table(setup_data, colWidths=[55 * mm, 60 * mm, 45 * mm])
        setup_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e9ecef')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        elements.append(setup_table)

    elements.append(Spacer(1, 6 * mm))

    # ── Standard Terms ──
    elements.append(Paragraph('5. Standard Terms', styles['Heading1']))

    terms = [
        (
            'Confidentiality',
            'Each party shall treat as confidential all information received from the '
            'other party in connection with this Agreement and shall not disclose such '
            'information to any third party without the prior written consent of the other '
            'party, except as required by law or regulation.'
        ),
        (
            'Termination',
            'Either party may terminate this Agreement by giving not less than 90 days\' '
            'written notice to the other party. Upon termination, the Administrator shall '
            'provide reasonable assistance in transferring the administration services to '
            'a successor administrator.'
        ),
        (
            'Governing Law',
            'This Agreement shall be governed by and construed in accordance with the laws '
            'of the Island of Jersey, and the parties submit to the exclusive jurisdiction '
            'of the courts of Jersey.'
        ),
        (
            'Liability',
            'The Administrator shall not be liable for any loss arising from any act or '
            'omission in the performance of its duties hereunder except where such loss '
            'arises from the Administrator\'s negligence, wilful default or fraud.'
        ),
    ]

    for title, body in terms:
        elements.append(Paragraph(f'<b>{title}</b>', styles['Normal']))
        elements.append(Spacer(1, 1 * mm))
        elements.append(Paragraph(body, styles['Normal']))
        elements.append(Spacer(1, 3 * mm))

    elements.append(Spacer(1, 6 * mm))

    # ── Signature Blocks ──
    elements.append(Paragraph('6. Execution', styles['Heading1']))
    elements.append(Paragraph(
        'IN WITNESS WHEREOF the parties have executed this Agreement on the date first written above.',
        styles['Normal']
    ))
    elements.append(Spacer(1, 8 * mm))

    # Fund signature block
    elements.append(Paragraph(f'<b>For and on behalf of {fund_name}</b>', styles['Normal']))
    elements.append(Spacer(1, 10 * mm))

    fund_sig = [
        ['Signature:', '_' * 45],
        ['Name:', '_' * 45],
        ['Title:', 'Authorized Signatory'],
        ['Date:', '_' * 45],
    ]
    fund_sig_table = Table(fund_sig, colWidths=[25 * mm, 80 * mm])
    fund_sig_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#495057')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(fund_sig_table)
    elements.append(Spacer(1, 10 * mm))

    # Administrator signature block
    elements.append(Paragraph('<b>For and on behalf of ABC Fund Services (Jersey) Limited</b>', styles['Normal']))
    elements.append(Spacer(1, 10 * mm))

    admin_sig = [
        ['Signature:', '_' * 45],
        ['Name:', '_' * 45],
        ['Title:', 'Authorized Signatory'],
        ['Date:', '_' * 45],
    ]
    admin_sig_table = Table(admin_sig, colWidths=[25 * mm, 80 * mm])
    admin_sig_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#495057')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(admin_sig_table)

    # ── Build the PDF ──
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=20 * mm,
    )

    def add_page_number(canvas, doc):
        canvas.saveState()
        page_num = canvas.getPageNumber()
        text = f"Page {page_num} | Confidential | ABC Fund Services (Jersey) Limited"
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#6c757d'))
        canvas.drawCentredString(A4[0] / 2, 10 * mm, text)
        canvas.restoreState()

    doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    logger.info(f"Generated admin agreement PDF ({len(pdf_bytes)} bytes)")
    return pdf_bytes