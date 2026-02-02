"""
Client Onboarding System - Main Application
JFSC-compliant client onboarding for Jersey fund administration
"""

import os
import logging
from datetime import datetime
from functools import wraps
from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, flash, session, g
)
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins=['https://coreworker-landing.onrender.com', 'http://localhost:*'])

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24))
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV', 'development') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Demo mode for POC
DEMO_MODE = os.environ.get('DEMO_MODE', 'true').lower() == 'true'

# User roles
ROLES = {
    'bd': {'name': 'Business Development', 'can_approve': False},
    'compliance': {'name': 'Compliance Analyst', 'can_approve': 'standard'},
    'mlro': {'name': 'MLRO', 'can_approve': 'all'},
    'admin': {'name': 'Administrator', 'can_approve': False}
}

# Demo users for POC
DEMO_USERS = {
    'bd_user': {'name': 'Sarah Johnson', 'role': 'bd', 'email': 'sarah.johnson@example.com'},
    'compliance_user': {'name': 'James Smith', 'role': 'compliance', 'email': 'james.smith@example.com'},
    'mlro_user': {'name': 'Emma Williams', 'role': 'mlro', 'email': 'emma.williams@example.com'},
    'admin_user': {'name': 'Michael Brown', 'role': 'admin', 'email': 'michael.brown@example.com'}
}


# ========== Security Headers ==========

@app.after_request
def add_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://sheets.googleapis.com https://www.googleapis.com https://drive.googleapis.com; "
        "frame-ancestors 'self';"
    )
    return response


# ========== Context Processors ==========

@app.context_processor
def inject_globals():
    """Inject global variables into all templates"""
    user = get_current_user()
    return {
        'demo_mode': DEMO_MODE,
        'current_user': user,
        'current_role': ROLES.get(user['role']) if user else None,
        'roles': ROLES,
        'now': datetime.now()
    }


# ========== Authentication ==========

def get_current_user():
    """Get current user from session"""
    user_id = session.get('user_id')
    if user_id and user_id in DEMO_USERS:
        return {**DEMO_USERS[user_id], 'id': user_id}
    return None


def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if DEMO_MODE and not session.get('user_id'):
            # Auto-login as BD user for demo
            session['user_id'] = 'bd_user'

        if not get_current_user():
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    """Decorator to require specific roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user or user['role'] not in roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ========== Routes ==========

@app.route('/')
def index():
    """Landing page / redirect to dashboard"""
    if get_current_user():
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        if user_id in DEMO_USERS:
            session['user_id'] = user_id
            flash(f'Welcome, {DEMO_USERS[user_id]["name"]}!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid user selection.', 'danger')

    return render_template('login.html', users=DEMO_USERS)


@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/switch-user/<user_id>')
def switch_user(user_id):
    """Quick user switch for demo"""
    if DEMO_MODE and user_id in DEMO_USERS:
        session['user_id'] = user_id
        flash(f'Switched to {DEMO_USERS[user_id]["name"]} ({ROLES[DEMO_USERS[user_id]["role"]]["name"]})', 'info')
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard - role-specific view"""
    user = get_current_user()

    # Mock data for POC - will be replaced with Google Sheets data
    mock_onboardings = [
        {
            'id': 'S-12',
            'sponsor_name': 'Granite Capital Partners LLP',
            'fund_name': 'Granite Capital Fund III LP',
            'phase': 4,
            'phase_name': 'Screening & Risk',
            'status': 'in_progress',
            'risk_level': 'low',
            'assigned_to': 'James Smith',
            'is_existing_sponsor': False,
            'created_at': '2026-01-15',
            'updated_at': '2026-02-01'
        },
        {
            'id': 'S-11',
            'sponsor_name': 'Ashford Capital Advisors Ltd',
            'fund_name': 'Ashford Growth Fund I LP',
            'phase': 6,
            'phase_name': 'Approval',
            'status': 'pending_mlro',
            'risk_level': 'medium',
            'assigned_to': 'James Smith',
            'is_existing_sponsor': False,
            'created_at': '2026-01-10',
            'updated_at': '2026-02-02'
        },
        {
            'id': 'S-10',
            'sponsor_name': 'Bluewater Asset Management',
            'fund_name': 'Bluewater Real Estate Fund LP',
            'phase': 7,
            'phase_name': 'Commercial',
            'status': 'approved',
            'risk_level': 'medium',
            'assigned_to': 'Sarah Johnson',
            'is_existing_sponsor': False,
            'created_at': '2026-01-05',
            'updated_at': '2026-02-02'
        },
        {
            'id': 'S-09',
            'sponsor_name': 'Granite Capital Partners LLP',
            'fund_name': 'Granite Capital Fund IV LP',
            'phase': 2,
            'phase_name': 'Sponsor Review',
            'status': 'in_progress',
            'risk_level': 'low',
            'assigned_to': 'James Smith',
            'is_existing_sponsor': True,
            'created_at': '2026-01-28',
            'updated_at': '2026-02-01'
        }
    ]

    # Calculate stats
    stats = {
        'in_progress': sum(1 for o in mock_onboardings if o['status'] == 'in_progress'),
        'pending_approval': sum(1 for o in mock_onboardings if o['status'] == 'pending_mlro'),
        'approved_this_month': sum(1 for o in mock_onboardings if o['status'] == 'approved'),
        'on_hold': 0
    }

    # Filter by role
    if user['role'] == 'bd':
        # BD sees their own cases
        onboardings = [o for o in mock_onboardings if o['assigned_to'] == user['name'] or o['phase'] <= 2]
    elif user['role'] == 'mlro':
        # MLRO sees approval queue prominently
        onboardings = sorted(mock_onboardings, key=lambda x: (x['status'] != 'pending_mlro', x['updated_at']))
    else:
        onboardings = mock_onboardings

    return render_template('dashboard.html',
                         onboardings=onboardings,
                         stats=stats,
                         phases=get_phases())


@app.route('/onboarding/new', methods=['GET', 'POST'])
@login_required
def new_onboarding():
    """Start new client onboarding"""
    if request.method == 'POST':
        # Handle form submission
        sponsor_type = request.form.get('sponsor_type')  # 'new' or 'existing'

        if sponsor_type == 'existing':
            sponsor_id = request.form.get('sponsor_id')
            # Redirect to trigger review workflow
            flash('Starting trigger review for existing sponsor...', 'info')
            return redirect(url_for('trigger_review', sponsor_id=sponsor_id))
        else:
            # Start new sponsor onboarding
            flash('New client enquiry started.', 'success')
            return redirect(url_for('onboarding_phase', onboarding_id='NEW', phase=1))

    # Mock existing sponsors for selection
    existing_sponsors = [
        {'id': 'SP-001', 'name': 'Granite Capital Partners LLP', 'last_approved': '2025-06-15'},
        {'id': 'SP-002', 'name': 'Highland Ventures Ltd', 'last_approved': '2025-09-20'},
    ]

    return render_template('onboarding/new.html', existing_sponsors=existing_sponsors)


@app.route('/onboarding/<onboarding_id>/phase/<int:phase>')
@login_required
def onboarding_phase(onboarding_id, phase):
    """Onboarding wizard - specific phase"""
    phases = get_phases()
    if phase < 1 or phase > len(phases):
        flash('Invalid phase.', 'danger')
        return redirect(url_for('dashboard'))

    current_phase = phases[phase - 1]

    return render_template(f'onboarding/phase{phase}.html',
                         onboarding_id=onboarding_id,
                         phase=phase,
                         phases=phases,
                         current_phase=current_phase)


@app.route('/onboarding/<onboarding_id>/trigger-review')
@login_required
def trigger_review(onboarding_id):
    """Trigger event review for existing sponsor"""
    return render_template('onboarding/trigger_review.html',
                         onboarding_id=onboarding_id)


@app.route('/approvals')
@login_required
@role_required('mlro', 'compliance')
def approvals():
    """Approval queue"""
    user = get_current_user()

    # Mock pending approvals
    pending = [
        {
            'id': 'S-11',
            'sponsor_name': 'Ashford Capital Advisors Ltd',
            'fund_name': 'Ashford Growth Fund I LP',
            'risk_level': 'medium',
            'risk_score': 55,
            'pep_status': 'Domestic PEP',
            'reviewer': 'James Smith',
            'waiting_days': 3,
            'approval_type': 'mlro'
        }
    ]

    # Filter based on role
    if user['role'] == 'compliance':
        pending = [p for p in pending if p['approval_type'] == 'compliance']

    return render_template('approvals.html', pending=pending)


# ========== API Routes ==========

@app.route('/api/onboardings')
@login_required
def api_onboardings():
    """API: Get onboardings list"""
    # Will integrate with Google Sheets
    return jsonify({'onboardings': [], 'status': 'ok'})


@app.route('/api/onboarding/<onboarding_id>')
@login_required
def api_onboarding_detail(onboarding_id):
    """API: Get onboarding details"""
    return jsonify({'onboarding': {}, 'status': 'ok'})


@app.route('/api/onboarding/<onboarding_id>/approve', methods=['POST'])
@login_required
@role_required('mlro', 'compliance')
def api_approve(onboarding_id):
    """API: Approve onboarding"""
    user = get_current_user()
    data = request.get_json()

    # Validate approval permissions
    # Will integrate with approval workflow

    return jsonify({'status': 'ok', 'message': 'Approved'})


# ========== Helper Functions ==========

def get_phases():
    """Get workflow phases configuration"""
    return [
        {'num': 1, 'name': 'Enquiry', 'icon': 'bi-clipboard-check', 'description': 'Initial intake and conflict check'},
        {'num': 2, 'name': 'Sponsor', 'icon': 'bi-person-badge', 'description': 'Sponsor entity and principals'},
        {'num': 3, 'name': 'Fund Structure', 'icon': 'bi-building', 'description': 'Fund vehicles and GP setup'},
        {'num': 4, 'name': 'Screening & Risk', 'icon': 'bi-search', 'description': 'PEP, Sanctions, Risk assessment'},
        {'num': 5, 'name': 'EDD', 'icon': 'bi-shield-exclamation', 'description': 'Enhanced due diligence (if required)'},
        {'num': 6, 'name': 'Approval', 'icon': 'bi-check-circle', 'description': 'MLRO and Board sign-off'},
        {'num': 7, 'name': 'Commercial', 'icon': 'bi-file-earmark-text', 'description': 'Engagement letter execution'},
        {'num': 8, 'name': 'Complete', 'icon': 'bi-flag', 'description': 'Onboarding finalization'}
    ]


# ========== Error Handlers ==========

@app.errorhandler(404)
def not_found(e):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(e):
    logger.error(f'Server error: {e}')
    return render_template('errors/500.html'), 500


# ========== Main ==========

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
