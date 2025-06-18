// Main JavaScript for Diabetic Retinopathy Detector

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize file upload functionality
    initializeFileUpload();
    
    // Initialize form validation
    initializeFormValidation();
    
    // Initialize progress animations
    initializeProgressAnimations();
    
    // Initialize dark mode
    initializeDarkMode();
    
    // Initialize back to top button
    initializeBackToTop();
    
    // Initialize notifications
    initializeNotifications();
    
    // Initialize comparison functionality
    initializeComparisonFeatures();
    
    // Initialize social sharing
    initializeSocialSharing();
    
    // Initialize FAQ accordion
    initializeFAQAccordion();
    
    // Initialize contact form
    initializeContactForm();
});

// Dark Mode Functionality
function initializeDarkMode() {
    const darkModeToggle = document.getElementById('darkModeToggle');
    const darkModeIcon = document.getElementById('darkModeIcon');
    
    if (!darkModeToggle) return;
    
    // Check for saved dark mode preference
    const darkMode = localStorage.getItem('darkMode') === 'true';
    if (darkMode) {
        enableDarkMode();
    }
    
    darkModeToggle.addEventListener('click', function() {
        if (document.body.classList.contains('dark-mode')) {
            disableDarkMode();
        } else {
            enableDarkMode();
        }
    });
}

function enableDarkMode() {
    document.body.classList.add('dark-mode');
    const darkModeIcon = document.getElementById('darkModeIcon');
    if (darkModeIcon) {
        darkModeIcon.className = 'bi bi-sun-fill';
    }
    localStorage.setItem('darkMode', 'true');
}

function disableDarkMode() {
    document.body.classList.remove('dark-mode');
    const darkModeIcon = document.getElementById('darkModeIcon');
    if (darkModeIcon) {
        darkModeIcon.className = 'bi bi-moon-fill';
    }
    localStorage.setItem('darkMode', 'false');
}

// Back to Top Button
function initializeBackToTop() {
    const backToTop = document.getElementById('backToTop');
    if (!backToTop) return;
    
    window.addEventListener('scroll', function() {
        if (window.pageYOffset > 300) {
            backToTop.style.display = 'block';
        } else {
            backToTop.style.display = 'none';
        }
    });
    
    backToTop.addEventListener('click', function() {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
}

// Notification System
function initializeNotifications() {
    loadNotifications();
    // Poll for new notifications every 30 seconds
    setInterval(loadNotifications, 30000);
}

function loadNotifications() {
    if (!document.getElementById('notificationList')) return;
    
    fetch('/api/notifications')
        .then(response => response.json())
        .then(data => {
            updateNotificationBadge(data.unread_count);
            updateNotificationList(data.notifications);
        })
        .catch(error => console.error('Error loading notifications:', error));
}

function updateNotificationBadge(count) {
    const badge = document.getElementById('notificationBadge');
    if (!badge) return;
    
    if (count > 0) {
        badge.textContent = count > 99 ? '99+' : count;
        badge.style.display = 'inline';
    } else {
        badge.style.display = 'none';
    }
}

function updateNotificationList(notifications) {
    const list = document.getElementById('notificationList');
    if (!list) return;
    
    if (notifications.length === 0) {
        list.innerHTML = '<p class="text-muted mb-0">No new notifications</p>';
        return;
    }
    
    list.innerHTML = notifications.map(notification => `
        <div class="notification-item ${notification.read ? '' : 'unread'} p-2 mb-2 rounded">
            <div class="d-flex justify-content-between">
                <small class="text-muted">${formatDateTime(notification.created_at)}</small>
                ${!notification.read ? '<span class="badge bg-primary">New</span>' : ''}
            </div>
            <p class="mb-1">${notification.message}</p>
            ${!notification.read ? `<button class="btn btn-sm btn-outline-primary" onclick="markAsRead(${notification.id})">Mark as Read</button>` : ''}
        </div>
    `).join('');
}

function markAsRead(notificationId) {
    fetch(`/api/notifications/${notificationId}/read`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            loadNotifications();
        }
    })
    .catch(error => console.error('Error marking notification as read:', error));
}

// Comparison Functionality
function initializeComparisonFeatures() {
    const compareBtn = document.getElementById('compareSelectedBtn');
    const checkboxes = document.querySelectorAll('.record-checkbox');
    
    if (!compareBtn) return;
    
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateCompareButton);
    });
}

function updateCompareButton() {
    const checkboxes = document.querySelectorAll('.record-checkbox:checked');
    const compareBtn = document.getElementById('compareSelectedBtn');
    
    if (!compareBtn) return;
    
    if (checkboxes.length >= 2) {
        compareBtn.disabled = false;
        compareBtn.textContent = `Compare Selected (${checkboxes.length})`;
    } else {
        compareBtn.disabled = true;
        compareBtn.textContent = 'Select 2+ records to compare';
    }
}

function compareSelected() {
    const checkboxes = document.querySelectorAll('.record-checkbox:checked');
    const recordIds = Array.from(checkboxes).map(cb => cb.value);
    
    if (recordIds.length < 2) {
        showAlert('Please select at least 2 records to compare', 'warning');
        return;
    }
    
    window.location.href = `/compare-results?ids=${recordIds.join(',')}`;
}

// Social Sharing
function initializeSocialSharing() {
    // Initialize social sharing buttons if present
    const socialButtons = document.querySelectorAll('.social-share-btn');
    socialButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const platform = this.dataset.platform;
            const url = this.dataset.url;
            const text = this.dataset.text;
            shareOnSocial(platform, url, text);
        });
    });
}

function shareOnSocial(platform, url, text) {
    const encodedUrl = encodeURIComponent(url);
    const encodedText = encodeURIComponent(text);
    let shareUrl = '';
    
    switch (platform) {
        case 'facebook':
            shareUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}`;
            break;
        case 'twitter':
            shareUrl = `https://twitter.com/intent/tweet?url=${encodedUrl}&text=${encodedText}`;
            break;
        case 'linkedin':
            shareUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${encodedUrl}`;
            break;
        case 'whatsapp':
            shareUrl = `https://wa.me/?text=${encodedText}%20${encodedUrl}`;
            break;
        case 'telegram':
            shareUrl = `https://t.me/share/url?url=${encodedUrl}&text=${encodedText}`;
            break;
    }
    
    if (shareUrl) {
        window.open(shareUrl, '_blank', 'width=600,height=400');
    }
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        showAlert('Link copied to clipboard!', 'success');
    }).catch(function() {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        showAlert('Link copied to clipboard!', 'success');
    });
}

// FAQ Accordion
function initializeFAQAccordion() {
    const searchInput = document.getElementById('faqSearch');
    if (!searchInput) return;
    
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        const faqItems = document.querySelectorAll('.accordion-item');
        
        faqItems.forEach(item => {
            const question = item.querySelector('.accordion-button').textContent.toLowerCase();
            const answer = item.querySelector('.accordion-body').textContent.toLowerCase();
            
            if (question.includes(searchTerm) || answer.includes(searchTerm)) {
                item.style.display = 'block';
            } else {
                item.style.display = 'none';
            }
        });
    });
}

// Contact Form
function initializeContactForm() {
    const contactForm = document.getElementById('contactForm');
    if (!contactForm) return;
    
    contactForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        const submitBtn = this.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="bi bi-spinner bi-spin"></i> Sending...';
        
        fetch('/contact', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert('Message sent successfully! We\'ll get back to you soon.', 'success');
                contactForm.reset();
            } else {
                showAlert('Error sending message: ' + data.error, 'danger');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Error sending message. Please try again.', 'danger');
        })
        .finally(() => {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        });
    });
}

// Analytics Charts
function initializeAnalyticsCharts() {
    // Initialize charts for analytics page
    const chartElements = document.querySelectorAll('.analytics-chart');
    chartElements.forEach(element => {
        const chartType = element.dataset.chartType;
        const chartData = JSON.parse(element.dataset.chartData);
        createChart(element, chartType, chartData);
    });
}

function createChart(element, type, data) {
    // This would integrate with Chart.js or similar library
    // For now, we'll create simple visual representations
    if (type === 'line') {
        createLineChart(element, data);
    } else if (type === 'pie') {
        createPieChart(element, data);
    } else if (type === 'bar') {
        createBarChart(element, data);
    }
}

// File Upload Functionality
function initializeFileUpload() {
    const fileInput = document.getElementById('image');
    const uploadForm = document.getElementById('uploadForm');
    const progressBar = document.querySelector('.progress-bar');
    
    if (!fileInput) return;
    
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            // Validate file type
            const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png'];
            if (!allowedTypes.includes(file.type)) {
                showAlert('Please select a valid image file (JPEG, JPG, or PNG).', 'danger');
                fileInput.value = '';
                return;
            }
            
            // Validate file size (10MB max)
            if (file.size > 10 * 1024 * 1024) {
                showAlert('File size must be less than 10MB.', 'danger');
                fileInput.value = '';
                return;
            }
            
            // Show file preview
            showFilePreview(file);
        }
    });
    
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            const file = fileInput.files[0];
            if (!file) {
                e.preventDefault();
                showAlert('Please select an image file to upload.', 'danger');
                return;
            }
            
            // Show progress bar
            if (progressBar) {
                progressBar.style.width = '0%';
                progressBar.parentElement.style.display = 'block';
                
                // Simulate progress
                let progress = 0;
                const interval = setInterval(() => {
                    progress += 10;
                    progressBar.style.width = progress + '%';
                    if (progress >= 90) {
                        clearInterval(interval);
                    }
                }, 200);
            }
        });
    }
}

function showFilePreview(file) {
    const preview = document.getElementById('imagePreview');
    if (!preview) return;
    
    const reader = new FileReader();
    reader.onload = function(e) {
        preview.innerHTML = `
            <div class="text-center">
                <img src="${e.target.result}" alt="Preview" class="img-fluid rounded" style="max-height: 200px;">
                <p class="mt-2 small text-muted">${file.name} (${formatFileSize(file.size)})</p>
            </div>
        `;
        preview.style.display = 'block';
    };
    reader.readAsDataURL(file);
}

// Alert/Notification System
function showAlert(message, type = 'info', duration = 5000) {
    // Remove existing alerts
    const existingAlerts = document.querySelectorAll('.custom-alert');
    existingAlerts.forEach(alert => alert.remove());
    
    // Create new alert
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show custom-alert`;
    alertDiv.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Auto dismiss
    if (duration > 0) {
        setTimeout(() => {
            if (alertDiv.parentElement) {
                alertDiv.remove();
            }
        }, duration);
    }
}

// Form Validation
function initializeFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
}

// Progress Animations
function initializeProgressAnimations() {
    const progressBars = document.querySelectorAll('.progress-bar[data-percentage]');
    
    progressBars.forEach(bar => {
        const percentage = bar.getAttribute('data-percentage');
        setTimeout(() => {
            bar.style.width = percentage + '%';
        }, 500);
    });
}

// Admin Functions
function refreshSystemInfo() {
    const systemInfoDiv = document.getElementById('system-info');
    if (!systemInfoDiv) return;
    
    fetch('/api/system-info')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                systemInfoDiv.innerHTML = '<div class="alert alert-danger">' + data.error + '</div>';
                return;
            }
            
            // Update the statistics
            const totalUsersElement = document.getElementById('totalUsers');
            const totalAnalysesElement = document.getElementById('totalAnalyses');
            const monthlyAnalysesElement = document.getElementById('monthlyAnalyses');
            
            if (totalUsersElement) totalUsersElement.textContent = data.total_users;
            if (totalAnalysesElement) totalAnalysesElement.textContent = data.total_analyses;
            if (monthlyAnalysesElement) monthlyAnalysesElement.textContent = data.recent_analyses;
            
            // Update system info
            systemInfoDiv.innerHTML = `
                <div class="row">
                    <div class="col-6"><strong>Database Status:</strong></div>
                    <div class="col-6"><span class="badge bg-success">Connected</span></div>
                </div>
                <div class="row mt-2">
                    <div class="col-6"><strong>Total Users:</strong></div>
                    <div class="col-6">${data.total_users}</div>
                </div>
                <div class="row mt-2">
                    <div class="col-6"><strong>Total Analyses:</strong></div>
                    <div class="col-6">${data.total_analyses}</div>
                </div>
                <div class="row mt-2">
                    <div class="col-6"><strong>Last Updated:</strong></div>
                    <div class="col-6">${new Date().toLocaleString()}</div>
                </div>
            `;
        })
        .catch(error => {
            console.error('Error:', error);
            if (systemInfoDiv) {
                systemInfoDiv.innerHTML = '<div class="alert alert-danger">Error loading system information</div>';
            }
        });
}

// Utility Functions
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

function generateUniqueId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

// Loading Overlay
function showLoadingOverlay(message = 'Loading...') {
    const overlay = document.createElement('div');
    overlay.id = 'loadingOverlay';
    overlay.className = 'loading-overlay';
    overlay.innerHTML = `
        <div class="loading-content">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-3">${message}</p>
        </div>
    `;
    document.body.appendChild(overlay);
}

function hideLoadingOverlay() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.remove();
    }
}

// Enhanced File Upload with Progress
function uploadFileWithProgress(file, url, onProgress, onComplete) {
    const formData = new FormData();
    formData.append('file', file);
    
    const xhr = new XMLHttpRequest();
    
    xhr.upload.addEventListener('progress', function(e) {
        if (e.lengthComputable) {
            const percentComplete = (e.loaded / e.total) * 100;
            if (onProgress) onProgress(percentComplete);
        }
    });
    
    xhr.addEventListener('load', function() {
        if (onComplete) onComplete(xhr.response);
    });
    
    xhr.open('POST', url);
    xhr.send(formData);
}

// Delete record function
function deleteRecord(recordId) {
    if (confirm('Are you sure you want to delete this analysis record?')) {
        fetch(`/api/delete-record/${recordId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert('Record deleted successfully!', 'success');
                setTimeout(() => {
                    location.reload();
                }, 1000);
            } else {
                showAlert('Error deleting record: ' + (data.message || 'Unknown error'), 'danger');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Error deleting record. Please try again.', 'danger');
        });
    }
}

// Export functions to global scope
window.deleteRecord = deleteRecord;
window.compareSelected = compareSelected;
window.copyToClipboard = copyToClipboard;
window.shareOnSocial = shareOnSocial;
window.markAsRead = markAsRead;
window.refreshSystemInfo = refreshSystemInfo;