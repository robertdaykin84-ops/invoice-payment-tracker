# Merged Enquiry Form Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Merge Enquiry (Phase 1) and Sponsor (Phase 2) data capture into a single comprehensive enquiry form with full principal CDD upfront.

**Architecture:** Single form replaces two phases. On submit, creates Enquiry, Sponsor, Persons, and PersonRoles records. Phases 3-8 shift to become Phases 2-7.

**Tech Stack:** Flask, Jinja2 templates, Bootstrap 5, Google Sheets persistence

---

## Form Structure

### Section 1: Sponsor Entity Details

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Legal Name | text | Yes | e.g., "Granite Capital Partners LLP" |
| Trading Name | text | No | Only if different from legal name |
| Entity Type | radio cards | Yes | Company, LLP, LP, Trust, Foundation, Other |
| Jurisdiction | select | Yes | UK, Jersey, Guernsey, Cayman, Luxembourg, Ireland, US-Delaware, Other |
| Registration Number | text | Yes | e.g., "OC123456" |
| Date of Incorporation | date | Yes | Must be in the past |
| Registered Address | textarea | Yes | Full postal address |
| Principal Place of Business | textarea | No | "Same as registered" checkbox available |

### Section 2: Regulatory Status

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Regulatory Status | select | Yes | Regulated, Not Regulated, Exempt, Pending Registration |
| Regulator | select | Conditional | Required if "Regulated" - FCA, JFSC, GFSC, CIMA, SEC, CSSF, CBI, Other |
| License/Registration Number | text | Conditional | Required if "Regulated" |

### Section 3: Source of Wealth

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Principal Business Activities | textarea | Yes | Primary activities and revenue sources |
| Source of Wealth Narrative | textarea | Yes | How the sponsor accumulated capital |

### Section 4: Proposed Fund Structure

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Fund Name | text | Yes | e.g., "Granite Capital Fund III LP" |
| Fund Type | select | Yes | Jersey Private Fund (JPF), Expert Fund, Listed Fund, Other |
| Legal Structure | select | Yes | Limited Partnership, Unit Trust, ICC, PCC, Other |
| Target Fund Size | currency | Yes | USD amount with $ prefix |
| Investment Strategy | textarea | Yes | Brief description of investment focus |

### Section 5: Principals & Beneficial Owners

**Per Principal:**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Full Legal Name | text | Yes | As appears on ID |
| Former Names | text | No | Maiden name, previous names |
| Date of Birth | date | Yes | Must be 18+ |
| Nationality | select | Yes | Country list |
| Country of Residence | select | Yes | Country list |
| Residential Address | textarea | Yes | Full postal address |
| Role | select | Yes | Director, Partner, Shareholder, UBO, Designated Member, General Partner |
| Ownership % | number | Conditional | Required if Shareholder/Partner |
| Is UBO | checkbox | No | Auto-checked if ownership >= 25% |

**UI Pattern:**
- "Add Principal" button opens modal form
- Principals displayed in table with edit/remove actions
- Minimum 1 principal required
- Warning if no UBOs identified

**Validation:**
- At least one principal required
- If entity type is LLP: at least 2 designated members
- Total ownership % cannot exceed 100%

### Section 6: Primary Contact

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Contact Name | text | Yes | Primary point of contact |
| Email | email | Yes | For correspondence |
| Phone | tel | No | Optional |
| Enquiry Source | select | No | Referral, Existing Client, Website, Industry Event, Other |
| Referrer Name | text | Conditional | Required if source = "Referral" |

### Section 7: Supporting Documents

| Document | Required | Notes |
|----------|----------|-------|
| Certificate of Incorporation | No | Upload now or later |
| Memorandum & Articles | No | Upload now or later |
| Structure Chart | No | Recommended if complex |

### Section 8: Declaration

**Checkbox (required):**
> "I confirm that the information provided is accurate and complete to the best of my knowledge. I understand that this information will be used for due diligence and regulatory compliance purposes."

---

## Data Flow

**On Submit:**
1. Validate all required fields
2. Create `Enquiry` record (status: "pending")
3. Create `Sponsor` record
4. Create `Person` record for each principal
5. Create `PersonRole` record linking each person to sponsor
6. Save audit trail to Google Drive
7. Redirect to dashboard or confirmation

**On Confirm (staff review):**
1. Update Enquiry status to "confirmed"
2. Create `Onboarding` record (current_phase: 2)
3. Redirect to Phase 2 (Fund Structure - formerly Phase 3)

---

## Phase Renumbering

| Old Phase | New Phase | Name |
|-----------|-----------|------|
| Phase 1 | Phase 1 | Enquiry (merged) |
| Phase 2 | (removed) | - |
| Phase 3 | Phase 2 | Fund Structure |
| Phase 4 | Phase 3 | Screening |
| Phase 5 | Phase 4 | EDD (if required) |
| Phase 6 | Phase 5 | Approval |
| Phase 7 | Phase 6 | Commercial |
| Phase 8 | Phase 7 | Complete |

---

## Sample Enquiry Data

### Sample 1: Granite Capital Partners LLP

```json
{
  "sponsor": {
    "legal_name": "Granite Capital Partners LLP",
    "trading_name": "",
    "entity_type": "llp",
    "jurisdiction": "UK",
    "registration_number": "OC123456",
    "date_incorporated": "2015-03-15",
    "registered_address": "10 Fleet Street\nLondon\nEC4Y 1AU\nUnited Kingdom",
    "business_address": "",
    "regulatory_status": "regulated",
    "regulator": "FCA",
    "license_number": "789012",
    "business_activities": "Private equity fund management focused on mid-market buyouts in technology and healthcare sectors across UK and Europe.",
    "source_of_wealth": "Management fees from existing funds under management (Funds I and II totaling $800M AUM), carried interest from successful exits, and partner capital contributions from previous investment banking careers."
  },
  "fund": {
    "fund_name": "Granite Capital Fund III LP",
    "fund_type": "jpf",
    "legal_structure": "lp",
    "target_size": "500000000",
    "investment_strategy": "Mid-market buyout investments in UK and European technology and healthcare sectors, targeting companies with £20-100M enterprise value and strong growth potential."
  },
  "principals": [
    {
      "full_name": "John Edward Smith",
      "former_names": "",
      "dob": "1975-06-12",
      "nationality": "British",
      "country_of_residence": "UK",
      "residential_address": "42 Kensington Gardens\nLondon\nW8 4PX\nUnited Kingdom",
      "role": "partner",
      "ownership_pct": 40,
      "is_ubo": true
    },
    {
      "full_name": "Sarah Jane Johnson",
      "former_names": "Sarah Jane Mitchell",
      "dob": "1978-09-23",
      "nationality": "British",
      "country_of_residence": "UK",
      "residential_address": "15 Chelsea Embankment\nLondon\nSW3 4LG\nUnited Kingdom",
      "role": "partner",
      "ownership_pct": 35,
      "is_ubo": true
    },
    {
      "full_name": "Michael James Brown",
      "former_names": "",
      "dob": "1980-02-08",
      "nationality": "British",
      "country_of_residence": "UK",
      "residential_address": "8 Richmond Hill\nRichmond\nTW10 6QX\nUnited Kingdom",
      "role": "partner",
      "ownership_pct": 25,
      "is_ubo": true
    }
  ],
  "contact": {
    "name": "John Smith",
    "email": "john.smith@granitecapital.com",
    "phone": "+44 20 7123 4567",
    "enquiry_source": "existing",
    "referrer_name": ""
  }
}
```

### Sample 2: Evergreen Capital Management Ltd

```json
{
  "sponsor": {
    "legal_name": "Evergreen Capital Management Ltd",
    "trading_name": "Evergreen Capital",
    "entity_type": "company",
    "jurisdiction": "UK",
    "registration_number": "12345678",
    "date_incorporated": "2018-07-20",
    "registered_address": "25 Old Broad Street\nLondon\nEC2N 1HQ\nUnited Kingdom",
    "business_address": "25 Old Broad Street\nLondon\nEC2N 1HQ\nUnited Kingdom",
    "regulatory_status": "regulated",
    "regulator": "FCA",
    "license_number": "823456",
    "business_activities": "ESG-focused investment management specializing in renewable energy infrastructure and sustainable growth equity.",
    "source_of_wealth": "Seed capital from founding partners' previous fund management roles at major institutions, subsequently grown through management fees and performance fees from Fund I ($150M)."
  },
  "fund": {
    "fund_name": "Evergreen Sustainable Growth Fund LP",
    "fund_type": "jpf",
    "legal_structure": "lp",
    "target_size": "250000000",
    "investment_strategy": "ESG-focused growth equity investments in renewable energy infrastructure, clean technology, and sustainable businesses across Europe."
  },
  "principals": [
    {
      "full_name": "Elizabeth Wei Chen",
      "former_names": "",
      "dob": "1982-11-30",
      "nationality": "British",
      "country_of_residence": "UK",
      "residential_address": "Flat 12, The Tower\nCanary Wharf\nLondon\nE14 5AB\nUnited Kingdom",
      "role": "director",
      "ownership_pct": 50,
      "is_ubo": true
    },
    {
      "full_name": "David Robert Thompson",
      "former_names": "",
      "dob": "1979-04-17",
      "nationality": "British",
      "country_of_residence": "UK",
      "residential_address": "23 Hampstead Lane\nLondon\nN6 4RS\nUnited Kingdom",
      "role": "director",
      "ownership_pct": 30,
      "is_ubo": true
    },
    {
      "full_name": "Green Future Investments Ltd",
      "former_names": "",
      "dob": "",
      "nationality": "",
      "country_of_residence": "UK",
      "residential_address": "1 Angel Court\nLondon\nEC2R 7HJ\nUnited Kingdom",
      "role": "shareholder",
      "ownership_pct": 20,
      "is_ubo": false
    }
  ],
  "contact": {
    "name": "Elizabeth Chen",
    "email": "e.chen@evergreencap.com",
    "phone": "+44 20 7456 7890",
    "enquiry_source": "referral",
    "referrer_name": "James Morrison, Clifford Chance LLP"
  }
}
```

### Sample 3: Nordic Ventures AS

```json
{
  "sponsor": {
    "legal_name": "Nordic Ventures AS",
    "trading_name": "",
    "entity_type": "company",
    "jurisdiction": "other",
    "jurisdiction_other": "Norway",
    "registration_number": "NO 912 345 678",
    "date_incorporated": "2012-01-10",
    "registered_address": "Aker Brygge 1\nOslo 0250\nNorway",
    "business_address": "Aker Brygge 1\nOslo 0250\nNorway",
    "regulatory_status": "regulated",
    "regulator": "other",
    "regulator_other": "FSA Norway (Finanstilsynet)",
    "license_number": "NOR-2012-0456",
    "business_activities": "Venture capital and growth equity investments in Nordic technology companies, with focus on software, fintech, and digital health sectors.",
    "source_of_wealth": "Founding partners' successful exits from previous technology ventures, combined with institutional LP commitments to Funds I-III totaling €400M."
  },
  "fund": {
    "fund_name": "Nordic Technology Opportunities Fund LP",
    "fund_type": "expert",
    "legal_structure": "lp",
    "target_size": "150000000",
    "investment_strategy": "Early-stage and growth investments in Nordic technology companies, targeting Series A to Series C rounds in software, fintech, and digital health sectors."
  },
  "principals": [
    {
      "full_name": "Erik Anders Larsson",
      "former_names": "",
      "dob": "1970-08-22",
      "nationality": "Norwegian",
      "country_of_residence": "Norway",
      "residential_address": "Bygdøy Allé 45\nOslo 0265\nNorway",
      "role": "director",
      "ownership_pct": 60,
      "is_ubo": true
    },
    {
      "full_name": "Anna Kristina Bergström",
      "former_names": "Anna Kristina Nilsson",
      "dob": "1976-03-14",
      "nationality": "Swedish",
      "country_of_residence": "Norway",
      "residential_address": "Frognerveien 12\nOslo 0263\nNorway",
      "role": "director",
      "ownership_pct": 40,
      "is_ubo": true
    }
  ],
  "contact": {
    "name": "Erik Larsson",
    "email": "erik@nordicventures.no",
    "phone": "+47 22 12 34 56",
    "enquiry_source": "event",
    "referrer_name": ""
  }
}
```

---

## Files to Modify/Create

| File | Action | Purpose |
|------|--------|---------|
| `templates/onboarding/phase1.html` | Rewrite | New merged enquiry form |
| `templates/onboarding/phase2.html` | Delete | No longer needed |
| `templates/onboarding/phase3.html` | Rename | Becomes phase2.html |
| `templates/onboarding/phase4.html` | Rename | Becomes phase3.html |
| `templates/onboarding/phase5.html` | Rename | Becomes phase4.html |
| `templates/onboarding/phase6.html` | Rename | Becomes phase5.html |
| `templates/onboarding/phase7.html` | Rename | Becomes phase6.html |
| `templates/onboarding/phase8.html` | Rename | Becomes phase7.html |
| `app.py` | Modify | Update phase routing, form handling |
| `services/sheets_db.py` | Modify | Update schema if needed |
| `static/data/sample_enquiries.json` | Create | Sample enquiry data |

---

## Validation Rules

1. All required fields must be completed
2. At least one principal required
3. If LLP: minimum 2 designated members
4. Total ownership cannot exceed 100%
5. Warning (non-blocking) if no UBO identified
6. Date of incorporation must be in the past
7. DOB must make principal 18+ years old
8. Email must be valid format
