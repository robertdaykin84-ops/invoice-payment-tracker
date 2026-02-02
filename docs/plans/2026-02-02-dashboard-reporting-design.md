# Dashboard & Reporting Enhancement - Design Document

**Project:** Client Onboarding - Dashboard & Reporting
**Date:** 2026-02-02
**Status:** Approved

---

## Overview

Enhance the existing dashboard with visual charts and add a dedicated reporting page with pipeline analytics, risk distribution, and exportable reports.

---

## New Features

### 1. Dashboard Charts (Phase 1)
Add visual charts to the existing dashboard:
- **Pipeline Funnel Chart**: Onboardings by phase (1-8)
- **Risk Distribution Pie**: Count by risk rating (low/medium/high)
- **Monthly Trend Line**: Approvals over time

### 2. Reporting Page (Phase 2)
New `/reports` page with:
- Summary statistics cards
- Interactive filters (date range, status, risk)
- Data tables with export to CSV
- Download all data button

---

## Architecture

**Library:** Chart.js (CDN, no build step needed)

**New Files:**
- `templates/reports.html` - Reporting page template
- `static/js/charts.js` - Chart initialization scripts

**Modified Files:**
- `app.py` - Add `/reports` endpoint, add `/api/reports/data` endpoint
- `templates/dashboard.html` - Add chart containers
- `templates/base.html` - Add Chart.js CDN link

---

## API Endpoints

```
GET /reports
  - Returns reports.html with initial data

GET /api/reports/data
  Query params:
    - date_from: YYYY-MM-DD (optional)
    - date_to: YYYY-MM-DD (optional)
    - status: filter by status (optional)
    - risk_level: filter by risk (optional)
    - format: json|csv (default: json)

  Response (JSON):
    {
      "summary": {
        "total": 15,
        "in_progress": 8,
        "pending_approval": 3,
        "approved": 4,
        "avg_days_to_complete": 12.5
      },
      "by_phase": [
        {"phase": 1, "name": "Enquiry", "count": 2},
        {"phase": 2, "name": "Sponsor", "count": 3},
        ...
      ],
      "by_risk": [
        {"rating": "low", "count": 8},
        {"rating": "medium", "count": 5},
        {"rating": "high", "count": 2}
      ],
      "by_month": [
        {"month": "2026-01", "approved": 5, "rejected": 1},
        {"month": "2026-02", "approved": 3, "rejected": 0}
      ],
      "onboardings": [/* filtered list */]
    }

  Response (CSV):
    Returns downloadable CSV file
```

---

## Implementation Tasks

1. Add Chart.js CDN to base.html
2. Create /api/reports/data endpoint with aggregation logic
3. Add charts to dashboard.html
4. Create reports.html template
5. Add /reports route to app.py
6. Add CSV export functionality
7. Test and verify

---

*End of Design Document*
