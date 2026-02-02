# Email Notifications - Design Document

**Project:** Client Onboarding - Email Notifications
**Date:** 2026-02-02
**Status:** Approved

---

## Overview

Implement SMTP-based email notifications for key workflow events in the client onboarding process.

---

## Notification Events

| Event | Trigger | Recipients |
|-------|---------|------------|
| **EDD Triggered** | Risk score ≥ 40 or prohibited jurisdiction | MLRO, assigned analyst |
| **Approval Required** | Screening complete, needs MLRO or Board sign-off | MLRO (medium risk), MLRO + Board (high risk) |
| **Screening Complete** | `/api/screening/run` finishes | Assigned analyst |
| **Phase Completed** | User advances to next phase | Assigned analyst, supervisor |
| **Onboarding Approved** | Final approval given | Sponsor contact, analyst, compliance |
| **Onboarding Rejected** | Onboarding declined | Analyst, compliance |

---

## Configuration

Environment variables:

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=notifications@yourcompany.com
SMTP_PASSWORD=app-password
SMTP_FROM=Client Onboarding <notifications@yourcompany.com>
NOTIFICATION_MLRO_EMAIL=mlro@yourcompany.com
NOTIFICATION_BOARD_EMAIL=board@yourcompany.com
```

---

## Architecture

**New service:** `services/email_notify.py`

```
┌─────────────────────────────────────────────────────────────────┐
│  Event Trigger (e.g., screening complete)                       │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  email_notify.py                                                │
│  ├─ send_notification(event_type, data, recipients)            │
│  ├─ _get_template(event_type) -> HTML template                 │
│  ├─ _send_smtp(to, subject, html_body)                         │
│  └─ notify_* convenience functions:                            │
│       ├─ notify_edd_triggered(onboarding, risk_assessment)     │
│       ├─ notify_approval_required(onboarding, approval_level)  │
│       ├─ notify_screening_complete(onboarding, results)        │
│       ├─ notify_phase_completed(onboarding, phase)             │
│       └─ notify_onboarding_decision(onboarding, approved)      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Demo Mode

When SMTP not configured:
- Logs email content to console
- Stores "sent" emails in memory for testing
- Returns success without actually sending

---

## Integration Points

| Location | Event | Code Change |
|----------|-------|-------------|
| `/api/screening/run` | Screening complete | After risk calculation, call `notify_screening_complete()` |
| `/api/screening/run` | EDD triggered | If `risk_assessment['edd_required']`, call `notify_edd_triggered()` |
| `/api/screening/run` | Approval required | If approval_level != 'compliance', call `notify_approval_required()` |
| `onboarding_phase()` POST | Phase completed | After phase saved, call `notify_phase_completed()` |
| `onboarding_approve()` (new) | Approved/Rejected | New endpoint for final decision, calls `notify_onboarding_decision()` |

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `services/email_notify.py` | Create - SMTP email service with templates |
| `services/__init__.py` | Modify - export email_notify functions |
| `app.py` | Modify - add notification calls at trigger points |
| `.env.example` | Modify - add SMTP configuration variables |

---

## Email Template Style

- Plain HTML with inline CSS (maximum email client compatibility)
- Company header with logo placeholder
- Clear action buttons linking to the app
- Footer with confidentiality notice

Example:

```
Subject: [Client Onboarding] EDD Required - {sponsor_name}
─────────────────────────────────────────────────
Risk Alert: Enhanced Due Diligence Required

Client: {sponsor_name} / {fund_name}
Risk Score: {score} ({rating})
Approval Level: {approval_level}

Triggered by:
• {trigger_reasons}

Action Required: Review in Client Onboarding System
─────────────────────────────────────────────────
```

---

*End of Design Document*
