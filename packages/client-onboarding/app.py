"""
Client Onboarding System - Main Application
JFSC-compliant client onboarding for Jersey fund administration
"""

import os
import logging
import threading
from datetime import datetime
from functools import wraps
from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, flash, session, g, make_response, Response
)
from flask_cors import CORS
from dotenv import load_dotenv
from services.sheets_db import get_client as get_sheets_client
from services.pdf_report import generate_report, REPORT_TYPES
from services import (
    notify_edd_triggered,
    notify_approval_required,
    notify_screening_complete
)
from services.gdrive_audit import save_form_data, ensure_folder_structure, save_api_response
import json


def run_in_background(func, *args, **kwargs):
    """Run a function in a background thread without blocking the response"""
    thread = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
    thread.start()
    return thread

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

# Initialize Google Sheets database
sheets_db = get_sheets_client()

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

# Mock completed enquiry submissions
MOCK_ENQUIRIES = {
    'ENQ-001': {
        'id': 'ENQ-001',
        'status': 'pending',
        'submitted_at': '2026-02-01 09:30',
        'sponsor_name': 'Granite Capital Partners LLP',
        'entity_type': 'llp',
        'jurisdiction': 'UK',
        'registration_number': 'OC123456',
        'registered_address': '100 Liverpool Street, London, EC2M 2RH',
        'business_address': '100 Liverpool Street, 5th Floor, London, EC2M 2RH',
        'trading_name': 'Granite Capital',
        'regulatory_status': 'regulated',
        'regulator': 'FCA',
        'license_number': '123456',
        'date_of_incorporation': '2015-03-15',
        'website': 'https://www.granitecapital.com',
        'lei': '5493001KJTIIGC8Y1R17',
        'tax_id': 'GB123456789',
        'business_activities': 'Private equity fund management, mid-market buyout investments in technology and healthcare sectors. Managed assets under management of approximately $2 billion across three funds.',
        'source_of_wealth': 'Management fees from previous funds (Granite I and II totaling $1.2B AUM), carried interest from successful exits, and personal capital contributions from founding partners.',
        'source_of_funds': 'Institutional investors (pension funds, endowments), family offices, and high net worth individuals. Anchor commitments from UK pension funds totaling $150M.',
        'fund_name': 'Granite Capital Fund III LP',
        'fund_type': 'jpf',
        'legal_structure': 'lp',
        'target_size': '500,000,000',
        'investment_strategy': 'Mid-market buyout investments in UK and European technology and healthcare sectors. Target companies with EBITDA of $10-50M.',
        'target_countries': ['uk', 'eu'],
        'principals': [
            {
                'name': 'John Smith',
                'full_name': 'John Edward Smith',
                'former_names': '',
                'role': 'both',
                'nationality': 'British',
                'dob': '1972-05-15',
                'residential_address': '45 Kensington Gardens, London, W8 4QS',
                'country_of_residence': 'UK',
                'ownership': '35',
                'ownership_pct': 35,
                'is_ubo': True
            },
            {
                'name': 'Sarah Johnson',
                'full_name': 'Sarah Anne Johnson',
                'former_names': 'Sarah Anne Williams (maiden name)',
                'role': 'both',
                'nationality': 'British',
                'dob': '1978-09-22',
                'residential_address': '12 Chelsea Embankment, London, SW3 4LF',
                'country_of_residence': 'UK',
                'ownership': '35',
                'ownership_pct': 35,
                'is_ubo': True
            },
            {
                'name': 'Michael Brown',
                'full_name': 'Michael James Brown',
                'former_names': '',
                'role': 'both',
                'nationality': 'British',
                'dob': '1980-01-10',
                'residential_address': '8 Hampstead Heath, London, NW3 1AA',
                'country_of_residence': 'UK',
                'ownership': '30',
                'ownership_pct': 30,
                'is_ubo': True
            }
        ],
        'gp_directors': [
            {
                'principal_id': 'principal_js_enq001',
                'full_name': 'John Edward Smith',
                'former_names': '',
                'dob': '1972-05-15',
                'nationality': 'British',
                'residential_address': '45 Kensington Gardens, London, W8 4QS',
                'country_of_residence': 'UK',
                'position': 'director',
                'source': 'enquiry'
            },
            {
                'principal_id': 'principal_saj_enq001',
                'full_name': 'Sarah Anne Johnson',
                'former_names': 'Sarah Anne Williams (maiden name)',
                'dob': '1978-09-22',
                'nationality': 'British',
                'residential_address': '12 Chelsea Embankment, London, SW3 4LF',
                'country_of_residence': 'UK',
                'position': 'director',
                'source': 'enquiry'
            }
        ],
        'initial_investors': [
            {'name': 'UK Public Pension Fund', 'type': 'pension_fund', 'jurisdiction': 'UK', 'commitment_pct': 30, 'commitment_amount': '150,000,000'},
            {'name': 'Smith Family Office', 'type': 'family_office', 'jurisdiction': 'UK', 'commitment_pct': 10, 'commitment_amount': '50,000,000'},
            {'name': 'European Insurance Co', 'type': 'institutional', 'jurisdiction': 'EU', 'commitment_pct': 25, 'commitment_amount': '125,000,000'},
            {'name': 'US University Endowment', 'type': 'institutional', 'jurisdiction': 'US', 'commitment_pct': 20, 'commitment_amount': '100,000,000'},
            {'name': 'GP Commitment', 'type': 'sponsor_affiliate', 'jurisdiction': 'UK', 'commitment_pct': 15, 'commitment_amount': '75,000,000'}
        ],
        'contact_name': 'John Smith',
        'contact_email': 'john.smith@granitecapital.com',
        'contact_phone': '+44 20 7123 4567',
        'enquiry_source': 'referral',
        'referrer_name': 'James Wilson - Highland Ventures',
        'declaration_accepted': True
    },
    'ENQ-002': {
        'id': 'ENQ-002',
        'status': 'pending',
        'submitted_at': '2026-02-02 11:15',
        'sponsor_name': 'Evergreen Capital Management Ltd',
        'entity_type': 'company',
        'jurisdiction': 'UK',
        'registration_number': '12345678',
        'registered_address': '25 Cannon Street, London, EC4M 5TA',
        'business_address': '25 Cannon Street, 10th Floor, London, EC4M 5TA',
        'trading_name': 'Evergreen Capital',
        'regulatory_status': 'regulated',
        'regulator': 'FCA',
        'license_number': '654321',
        'date_of_incorporation': '2018-07-01',
        'website': 'https://www.evergreencap.com',
        'lei': '549300EXAMPLE123456',
        'tax_id': 'GB987654321',
        'business_activities': 'ESG-focused investment management specializing in renewable energy and sustainable technology. First fund launched in 2019 with $100M AUM.',
        'source_of_wealth': 'Seed capital from founders (prior careers in investment banking and asset management), anchor investor commitments, and management fees from Fund I.',
        'source_of_funds': 'ESG-focused institutional investors, impact funds, sovereign wealth funds with sustainability mandates, and green bond investors.',
        'fund_name': 'Evergreen Sustainable Growth Fund LP',
        'fund_type': 'jpf',
        'legal_structure': 'lp',
        'target_size': '250,000,000',
        'investment_strategy': 'ESG-focused growth equity investments in renewable energy infrastructure and sustainable technology across Europe.',
        'target_countries': ['uk', 'eu', 'global'],
        'principals': [
            {
                'name': 'Elizabeth Chen',
                'full_name': 'Elizabeth Wei Chen',
                'former_names': '',
                'role': 'both',
                'nationality': 'British',
                'dob': '1975-03-28',
                'residential_address': '22 Mayfair Place, London, W1K 3AE',
                'country_of_residence': 'UK',
                'ownership': '40',
                'ownership_pct': 40,
                'is_ubo': True
            },
            {
                'name': 'David Kumar',
                'full_name': 'David Raj Kumar',
                'former_names': '',
                'role': 'both',
                'nationality': 'British',
                'dob': '1979-11-05',
                'residential_address': '15 Richmond Hill, Surrey, TW10 6QX',
                'country_of_residence': 'UK',
                'ownership': '30',
                'ownership_pct': 30,
                'is_ubo': True
            },
            {
                'name': 'Anna Schmidt',
                'full_name': 'Anna Maria Schmidt',
                'former_names': 'Anna Maria Weber (maiden name)',
                'role': 'both',
                'nationality': 'German',
                'dob': '1982-07-14',
                'residential_address': 'Friedrichstrasse 123, 10117 Berlin, Germany',
                'country_of_residence': 'Germany',
                'ownership': '30',
                'ownership_pct': 30,
                'is_ubo': True
            }
        ],
        'gp_directors': [
            {
                'full_name': 'Elizabeth Wei Chen',
                'former_names': '',
                'dob': '1975-03-28',
                'nationality': 'British',
                'residential_address': '22 Mayfair Place, London, W1K 3AE',
                'country_of_residence': 'UK',
                'position': 'chairman'
            },
            {
                'full_name': 'David Raj Kumar',
                'former_names': '',
                'dob': '1979-11-05',
                'nationality': 'British',
                'residential_address': '15 Richmond Hill, Surrey, TW10 6QX',
                'country_of_residence': 'UK',
                'position': 'director'
            }
        ],
        'initial_investors': [
            {'name': 'Nordic Green Fund', 'type': 'fund_of_funds', 'jurisdiction': 'EU', 'commitment_pct': 30, 'commitment_amount': '75,000,000'},
            {'name': 'Impact Capital Partners', 'type': 'institutional', 'jurisdiction': 'UK', 'commitment_pct': 25, 'commitment_amount': '62,500,000'},
            {'name': 'Swiss Sustainability Fund', 'type': 'institutional', 'jurisdiction': 'Other', 'commitment_pct': 20, 'commitment_amount': '50,000,000'},
            {'name': 'German Pension Alliance', 'type': 'pension_fund', 'jurisdiction': 'EU', 'commitment_pct': 15, 'commitment_amount': '37,500,000'},
            {'name': 'Chen Family Trust', 'type': 'sponsor_affiliate', 'jurisdiction': 'UK', 'commitment_pct': 10, 'commitment_amount': '25,000,000'}
        ],
        'contact_name': 'Elizabeth Chen',
        'contact_email': 'e.chen@evergreencap.com',
        'contact_phone': '+44 20 7987 6543',
        'enquiry_source': 'website',
        'referrer_name': '',
        'declaration_accepted': True
    },
    'ENQ-003': {
        'id': 'ENQ-003',
        'status': 'pending',
        'submitted_at': '2026-02-02 14:45',
        'sponsor_name': 'Nordic Ventures AS',
        'entity_type': 'company',
        'jurisdiction': 'Other',
        'jurisdiction_other': 'Norway',
        'registration_number': 'NO 912 345 678',
        'registered_address': 'Aker Brygge, Stranden 1, 0250 Oslo, Norway',
        'business_address': 'Aker Brygge, Stranden 1, 0250 Oslo, Norway',
        'trading_name': 'Nordic Ventures',
        'regulatory_status': 'regulated',
        'regulator': 'Other',
        'license_number': 'NV-2020-0456',
        'date_of_incorporation': '2020-01-15',
        'website': 'https://www.nordicventures.no',
        'lei': '5493009NORDIC12345',
        'tax_id': 'NO912345678MVA',
        'business_activities': 'Venture capital and growth equity investments in Nordic technology companies. Focus on fintech, healthtech, and cleantech sectors.',
        'source_of_wealth': 'Founder capital from successful prior technology exits, institutional investors including Nordic pension funds, and family office commitments.',
        'source_of_funds': 'Nordic pension funds, Norwegian sovereign wealth fund co-investments, family offices with technology focus, and corporate venture capital arms.',
        'fund_name': 'Nordic Technology Opportunities Fund LP',
        'fund_type': 'jpf',
        'legal_structure': 'lp',
        'target_size': '150,000,000',
        'investment_strategy': 'Early-stage and growth investments in Nordic technology companies, with focus on fintech, healthtech, and cleantech sectors.',
        'target_countries': ['eu'],
        'principals': [
            {
                'name': 'Erik Larsson',
                'full_name': 'Erik Gustav Larsson',
                'former_names': '',
                'role': 'both',
                'nationality': 'Norwegian',
                'dob': '1976-08-20',
                'residential_address': 'Bygdoy Alle 45, 0265 Oslo, Norway',
                'country_of_residence': 'Norway',
                'ownership': '50',
                'ownership_pct': 50,
                'is_ubo': True
            },
            {
                'name': 'Ingrid Olsen',
                'full_name': 'Ingrid Marie Olsen',
                'former_names': 'Ingrid Marie Hansen (maiden name)',
                'role': 'both',
                'nationality': 'Norwegian',
                'dob': '1981-04-12',
                'residential_address': 'Frognerveien 88, 0271 Oslo, Norway',
                'country_of_residence': 'Norway',
                'ownership': '50',
                'ownership_pct': 50,
                'is_ubo': True
            }
        ],
        'gp_directors': [
            {
                'full_name': 'Erik Gustav Larsson',
                'former_names': '',
                'dob': '1976-08-20',
                'nationality': 'Norwegian',
                'residential_address': 'Bygdoy Alle 45, 0265 Oslo, Norway',
                'country_of_residence': 'Norway',
                'position': 'chairman'
            },
            {
                'full_name': 'Ingrid Marie Olsen',
                'former_names': 'Ingrid Marie Hansen (maiden name)',
                'dob': '1981-04-12',
                'nationality': 'Norwegian',
                'residential_address': 'Frognerveien 88, 0271 Oslo, Norway',
                'country_of_residence': 'Norway',
                'position': 'director'
            }
        ],
        'initial_investors': [
            {'name': 'Norwegian Tech Pension', 'type': 'pension_fund', 'jurisdiction': 'EU', 'commitment_pct': 35, 'commitment_amount': '52,500,000'},
            {'name': 'Larsson Family Trust', 'type': 'sponsor_affiliate', 'jurisdiction': 'EU', 'commitment_pct': 15, 'commitment_amount': '22,500,000'},
            {'name': 'Swedish Innovation Fund', 'type': 'fund_of_funds', 'jurisdiction': 'EU', 'commitment_pct': 25, 'commitment_amount': '37,500,000'},
            {'name': 'Finnish Technology Ventures', 'type': 'institutional', 'jurisdiction': 'EU', 'commitment_pct': 15, 'commitment_amount': '22,500,000'},
            {'name': 'Olsen Investment Holdings', 'type': 'family_office', 'jurisdiction': 'Other', 'commitment_pct': 10, 'commitment_amount': '15,000,000'}
        ],
        'contact_name': 'Erik Larsson',
        'contact_email': 'erik@nordicventures.no',
        'contact_phone': '+47 22 12 34 56',
        'enquiry_source': 'event',
        'referrer_name': 'Met at Jersey Finance Roadshow London',
        'declaration_accepted': True
    }
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
        'sheets_demo_mode': sheets_db.demo_mode,
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
            # For API endpoints, return JSON error instead of redirect
            if request.path.startswith('/api/'):
                return jsonify({'status': 'error', 'message': 'Authentication required'}), 401
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

    # Get onboardings from Sheets
    onboardings = sheets_db.get_onboardings()

    # Fallback to mock data if Sheets is empty/demo mode
    if not onboardings:
        onboardings = [
            {
                'onboarding_id': 'ONB-001',
                'sponsor_name': 'Granite Capital Partners LLP',
                'fund_name': 'Granite Capital Fund III LP',
                'current_phase': 4,
                'status': 'in_progress',
                'risk_level': 'low',
                'assigned_to': 'James Smith',
                'is_existing_sponsor': False,
                'created_at': '2026-01-15',
                'updated_at': '2026-02-01'
            },
            {
                'onboarding_id': 'ONB-002',
                'sponsor_name': 'Ashford Capital Advisors Ltd',
                'fund_name': 'Ashford Growth Fund I LP',
                'current_phase': 6,
                'status': 'pending_mlro',
                'risk_level': 'medium',
                'assigned_to': 'James Smith',
                'is_existing_sponsor': False,
                'created_at': '2026-01-10',
                'updated_at': '2026-02-02'
            },
            {
                'onboarding_id': 'ONB-003',
                'sponsor_name': 'Bluewater Asset Management',
                'fund_name': 'Bluewater Real Estate Fund LP',
                'current_phase': 7,
                'status': 'approved',
                'risk_level': 'medium',
                'assigned_to': 'Sarah Johnson',
                'is_existing_sponsor': False,
                'created_at': '2026-01-05',
                'updated_at': '2026-02-02'
            },
            {
                'onboarding_id': 'ONB-004',
                'sponsor_name': 'Granite Capital Partners LLP',
                'fund_name': 'Granite Capital Fund IV LP',
                'current_phase': 2,
                'status': 'in_progress',
                'risk_level': 'low',
                'assigned_to': 'James Smith',
                'is_existing_sponsor': True,
                'created_at': '2026-01-28',
                'updated_at': '2026-02-01'
            }
        ]
    else:
        # Enrich onboardings with sponsor names if not present
        for onb in onboardings:
            if not onb.get('sponsor_name') and onb.get('sponsor_id'):
                sponsor = sheets_db.get_sponsor(onb['sponsor_id'])
                if sponsor:
                    onb['sponsor_name'] = sponsor.get('legal_name', 'Unknown')
            # Convert string booleans
            if isinstance(onb.get('is_existing_sponsor'), str):
                onb['is_existing_sponsor'] = onb['is_existing_sponsor'].lower() == 'true'
            # Ensure phase is int
            if isinstance(onb.get('current_phase'), str):
                onb['current_phase'] = int(onb['current_phase'])

    # Calculate stats
    stats = {
        'in_progress': sum(1 for o in onboardings if o.get('status') == 'in_progress'),
        'pending_approval': sum(1 for o in onboardings if o.get('status') == 'pending_mlro'),
        'approved_this_month': sum(1 for o in onboardings if o.get('status') == 'approved'),
        'on_hold': 0
    }

    # Filter by role
    if user['role'] == 'bd':
        onboardings = [o for o in onboardings if o.get('assigned_to') == user['name'] or o.get('current_phase', 0) <= 2]
    elif user['role'] == 'mlro':
        onboardings = sorted(onboardings, key=lambda x: (x.get('status') != 'pending_mlro', x.get('updated_at', '')))

    # Add phase_name for display
    phases = get_phases()
    for onb in onboardings:
        phase_num = onb.get('current_phase', 1)
        if 1 <= phase_num <= len(phases):
            onb['phase_name'] = phases[phase_num - 1]['name']
            onb['phase'] = phase_num
        if 'id' not in onb:
            onb['id'] = onb.get('onboarding_id', '')

    return render_template('dashboard.html',
                         onboardings=onboardings,
                         stats=stats,
                         phases=phases)


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


@app.route('/onboarding/<onboarding_id>/phase/<int:phase>', methods=['GET', 'POST'])
@login_required
def onboarding_phase(onboarding_id, phase):
    """Onboarding wizard - specific phase"""
    phases = get_phases()
    if phase < 1 or phase > len(phases):
        flash('Invalid phase.', 'danger')
        return redirect(url_for('dashboard'))

    current_phase = phases[phase - 1]

    # Handle form submission (POST)
    if request.method == 'POST':
        action = request.form.get('action', 'next')

        # Extract sponsor and fund info from form for audit trail
        sponsor_name = request.form.get('sponsor_name', 'Unknown Sponsor')
        fund_name = request.form.get('fund_name', 'Unknown Fund')

        # Store in session for subsequent phases
        if sponsor_name and sponsor_name != 'Unknown Sponsor':
            session['current_sponsor'] = sponsor_name
        if fund_name and fund_name != 'Unknown Fund':
            session['current_fund'] = fund_name

        # Use session values if not in form
        sponsor_name = sponsor_name if sponsor_name != 'Unknown Sponsor' else session.get('current_sponsor', 'Unknown Sponsor')
        fund_name = fund_name if fund_name != 'Unknown Fund' else session.get('current_fund', 'Unknown Fund')

        # Build form data dict once
        form_data = {key: value for key, value in request.form.items() if key != 'action'}

        # Save form data to audit trail (skip in demo mode for performance)
        if not DEMO_MODE:
            audit_result = save_form_data(form_data, phase, sponsor_name, fund_name)
            logger.info(f"Audit trail save for phase {phase}: {audit_result.get('status')}")

        # Save to Google Sheets if not in demo mode
        # Run non-essential operations in background for faster phase transitions
        if not sheets_db.demo_mode:
            def save_phase_to_sheets():
                """Background task to save phase data to Google Sheets"""
                try:
                    if phase == 1:
                        # Phase 1: Create/update enquiry with merged form data
                        # Parse sponsor principals, GP directors, and investors from JSON
                        sponsor_principals_json = form_data.get('sponsor_principals_json', '[]')
                        gp_directors_json = form_data.get('gp_directors_json', '[]')
                        investors_json = form_data.get('investors_json', '[]')
                        try:
                            sponsor_principals = json.loads(sponsor_principals_json)
                        except json.JSONDecodeError:
                            sponsor_principals = []
                        try:
                            gp_directors = json.loads(gp_directors_json)
                        except json.JSONDecodeError:
                            gp_directors = []
                        try:
                            investors = json.loads(investors_json)
                        except json.JSONDecodeError:
                            investors = []

                        # Create enquiry record with all new fields
                        enquiry_data = {
                            'sponsor_name': form_data.get('legal_name'),
                            'trading_name': form_data.get('trading_name', ''),
                            'fund_name': form_data.get('fund_name'),
                            'contact_name': form_data.get('contact_name'),
                            'contact_email': form_data.get('contact_email'),
                            'entity_type': form_data.get('entity_type'),
                            'jurisdiction': form_data.get('jurisdiction'),
                            'registration_number': form_data.get('registration_number'),
                            'date_incorporated': form_data.get('date_of_incorporation'),
                            'registered_address': form_data.get('registered_address'),
                            'business_address': form_data.get('business_address', ''),
                            'regulatory_status': form_data.get('regulatory_status'),
                            'regulator': form_data.get('regulator', ''),
                            'license_number': form_data.get('license_number', ''),
                            'business_activities': form_data.get('principal_business_activities'),
                            'source_of_wealth': form_data.get('source_of_wealth', ''),
                            'source_of_funds': form_data.get('source_of_funds', ''),
                            'fund_type': form_data.get('fund_type'),
                            'legal_structure': form_data.get('fund_legal_structure'),
                            'investment_strategy': form_data.get('investment_strategy'),
                            'target_size': form_data.get('target_fund_size'),
                            'declaration_accepted': request.form.get('declaration') == 'on',
                            'status': 'in_progress',
                            'notes': ''
                        }
                        enquiry_id = sheets_db.create_enquiry(enquiry_data)
                        logger.info(f"Phase 1 (background): Created enquiry {enquiry_id} in Sheets")

                        # Create sponsor record
                        sponsor_data = {
                            'legal_name': form_data.get('legal_name'),
                            'trading_name': form_data.get('trading_name', ''),
                            'entity_type': form_data.get('entity_type'),
                            'jurisdiction': form_data.get('jurisdiction'),
                            'registration_number': form_data.get('registration_number'),
                            'date_incorporated': form_data.get('date_of_incorporation'),
                            'registered_address': form_data.get('registered_address'),
                            'business_address': form_data.get('business_address', ''),
                            'business_activities': form_data.get('principal_business_activities'),
                            'source_of_wealth': form_data.get('source_of_wealth', ''),
                            'source_of_funds': form_data.get('source_of_funds', ''),
                            'regulated_status': form_data.get('regulatory_status'),
                            'cdd_status': 'in_progress'
                        }
                        sponsor_id = sheets_db.create_sponsor(sponsor_data)
                        logger.info(f"Phase 1 (background): Created sponsor {sponsor_id} in Sheets")

                        # Create person records for sponsor principals (directors/UBOs)
                        for principal in sponsor_principals:
                            person_data = {
                                'full_name': principal.get('full_name'),
                                'former_names': principal.get('former_names', ''),
                                'nationality': principal.get('nationality'),
                                'dob': principal.get('dob'),
                                'country_of_residence': principal.get('country_of_residence'),
                                'residential_address': principal.get('residential_address'),
                                'pep_status': 'unknown',
                                'id_verified': False
                            }
                            person_id = sheets_db.create_person(person_data)

                            # Create person role linking person to sponsor
                            person_role_data = {
                                'person_id': person_id,
                                'entity_id': sponsor_id,
                                'entity_type': 'Sponsor',
                                'role': principal.get('role'),
                                'ownership_pct': principal.get('ownership_pct'),
                                'is_ubo': principal.get('is_ubo', False)
                            }
                            sheets_db.create_person_role(person_role_data)
                            logger.info(f"Phase 1 (background): Created sponsor principal {person_id}")

                        # Create person records for GP directors
                        for director in gp_directors:
                            person_data = {
                                'full_name': director.get('full_name'),
                                'former_names': director.get('former_names', ''),
                                'nationality': director.get('nationality'),
                                'dob': director.get('dob'),
                                'country_of_residence': director.get('country_of_residence'),
                                'residential_address': director.get('residential_address'),
                                'pep_status': 'unknown',
                                'id_verified': False
                            }
                            person_id = sheets_db.create_person(person_data)

                            # Create person role linking person to GP
                            person_role_data = {
                                'person_id': person_id,
                                'entity_id': sponsor_id,  # Will be updated to GP entity when created
                                'entity_type': 'GP',
                                'role': director.get('position', 'director'),
                                'ownership_pct': None,
                                'is_ubo': False
                            }
                            sheets_db.create_person_role(person_role_data)
                            logger.info(f"Phase 1 (background): Created GP director {person_id}")

                        logger.info(f"Phase 1 (background): Completed all Sheets saves")

                    elif phase == 2:
                        # Phase 2 (Fund): Create/update onboarding record with fund details
                        onboarding_data = {
                            'fund_name': form_data.get('fund_name') or fund_name,
                            'current_phase': phase,
                            'status': 'in_progress',
                            'is_existing_sponsor': form_data.get('is_existing_sponsor', False)
                        }
                        if onboarding_id != 'NEW':
                            sheets_db.update_onboarding(onboarding_id, onboarding_data)
                        logger.info(f"Phase 2 (background): Updated onboarding in Sheets")

                    # Update onboarding phase for phases 3+
                    if phase >= 3 and onboarding_id != 'NEW':
                        sheets_db.update_onboarding(onboarding_id, {'current_phase': phase})
                        logger.info(f"Phase {phase} (background): Updated phase in Sheets")

                except Exception as e:
                    logger.error(f"Error saving phase {phase} to Sheets (background): {e}")

            # Run Sheets operations in background thread
            run_in_background(save_phase_to_sheets)

            # Store essential session data synchronously (before redirect)
            if phase == 1:
                session['initial_investors'] = json.loads(form_data.get('investors_json', '[]'))
                session['current_sponsor'] = form_data.get('legal_name')
                session['current_fund'] = form_data.get('fund_name')

        # On phase 1, ensure folder structure is created
        if phase == 1 and sponsor_name != 'Unknown Sponsor':
            ensure_folder_structure(sponsor_name, fund_name)

        if action == 'save':
            # Save draft - stay on current phase
            flash('Draft saved successfully.', 'success')
            return redirect(url_for('onboarding_phase', onboarding_id=onboarding_id, phase=phase))
        else:
            # Continue to next phase
            if phase < len(phases):
                next_phase = phase + 1
                flash(f'Phase {phase} completed. Proceeding to {phases[next_phase - 1]["name"]}.', 'success')
                return redirect(url_for('onboarding_phase', onboarding_id=onboarding_id, phase=next_phase))
            else:
                flash('Onboarding complete!', 'success')
                return redirect(url_for('dashboard'))

    # Handle GET request - display form
    # Check if we're auto-populating from an enquiry
    # Priority: 1) URL param, 2) Onboarding's enquiry_id field, 3) Session (for NEW only)
    enquiry_id = request.args.get('enquiry_id')

    # For existing onboardings, always use the onboarding's enquiry_id
    if not enquiry_id and onboarding_id != 'NEW':
        onboarding = sheets_db.get_onboarding(onboarding_id)
        if onboarding:
            enquiry_id = onboarding.get('enquiry_id')
            if enquiry_id:
                logger.info(f"Loaded enquiry_id '{enquiry_id}' from onboarding {onboarding_id}")

    # For new onboardings, fall back to session
    if not enquiry_id and onboarding_id == 'NEW':
        enquiry_id = session.get('current_enquiry_id')

    enquiry = None
    if enquiry_id:
        # Try to get from Sheets first
        sheets_enquiry = sheets_db.get_enquiry(enquiry_id)
        mock_enquiry = MOCK_ENQUIRIES.get(enquiry_id)

        if sheets_enquiry:
            enquiry = sheets_enquiry
            # Merge all missing fields from MOCK_ENQUIRIES into Sheets data
            # (Sheets may not have all fields, especially nested ones like principals)
            if mock_enquiry:
                # Merge nested arrays (stored in separate Sheets tables)
                for array_key in ['principals', 'gp_directors', 'initial_investors']:
                    if array_key not in enquiry or not enquiry.get(array_key):
                        enquiry[array_key] = mock_enquiry.get(array_key, [])

                # Merge all other missing scalar fields (including regulatory_status)
                for key, value in mock_enquiry.items():
                    # Use mock value if key missing, empty string, or None
                    if key not in enquiry or enquiry.get(key) in (None, '', []):
                        enquiry[key] = value
        else:
            enquiry = mock_enquiry

        # Normalize regulatory_status to expected values
        if enquiry:
            raw_status = enquiry.get('regulatory_status', '')
            if raw_status:
                status_lower = raw_status.lower()
                if 'regulated' in status_lower and 'not' not in status_lower:
                    enquiry['regulatory_status'] = 'regulated'
                elif 'not' in status_lower or 'unregulated' in status_lower:
                    enquiry['regulatory_status'] = 'not_regulated'
                elif 'exempt' in status_lower:
                    enquiry['regulatory_status'] = 'exempt'
                elif 'pending' in status_lower:
                    enquiry['regulatory_status'] = 'pending_registration'
            logger.info(f"Enquiry {enquiry_id} loaded - regulatory_status: '{enquiry.get('regulatory_status')}', sponsor: '{enquiry.get('sponsor_name')}'")

        # Update session with enquiry_id for subsequent phases
        session['current_enquiry_id'] = enquiry_id
    uploaded = request.args.get('uploaded') == '1'  # Flag if data came from uploaded document

    # Get list of pending enquiries for Phase 1 dropdown
    pending_enquiries = [e for e in MOCK_ENQUIRIES.values() if e['status'] == 'pending'] if phase == 1 else []

    # Prepare context for template
    context = {
        'onboarding_id': onboarding_id,
        'phase': phase,
        'phases': phases,
        'current_phase': current_phase,
        'enquiry': enquiry,
        'pending_enquiries': pending_enquiries,
        'uploaded': uploaded
    }

    # Phase 2: Add additional principals (not from enquiry)
    if phase == 2 and onboarding_id != 'NEW':
        try:
            added_principals = sheets_db.query('FundPrincipals', filters={
                'onboarding_id': onboarding_id
            })
            # Filter out enquiry principals - only get manually added ones
            added_principals = [p for p in added_principals if p.get('source') != 'enquiry']
            context['added_principals'] = added_principals
        except Exception as e:
            logger.error(f"Error fetching added principals: {e}")
            context['added_principals'] = []
    elif phase == 2:
        # For NEW onboarding, add Robert Jones as an example added principal
        context['added_principals'] = [
            {
                'principal_id': 'principal_rj_123',
                'full_name': 'Robert Jones',
                'former_names': '',
                'dob': '1975-08-20',
                'nationality': 'British',
                'residential_address': '78 Mayfair Gardens, London, W1K 3AB',
                'country_of_residence': 'UK',
                'position': 'independent_director',
                'source': 'manual'
            }
        ]

    # Phase 5: Add screening and risk data
    if phase == 5:
        # Get screening results from sheets_db
        screening_results = sheets_db.get_screening_results(onboarding_id)
        risk_data = sheets_db.get_risk_assessment(onboarding_id)

        context.update({
            'screening_results': screening_results,
            'risk_score': risk_data.get('score') if risk_data else None,
            'risk_rating': risk_data.get('rating') if risk_data else None,
            'jurisdiction_risk': risk_data.get('jurisdiction') if risk_data else None,
            'business_risk': risk_data.get('business_type') if risk_data else None,
            'screening_risk': risk_data.get('screening') if risk_data else None
        })

    return render_template(f'onboarding/phase{phase}.html', **context)


@app.route('/onboarding/<onboarding_id>/trigger-review')
@login_required
def trigger_review(onboarding_id):
    """Trigger event review for existing sponsor"""
    return render_template('onboarding/trigger_review.html',
                         onboarding_id=onboarding_id)


@app.route('/reports')
@login_required
def reports():
    """Reports and analytics page"""
    return render_template('reports.html')


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


# ========== Enquiry Form Routes ==========

@app.route('/enquiry')
def enquiry_form():
    """Public enquiry form for sponsors to complete"""
    return render_template('enquiry_form.html')


@app.route('/enquiry/submit', methods=['POST'])
def submit_enquiry():
    """Handle enquiry form submission"""
    # Extract form data
    form_data = {key: value for key, value in request.form.items()}
    sponsor_name = form_data.get('sponsor_name', 'Unknown Sponsor')
    fund_name = form_data.get('fund_name', 'Unknown Fund')

    # Create folder structure and save enquiry to audit trail (skip in demo mode)
    if not DEMO_MODE and sponsor_name != 'Unknown Sponsor':
        ensure_folder_structure(sponsor_name, fund_name)
        audit_result = save_form_data(form_data, 1, sponsor_name, fund_name)
        logger.info(f"Enquiry saved to audit trail: {audit_result.get('status')}")

    # In production, this would also save to Google Sheets
    # For POC, we'll just show a success message
    flash('Thank you for your enquiry. Our team will review your submission and contact you shortly.', 'success')
    return redirect(url_for('enquiry_submitted'))


@app.route('/enquiry/submitted')
def enquiry_submitted():
    """Enquiry submission confirmation page"""
    return render_template('enquiry_submitted.html')


@app.route('/enquiries')
@login_required
def pending_enquiries():
    """View pending enquiries (internal staff)"""
    enquiries = sheets_db.get_enquiries()
    if not enquiries:
        enquiries = list(MOCK_ENQUIRIES.values())
    enquiries.sort(key=lambda x: x.get('submitted_at', x.get('created_at', '')), reverse=True)
    return render_template('enquiries.html', enquiries=enquiries)


@app.route('/enquiry/<enquiry_id>/view')
@login_required
def view_enquiry(enquiry_id):
    """View details of a submitted enquiry"""
    enquiry = sheets_db.get_enquiry(enquiry_id)
    if not enquiry:
        enquiry = MOCK_ENQUIRIES.get(enquiry_id)
    if not enquiry:
        flash('Enquiry not found.', 'danger')
        return redirect(url_for('pending_enquiries'))
    return render_template('enquiry_detail.html', enquiry=enquiry)


@app.route('/enquiry/<enquiry_id>/export-pdf')
@login_required
def export_enquiry_pdf(enquiry_id):
    """Export enquiry as PDF for review"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.units import inch
    import io

    # Get enquiry data
    enquiry = MOCK_ENQUIRIES.get(enquiry_id)
    if not enquiry:
        flash('Enquiry not found', 'danger')
        return redirect(url_for('pending_enquiries'))

    # Create PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, spaceAfter=20)
    section_style = ParagraphStyle('Section', parent=styles['Heading2'], fontSize=12, textColor=colors.HexColor('#0d6efd'), spaceBefore=15, spaceAfter=10)
    label_style = ParagraphStyle('Label', parent=styles['Normal'], fontSize=9, textColor=colors.grey)
    value_style = ParagraphStyle('Value', parent=styles['Normal'], fontSize=10, spaceBefore=2, spaceAfter=8)

    elements = []

    # Title
    elements.append(Paragraph(f"Enquiry Review: {enquiry_id}", title_style))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%d %B %Y at %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 20))

    # Sponsor Information
    elements.append(Paragraph("1. Sponsor Entity Details", section_style))
    sponsor_data = [
        ['Legal Name:', enquiry.get('sponsor_name', '-')],
        ['Entity Type:', enquiry.get('entity_type', '-').upper()],
        ['Jurisdiction:', enquiry.get('jurisdiction', '-')],
        ['Registration No:', enquiry.get('registration_number', '-')],
        ['Regulatory Status:', enquiry.get('regulatory_status', '-')],
        ['Date of Incorporation:', enquiry.get('date_of_incorporation', '-')],
        ['Website:', enquiry.get('website', '-')],
        ['LEI:', enquiry.get('lei', '-')],
        ['Tax ID:', enquiry.get('tax_id', '-')],
    ]
    if enquiry.get('ultimate_parent'):
        sponsor_data.append(['Ultimate Parent:', enquiry.get('ultimate_parent', '-')])
        sponsor_data.append(['Parent Jurisdiction:', enquiry.get('parent_jurisdiction', '-')])

    t = Table(sponsor_data, colWidths=[1.8*inch, 4.5*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(t)

    # Fund Information
    elements.append(Paragraph("2. Proposed Fund", section_style))
    fund_data = [
        ['Fund Name:', enquiry.get('fund_name', '-')],
        ['Fund Type:', enquiry.get('fund_type', '-').upper() if enquiry.get('fund_type') else '-'],
        ['Legal Structure:', enquiry.get('legal_structure', '-')],
        ['Target Size:', f"${enquiry.get('target_size', '-')}"],
        ['Investment Strategy:', enquiry.get('investment_strategy', '-')[:200] + '...' if len(enquiry.get('investment_strategy', '')) > 200 else enquiry.get('investment_strategy', '-')],
    ]
    t2 = Table(fund_data, colWidths=[1.8*inch, 4.5*inch])
    t2.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(t2)

    # Principals
    if enquiry.get('principals'):
        elements.append(Paragraph("3. Key Principals", section_style))
        principal_data = [['Name', 'Role', 'Nationality', 'Ownership']]
        for p in enquiry.get('principals', []):
            principal_data.append([p.get('name', '-'), p.get('role', '-'), p.get('nationality', '-'), p.get('ownership', '-')])
        t3 = Table(principal_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.3*inch])
        t3.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(t3)

    # Contact
    elements.append(Paragraph("4. Primary Contact", section_style))
    contact_data = [
        ['Name:', enquiry.get('contact_name', '-')],
        ['Email:', enquiry.get('contact_email', '-')],
        ['Phone:', enquiry.get('contact_phone', '-')],
    ]
    t4 = Table(contact_data, colWidths=[1.8*inch, 4.5*inch])
    t4.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(t4)

    # Footer
    elements.append(Spacer(1, 30))
    elements.append(Paragraph("-" * 80, styles['Normal']))
    elements.append(Paragraph("CONFIDENTIAL - For internal compliance review only",
                             ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey)))

    # Build PDF
    doc.build(elements)
    buffer.seek(0)

    filename = f"Enquiry-{enquiry_id}-{datetime.now().strftime('%Y%m%d')}.pdf"
    return Response(
        buffer.getvalue(),
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )


@app.route('/enquiry/<enquiry_id>/start-onboarding')
@login_required
def start_onboarding_from_enquiry(enquiry_id):
    """Start onboarding process from a submitted enquiry"""
    enquiry = sheets_db.get_enquiry(enquiry_id)
    if not enquiry:
        enquiry = MOCK_ENQUIRIES.get(enquiry_id)
    if not enquiry:
        flash('Enquiry not found.', 'danger')
        return redirect(url_for('pending_enquiries'))
    # Store enquiry_id in session so it persists across phases
    session['current_enquiry_id'] = enquiry_id
    flash(f'Starting onboarding for {enquiry.get("sponsor_name")}. Form pre-populated from enquiry.', 'success')
    return redirect(url_for('onboarding_phase', onboarding_id='NEW', phase=1, enquiry_id=enquiry_id))


@app.route('/samples')
@login_required
def sample_enquiries():
    """List sample enquiry forms for testing"""
    samples = [
        {
            'name': 'Granite Capital Partners LLP',
            'fund': 'Granite Capital Fund III LP',
            'file': 'enquiry-granite-capital.html',
            'size': '$500M',
            'jurisdiction': 'UK'
        },
        {
            'name': 'Evergreen Capital Management Ltd',
            'fund': 'Evergreen Sustainable Growth Fund LP',
            'file': 'enquiry-evergreen-capital.html',
            'size': '$250M',
            'jurisdiction': 'UK'
        },
        {
            'name': 'Nordic Ventures AS',
            'fund': 'Nordic Technology Opportunities Fund LP',
            'file': 'enquiry-nordic-ventures.html',
            'size': '$150M',
            'jurisdiction': 'Norway'
        }
    ]
    return render_template('samples.html', samples=samples)


@app.route('/upload-enquiry', methods=['POST'])
@login_required
def upload_enquiry():
    """Handle enquiry form upload and AI extraction"""
    from services.gdrive_audit import get_client as get_gdrive_client
    import tempfile

    if 'enquiry_file' not in request.files:
        flash('No file uploaded.', 'danger')
        return redirect(url_for('new_onboarding'))

    file = request.files['enquiry_file']
    if file.filename == '':
        flash('No file selected.', 'danger')
        return redirect(url_for('new_onboarding'))

    # Save uploaded file to audit trail
    gdrive_client = get_gdrive_client()

    # For demo, use mock data; in production would extract from uploaded file
    # Save the uploaded file temporarily and upload to GDrive
    enquiry = MOCK_ENQUIRIES.get('ENQ-001')
    sponsor_name = enquiry.get('sponsor_name', 'Unknown Sponsor') if enquiry else 'Unknown Sponsor'
    fund_name = enquiry.get('fund_name', 'Unknown Fund') if enquiry else 'Unknown Fund'

    # Upload the file content to Google Drive
    file_content = file.read()
    file.seek(0)  # Reset file pointer

    audit_result = gdrive_client.upload_content(
        content=file_content,
        filename=f"uploaded-enquiry-{file.filename}",
        sponsor_name=sponsor_name,
        fund_name=fund_name,
        subfolder='Phase-1-Enquiry',
        mime_type=file.content_type or 'application/octet-stream'
    )
    logger.info(f"Uploaded enquiry document to audit trail: {audit_result.get('status')}")

    # For POC: Simulate AI extraction by using a mock enquiry
    # In production, this would send the file to an AI service for extraction

    # Simulate processing delay message
    flash('Document uploaded successfully. AI has extracted the following information - please verify.', 'success')

    # Use ENQ-001 as the "extracted" data for demo purposes
    # In production, this would create a new extracted enquiry record
    return redirect(url_for('onboarding_phase', onboarding_id='NEW', phase=1, enquiry_id='ENQ-001', uploaded=1))


# ========== API Routes ==========

@app.route('/api/screening/run', methods=['POST'])
@login_required
def api_run_screening():
    """API: Run sanctions/PEP screening via OpenSanctions"""
    from services.opensanctions import batch_screen, get_client
    from services.gdrive_audit import save_screening_results, get_client as get_gdrive_client
    from services.risk_scoring import calculate_risk

    data = request.get_json()
    entities = data.get('entities', [])
    sponsor_name = data.get('sponsor_name', 'Unknown Sponsor')
    fund_name = data.get('fund_name', 'Unknown Fund')

    if not entities:
        return jsonify({'status': 'error', 'message': 'No entities provided'}), 400

    # Check if running in demo mode
    client = get_client()
    demo_mode = client.demo_mode

    # Run batch screening
    results = batch_screen(entities, threshold=0.5)

    # Format response
    screening_results = []
    for entity_name, result in results.items():
        screening_results.append({
            'name': entity_name,
            'status': result.get('status'),
            'risk_level': result.get('risk_level', 'clear'),
            'has_sanctions_hit': result.get('has_sanctions_hit', False),
            'has_pep_hit': result.get('has_pep_hit', False),
            'has_adverse_media': result.get('has_adverse_media', False),
            'total_matches': result.get('total_matches', 0),
            'matches': result.get('matches', [])[:5]  # Limit to top 5 matches
        })

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
    if onboarding_id and onboarding_id != 'NEW':
        assessment_id = sheets_db.save_risk_assessment({
            'onboarding_id': onboarding_id,
            'risk_score': risk_assessment['score'],
            'risk_rating': risk_assessment['rating'],
            'risk_factors': risk_assessment['factors'],
            'edd_triggered': risk_assessment['edd_required']
        })
        risk_assessment['assessment_id'] = assessment_id

    # Save screening results to Google Drive audit trail
    gdrive_client = get_gdrive_client()
    audit_result = save_screening_results(
        screening_results={
            'entities_screened': entities,
            'results': screening_results,
            'screened_at': datetime.now().isoformat(),
            'demo_mode': demo_mode
        },
        sponsor_name=sponsor_name,
        fund_name=fund_name
    )

    # Save individual screening results to Sheets database
    current_user = get_current_user()
    for result in screening_results:
        screening_data = {
            'onboarding_id': onboarding_id or 'NEW',
            'person_id': None,  # Can be linked if tracking persons
            'screening_type': 'comprehensive',
            'result': result.get('status', 'clear'),
            'match_details': json.dumps(result.get('matches', [])),
            'risk_level': result.get('risk_level', 'clear'),
            'screened_by': current_user['name'] if current_user else 'System'
        }
        sheets_db.save_screening(screening_data)

    # Send email notifications
    onboarding_data = {
        'onboarding_id': onboarding_id,
        'sponsor_name': sponsor_name,
        'fund_name': fund_name
    }

    # Notify screening complete
    notify_screening_complete(onboarding_data, screening_results, risk_assessment)

    # Notify if EDD required
    if risk_assessment.get('edd_required'):
        notify_edd_triggered(onboarding_data, risk_assessment)

    # Notify if approval required (above compliance level)
    if risk_assessment.get('approval_level') != 'compliance':
        notify_approval_required(onboarding_data, risk_assessment)

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


@app.route('/api/screening/person', methods=['POST'])
@login_required
def api_screen_person():
    """API: Screen individual person"""
    from services.opensanctions import screen_person

    data = request.get_json()
    name = data.get('name')

    if not name:
        return jsonify({'status': 'error', 'message': 'Name is required'}), 400

    result = screen_person(
        name=name,
        birth_date=data.get('birth_date'),
        nationality=data.get('nationality'),
        threshold=0.5
    )

    return jsonify({
        'status': 'ok',
        'name': name,
        'result': result
    })


@app.route('/api/screening/company', methods=['POST'])
@login_required
def api_screen_company():
    """API: Screen company/entity"""
    from services.opensanctions import screen_company

    data = request.get_json()
    name = data.get('name')

    if not name:
        return jsonify({'status': 'error', 'message': 'Company name is required'}), 400

    result = screen_company(
        name=name,
        jurisdiction=data.get('jurisdiction'),
        registration_number=data.get('registration_number'),
        threshold=0.5
    )

    return jsonify({
        'status': 'ok',
        'name': name,
        'result': result
    })


@app.route('/api/audit/status')
@login_required
def api_audit_status():
    """API: Get Google Drive audit trail status"""
    from services.gdrive_audit import get_client

    client = get_client()
    return jsonify({
        'status': 'ok',
        'audit_enabled': True,
        'demo_mode': client.demo_mode,
        'message': 'Audit trail running in demo mode - documents logged but not uploaded' if client.demo_mode else 'Audit trail connected to Google Drive'
    })


@app.route('/api/sheets/status')
@login_required
def api_sheets_status():
    """API: Get Google Sheets database status"""
    return jsonify({
        'status': 'ok',
        'demo_mode': sheets_db.demo_mode,
        'message': 'Sheets running in demo mode - data not persisted' if sheets_db.demo_mode else 'Sheets connected'
    })


@app.route('/api/audit/save', methods=['POST'])
@login_required
def api_audit_save():
    """API: Manually save document/data to audit trail"""
    data = request.get_json()
    doc_type = data.get('type', 'form')  # 'form' or 'api'
    sponsor_name = data.get('sponsor_name')
    fund_name = data.get('fund_name')
    content = data.get('content', {})

    if not sponsor_name or not fund_name:
        return jsonify({'status': 'error', 'message': 'sponsor_name and fund_name are required'}), 400

    if doc_type == 'form':
        phase = data.get('phase', 1)
        result = save_form_data(content, phase, sponsor_name, fund_name)
    else:
        api_name = data.get('api_name', 'unknown')
        result = save_api_response(api_name, content, sponsor_name, fund_name)

    return jsonify({
        'status': 'ok',
        'result': result
    })


@app.route('/api/audit/folder', methods=['POST'])
@login_required
def api_audit_create_folder():
    """API: Create folder structure for a new onboarding"""
    data = request.get_json()
    sponsor_name = data.get('sponsor_name')
    fund_name = data.get('fund_name')

    if not sponsor_name or not fund_name:
        return jsonify({'status': 'error', 'message': 'sponsor_name and fund_name are required'}), 400

    folders = ensure_folder_structure(sponsor_name, fund_name)

    return jsonify({
        'status': 'ok',
        'folders_created': len(folders),
        'folder_ids': folders
    })


@app.route('/api/onboardings')
@login_required
def api_onboardings():
    """API: Get onboardings list"""
    onboardings = sheets_db.get_onboardings()
    return jsonify({'onboardings': onboardings, 'status': 'ok', 'demo_mode': sheets_db.demo_mode})


@app.route('/api/onboarding/<onboarding_id>')
@login_required
def api_onboarding_detail(onboarding_id):
    """API: Get onboarding details"""
    onboarding = sheets_db.get_onboarding(onboarding_id)
    if onboarding and onboarding.get('sponsor_id'):
        onboarding['sponsor'] = sheets_db.get_sponsor(onboarding['sponsor_id'])
        onboarding['persons'] = sheets_db.get_persons_for_onboarding(onboarding_id)
        onboarding['screenings'] = sheets_db.get_screenings(onboarding_id)
        onboarding['risk_assessment'] = sheets_db.get_risk_assessment(onboarding_id)
    return jsonify({'onboarding': onboarding or {}, 'status': 'ok'})


@app.route('/api/onboarding/<onboarding_id>', methods=['DELETE'])
@login_required
def api_delete_onboarding(onboarding_id):
    """API: Delete an onboarding"""
    user = get_current_user()

    # Check if onboarding exists
    onboarding = sheets_db.get_onboarding(onboarding_id)
    if not onboarding:
        return jsonify({'status': 'error', 'message': 'Onboarding not found'}), 404

    # Only allow deletion by the assigned user, admin, or if still in early phases
    is_owner = onboarding.get('assigned_to') == user['name']
    is_admin = user['role'] == 'admin'
    current_phase = onboarding.get('current_phase', 1)
    if isinstance(current_phase, str):
        current_phase = int(current_phase)
    is_early_phase = current_phase <= 3
    is_approved = onboarding.get('status') == 'approved'

    if is_approved and not is_admin:
        return jsonify({
            'status': 'error',
            'message': 'Cannot delete approved onboardings. Contact admin.'
        }), 403

    if not (is_owner or is_admin or is_early_phase):
        return jsonify({
            'status': 'error',
            'message': 'You do not have permission to delete this onboarding'
        }), 403

    # Perform deletion
    success = sheets_db.delete_onboarding(onboarding_id)

    if success:
        logger.info(f"Onboarding {onboarding_id} deleted by {user['name']}")
        return jsonify({
            'status': 'ok',
            'message': f'Onboarding {onboarding_id} has been deleted'
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'Failed to delete onboarding'
        }), 500


@app.route('/api/onboarding/<onboarding_id>/approve', methods=['POST'])
@login_required
@role_required('mlro', 'compliance')
def api_approve(onboarding_id):
    """API: Approve, reject, or request info for onboarding"""
    from services.gdrive_audit import get_client as get_gdrive_client

    user = get_current_user()
    data = request.get_json() or {}

    action = data.get('action', 'approve')  # 'approve', 'reject', 'request_info'
    comments = data.get('comments', '')

    # Map action to status
    status_map = {
        'approve': 'approved',
        'reject': 'rejected',
        'request_info': 'pending_info'
    }

    if action not in status_map:
        return jsonify({'status': 'error', 'message': f'Invalid action: {action}'}), 400

    new_status = status_map[action]

    # Get current onboarding data
    onboarding = sheets_db.get_onboarding(onboarding_id)
    if not onboarding and onboarding_id != 'NEW':
        # Create mock onboarding for demo mode
        onboarding = {
            'onboarding_id': onboarding_id,
            'status': 'pending_mlro',
            'sponsor_name': session.get('current_sponsor', 'Demo Sponsor'),
            'fund_name': session.get('current_fund', 'Demo Fund')
        }

    # Validate MLRO can approve (compliance can only approve standard risk)
    risk_assessment = sheets_db.get_risk_assessment(onboarding_id) or {}
    risk_level = risk_assessment.get('risk_rating', 'low')

    if user['role'] == 'compliance' and risk_level in ['medium', 'high']:
        return jsonify({
            'status': 'error',
            'message': 'Only MLRO can approve medium/high risk onboardings'
        }), 403

    # Update onboarding status in Sheets
    update_data = {
        'status': new_status,
        'approval_action': action,
        'approval_comments': comments,
        'approved_by': user['name'],
        'approved_at': datetime.now().isoformat(),
        'approver_role': user['role']
    }

    sheets_db.update_onboarding(onboarding_id, update_data)

    # Save approval to audit trail in Google Drive
    gdrive_client = get_gdrive_client()
    sponsor_name = onboarding.get('sponsor_name') or session.get('current_sponsor', 'Unknown')
    fund_name = onboarding.get('fund_name') or session.get('current_fund', 'Unknown')

    audit_data = {
        'onboarding_id': onboarding_id,
        'action': action,
        'new_status': new_status,
        'comments': comments,
        'approved_by': user['name'],
        'approver_role': user['role'],
        'approved_at': datetime.now().isoformat(),
        'risk_level': risk_level
    }

    from services.gdrive_audit import save_json_audit
    save_json_audit(
        data=audit_data,
        filename=f'approval_{action}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
        sponsor_name=sponsor_name,
        fund_name=fund_name,
        phase='Phase-6-Approval'
    )

    # Send email notifications
    onboarding_data = {
        'onboarding_id': onboarding_id,
        'sponsor_name': sponsor_name,
        'fund_name': fund_name
    }

    if action == 'approve':
        notify_onboarding_decision(onboarding_data, 'approved', user['name'], comments)
    elif action == 'reject':
        notify_onboarding_decision(onboarding_data, 'rejected', user['name'], comments)

    # Store approval status in session for template access
    session['approval_status'] = new_status
    session['approval_action'] = action

    return jsonify({
        'status': 'ok',
        'action': action,
        'new_status': new_status,
        'approved_by': user['name'],
        'message': f'Onboarding {action}d successfully'
    })


@app.route('/api/fees/calculate', methods=['POST'])
@login_required
def api_calculate_fees():
    """API: Calculate dynamic fees based on fund parameters and services selected."""
    from services.fee_calculator import calculate_fees, get_available_services

    data = request.get_json() or {}

    fund_size = data.get('fund_size', 500_000_000)  # Default $500M
    services = data.get('services', ['nav', 'investor', 'accounting', 'ta', 'director', 'cosec'])
    num_investors = data.get('num_investors', 50)
    num_directors = data.get('num_directors', 2)
    complexity = data.get('complexity', 'low')
    include_setup = data.get('include_setup', True)

    # Convert fund_size to int if string
    if isinstance(fund_size, str):
        # Remove commas and currency symbols
        fund_size = int(fund_size.replace(',', '').replace('$', '').replace('£', ''))

    result = calculate_fees(
        fund_size=fund_size,
        services=services,
        num_investors=num_investors,
        num_directors=num_directors,
        complexity=complexity,
        include_setup=include_setup
    )

    return jsonify({
        'status': 'ok',
        **result
    })


@app.route('/api/fees/services', methods=['GET'])
@login_required
def api_get_services():
    """API: Get list of available services and their base fees."""
    from services.fee_calculator import get_available_services, get_setup_fees

    return jsonify({
        'status': 'ok',
        'services': get_available_services(),
        'setup_fees': get_setup_fees()
    })


@app.route('/api/report/generate/<onboarding_id>')
def api_generate_report(onboarding_id):
    """Generate PDF risk report for an onboarding."""
    report_type = request.args.get('type', 'compliance')
    save_to_drive = request.args.get('save_to_drive', 'true').lower() == 'true'

    # Get sponsor/fund from session or args
    sponsor_name = request.args.get('sponsor_name') or session.get('current_sponsor')
    fund_name = request.args.get('fund_name') or session.get('current_fund')

    try:
        result = generate_report(
            onboarding_id=onboarding_id,
            report_type=report_type,
            save_to_drive=save_to_drive,
            sponsor_name=sponsor_name,
            fund_name=fund_name
        )

        # Create response with PDF
        response = make_response(result['pdf_bytes'])
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{result["filename"]}"'

        # Add custom headers for JS to read
        if result.get('drive_result'):
            drive = result['drive_result']
            response.headers['X-Drive-Status'] = drive.get('status', 'unknown')
            if drive.get('file_id'):
                response.headers['X-Drive-File-Id'] = drive['file_id']

        response.headers['X-Demo-Mode'] = 'true' if result.get('demo_mode') else 'false'

        return response

    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        logger.exception(f"Error generating report: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to generate report'}), 500


@app.route('/api/reports/data')
@login_required
def api_reports_data():
    """API endpoint for reporting data with aggregations"""
    from datetime import datetime
    import csv
    import io

    # Get filter params
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    status_filter = request.args.get('status')
    risk_filter = request.args.get('risk_level')
    output_format = request.args.get('format', 'json')

    # Get all onboardings
    onboardings = sheets_db.get_onboardings()

    # Fallback to mock data if empty
    if not onboardings:
        onboardings = [
            {'onboarding_id': 'ONB-001', 'sponsor_name': 'Test Corp', 'fund_name': 'Fund I',
             'current_phase': 4, 'status': 'in_progress', 'risk_level': 'low',
             'created_at': '2026-01-15', 'updated_at': '2026-02-01'},
            {'onboarding_id': 'ONB-002', 'sponsor_name': 'Alpha Partners', 'fund_name': 'Growth Fund',
             'current_phase': 6, 'status': 'pending_mlro', 'risk_level': 'medium',
             'created_at': '2026-01-20', 'updated_at': '2026-02-01'},
            {'onboarding_id': 'ONB-003', 'sponsor_name': 'Beta Capital', 'fund_name': 'Value Fund',
             'current_phase': 8, 'status': 'approved', 'risk_level': 'low',
             'created_at': '2026-01-10', 'updated_at': '2026-01-25'},
        ]

    # Apply filters
    filtered = onboardings
    if status_filter:
        filtered = [o for o in filtered if o.get('status') == status_filter]
    if risk_filter:
        filtered = [o for o in filtered if o.get('risk_level') == risk_filter]

    # Get phases from workflow configuration (consistent with dashboard)
    phases = get_phases()
    phase_names = {p['num']: p['name'] for p in phases}

    # Aggregate by phase (convert current_phase to int for comparison)
    def safe_int(val, default=0):
        try:
            return int(val) if val else default
        except (ValueError, TypeError):
            return default

    by_phase = []
    for phase in phases:
        phase_num = phase['num']
        count = sum(1 for o in filtered if safe_int(o.get('current_phase')) == phase_num)
        by_phase.append({
            'phase': phase_num,
            'name': phase['name'],
            'count': count
        })

    # Aggregate by risk
    risk_counts = {'low': 0, 'medium': 0, 'high': 0}
    for o in filtered:
        risk = o.get('risk_level', 'low')
        if risk in risk_counts:
            risk_counts[risk] += 1
    by_risk = [{'rating': k, 'count': v} for k, v in risk_counts.items()]

    # Summary stats
    summary = {
        'total': len(filtered),
        'in_progress': sum(1 for o in filtered if o.get('status') == 'in_progress'),
        'pending_approval': sum(1 for o in filtered if o.get('status') in ['pending_mlro', 'pending_board']),
        'approved': sum(1 for o in filtered if o.get('status') == 'approved'),
        'rejected': sum(1 for o in filtered if o.get('status') == 'rejected'),
    }

    # CSV export
    if output_format == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Sponsor', 'Fund', 'Phase', 'Status', 'Risk', 'Created', 'Updated'])
        for o in filtered:
            writer.writerow([
                o.get('onboarding_id', ''),
                o.get('sponsor_name', ''),
                o.get('fund_name', ''),
                o.get('current_phase', ''),
                o.get('status', ''),
                o.get('risk_level', ''),
                o.get('created_at', ''),
                o.get('updated_at', '')
            ])
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=onboardings_report.csv'}
        )

    # JSON response
    return jsonify({
        'summary': summary,
        'by_phase': by_phase,
        'by_risk': by_risk,
        'onboardings': filtered
    })


# ========== Document Upload API Routes ==========

@app.route('/api/documents/upload', methods=['POST'])
@login_required
def api_upload_document():
    """Upload a document for an onboarding"""
    from services.documents import upload_document

    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file provided'}), 400

    file = request.files['file']
    onboarding_id = request.form.get('onboarding_id')
    document_type = request.form.get('document_type', 'other')

    if not onboarding_id:
        return jsonify({'status': 'error', 'message': 'onboarding_id required'}), 400

    user = get_current_user()
    result = upload_document(file, onboarding_id, document_type, uploaded_by=user['name'])

    status_code = 200 if result['status'] == 'success' else 400
    return jsonify(result), status_code


@app.route('/api/documents/<onboarding_id>')
@login_required
def api_get_documents(onboarding_id):
    """Get all documents for an onboarding"""
    from services.documents import get_documents, DOCUMENT_TYPES

    documents = get_documents(onboarding_id)
    return jsonify({
        'onboarding_id': onboarding_id,
        'documents': documents,
        'document_types': DOCUMENT_TYPES
    })


@app.route('/api/documents/delete/<document_id>', methods=['DELETE'])
@login_required
def api_delete_document(document_id):
    """Delete a document"""
    from services.documents import delete_document

    result = delete_document(document_id)
    status_code = 200 if result['status'] == 'success' else 404
    return jsonify(result), status_code


# ========== User Management API Routes ==========

@app.route('/api/users')
@login_required
@role_required('admin')
def api_list_users():
    """List all users (admin only)"""
    from services.auth import list_users, USER_ROLES
    return jsonify({
        'users': list_users(),
        'roles': USER_ROLES
    })


@app.route('/api/users', methods=['POST'])
@login_required
@role_required('admin')
def api_create_user():
    """Create a new user (admin only)"""
    from services.auth import create_user

    data = request.get_json()
    result = create_user(
        user_id=data.get('user_id'),
        name=data.get('name'),
        email=data.get('email'),
        role=data.get('role'),
        password=data.get('password')
    )

    status_code = 200 if result['status'] == 'success' else 400
    return jsonify(result), status_code


@app.route('/api/users/change-password', methods=['POST'])
@login_required
def api_change_password():
    """Change current user's password"""
    from services.auth import change_password

    user = get_current_user()
    data = request.get_json()

    result = change_password(
        user_id=user['id'],
        old_password=data.get('old_password'),
        new_password=data.get('new_password')
    )

    status_code = 200 if result['status'] == 'success' else 400
    return jsonify(result), status_code


# ========== Workflow API Routes ==========

@app.route('/api/workflow/<onboarding_id>')
@login_required
def api_workflow_status(onboarding_id):
    """Get workflow status for an onboarding"""
    from services.workflow import generate_workflow_summary, check_phase_completion

    # Get onboarding
    onboarding = sheets_db.get_onboarding(onboarding_id)
    if not onboarding:
        return jsonify({'status': 'error', 'message': 'Onboarding not found'}), 404

    # Get risk assessment if available
    risk = sheets_db.get_risk_assessment(onboarding_id)

    summary = generate_workflow_summary(onboarding, risk)

    return jsonify({
        'onboarding_id': onboarding_id,
        'workflow': summary
    })


@app.route('/api/workflow/overdue')
@login_required
def api_overdue_onboardings():
    """Get list of overdue onboardings"""
    from services.workflow import check_overdue

    onboardings = sheets_db.get_onboardings()
    overdue = check_overdue(onboardings)

    return jsonify({
        'count': len(overdue),
        'overdue': overdue
    })


# ========== KYC/CDD API Routes ==========

@app.route('/api/kyc/<onboarding_id>/checklist', methods=['GET'])
@login_required
def api_kyc_checklist(onboarding_id):
    """API: Get KYC document checklist for an onboarding"""
    from services.kyc_checklist import generate_checklist, get_checklist_progress

    # Get enquiry data (use same merge logic as phase rendering and upload)
    enquiry_id = request.args.get('enquiry_id') or session.get('current_enquiry_id')
    enquiry = None

    if enquiry_id:
        sheets_enquiry = sheets_db.get_enquiry(enquiry_id)
        mock_enquiry = MOCK_ENQUIRIES.get(enquiry_id)

        if sheets_enquiry:
            enquiry = sheets_enquiry
            # Merge principals from mock if not in sheets
            if mock_enquiry:
                for array_key in ['principals', 'gp_directors', 'initial_investors']:
                    if array_key not in enquiry or not enquiry.get(array_key):
                        enquiry[array_key] = mock_enquiry.get(array_key, [])
        else:
            enquiry = mock_enquiry

    if not enquiry:
        # Use first mock enquiry as fallback for demo
        enquiry = MOCK_ENQUIRIES.get('ENQ-001')

    # Get risk assessment from session or default
    risk_assessment = session.get('risk_assessment', {})

    # Generate checklist
    checklist = generate_checklist(enquiry, risk_assessment)
    checklist['onboarding_id'] = onboarding_id

    # Get progress
    progress = get_checklist_progress(checklist)

    return jsonify({
        'status': 'ok',
        'checklist': checklist,
        'progress': progress
    })


@app.route('/api/kyc/<onboarding_id>/upload', methods=['POST'])
@login_required
def api_kyc_upload(onboarding_id):
    """API: Upload and analyze KYC documents"""
    from services.document_review import analyze_batch
    from services.kyc_checklist import generate_checklist

    if 'files' not in request.files:
        return jsonify({'status': 'error', 'message': 'No files uploaded'}), 400

    files = request.files.getlist('files')
    if not files or all(f.filename == '' for f in files):
        return jsonify({'status': 'error', 'message': 'No files selected'}), 400

    # Get enquiry data for key parties (use same logic as phase rendering)
    enquiry_id = request.form.get('enquiry_id') or session.get('current_enquiry_id')

    # Load enquiry from Sheets first, then merge with MOCK_ENQUIRIES if needed
    enquiry = None
    if enquiry_id:
        sheets_enquiry = sheets_db.get_enquiry(enquiry_id)
        mock_enquiry = MOCK_ENQUIRIES.get(enquiry_id)

        if sheets_enquiry:
            enquiry = sheets_enquiry
            # Merge principals from mock if not in sheets
            if mock_enquiry:
                for array_key in ['principals', 'gp_directors', 'initial_investors']:
                    if array_key not in enquiry or not enquiry.get(array_key):
                        enquiry[array_key] = mock_enquiry.get(array_key, [])
        else:
            enquiry = mock_enquiry

    # Fallback to default mock
    if not enquiry:
        enquiry = MOCK_ENQUIRIES.get('ENQ-001')

    key_parties = []
    for i, p in enumerate(enquiry.get('principals', [])):
        key_parties.append({
            'person_id': f'principal_{i}',
            'name': p.get('full_name') or p.get('name')
        })

    sponsor_name = enquiry.get('sponsor_name', 'Unknown Sponsor')

    # Process each file
    import os
    from werkzeug.utils import secure_filename

    # Create uploads directory if it doesn't exist
    upload_folder = os.path.join(app.root_path, 'uploads', onboarding_id)
    os.makedirs(upload_folder, exist_ok=True)

    documents = []
    file_paths = []
    for file in files:
        if file and file.filename:
            content = file.read()
            documents.append({
                'content': content,
                'filename': file.filename,
                'mime_type': file.content_type or 'application/octet-stream'
            })

            # Save file to disk
            filename = secure_filename(file.filename)
            file_path = os.path.join(upload_folder, filename)
            with open(file_path, 'wb') as f:
                f.write(content)
            file_paths.append(f'uploads/{onboarding_id}/{filename}')

    # Analyze all documents
    results = analyze_batch(documents, key_parties, sponsor_name)

    # Store results in session for now (in production, save to DB)
    if 'kyc_documents' not in session:
        session['kyc_documents'] = {}

    processed_results = []
    for i, result in enumerate(results):
        doc_id = f"DOC-{datetime.now().strftime('%Y%m%d%H%M%S')}-{i:03d}"
        doc_record = {
            'document_id': doc_id,
            'onboarding_id': onboarding_id,
            'filename': result['filename'],
            'file_path': file_paths[i],
            'analysis': result['analysis'],
            'suggested_assignment': result['suggested_assignment'],
            'uploaded_at': datetime.now().isoformat(),
            'uploaded_by': get_current_user()['name']
        }
        session['kyc_documents'][doc_id] = doc_record
        processed_results.append(doc_record)

    session.modified = True

    return jsonify({
        'status': 'ok',
        'message': f'Analyzed {len(results)} documents',
        'documents': processed_results
    })


@app.route('/api/kyc/<onboarding_id>/document/<doc_id>/reassign', methods=['POST'])
@login_required
def api_kyc_reassign(onboarding_id, doc_id):
    """API: Reassign a document to a different checklist slot"""
    logger.info(f"[REASSIGN API] onboarding_id={onboarding_id}, doc_id={doc_id}")

    data = request.get_json()
    if not data:
        logger.error("[REASSIGN API] No JSON payload")
        return jsonify({'status': 'error', 'message': 'Invalid JSON payload'}), 400

    assignment_type = data.get('type')  # 'sponsor' or 'key_party'
    if assignment_type not in ('sponsor', 'key_party'):
        logger.error(f"[REASSIGN API] Invalid assignment type: {assignment_type}")
        return jsonify({'status': 'error', 'message': 'Invalid assignment type'}), 400

    document_type = data.get('document_type')
    person_id = data.get('person_id')  # For key_party assignments
    logger.info(f"[REASSIGN API] assignment_type={assignment_type}, document_type={document_type}, person_id={person_id}")

    # Get document from session
    all_docs = session.get('kyc_documents', {})
    logger.info(f"[REASSIGN API] Total docs in session: {len(all_docs)}, doc_ids: {list(all_docs.keys())}")

    doc = all_docs.get(doc_id)
    if not doc:
        logger.error(f"[REASSIGN API] Document {doc_id} not found in session")
        return jsonify({'status': 'error', 'message': 'Document not found'}), 404

    if doc.get('onboarding_id') != onboarding_id:
        logger.error(f"[REASSIGN API] Document {doc_id} belongs to different onboarding: {doc.get('onboarding_id')} != {onboarding_id}")
        return jsonify({'status': 'error', 'message': 'Document not found'}), 404

    # Update assignment
    doc['suggested_assignment'] = {
        'type': assignment_type,
        'document_type': document_type,
        'person_id': person_id,
        'confidence': 1.0,  # Manual assignment = 100% confidence
        'manually_assigned': True
    }

    session.modified = True
    logger.info(f"[REASSIGN API] Successfully reassigned document {doc_id}")

    return jsonify({
        'status': 'ok',
        'message': 'Document reassigned',
        'document': doc
    })


@app.route('/api/debug/session-documents', methods=['GET'])
@login_required
def debug_session_documents():
    """Debug endpoint to check what documents are in session"""
    all_docs = session.get('kyc_documents', {})
    return jsonify({
        'total': len(all_docs),
        'document_ids': list(all_docs.keys()),
        'documents': [{
            'document_id': doc_id,
            'onboarding_id': doc.get('onboarding_id'),
            'filename': doc.get('filename')
        } for doc_id, doc in all_docs.items()]
    })


@app.route('/api/kyc/<onboarding_id>/documents', methods=['GET'])
@login_required
def get_kyc_documents(onboarding_id):
    """Get all KYC documents for a specific onboarding"""
    all_docs = session.get('kyc_documents', {})

    # If onboarding_id is not 'NEW', migrate any documents from 'NEW' to this onboarding_id
    # This handles the case where documents were uploaded during initial onboarding creation
    if onboarding_id != 'NEW':
        migrated = False
        for doc_id, doc in all_docs.items():
            if doc.get('onboarding_id') == 'NEW':
                doc['onboarding_id'] = onboarding_id
                migrated = True
                logger.info(f"Migrated document {doc_id} from NEW to {onboarding_id}")

        if migrated:
            session.modified = True

    # Filter documents by onboarding_id
    onboarding_docs = [
        doc for doc_id, doc in all_docs.items()
        if doc.get('onboarding_id') == onboarding_id
    ]

    return jsonify({
        'status': 'ok',
        'documents': onboarding_docs
    })


@app.route('/api/kyc/<onboarding_id>/document/<doc_id>/override', methods=['POST'])
@login_required
def api_kyc_override(onboarding_id, doc_id):
    """API: Override a warning on a document"""
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'Invalid JSON payload'}), 400

    reason = data.get('reason')

    if not reason:
        return jsonify({'status': 'error', 'message': 'Override reason required'}), 400

    # Get document from session
    doc = session.get('kyc_documents', {}).get(doc_id)
    if not doc:
        return jsonify({'status': 'error', 'message': 'Document not found'}), 404

    if doc.get('onboarding_id') != onboarding_id:
        return jsonify({'status': 'error', 'message': 'Document not found'}), 404

    # Apply override
    doc['override'] = {
        'applied': True,
        'reason': reason,
        'by': get_current_user()['name'],
        'at': datetime.now().isoformat()
    }

    # Update overall status
    doc['analysis']['overall_status'] = 'pass'

    session.modified = True

    return jsonify({
        'status': 'ok',
        'message': 'Override applied',
        'document': doc
    })


@app.route('/api/onboarding/<onboarding_id>/documents/status', methods=['GET'])
@login_required
def get_document_status(onboarding_id):
    """Get current status of all documents."""
    try:
        # Get documents from session (POC uses session storage)
        all_documents = session.get('kyc_documents', {})

        # Filter by onboarding_id
        onboarding_docs = [
            {
                'id': doc_id,
                'status': doc.get('analysis', {}).get('overall_status', 'Pending Review'),
                'filename': doc.get('filename', 'Unknown')
            }
            for doc_id, doc in all_documents.items()
            if doc.get('onboarding_id') == onboarding_id
        ]

        # Map status values to display format
        status_map = {
            'pass': 'Verified',
            'review_needed': 'Pending Review',
            'fail': 'Rejected'
        }

        for doc in onboarding_docs:
            doc['status'] = status_map.get(doc['status'], 'Pending Review')

        # Calculate summary
        total = len(onboarding_docs)
        verified = sum(1 for d in onboarding_docs if d.get('status') == 'Verified')
        pending = sum(1 for d in onboarding_docs if d.get('status') == 'Pending Review')
        progress = (verified / total * 100) if total > 0 else 0

        return jsonify({
            'success': True,
            'documents': onboarding_docs,
            'summary': {
                'total': total,
                'verified': verified,
                'pending': pending,
                'progress': round(progress, 1)
            }
        })

    except Exception as e:
        logger.error(f"Error getting document status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/onboarding/<onboarding_id>/requirements', methods=['GET'])
@login_required
def api_get_requirements(onboarding_id):
    """Get all document requirements with fulfillment status."""
    try:
        sheets = get_sheets_client()

        # Get all requirements for this onboarding
        requirements = sheets.query('DocumentRequirements',
                                   filters={'onboarding_id': onboarding_id})

        # Enrich with document details if uploaded
        for req in requirements:
            if req.get('uploaded_doc_id'):
                doc = sheets.query('Documents',
                                  filters={'doc_id': req['uploaded_doc_id']})
                if doc:
                    req['document'] = doc[0]

        # Group by person
        grouped = {}
        for req in requirements:
            person = req['person_name']
            if person not in grouped:
                grouped[person] = {
                    'person_name': person,
                    'person_role': req['person_role'],
                    'requirements': []
                }
            grouped[person]['requirements'].append(req)

        return jsonify({
            'success': True,
            'requirements': list(grouped.values())
        })
    except Exception as e:
        logger.error(f"Error fetching requirements: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/onboarding/<onboarding_id>/requirements/generate', methods=['POST'])
@login_required
def api_generate_requirements(onboarding_id):
    """Generate document requirements for all principals."""
    try:
        requirements = generate_document_requirements(onboarding_id)
        return jsonify({
            'success': True,
            'requirements': requirements,
            'count': len(requirements)
        })
    except Exception as e:
        logger.error(f"Error generating requirements: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/onboarding/<onboarding_id>/documents', methods=['POST'])
@login_required
def api_upload_documents(onboarding_id):
    """Upload document and optionally link to requirement."""
    from datetime import datetime
    from werkzeug.utils import secure_filename
    import uuid
    import os

    try:
        sheets = get_sheets_client()

        # Get uploaded file
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Empty filename'}), 400

        # Get optional assignment parameters
        person_name = request.form.get('person_name', '')
        doc_type = request.form.get('doc_type', '')

        # Generate document ID and secure filename
        doc_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        file_size = 0

        # Save file (for now, save to static/samples/ - later integrate with Google Drive)
        upload_folder = os.path.join(app.root_path, 'static', 'samples')
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        file_size = os.path.getsize(file_path)

        # Create document record
        document = {
            'doc_id': doc_id,
            'onboarding_id': onboarding_id,
            'filename': filename,
            'file_path': f'static/samples/{filename}',
            'fulfills_requirement_id': '',
            'uploaded_at': datetime.now().isoformat(),
            'file_size': str(file_size)
        }

        # If assigned, link to requirement
        if person_name and doc_type:
            # Find matching requirement
            requirements = sheets.query('DocumentRequirements', filters={
                'onboarding_id': onboarding_id,
                'person_name': person_name,
                'doc_type': doc_type
            })

            if requirements:
                requirement = requirements[0]
                requirement_id = requirement['requirement_id']

                # Link document to requirement
                document['fulfills_requirement_id'] = requirement_id

                # Update requirement status
                sheets.update('DocumentRequirements', requirement_id, {
                    'uploaded_doc_id': doc_id,
                    'status': 'submitted',
                    'uploaded_at': datetime.now().isoformat()
                })

        # Save document to database
        sheets.insert('Documents', document)

        return jsonify({
            'success': True,
            'document': document
        })

    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/onboarding/<onboarding_id>/document/<doc_id>', methods=['GET'])
@login_required
def get_document_detail(onboarding_id, doc_id):
    """Get full document details for viewing."""
    try:
        # Get document from session
        all_documents = session.get('kyc_documents', {})
        doc = all_documents.get(doc_id)

        if not doc:
            return jsonify({
                'success': False,
                'error': 'Document not found'
            }), 404

        if doc.get('onboarding_id') != onboarding_id:
            return jsonify({
                'success': False,
                'error': 'Document not found'
            }), 404

        return jsonify({
            'success': True,
            'document': doc
        })

    except Exception as e:
        logger.error(f"Error fetching document {doc_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/documents/<doc_id>/view', methods=['GET'])
@login_required
def api_view_document(doc_id):
    """Serve PDF file for viewing."""
    from flask import send_file
    import os

    try:
        # Check session documents (KYC uploads with AI analysis)
        session_docs = session.get('kyc_documents', {})
        if doc_id in session_docs:
            document = session_docs[doc_id]
            file_path = os.path.join(app.root_path, document['file_path'])

            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return jsonify({'success': False, 'error': 'File not found on disk'}), 404

            return send_file(file_path, mimetype='application/pdf')

        # Document not found in session
        logger.error(f"Document {doc_id} not found in session")
        return jsonify({'success': False, 'error': 'Document not found'}), 404

    except Exception as e:
        logger.error(f"Error viewing document: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/onboarding/<onboarding_id>/save-progress', methods=['POST'])
@login_required
def save_onboarding_progress(onboarding_id):
    """Save onboarding progress without completing the phase."""
    try:
        data = request.get_json() or {}
        phase = data.get('phase', 5)

        # Save phase-specific data to session
        progress_key = f'onboarding_{onboarding_id}_progress'
        if progress_key not in session:
            session[progress_key] = {}

        # Store the data
        session[progress_key][f'phase_{phase}'] = {
            'saved_at': datetime.now().isoformat(),
            'data': data
        }
        session.modified = True

        logger.info(f"Saved progress for onboarding {onboarding_id}, phase {phase}")

        return jsonify({
            'status': 'ok',
            'message': 'Progress saved successfully'
        })

    except Exception as e:
        logger.error(f"Error saving progress: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/onboarding/<onboarding_id>/principals/<principal_id>', methods=['GET'])
@login_required
def api_get_principal(onboarding_id, principal_id):
    """Get principal details."""
    try:
        sheets = get_sheets_client()
        principals = sheets.query('FundPrincipals', filters={
            'onboarding_id': onboarding_id,
            'principal_id': principal_id
        })

        if not principals:
            return jsonify({'success': False, 'error': 'Principal not found'}), 404

        return jsonify({
            'success': True,
            'principal': principals[0]
        })
    except Exception as e:
        logger.error(f"Error fetching principal: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/onboarding/<onboarding_id>/principals/<principal_id>', methods=['DELETE'])
@login_required
def api_delete_principal(onboarding_id, principal_id):
    """Delete a principal."""
    try:
        sheets = get_sheets_client()
        sheets.delete('FundPrincipals', principal_id)

        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error deleting principal: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/onboarding/<onboarding_id>/principals/<principal_id>', methods=['PUT'])
@login_required
def api_update_principal(onboarding_id, principal_id):
    """Update principal details."""
    try:
        sheets = get_sheets_client()
        data = request.get_json()

        sheets.update('FundPrincipals', principal_id, data)

        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error updating principal: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/onboarding/<onboarding_id>/principals', methods=['POST'])
@login_required
def api_add_principal(onboarding_id):
    """Add a new principal."""
    try:
        sheets = get_sheets_client()
        data = request.get_json()

        # Add onboarding_id to the data
        data['onboarding_id'] = onboarding_id

        # Generate a principal_id if not provided
        if 'principal_id' not in data:
            import uuid
            data['principal_id'] = f"principal_{uuid.uuid4().hex[:8]}"

        # Create the principal
        sheets.create('FundPrincipals', data)

        return jsonify({'success': True, 'principal_id': data['principal_id']})
    except Exception as e:
        logger.error(f"Error adding principal: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/kyc/<onboarding_id>/signoff', methods=['POST'])
@login_required
def api_kyc_signoff(onboarding_id):
    """API: KYC documentation sign-off (with optional MLRO/MLCO override)"""
    from services.kyc_checklist import get_checklist_progress

    data = request.get_json() or {}
    current_user = get_current_user()

    # Check all documents are complete
    docs = session.get('kyc_documents', {})

    # Build sign-off record
    signoff_data = {
        'onboarding_id': onboarding_id,
        'signed_off_by': current_user['name'],
        'signed_off_by_role': current_user.get('role', ''),
        'signed_off_at': datetime.now().isoformat(),
        'document_count': len(docs)
    }

    # Handle MLRO/MLCO override
    if data.get('mlro_override'):
        if current_user.get('role') not in ['mlro', 'compliance']:
            return jsonify({
                'status': 'error',
                'message': 'Only MLRO/MLCO can override documentation requirements'
            }), 403

        justification = data.get('justification', '').strip()
        if not justification or len(justification) < 50:
            return jsonify({
                'status': 'error',
                'message': 'MLRO override requires detailed justification (minimum 50 characters)'
            }), 400

        signoff_data['mlro_override'] = {
            'justification': justification,
            'outstanding_documents': data.get('outstanding_documents', []),
            'override_by': current_user['name'],
            'override_at': datetime.now().isoformat()
        }
        logger.info(f"MLRO/MLCO override applied for {onboarding_id} by {current_user['name']}")

    session['kyc_signed_off'] = signoff_data
    session.modified = True

    return jsonify({
        'status': 'ok',
        'message': 'KYC documentation signed off',
        'signoff': signoff_data
    })


# ========== Helper Functions ==========

def generate_document_requirements(onboarding_id):
    """Generate document requirements for all fund principals."""
    from datetime import datetime
    import uuid

    sheets = get_sheets_client()

    # Get all principals for this onboarding
    principals_data = sheets.query('FundPrincipals',
                                   filters={'onboarding_id': onboarding_id})

    requirements = []

    for principal in principals_data:
        person_name = principal.get('name', '')
        person_role = principal.get('role', '')

        # All principals need passport and proof of address
        for doc_type in ['passport', 'proof_of_address']:
            requirement = {
                'requirement_id': str(uuid.uuid4()),
                'onboarding_id': onboarding_id,
                'person_name': person_name,
                'person_role': person_role,
                'doc_type': doc_type,
                'status': 'outstanding',
                'uploaded_doc_id': '',
                'uploaded_at': '',
                'created_at': datetime.now().isoformat()
            }
            requirements.append(requirement)

        # Only partners/UBOs need source of wealth
        if person_role in ['Managing Partner', 'Partner', 'UBO', 'Beneficial Owner']:
            requirement = {
                'requirement_id': str(uuid.uuid4()),
                'onboarding_id': onboarding_id,
                'person_name': person_name,
                'person_role': person_role,
                'doc_type': 'source_of_wealth',
                'status': 'outstanding',
                'uploaded_doc_id': '',
                'uploaded_at': '',
                'created_at': datetime.now().isoformat()
            }
            requirements.append(requirement)

    # Save all requirements to database
    for req in requirements:
        sheets.insert('DocumentRequirements', req)

    return requirements


def get_phases():
    """Get workflow phases configuration"""
    return [
        {'num': 1, 'name': 'Enquiry', 'icon': 'bi-clipboard-check', 'description': 'Merged enquiry, sponsor, and principals'},
        {'num': 2, 'name': 'Fund', 'icon': 'bi-diagram-3', 'description': 'Fund vehicles and GP setup'},
        {'num': 3, 'name': 'Screening', 'icon': 'bi-search', 'description': 'PEP, Sanctions, Risk assessment'},
        {'num': 4, 'name': 'KYC & CDD', 'icon': 'bi-file-earmark-check', 'description': 'Document collection and AI review'},
        {'num': 5, 'name': 'Approval', 'icon': 'bi-check-circle', 'description': 'MLRO and Board sign-off'},
        {'num': 6, 'name': 'Commercial', 'icon': 'bi-currency-pound', 'description': 'Engagement letter execution'},
        {'num': 7, 'name': 'Complete', 'icon': 'bi-flag', 'description': 'Onboarding finalization'}
    ]


# ========== Error Handlers ==========

@app.errorhandler(404)
def not_found(e):
    # Return JSON for API endpoints
    if request.path.startswith('/api/'):
        return jsonify({'status': 'error', 'message': 'Endpoint not found'}), 404
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(e):
    logger.error(f'Server error: {e}')
    # Return JSON for API endpoints
    if request.path.startswith('/api/'):
        return jsonify({'status': 'error', 'message': 'Internal server error', 'details': str(e)}), 500
    return render_template('errors/500.html'), 500


@app.errorhandler(Exception)
def handle_exception(e):
    """Catch-all exception handler for API endpoints"""
    logger.error(f'Unhandled exception: {e}', exc_info=True)
    if request.path.startswith('/api/'):
        return jsonify({'status': 'error', 'message': str(e)}), 500
    # For non-API routes, re-raise to trigger the 500 handler
    raise e


# ========== Startup ==========

def init_app():
    """Initialize application - ensure schema and seed data."""
    sheets_db.ensure_schema()
    sheets_db.seed_initial_data()
    logger.info(f"App initialized - Sheets demo_mode: {sheets_db.demo_mode}")

# Run initialization
init_app()


# ========== Main ==========

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
