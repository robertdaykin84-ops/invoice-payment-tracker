# Client Onboarding System - Design Document

**Project:** New Client Setup / Client Onboarding
**Package:** `packages/client-onboarding/`
**Repository:** github.com/robertdaykin84-ops/invoice-payment-tracker (fund-admin-tools monorepo)
**Date:** 2026-02-02
**Status:** Draft - Pending Approval

---

## 1. Executive Summary

### Purpose
Proof of concept for automating the New Client Take-on (onboarding) process for a Jersey-based fund administration business, in compliance with JFSC (Jersey Financial Services Commission) requirements.

### Scope
- **Client Type Focus:** PE House Sponsors setting up Jersey Private Funds (JPFs)
- **Goal:** Demonstrate both workflow automation AND AI document processing capabilities
- **Approach:** Wizard-based linear flow with parallel Commercial track

### Key Features
- Multi-entity type support (Individual, Company, LP, Trust, Foundation)
- Sponsor + Fund Structure dual-level onboarding
- AI-powered document extraction, screening analysis, and document generation
- Role-based workflows (BD, Compliance, MLRO, Admin)
- JFSC compliance mapping with evidence trail
- Proactive reminder system

---

## 2. JFSC Regulatory Framework

### Primary Legislation
| Legislation | Purpose |
|-------------|---------|
| Proceeds of Crime (Jersey) Law 1999 | Primary ML offense legislation |
| Money Laundering (Jersey) Order 2008 (MLO) | Detailed CDD requirements |
| Sanctions and Asset-Freezing (Jersey) Law 2019 | Sanctions implementation |
| Proceeds of Crime (Supervisory Bodies) (Jersey) Law 2008 | JFSC supervisory powers |

### Key JFSC Sources
| Document | URL |
|----------|-----|
| AML/CFT/CPF Handbook | https://www.jerseyfsc.org/industry/financial-crime/amlcftcpf-handbooks/ |
| Fund Services Business Code of Practice | https://www.jerseyfsc.org/industry/codes-of-practice/fund-services-business-code-of-practice/ |
| JPF Guide | https://www.jerseyfsc.org/industry/guidance-and-policy/jersey-private-funds/ |
| Beneficial Ownership Guidance | https://www.jerseyfsc.org/industry/guidance-and-policy/beneficial-ownership-and-controller-guidance/ |
| Sanctions Guidance | https://www.jerseyfsc.org/industry/international-co-operation/sanctions/about-sanctions/ |

### Compliance Requirements Summary

#### CDD Requirements
- Identify and verify customer identity
- Identify beneficial owners (25%+ threshold, 10% on incorporation)
- Apply three-tier test for UBO identification
- Obtain Source of Wealth and Source of Funds
- Conduct CDD before establishing business relationship

#### Screening Requirements
- PEP screening on all principals and UBOs
- Sanctions screening (OFSI, OFAC, EU, UN)
- Adverse media screening
- Regulatory status verification (adaptive by jurisdiction)

#### Enhanced Due Diligence Triggers
- PEP connections
- High-risk jurisdictions (Russia, Belarus, FATF lists)
- Complex/opaque structures
- Adverse media findings
- High-risk assessment score

#### Approval Requirements
- MLRO approval for all clients
- Board approval for high-risk clients
- Senior management approval before EDD relationships

#### Record Keeping
- Retain CDD records minimum 5 years from end of relationship
- Maintain full audit trail
- Ongoing monitoring based on risk level

---

## 3. Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
│  Flask Templates + Role-Based Dashboards                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ BD View  │ │Compliance│ │  MLRO    │ │  Admin   │           │
│  │          │ │  View    │ │  View    │ │  View    │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                         BACKEND                                  │
│  Flask Application (app.py)                                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│  │ Workflow     │ │ Document     │ │ Screening    │            │
│  │ Engine       │ │ Processor    │ │ Service      │            │
│  └──────────────┘ └──────────────┘ └──────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                              │
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│  Claude API   │  │ Google Sheets │  │  Mock APIs    │
│  (AI Engine)  │  │  (Database)   │  │  (Screening)  │
└───────────────┘  └───────────────┘  └───────────────┘
                   │               │
                   └───────┬───────┘
                           │
                  ┌────────────────┐
                  │ Google Drive   │
                  │ (Doc Storage)  │
                  └────────────────┘
```

### Technology Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.11+, Flask 3.x |
| Frontend | Bootstrap 5, Jinja2 templates, CoreWorker AI branding |
| Database | Google Sheets API v4 |
| File Storage | Google Drive API v3 |
| AI | Claude API (Sonnet for speed, Opus for complex reasoning) |
| Auth | Flask sessions (POC), upgrade path to Google OAuth |
| Deployment | Render |

### Google Drive Folder Structure

```
Client-Onboarding/
├── {SponsorID}-{SponsorName}/
│   ├── 01-Intake/
│   ├── 02-Verification/
│   │   ├── Sponsor/
│   │   └── Principals/
│   ├── 03-Screening/
│   ├── 04-Approvals/
│   ├── 05-Commercial/
│   └── Funds/
│       └── {FundID}-{FundName}/
│           ├── Formation/
│           ├── Principals/
│           └── Screening/
```

---

## 4. Data Model

### Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         SPONSOR                                  │
│              (PE House / Fund Manager - THE CLIENT)             │
├─────────────────────────────────────────────────────────────────┤
│  Sponsor Principals (via PersonRoles):                          │
│  - Partners/Directors of the PE House                           │
│  - UBOs of the sponsor entity                                   │
│  - Promoter/Instigator (if applicable)                          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ Sets up / manages
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FUND STRUCTURE                             │
├─────────────────────────────────────────────────────────────────┤
│  Fund Principals (SEPARATE - may have crossover):               │
│  - GP Directors                                                 │
│  - Fund Directors/Officers                                      │
│  - Professional/Independent Directors                           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ Will have (over time)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ANTICIPATED INVESTORS                        │
│  (Optional at take-on - for planning only)                      │
└─────────────────────────────────────────────────────────────────┘
```

### Core Entities

#### ENTITY (Polymorphic)
Supports: Individual, Company, LLP, LP, Trust, Foundation, PCC, Other

| Field | Type | Description |
|-------|------|-------------|
| entity_id | PK | Unique identifier |
| entity_type | Enum | Individual/Company/LLP/LP/Trust/Foundation/PCC/Other |
| legal_name | String | Legal name |
| jurisdiction | String | Country/jurisdiction of formation |
| registration_number | String | Company/registration number |
| date_formed | Date | Formation/incorporation date |
| regulated_status | String | Regulated/Not Regulated/Pending |
| cdd_status | Enum | Pending/In Progress/Complete/Expired |
| parent_entity_id | FK | For ownership chains |
| reliance_applied | Boolean | Relying on third-party CDD? |
| reliance_details | JSON | Obliged person details if reliance |

#### PERSON
| Field | Type | Description |
|-------|------|-------------|
| person_id | PK | Unique identifier |
| full_name | String | Full legal name |
| former_names | String | Any previous names |
| nationality | String | Primary nationality |
| other_nationalities | String | Additional nationalities |
| dob | Date | Date of birth |
| country_of_residence | String | Current residence |
| pep_status | Enum | Not PEP/Domestic PEP/Foreign PEP/RCA |
| sow_description | Text | Source of wealth narrative |
| id_verified | Boolean | ID verification complete |
| address_verified | Boolean | Address verification complete |

#### PERSON_ROLES
| Field | Type | Description |
|-------|------|-------------|
| role_id | PK | Unique identifier |
| person_id | FK | Link to Person |
| entity_id | FK | Link to Entity (Sponsor/Fund/GP) |
| role_type | Enum | Director/Partner/UBO/Trustee/Settlor/Protector/Council/Promoter/etc. |
| ownership_pct | Decimal | Ownership percentage if applicable |
| is_ubo | Boolean | Is this person a UBO? |
| appointed_date | Date | Date appointed to role |
| cdd_required | Boolean | Is CDD required for this role? |

#### FUND_STRUCTURES
| Field | Type | Description |
|-------|------|-------------|
| fund_id | PK | Unique identifier |
| sponsor_id | FK | Link to Sponsor |
| fund_name | String | Fund name |
| legal_structure | Enum | LP/Unit Trust/ICC/PCC/Other |
| jurisdiction | String | Fund jurisdiction |
| fund_type | Enum | JPF/Expert Fund/Listed/Other |
| gp_entity_id | FK | Link to GP Entity |
| investment_strategy | Text | Strategy description |
| target_size | Decimal | Target fund size |
| target_jurisdictions | JSON | Target investment jurisdictions |
| accepts_cash | Boolean | Accepts physical currency? |
| promoter_id | FK | Link to Promoter (Person or Entity) if different from Sponsor |

#### SCREENINGS
| Field | Type | Description |
|-------|------|-------------|
| screening_id | PK | Unique identifier |
| person_id | FK | Link to Person |
| entity_id | FK | Link to Entity (if entity-level screening) |
| screening_type | Enum | PEP/Sanctions/Adverse Media |
| provider | String | World-Check/Mock/etc. |
| result | Enum | Clear/Match/Review Required |
| match_details | JSON | Match details if applicable |
| screened_at | Timestamp | When screened |
| screened_by | String | User who ran screening |
| next_screening_due | Date | Annual re-screening date |

#### RISK_ASSESSMENTS
| Field | Type | Description |
|-------|------|-------------|
| assessment_id | PK | Unique identifier |
| sponsor_id | FK | Link to Sponsor |
| fund_id | FK | Link to Fund (if fund-level) |
| assessment_level | Enum | Sponsor/Fund/Overall |
| risk_factors | JSON | Risk factors identified |
| risk_score | Integer | Score 0-100 |
| risk_rating | Enum | Low/Medium/High |
| edd_triggered | Boolean | Does this trigger EDD? |
| ai_reasoning | Text | AI explanation |
| assessed_at | Timestamp | Assessment date |
| assessed_by | String | User/AI |

#### APPROVALS
| Field | Type | Description |
|-------|------|-------------|
| approval_id | PK | Unique identifier |
| sponsor_id | FK | Link to Sponsor |
| approval_type | Enum | Compliance/MLRO/Board |
| status | Enum | Pending/Approved/Rejected |
| approver | String | Approving user |
| comments | Text | Approval comments |
| decided_at | Timestamp | Decision timestamp |

#### DOCUMENTS
| Field | Type | Description |
|-------|------|-------------|
| document_id | PK | Unique identifier |
| entity_id | FK | Link to Entity |
| person_id | FK | Link to Person (if personal doc) |
| doc_type | String | Document type (from checklist) |
| doc_name | String | File name |
| gdrive_file_id | String | Google Drive file ID |
| gdrive_url | String | Google Drive URL |
| uploaded_at | Timestamp | Upload timestamp |
| uploaded_by | String | Uploading user |
| verified | Boolean | Verified by compliance? |
| verified_by | String | Verifying user |
| expiry_date | Date | Document expiry (passports, certs) |

---

## 5. Entity Type Framework

### Supported Entity Types & CDD Requirements

| Entity Type | Identification Docs | Ownership/Control Docs | Look-Through Required |
|-------------|--------------------|-----------------------|----------------------|
| Individual | Passport/ID, Proof of Address | N/A | No |
| Private Company (Ltd) | Certificate of Incorporation, M&A | Register of Directors, Register of Shareholders | Yes - to 25%+ shareholders |
| LLP | Registration Certificate, LLP Agreement | Register of Members, Designated Members | Yes - to 25%+ members |
| Limited Partnership | Partnership Agreement, Certificate | GP details, LP Register | Yes - GP fully, LPs at 25%+ |
| Trust | Trust Deed | Trustees, Settlor, Protector, Beneficiaries | Yes - all controllers + vested beneficiaries |
| Foundation | Foundation Charter/Regulations | Council Members, Founder, Guardian, Beneficiaries | Yes - all controllers |

### Document Checklist by Entity Type

#### Individual
- [ ] Certified passport (photo page)
- [ ] Proof of address (<3 months)
- [ ] Source of wealth declaration
- [ ] CV/biography (if principal)

#### Private Company (Ltd/Inc)
- [ ] Certificate of Incorporation
- [ ] Memorandum & Articles of Association
- [ ] Register of Directors (current)
- [ ] Register of Shareholders (current)
- [ ] Certificate of Good Standing (if >12 months old)
- [ ] Structure chart
- [ ] Latest audited accounts (if available)
- [ ] Regulated status confirmation (if applicable)

#### Limited Partnership (LP/SLP/ILP)
- [ ] Certificate of Registration
- [ ] Partnership Agreement (LPA)
- [ ] GP details (full CDD on GP entity)
- [ ] LP Register (names, commitments, %)
- [ ] Structure chart

#### Trust
- [ ] Trust Deed (certified)
- [ ] Deed of Appointment (if trustees changed)
- [ ] Letter of Wishes (if available)
- [ ] Schedule of Beneficiaries
- [ ] ID for: Trustees, Settlor, Protector, Vested Beneficiaries (25%+)

#### Foundation
- [ ] Foundation Charter
- [ ] Regulations/By-laws
- [ ] Register of Council Members
- [ ] ID for: Founder, Council Members, Guardian, Beneficiaries

---

## 6. Workflow Design

### Parallel Track Approach

```
                    ┌─────────────────────────────────────────┐
                    │            ENQUIRY (Phase 1)            │
                    └─────────────────┬───────────────────────┘
                                      │
              ┌───────────────────────┴───────────────────────┐
              │                                               │
              ▼                                               ▼
┌─────────────────────────────┐             ┌─────────────────────────────┐
│     COMPLIANCE TRACK        │             │     COMMERCIAL TRACK        │
│                             │             │     (can start anytime)     │
│  2. Sponsor Onboarding      │             │                             │
│         ↓                   │             │  - Negotiate terms          │
│  3. Fund Structure          │             │  - Draft engagement letter  │
│         ↓                   │             │  - Draft fee schedule       │
│  4. Screening & Risk        │             │                             │
│         ↓                   │             │     DRAFT status until      │
│  5. EDD (if high-risk)      │             │     approval granted        │
│         ↓                   │             │                             │
│  6. Approval (MLRO/Board)   │             │                             │
└─────────────┬───────────────┘             └─────────────┬───────────────┘
              │                                           │
              │              ┌─────────────┐              │
              └─────────────►│  APPROVED?  │◄─────────────┘
                             └──────┬──────┘
                                    │ Yes
                                    ▼
                    ┌─────────────────────────────────────────┐
                    │      7. EXECUTE AGREEMENT               │
                    │      (Requires compliance approval)     │
                    └─────────────────┬───────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────────┐
                    │      8. ONBOARDING COMPLETION           │
                    └─────────────────────────────────────────┘
```

### Phase Details

| Phase | Focus | Key Activities |
|-------|-------|----------------|
| 1. Enquiry | Initial intake | New sponsor form, entity type selection, jurisdiction screening, conflict check |
| 2. Sponsor Onboarding | Sponsor CDD | Entity capture, principal capture, document upload, promoter identification |
| 3. Fund Structure | Fund setup | Fund vehicles, GP entity, fund principals, structure visualization |
| 4. Screening & Risk | Due diligence | PEP/Sanctions/Adverse media on all principals (Sponsor + Fund), regulatory checks, risk scoring |
| 5. EDD | Enhanced DD (if triggered) | Additional documentation, site visits, detailed SOW evidence |
| 6. Approval | Sign-off | Acceptance memo generation, MLRO review, Board approval (high-risk) |
| 7. Commercial | Execution | Engagement letter, legal review, agreement execution (requires approval) |
| 8. Onboarding | Completion | Client record creation, monitoring schedule, welcome pack |

### Risk Assessment Levels

```
┌─────────────────────────────────────────────────────────────────┐
│                 OVERALL RELATIONSHIP RISK                       │
│            (Highest of Sponsor or Fund risk)                    │
│                                                                  │
│   ┌─────────────────────┐     ┌─────────────────────┐          │
│   │   SPONSOR RISK      │     │   FUND RISK         │          │
│   │                     │     │                     │          │
│   │ - Jurisdiction      │     │ - Structure         │          │
│   │ - Principal PEPs    │     │ - GP jurisdiction   │          │
│   │ - Regulatory status │     │ - Fund principals   │          │
│   │ - Track record      │     │ - Strategy/region   │          │
│   │ - Adverse media     │     │ - Investor profile  │          │
│   └─────────────────────┘     └─────────────────────┘          │
│                                                                  │
│            Overall = MAX(Sponsor Risk, Fund Risk)               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. User Roles & Permissions

### Role Definitions

| Role | Primary Function | Can Approve | System Access |
|------|------------------|-------------|---------------|
| Business Development | Intake, enquiries, commercial negotiation | No | Own cases only |
| Compliance Analyst | CDD, screening, risk assessment | Standard risk only | All cases (read), assigned cases (write) |
| MLRO/MLCO | Final compliance sign-off | All risk levels | All cases (read/write) |
| Admin | System config, user management | No (system only) | Full system, no case approvals |

### Approval Matrix

| Risk Level | Required Approvals |
|------------|-------------------|
| Low | Compliance Analyst |
| Medium | Compliance Analyst → MLRO |
| High | Compliance Analyst → MLRO → Board (external, tracked) |

### Admin Capabilities & Restrictions

**Can Do:**
- User management (create/edit/deactivate accounts)
- Role assignment
- System configuration (risk weights, thresholds)
- Audit log access
- Data export
- Override stuck workflows
- Template management

**Cannot Do:**
- Approve submissions (separation of duties)
- Delete audit logs (regulatory requirement)
- Bypass MLRO sign-off
- Backdate entries

---

## 8. AI Integration

### AI Features by Phase

| Phase | AI Feature | Input | Output |
|-------|------------|-------|--------|
| 1. Enquiry | Jurisdiction Screening | Country name | Risk assessment, prohibited flag |
| 1. Enquiry | Conflict Check | Client name, principals | Potential conflicts |
| 2. Sponsor | Document Data Extraction | Uploaded PDF/image | Extracted fields |
| 2. Sponsor | Passport OCR | Passport image | Name, DOB, nationality, MRZ |
| 4. Screening | Regulatory Status Check | Entity, jurisdiction | Regulator, license status |
| 4. Screening | PEP/Sanctions Analysis | Screening results | Match assessment, reasoning |
| 4. Screening | Risk Score Calculation | All client data | Score, rating, reasoning |
| 6. Approval | Acceptance Memo Draft | Full client file | Formatted memo |
| 7. Commercial | Engagement Letter Draft | Client details, terms | Draft letter |
| 8. Onboarding | Welcome Pack Generation | Client details | Compiled PDF |

### Adaptive Regulatory Lookup

The AI dynamically determines relevant regulators based on jurisdiction:

| Jurisdiction | Regulator | Register |
|--------------|-----------|----------|
| Jersey | JFSC | jerseyfsc.org |
| UK | FCA | register.fca.org.uk |
| US | SEC | adviserinfo.sec.gov |
| Cayman | CIMA | cima.ky |
| Luxembourg | CSSF | cssf.lu |
| Ireland | CBI | centralbank.ie |
| Singapore | MAS | mas.gov.sg |
| Hong Kong | SFC | sfc.hk |

### Mock External APIs (POC)

| Service | Mock Behavior |
|---------|---------------|
| PEP Screening | Realistic matches based on test scenarios |
| Sanctions Screening | Clear/match based on test data |
| Adverse Media | Sample articles for test names |
| Company Registry | Mock company data |
| Regulatory Check | Mock registration status |

---

## 9. Google Sheets Schema

### Workbook: `Client_Onboarding_DB`

| Tab | Purpose |
|-----|---------|
| Config | System settings |
| Users | Staff accounts & roles |
| Sponsors | Sponsor/client records |
| Entities | All entities (polymorphic) |
| Persons | All individuals (deduplicated) |
| PersonRoles | Links persons to entities with roles |
| FundStructures | Fund vehicles |
| EntityRoles | Links entities to onboarding context |
| Documents | Document registry |
| DocumentChecklists | Required docs by entity type (config) |
| Screenings | PEP/Sanctions/Adverse media |
| RegulatoryChecks | Regulatory status verifications |
| RiskAssessments | Risk scoring history |
| Approvals | Approval workflow |
| AuditLog | Immutable action log |
| Reminders | Notification queue |
| AnticipatedInvestors | Known investors at setup |
| GeneratedDocs | AI-generated memos, letters |
| JFSC_Compliance_Map | Compliance evidence mapping |

---

## 10. JFSC Compliance Mapping

### Compliance Evidence Tab Structure

| Column | Description |
|--------|-------------|
| Requirement_ID | Unique identifier (e.g., JFSC-CDD-001) |
| Category | CDD / EDD / Screening / Risk / Approval / Records / Monitoring |
| Requirement | Plain English description |
| JFSC_Source | Specific handbook section/article |
| JFSC_URL | Hyperlink to JFSC documentation |
| System_Control | How our system addresses this |
| System_Location | Screen/form/process |
| Evidence_Captured | Data/documents proving compliance |
| Review_Frequency | How often reviewed |
| Last_Reviewed | Date |
| Reviewed_By | MLRO/Compliance |
| Status | Compliant / Partial / Gap / N/A |

### Key Requirements Mapped

| ID | Requirement | System Control |
|----|-------------|----------------|
| JFSC-CDD-001 | Identify customer before business relationship | Entity capture required before Phase 6 approval |
| JFSC-CDD-002 | Identify beneficial owners (25%+) | UBO capture with three-tier test |
| JFSC-CDD-003 | Verify identity using reliable documents | Document checklist by entity type |
| JFSC-CDD-004 | Obtain Source of Wealth | SOW declaration form; AI analysis |
| JFSC-EDD-001 | Apply EDD for PEPs | Auto-trigger EDD when PEP match found |
| JFSC-SCR-001 | Screen against sanctions lists | Sanctions screening on all principals |
| JFSC-RSK-001 | Conduct customer risk assessment | AI risk scoring at Sponsor + Fund level |
| JFSC-APR-001 | Senior management approval for high-risk | Board approval required |
| JFSC-REC-001 | Retain CDD records 5 years | Google Sheets + GDrive retention |
| JFSC-JPF-001 | Identify Promoter/Instigator | Promoter role in PersonRoles |

---

## 11. Notifications & Reminders

### Reminder Types

| Type | Trigger | Recipients | Timing |
|------|---------|------------|--------|
| Periodic Review Due | Review date approaching | Compliance | 30, 14, 7 days |
| Document Expiry | Passport/cert expiring | Compliance | 60, 30, 14 days |
| Approval Pending | Item waiting >2 days | MLRO | Daily |
| EDD Overdue | High-risk EDD incomplete >14 days | MLRO + Compliance | Every 3 days |
| Screening Refresh | Annual re-screening due | Compliance | 30, 14 days |
| Compliance Map Review | Annual review due | MLRO | 30, 14 days |
| Stale Onboarding | Inactive >30 days | Assigned user | Weekly |

### Delivery Methods
- In-app dashboard widget (primary)
- Email notifications (daily digest or immediate)
- Badge count on navbar

---

## 12. Mock Test Scenarios

### Scenario 1: Granite Capital Partners LLP (Low Risk)

**Sponsor:** Established UK PE house, FCA authorised
**Fund:** Granite Capital Fund III LP (Jersey JPF)
**Principals:** 3 British partners, clean screening
**Risk Score:** 25 (Low)
**Flow:** Standard path, MLRO approval only

### Scenario 2: Ashford Capital Advisors Ltd (Medium Risk - PEP)

**Sponsor:** UK-based advisor
**Fund:** Ashford Growth Fund I LP (Jersey JPF)
**Principals:** Includes former MP (domestic PEP)
**Risk Score:** 55 (Medium)
**Flow:** Triggers EDD, MLRO approval

### Scenario 3: Bluewater Asset Management (Medium Risk - Adverse Media)

**Sponsor:** Property-focused manager
**Fund:** Bluewater Real Estate Fund LP (Jersey JPF)
**Principals:** One with historic adverse media (resolved)
**Risk Score:** 52 (Medium)
**Flow:** Adverse media review, documented resolution

### Scenario 4: Volkov Capital Partners (High Risk)

**Sponsor:** Growth equity manager
**Fund:** Volkov Ventures Fund I LP (Jersey JPF + Cayman feeder)
**Principals:** Russian nationals, UAE connections
**Risk Score:** 75 (High)
**Flow:** Full EDD, MLRO + Board approval

---

## 13. Implementation Plan

### Phased Delivery

| Phase | Focus | Key Deliverables |
|-------|-------|------------------|
| 1 | Foundation | Project setup, Sheets schema, base UI, auth |
| 2 | Sponsor Onboarding | Entity forms, principal capture, document upload |
| 3 | Fund Structure | Fund vehicles, GP setup, structure visualization |
| 4 | Screening & Risk | Mock APIs, screenings, risk scoring |
| 5 | Approval Workflow | Memo generation, MLRO queue, approvals |
| 6 | Commercial Track | Engagement letter, parallel workflow |
| 7 | Completion | Welcome pack, monitoring, dashboards, reminders |

### POC Success Criteria

| Criteria | Target |
|----------|--------|
| End-to-end flow | Complete Granite scenario |
| Entity types | Individual, Company, LP, Trust working |
| AI features | Doc extraction, risk scoring, memo generation |
| Screening | Mock PEP/Sanctions/Adverse media |
| Parallel tracks | Commercial draft during compliance |
| Role separation | BD, Compliance, MLRO dashboards |
| Compliance evidence | JFSC mapping tab populated |
| Reminders | Basic reminder system working |

---

## 14. UI/UX Consistency

The system will maintain visual consistency with the existing invoice-tracker using CoreWorker AI branding:

- **Primary Blue:** #54A6ED
- **Accent Green:** #10B981
- **Dark Theme (nav/footer):** linear-gradient(135deg, #1a1a2e → #16213e)
- **Fonts:** Outfit (headings), Inter (body)
- **Framework:** Bootstrap 5 + Bootstrap Icons

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| Sponsor | The PE House/Fund Manager - the actual client relationship |
| JPF | Jersey Private Fund |
| UBO | Ultimate Beneficial Owner (25%+ ownership) |
| PEP | Politically Exposed Person |
| RCA | Relative or Close Associate (of PEP) |
| EDD | Enhanced Due Diligence |
| SOW | Source of Wealth |
| SOF | Source of Funds |
| MLRO | Money Laundering Reporting Officer |
| MLCO | Money Laundering Compliance Officer |
| BRA | Business Risk Assessment |
| CRA | Customer Risk Assessment |

---

## Appendix B: Document Approval

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Author | Claude Code | 2026-02-02 | |
| Product Owner | | | |
| Compliance Review | | | |
| Technical Review | | | |

---

*End of Design Document*
