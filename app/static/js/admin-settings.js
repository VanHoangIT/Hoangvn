/**
 * ===================================================================
 * ADMIN SETTINGS PAGE - JAVASCRIPT
 * File: static/js/admin-settings.js
 * ===================================================================
 */

(function() {
    'use strict';

    // ============ GLOBAL VARIABLES ============
    let formChanged = false;
    let saveTimeout;

    // ============ WAIT FOR DOM READY ============
    document.addEventListener('DOMContentLoaded', function() {
        initTabs();
        initColorPicker();
        initFileUpload();
        initFormValidation();
        initAutoSaveIndicator();
        initTextareaAutoResize();
        initKeyboardShortcuts();
        initUnsavedChangesWarning();
        initSuccessMessage();
        initCharacterCounter();
        initDragAndDrop();
    });

    // ============ TAB SWITCHING ============
    function initTabs() {
        const tabs = document.querySelectorAll('.settings-tab');

        tabs.forEach(tab => {
            tab.addEventListener('click', function() {
                // Remove active class from all tabs
                tabs.forEach(t => t.classList.remove('active'));

                // Add active class to clicked tab
                this.classList.add('active');

                // Smooth scroll to top of content
                const content = document.querySelector('.settings-tab-content');
                if (content) {
                    content.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            });
        });
    }

    // ============ COLOR PICKER PREVIEW ============
    function initColorPicker() {
        const primaryColorInput = document.getElementById('primaryColorInput');
        const colorPreview = document.getElementById('colorPreview');
        const colorValue = document.getElementById('colorValue');

        if (!primaryColorInput || !colorPreview || !colorValue) return;

        // Initialize preview
        updateColorPreview(primaryColorInput.value);

        // Update on change
        primaryColorInput.addEventListener('input', function() {
            updateColorPreview(this.value);
        });

        function updateColorPreview(color) {
            colorPreview.style.backgroundColor = color;
            colorValue.textContent = color.toUpperCase();

            // Add pulse animation
            colorPreview.style.animation = 'none';
            setTimeout(() => {
                colorPreview.style.animation = 'pulse 0.5s ease-in-out';
            }, 10);
        }
    }

    // ============ FILE UPLOAD PREVIEW ============
    function initFileUpload() {
        const fileInputs = document.querySelectorAll('input[type="file"]');

        fileInputs.forEach(input => {
            input.addEventListener('change', function() {
                handleFilePreview(this);
            });
        });
    }

    function handleFilePreview(input) {
        const file = input.files[0];

        if (!file || !file.type.startsWith('image/')) return;

        // Check file size (max 5MB)
        const maxSize = 5 * 1024 * 1024; // 5MB
        if (file.size > maxSize) {
            showAlert('danger', 'File quá lớn! Kích thước tối đa 5MB.');
            input.value = '';
            return;
        }

        const reader = new FileReader();

        reader.onload = function(e) {
            displayImagePreview(input, e.target.result);
        };

        reader.readAsDataURL(file);
    }

    function displayImagePreview(input, src) {
        // Find or create preview container
        let previewContainer = input.parentElement.querySelector('.settings-image-preview');

        if (!previewContainer) {
            previewContainer = document.createElement('div');
            previewContainer.className = 'settings-image-preview';
            input.parentElement.appendChild(previewContainer);
        }

        // Find or create preview image
        let previewImg = previewContainer.querySelector('img');
        if (!previewImg) {
            previewImg = document.createElement('img');
            previewImg.className = 'settings-preview-img';

            // Check if this is favicon
            if (input.name === 'favicon') {
                previewImg.classList.add('settings-preview-favicon');
                previewImg.style.maxWidth = '48px';
            } else {
                previewImg.style.maxWidth = '200px';
            }

            previewContainer.appendChild(previewImg);
        }

        previewImg.src = src;
        previewContainer.style.display = 'block';

        // Add fade-in animation
        previewContainer.style.animation = 'fadeIn 0.3s ease-in-out';
    }

    // ============ DRAG AND DROP ============
    function initDragAndDrop() {
        const fileInputs = document.querySelectorAll('input[type="file"]');

        fileInputs.forEach(input => {
            const parent = input.closest('.settings-form-group');
            if (!parent) return;

            parent.addEventListener('dragover', handleDragOver);
            parent.addEventListener('dragleave', handleDragLeave);
            parent.addEventListener('drop', function(e) {
                handleDrop(e, input);
            });
        });
    }

    function handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        this.style.borderColor = '#4F46E5';
        this.style.background = '#F3F4F6';
    }

    function handleDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();
        this.style.borderColor = '';
        this.style.background = '';
    }

    function handleDrop(e, input) {
        e.preventDefault();
        e.stopPropagation();

        const parent = input.closest('.settings-form-group');
        if (parent) {
            parent.style.borderColor = '';
            parent.style.background = '';
        }

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            input.files = files;
            input.dispatchEvent(new Event('change'));
        }
    }

    // ============ FORM VALIDATION ============
    function initFormValidation() {
        const form = document.querySelector('form');

        if (!form) return;

        form.addEventListener('submit', function(e) {
            const submitBtn = this.querySelector('.settings-btn-primary');
            if (!submitBtn) return;

            const originalText = submitBtn.innerHTML;

            // Show loading state
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="settings-loading"></span> Đang lưu...';

            // Disable all form inputs
            const inputs = form.querySelectorAll('input, textarea, select');
            inputs.forEach(input => input.disabled = true);

            // Reset formChanged flag
            formChanged = false;

            // If form doesn't submit after 10 seconds, re-enable (fallback)
            setTimeout(() => {
                if (submitBtn.disabled) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalText;
                    inputs.forEach(input => input.disabled = false);
                }
            }, 10000);
        });
    }

    // ============ AUTO-SAVE INDICATOR ============
    function initAutoSaveIndicator() {
        const inputs = document.querySelectorAll('.settings-form-control');

        inputs.forEach(input => {
            input.addEventListener('input', function() {
                clearTimeout(saveTimeout);
                showUnsavedIndicator();
            });
        });
    }

    function showUnsavedIndicator() {
        // Remove existing indicator
        const existingIndicator = document.getElementById('unsaved-indicator');
        if (existingIndicator) {
            existingIndicator.remove();
        }

        // Create new indicator
        const indicator = document.createElement('span');
        indicator.className = 'badge bg-warning ms-2';
        indicator.textContent = 'Chưa lưu';
        indicator.id = 'unsaved-indicator';
        indicator.style.animation = 'pulse 2s ease-in-out infinite';

        const submitBtn = document.querySelector('.settings-btn-primary');
        if (submitBtn) {
            submitBtn.parentElement.insertBefore(indicator, submitBtn);
        }
    }

    // ============ SMOOTH SCROLL TO ERROR ============
    function scrollToError() {
        const errorElements = document.querySelectorAll('.text-danger');
        if (errorElements.length > 0) {
            errorElements[0].scrollIntoView({
                behavior: 'smooth',
                block: 'center'
            });

            // Highlight the field with error
            const errorField = errorElements[0].closest('.settings-form-group');
            if (errorField) {
                errorField.style.animation = 'shake 0.5s ease-in-out';
            }
        }
    }

    // ============ TEXTAREA AUTO-RESIZE ============
    function initTextareaAutoResize() {
        const textareas = document.querySelectorAll('textarea.settings-form-control');

        textareas.forEach(textarea => {
            // Add input listener
            textarea.addEventListener('input', function() {
                autoResize(this);
            });

            // Initialize
            autoResize(textarea);
        });
    }

    function autoResize(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = (textarea.scrollHeight) + 'px';
    }

    // ============ KEYBOARD SHORTCUTS ============
    function initKeyboardShortcuts() {
        document.addEventListener('keydown', function(e) {
            // Ctrl/Cmd + S to save
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                const submitBtn = document.querySelector('.settings-btn-primary');
                if (submitBtn && !submitBtn.disabled) {
                    submitBtn.click();
                    showAlert('info', 'Đang lưu cài đặt... (Ctrl+S)');
                }
            }

            // Esc to cancel
            if (e.key === 'Escape') {
                const cancelBtn = document.querySelector('.settings-btn-secondary');
                if (cancelBtn) {
                    if (confirm('Bạn có chắc muốn hủy bỏ các thay đổi?')) {
                        cancelBtn.click();
                    }
                }
            }
        });
    }

    // ============ UNSAVED CHANGES WARNING ============
    function initUnsavedChangesWarning() {
        const inputs = document.querySelectorAll('.settings-form-control');

        inputs.forEach(input => {
            input.addEventListener('change', function() {
                formChanged = true;
            });
        });

        window.addEventListener('beforeunload', function(e) {
            if (formChanged) {
                e.preventDefault();
                e.returnValue = 'Bạn có thay đổi chưa được lưu. Bạn có chắc muốn rời khỏi trang?';
                return e.returnValue;
            }
        });

        // Reset flag on form submit
        const form = document.querySelector('form');
        if (form) {
            form.addEventListener('submit', function() {
                formChanged = false;
            });
        }
    }

    // ============ SUCCESS MESSAGE ============
    function initSuccessMessage() {
        // Check URL for success parameter
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('saved') === 'true') {
            showAlert('success', 'Cài đặt đã được lưu thành công!', true);

            // Remove parameter from URL
            window.history.replaceState({}, document.title, window.location.pathname);
        }

        // Scroll to error if exists
        setTimeout(scrollToError, 500);
    }

    // ============ CHARACTER COUNTER ============
    function initCharacterCounter() {
        const textareasWithLimit = document.querySelectorAll('textarea[maxlength]');

        textareasWithLimit.forEach(textarea => {
            const maxLength = parseInt(textarea.getAttribute('maxlength'));
            const counter = document.createElement('small');
            counter.className = 'settings-help-text';
            counter.style.marginTop = '0.25rem';

            const updateCounter = () => {
                const remaining = maxLength - textarea.value.length;
                counter.innerHTML = `<i class="bi bi-text-left"></i> ${remaining} ký tự còn lại`;

                if (remaining < 20) {
                    counter.style.color = '#EF4444';
                } else if (remaining < 50) {
                    counter.style.color = '#F59E0B';
                } else {
                    counter.style.color = '#6B7280';
                }
            };

            textarea.addEventListener('input', updateCounter);
            textarea.parentElement.appendChild(counter);
            updateCounter();
        });
    }

    // ============ ALERT HELPER ============
    function showAlert(type, message, autoHide = false) {
        // Remove existing alerts
        const existingAlerts = document.querySelectorAll('.settings-alert-custom');
        existingAlerts.forEach(alert => alert.remove());

        // Create new alert
        const alert = document.createElement('div');
        alert.className = `settings-alert settings-alert-${type} settings-alert-custom`;

        let icon = 'info-circle-fill';
        if (type === 'success') icon = 'check-circle-fill';
        if (type === 'warning') icon = 'exclamation-triangle-fill';
        if (type === 'danger') icon = 'x-circle-fill';

        alert.innerHTML = `
            <i class="bi bi-${icon}"></i>
            <div>
                <strong>${getAlertTitle(type)}:</strong> ${message}
            </div>
        `;

        // Insert at top of content
        const container = document.querySelector('.settings-tab-content');
        if (container) {
            container.insertBefore(alert, container.firstChild);

            // Smooth scroll to alert
            alert.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

            // Auto-hide
            if (autoHide) {
                setTimeout(() => {
                    alert.style.transition = 'opacity 0.5s, transform 0.5s';
                    alert.style.opacity = '0';
                    alert.style.transform = 'translateY(-20px)';
                    setTimeout(() => alert.remove(), 500);
                }, 5000);
            }
        }
    }

    function getAlertTitle(type) {
        switch(type) {
            case 'success': return 'Thành công';
            case 'warning': return 'Cảnh báo';
            case 'danger': return 'Lỗi';
            default: return 'Thông tin';
        }
    }

    // ============ BOOTSTRAP TOOLTIP INITIALIZATION ============
    function initTooltips() {
        const tooltipTriggerList = [].slice.call(
            document.querySelectorAll('[data-bs-toggle="tooltip"]')
        );

        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // Initialize tooltips if Bootstrap is available
    if (typeof bootstrap !== 'undefined') {
        initTooltips();
    }

    // ============ EXPORT FOR TESTING ============
    window.SettingsJS = {
        showAlert: showAlert,
        scrollToError: scrollToError
    };

})();

// ============ CSS ANIMATIONS (Add to CSS if not exists) ============
/*
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(-10px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes shake {
    0%, 100% { transform: translateX(0); }
    25% { transform: translateX(-10px); }
    75% { transform: translateX(10px); }
}

@keyframes pulse {
    0%, 100% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.05); opacity: 0.8; }
}
*/