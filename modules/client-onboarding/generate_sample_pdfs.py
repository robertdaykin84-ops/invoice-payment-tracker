#!/usr/bin/env python3
"""Generate sample KYC PDF documents for Phase 4 testing.

Creates 6 PDFs:
- passport-michael-brown-certified.pdf (replace 3KB placeholder)
- address-proof-michael-brown-certified.pdf (replace 3KB placeholder)
- source-of-wealth-michael-brown.pdf (replace 4KB placeholder)
- source-of-wealth-john-smith.pdf (NEW - missing)
- source-of-wealth-sarah-johnson.pdf (NEW - missing)
- proof-of-registered-office-granite-capital.pdf (NEW - missing)
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Frame, PageTemplate, BaseDocTemplate, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'static', 'samples', 'kyc-documents')

# Colors
NAVY = HexColor('#1a237e')
RED = HexColor('#c62828')
GREY = HexColor('#666666')
LIGHT_GREY = HexColor('#f5f5f5')
BLUE = HexColor('#0066cc')
ORANGE = HexColor('#ff6600')
GREEN_BG = HexColor('#e8f5e9')
GREEN_BORDER = HexColor('#4caf50')
AMBER = HexColor('#ff9800')
AMBER_BG = HexColor('#fff3e0')

# Shared styles
styles = getSampleStyleSheet()

TITLE_STYLE = ParagraphStyle(
    'DocTitle', parent=styles['Heading1'],
    fontSize=22, textColor=NAVY, alignment=TA_CENTER, spaceAfter=6
)
SUBTITLE_STYLE = ParagraphStyle(
    'DocSubtitle', parent=styles['Normal'],
    fontSize=11, textColor=GREY, alignment=TA_CENTER, spaceAfter=20
)
SECTION_STYLE = ParagraphStyle(
    'SectionHead', parent=styles['Heading2'],
    fontSize=14, textColor=NAVY, spaceAfter=10, spaceBefore=16,
    borderWidth=0, borderPadding=0
)
BODY_STYLE = ParagraphStyle(
    'DocBody', parent=styles['Normal'],
    fontSize=10, leading=14, spaceAfter=6
)
BOLD_STYLE = ParagraphStyle(
    'DocBold', parent=BODY_STYLE, fontName='Helvetica-Bold'
)
CERT_TITLE = ParagraphStyle(
    'CertTitle', parent=styles['Heading3'],
    fontSize=14, textColor=RED, spaceAfter=10
)
FIELD_LABEL = ParagraphStyle(
    'FieldLabel', parent=styles['Normal'],
    fontSize=10, textColor=GREY, fontName='Helvetica-Bold'
)
FIELD_VALUE = ParagraphStyle(
    'FieldValue', parent=styles['Normal'], fontSize=10
)
SMALL_STYLE = ParagraphStyle(
    'Small', parent=styles['Normal'], fontSize=9, textColor=GREY
)


def add_certification_section(elements):
    """Add the standard Roberts & Partners certification block."""
    elements.append(Spacer(1, 20))

    # Red border certification box as a table
    cert_data = [
        [Paragraph('<b>CERTIFICATION</b>', ParagraphStyle(
            'ct', parent=CERT_TITLE, fontSize=14, textColor=RED, spaceAfter=4))],
        [Paragraph('<b>I certify this is a true copy of the original document.</b>', BODY_STYLE)],
        [Paragraph(
            'I have seen the original document and confirm that this copy is a true '
            'and accurate representation of the original document.', BODY_STYLE)],
        [Spacer(1, 10)],
        [Paragraph('<i>J. Roberts</i>', ParagraphStyle(
            'sig', parent=BODY_STYLE, fontSize=14, fontName='Helvetica-Oblique'))],
        [Paragraph('___________________________', BODY_STYLE)],
        [Paragraph('<b>Signature of Certifier</b>', BODY_STYLE)],
        [Spacer(1, 8)],
    ]

    # Certifier details
    cert_fields = [
        ('Name:', 'James Roberts'),
        ('Qualification:', 'Solicitor'),
        ('Firm:', 'Roberts & Partners LLP'),
        ('Address:', "15 Lincoln's Inn Fields, London WC2A 3BP"),
        ('Date:', '15 January 2026'),
    ]
    for label, value in cert_fields:
        row_table = Table(
            [[Paragraph(f'<b>{label}</b>', FIELD_LABEL),
              Paragraph(value, FIELD_VALUE)]],
            colWidths=[100, 350]
        )
        row_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ]))
        cert_data.append([row_table])

    # Stamp text
    cert_data.append([Spacer(1, 6)])
    cert_data.append([Paragraph(
        '<font color="#c62828"><b>ROBERTS &amp; PARTNERS | SOLICITORS | CERTIFIED</b></font>',
        ParagraphStyle('stamp', parent=SMALL_STYLE, textColor=RED, alignment=TA_RIGHT)
    )])

    cert_table = Table(cert_data, colWidths=[470])
    cert_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 2, RED),
        ('LEFTPADDING', (0, 0), (-1, -1), 15),
        ('RIGHTPADDING', (0, 0), (-1, -1), 15),
        ('TOPPADDING', (0, 0), (0, 0), 12),
        ('BOTTOMPADDING', (-1, -1), (-1, -1), 12),
    ]))
    elements.append(cert_table)


def make_field_row(label, value, label_width=140, value_width=330):
    """Create a label-value pair as a table row."""
    return Table(
        [[Paragraph(f'<b>{label}</b>', FIELD_LABEL),
          Paragraph(value, FIELD_VALUE)]],
        colWidths=[label_width, value_width]
    )


def build_doc(filename, elements):
    """Build a PDF document with the given elements."""
    path = os.path.join(OUTPUT_DIR, filename)
    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )
    doc.build(elements)
    size_kb = os.path.getsize(path) / 1024
    print(f"  Created: {filename} ({size_kb:.0f} KB)")
    return path


# ─── PASSPORT ────────────────────────────────────────────────────────────────

def generate_passport(person):
    """Generate a certified passport copy PDF."""
    elements = []

    # Header
    elements.append(Paragraph('CERTIFIED TRUE COPY', TITLE_STYLE))
    elements.append(Paragraph('United Kingdom Passport', SUBTITLE_STYLE))

    # Blue line
    elements.append(Table([['']], colWidths=[470], rowHeights=[3]))
    elements[-1].setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), NAVY),
        ('LINEBELOW', (0, 0), (-1, -1), 0, white),
    ]))
    elements.append(Spacer(1, 10))

    # Passport header bar
    passport_header = Table(
        [[Paragraph(
            '<font color="white"><b>UNITED KINGDOM OF GREAT BRITAIN AND NORTHERN IRELAND<br/>PASSPORT</b></font>',
            ParagraphStyle('ph', parent=BODY_STYLE, alignment=TA_CENTER, textColor=white)
        )]],
        colWidths=[470], rowHeights=[40]
    )
    passport_header.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), NAVY),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(passport_header)
    elements.append(Spacer(1, 10))

    # Photo placeholder + fields
    photo = Table(
        [[Paragraph(f'[PHOTOGRAPH]<br/>{person["short_name"]}',
                    ParagraphStyle('photo', parent=SMALL_STYLE, alignment=TA_CENTER))]],
        colWidths=[80], rowHeights=[100]
    )
    photo.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, black),
        ('BACKGROUND', (0, 0), (-1, -1), HexColor('#dddddd')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    passport_fields = [
        ('Type / Type:', 'P'),
        ('Country Code:', 'GBR'),
        ('Passport No.:', person['passport_no']),
        ('Surname:', person['surname']),
        ('Given Names:', person['given_names']),
        ('Nationality:', 'BRITISH CITIZEN'),
        ('Date of Birth:', person['dob_display']),
        ('Sex:', person['sex']),
        ('Place of Birth:', person['pob']),
        ('Date of Issue:', person['issue_date']),
        ('Date of Expiry:', person['expiry_date']),
        ('Authority:', 'HMPO'),
    ]

    field_rows = []
    for label, value in passport_fields:
        field_rows.append([
            Paragraph(f'<b>{label}</b>', FIELD_LABEL),
            Paragraph(value, FIELD_VALUE)
        ])

    fields_table = Table(field_rows, colWidths=[120, 200])
    fields_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))

    # Combine photo and fields side by side
    layout = Table([[fields_table, photo]], colWidths=[340, 130])
    layout.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(layout)

    # MRZ
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        f'<font face="Courier" size="8">{person["mrz_line1"]}<br/>{person["mrz_line2"]}</font>',
        ParagraphStyle('mrz', parent=BODY_STYLE, fontName='Courier', fontSize=8,
                       leading=10, spaceBefore=6)
    ))

    # Passport box border
    elements.append(Spacer(1, 6))

    add_certification_section(elements)

    return build_doc(person['passport_filename'], elements)


# ─── ADDRESS PROOF ───────────────────────────────────────────────────────────

def generate_address_proof(person):
    """Generate a certified utility bill address proof PDF."""
    elements = []

    # Utility company header
    header_table = Table([
        [Paragraph('<font color="#0066cc"><b>British</b></font><font color="#ff6600"><b>Gas</b></font>',
                   ParagraphStyle('logo', parent=styles['Normal'], fontSize=22)),
         Paragraph('<b>Gas &amp; Electricity Bill</b><br/>Statement Date: 15 December 2025',
                   ParagraphStyle('bi', parent=BODY_STYLE, alignment=TA_RIGHT))]
    ], colWidths=[235, 235])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEBELOW', (0, 0), (-1, -1), 2, BLUE),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 15))

    # Address section
    addr_content = Table([
        [Paragraph('<font size="8" color="#666666">SERVICE ADDRESS &amp; ACCOUNT HOLDER</font>', SMALL_STYLE)],
        [Paragraph(
            f'<b>Mr {person["full_name"]}</b><br/>'
            f'{person["address_line1"]}<br/>'
            f'{person["address_city"]}<br/>'
            f'{person["address_postcode"]}<br/>'
            'United Kingdom',
            BODY_STYLE
        )],
    ], colWidths=[470])
    addr_content.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GREY),
        ('LEFTPADDING', (0, 0), (-1, -1), 15),
        ('TOPPADDING', (0, 0), (0, 0), 10),
        ('BOTTOMPADDING', (-1, -1), (-1, -1), 10),
    ]))
    elements.append(addr_content)
    elements.append(Spacer(1, 15))

    # Account details boxes
    detail_data = [
        [Paragraph('<font size="8" color="#666666">ACCOUNT NUMBER</font>', SMALL_STYLE),
         Paragraph('<font size="8" color="#666666">BILL PERIOD</font>', SMALL_STYLE),
         Paragraph('<font size="8" color="#666666">PAYMENT DUE</font>', SMALL_STYLE)],
        [Paragraph(f'<b>{person["account_no"]}</b>', BODY_STYLE),
         Paragraph('<b>15 Nov - 15 Dec 2025</b>', BODY_STYLE),
         Paragraph('<b>02 January 2026</b>', BODY_STYLE)],
    ]
    detail_table = Table(detail_data, colWidths=[156, 157, 157])
    detail_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GREY),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (-1, -1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#dddddd')),
    ]))
    elements.append(detail_table)
    elements.append(Spacer(1, 15))

    # Charges table
    charges = [
        ['Description', 'Usage', 'Amount'],
        ['Gas Consumption', f'{person["gas_kwh"]} kWh', f'{person["gas_cost"]}'],
        ['Electricity Consumption', f'{person["elec_kwh"]} kWh', f'{person["elec_cost"]}'],
        ['Standing Charge (Gas)', '31 days', person['gas_standing']],
        ['Standing Charge (Electric)', '31 days', person['elec_standing']],
        ['VAT @ 5%', '', person['vat']],
        ['Total Amount Due', '', person['total']],
    ]
    charges_formatted = []
    for i, row in enumerate(charges):
        if i == 0:
            charges_formatted.append([
                Paragraph(f'<font color="#666666">{c}</font>', SMALL_STYLE) for c in row
            ])
        elif i == len(charges) - 1:
            charges_formatted.append([
                Paragraph(f'<b>{row[0]}</b>', BOLD_STYLE),
                Paragraph(row[1], BODY_STYLE),
                Paragraph(f'<b>{row[2]}</b>', BOLD_STYLE),
            ])
        else:
            charges_formatted.append([Paragraph(c, BODY_STYLE) for c in row])

    charges_table = Table(charges_formatted, colWidths=[235, 100, 135])
    charges_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_GREY),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, HexColor('#dddddd')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(charges_table)
    elements.append(Spacer(1, 10))

    elements.append(Paragraph(
        'If you have any questions about this bill, please call us on 0333 202 9802',
        SMALL_STYLE
    ))

    add_certification_section(elements)

    return build_doc(person['address_filename'], elements)


# ─── SOURCE OF WEALTH ────────────────────────────────────────────────────────

def generate_source_of_wealth(person):
    """Generate a certified source of wealth statement PDF."""
    elements = []

    # Header
    elements.append(Paragraph('SOURCE OF WEALTH STATEMENT', TITLE_STYLE))
    elements.append(Paragraph('Confidential Document - For KYC/AML Compliance Purposes', SUBTITLE_STYLE))

    # Blue line
    elements.append(Table([['']], colWidths=[470], rowHeights=[2]))
    elements[-1].setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), NAVY),
    ]))
    elements.append(Spacer(1, 10))

    # Personal Information
    elements.append(Paragraph('<b>Personal Information</b>', SECTION_STYLE))
    pi_fields = [
        ('Full Name:', person['full_name']),
        ('Date of Birth:', person['dob_long']),
        ('Nationality:', person['nationality']),
        ('Address:', person['full_address']),
        ('Date of Statement:', '15 January 2026'),
    ]
    for label, value in pi_fields:
        elements.append(make_field_row(label, value))
        elements.append(Spacer(1, 2))

    # Professional Background
    elements.append(Spacer(1, 8))
    elements.append(Paragraph('<b>Professional Background</b>', SECTION_STYLE))

    bg_data = [
        ('Current Position:', person['position']),
        ('Company:', 'Granite Capital Partners LLP'),
        ('Ownership Interest:', person['ownership']),
        ('Role:', person['role_desc']),
        ('Industry:', 'Private Equity / Investment Management'),
        ('Years in Industry:', person['years_industry']),
    ]
    bg_rows = []
    for label, value in bg_data:
        bg_rows.append([
            Paragraph(f'<b>{label}</b>', FIELD_LABEL),
            Paragraph(value, FIELD_VALUE)
        ])
    bg_table = Table(bg_rows, colWidths=[140, 320])
    bg_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor('#f9f9f9')),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEBEFOREWIDTH', (0, 0), (0, -1), 3),
        ('LINEBEFORE', (0, 0), (0, -1), 3, NAVY),
    ]))
    elements.append(bg_table)

    # Source of Wealth
    elements.append(Spacer(1, 8))
    elements.append(Paragraph('<b>Source of Wealth</b>', SECTION_STYLE))

    # Primary source
    primary_content = [
        [Paragraph(f'<b><font color="#2e7d32">Primary Source: {person["primary_source_title"]}</font></b>',
                   BODY_STYLE)],
        [Paragraph(f'<b>Description:</b> {person["primary_source_desc"]}', BODY_STYLE)],
        [Paragraph('<b>Income Components:</b>', BODY_STYLE)],
    ]
    for item in person['income_components']:
        primary_content.append([Paragraph(f'  \u2022  {item}', BODY_STYLE)])
    primary_content.append([Paragraph(
        f'<b>Estimated Annual Income:</b> {person["annual_income"]}', BODY_STYLE)])

    primary_table = Table(primary_content, colWidths=[460])
    primary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), GREEN_BG),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (0, 0), 10),
        ('BOTTOMPADDING', (-1, -1), (-1, -1), 10),
        ('LINEBEFORE', (0, 0), (0, -1), 3, GREEN_BORDER),
    ]))
    elements.append(primary_table)
    elements.append(Spacer(1, 8))

    # Secondary source
    secondary_content = [
        [Paragraph('<b><font color="#2e7d32">Secondary Source: Investment Portfolio</font></b>', BODY_STYLE)],
        [Paragraph(f'<b>Description:</b> {person["secondary_source_desc"]}', BODY_STYLE)],
    ]
    secondary_table = Table(secondary_content, colWidths=[460])
    secondary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), GREEN_BG),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (0, 0), 10),
        ('BOTTOMPADDING', (-1, -1), (-1, -1), 10),
        ('LINEBEFORE', (0, 0), (0, -1), 3, GREEN_BORDER),
    ]))
    elements.append(secondary_table)

    # Employment History
    elements.append(Spacer(1, 8))
    elements.append(Paragraph('<b>Employment History</b>', SECTION_STYLE))
    emp_rows = []
    for entry in person['employment']:
        emp_rows.append([Paragraph(f'<b>{entry[0]}</b> {entry[1]}', BODY_STYLE)])
    emp_table = Table(emp_rows, colWidths=[460])
    emp_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor('#f9f9f9')),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LINEBEFORE', (0, 0), (0, -1), 3, NAVY),
    ]))
    elements.append(emp_table)

    # Declaration
    elements.append(Spacer(1, 10))
    decl_content = [
        [Paragraph('<b><font color="#ff9800">Declaration</font></b>', BODY_STYLE)],
        [Paragraph(
            f'I, {person["full_name"]}, hereby declare that the information provided in this '
            'Source of Wealth Statement is true, accurate, and complete to the best of my '
            'knowledge and belief.', BODY_STYLE)],
        [Paragraph(
            'I understand that this information is being provided for anti-money laundering (AML) '
            'and know-your-customer (KYC) compliance purposes.', BODY_STYLE)],
    ]
    decl_table = Table(decl_content, colWidths=[460])
    decl_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 2, AMBER),
        ('BACKGROUND', (0, 0), (-1, -1), AMBER_BG),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (0, 0), 10),
        ('BOTTOMPADDING', (-1, -1), (-1, -1), 10),
    ]))
    elements.append(decl_table)

    # Signature
    elements.append(Spacer(1, 15))
    elements.append(Paragraph('<b>Signature of Declarant:</b>', BODY_STYLE))
    elements.append(Paragraph(
        f'<i><font size="14">{person["signature"]}</font></i>', BODY_STYLE))
    elements.append(Paragraph('___________________________', BODY_STYLE))
    sig_fields = [
        ('Name:', person['full_name']),
        ('Date:', '15 January 2026'),
    ]
    for label, value in sig_fields:
        elements.append(make_field_row(label, value))

    add_certification_section(elements)

    return build_doc(person['sow_filename'], elements)


# ─── PROOF OF REGISTERED OFFICE ──────────────────────────────────────────────

def generate_proof_of_registered_office():
    """Generate proof of registered office for Granite Capital Partners LLP."""
    elements = []

    # Header
    elements.append(Paragraph('PROOF OF REGISTERED OFFICE', TITLE_STYLE))
    elements.append(Paragraph('Granite Capital Partners LLP', SUBTITLE_STYLE))

    # Blue line
    elements.append(Table([['']], colWidths=[470], rowHeights=[2]))
    elements[-1].setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), NAVY),
    ]))
    elements.append(Spacer(1, 15))

    # Office details
    elements.append(Paragraph('<b>Registered Office Details</b>', SECTION_STYLE))
    office_fields = [
        ('Entity Name:', 'Granite Capital Partners LLP'),
        ('Registration No.:', 'OC412876'),
        ('Registered Office:', '25 St Helier Square, St Helier, Jersey, JE2 3RT'),
        ('Jurisdiction:', 'Jersey, Channel Islands'),
        ('Registered Since:', '15 March 2015'),
    ]
    for label, value in office_fields:
        elements.append(make_field_row(label, value))
        elements.append(Spacer(1, 2))

    # Lease / Tenancy details
    elements.append(Spacer(1, 8))
    elements.append(Paragraph('<b>Tenancy Agreement Summary</b>', SECTION_STYLE))

    lease_data = [
        ('Landlord:', 'St Helier Commercial Properties Ltd'),
        ('Property:', 'Suite 4B, 25 St Helier Square, St Helier, Jersey, JE2 3RT'),
        ('Lease Commencement:', '15 March 2015'),
        ('Lease Expiry:', '14 March 2030'),
        ('Lease Type:', 'Commercial Office Lease'),
        ('Annual Rent:', '\u00a385,000'),
    ]
    lease_rows = []
    for label, value in lease_data:
        lease_rows.append([
            Paragraph(f'<b>{label}</b>', FIELD_LABEL),
            Paragraph(value, FIELD_VALUE)
        ])
    lease_table = Table(lease_rows, colWidths=[140, 320])
    lease_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor('#f9f9f9')),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEBEFORE', (0, 0), (0, -1), 3, NAVY),
    ]))
    elements.append(lease_table)

    # Confirmation letter
    elements.append(Spacer(1, 15))
    elements.append(Paragraph('<b>Confirmation of Registered Office</b>', SECTION_STYLE))

    letter_text = (
        'This is to confirm that the registered office of Granite Capital Partners LLP '
        'is situated at Suite 4B, 25 St Helier Square, St Helier, Jersey, JE2 3RT. '
        'The premises have been occupied by the entity since 15 March 2015 under a '
        'commercial lease agreement.<br/><br/>'
        'The registered office is used for the conduct of the entity\'s business activities '
        'including fund administration, client meetings, and regulatory correspondence. '
        'All official communications from the Jersey Financial Services Commission (JFSC) '
        'are received at this address.<br/><br/>'
        'The entity maintains appropriate signage and a dedicated reception area at the '
        'registered office address.'
    )
    letter_content = [
        [Paragraph(letter_text, BODY_STYLE)],
    ]
    letter_table = Table(letter_content, colWidths=[460])
    letter_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor('#f9f9f9')),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (0, 0), 10),
        ('BOTTOMPADDING', (-1, -1), (-1, -1), 10),
        ('LINEBEFORE', (0, 0), (0, -1), 3, NAVY),
    ]))
    elements.append(letter_table)

    # Landlord confirmation
    elements.append(Spacer(1, 15))
    elements.append(Paragraph('<b>Landlord Confirmation</b>', SECTION_STYLE))
    elements.append(Paragraph(
        'I, David Patterson, Director of St Helier Commercial Properties Ltd, confirm that '
        'Granite Capital Partners LLP is the current tenant of Suite 4B, 25 St Helier Square, '
        'St Helier, Jersey, JE2 3RT, and has been in continuous occupation since 15 March 2015.',
        BODY_STYLE
    ))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph('<i><font size="14">D. Patterson</font></i>', BODY_STYLE))
    elements.append(Paragraph('___________________________', BODY_STYLE))
    landlord_fields = [
        ('Name:', 'David Patterson'),
        ('Title:', 'Director, St Helier Commercial Properties Ltd'),
        ('Date:', '10 January 2026'),
    ]
    for label, value in landlord_fields:
        elements.append(make_field_row(label, value))

    add_certification_section(elements)

    return build_doc('proof-of-registered-office-granite-capital.pdf', elements)


# ─── REGULATORY LICENSE ──────────────────────────────────────────────────────

def generate_regulatory_license():
    """Generate a regulatory license/authorisation for Granite Capital Partners LLP."""
    elements = []

    # Header
    elements.append(Paragraph('REGULATORY LICENSE', TITLE_STYLE))
    elements.append(Paragraph(
        'Jersey Financial Services Commission',
        ParagraphStyle('jfsc', parent=SUBTITLE_STYLE, textColor=NAVY, fontSize=13)
    ))
    elements.append(Paragraph('Financial Services (Jersey) Law 1998', SUBTITLE_STYLE))

    # Blue line
    elements.append(Table([['']], colWidths=[470], rowHeights=[3]))
    elements[-1].setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), NAVY),
    ]))
    elements.append(Spacer(1, 15))

    # License details
    elements.append(Paragraph('<b>License Details</b>', SECTION_STYLE))
    license_fields = [
        ('License Number:', 'JFSC/FSB/2015/0847'),
        ('Entity Name:', 'Granite Capital Partners LLP'),
        ('Registration No.:', 'OC412876'),
        ('Registered Office:', '25 St Helier Square, St Helier, Jersey, JE2 3RT'),
        ('License Category:', 'Fund Services Business'),
        ('Class of Business:', 'Class B Fund Administration'),
        ('Date of Issue:', '15 June 2015'),
        ('Renewal Date:', '14 June 2026'),
        ('Status:', 'Active'),
    ]
    for label, value in license_fields:
        elements.append(make_field_row(label, value))
        elements.append(Spacer(1, 2))

    # Permitted activities
    elements.append(Spacer(1, 8))
    elements.append(Paragraph('<b>Permitted Activities</b>', SECTION_STYLE))
    activities = [
        'Administration of collective investment funds',
        'Provision of fund management services',
        'Acting as designated fund service provider',
        'Provision of registrar and transfer agency services',
        'Fund accounting and NAV calculation',
    ]
    activity_rows = []
    for activity in activities:
        activity_rows.append([Paragraph(f'  \u2022  {activity}', BODY_STYLE)])
    activity_table = Table(activity_rows, colWidths=[460])
    activity_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor('#f9f9f9')),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEBEFORE', (0, 0), (0, -1), 3, NAVY),
    ]))
    elements.append(activity_table)

    # Conditions
    elements.append(Spacer(1, 10))
    elements.append(Paragraph('<b>Conditions of License</b>', SECTION_STYLE))
    conditions_text = (
        'This license is granted subject to compliance with:<br/><br/>'
        '1. Financial Services (Jersey) Law 1998<br/>'
        '2. Money Laundering (Jersey) Order 2008<br/>'
        '3. JFSC AML/CFT/CPF Handbook<br/>'
        '4. Fund Services Business Code of Practice<br/>'
        '5. All applicable JFSC guidance notes and policy statements<br/><br/>'
        'The licensee must maintain adequate capital resources, professional indemnity '
        'insurance, and appropriate systems and controls as prescribed by the Commission.'
    )
    cond_content = [[Paragraph(conditions_text, BODY_STYLE)]]
    cond_table = Table(cond_content, colWidths=[460])
    cond_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor('#f9f9f9')),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (0, 0), 10),
        ('BOTTOMPADDING', (-1, -1), (-1, -1), 10),
        ('LINEBEFORE', (0, 0), (0, -1), 3, NAVY),
    ]))
    elements.append(cond_table)

    # Authorisation
    elements.append(Spacer(1, 15))
    elements.append(Paragraph('<b>Authorised by:</b>', BODY_STYLE))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph('<i><font size="14">R. Mayfield</font></i>', BODY_STYLE))
    elements.append(Paragraph('___________________________', BODY_STYLE))
    auth_fields = [
        ('Name:', 'Richard Mayfield'),
        ('Title:', 'Director of Supervision, JFSC'),
        ('Date:', '15 June 2015'),
    ]
    for label, value in auth_fields:
        elements.append(make_field_row(label, value))

    # JFSC stamp
    elements.append(Spacer(1, 15))
    stamp_content = [[Paragraph(
        '<font color="#1a237e"><b>JERSEY FINANCIAL SERVICES COMMISSION<br/>'
        'OFFICIAL LICENSE<br/>JFSC/FSB/2015/0847</b></font>',
        ParagraphStyle('jfsc_stamp', parent=SMALL_STYLE, textColor=NAVY, alignment=TA_CENTER)
    )]]
    stamp_table = Table(stamp_content, colWidths=[200])
    stamp_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 2, NAVY),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(stamp_table)

    return build_doc('regulatory-license-granite-capital.pdf', elements)


# ─── PERSON DATA ─────────────────────────────────────────────────────────────

MICHAEL_BROWN = {
    'full_name': 'Michael James Brown',
    'short_name': 'Michael J. Brown',
    'nationality': 'British',
    'dob_long': '10 January 1980',
    'dob_display': '10 JAN 1980',
    'full_address': '8 Hampstead Heath, London, NW3 6TX, United Kingdom',
    'address_line1': '8 Hampstead Heath',
    'address_city': 'London',
    'address_postcode': 'NW3 6TX',
    'ownership': '30%',
    'position': 'Partner & Director',
    'role_desc': 'Ultimate Beneficial Owner (UBO) and Director',
    'years_industry': '22 years (2004-present)',
    'primary_source_title': 'Investment Management Income',
    'primary_source_desc': (
        'My primary source of wealth derives from my career in investment management '
        'and private equity. Since 2004, I have worked in progressively senior roles '
        'within the asset management sector, culminating in my current position as '
        'Partner at Granite Capital Partners LLP since 2015.'
    ),
    'income_components': [
        'Annual salary and bonuses from Granite Capital Partners LLP',
        'Partnership profit distributions (30% ownership stake)',
        'Management and performance fees from fund operations',
    ],
    'annual_income': '\u00a3250,000 - \u00a3500,000 (subject to fund performance)',
    'secondary_source_desc': (
        'Over the past 22 years, I have built a personal investment portfolio consisting of '
        'public equities and bonds, co-investments in private equity transactions, and '
        'residential property in London.'
    ),
    'employment': [
        ('2015 - Present:', 'Partner & Director, Granite Capital Partners LLP'),
        ('2010 - 2015:', 'Senior Vice President, Goldman Sachs Asset Management'),
        ('2007 - 2010:', 'Vice President, Barclays Capital'),
        ('2004 - 2007:', 'Associate, Morgan Stanley Investment Management'),
    ],
    'signature': 'M. J. Brown',
    'sow_filename': 'source-of-wealth-michael-brown.pdf',
    # Passport
    'surname': 'BROWN',
    'given_names': 'MICHAEL JAMES',
    'sex': 'M',
    'pob': 'EDINBURGH',
    'passport_no': '723948651',
    'issue_date': '12 MAR 2021',
    'expiry_date': '12 MAR 2031',
    'mrz_line1': 'P<GBRBROWN<<MICHAEL<JAMES<<<<<<<<<<<<<<<<<<',
    'mrz_line2': '7239486515GBR8001101M3103126<<<<<<<<<<<<<<08',
    'passport_filename': 'passport-michael-brown-certified.pdf',
    # Address proof
    'address_filename': 'address-proof-michael-brown-certified.pdf',
    'account_no': '850 437 8912',
    'gas_kwh': '510',
    'gas_cost': '\u00a361.20',
    'elec_kwh': '298',
    'elec_cost': '\u00a392.38',
    'gas_standing': '\u00a38.06',
    'elec_standing': '\u00a315.50',
    'vat': '\u00a38.86',
    'total': '\u00a3186.00',
}

JOHN_SMITH = {
    'full_name': 'John Edward Smith',
    'short_name': 'John E. Smith',
    'nationality': 'British',
    'dob_long': '15 May 1972',
    'full_address': '45 Kensington Gardens, London, W8 4QS, United Kingdom',
    'ownership': '35%',
    'position': 'Managing Partner & Director',
    'role_desc': 'Ultimate Beneficial Owner (UBO) and Director',
    'years_industry': '28 years (1998-present)',
    'primary_source_title': 'Investment Management Income',
    'primary_source_desc': (
        'My primary source of wealth derives from a career spanning 28 years in investment '
        'management and private equity. I co-founded Granite Capital Partners LLP in 2015 '
        'and have served as Managing Partner since inception. Prior to this, I held senior '
        'positions at leading financial institutions in the City of London.'
    ),
    'income_components': [
        'Annual salary and profit share from Granite Capital Partners LLP',
        'Partnership profit distributions (35% ownership stake)',
        'Carried interest from fund performance',
        'Management fees from fund operations',
    ],
    'annual_income': '\u00a3400,000 - \u00a3750,000 (subject to fund performance)',
    'secondary_source_desc': (
        'Over my 28-year career, I have accumulated a personal investment portfolio including '
        'public market investments, co-investments alongside fund positions, residential '
        'property in London (Kensington), and inheritance from family estate.'
    ),
    'employment': [
        ('2015 - Present:', 'Managing Partner & Director, Granite Capital Partners LLP'),
        ('2008 - 2015:', 'Managing Director, J.P. Morgan Asset Management'),
        ('2003 - 2008:', 'Director, Schroders Investment Management'),
        ('1998 - 2003:', 'Vice President, Deutsche Bank Asset Management'),
    ],
    'signature': 'J. E. Smith',
    'sow_filename': 'source-of-wealth-john-smith.pdf',
}

SARAH_JOHNSON = {
    'full_name': 'Sarah Anne Johnson',
    'short_name': 'Sarah A. Johnson',
    'nationality': 'British',
    'dob_long': '22 September 1978',
    'full_address': '12 Chelsea Embankment, London, SW3 4LF, United Kingdom',
    'ownership': '35%',
    'position': 'Partner & Director',
    'role_desc': 'Ultimate Beneficial Owner (UBO) and Director',
    'years_industry': '24 years (2002-present)',
    'primary_source_title': 'Investment Management Income',
    'primary_source_desc': (
        'My primary source of wealth derives from a 24-year career in investment management '
        'and private equity. I co-founded Granite Capital Partners LLP in 2015 and serve '
        'as Partner and Director. I specialise in fund structuring and investor relations, '
        'having previously held senior roles at prominent asset management firms.'
    ),
    'income_components': [
        'Annual salary and profit share from Granite Capital Partners LLP',
        'Partnership profit distributions (35% ownership stake)',
        'Carried interest from fund performance',
        'Advisory fees from fund structuring mandates',
    ],
    'annual_income': '\u00a3350,000 - \u00a3650,000 (subject to fund performance)',
    'secondary_source_desc': (
        'Over my 24-year career, I have built a personal investment portfolio including '
        'public equities, fixed income securities, co-investments in private equity, '
        'and residential property in Chelsea, London.'
    ),
    'employment': [
        ('2015 - Present:', 'Partner & Director, Granite Capital Partners LLP'),
        ('2009 - 2015:', 'Director, BlackRock Investment Management'),
        ('2005 - 2009:', 'Senior Associate, Bridgepoint Capital'),
        ('2002 - 2005:', 'Analyst, Fidelity International'),
    ],
    'signature': 'S. A. Johnson',
    'sow_filename': 'source-of-wealth-sarah-johnson.pdf',
}


# ─── MAIN ────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("Generating sample KYC PDF documents...\n")

    # Michael Brown - all 3 (replacing placeholders)
    print("Michael James Brown:")
    generate_passport(MICHAEL_BROWN)
    generate_address_proof(MICHAEL_BROWN)
    generate_source_of_wealth(MICHAEL_BROWN)

    # John Smith - source of wealth (missing)
    print("\nJohn Edward Smith:")
    generate_source_of_wealth(JOHN_SMITH)

    # Sarah Johnson - source of wealth (missing)
    print("\nSarah Anne Johnson:")
    generate_source_of_wealth(SARAH_JOHNSON)

    # Sponsor entity documents
    print("\nSponsor Entity:")
    generate_proof_of_registered_office()
    generate_regulatory_license()

    print("\nDone! 7 PDFs generated.")
