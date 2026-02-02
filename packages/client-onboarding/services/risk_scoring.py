"""
Risk Scoring Service for Client Onboarding

Implements JFSC/FATF-based jurisdiction risk scoring and comprehensive
risk assessment for AML/KYC compliance.
"""

from typing import Optional

# =============================================================================
# JURISDICTION RISK CONSTANTS (JFSC/FATF based)
# =============================================================================

# FATF Black List - Prohibited (score 100)
JURISDICTION_PROHIBITED = {'KP', 'IR', 'MM'}  # North Korea, Iran, Myanmar

# FATF Grey List - High Risk (score 80)
JURISDICTION_HIGH = {
    'DZ', 'AO', 'BO', 'BG', 'CM', 'CI', 'CD', 'HT', 'KE', 'LA',
    'LB', 'MC', 'NA', 'NP', 'SS', 'SY', 'VE', 'VN', 'VG', 'YE'
}

# Offshore Financial Centers - Elevated (score 50)
JURISDICTION_ELEVATED = {
    'KY', 'BM', 'IM', 'PA', 'SC', 'MU', 'BS', 'BB', 'AG', 'LC', 'VC', 'TC', 'AI'
}

# Low Risk - Established (score 0)
JURISDICTION_LOW = {'GB', 'JE', 'GG', 'IE'}

# Country name mapping for human-readable output
JURISDICTION_NAMES = {
    # Prohibited
    'KP': 'North Korea',
    'IR': 'Iran',
    'MM': 'Myanmar',
    # High Risk
    'DZ': 'Algeria',
    'AO': 'Angola',
    'BO': 'Bolivia',
    'BG': 'Bulgaria',
    'CM': 'Cameroon',
    'CI': 'Côte d\'Ivoire',
    'CD': 'Democratic Republic of the Congo',
    'HT': 'Haiti',
    'KE': 'Kenya',
    'LA': 'Laos',
    'LB': 'Lebanon',
    'MC': 'Monaco',
    'NA': 'Namibia',
    'NP': 'Nepal',
    'SS': 'South Sudan',
    'SY': 'Syria',
    'VE': 'Venezuela',
    'VN': 'Vietnam',
    'VG': 'British Virgin Islands',
    'YE': 'Yemen',
    # Elevated
    'KY': 'Cayman Islands',
    'BM': 'Bermuda',
    'IM': 'Isle of Man',
    'PA': 'Panama',
    'SC': 'Seychelles',
    'MU': 'Mauritius',
    'BS': 'Bahamas',
    'BB': 'Barbados',
    'AG': 'Antigua and Barbuda',
    'LC': 'Saint Lucia',
    'VC': 'Saint Vincent and the Grenadines',
    'TC': 'Turks and Caicos Islands',
    'AI': 'Anguilla',
    # Low Risk
    'GB': 'United Kingdom',
    'JE': 'Jersey',
    'GG': 'Guernsey',
    'IE': 'Ireland',
}

# =============================================================================
# RISK WEIGHTS AND THRESHOLDS
# =============================================================================

WEIGHTS = {
    'jurisdiction': 0.25,
    'pep_status': 0.25,
    'sanctions': 0.30,
    'adverse_media': 0.10,
    'entity_structure': 0.10
}

THRESHOLD_LOW = 40      # 0-39 = Low
THRESHOLD_MEDIUM = 70   # 40-69 = Medium, 70+ = High

# Entity structure risk scores
ENTITY_STRUCTURE_SCORES = {
    'company': 0,
    'llp': 10,
    'lp': 20,
    'trust': 40,
    'foundation': 60
}


# =============================================================================
# SCORING FUNCTIONS
# =============================================================================

def get_jurisdiction_score(country_code: str) -> dict:
    """
    Calculate risk score for a jurisdiction based on FATF lists.

    Args:
        country_code: ISO 3166-1 alpha-2 country code (e.g., 'GB', 'KP')

    Returns:
        dict with 'score', 'tier', and 'reason'
    """
    if not country_code:
        return {
            'score': 20,
            'tier': 'standard',
            'reason': 'No jurisdiction specified - Standard Risk applied'
        }

    code = country_code.upper().strip()
    country_name = JURISDICTION_NAMES.get(code, code)

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
            'reason': f'{country_name} - Offshore Financial Center (Elevated Risk)'
        }

    if code in JURISDICTION_LOW:
        return {
            'score': 0,
            'tier': 'low',
            'reason': f'{country_name} - Established Relationship (Low Risk)'
        }

    # Standard risk for all other jurisdictions
    return {
        'score': 20,
        'tier': 'standard',
        'reason': f'{country_name} - Standard Risk'
    }


def get_pep_score(screening_results: list) -> dict:
    """
    Calculate PEP (Politically Exposed Person) risk score from screening results.

    Args:
        screening_results: List of screening result dicts with 'has_pep_hit' field

    Returns:
        dict with 'score' and 'reason'
    """
    if not screening_results:
        return {
            'score': 0,
            'reason': 'No screening results provided'
        }

    # Check for any PEP hits in screening results
    for result in screening_results:
        if result.get('has_pep_hit'):
            return {
                'score': 60,
                'reason': 'Domestic PEP match identified'
            }

    return {
        'score': 0,
        'reason': 'No PEP matches found'
    }


def get_sanctions_score(screening_results: list) -> dict:
    """
    Calculate sanctions risk score from screening results.

    Args:
        screening_results: List of screening result dicts with 'has_sanctions_hit' field

    Returns:
        dict with 'score' and 'reason'
    """
    if not screening_results:
        return {
            'score': 0,
            'reason': 'No screening results provided'
        }

    # Check for any sanctions hits
    for result in screening_results:
        if result.get('has_sanctions_hit'):
            return {
                'score': 100,
                'reason': 'Sanctions match identified - Immediate escalation required'
            }

    return {
        'score': 0,
        'reason': 'Sanctions screening clear'
    }


def get_adverse_media_score(screening_results: list) -> dict:
    """
    Calculate adverse media risk score from screening results.

    Args:
        screening_results: List of screening result dicts with 'has_adverse_media' field

    Returns:
        dict with 'score' and 'reason'
    """
    if not screening_results:
        return {
            'score': 0,
            'reason': 'No screening results provided'
        }

    # Check for adverse media hits
    for result in screening_results:
        if result.get('has_adverse_media'):
            return {
                'score': 30,
                'reason': 'Historical adverse media identified'
            }

    return {
        'score': 0,
        'reason': 'No adverse media found'
    }


def get_structure_score(entity_type: str) -> dict:
    """
    Calculate risk score based on entity structure type.

    Args:
        entity_type: Type of entity (company, llp, lp, trust, foundation)

    Returns:
        dict with 'score' and 'reason'
    """
    if not entity_type:
        return {
            'score': 0,
            'reason': 'No entity type specified - Default (Company) applied'
        }

    entity_lower = entity_type.lower().strip()

    structure_descriptions = {
        'company': 'Standard Company Structure',
        'llp': 'Limited Liability Partnership',
        'lp': 'Limited Partnership',
        'trust': 'Trust Structure',
        'foundation': 'Foundation Structure'
    }

    if entity_lower in ENTITY_STRUCTURE_SCORES:
        score = ENTITY_STRUCTURE_SCORES[entity_lower]
        description = structure_descriptions.get(entity_lower, entity_lower.upper())

        if score == 0:
            risk_level = 'Low complexity'
        elif score <= 20:
            risk_level = 'Moderate complexity'
        else:
            risk_level = 'High complexity'

        return {
            'score': score,
            'reason': f'{description} - {risk_level}'
        }

    # Unknown entity type defaults to 0
    return {
        'score': 0,
        'reason': f'Unknown entity type ({entity_type}) - Default risk applied'
    }


# =============================================================================
# MAIN RISK CALCULATION FUNCTION
# =============================================================================

def calculate_risk(
    screening_results: list,
    jurisdiction: str = None,
    entity_type: str = None,
    onboarding_id: str = None
) -> dict:
    """
    Calculate comprehensive risk score for client onboarding.

    Args:
        screening_results: List of screening result dicts containing:
            - has_pep_hit: bool
            - has_sanctions_hit: bool
            - has_adverse_media: bool
        jurisdiction: ISO 3166-1 alpha-2 country code
        entity_type: Type of entity (company, llp, lp, trust, foundation)
        onboarding_id: Optional reference ID for audit trail

    Returns:
        dict containing:
            - score: Overall weighted risk score (0-100)
            - rating: 'low', 'medium', or 'high'
            - factors: Detailed breakdown of each risk factor
            - edd_required: Whether Enhanced Due Diligence is required
            - approval_level: Required approval level ('compliance', 'mlro', 'board')
    """
    # Calculate individual factor scores
    jurisdiction_result = get_jurisdiction_score(jurisdiction)
    pep_result = get_pep_score(screening_results)
    sanctions_result = get_sanctions_score(screening_results)
    adverse_media_result = get_adverse_media_score(screening_results)
    structure_result = get_structure_score(entity_type)

    # Build factors dictionary with weighted contributions
    factors = {
        'jurisdiction': {
            'score': jurisdiction_result['score'],
            'weight': int(WEIGHTS['jurisdiction'] * 100),
            'contribution': round(jurisdiction_result['score'] * WEIGHTS['jurisdiction'], 2),
            'reason': jurisdiction_result['reason']
        },
        'pep_status': {
            'score': pep_result['score'],
            'weight': int(WEIGHTS['pep_status'] * 100),
            'contribution': round(pep_result['score'] * WEIGHTS['pep_status'], 2),
            'reason': pep_result['reason']
        },
        'sanctions': {
            'score': sanctions_result['score'],
            'weight': int(WEIGHTS['sanctions'] * 100),
            'contribution': round(sanctions_result['score'] * WEIGHTS['sanctions'], 2),
            'reason': sanctions_result['reason']
        },
        'adverse_media': {
            'score': adverse_media_result['score'],
            'weight': int(WEIGHTS['adverse_media'] * 100),
            'contribution': round(adverse_media_result['score'] * WEIGHTS['adverse_media'], 2),
            'reason': adverse_media_result['reason']
        },
        'entity_structure': {
            'score': structure_result['score'],
            'weight': int(WEIGHTS['entity_structure'] * 100),
            'contribution': round(structure_result['score'] * WEIGHTS['entity_structure'], 2),
            'reason': structure_result['reason']
        }
    }

    # Calculate total weighted score
    total_score = sum(factor['contribution'] for factor in factors.values())
    total_score = round(total_score, 2)

    # Determine rating based on thresholds
    if total_score < THRESHOLD_LOW:
        rating = 'low'
        approval_level = 'compliance'
        edd_required = False
    elif total_score < THRESHOLD_MEDIUM:
        rating = 'medium'
        approval_level = 'mlro'
        edd_required = True
    else:
        rating = 'high'
        approval_level = 'board'
        edd_required = True

    # Override: Any sanctions hit = high risk regardless of score
    if sanctions_result['score'] > 0:
        rating = 'high'
        approval_level = 'board'
        edd_required = True

    # Override: Prohibited jurisdictions = high risk regardless of score
    if jurisdiction_result.get('tier') == 'prohibited':
        rating = 'high'
        approval_level = 'board'
        edd_required = True

    result = {
        'score': total_score,
        'rating': rating,
        'factors': factors,
        'edd_required': edd_required,
        'approval_level': approval_level
    }

    # Include onboarding_id if provided for audit trail
    if onboarding_id:
        result['onboarding_id'] = onboarding_id

    return result
