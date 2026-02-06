/**
 * Invoice Tracker - Main JavaScript
 * Handles file uploads, form validation, AJAX requests, and UI interactions
 */

(function() {
    'use strict';

    // ========== Configuration ==========
    const CONFIG = {
        maxFileSize: 16 * 1024 * 1024, // 16MB
        allowedTypes: ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg'],
        allowedExtensions: ['.pdf', '.png', '.jpg', '.jpeg'],
        apiEndpoints: {
            upload: '/upload',
            saveInvoice: '/save-invoice',
            savePaymentDetails: '/save-payment-details',
            invoices: '/api/invoices',
            paymentDetails: '/api/payment-details',
            suppliers: '/api/suppliers',
            testConnection: '/api/test-connection'
        },
        messages: {
            uploadSuccess: 'Invoice uploaded and processed successfully!',
            uploadError: 'Failed to upload invoice. Please try again.',
            saveSuccess: 'Data saved successfully!',
            saveError: 'Failed to save data. Please try again.',
            validationError: 'Please fill in all required fields.',
            fileTypeError: 'Invalid file type. Please upload PDF, PNG, or JPG files.',
            fileSizeError: 'File is too large. Maximum size is 16MB.',
            networkError: 'Network error. Please check your connection.',
            confirmDelete: 'Are you sure you want to delete this item?',
            confirmDiscard: 'You have unsaved changes. Are you sure you want to leave?'
        }
    };

    // ========== Utility Functions ==========

    /**
     * Show a toast notification
     */
    function showToast(message, type = 'info', duration = 5000) {
        const toastContainer = getOrCreateToastContainer();

        const toast = document.createElement('div');
        toast.className = `alert alert-${type} alert-dismissible fade show`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <i class="bi bi-${getToastIcon(type)} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;

        toastContainer.appendChild(toast);

        // Auto dismiss
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 150);
        }, duration);
    }

    function getToastIcon(type) {
        const icons = {
            success: 'check-circle-fill',
            danger: 'exclamation-triangle-fill',
            warning: 'exclamation-circle-fill',
            info: 'info-circle-fill'
        };
        return icons[type] || 'info-circle-fill';
    }

    function getOrCreateToastContainer() {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.style.cssText = 'position: fixed; top: 1rem; right: 1rem; z-index: 10000; max-width: 400px;';
            document.body.appendChild(container);
        }
        return container;
    }

    /**
     * Show/hide loading overlay
     */
    function showLoading(message = 'Processing...') {
        let overlay = document.getElementById('loading-overlay');

        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'loading-overlay';
            overlay.className = 'loading-overlay';
            overlay.innerHTML = `
                <div class="loading-spinner"></div>
                <p class="loading-text">${message}</p>
            `;
            document.body.appendChild(overlay);
        } else {
            const textEl = overlay.querySelector('.loading-text');
            if (textEl) textEl.textContent = message;
        }

        overlay.classList.add('active');
    }

    function hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.remove('active');
        }
    }

    /**
     * Format currency
     */
    function formatCurrency(amount, currency = 'GBP') {
        const symbols = {
            'GBP': '£', 'USD': '$', 'EUR': '€', 'CAD': 'C$',
            'AUD': 'A$', 'JPY': '¥', 'CHF': 'CHF ', 'CNY': '¥',
            'INR': '₹', 'MXN': 'MX$'
        };
        const symbol = symbols[currency] || currency + ' ';
        return symbol + parseFloat(amount || 0).toFixed(2);
    }

    /**
     * Format date for input fields
     */
    function formatDateForInput(dateStr) {
        if (!dateStr) return '';

        // Try to parse the date
        const date = new Date(dateStr);
        if (isNaN(date.getTime())) return dateStr;

        // Return YYYY-MM-DD format
        return date.toISOString().split('T')[0];
    }

    /**
     * Validate email format
     */
    function isValidEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    }

    /**
     * Validate file
     */
    function validateFile(file) {
        if (!file) {
            return { valid: false, error: 'No file selected' };
        }

        // Check file type
        const ext = '.' + file.name.split('.').pop().toLowerCase();
        if (!CONFIG.allowedExtensions.includes(ext)) {
            return { valid: false, error: CONFIG.messages.fileTypeError };
        }

        // Check file size
        if (file.size > CONFIG.maxFileSize) {
            return { valid: false, error: CONFIG.messages.fileSizeError };
        }

        return { valid: true };
    }

    /**
     * AJAX request wrapper
     */
    async function apiRequest(url, options = {}) {
        const defaultOptions = {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            }
        };

        const mergedOptions = { ...defaultOptions, ...options };

        // Don't set Content-Type for FormData (browser will set it with boundary)
        if (!(mergedOptions.body instanceof FormData)) {
            mergedOptions.headers['Content-Type'] = 'application/json';
        }

        try {
            const response = await fetch(url, mergedOptions);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || `HTTP ${response.status}`);
            }

            return data;
        } catch (error) {
            if (error.name === 'TypeError') {
                throw new Error(CONFIG.messages.networkError);
            }
            throw error;
        }
    }

    // ========== File Upload Handler ==========

    class FileUploader {
        constructor(options = {}) {
            this.dropzone = options.dropzone;
            this.fileInput = options.fileInput;
            this.onSuccess = options.onSuccess || (() => {});
            this.onError = options.onError || (() => {});
            this.onProgress = options.onProgress || (() => {});

            this.init();
        }

        init() {
            if (this.dropzone) {
                this.setupDropzone();
            }
            if (this.fileInput) {
                this.setupFileInput();
            }
        }

        setupDropzone() {
            const dz = this.dropzone;

            // Prevent default drag behaviors
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(event => {
                dz.addEventListener(event, (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                });
            });

            // Highlight on drag
            ['dragenter', 'dragover'].forEach(event => {
                dz.addEventListener(event, () => {
                    dz.classList.add('drag-over', 'dz-drag-hover');
                });
            });

            ['dragleave', 'drop'].forEach(event => {
                dz.addEventListener(event, () => {
                    dz.classList.remove('drag-over', 'dz-drag-hover');
                });
            });

            // Handle drop
            dz.addEventListener('drop', (e) => {
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    this.handleFile(files[0]);
                }
            });

            // Click to select file
            dz.addEventListener('click', () => {
                if (this.fileInput) {
                    this.fileInput.click();
                }
            });
        }

        setupFileInput() {
            this.fileInput.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    this.handleFile(e.target.files[0]);
                }
            });
        }

        async handleFile(file) {
            // Validate file
            const validation = validateFile(file);
            if (!validation.valid) {
                this.onError(validation.error);
                showToast(validation.error, 'danger');
                return;
            }

            // Create form data
            const formData = new FormData();
            formData.append('file', file);

            // Show loading
            showLoading('Uploading and processing invoice...');
            this.onProgress('upload', 0);

            try {
                // Upload file
                const response = await fetch(CONFIG.apiEndpoints.upload, {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                hideLoading();

                if (data.success) {
                    this.onSuccess(data);

                    if (data.warning) {
                        showToast(data.warning, 'warning');
                    } else {
                        showToast(CONFIG.messages.uploadSuccess, 'success');
                    }

                    // Redirect if provided
                    if (data.redirect) {
                        setTimeout(() => {
                            window.location.href = data.redirect;
                        }, 1000);
                    }
                } else {
                    throw new Error(data.error || CONFIG.messages.uploadError);
                }
            } catch (error) {
                hideLoading();
                this.onError(error.message);
                showToast(error.message, 'danger');
            }
        }
    }

    // ========== Form Validator ==========

    class FormValidator {
        constructor(form, options = {}) {
            this.form = form;
            this.rules = options.rules || {};
            this.onValid = options.onValid || (() => {});
            this.onInvalid = options.onInvalid || (() => {});

            this.init();
        }

        init() {
            // Real-time validation on blur
            this.form.querySelectorAll('input, select, textarea').forEach(field => {
                field.addEventListener('blur', () => this.validateField(field));
                field.addEventListener('input', () => {
                    if (field.classList.contains('is-invalid')) {
                        this.validateField(field);
                    }
                });
            });

            // Form submission
            this.form.addEventListener('submit', (e) => {
                if (!this.validateAll()) {
                    e.preventDefault();
                    this.onInvalid();
                    showToast(CONFIG.messages.validationError, 'warning');

                    // Focus first invalid field
                    const firstInvalid = this.form.querySelector('.is-invalid');
                    if (firstInvalid) {
                        firstInvalid.focus();
                        firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                } else {
                    this.onValid(e);
                }
            });
        }

        validateField(field) {
            const name = field.name;
            const value = field.value.trim();
            let isValid = true;
            let message = '';

            // Required check
            if (field.hasAttribute('required') && !value) {
                isValid = false;
                message = 'This field is required';
            }

            // Email validation
            if (isValid && field.type === 'email' && value && !isValidEmail(value)) {
                isValid = false;
                message = 'Please enter a valid email address';
            }

            // Number validation
            if (isValid && field.type === 'number' && value) {
                const num = parseFloat(value);
                const min = field.getAttribute('min');
                const max = field.getAttribute('max');

                if (min !== null && num < parseFloat(min)) {
                    isValid = false;
                    message = `Value must be at least ${min}`;
                }
                if (max !== null && num > parseFloat(max)) {
                    isValid = false;
                    message = `Value must be at most ${max}`;
                }
            }

            // Custom rules
            if (isValid && this.rules[name]) {
                const rule = this.rules[name];
                if (typeof rule === 'function') {
                    const result = rule(value, this.form);
                    if (result !== true) {
                        isValid = false;
                        message = result || 'Invalid value';
                    }
                }
            }

            // Update field state
            this.setFieldState(field, isValid, message);
            return isValid;
        }

        validateAll() {
            let isValid = true;

            this.form.querySelectorAll('input, select, textarea').forEach(field => {
                if (!this.validateField(field)) {
                    isValid = false;
                }
            });

            return isValid;
        }

        setFieldState(field, isValid, message = '') {
            const feedback = field.nextElementSibling;

            if (isValid) {
                field.classList.remove('is-invalid');
                field.classList.add('is-valid');
            } else {
                field.classList.remove('is-valid');
                field.classList.add('is-invalid');

                if (feedback && feedback.classList.contains('invalid-feedback')) {
                    feedback.textContent = message;
                }
            }
        }

        reset() {
            this.form.querySelectorAll('.is-valid, .is-invalid').forEach(field => {
                field.classList.remove('is-valid', 'is-invalid');
            });
        }
    }

    // ========== Confirmation Dialog ==========

    function confirm(message, options = {}) {
        return new Promise((resolve) => {
            const title = options.title || 'Confirm';
            const confirmText = options.confirmText || 'Confirm';
            const cancelText = options.cancelText || 'Cancel';
            const type = options.type || 'primary';

            // Create modal
            const modalId = 'confirm-modal-' + Date.now();
            const modalHtml = `
                <div class="modal fade" id="${modalId}" tabindex="-1">
                    <div class="modal-dialog modal-dialog-centered">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">${title}</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <p class="mb-0">${message}</p>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">${cancelText}</button>
                                <button type="button" class="btn btn-${type}" id="${modalId}-confirm">${confirmText}</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            document.body.insertAdjacentHTML('beforeend', modalHtml);

            const modalEl = document.getElementById(modalId);
            const modal = new bootstrap.Modal(modalEl);

            const confirmBtn = document.getElementById(`${modalId}-confirm`);

            confirmBtn.addEventListener('click', () => {
                modal.hide();
                resolve(true);
            });

            modalEl.addEventListener('hidden.bs.modal', () => {
                modalEl.remove();
                resolve(false);
            });

            modal.show();
        });
    }

    // ========== Auto-populate Fields ==========

    function populateForm(form, data) {
        if (!form || !data) return;

        Object.keys(data).forEach(key => {
            const field = form.querySelector(`[name="${key}"]`);
            if (field) {
                let value = data[key];

                // Format dates for date inputs
                if (field.type === 'date' && value) {
                    value = formatDateForInput(value);
                }

                // Handle select elements
                if (field.tagName === 'SELECT') {
                    const option = field.querySelector(`option[value="${value}"]`);
                    if (option) {
                        field.value = value;
                    }
                } else {
                    field.value = value || '';
                }

                // Trigger change event
                field.dispatchEvent(new Event('change', { bubbles: true }));
            }
        });
    }

    // ========== Table Enhancements ==========

    function initTables() {
        // Add sorting to tables with data-sortable
        document.querySelectorAll('table[data-sortable]').forEach(table => {
            const headers = table.querySelectorAll('th[data-sort]');
            headers.forEach(header => {
                header.style.cursor = 'pointer';
                header.addEventListener('click', () => sortTable(table, header));
            });
        });

        // Add search functionality
        document.querySelectorAll('[data-table-search]').forEach(input => {
            const tableId = input.dataset.tableSearch;
            const table = document.getElementById(tableId);
            if (table) {
                input.addEventListener('input', () => filterTable(table, input.value));
            }
        });
    }

    function sortTable(table, header) {
        const column = header.dataset.sort;
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const isAsc = header.classList.contains('sort-asc');

        // Remove sort classes from all headers
        table.querySelectorAll('th').forEach(th => {
            th.classList.remove('sort-asc', 'sort-desc');
        });

        // Sort rows
        rows.sort((a, b) => {
            const aVal = a.querySelector(`td:nth-child(${column})`).textContent.trim();
            const bVal = b.querySelector(`td:nth-child(${column})`).textContent.trim();

            // Try numeric sort first
            const aNum = parseFloat(aVal.replace(/[^0-9.-]/g, ''));
            const bNum = parseFloat(bVal.replace(/[^0-9.-]/g, ''));

            if (!isNaN(aNum) && !isNaN(bNum)) {
                return isAsc ? bNum - aNum : aNum - bNum;
            }

            // Fall back to string sort
            return isAsc ? bVal.localeCompare(aVal) : aVal.localeCompare(bVal);
        });

        // Update DOM
        rows.forEach(row => tbody.appendChild(row));
        header.classList.add(isAsc ? 'sort-desc' : 'sort-asc');
    }

    function filterTable(table, query) {
        const tbody = table.querySelector('tbody');
        const rows = tbody.querySelectorAll('tr');
        const lowerQuery = query.toLowerCase();

        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(lowerQuery) ? '' : 'none';
        });
    }

    // ========== Unsaved Changes Warning ==========

    function trackUnsavedChanges(form) {
        let hasChanges = false;
        const initialData = new FormData(form);

        form.addEventListener('input', () => {
            hasChanges = true;
        });

        form.addEventListener('submit', () => {
            hasChanges = false;
        });

        window.addEventListener('beforeunload', (e) => {
            if (hasChanges) {
                e.preventDefault();
                e.returnValue = CONFIG.messages.confirmDiscard;
                return CONFIG.messages.confirmDiscard;
            }
        });
    }

    // ========== Copy to Clipboard ==========

    async function copyToClipboard(text, successMessage = 'Copied to clipboard!') {
        try {
            await navigator.clipboard.writeText(text);
            showToast(successMessage, 'success', 2000);
            return true;
        } catch (err) {
            showToast('Failed to copy to clipboard', 'danger');
            return false;
        }
    }

    // ========== Initialize on DOM Ready ==========

    function init() {
        // Initialize Dropzone if exists
        const dropzoneEl = document.getElementById('invoice-dropzone');
        const fileInput = document.getElementById('file-input');

        if (dropzoneEl) {
            // Check if Dropzone.js is loaded (from upload page)
            if (typeof Dropzone !== 'undefined') {
                // Dropzone.js handles everything
                console.log('Dropzone.js detected, using native implementation');
            } else {
                // Use our custom uploader
                new FileUploader({
                    dropzone: dropzoneEl,
                    fileInput: fileInput,
                    onSuccess: (data) => {
                        console.log('Upload successful:', data);
                    },
                    onError: (error) => {
                        console.error('Upload error:', error);
                    }
                });
            }
        }

        // Initialize form validation
        document.querySelectorAll('form[data-validate]').forEach(form => {
            new FormValidator(form, {
                rules: {
                    due_date: (value, form) => {
                        const invoiceDate = form.querySelector('[name="invoice_date"]')?.value;
                        if (invoiceDate && value && new Date(value) < new Date(invoiceDate)) {
                            return 'Due date cannot be before invoice date';
                        }
                        return true;
                    }
                },
                onValid: () => {
                    showLoading('Saving...');
                }
            });
        });

        // Initialize tables
        initTables();

        // Track unsaved changes on forms with data-track-changes
        document.querySelectorAll('form[data-track-changes]').forEach(form => {
            trackUnsavedChanges(form);
        });

        // Copy buttons
        document.querySelectorAll('[data-copy]').forEach(btn => {
            btn.addEventListener('click', () => {
                const text = btn.dataset.copy;
                copyToClipboard(text);
            });
        });

        // Confirm buttons
        document.querySelectorAll('[data-confirm]').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.preventDefault();
                const message = btn.dataset.confirm;
                const confirmed = await confirm(message, {
                    type: btn.dataset.confirmType || 'danger',
                    title: btn.dataset.confirmTitle || 'Confirm Action'
                });

                if (confirmed) {
                    // If it's a link, navigate
                    if (btn.href) {
                        window.location.href = btn.href;
                    }
                    // If it's a form button, submit
                    if (btn.form) {
                        btn.form.submit();
                    }
                    // Trigger custom event
                    btn.dispatchEvent(new CustomEvent('confirmed'));
                }
            });
        });

        // Auto-hide alerts after 5 seconds
        document.querySelectorAll('.alert:not(.alert-permanent)').forEach(alert => {
            setTimeout(() => {
                const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
                bsAlert.close();
            }, 5000);
        });

        // Initialize tooltips
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        tooltipTriggerList.forEach(el => new bootstrap.Tooltip(el));

        // Initialize popovers
        const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');
        popoverTriggerList.forEach(el => new bootstrap.Popover(el));

        console.log('Invoice Tracker initialized');
    }

    // ========== Expose Public API ==========

    window.InvoiceTracker = {
        showToast,
        showLoading,
        hideLoading,
        confirm,
        populateForm,
        copyToClipboard,
        formatCurrency,
        formatDateForInput,
        validateFile,
        apiRequest,
        FileUploader,
        FormValidator,
        CONFIG
    };

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
