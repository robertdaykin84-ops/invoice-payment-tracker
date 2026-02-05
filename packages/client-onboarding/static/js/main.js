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
function viewPrincipal(name) {
    // TODO: Fetch principal details and show modal
    alert(`View principal: ${name}`);
}

function editPrincipal(principalId) {
    // TODO: Open edit modal with form
    alert(`Edit principal: ${principalId}`);
}

async function deletePrincipal(principalId) {
    if (!confirm('Are you sure you want to delete this principal?')) {
        return;
    }

    try {
        const response = await fetch(`/api/onboarding/principals/${principalId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            location.reload();
        } else {
            alert('Error deleting principal');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error deleting principal');
    }
}
