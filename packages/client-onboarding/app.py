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
        'regulatory_status': 'FCA Regulated',
        'fca_frn': '123456',
        'fund_name': 'Granite Capital Fund III LP',
        'fund_type': 'jpf',
        'legal_structure': 'lp',
        'target_size': '500,000,000',
        'investment_strategy': 'Mid-market buyout investments in UK and European technology and healthcare sectors. Target companies with EBITDA of $10-50M.',
        'principals': [
            {'name': 'John Smith', 'role': 'Managing Partner', 'nationality': 'British', 'ownership': '35%'},
            {'name': 'Sarah Johnson', 'role': 'Partner', 'nationality': 'British', 'ownership': '35%'},
            {'name': 'Michael Brown', 'role': 'Partner', 'nationality': 'British', 'ownership': '30%'}
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
        'regulatory_status': 'FCA Regulated',
        'fca_frn': '654321',
        'fund_name': 'Evergreen Sustainable Growth Fund LP',
        'fund_type': 'jpf',
        'legal_structure': 'lp',
        'target_size': '250,000,000',
        'investment_strategy': 'ESG-focused growth equity investments in renewable energy infrastructure and sustainable technology across Europe.',
        'principals': [
            {'name': 'Elizabeth Chen', 'role': 'CEO', 'nationality': 'British', 'ownership': '40%'},
            {'name': 'David Kumar', 'role': 'CIO', 'nationality': 'British', 'ownership': '30%'},
            {'name': 'Anna Schmidt', 'role': 'CFO', 'nationality': 'German', 'ownership': '30%'}
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
        'jurisdiction': 'other',
        'jurisdiction_other': 'Norway',
        'registration_number': 'NO 912 345 678',
        'regulatory_status': 'FSA Norway Regulated',
        'fca_frn': '',
        'fund_name': 'Nordic Technology Opportunities Fund LP',
        'fund_type': 'jpf',
        'legal_structure': 'lp',
        'target_size': '150,000,000',
        'investment_strategy': 'Early-stage and growth investments in Nordic technology companies, with focus on fintech, healthtech, and cleantech sectors.',
        'principals': [
            {'name': 'Erik Larsson', 'role': 'Founder & CEO', 'nationality': 'Norwegian', 'ownership': '50%'},
            {'name': 'Ingrid Olsen', 'role': 'Partner', 'nationality': 'Norwegian', 'ownership': '50%'}
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
    from services.gdrive_audit import save_form_data, ensure_folder_structure

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

        # Save form data to audit trail
        form_data = {key: value for key, value in request.form.items() if key != 'action'}
        audit_result = save_form_data(form_data, phase, sponsor_name, fund_name)
        logger.info(f"Audit trail save for phase {phase}: {audit_result.get('status')}")

        # On phase 1, ensure folder structure is created
        if phase == 1 and sponsor_name != 'Unknown Sponsor':
            ensure_folder_structure(sponsor_name, fund_name)

        if action == 'save':
            # Save draft - stay on current phase
            flash('Draft saved successfully.', 'success')
            return redirect(url_for('onboarding_phase', onboarding_id=onboarding_id, phase=phase))
        else:
            # Continue to next phase
            # In production, this would save data to Google Sheets
            if phase < len(phases):
                next_phase = phase + 1
                # Skip Phase 5 (EDD) if not required (for POC, always skip)
                if next_phase == 5:
                    next_phase = 6  # Skip to Approval
                    flash('EDD not required - proceeding to Approval phase.', 'info')
                else:
                    flash(f'Phase {phase} completed. Proceeding to {phases[next_phase - 1]["name"]}.', 'success')
                return redirect(url_for('onboarding_phase', onboarding_id=onboarding_id, phase=next_phase))
            else:
                flash('Onboarding complete!', 'success')
                return redirect(url_for('dashboard'))

    # Handle GET request - display form
    # Check if we're auto-populating from an enquiry
    enquiry_id = request.args.get('enquiry_id')
    enquiry = MOCK_ENQUIRIES.get(enquiry_id) if enquiry_id else None
    uploaded = request.args.get('uploaded') == '1'  # Flag if data came from uploaded document

    # Get list of pending enquiries for Phase 1 dropdown
    pending_enquiries = [e for e in MOCK_ENQUIRIES.values() if e['status'] == 'pending'] if phase == 1 else []

    return render_template(f'onboarding/phase{phase}.html',
                         onboarding_id=onboarding_id,
                         phase=phase,
                         phases=phases,
                         current_phase=current_phase,
                         enquiry=enquiry,
                         pending_enquiries=pending_enquiries,
                         uploaded=uploaded)


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


# ========== Enquiry Form Routes ==========

@app.route('/enquiry')
def enquiry_form():
    """Public enquiry form for sponsors to complete"""
    return render_template('enquiry_form.html')


@app.route('/enquiry/submit', methods=['POST'])
def submit_enquiry():
    """Handle enquiry form submission"""
    from services.gdrive_audit import save_form_data, ensure_folder_structure

    # Extract form data
    form_data = {key: value for key, value in request.form.items()}
    sponsor_name = form_data.get('sponsor_name', 'Unknown Sponsor')
    fund_name = form_data.get('fund_name', 'Unknown Fund')

    # Create folder structure and save enquiry to audit trail
    if sponsor_name != 'Unknown Sponsor':
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
    from services.gdrive_audit import save_form_data, save_api_response

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
    from services.gdrive_audit import ensure_folder_structure

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

    # Phase names
    phase_names = {
        1: 'Enquiry', 2: 'Sponsor', 3: 'Fund', 4: 'Screening',
        5: 'EDD', 6: 'Approval', 7: 'Commercial', 8: 'Complete'
    }

    # Aggregate by phase
    by_phase = []
    for phase_num in range(1, 9):
        count = sum(1 for o in filtered if o.get('current_phase') == phase_num)
        by_phase.append({
            'phase': phase_num,
            'name': phase_names[phase_num],
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
