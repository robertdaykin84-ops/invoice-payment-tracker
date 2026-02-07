"""
Distributions Module - Flask Application

Five-phase distribution processing workflow:
  1. Initiation   - Receive and validate distribution instruction
  2. Calculation   - Calculate LP allocations and generate schedule
  3. Approval      - Four-eyes review and manager approval
  4. Distribution  - Generate notices, send payments
  5. Reconciliation - Confirm payments and update accounts
"""

import os
import logging
from datetime import datetime
from functools import wraps

from flask import (
    Flask, Blueprint, render_template, request, jsonify,
    redirect, url_for, flash, session
)
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Blueprint (templates reference 'distributions.*' routes)
# ---------------------------------------------------------------------------

distributions_bp = Blueprint(
    'distributions',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/static/distributions'
)

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24))

DEMO_MODE = os.environ.get('DEMO_MODE', 'true').lower() == 'true'

# ---------------------------------------------------------------------------
# Services (lazy init)
# ---------------------------------------------------------------------------

_data_store = None


def get_data_store():
    global _data_store
    if _data_store is None:
        from services.data_store import DataStore
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        _data_store = DataStore(data_dir=data_dir)
    return _data_store


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

from services.auth import DEMO_USERS, ROLES, get_current_user, login_required


@distributions_bp.context_processor
def inject_globals():
    """Inject user and demo_mode into all templates."""
    return {
        'demo_mode': DEMO_MODE,
        'current_user': get_current_user(),
        'roles': ROLES,
    }


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@distributions_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id') and session['user_id'] in DEMO_USERS:
        return redirect(url_for('distributions.dashboard'))

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        if user_id and user_id in DEMO_USERS:
            user = DEMO_USERS[user_id]
            session['user_id'] = user_id
            session['user_name'] = user['name']
            session['user_role'] = user['role']
            session.permanent = True
            logger.info(f"User logged in: {user['name']} ({user['role']})")
            return redirect(url_for('distributions.dashboard'))
        flash('Invalid user selection.', 'warning')

    return render_template('login.html', demo_mode=DEMO_MODE)


@distributions_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('distributions.login'))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@distributions_bp.route('/')
@login_required
def index():
    return redirect(url_for('distributions.dashboard'))


@distributions_bp.route('/dashboard')
@login_required
def dashboard():
    store = get_data_store()
    fund = store.get_fund()
    dists = store.get_distributions()

    stats = {
        'active_count': sum(1 for d in dists if d.get('status') not in ('completed', 'rejected')),
        'pending_approvals': sum(1 for d in dists if d.get('status') == 'pending_approval'),
        'completed_count': sum(1 for d in dists if d.get('status') == 'completed'),
        'total_distributed': sum(d.get('total_amount', 0) for d in dists if d.get('status') == 'completed'),
    }

    recent = sorted(dists, key=lambda d: d.get('created_at', ''), reverse=True)[:5]

    return render_template('dashboard.html', fund=fund, stats=stats, recent_distributions=recent)


# ---------------------------------------------------------------------------
# Distribution CRUD
# ---------------------------------------------------------------------------

@distributions_bp.route('/distributions')
@login_required
def list_distributions():
    store = get_data_store()
    dists = store.get_distributions()
    return render_template('distribution/list.html', distributions=dists)


@distributions_bp.route('/distributions/new', methods=['GET', 'POST'])
@login_required
def new_distribution():
    if request.method == 'POST':
        return create_distribution()
    store = get_data_store()
    fund = store.get_fund()
    lps = store.get_lps()
    return render_template('distribution/new.html', fund=fund, lps=lps)


@distributions_bp.route('/distributions/create', methods=['POST'])
@login_required
def create_distribution():
    store = get_data_store()
    user = get_current_user()
    dist_id = store.generate_id('DIST')

    dist = {
        'dist_id': dist_id,
        'distribution_type': request.form.get('distribution_type', 'dividend'),
        'total_amount': float(request.form.get('total_amount', 0)),
        'currency': request.form.get('currency', 'GBP'),
        'effective_date': request.form.get('effective_date', ''),
        'payment_date': request.form.get('payment_date', ''),
        'description': request.form.get('description', ''),
        'status': 'draft',
        'current_phase': 1,
        'created_by': user['name'] if user else 'Unknown',
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
    }
    store.create_distribution(dist)
    flash(f'Distribution {dist_id} created successfully.', 'success')
    return redirect(url_for('distributions.distribution_detail', dist_id=dist_id))


@distributions_bp.route('/distributions/<dist_id>')
@login_required
def distribution_detail(dist_id):
    store = get_data_store()
    dist = store.get_distribution(dist_id)
    if not dist:
        flash('Distribution not found.', 'danger')
        return redirect(url_for('distributions.list_distributions'))
    fund = store.get_fund()
    lps = store.get_lps()
    return render_template('distribution/detail.html', distribution=dist, fund=fund, lps=lps)


# ---------------------------------------------------------------------------
# Phase routes
# ---------------------------------------------------------------------------

@distributions_bp.route('/distributions/<dist_id>/phase/<int:phase>', methods=['GET', 'POST'])
@login_required
def distribution_phase(dist_id, phase):
    store = get_data_store()
    dist = store.get_distribution(dist_id)
    if not dist:
        flash('Distribution not found.', 'danger')
        return redirect(url_for('distributions.list_distributions'))

    fund = store.get_fund()
    lps = store.get_lps()
    user = get_current_user()

    if request.method == 'POST':
        # Handle phase progression
        from services.workflow import advance_phase
        success, msg = advance_phase(dist, phase, user, store)
        if success:
            flash(msg or f'Phase {phase} completed.', 'success')
        else:
            flash(msg or f'Cannot advance phase {phase}.', 'warning')
        return redirect(url_for('distributions.distribution_detail', dist_id=dist_id))

    return render_template(
        f'distribution/phase{phase}.html',
        distribution=dist, fund=fund, lps=lps, phase=phase
    )


# ---------------------------------------------------------------------------
# Investor Portal
# ---------------------------------------------------------------------------

@distributions_bp.route('/portal')
@login_required
def investor_portal():
    store = get_data_store()
    lps = store.get_lps()
    return render_template('portal/index.html', lps=lps)


@distributions_bp.route('/portal/<lp_id>')
@login_required
def portal_dashboard(lp_id):
    store = get_data_store()
    lp = store.get_lp(lp_id)
    if not lp:
        flash('LP not found.', 'danger')
        return redirect(url_for('distributions.investor_portal'))
    dists = store.get_distributions()
    return render_template('portal/dashboard.html', lp=lp, distributions=dists)


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

@distributions_bp.route('/reports/audit-trail')
@login_required
def audit_trail():
    store = get_data_store()
    trail = store.get_audit_trail()
    return render_template('reports/audit_trail.html', audit_trail=trail)


@distributions_bp.route('/reports/regulatory')
@login_required
def regulatory_reports():
    store = get_data_store()
    fund = store.get_fund()
    dists = store.get_distributions()
    return render_template('reports/regulatory.html', fund=fund, distributions=dists)


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

@distributions_bp.route('/api/distributions', methods=['GET'])
@login_required
def api_get_distributions():
    store = get_data_store()
    return jsonify(store.get_distributions())


@distributions_bp.route('/api/distributions/<dist_id>', methods=['GET'])
@login_required
def api_get_distribution(dist_id):
    store = get_data_store()
    dist = store.get_distribution(dist_id)
    if not dist:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(dist)


@distributions_bp.route('/api/fund', methods=['GET'])
@login_required
def api_get_fund():
    store = get_data_store()
    return jsonify(store.get_fund())


@distributions_bp.route('/api/lps', methods=['GET'])
@login_required
def api_get_lps():
    store = get_data_store()
    return jsonify(store.get_lps())


@distributions_bp.route('/api/reset', methods=['POST'])
@login_required
def api_reset():
    store = get_data_store()
    store.reset()
    return jsonify({'success': True, 'message': 'Data reset to sample state.'})


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('errors/500.html'), 500


# ---------------------------------------------------------------------------
# Register blueprint and run
# ---------------------------------------------------------------------------

app.register_blueprint(distributions_bp)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5002))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    logger.info(f"Starting Distributions module on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
