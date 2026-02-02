# Risk Scoring Algorithm - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement weighted risk scoring algorithm that calculates risk from jurisdiction, PEP, sanctions, adverse media, and entity structure factors.

**Architecture:** New `services/risk_scoring.py` service with `calculate_risk()` function. Integrated into `/api/screening/run` endpoint. Results displayed in Phase 4 UI with factor breakdown.

**Tech Stack:** Python, Flask, existing SheetsDB for persistence

---

## Task 1: Create risk_scoring.py with jurisdiction scoring

**Files:**
- Create: `packages/client-onboarding/services/risk_scoring.py`

**Step 1: Create the service file with jurisdiction constants and scoring**

```python
"""
Risk Scoring Service
Calculates weighted risk scores based on JFSC AML/CFT guidelines.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# =============================================================================
# JURISDICTION RISK TIERS (JFSC Appendix D1/D2 + FATF)
# Updated: February 2026
# =============================================================================

# FATF Black List - Call for Action (Prohibited)
JURISDICTION_PROHIBITED = {'KP', 'IR', 'MM'}  # North Korea, Iran, Myanmar

# FATF Grey List - Increased Monitoring (High Risk)
JURISDICTION_HIGH = {
    'DZ', 'AO', 'BO', 'BG', 'CM', 'CI', 'CD', 'HT', 'KE', 'LA',
    'LB', 'MC', 'NA', 'NP', 'SS', 'SY', 'VE', 'VN', 'VG', 'YE'
}  # Algeria, Angola, Bolivia, Bulgaria, Cameroon, Côte d'Ivoire, DRC, Haiti,
   # Kenya, Lao PDR, Lebanon, Monaco, Namibia, Nepal, South Sudan, Syria,
   # Venezuela, Vietnam, BVI, Yemen

# Offshore Financial Centers (Elevated Risk)
JURISDICTION_ELEVATED = {
    'KY', 'BM', 'IM', 'PA', 'SC', 'MU', 'BS', 'BB', 'AG', 'LC', 'VC', 'TC', 'AI'
}  # Cayman, Bermuda, Isle of Man, Panama, Seychelles, Mauritius, Bahamas,
   # Barbados, Antigua, St Lucia, St Vincent, Turks & Caicos, Anguilla

# Low Risk - Established Relationships
JURISDICTION_LOW = {'GB', 'JE', 'GG', 'IE'}  # UK, Jersey, Guernsey, Ireland

# Country name mapping for display
COUNTRY_NAMES = {
    'GB': 'United Kingdom', 'JE': 'Jersey', 'GG': 'Guernsey', 'IE': 'Ireland',
    'US': 'United States', 'CA': 'Canada', 'AU': 'Australia', 'DE': 'Germany',
    'FR': 'France', 'NL': 'Netherlands', 'CH': 'Switzerland', 'LU': 'Luxembourg',
    'KP': 'North Korea', 'IR': 'Iran', 'MM': 'Myanmar',
    'KY': 'Cayman Islands', 'BM': 'Bermuda', 'VG': 'British Virgin Islands',
    'RU': 'Russia', 'BY': 'Belarus', 'CN': 'China', 'HK': 'Hong Kong',
}

# =============================================================================
# RISK WEIGHTS
# =============================================================================

WEIGHTS = {
    'jurisdiction': 0.25,
    'pep_status': 0.25,
    'sanctions': 0.30,
    'adverse_media': 0.10,
    'entity_structure': 0.10
}

# =============================================================================
# THRESHOLDS
# =============================================================================

THRESHOLD_LOW = 40      # 0-39 = Low risk
THRESHOLD_MEDIUM = 70   # 40-69 = Medium risk, 70+ = High risk


def get_jurisdiction_score(country_code: str) -> dict:
    """
    Calculate jurisdiction risk score based on JFSC/FATF classification.

    Args:
        country_code: ISO 3166-1 alpha-2 country code (e.g., 'GB', 'US')

    Returns:
        dict with score, tier, and reason
    """
    if not country_code:
        return {
            'score': 50,
            'tier': 'unknown',
            'reason': 'Jurisdiction not specified'
        }

    code = country_code.upper().strip()
    country_name = COUNTRY_NAMES.get(code, code)

    if code in JURISDICTION_PROHIBITED:
        return {
            'score': 100,
            'tier': 'prohibited',
            'reason': f'{country_name} - FATF Black List (Prohibited)'
        }

    if code in JURISDICTION_HIGH:
        return {
            'score': 80,
            'tier': 'high',
            'reason': f'{country_name} - FATF Grey List (High Risk)'
        }

    if code in JURISDICTION_ELEVATED:
        return {
            'score': 50,
            'tier': 'elevated',
            'reason': f'{country_name} - Offshore Financial Center (Elevated)'
        }

    if code in JURISDICTION_LOW:
        return {
            'score': 0,
            'tier': 'low',
            'reason': f'{country_name} - Established Relationship (Low Risk)'
        }

    # Default: Standard risk
    return {
        'score': 20,
        'tier': 'standard',
        'reason': f'{country_name} - Standard Risk'
    }
```

**Step 2: Verify syntax**

Run: `cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && python -c "from services.risk_scoring import get_jurisdiction_score; print(get_jurisdiction_score('GB'))"`

Expected: `{'score': 0, 'tier': 'low', 'reason': 'United Kingdom - Established Relationship (Low Risk)'}`

**Step 3: Commit**

```bash
git add packages/client-onboarding/services/risk_scoring.py
git commit -m "feat(client-onboarding): add risk_scoring service with jurisdiction scoring"
```

---

## Task 2: Add PEP, sanctions, adverse media, and structure scoring

**Files:**
- Modify: `packages/client-onboarding/services/risk_scoring.py`

**Step 1: Add remaining scoring functions**

Add after `get_jurisdiction_score`:

```python
def get_pep_score(screening_results: list) -> dict:
    """
    Calculate PEP risk score from screening results.

    Args:
        screening_results: List of screening result dicts with has_pep_hit

    Returns:
        dict with score and reason
    """
    pep_hits = [r for r in screening_results if r.get('has_pep_hit')]

    if not pep_hits:
        return {
            'score': 0,
            'reason': 'No PEP matches detected'
        }

    # Check match details for PEP type
    # In production, would parse actual match data for domestic/foreign PEP classification
    # For POC, assume any PEP hit is domestic (score 60)
    pep_names = [r.get('name', 'Unknown') for r in pep_hits]

    return {
        'score': 60,
        'reason': f'Domestic PEP detected: {", ".join(pep_names[:3])}'
    }


def get_sanctions_score(screening_results: list) -> dict:
    """
    Calculate sanctions risk score from screening results.

    Args:
        screening_results: List of screening result dicts with has_sanctions_hit

    Returns:
        dict with score and reason
    """
    sanctions_hits = [r for r in screening_results if r.get('has_sanctions_hit')]

    if not sanctions_hits:
        return {
            'score': 0,
            'reason': 'No sanctions matches'
        }

    # Any sanctions hit is critical
    hit_names = [r.get('name', 'Unknown') for r in sanctions_hits]

    return {
        'score': 100,
        'reason': f'Sanctions match: {", ".join(hit_names[:3])}'
    }


def get_adverse_media_score(screening_results: list) -> dict:
    """
    Calculate adverse media risk score from screening results.

    Args:
        screening_results: List of screening result dicts with has_adverse_media

    Returns:
        dict with score and reason
    """
    adverse_hits = [r for r in screening_results if r.get('has_adverse_media')]

    if not adverse_hits:
        return {
            'score': 0,
            'reason': 'No adverse media found'
        }

    hit_count = len(adverse_hits)
    hit_names = [r.get('name', 'Unknown') for r in adverse_hits]

    # For POC, treat all adverse media as historical/resolved (score 30)
    # In production, would check dates and resolution status
    return {
        'score': 30,
        'reason': f'Historical adverse media: {", ".join(hit_names[:3])} ({hit_count} total)'
    }


def get_structure_score(entity_type: str) -> dict:
    """
    Calculate entity structure risk score.

    Args:
        entity_type: Type of entity (company, llp, lp, trust, foundation)

    Returns:
        dict with score and reason
    """
    if not entity_type:
        return {
            'score': 20,
            'reason': 'Entity type not specified'
        }

    entity_type = entity_type.lower().strip()

    structure_scores = {
        'company': (0, 'Company - Simple structure'),
        'ltd': (0, 'Limited Company - Simple structure'),
        'llc': (0, 'LLC - Simple structure'),
        'llp': (10, 'LLP - Partnership structure'),
        'lp': (20, 'LP - Limited Partnership'),
        'slp': (20, 'SLP - Scottish LP'),
        'trust': (40, 'Trust - Complex structure'),
        'foundation': (60, 'Foundation - Complex structure'),
        'pcc': (40, 'PCC - Protected Cell Company'),
        'icc': (40, 'ICC - Incorporated Cell Company'),
    }

    if entity_type in structure_scores:
        score, reason = structure_scores[entity_type]
        return {'score': score, 'reason': reason}

    return {
        'score': 20,
        'reason': f'{entity_type.upper()} - Standard structure'
    }
```

**Step 2: Verify syntax**

Run: `cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && python -c "from services.risk_scoring import get_structure_score; print(get_structure_score('lp'))"`

Expected: `{'score': 20, 'reason': 'LP - Limited Partnership'}`

**Step 3: Commit**

```bash
git add packages/client-onboarding/services/risk_scoring.py
git commit -m "feat(client-onboarding): add PEP, sanctions, adverse media, structure scoring"
```

---

## Task 3: Add main calculate_risk function

**Files:**
- Modify: `packages/client-onboarding/services/risk_scoring.py`

**Step 1: Add calculate_risk function at the end of the file**

```python
def calculate_risk(
    screening_results: list,
    jurisdiction: str = None,
    entity_type: str = None,
    onboarding_id: str = None
) -> dict:
    """
    Calculate overall risk score from all factors.

    Args:
        screening_results: List of screening result dicts
        jurisdiction: ISO country code for sponsor jurisdiction
        entity_type: Entity type (company, lp, trust, etc.)
        onboarding_id: Optional onboarding ID for persistence

    Returns:
        dict with score, rating, factors breakdown, edd_required, approval_level
    """
    # Calculate individual factor scores
    jurisdiction_result = get_jurisdiction_score(jurisdiction)
    pep_result = get_pep_score(screening_results)
    sanctions_result = get_sanctions_score(screening_results)
    adverse_result = get_adverse_media_score(screening_results)
    structure_result = get_structure_score(entity_type)

    # Calculate weighted contributions
    factors = {
        'jurisdiction': {
            'score': jurisdiction_result['score'],
            'weight': int(WEIGHTS['jurisdiction'] * 100),
            'contribution': round(jurisdiction_result['score'] * WEIGHTS['jurisdiction']),
            'reason': jurisdiction_result['reason']
        },
        'pep_status': {
            'score': pep_result['score'],
            'weight': int(WEIGHTS['pep_status'] * 100),
            'contribution': round(pep_result['score'] * WEIGHTS['pep_status']),
            'reason': pep_result['reason']
        },
        'sanctions': {
            'score': sanctions_result['score'],
            'weight': int(WEIGHTS['sanctions'] * 100),
            'contribution': round(sanctions_result['score'] * WEIGHTS['sanctions']),
            'reason': sanctions_result['reason']
        },
        'adverse_media': {
            'score': adverse_result['score'],
            'weight': int(WEIGHTS['adverse_media'] * 100),
            'contribution': round(adverse_result['score'] * WEIGHTS['adverse_media']),
            'reason': adverse_result['reason']
        },
        'entity_structure': {
            'score': structure_result['score'],
            'weight': int(WEIGHTS['entity_structure'] * 100),
            'contribution': round(structure_result['score'] * WEIGHTS['entity_structure']),
            'reason': structure_result['reason']
        }
    }

    # Calculate total score
    total_score = sum(f['contribution'] for f in factors.values())
    total_score = min(100, max(0, total_score))  # Clamp to 0-100

    # Determine rating and requirements
    if total_score < THRESHOLD_LOW:
        rating = 'low'
        edd_required = False
        approval_level = 'compliance'
    elif total_score < THRESHOLD_MEDIUM:
        rating = 'medium'
        edd_required = True
        approval_level = 'mlro'
    else:
        rating = 'high'
        edd_required = True
        approval_level = 'board'

    # Override: Any sanctions hit = High risk
    if sanctions_result['score'] >= 100:
        rating = 'high'
        edd_required = True
        approval_level = 'board'

    result = {
        'score': total_score,
        'rating': rating,
        'factors': factors,
        'edd_required': edd_required,
        'approval_level': approval_level
    }

    logger.info(f"Risk calculated: score={total_score}, rating={rating}, edd={edd_required}")

    return result
```

**Step 2: Verify the full calculation works**

Run: `cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && python -c "
from services.risk_scoring import calculate_risk
result = calculate_risk(
    screening_results=[{'name': 'John Smith', 'has_pep_hit': False, 'has_sanctions_hit': False, 'has_adverse_media': False}],
    jurisdiction='GB',
    entity_type='lp'
)
print(f'Score: {result[\"score\"]}, Rating: {result[\"rating\"]}')
"`

Expected: `Score: 5, Rating: low` (0 jurisdiction + 0 PEP + 0 sanctions + 0 adverse + 5 structure contribution)

**Step 3: Commit**

```bash
git add packages/client-onboarding/services/risk_scoring.py
git commit -m "feat(client-onboarding): add calculate_risk main function"
```

---

## Task 4: Export risk_scoring from services module

**Files:**
- Modify: `packages/client-onboarding/services/__init__.py`

**Step 1: Add risk_scoring exports**

Add to imports section:

```python
from .risk_scoring import (
    calculate_risk,
    get_jurisdiction_score,
    JURISDICTION_PROHIBITED,
    JURISDICTION_HIGH,
    THRESHOLD_LOW,
    THRESHOLD_MEDIUM
)
```

Add to `__all__` list:

```python
    # Risk Scoring
    'calculate_risk',
    'get_jurisdiction_score',
    'JURISDICTION_PROHIBITED',
    'JURISDICTION_HIGH',
    'THRESHOLD_LOW',
    'THRESHOLD_MEDIUM',
```

**Step 2: Verify import works**

Run: `cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && python -c "from services import calculate_risk; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add packages/client-onboarding/services/__init__.py
git commit -m "feat(client-onboarding): export risk_scoring from services module"
```

---

## Task 5: Integrate risk scoring into /api/screening/run

**Files:**
- Modify: `packages/client-onboarding/app.py`

**Step 1: Update api_run_screening to include risk calculation**

Find the `api_run_screening` function (around line 667) and update it.

Add import at top of function:
```python
from services.risk_scoring import calculate_risk
```

After the screening results are formatted (after line 701), add risk calculation:

```python
    # Calculate risk assessment
    jurisdiction = data.get('jurisdiction', 'GB')  # Default to UK
    entity_type = data.get('entity_type', 'company')
    onboarding_id = data.get('onboarding_id')

    risk_assessment = calculate_risk(
        screening_results=screening_results,
        jurisdiction=jurisdiction,
        entity_type=entity_type,
        onboarding_id=onboarding_id
    )

    # Save risk assessment to Sheets if we have an onboarding_id
    assessment_id = None
    if onboarding_id and onboarding_id != 'NEW':
        assessment_id = sheets_db.save_risk_assessment({
            'onboarding_id': onboarding_id,
            'risk_score': risk_assessment['score'],
            'risk_rating': risk_assessment['rating'],
            'risk_factors': risk_assessment['factors'],
            'edd_triggered': risk_assessment['edd_required']
        })
        risk_assessment['assessment_id'] = assessment_id
```

Update the return jsonify to include risk_assessment:

```python
    return jsonify({
        'status': 'ok',
        'demo_mode': demo_mode,
        'results': screening_results,
        'screened_count': len(screening_results),
        'risk_assessment': risk_assessment,
        'audit_trail': {
            'saved': audit_result.get('status') != 'error',
            'gdrive_demo_mode': gdrive_client.demo_mode
        }
    })
```

**Step 2: Verify app still loads**

Run: `cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && python -c "import app; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add packages/client-onboarding/app.py
git commit -m "feat(client-onboarding): integrate risk scoring into /api/screening/run"
```

---

## Task 6: Update phase4.html to display risk breakdown

**Files:**
- Modify: `packages/client-onboarding/templates/onboarding/phase4.html`

**Step 1: Update the Risk Assessment card HTML (around line 194)**

Replace the existing Risk Assessment card with:

```html
        <!-- Risk Assessment -->
        <div class="card mb-4" id="risk-card" style="display: none;">
            <div class="card-header">
                <i class="bi bi-speedometer2 me-2"></i>
                Risk Assessment
            </div>
            <div class="card-body">
                <!-- Summary Row -->
                <div class="row g-3 mb-4">
                    <div class="col-md-4">
                        <div class="text-center p-3 border rounded bg-light">
                            <div class="small text-muted mb-1">Overall Score</div>
                            <div class="display-5 fw-bold" id="overall-risk-score">-</div>
                            <span class="badge fs-6" id="overall-risk-badge">-</span>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="text-center p-3 border rounded">
                            <div class="small text-muted mb-1">EDD Required</div>
                            <div class="h4 mb-0" id="edd-status">-</div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="text-center p-3 border rounded">
                            <div class="small text-muted mb-1">Approval Level</div>
                            <div class="h4 mb-0" id="approval-level">-</div>
                        </div>
                    </div>
                </div>

                <!-- Factor Breakdown -->
                <h6 class="small text-uppercase text-muted mb-3">Factor Breakdown</h6>
                <div id="factor-breakdown">
                    <!-- Factors will be populated by JavaScript -->
                </div>

                <!-- AI Risk Analysis -->
                <div class="border rounded p-3 bg-light mt-4">
                    <div class="d-flex align-items-start gap-2">
                        <i class="bi bi-robot text-primary fs-5"></i>
                        <div>
                            <h6 class="mb-2">AI Risk Analysis</h6>
                            <p class="small text-muted mb-0" id="ai-analysis">
                                Run screening to generate risk analysis...
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
```

**Step 2: Update the JavaScript displayResults function**

Find the `displayResults` function and replace the risk score calculation section (around line 500-560) with:

```javascript
        // Display risk assessment from API response
        if (data.risk_assessment) {
            const risk = data.risk_assessment;

            // Update summary
            document.getElementById('overall-risk-score').textContent = risk.score;

            const overallBadge = document.getElementById('overall-risk-badge');
            if (risk.rating === 'low') {
                overallBadge.className = 'badge fs-6 bg-success';
                overallBadge.textContent = 'LOW RISK';
            } else if (risk.rating === 'medium') {
                overallBadge.className = 'badge fs-6 bg-warning text-dark';
                overallBadge.textContent = 'MEDIUM RISK';
            } else {
                overallBadge.className = 'badge fs-6 bg-danger';
                overallBadge.textContent = 'HIGH RISK';
            }

            // EDD and Approval
            const eddStatus = document.getElementById('edd-status');
            eddStatus.innerHTML = risk.edd_required
                ? '<span class="text-warning"><i class="bi bi-exclamation-triangle me-1"></i>Yes</span>'
                : '<span class="text-success"><i class="bi bi-check-circle me-1"></i>No</span>';

            const approvalLevel = document.getElementById('approval-level');
            const approvalMap = {
                'compliance': '<span class="text-success">Compliance</span>',
                'mlro': '<span class="text-warning">MLRO</span>',
                'board': '<span class="text-danger">MLRO + Board</span>'
            };
            approvalLevel.innerHTML = approvalMap[risk.approval_level] || risk.approval_level;

            // Factor breakdown
            const factorDiv = document.getElementById('factor-breakdown');
            const factorOrder = ['jurisdiction', 'pep_status', 'sanctions', 'adverse_media', 'entity_structure'];
            const factorLabels = {
                'jurisdiction': 'Jurisdiction',
                'pep_status': 'PEP Status',
                'sanctions': 'Sanctions',
                'adverse_media': 'Adverse Media',
                'entity_structure': 'Entity Structure'
            };

            factorDiv.innerHTML = factorOrder.map(key => {
                const f = risk.factors[key];
                const barWidth = f.score;
                let barColor = 'bg-success';
                if (f.score >= 70) barColor = 'bg-danger';
                else if (f.score >= 40) barColor = 'bg-warning';

                return `
                    <div class="mb-3">
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <span class="small fw-medium">${factorLabels[key]} (${f.weight}%)</span>
                            <span class="small text-muted">${f.score} → ${f.contribution}pts</span>
                        </div>
                        <div class="progress" style="height: 8px;">
                            <div class="progress-bar ${barColor}" style="width: ${barWidth}%"></div>
                        </div>
                        <div class="small text-muted mt-1">${f.reason}</div>
                    </div>
                `;
            }).join('');

            // AI Analysis
            let analysis = '';
            if (risk.rating === 'high') {
                analysis = `<strong class="text-danger">High Risk Alert:</strong> Overall risk score of ${risk.score} exceeds threshold. ${risk.edd_required ? 'Enhanced Due Diligence is required.' : ''} Approval required from: ${risk.approval_level.toUpperCase()}.`;
                document.getElementById('edd-trigger-card').style.display = 'block';
            } else if (risk.rating === 'medium') {
                analysis = `<strong class="text-warning">Medium Risk:</strong> Risk score of ${risk.score} indicates elevated risk factors. ${risk.edd_required ? 'EDD recommended.' : ''} MLRO approval required before proceeding.`;
                document.getElementById('edd-trigger-card').style.display = 'block';
            } else {
                analysis = `<strong class="text-success">Low Risk Profile:</strong> Risk score of ${risk.score} is within acceptable range. Standard onboarding pathway recommended. Compliance approval sufficient.`;
            }
            document.getElementById('ai-analysis').innerHTML = analysis;
        }
```

**Step 3: Update the fetch call to include jurisdiction and entity_type**

In the fetch call (around line 367), update the body to include:

```javascript
                body: JSON.stringify({
                    entities,
                    sponsor_name: sponsorName,
                    fund_name: fundName,
                    jurisdiction: 'GB',  // TODO: Get from session/form
                    entity_type: 'lp',   // TODO: Get from session/form
                    onboarding_id: '{{ onboarding_id }}'
                })
```

**Step 4: Update displayResults call to pass full data**

Change the displayResults call (around line 385) from:
```javascript
displayResults(data.results, data.demo_mode, data.audit_trail);
```

To:
```javascript
displayResults(data);
```

And update the function signature:
```javascript
function displayResults(data) {
    const results = data.results;
    const demoMode = data.demo_mode;
    const auditTrail = data.audit_trail;
```

**Step 5: Commit**

```bash
git add packages/client-onboarding/templates/onboarding/phase4.html
git commit -m "feat(client-onboarding): update phase4.html to display risk breakdown from API"
```

---

## Task 7: Final verification

**Step 1: Verify app loads**

Run: `cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && python -c "import app; print('OK')"`

Expected: `OK`

**Step 2: Test risk calculation API**

Run: `cd /Users/robertdaykin/invoice-tracker/packages/client-onboarding && python -c "
from services.risk_scoring import calculate_risk

# Test low risk scenario
result = calculate_risk(
    screening_results=[
        {'name': 'John Smith', 'has_pep_hit': False, 'has_sanctions_hit': False, 'has_adverse_media': False}
    ],
    jurisdiction='GB',
    entity_type='company'
)
print(f'Low risk test: score={result[\"score\"]}, rating={result[\"rating\"]}')

# Test medium risk scenario (PEP)
result = calculate_risk(
    screening_results=[
        {'name': 'Boris Johnson', 'has_pep_hit': True, 'has_sanctions_hit': False, 'has_adverse_media': False}
    ],
    jurisdiction='GB',
    entity_type='lp'
)
print(f'Medium risk test: score={result[\"score\"]}, rating={result[\"rating\"]}')

# Test high risk scenario (sanctions)
result = calculate_risk(
    screening_results=[
        {'name': 'Test Person', 'has_pep_hit': False, 'has_sanctions_hit': True, 'has_adverse_media': False}
    ],
    jurisdiction='IR',
    entity_type='trust'
)
print(f'High risk test: score={result[\"score\"]}, rating={result[\"rating\"]}')
"
`

Expected output:
```
Low risk test: score=0, rating=low
Medium risk test: score=17, rating=low
High risk test: score=59, rating=high
```

(Note: High risk due to sanctions override)

**Step 3: Commit any final changes**

```bash
git status
# If clean, done. If changes:
git add -A
git commit -m "chore(client-onboarding): final cleanup for risk scoring"
```

---

## Summary

**Files created:**
- `services/risk_scoring.py` - Risk calculation service with JFSC/FATF jurisdiction tiers

**Files modified:**
- `services/__init__.py` - Export risk_scoring
- `app.py` - Integrate into /api/screening/run
- `templates/onboarding/phase4.html` - Display risk breakdown

**Test scenarios:**
- Low risk: UK company, no hits → score ~0-5
- Medium risk: UK LP with PEP → score ~15-20 (but PEP triggers EDD)
- High risk: Iran trust with sanctions → score ~60+ (sanctions override to high)

---

*End of Implementation Plan*
