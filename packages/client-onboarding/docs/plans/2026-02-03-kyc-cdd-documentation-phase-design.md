# KYC & CDD Documentation Phase Design

## Overview

Transform Phase 4 from "EDD" to a comprehensive **KYC & CDD Documentation** phase with AI-powered document review, JFSC compliance checking, and bulk upload capability.

**Goal:** Collect and validate all sponsor and key party documentation with AI assistance before MLRO sign-off.

**Key Principle:** Investor KYC is out of scope - collected separately during subscription. Fund cannot accept investors until their KYC is approved.

---

## Dynamic Checklist Generation

The system generates a tailored document checklist based on Phase 1 enquiry data.

### Inputs from Enquiry

| Field | Impact on Checklist |
|-------|---------------------|
| Entity Type | Determines constitutional documents (LLP Agreement vs Articles, etc.) |
| Jurisdiction | Country-specific requirements |
| Regulatory Status | If regulated: license + compliance certificates required |
| Key Parties List | One document set per director/UBO |

### Sponsor Entity Documents (Standard Corporate CDD)

| Entity Type | Required Documents |
|-------------|-------------------|
| **LLP** | Certificate of Registration, LLP Agreement, Register of Members, Structure Chart, Proof of Registered Office |
| **Limited Company** | Certificate of Incorporation, M&A/Articles, Register of Directors, Register of Shareholders, Structure Chart, Proof of Registered Office |
| **Trust** | Trust Deed, Certificate of Registration (if applicable), Schedule of Trustees, Schedule of Beneficiaries, Structure Chart |
| **Partnership** | Partnership Agreement, Register of Partners, Structure Chart, Proof of Address |

### Key Party Documents (Per Director/UBO)

| Document | Requirement |
|----------|-------------|
| Certified Passport Copy | Valid, unexpired, JFSC-compliant certification |
| Proof of Address | Utility bill or bank statement dated within 3 months, certified |

---

## Bulk Upload with AI Assignment

### Upload Flow

1. BD drags and drops all documents into single upload zone
2. System accepts PDF, JPG, PNG (max 20MB each)
3. AI processes all documents in parallel

### AI Processing Steps

1. **Document Type Detection** - Identify passport, utility bill, certificate, etc.
2. **Entity vs Personal Classification** - Corporate document or individual ID?
3. **Name Extraction** - Read name from passports/IDs using OCR
4. **Auto-Assignment** - Match to correct key party or sponsor checklist slot
5. **Certification Review** - Run all JFSC compliance checks
6. **Confidence Scoring** - Flag low-confidence matches for human review

### Post-Upload Display

Documents grouped by assignment:
- Sponsor Entity Documents (with AI match confidence)
- Key Party sections (one per person, with matched documents)
- Unassigned Documents (if AI couldn't match)

BD can manually reassign documents if AI got it wrong.

---

## AI Document Review Checks

### JFSC Compliance Checks

| Check | Description | Pass Criteria |
|-------|-------------|---------------|
| **Document Type Match** | Correct document for the slot | Passport in passport slot |
| **Certification Wording** | JFSC-acceptable certification text | Contains "I certify this is a true copy of the original" or equivalent |
| **Certifier Details** | All required elements present | Signature, printed name, qualification, date |
| **Certifier Qualification** | Acceptable certifier type | Lawyer, Notary Public, or Chartered Accountant |
| **Certification Date** | Not stale | Within 3 months for address proof; within 12 months for ID certification |
| **Document Expiry** | ID not expired | Valid for at least 3 months from submission |
| **Name Matching** | Name matches enquiry data | Passport name matches key party record (fuzzy match for middle names, etc.) |
| **Image Quality** | Legible and complete | All corners visible, text readable, not blurry |

### Review Result Format

```
Document: Passport - John Smith
Overall: PASS (6/6 checks passed)

✅ Document Type: Passport detected - PASS
✅ Certification Wording: "I certify this is a true copy..." - PASS
✅ Certifier: J. Roberts, Solicitor, 15 Jan 2026 - PASS
✅ Certification Date: 15 Jan 2026 (within 3 months) - PASS
✅ Document Expiry: Valid until Jun 2030 - PASS
✅ Name Match: "John David Smith" matches "John Smith" - PASS
✅ Image Quality: Clear and legible - PASS
```

### Override Capability

BD can override warnings with justification:
- Click "Override" on flagged item
- Enter reason (e.g., "Middle initial not captured in system - passport is correct")
- Override logged with timestamp and user

---

## EDD Subsection

### Trigger Conditions

EDD section appears within Phase 4 when any of:

| Condition | Source |
|-----------|--------|
| Risk rating = High | Phase 3 risk assessment |
| PEP identified | Phase 3 PEP screening |
| High-risk jurisdiction | Sponsor or key party from FATF grey/black list |
| Sanctions near-match | Phase 3 sanctions screening flag |

### Additional EDD Documents

| Document | Purpose |
|----------|---------|
| Source of Wealth Declaration | Signed statement explaining how wealth was accumulated |
| Source of Funds Evidence | Bank statements, sale contracts, inheritance docs |
| Professional Reference Letter | From lawyer, accountant, or banker confirming identity and standing |

---

## Data Model

### Document Record

```python
{
    'document_id': 'DOC-001',
    'onboarding_id': 'ONB-001',
    'document_type': 'passport',
    'checklist_item': 'key_party_passport',
    'assigned_to': 'PER-001',              # Person ID or 'SPONSOR'
    'assigned_to_name': 'John Smith',
    'file_path': '/audit/ONB-001/kyc/...',
    'file_size': 245000,
    'mime_type': 'application/pdf',
    'uploaded_at': '2026-02-03T14:30:00Z',
    'uploaded_by': 'bd_user',

    'ai_review': {
        'overall_status': 'pass',          # pass, review_needed, fail
        'confidence': 0.96,
        'processed_at': '2026-02-03T14:30:05Z',
        'checks': {
            'document_type_match': {'status': 'pass', 'detail': 'Passport detected'},
            'certification_wording': {'status': 'pass', 'detail': 'Valid certification found'},
            'certifier_details': {'status': 'pass', 'detail': 'J. Roberts, Solicitor, 15 Jan 2026'},
            'certification_date': {'status': 'pass', 'detail': 'Within 3 months'},
            'document_expiry': {'status': 'pass', 'detail': 'Valid until 2030'},
            'name_match': {'status': 'pass', 'detail': 'John David Smith matches John Smith'},
            'image_quality': {'status': 'pass', 'detail': 'Clear and legible'}
        },
        'extracted_data': {
            'detected_type': 'passport',
            'name': 'John David Smith',
            'dob': '1975-03-15',
            'document_number': 'AB123456',
            'expiry': '2030-06-20',
            'nationality': 'British',
            'certifier_name': 'J. Roberts',
            'certifier_qualification': 'Solicitor',
            'certification_date': '2026-01-15'
        }
    },

    'override': {
        'applied': False,
        'reason': None,
        'by': None,
        'at': None
    }
}
```

### KYC Checklist Record

```python
{
    'onboarding_id': 'ONB-001',
    'generated_at': '2026-02-03T10:00:00Z',
    'sponsor_documents': [
        {'item': 'certificate_of_registration', 'label': 'Certificate of Registration', 'required': True, 'document_id': 'DOC-001', 'status': 'complete'},
        {'item': 'llp_agreement', 'label': 'LLP Agreement', 'required': True, 'document_id': None, 'status': 'pending'},
        # ...
    ],
    'key_parties': [
        {
            'person_id': 'PER-001',
            'name': 'John Smith',
            'role': 'Director & UBO',
            'documents': [
                {'item': 'passport', 'label': 'Certified Passport', 'required': True, 'document_id': 'DOC-005', 'status': 'complete'},
                {'item': 'address_proof', 'label': 'Proof of Address', 'required': True, 'document_id': 'DOC-006', 'status': 'complete'}
            ]
        },
        # ...
    ],
    'edd_required': False,
    'edd_trigger_reason': None,
    'edd_documents': [],
    'overall_status': 'in_progress',       # pending, in_progress, review_needed, complete
    'signed_off_by': None,
    'signed_off_at': None
}
```

---

## Workflow

```
Phase 1 (Enquiry)
       │
       ▼
Phase 3 (Screening) ──────────────────┐
       │                              │
       ▼                              │ Risk result
Phase 4 (KYC/CDD)                     │
       │                              │
       ├── Generate Checklist ◄───────┘
       │
       ├── BD Uploads All Documents
       │
       ├── AI Processes & Assigns
       │         │
       │         ├── Document Type Detection
       │         ├── Name Extraction (OCR)
       │         ├── Auto-Assignment
       │         └── JFSC Compliance Checks
       │
       ├── BD Reviews Results
       │         │
       │         ├── All Pass → Ready
       │         └── Issues → Override with reason
       │
       ├── EDD Section (if triggered)
       │         │
       │         └── Additional docs required
       │
       └── BD Sign Off
              │
              ▼
       Phase 5 (MLRO Approval)
```

---

## UI Components

### Main Phase 4 Page

1. **Header** - Phase title, sponsor name, progress indicator
2. **Upload Zone** - Drag-drop area for bulk upload
3. **Processing Indicator** - Shows AI analysis progress
4. **Results View** - Grouped by sponsor/key parties with status icons
5. **Document Viewer** - Modal to view uploaded document with AI annotations
6. **EDD Section** - Conditional, appears if triggered
7. **Action Bar** - Upload More, Sign Off buttons

### Status Icons

- ⬜ Pending (no document)
- 🔄 Processing (AI analyzing)
- ✅ Pass (all checks passed)
- ⚠️ Review Needed (issues flagged)
- ✅ Overridden (warning acknowledged)
- ❌ Failed (critical issue)

---

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `app.py` | Modify | Update Phase 4 route, add upload/review APIs |
| `templates/onboarding/phase4.html` | Replace | New KYC/CDD documentation UI |
| `services/document_review.py` | Create | AI document analysis using Claude API |
| `services/kyc_checklist.py` | Create | Dynamic checklist generation |
| `static/js/kyc-upload.js` | Create | Bulk upload, drag-drop, progress UI |
| `static/css/kyc.css` | Create | Styling for document cards, status indicators |

---

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/kyc/<onboarding_id>/checklist` | GET | Get generated checklist |
| `/api/kyc/<onboarding_id>/upload` | POST | Upload documents (multipart) |
| `/api/kyc/<onboarding_id>/document/<doc_id>` | GET | Get document details + AI review |
| `/api/kyc/<onboarding_id>/document/<doc_id>/reassign` | POST | Reassign document to different slot |
| `/api/kyc/<onboarding_id>/document/<doc_id>/override` | POST | Override warning with reason |
| `/api/kyc/<onboarding_id>/signoff` | POST | BD sign-off |

---

## Success Criteria

1. BD can upload all documents in single action
2. AI correctly identifies and assigns 90%+ of documents
3. AI certification checks match JFSC requirements
4. BD can override warnings with audit trail
5. Phase blocks progression until all required docs complete
6. EDD section appears automatically when risk triggers met
7. Clear visibility of what's missing/needs attention
