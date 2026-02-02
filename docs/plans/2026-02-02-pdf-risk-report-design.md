# PDF Risk Report - Design Document

**Project:** Client Onboarding - PDF Report Generation
**Date:** 2026-02-02
**Status:** Approved

---

## Overview

Generate downloadable PDF compliance reports with risk assessment, screening results, and audit trail for MLRO/Board review. Reports saved to Google Drive audit folder and available for direct download.

---

## Report Types

| Report | Audience | Content |
|--------|----------|---------|
| **Compliance Report** | MLRO/Analyst | Full detail: all screening results, risk factor breakdown, individual match details, recommendation, signature block for sign-off |
| **Board Summary** | Board/Committee | Executive summary: client name, risk rating, key flags (PEP/sanctions/jurisdiction), EDD requirement, approval recommendation - fits on 1 page |
| **Audit Pack** | External Auditor | Complete record: everything in Compliance Report + full audit trail timestamps, data sources, methodology notes, regulatory references (JFSC/FATF) |

**Common elements across all:**
- Header with company logo placeholder, report ID, generation timestamp
- Client identification (name, entity type, jurisdiction)
- Risk score with visual indicator (color-coded: green/amber/red)
- Footer with page numbers, confidentiality notice

---

## Architecture

**Library:** ReportLab (pure Python, no external dependencies)

**New service:** `services/pdf_report.py`

```
┌─────────────────────────────────────────────────────────────────┐
│  API Request: GET /api/report/generate/<onboarding_id>          │
│  Query params: ?type=compliance|board|audit                     │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  pdf_report.py                                                  │
│  ├─ generate_report(onboarding_id, report_type) -> bytes        │
│  ├─ _build_compliance_report(data) -> ReportLab canvas          │
│  ├─ _build_board_report(data) -> ReportLab canvas               │
│  ├─ _build_audit_report(data) -> ReportLab canvas               │
│  └─ _gather_report_data(onboarding_id) -> dict                  │
│       └─ Pulls from: SheetsDB (onboarding, screening, risk)     │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  Two outputs:                                                   │
│  1. gdrive_audit.upload_file() → Save to client's audit folder  │
│  2. Return PDF bytes → Stream to browser for download           │
└─────────────────────────────────────────────────────────────────┘
```

**Data gathered for report:**
- Onboarding record (client name, entity type, jurisdiction, phase)
- All persons/roles associated with onboarding
- Screening results (PEP, sanctions, adverse media hits)
- Risk assessment (score, rating, all factors, EDD flag)
- Audit log entries (for audit pack only)

---

## API Endpoint

```
GET /api/report/generate/<onboarding_id>
Query params:
  - type: compliance | board | audit (default: compliance)
  - save_to_drive: true | false (default: true)

Response:
  - Content-Type: application/pdf
  - Content-Disposition: attachment; filename="RSK-001-compliance-2026-02-02.pdf"
  - Headers include X-Drive-File-Id if saved to GDrive
```

---

## Frontend Integration

Update `phase4.html` to add report generation buttons after risk assessment display:

```
┌─────────────────────────────────────────────────────────────────┐
│  Risk Assessment                                    Score: 55   │
│  ├─ [existing factor breakdown]                                 │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Generate Reports                                        │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐     │   │
│  │  │ 📄 Compliance │ │ 📋 Board     │ │ 📁 Audit Pack │     │   │
│  │  │   Report     │ │   Summary    │ │              │     │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘     │   │
│  │  [Downloads PDF + saves to Google Drive]                 │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

**Button behavior:**
- Click → Show spinner → Generate PDF → Auto-download → Toast notification "Saved to Google Drive"
- Demo mode: Generates PDF but skips GDrive upload, shows "Demo mode - not saved to Drive"

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `services/pdf_report.py` | Create - ReportLab PDF generation service |
| `services/__init__.py` | Modify - export pdf_report |
| `app.py` | Modify - add `/api/report/generate/<id>` endpoint |
| `templates/onboarding/phase4.html` | Modify - add report generation buttons |
| `requirements.txt` | Modify - add `reportlab` |

---

## Report Naming Convention

```
{onboarding_id}-{report_type}-{date}.pdf
Examples:
  ONB-001-compliance-2026-02-02.pdf
  ONB-001-board-2026-02-02.pdf
  ONB-001-audit-2026-02-02.pdf
```

---

## Demo Mode Behavior

- PDF generation works fully (no external dependencies)
- GDrive upload skipped, logged to console
- Report data pulled from mock data if SheetsDB not configured

---

*End of Design Document*
