/**
 * Client Onboarding System - Main JavaScript
 * CoreWorker AI
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(el => new bootstrap.Tooltip(el));

    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 5000);
    });

    // Form validation
    const forms = document.querySelectorAll('form[data-validate]');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // Search functionality
    const searchInputs = document.querySelectorAll('input[type="search"]');
    searchInputs.forEach(input => {
        input.addEventListener('input', debounce(function(e) {
            const query = e.target.value.toLowerCase();
            const table = document.querySelector('.onboarding-table tbody');
            if (!table) return;

            const rows = table.querySelectorAll('tr');
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(query) ? '' : 'none';
            });
        }, 300));
    });

    // Status filter
    const statusFilter = document.querySelector('select[name="status_filter"]');
    if (statusFilter) {
        statusFilter.addEventListener('change', function(e) {
            const status = e.target.value;
            const table = document.querySelector('.onboarding-table tbody');
            if (!table) return;

            const rows = table.querySelectorAll('tr');
            rows.forEach(row => {
                if (!status) {
                    row.style.display = '';
                    return;
                }
                const badge = row.querySelector('.badge-status-' + status);
                row.style.display = badge ? '' : 'none';
            });
        });
    }
});

// Utility: Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Utility: Format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount);
}

// Utility: Format date
function formatDate(dateString) {
    const options = { year: 'numeric', month: 'short', day: 'numeric' };
    return new Date(dateString).toLocaleDateString('en-GB', options);
}

// Fund Principals Management
async function viewPrincipal(onboardingId, principalId) {
    try {
        const response = await fetch(`/api/onboarding/${onboardingId}/principals/${principalId}`);
        const data = await response.json();

        if (data.success && data.principal) {
            const principal = data.principal;

            // Build modal content
            const modalContent = `
                <div class="row g-3">
                    <div class="col-md-12">
                        <h6 class="text-muted mb-3">Personal Information</h6>
                    </div>
                    <div class="col-md-6">
                        <small class="text-muted">Full Name</small>
                        <p class="mb-0"><strong>${principal.full_name || 'N/A'}</strong></p>
                    </div>
                    <div class="col-md-6">
                        <small class="text-muted">Former Names</small>
                        <p class="mb-0">${principal.former_names || 'None'}</p>
                    </div>
                    <div class="col-md-6">
                        <small class="text-muted">Date of Birth</small>
                        <p class="mb-0">${principal.dob || 'N/A'}</p>
                    </div>
                    <div class="col-md-6">
                        <small class="text-muted">Nationality</small>
                        <p class="mb-0">${principal.nationality || 'N/A'}</p>
                    </div>
                    <div class="col-md-12">
                        <small class="text-muted">Residential Address</small>
                        <p class="mb-0">${principal.residential_address || 'N/A'}</p>
                    </div>
                    <div class="col-md-6">
                        <small class="text-muted">Country of Residence</small>
                        <p class="mb-0">${principal.country_of_residence || 'N/A'}</p>
                    </div>
                    <div class="col-md-6">
                        <small class="text-muted">Position</small>
                        <p class="mb-0"><span class="badge bg-info">${principal.position ? principal.position.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()) : 'N/A'}</span></p>
                    </div>
                    <div class="col-md-6">
                        <small class="text-muted">Source</small>
                        <p class="mb-0"><span class="badge bg-secondary">${principal.source ? principal.source.charAt(0).toUpperCase() + principal.source.slice(1) : 'N/A'}</span></p>
                    </div>
                </div>
            `;

            // Create or update modal
            let modal = document.getElementById('viewPrincipalModal');
            if (!modal) {
                const modalHtml = `
                    <div class="modal fade" id="viewPrincipalModal" tabindex="-1">
                        <div class="modal-dialog modal-lg">
                            <div class="modal-content">
                                <div class="modal-header">
                                    <h5 class="modal-title"><i class="bi bi-person me-2"></i>Principal Details</h5>
                                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                                </div>
                                <div class="modal-body" id="viewPrincipalModalBody"></div>
                                <div class="modal-footer">
                                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                document.body.insertAdjacentHTML('beforeend', modalHtml);
                modal = document.getElementById('viewPrincipalModal');
            }

            document.getElementById('viewPrincipalModalBody').innerHTML = modalContent;
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
        } else {
            alert('Error loading principal details');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error loading principal details');
    }
}

async function editPrincipal(onboardingId, principalId) {
    try {
        const response = await fetch(`/api/onboarding/${onboardingId}/principals/${principalId}`);
        const data = await response.json();

        if (data.success && data.principal) {
            const principal = data.principal;

            // Build edit form
            const modalContent = `
                <form id="editPrincipalForm">
                    <div class="row g-3">
                        <div class="col-md-12">
                            <label class="form-label">Full Name <span class="text-danger">*</span></label>
                            <input type="text" class="form-control" name="full_name" value="${principal.full_name || ''}" required>
                        </div>
                        <div class="col-md-12">
                            <label class="form-label">Former Names</label>
                            <input type="text" class="form-control" name="former_names" value="${principal.former_names || ''}">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Date of Birth</label>
                            <input type="date" class="form-control" name="dob" value="${principal.dob || ''}">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Nationality</label>
                            <input type="text" class="form-control" name="nationality" value="${principal.nationality || ''}">
                        </div>
                        <div class="col-md-12">
                            <label class="form-label">Residential Address</label>
                            <textarea class="form-control" name="residential_address" rows="2">${principal.residential_address || ''}</textarea>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Country of Residence</label>
                            <input type="text" class="form-control" name="country_of_residence" value="${principal.country_of_residence || ''}">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Position</label>
                            <select class="form-select" name="position">
                                <option value="director" ${principal.position === 'director' ? 'selected' : ''}>GP Director</option>
                                <option value="fund_director" ${principal.position === 'fund_director' ? 'selected' : ''}>Fund Director</option>
                                <option value="independent_director" ${principal.position === 'independent_director' ? 'selected' : ''}>Independent Director</option>
                                <option value="investment_committee" ${principal.position === 'investment_committee' ? 'selected' : ''}>Investment Committee</option>
                            </select>
                        </div>
                    </div>
                </form>
            `;

            // Create or update modal
            let modal = document.getElementById('editPrincipalModal');
            if (!modal) {
                const modalHtml = `
                    <div class="modal fade" id="editPrincipalModal" tabindex="-1">
                        <div class="modal-dialog modal-lg">
                            <div class="modal-content">
                                <div class="modal-header">
                                    <h5 class="modal-title"><i class="bi bi-pencil me-2"></i>Edit Principal</h5>
                                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                                </div>
                                <div class="modal-body" id="editPrincipalModalBody"></div>
                                <div class="modal-footer">
                                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                    <button type="button" class="btn btn-primary" onclick="savePrincipal('${onboardingId}', '${principalId}')">
                                        <i class="bi bi-save me-1"></i> Save Changes
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                document.body.insertAdjacentHTML('beforeend', modalHtml);
                modal = document.getElementById('editPrincipalModal');
            } else {
                // Update the save button onclick
                modal.querySelector('.modal-footer .btn-primary').setAttribute('onclick', `savePrincipal('${onboardingId}', '${principalId}')`);
            }

            document.getElementById('editPrincipalModalBody').innerHTML = modalContent;
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
        } else {
            alert('Error loading principal details');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error loading principal details');
    }
}

async function savePrincipal(onboardingId, principalId) {
    const form = document.getElementById('editPrincipalForm');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    try {
        const response = await fetch(`/api/onboarding/${onboardingId}/principals/${principalId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (result.success) {
            // Close modal and reload page
            const modal = bootstrap.Modal.getInstance(document.getElementById('editPrincipalModal'));
            modal.hide();
            location.reload();
        } else {
            alert('Error saving principal: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error saving principal');
    }
}

async function deletePrincipal(onboardingId, principalId, isEnquiry) {
    // Don't allow deletion of enquiry principals
    if (isEnquiry) {
        alert('Principals from the enquiry cannot be deleted. They are read-only.');
        return;
    }

    if (!confirm('Are you sure you want to delete this principal?')) {
        return;
    }

    try {
        const response = await fetch(`/api/onboarding/${onboardingId}/principals/${principalId}`, {
            method: 'DELETE'
        });

        const result = await response.json();

        if (result.success) {
            location.reload();
        } else {
            alert('Error deleting principal: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error deleting principal');
    }
}
