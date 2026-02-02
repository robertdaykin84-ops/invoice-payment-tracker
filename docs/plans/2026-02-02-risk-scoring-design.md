# Risk Scoring Algorithm - Design Document

**Project:** Client Onboarding - Risk Assessment
**Date:** 2026-02-02
**Status:** Approved

---

## Overview

Implement a weighted risk scoring algorithm for client onboarding that calculates risk from multiple factors per JFSC AML/CFT guidelines.

## Approach

**Weighted formula** - Each factor has a weight, scores sum to 0-100. Transparent and auditable.

---

## Risk Factors & Weights

| Factor | Weight | Scoring Logic |
|--------|--------|---------------|
| **Jurisdiction** | 25% | Based on JFSC Appendix D1/D2 and FATF lists |
| **PEP Status** | 25% | None=0, RCA=40, Domestic=60, Foreign=80 |
| **Sanctions Hits** | 30% | Clear=0, Potential=50, Confirmed=100 |
| **Adverse Media** | 10% | None=0, Resolved=30, Active=70 |
| **Entity Structure** | 10% | Company=0, LP=20, Trust=40, Foundation=60 |

---

## Jurisdiction Risk Tiers (JFSC/FATF)

| Tier | Score | Jurisdictions |
|------|-------|---------------|
| **Prohibited** | 100 | DPRK (KP), Iran (IR), Myanmar (MM) - FATF Black List |
| **High Risk** | 80 | FATF Grey List: Algeria (DZ), Angola (AO), Bolivia (BO), Bulgaria (BG), Cameroon (CM), Côte d'Ivoire (CI), DRC (CD), Haiti (HT), Kenya (KE), Lao PDR (LA), Lebanon (LB), Monaco (MC), Namibia (NA), Nepal (NP), South Sudan (SS), Syria (SY), Venezuela (VE), Vietnam (VN), BVI (VG), Yemen (YE) |
| **Elevated** | 50 | Offshore not in Grey List: Cayman (KY), Bermuda (BM), Guernsey (GG), Isle of Man (IM), Luxembourg (LU), etc. |
| **Standard** | 20 | Most jurisdictions: EU, US (US), Canada (CA), Australia (AU), etc. |
| **Low** | 0 | UK (GB), Jersey (JE), Ireland (IE) - established relationships |

Lists are configurable and should be updated when FATF publishes new lists (3x/year).

Sources:
- JFSC Appendix D2: https://www.jerseyfsc.org/industry/financial-crime/amlcftcpf-handbooks/appendix-d2-countries-and-territories-identified-as-presenting-higher-risks/
- FATF High-Risk Jurisdictions: https://www.fatf-gafi.org/en/publications/High-risk-and-other-monitored-jurisdictions/Call-for-action-october-2025.html

---

## Thresholds

| Score Range | Rating | EDD Required | Approval Level |
|-------------|--------|--------------|----------------|
| 0-39 | Low | No | Compliance Analyst |
| 40-69 | Medium | Yes | MLRO |
| 70-100 | High | Yes | MLRO + Board |

---

## Architecture

**File:** `services/risk_scoring.py`

```python
# Constants
JURISDICTION_TIERS = {
    'prohibited': ['KP', 'IR', 'MM'],
    'high': ['DZ', 'AO', 'BO', 'BG', 'CM', 'CI', 'CD', 'HT', 'KE', 'LA', 'LB', 'MC', 'NA', 'NP', 'SS', 'SY', 'VE', 'VN', 'VG', 'YE'],
    'elevated': ['KY', 'BM', 'GG', 'IM', 'LU', 'PA', 'SC', 'MU'],
    'standard': [],  # Default for unlisted
    'low': ['GB', 'JE', 'IE', 'GG']
}

WEIGHTS = {
    'jurisdiction': 0.25,
    'pep_status': 0.25,
    'sanctions': 0.30,
    'adverse_media': 0.10,
    'entity_structure': 0.10
}

# Functions
calculate_risk(screening_results, entity_data) -> dict
get_jurisdiction_score(country_code) -> dict
get_pep_score(pep_status) -> dict
get_sanctions_score(screening_results) -> dict
get_adverse_media_score(screening_results) -> dict
get_structure_score(entity_type) -> dict
```

---

## API Response

Integrated into `/api/screening/run` response:

```json
{
  "status": "ok",
  "demo_mode": true,
  "results": [...],
  "screened_count": 4,
  "risk_assessment": {
    "score": 55,
    "rating": "medium",
    "factors": {
      "jurisdiction": {
        "score": 20,
        "weight": 25,
        "contribution": 5,
        "reason": "UK - Standard risk"
      },
      "pep_status": {
        "score": 60,
        "weight": 25,
        "contribution": 15,
        "reason": "Domestic PEP: Boris Johnson match"
      },
      "sanctions": {
        "score": 0,
        "weight": 30,
        "contribution": 0,
        "reason": "No sanctions matches"
      },
      "adverse_media": {
        "score": 30,
        "weight": 10,
        "contribution": 3,
        "reason": "Historical resolved: 1 entity"
      },
      "entity_structure": {
        "score": 20,
        "weight": 10,
        "contribution": 2,
        "reason": "LP structure"
      }
    },
    "edd_required": true,
    "approval_level": "mlro",
    "assessment_id": "RSK-001"
  },
  "audit_trail": {...}
}
```

---

## Frontend Integration

Update `phase4.html` to:

1. Read risk from API response (remove client-side calculation)
2. Display factor breakdown with visual bars
3. Show EDD trigger and approval level

```
┌─────────────────────────────────────────────────────────────┐
│  Risk Assessment                                             │
├─────────────────────────────────────────────────────────────┤
│  Overall: 55 MEDIUM    │    Approval: MLRO                  │
│                                                              │
│  Factor Breakdown:                                           │
│  ├─ Jurisdiction (25%)    ████░░░░░░  20 → 5pts   UK        │
│  ├─ PEP Status (25%)      ██████░░░░  60 → 15pts  Domestic  │
│  ├─ Sanctions (30%)       ░░░░░░░░░░   0 → 0pts   Clear     │
│  ├─ Adverse Media (10%)   ███░░░░░░░  30 → 3pts   Resolved  │
│  └─ Entity Structure (10%) ██░░░░░░░░  20 → 2pts   LP        │
│                                                              │
│  ⚠️ EDD Required                                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `services/risk_scoring.py` | Create - risk calculation service |
| `services/__init__.py` | Modify - export risk_scoring |
| `app.py` | Modify - integrate into /api/screening/run |
| `templates/onboarding/phase4.html` | Modify - display risk breakdown |

---

## Data Persistence

Risk assessments saved to SheetsDB `RiskAssessments` tab via `sheets_db.save_risk_assessment()`:

| Field | Value |
|-------|-------|
| assessment_id | RSK-001 |
| onboarding_id | ONB-001 |
| risk_score | 55 |
| risk_rating | medium |
| risk_factors | JSON of factor breakdown |
| edd_triggered | true |
| assessed_at | timestamp |

---

*End of Design Document*
