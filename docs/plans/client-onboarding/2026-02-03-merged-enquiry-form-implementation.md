# Merged Enquiry Form Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Merge Enquiry and Sponsor forms into a single comprehensive Phase 1 form with full principal CDD, renumber phases 3-8 to 2-7.

**Architecture:** Rewrite phase1.html with all sections, update app.py routing to handle merged data, rename phase templates, create sample data JSON file.

**Tech Stack:** Flask, Jinja2, Bootstrap 5, JavaScript, Google Sheets API

---

## Task 1: Create Sample Enquiry Data File

**Files:**
- Create: `static/data/sample_enquiries.json`

**Step 1: Create the sample data file**

Create file `static/data/sample_enquiries.json` with the 3 sample enquiries from the design document (Granite Capital, Evergreen Capital, Nordic Ventures). Include full sponsor, fund, principals, and contact data for each.

**Step 2: Verify JSON is valid**

Run: `python3 -c "import json; json.load(open('static/data/sample_enquiries.json'))"`
Expected: No output (valid JSON)

**Step 3: Commit**

```bash
git add static/data/sample_enquiries.json
git commit -m "feat: add sample enquiry data for merged form"
```

---

## Task 2: Update Sheets Schema for Enhanced Data

**Files:**
- Modify: `services/sheets_db.py:34-68` (SCHEMA definition)

**Step 1: Update the SCHEMA to include new fields**

Add to Enquiries schema:
- `trading_name`, `date_incorporated`, `registered_address`, `business_address`
- `regulatory_status`, `regulator`, `license_number`
- `business_activities`, `source_of_wealth`

Add to Sponsors schema:
- `trading_name`, `date_incorporated`, `registered_address`, `business_address`
- `business_activities`, `source_of_wealth`

Add to Persons schema:
- `former_names`, `residential_address`

**Step 2: Test schema loads**

Run: `python3 -c "from services.sheets_db import SCHEMA; print('Enquiries:', len(SCHEMA['Enquiries']), 'cols'); print('Sponsors:', len(SCHEMA['Sponsors']), 'cols')"`
Expected: Shows increased column counts

**Step 3: Commit**

```bash
git add services/sheets_db.py
git commit -m "feat: extend sheets schema for merged enquiry form"
```

---

## Task 3: Rewrite Phase 1 Template - Part 1 (Sponsor Entity)

**Files:**
- Modify: `templates/onboarding/phase1.html`

**Step 1: Replace the current form with new Section 1 (Sponsor Entity Details)**

Keep the page structure (breadcrumb, wizard stepper, sidebar) but replace the form content with:
- Legal Name (text, required)
- Trading Name (text, optional)
- Entity Type (radio cards: Company, LLP, LP, Trust, Foundation, Other)
- Jurisdiction (select with Other option)
- Registration Number (text, required)
- Date of Incorporation (date, required)
- Registered Address (textarea, required)
- Principal Place of Business (textarea, optional with "same as registered" checkbox)

Use Bootstrap 5 grid (col-md-6, col-md-4 etc.) matching current styling.

**Step 2: Test template renders**

Run: Start app, navigate to `/onboarding/new/1`
Expected: Form displays with new sponsor entity fields

**Step 3: Commit**

```bash
git add templates/onboarding/phase1.html
git commit -m "feat: phase1 template - sponsor entity section"
```

---

## Task 4: Rewrite Phase 1 Template - Part 2 (Regulatory & Source of Wealth)

**Files:**
- Modify: `templates/onboarding/phase1.html`

**Step 1: Add Section 2 (Regulatory Status) after sponsor entity section**

Add horizontal rule then:
- Regulatory Status (select: Regulated, Not Regulated, Exempt, Pending)
- Regulator (select, shown only if Regulated: FCA, JFSC, GFSC, CIMA, SEC, CSSF, CBI, Other)
- License/Registration Number (text, shown only if Regulated)

**Step 2: Add Section 3 (Source of Wealth)**

Add horizontal rule then:
- Principal Business Activities (textarea, required, 2 rows)
- Source of Wealth Narrative (textarea, required, 3 rows)

**Step 3: Add JavaScript for conditional field display**

Add script to show/hide regulator fields based on regulatory_status value.

**Step 4: Test conditional display**

Run: In browser, change Regulatory Status dropdown
Expected: Regulator and License fields appear/disappear based on selection

**Step 5: Commit**

```bash
git add templates/onboarding/phase1.html
git commit -m "feat: phase1 template - regulatory and source of wealth sections"
```

---

## Task 5: Rewrite Phase 1 Template - Part 3 (Fund Structure)

**Files:**
- Modify: `templates/onboarding/phase1.html`

**Step 1: Add Section 4 (Proposed Fund Structure)**

Add horizontal rule then:
- Fund Name (text, required)
- Fund Type (select: JPF, Expert Fund, Listed Fund, Other)
- Legal Structure (select: LP, Unit Trust, ICC, PCC, Other)
- Target Fund Size (input-group with $ prefix, required)
- Investment Strategy (textarea, required, 3 rows)

**Step 2: Test template renders**

Run: Refresh page in browser
Expected: Fund section displays below source of wealth

**Step 3: Commit**

```bash
git add templates/onboarding/phase1.html
git commit -m "feat: phase1 template - fund structure section"
```

---

## Task 6: Rewrite Phase 1 Template - Part 4 (Principals Table & Modal)

**Files:**
- Modify: `templates/onboarding/phase1.html`

**Step 1: Add Section 5 (Principals & Beneficial Owners)**

Add a card with:
- Header with "Add Principal" button
- Info text about adding directors, partners, shareholders (25%+), UBOs
- Empty table with columns: Name, Role, Ownership %, UBO, Actions
- Alert about UBO threshold (25%)

**Step 2: Add Principal Modal**

Add Bootstrap modal with form fields:
- Full Legal Name (text, required)
- Former Names (text, optional)
- Date of Birth (date, required)
- Nationality (select, required)
- Country of Residence (select, required)
- Residential Address (textarea, required)
- Role (select: Director, Partner, Shareholder, UBO, Designated Member, GP)
- Ownership % (number, 0-100)
- Is UBO checkbox

**Step 3: Test modal opens**

Run: Click "Add Principal" button
Expected: Modal opens with all fields

**Step 4: Commit**

```bash
git add templates/onboarding/phase1.html
git commit -m "feat: phase1 template - principals table and modal"
```

---

## Task 7: Rewrite Phase 1 Template - Part 5 (Principals JavaScript)

**Files:**
- Modify: `templates/onboarding/phase1.html`

**Step 1: Add JavaScript for principals management**

Add script block with:
- `principals` array to store added principals
- `addPrincipal()` function to collect modal form data, add to array, update table
- `removePrincipal(index)` function to remove from array and update table
- `renderPrincipalsTable()` function to rebuild table HTML from array
- Auto-check UBO if ownership >= 25%
- Hidden input to store principals JSON for form submission

**Step 2: Test adding a principal**

Run: Fill modal form, click Add
Expected: Principal appears in table, modal closes

**Step 3: Test removing a principal**

Run: Click remove button on a principal row
Expected: Row removed from table

**Step 4: Commit**

```bash
git add templates/onboarding/phase1.html
git commit -m "feat: phase1 template - principals JavaScript functionality"
```

---

## Task 8: Rewrite Phase 1 Template - Part 6 (Contact, Docs, Declaration)

**Files:**
- Modify: `templates/onboarding/phase1.html`

**Step 1: Add Section 6 (Primary Contact)**

Add horizontal rule then:
- Contact Name (text, required)
- Email (email, required)
- Phone (tel, optional)
- Enquiry Source (select: Referral, Existing Client, Website, Industry Event, Other)
- Referrer Name (text, shown if source=Referral)

**Step 2: Add Section 7 (Supporting Documents)**

Add card with upload placeholders for:
- Certificate of Incorporation (optional)
- Memorandum & Articles (optional)
- Structure Chart (optional)
Mark all as "Upload later available"

**Step 3: Add Section 8 (Declaration)**

Add checkbox with declaration text (required to submit)

**Step 4: Update form actions**

Keep Save Draft and Submit buttons, update submit to go to dashboard (no Phase 2)

**Step 5: Test full form renders**

Run: Refresh page
Expected: All 8 sections visible, form complete

**Step 6: Commit**

```bash
git add templates/onboarding/phase1.html
git commit -m "feat: phase1 template - contact, documents, declaration sections"
```

---

## Task 9: Update App.py Form Handler for Merged Data

**Files:**
- Modify: `app.py` (onboarding_phase function, around line 400-500)

**Step 1: Update Phase 1 POST handler**

Modify the phase 1 form handling to:
- Extract all new sponsor fields from form
- Extract fund fields
- Parse principals JSON from hidden input
- Create Enquiry record with all fields
- Create Sponsor record
- Create Person records for each principal
- Create PersonRole records linking persons to sponsor
- On success, redirect to Phase 2 (formerly Phase 3 - Fund Structure)

**Step 2: Test form submission**

Run: Fill out form completely, click Submit
Expected: Records created in Sheets, redirect to Phase 2

**Step 3: Commit**

```bash
git add app.py
git commit -m "feat: update phase 1 handler for merged enquiry/sponsor data"
```

---

## Task 10: Rename Phase Templates (3→2, 4→3, etc.)

**Files:**
- Rename: `templates/onboarding/phase3.html` → `templates/onboarding/phase2.html`
- Rename: `templates/onboarding/phase4.html` → `templates/onboarding/phase3.html`
- Rename: `templates/onboarding/phase5.html` → `templates/onboarding/phase4.html`
- Rename: `templates/onboarding/phase6.html` → `templates/onboarding/phase5.html`
- Rename: `templates/onboarding/phase7.html` → `templates/onboarding/phase6.html`
- Rename: `templates/onboarding/phase8.html` → `templates/onboarding/phase7.html`
- Delete: `templates/onboarding/phase2.html` (old sponsor form)

**Step 1: Delete old phase2.html**

```bash
rm templates/onboarding/phase2.html
```

**Step 2: Rename templates**

```bash
mv templates/onboarding/phase3.html templates/onboarding/phase2.html
mv templates/onboarding/phase4.html templates/onboarding/phase3.html
mv templates/onboarding/phase5.html templates/onboarding/phase4.html
mv templates/onboarding/phase6.html templates/onboarding/phase5.html
mv templates/onboarding/phase7.html templates/onboarding/phase6.html
mv templates/onboarding/phase8.html templates/onboarding/phase7.html
```

**Step 3: Commit renames**

```bash
git add -A
git commit -m "refactor: rename phase templates (remove phase 2, shift 3-8 to 2-7)"
```

---

## Task 11: Update Phase Navigation in Templates

**Files:**
- Modify: `templates/onboarding/phase2.html` (formerly phase3)
- Modify: `templates/onboarding/phase3.html` (formerly phase4)
- Modify: `templates/onboarding/phase4.html` (formerly phase5)
- Modify: `templates/onboarding/phase5.html` (formerly phase6)
- Modify: `templates/onboarding/phase6.html` (formerly phase7)
- Modify: `templates/onboarding/phase7.html` (formerly phase8)

**Step 1: Update each template's navigation links**

In each renamed template:
- Update "Back to Phase X" links (decrement by 1)
- Update "Continue to Phase X" links (decrement by 1)
- Update breadcrumb text if it mentions phase numbers
- Update page title if it mentions phase numbers

**Step 2: Verify all links**

Run: Navigate through all phases in browser
Expected: Back/Continue buttons work correctly through phases 1-7

**Step 3: Commit**

```bash
git add templates/onboarding/
git commit -m "fix: update phase navigation links after renumbering"
```

---

## Task 12: Update App.py Phase Configuration

**Files:**
- Modify: `app.py` (PHASES constant and routing)

**Step 1: Update PHASES constant**

Change from 8 phases to 7 phases:
```python
PHASES = [
    {'num': 1, 'name': 'Enquiry', 'icon': 'bi-clipboard-check'},
    {'num': 2, 'name': 'Fund', 'icon': 'bi-diagram-3'},
    {'num': 3, 'name': 'Screening', 'icon': 'bi-search'},
    {'num': 4, 'name': 'EDD', 'icon': 'bi-shield-check'},
    {'num': 5, 'name': 'Approval', 'icon': 'bi-check-circle'},
    {'num': 6, 'name': 'Commercial', 'icon': 'bi-currency-pound'},
    {'num': 7, 'name': 'Complete', 'icon': 'bi-flag'},
]
```

**Step 2: Update phase routing logic**

Ensure phase validation allows 1-7 (not 1-8)

**Step 3: Test phase stepper**

Run: Navigate to any phase
Expected: Wizard stepper shows 7 phases with correct icons

**Step 4: Commit**

```bash
git add app.py
git commit -m "refactor: update PHASES config from 8 to 7 phases"
```

---

## Task 13: Update Seed Data for New Schema

**Files:**
- Modify: `services/sheets_db.py` (seed_initial_data function, around line 898-1039)

**Step 1: Update seed enquiries with new fields**

Add to each seeded enquiry:
- trading_name, date_incorporated, registered_address, business_address
- regulatory_status, regulator, license_number
- business_activities, source_of_wealth

**Step 2: Update seed sponsors with new fields**

Add to each seeded sponsor:
- trading_name, date_incorporated, registered_address, business_address
- business_activities, source_of_wealth

**Step 3: Add seed persons with full CDD**

Create Person records for sample principals with:
- full_name, former_names, dob, nationality, country_of_residence, residential_address

**Step 4: Test seeding**

Run: Delete existing sheet data, restart app
Expected: New data seeded with all fields populated

**Step 5: Commit**

```bash
git add services/sheets_db.py
git commit -m "feat: update seed data with enhanced enquiry/sponsor fields"
```

---

## Task 14: End-to-End Testing

**Files:**
- None (testing only)

**Step 1: Clear existing data**

Delete all rows (except headers) from Google Sheets tabs

**Step 2: Restart app and verify seeding**

Run: `python3 app.py`
Expected: Seed data created with new fields

**Step 3: Test new enquiry flow**

1. Login as staff user
2. Navigate to New Onboarding
3. Fill out complete merged enquiry form
4. Add 2-3 principals via modal
5. Submit form
6. Verify records created in Sheets (Enquiries, Sponsors, Persons, PersonRoles)
7. Verify redirect to Phase 2 (Fund Structure)
8. Navigate through remaining phases 2-7

**Step 4: Fix any issues found**

Address any bugs discovered during testing

**Step 5: Final commit**

```bash
git add -A
git commit -m "test: verify merged enquiry form end-to-end"
```

---

## Summary

| Task | Description | Estimated Complexity |
|------|-------------|---------------------|
| 1 | Create sample enquiry JSON | Simple |
| 2 | Update Sheets schema | Simple |
| 3 | Phase 1 template - Sponsor Entity | Medium |
| 4 | Phase 1 template - Regulatory/SoW | Medium |
| 5 | Phase 1 template - Fund Structure | Simple |
| 6 | Phase 1 template - Principals UI | Medium |
| 7 | Phase 1 template - Principals JS | Complex |
| 8 | Phase 1 template - Contact/Docs/Declaration | Medium |
| 9 | Update app.py form handler | Complex |
| 10 | Rename phase templates | Simple |
| 11 | Update phase navigation links | Medium |
| 12 | Update PHASES config | Simple |
| 13 | Update seed data | Medium |
| 14 | End-to-end testing | Medium |

Total: 14 tasks
