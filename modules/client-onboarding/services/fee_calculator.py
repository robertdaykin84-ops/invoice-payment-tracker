"""
Fee Calculator Service
Calculates dynamic fees based on fund size, services selected, and structure complexity.
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Fee tiers based on fund size (AUM in USD)
FEE_TIERS = [
    {'name': 'Tier 1', 'min': 0, 'max': 100_000_000, 'admin_bps': 20},           # Up to $100M: 20 bps
    {'name': 'Tier 2', 'min': 100_000_000, 'max': 250_000_000, 'admin_bps': 18}, # $100M-$250M: 18 bps
    {'name': 'Tier 3', 'min': 250_000_000, 'max': 500_000_000, 'admin_bps': 15}, # $250M-$500M: 15 bps
    {'name': 'Tier 4', 'min': 500_000_000, 'max': None, 'admin_bps': 12},        # $500M+: 12 bps
]

# Service fees (annual unless otherwise noted)
SERVICE_FEES = {
    'nav': {
        'name': 'NAV Calculation',
        'annual': 30000,
        'description': 'Monthly/Quarterly valuations'
    },
    'investor': {
        'name': 'Investor Services',
        'annual': 500,
        'per_unit': 'investor',
        'description': 'Investor communications & reporting'
    },
    'accounting': {
        'name': 'Fund Accounting',
        'annual': 25000,
        'description': 'Management & performance fee calculations'
    },
    'aml': {
        'name': 'AML/KYC Services',
        'annual': 15000,
        'description': 'Ongoing investor due diligence'
    },
    'ta': {
        'name': 'Transfer Agency',
        'annual': 20000,
        'description': 'Subscription & redemption processing'
    },
    'reg': {
        'name': 'Regulatory Filings',
        'annual': 8000,
        'description': 'JFSC notifications & reporting'
    },
    'director': {
        'name': 'Director Services (GP)',
        'annual': 15000,
        'per_unit': 'director',
        'description': 'Independent director services'
    },
    'cosec': {
        'name': 'Company Secretary',
        'annual': 8000,
        'description': 'GP company secretarial services'
    }
}

# Setup fees (one-time)
SETUP_FEES = {
    'fund_onboarding': {
        'name': 'Fund Onboarding & Setup',
        'amount': 15000,
        'description': 'Initial fund setup and configuration'
    },
    'gp_incorporation': {
        'name': 'GP Incorporation (Jersey)',
        'amount': 5000,
        'description': 'General Partner entity incorporation'
    },
    'initial_aml': {
        'name': 'Initial AML/KYC (Sponsor)',
        'amount': 0,
        'description': 'Included in onboarding'
    }
}

# Complexity multipliers
COMPLEXITY_MULTIPLIERS = {
    'low': 1.0,      # Simple structure
    'medium': 1.15,  # Moderate complexity (multiple feeders, etc.)
    'high': 1.30     # Complex (multi-tier, co-invest vehicles, etc.)
}


def get_tier_for_fund_size(fund_size: int) -> dict:
    """Determine the appropriate fee tier based on fund size."""
    for tier in FEE_TIERS:
        if tier['max'] is None:
            return tier
        if tier['min'] <= fund_size < tier['max']:
            return tier
    return FEE_TIERS[-1]  # Default to highest tier


def calculate_admin_fee(fund_size: int) -> dict:
    """Calculate administration fee based on fund size."""
    tier = get_tier_for_fund_size(fund_size)
    bps = tier['admin_bps']
    annual_fee = int(fund_size * bps / 10000)

    return {
        'tier': tier['name'],
        'bps': bps,
        'annual_fee': annual_fee,
        'fund_size': fund_size
    }


def calculate_service_fee(service_id: str, num_investors: int = 50, num_directors: int = 2) -> dict:
    """Calculate fee for a specific service."""
    if service_id not in SERVICE_FEES:
        return {'service_id': service_id, 'annual': 0, 'error': 'Unknown service'}

    service = SERVICE_FEES[service_id]
    annual = service['annual']

    # Apply per-unit multipliers
    if service.get('per_unit') == 'investor':
        annual = annual * num_investors
    elif service.get('per_unit') == 'director':
        annual = annual * num_directors

    return {
        'service_id': service_id,
        'name': service['name'],
        'description': service['description'],
        'annual': annual,
        'per_unit': service.get('per_unit')
    }


def calculate_fees(
    fund_size: int,
    services: List[str],
    num_investors: int = 50,
    num_directors: int = 2,
    complexity: str = 'low',
    include_setup: bool = True
) -> dict:
    """
    Calculate total fees based on fund parameters.

    Args:
        fund_size: Target fund size in USD
        services: List of service IDs (e.g., ['nav', 'investor', 'accounting'])
        num_investors: Estimated number of investors (default 50)
        num_directors: Number of GP directors (default 2)
        complexity: Structure complexity ('low', 'medium', 'high')
        include_setup: Whether to include one-time setup fees

    Returns:
        dict with annual_total, setup_total, breakdown, effective_rate
    """
    logger.info(f"Calculating fees: fund_size={fund_size}, services={services}, "
                f"investors={num_investors}, directors={num_directors}, complexity={complexity}")

    # Get complexity multiplier
    multiplier = COMPLEXITY_MULTIPLIERS.get(complexity, 1.0)

    # Calculate service fees
    service_breakdown = []
    services_total = 0

    for service_id in services:
        fee = calculate_service_fee(service_id, num_investors, num_directors)
        if fee.get('annual', 0) > 0:
            adjusted_fee = int(fee['annual'] * multiplier)
            service_breakdown.append({
                'service_id': service_id,
                'name': fee['name'],
                'description': fee.get('description', ''),
                'base_fee': fee['annual'],
                'adjusted_fee': adjusted_fee,
                'per_unit': fee.get('per_unit')
            })
            services_total += adjusted_fee

    # Calculate setup fees
    setup_breakdown = []
    setup_total = 0

    if include_setup:
        for setup_id, setup in SETUP_FEES.items():
            setup_breakdown.append({
                'setup_id': setup_id,
                'name': setup['name'],
                'description': setup['description'],
                'amount': setup['amount']
            })
            setup_total += setup['amount']

    # Calculate effective rate (bps on AUM)
    effective_bps = (services_total / fund_size * 10000) if fund_size > 0 else 0

    # Get tier info
    tier = get_tier_for_fund_size(fund_size)

    result = {
        'fund_size': fund_size,
        'fund_size_formatted': f"${fund_size:,.0f}",
        'num_investors': num_investors,
        'num_directors': num_directors,
        'complexity': complexity,
        'complexity_multiplier': multiplier,
        'tier': tier['name'],
        'tier_bps': tier['admin_bps'],
        'annual_total': services_total,
        'annual_total_formatted': f"£{services_total:,.0f}",
        'setup_total': setup_total,
        'setup_total_formatted': f"£{setup_total:,.0f}",
        'year1_total': services_total + setup_total,
        'year1_total_formatted': f"£{services_total + setup_total:,.0f}",
        'effective_bps': round(effective_bps, 2),
        'service_breakdown': service_breakdown,
        'setup_breakdown': setup_breakdown
    }

    logger.info(f"Fee calculation result: annual={services_total}, setup={setup_total}, "
                f"effective_bps={effective_bps:.2f}")

    return result


def get_available_services() -> List[dict]:
    """Return list of all available services with their base fees."""
    services = []
    for service_id, service in SERVICE_FEES.items():
        services.append({
            'id': service_id,
            'name': service['name'],
            'description': service['description'],
            'base_annual': service['annual'],
            'per_unit': service.get('per_unit')
        })
    return services


def get_setup_fees() -> List[dict]:
    """Return list of all setup fees."""
    fees = []
    for setup_id, setup in SETUP_FEES.items():
        fees.append({
            'id': setup_id,
            'name': setup['name'],
            'description': setup['description'],
            'amount': setup['amount']
        })
    return fees
