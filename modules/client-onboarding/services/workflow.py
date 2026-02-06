"""
Workflow Automation Service for Client Onboarding

Provides automatic phase progression, task assignment, and deadline tracking.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Phase definitions
PHASES = {
    1: {'name': 'Enquiry', 'days_allowed': 2, 'auto_assign_role': 'bd'},
    2: {'name': 'Sponsor', 'days_allowed': 5, 'auto_assign_role': 'compliance'},
    3: {'name': 'Fund', 'days_allowed': 5, 'auto_assign_role': 'compliance'},
    4: {'name': 'Screening', 'days_allowed': 3, 'auto_assign_role': 'compliance'},
    5: {'name': 'EDD', 'days_allowed': 10, 'auto_assign_role': 'compliance'},
    6: {'name': 'Approval', 'days_allowed': 5, 'auto_assign_role': 'mlro'},
    7: {'name': 'Commercial', 'days_allowed': 3, 'auto_assign_role': 'bd'},
    8: {'name': 'Complete', 'days_allowed': 0, 'auto_assign_role': None}
}

# Phase completion rules
PHASE_COMPLETION_RULES = {
    1: ['enquiry_reviewed'],
    2: ['sponsor_data_complete', 'sponsor_verified'],
    3: ['fund_data_complete', 'fund_structure_verified'],
    4: ['screening_complete', 'risk_assessed'],
    5: ['edd_complete'],  # Only if required
    6: ['approval_granted'],
    7: ['commercial_terms_agreed'],
    8: []  # Final phase
}

# Status workflow
STATUS_TRANSITIONS = {
    'draft': ['in_progress'],
    'in_progress': ['pending_mlro', 'pending_board', 'on_hold', 'approved', 'rejected'],
    'pending_mlro': ['approved', 'rejected', 'in_progress'],
    'pending_board': ['approved', 'rejected', 'pending_mlro'],
    'on_hold': ['in_progress', 'rejected'],
    'approved': [],  # Terminal
    'rejected': []   # Terminal
}


def get_phase_info(phase_num: int) -> Dict[str, Any]:
    """Get information about a phase."""
    if phase_num not in PHASES:
        return {'name': 'Unknown', 'days_allowed': 0, 'auto_assign_role': None}
    return PHASES[phase_num]


def get_next_phase(current_phase: int) -> Optional[int]:
    """Get the next phase number."""
    if current_phase < 8:
        return current_phase + 1
    return None


def calculate_deadline(phase_num: int, start_date: datetime = None) -> datetime:
    """Calculate deadline for a phase."""
    if start_date is None:
        start_date = datetime.now()

    days_allowed = PHASES.get(phase_num, {}).get('days_allowed', 5)
    return start_date + timedelta(days=days_allowed)


def check_phase_completion(
    phase_num: int,
    completed_tasks: List[str],
    risk_assessment: Dict = None
) -> Dict[str, Any]:
    """
    Check if a phase can be marked complete.

    Args:
        phase_num: Current phase number
        completed_tasks: List of completed task identifiers
        risk_assessment: Risk assessment result (for EDD check)

    Returns:
        Dict with 'can_complete', 'missing_tasks', and 'next_phase'
    """
    required_tasks = PHASE_COMPLETION_RULES.get(phase_num, [])

    # Special case: EDD phase only required if edd_required is True
    if phase_num == 5:
        if risk_assessment and not risk_assessment.get('edd_required'):
            # EDD not required, auto-complete
            return {
                'can_complete': True,
                'missing_tasks': [],
                'next_phase': 6,
                'message': 'EDD not required, phase auto-completed'
            }

    missing = [task for task in required_tasks if task not in completed_tasks]

    can_complete = len(missing) == 0

    return {
        'can_complete': can_complete,
        'missing_tasks': missing,
        'next_phase': get_next_phase(phase_num) if can_complete else None,
        'message': 'Phase complete' if can_complete else f'Missing: {", ".join(missing)}'
    }


def can_transition_status(current_status: str, new_status: str) -> bool:
    """Check if a status transition is allowed."""
    allowed = STATUS_TRANSITIONS.get(current_status, [])
    return new_status in allowed


def determine_approval_routing(risk_assessment: Dict) -> Dict[str, Any]:
    """
    Determine where to route for approval based on risk.

    Args:
        risk_assessment: Risk assessment result

    Returns:
        Dict with routing info
    """
    approval_level = risk_assessment.get('approval_level', 'compliance')

    if approval_level == 'board':
        return {
            'route_to': 'board',
            'status': 'pending_board',
            'approvers': ['mlro', 'board'],
            'message': 'High risk - requires MLRO and Board approval'
        }
    elif approval_level == 'mlro':
        return {
            'route_to': 'mlro',
            'status': 'pending_mlro',
            'approvers': ['mlro'],
            'message': 'Medium risk - requires MLRO approval'
        }
    else:
        return {
            'route_to': 'compliance',
            'status': 'in_progress',
            'approvers': ['compliance'],
            'message': 'Low risk - compliance can approve'
        }


def get_auto_assignee(phase_num: int, risk_level: str = 'low') -> Optional[str]:
    """
    Get the role that should be auto-assigned for a phase.

    Args:
        phase_num: Phase number
        risk_level: Risk level (affects assignment)

    Returns:
        Role identifier or None
    """
    phase_info = PHASES.get(phase_num, {})
    base_role = phase_info.get('auto_assign_role')

    # High risk cases go to MLRO for certain phases
    if risk_level == 'high' and phase_num in [4, 5, 6]:
        return 'mlro'

    return base_role


def check_overdue(
    onboardings: List[Dict],
    current_date: datetime = None
) -> List[Dict]:
    """
    Check for overdue onboardings.

    Args:
        onboardings: List of onboarding records
        current_date: Date to check against (defaults to now)

    Returns:
        List of overdue onboardings with days overdue
    """
    if current_date is None:
        current_date = datetime.now()

    overdue = []

    for onb in onboardings:
        status = onb.get('status', '')
        if status in ['approved', 'rejected']:
            continue  # Skip completed

        phase = onb.get('current_phase', 1)
        phase_started = onb.get('phase_started_at')

        if phase_started:
            try:
                started = datetime.fromisoformat(phase_started)
                deadline = calculate_deadline(phase, started)

                if current_date > deadline:
                    days_overdue = (current_date - deadline).days
                    overdue.append({
                        **onb,
                        'days_overdue': days_overdue,
                        'deadline': deadline.isoformat()
                    })
            except (ValueError, TypeError):
                pass

    return sorted(overdue, key=lambda x: x['days_overdue'], reverse=True)


def generate_workflow_summary(onboarding: Dict, risk_assessment: Dict = None) -> Dict[str, Any]:
    """
    Generate a workflow summary for an onboarding.

    Args:
        onboarding: Onboarding record
        risk_assessment: Risk assessment result

    Returns:
        Dict with workflow status, next steps, and recommendations
    """
    current_phase = onboarding.get('current_phase', 1)
    status = onboarding.get('status', 'draft')

    phase_info = get_phase_info(current_phase)
    next_phase = get_next_phase(current_phase)

    summary = {
        'current_phase': {
            'number': current_phase,
            'name': phase_info['name'],
            'days_allowed': phase_info['days_allowed']
        },
        'status': status,
        'next_steps': [],
        'recommendations': []
    }

    if next_phase:
        summary['next_phase'] = {
            'number': next_phase,
            'name': PHASES[next_phase]['name']
        }

    # Add next steps based on phase
    if current_phase == 1:
        summary['next_steps'] = ['Review enquiry details', 'Accept or decline enquiry']
    elif current_phase == 2:
        summary['next_steps'] = ['Verify sponsor information', 'Complete due diligence checks']
    elif current_phase == 3:
        summary['next_steps'] = ['Verify fund structure', 'Confirm fund documentation']
    elif current_phase == 4:
        summary['next_steps'] = ['Run PEP/Sanctions screening', 'Review matches', 'Complete risk assessment']
    elif current_phase == 5:
        summary['next_steps'] = ['Complete enhanced due diligence', 'Document findings']
    elif current_phase == 6:
        if risk_assessment:
            routing = determine_approval_routing(risk_assessment)
            summary['next_steps'] = [f'Obtain {routing["route_to"].upper()} approval']
            summary['routing'] = routing
        else:
            summary['next_steps'] = ['Complete risk assessment first']
    elif current_phase == 7:
        summary['next_steps'] = ['Agree commercial terms', 'Prepare engagement documentation']
    elif current_phase == 8:
        summary['next_steps'] = ['Onboarding complete']
        summary['recommendations'].append('Archive documentation to audit folder')

    return summary


# Workflow events for logging/auditing
WORKFLOW_EVENTS = {
    'phase_started': 'Phase {phase} started',
    'phase_completed': 'Phase {phase} completed',
    'status_changed': 'Status changed from {old_status} to {new_status}',
    'assigned': 'Assigned to {assignee}',
    'approval_requested': 'Approval requested from {approver}',
    'approved': 'Approved by {approved_by}',
    'rejected': 'Rejected by {rejected_by}: {reason}'
}
