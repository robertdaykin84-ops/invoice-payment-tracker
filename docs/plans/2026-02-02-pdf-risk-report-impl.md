# PDF Risk Report Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Generate downloadable PDF compliance reports with risk assessment and screening results, saved to Google Drive.

**Architecture:** Create `services/pdf_report.py` using ReportLab for PDF generation. Three report types (compliance, board, audit) share common building blocks. API endpoint streams PDF to browser and optionally saves to GDrive via existing `gdrive_audit.py`.

**Tech Stack:** ReportLab (PDF generation), Flask (API endpoint), existing gdrive_audit.py integration

---

### Task 1: Add ReportLab dependency

**Files:**
- Modify: `packages/client-onboarding/requirements.txt`

**Step 1: Add reportlab to requirements**

Edit `requirements.txt` and add at the end:

```
# PDF Generation
reportlab==4.1.0
```

**Step 2: Install dependency**

Run: `cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && pip install reportlab==4.1.0`

Expected: Successfully installed reportlab-4.1.0

**Step 3: Verify installation**

Run: `python3 -c "from reportlab.lib.pagesizes import A4; print('ReportLab OK')"`

Expected: `ReportLab OK`

**Step 4: Commit**

```bash
git add packages/client-onboarding/requirements.txt
git commit -m "chore(client-onboarding): add reportlab for PDF generation"
```

---

### Task 2: Create PDF report service - Core structure and data gathering

**Files:**
- Create: `packages/client-onboarding/services/pdf_report.py`

**Step 1: Create the service file with imports and data gathering**

Create `services/pdf_report.py`:

```python
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
```

**Step 2: Verify syntax**

Run: `cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && python3 -c "from services.pdf_report import gather_report_data; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add packages/client-onboarding/services/pdf_report.py
git commit -m "feat(client-onboarding): add PDF report service - data gathering"
```

---

### Task 3: Add PDF building utilities and styles

**Files:**
- Modify: `packages/client-onboarding/services/pdf_report.py`

**Step 1: Add style definitions and utility functions**

Add after the `_get_demo_data` function:

```python


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
```

**Step 2: Verify syntax**

Run: `cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && python3 -c "from services.pdf_report import _get_styles, _create_header; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add packages/client-onboarding/services/pdf_report.py
git commit -m "feat(client-onboarding): add PDF report styles and utilities"
```

---

### Task 4: Add screening results and signature sections

**Files:**
- Modify: `packages/client-onboarding/services/pdf_report.py`

**Step 1: Add screening results and signature block functions**

Add after the `_create_factor_breakdown` function:

```python


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
```

**Step 2: Verify syntax**

Run: `cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && python3 -c "from services.pdf_report import _create_screening_results, _create_signature_block; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add packages/client-onboarding/services/pdf_report.py
git commit -m "feat(client-onboarding): add PDF screening results and signature sections"
```

---

### Task 5: Add report builder functions

**Files:**
- Modify: `packages/client-onboarding/services/pdf_report.py`

**Step 1: Add the three report builder functions**

Add after the `_create_methodology_notes` function:

```python


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
```

**Step 2: Verify syntax**

Run: `cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && python3 -c "from services.pdf_report import _build_compliance_report, _build_board_report, _build_audit_report; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add packages/client-onboarding/services/pdf_report.py
git commit -m "feat(client-onboarding): add PDF report builder functions"
```

---

### Task 6: Add main generate_report function and exports

**Files:**
- Modify: `packages/client-onboarding/services/pdf_report.py`
- Modify: `packages/client-onboarding/services/__init__.py`

**Step 1: Add the main generate_report function**

Add at the end of `pdf_report.py`:

```python


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
        styles = _get_styles()
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
```

**Step 2: Update services/__init__.py to export pdf_report**

Add to `services/__init__.py` after the risk_scoring imports:

```python
from .pdf_report import (
    generate_report,
    gather_report_data,
    REPORT_TYPES
)
```

And add to the `__all__` list:

```python
    # PDF Reports
    'generate_report',
    'gather_report_data',
    'REPORT_TYPES',
```

**Step 3: Verify imports**

Run: `cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && python3 -c "from services import generate_report, REPORT_TYPES; print('OK:', REPORT_TYPES)"`

Expected: `OK: ['compliance', 'board', 'audit']`

**Step 4: Commit**

```bash
git add packages/client-onboarding/services/pdf_report.py packages/client-onboarding/services/__init__.py
git commit -m "feat(client-onboarding): add generate_report function and exports"
```

---

### Task 7: Add API endpoint

**Files:**
- Modify: `packages/client-onboarding/app.py`

**Step 1: Add the report generation endpoint**

Find the imports section at the top of `app.py` and add to the services import:

```python
from services import generate_report, REPORT_TYPES
```

Then add the new endpoint. Find a suitable location (after the `/api/screening/run` endpoint) and add:

```python
@app.route('/api/report/generate/<onboarding_id>')
def api_generate_report(onboarding_id):
    """Generate PDF risk report for an onboarding."""
    report_type = request.args.get('type', 'compliance')
    save_to_drive = request.args.get('save_to_drive', 'true').lower() == 'true'

    # Get sponsor/fund from session or args
    sponsor_name = request.args.get('sponsor_name') or session.get('current_sponsor')
    fund_name = request.args.get('fund_name') or session.get('current_fund')

    try:
        result = generate_report(
            onboarding_id=onboarding_id,
            report_type=report_type,
            save_to_drive=save_to_drive,
            sponsor_name=sponsor_name,
            fund_name=fund_name
        )

        # Create response with PDF
        response = make_response(result['pdf_bytes'])
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{result["filename"]}"'

        # Add custom headers for JS to read
        if result.get('drive_result'):
            drive = result['drive_result']
            response.headers['X-Drive-Status'] = drive.get('status', 'unknown')
            if drive.get('file_id'):
                response.headers['X-Drive-File-Id'] = drive['file_id']

        response.headers['X-Demo-Mode'] = 'true' if result.get('demo_mode') else 'false'

        return response

    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        logger.exception(f"Error generating report: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to generate report'}), 500
```

**Step 2: Verify endpoint syntax**

Run: `cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && python3 -c "import app; print('App OK')"`

Expected: `App OK` (with possible warnings about demo mode)

**Step 3: Commit**

```bash
git add packages/client-onboarding/app.py
git commit -m "feat(client-onboarding): add /api/report/generate endpoint"
```

---

### Task 8: Add report generation buttons to phase4.html

**Files:**
- Modify: `packages/client-onboarding/templates/onboarding/phase4.html`

**Step 1: Add the Generate Reports section**

Find the Risk Assessment card closing `</div>` (around line 242, after the AI Risk Analysis section) and add before it:

```html
                <!-- Generate Reports -->
                <div id="report-generation" class="border rounded p-3 mt-4" style="display: none;">
                    <h6 class="mb-3"><i class="bi bi-file-earmark-pdf me-2"></i>Generate Reports</h6>
                    <div class="row g-2">
                        <div class="col-md-4">
                            <button class="btn btn-outline-primary w-100 report-btn" data-type="compliance">
                                <i class="bi bi-file-text me-1"></i>
                                Compliance Report
                                <div class="small text-muted">Full detail for MLRO</div>
                            </button>
                        </div>
                        <div class="col-md-4">
                            <button class="btn btn-outline-primary w-100 report-btn" data-type="board">
                                <i class="bi bi-clipboard-data me-1"></i>
                                Board Summary
                                <div class="small text-muted">Executive overview</div>
                            </button>
                        </div>
                        <div class="col-md-4">
                            <button class="btn btn-outline-primary w-100 report-btn" data-type="audit">
                                <i class="bi bi-folder2-open me-1"></i>
                                Audit Pack
                                <div class="small text-muted">Complete record</div>
                            </button>
                        </div>
                    </div>
                    <div id="report-status" class="small text-muted mt-2" style="display: none;"></div>
                </div>
```

**Step 2: Add JavaScript for report generation**

Find the closing `});` of the `document.addEventListener('DOMContentLoaded'` function (around line 607) and add before it:

```javascript

    // Report generation
    document.querySelectorAll('.report-btn').forEach(btn => {
        btn.addEventListener('click', async function() {
            const reportType = this.dataset.type;
            const statusDiv = document.getElementById('report-status');
            const originalText = this.innerHTML;

            // Show loading state
            this.disabled = true;
            this.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Generating...';
            statusDiv.style.display = 'block';
            statusDiv.textContent = `Generating ${reportType} report...`;

            try {
                const response = await fetch(`/api/report/generate/{{ onboarding_id }}?type=${reportType}`);

                if (!response.ok) {
                    throw new Error('Failed to generate report');
                }

                // Get filename from header
                const disposition = response.headers.get('Content-Disposition');
                const filename = disposition ? disposition.split('filename=')[1].replace(/"/g, '') : `report-${reportType}.pdf`;

                // Download the PDF
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                a.remove();

                // Show success message
                const driveStatus = response.headers.get('X-Drive-Status');
                const demoMode = response.headers.get('X-Demo-Mode') === 'true';

                if (driveStatus === 'success') {
                    statusDiv.innerHTML = '<i class="bi bi-cloud-check text-success me-1"></i>Report saved to Google Drive';
                } else if (driveStatus === 'demo') {
                    statusDiv.innerHTML = '<i class="bi bi-info-circle text-info me-1"></i>Demo mode - report not saved to Drive';
                } else if (demoMode) {
                    statusDiv.innerHTML = '<i class="bi bi-info-circle text-info me-1"></i>Report generated (demo mode)';
                } else {
                    statusDiv.innerHTML = '<i class="bi bi-check-circle text-success me-1"></i>Report downloaded';
                }

            } catch (error) {
                statusDiv.innerHTML = '<i class="bi bi-exclamation-triangle text-danger me-1"></i>Failed to generate report';
                console.error('Report generation error:', error);
            } finally {
                this.disabled = false;
                this.innerHTML = originalText;
            }
        });
    });
```

**Step 3: Show report section when risk assessment is displayed**

Find the line `riskCard.style.display = 'block';` in the `displayResults` function and add after it:

```javascript
        document.getElementById('report-generation').style.display = 'block';
```

**Step 4: Verify template syntax**

Run: `cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && python3 -c "from flask import Flask; from jinja2 import Environment, FileSystemLoader; env = Environment(loader=FileSystemLoader('templates')); t = env.get_template('onboarding/phase4.html'); print('Template OK')"`

Expected: `Template OK`

**Step 5: Commit**

```bash
git add packages/client-onboarding/templates/onboarding/phase4.html
git commit -m "feat(client-onboarding): add report generation buttons to phase4"
```

---

### Task 9: Test PDF generation

**Step 1: Test generate_report function directly**

Run:
```bash
cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && python3 -c "
from services.pdf_report import generate_report

# Test compliance report
result = generate_report('ONB-TEST-001', 'compliance', save_to_drive=False)
print(f'Compliance report: {len(result[\"pdf_bytes\"])} bytes, filename: {result[\"filename\"]}')

# Test board report
result = generate_report('ONB-TEST-001', 'board', save_to_drive=False)
print(f'Board report: {len(result[\"pdf_bytes\"])} bytes, filename: {result[\"filename\"]}')

# Test audit report
result = generate_report('ONB-TEST-001', 'audit', save_to_drive=False)
print(f'Audit report: {len(result[\"pdf_bytes\"])} bytes, filename: {result[\"filename\"]}')

print('All report types generated successfully!')
"
```

Expected: All three report types generate with reasonable byte sizes (>5000 bytes each)

**Step 2: Save a test PDF to verify it opens correctly**

Run:
```bash
cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && python3 -c "
from services.pdf_report import generate_report

result = generate_report('ONB-TEST-001', 'compliance', save_to_drive=False)
with open('/tmp/test-compliance-report.pdf', 'wb') as f:
    f.write(result['pdf_bytes'])
print('Saved to /tmp/test-compliance-report.pdf')
" && open /tmp/test-compliance-report.pdf
```

Expected: PDF opens in default viewer showing formatted compliance report

**Step 3: Commit verification**

```bash
git add -A
git commit -m "test(client-onboarding): verify PDF report generation" --allow-empty
```

---

### Task 10: Final integration test

**Step 1: Start the Flask app**

Run: `cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && python3 app.py`

Expected: Flask app starts on http://127.0.0.1:5000

**Step 2: Test the API endpoint**

In a separate terminal, run:
```bash
curl -o /tmp/api-test-report.pdf "http://127.0.0.1:5000/api/report/generate/ONB-001?type=compliance" && open /tmp/api-test-report.pdf
```

Expected: PDF downloads and opens correctly

**Step 3: Test via browser**

1. Navigate to http://127.0.0.1:5000
2. Go to an onboarding's Phase 4 (Screening)
3. Run screening
4. Click "Compliance Report" button
5. Verify PDF downloads

**Step 4: Final commit**

```bash
git add -A
git status
git commit -m "feat(client-onboarding): complete PDF risk report feature

- Three report types: compliance, board, audit
- ReportLab PDF generation with styled tables
- GDrive integration for saving reports
- API endpoint /api/report/generate/<id>
- Frontend buttons in phase4.html

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
" --allow-empty
```

---

*End of Implementation Plan*
