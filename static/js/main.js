document.addEventListener('DOMContentLoaded', function() {
    const navToggle = document.querySelector('.nav-toggle');
    const navMenu = document.getElementById('navMenu');
    
    if (navToggle) {
        navToggle.addEventListener('click', function() {
            const isActive = navMenu.classList.toggle('active');
            const spans = this.querySelectorAll('span');
            
            if (isActive) {
                spans[0].style.transform = 'rotate(45deg) translate(5px, 5px)';
                spans[1].style.opacity = '0';
                spans[2].style.transform = 'rotate(-45deg) translate(7px, -6px)';
                this.setAttribute('aria-expanded', 'true');
            } else {
                spans[0].style.transform = 'none';
                spans[1].style.opacity = '1';
                spans[2].style.transform = 'none';
                this.setAttribute('aria-expanded', 'false');
            }
        });
        
        document.addEventListener('click', function(event) {
            const isClickInside = navToggle.contains(event.target) || navMenu.contains(event.target);
            if (!isClickInside && navMenu.classList.contains('active')) {
                navMenu.classList.remove('active');
                navToggle.classList.remove('active');
                navToggle.setAttribute('aria-expanded', 'false');
                const spans = navToggle.querySelectorAll('span');
                spans[0].style.transform = 'none';
                spans[1].style.opacity = '1';
                spans[2].style.transform = 'none';
            }
        });
    }
    
    const messages = document.querySelectorAll('.alert');
    messages.forEach(function(message) {
        setTimeout(function() {
            message.style.opacity = '0';
            message.style.transform = 'translateY(-20px)';
            message.style.transition = 'all 0.3s ease';
            setTimeout(function() {
                message.remove();
            }, 300);
        }, 5000);
    });
    
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(function(field) {
                const existingError = field.parentNode.querySelector('.error-message');
                if (existingError) {
                    existingError.remove();
                }
                
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add('error');
                    field.style.borderColor = '#ef4444';
                    
                    const errorMsg = document.createElement('span');
                    errorMsg.className = 'error-message';
                    errorMsg.textContent = 'This field is required';
                    field.parentNode.appendChild(errorMsg);
                } else {
                    field.classList.remove('error');
                    field.style.borderColor = '';
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                const firstError = form.querySelector('.error');
                if (firstError) {
                    firstError.focus();
                }
            }
        });
        
        form.querySelectorAll('input, textarea, select').forEach(function(field) {
            field.addEventListener('input', function() {
                this.classList.remove('error');
                this.style.borderColor = '';
                const errorMsg = this.parentNode.querySelector('.error-message');
                if (errorMsg) {
                    errorMsg.remove();
                }
            });
        });
    });
    
    const passwordFields = document.querySelectorAll('input[type="password"]');
    passwordFields.forEach(function(field) {
        field.addEventListener('paste', function(e) {
            e.preventDefault();
            showNotification('Pasting password is not allowed for security reasons.', 'warning');
        });
        
        field.addEventListener('drop', function(e) {
            e.preventDefault();
        });
    });
    
    const tableRows = document.querySelectorAll('.data-table tbody tr');
    tableRows.forEach(function(row) {
        row.addEventListener('click', function() {
            const link = this.querySelector('a');
            if (link && window.innerWidth < 768) {
                link.click();
            }
        });
    });
    
    const dangerButtons = document.querySelectorAll('.btn-danger');
    dangerButtons.forEach(function(btn) {
        if (!btn.closest('form')) return;
        
        btn.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to proceed? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    });
    
    document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    const printButtons = document.querySelectorAll('.btn-print');
    printButtons.forEach(function(btn) {
        btn.addEventListener('click', function() {
            window.print();
        });
    });
    
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-menu a');
    navLinks.forEach(function(link) {
        const href = link.getAttribute('href');
        if (href === currentPath || 
            (currentPath.startsWith(href) && href !== '/' && href !== '' && href !== '#')) {
            link.classList.add('active');
        }
        if (href === '/' && currentPath === '/') {
            link.classList.add('active');
        }
    });
});

function showNotification(message, type) {
    type = type || 'info';
    const notification = document.createElement('div');
    notification.className = 'alert alert-' + type;
    notification.textContent = message;
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';
    notification.style.maxWidth = '400px';
    notification.style.boxShadow = '0 10px 15px -3px rgba(0,0,0,0.1)';
    notification.style.animation = 'slideIn 0.3s ease';
    
    document.body.appendChild(notification);
    
    setTimeout(function() {
        notification.style.opacity = '0';
        notification.style.transform = 'translateY(-20px)';
        notification.style.transition = 'all 0.3s ease';
        setTimeout(function() {
            notification.remove();
        }, 300);
    }, 3000);
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction() {
        const args = arguments;
        const later = function() {
            clearTimeout(timeout);
            func.apply(null, args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function formatCurrency(amount) {
    return 'KES ' + parseFloat(amount).toFixed(2).replace(/\d(?=(\d{3})+\.)/g, '$&,');
}

function formatDate(dateString) {
    const options = { year: 'numeric', month: 'short', day: 'numeric' };
    return new Date(dateString).toLocaleDateString('en-US', options);
}

function formatDateTime(dateString) {
    const options = { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' };
    return new Date(dateString).toLocaleDateString('en-US', options);
}

function getStatusBadge(status) {
    const statusMap = {
        'pending': 'badge-pending',
        'paid': 'badge-paid',
        'completed': 'badge-completed',
        'success': 'badge-success',
        'paid_late': 'badge-paid_late',
        'partial': 'badge-partial',
        'active': 'badge-active',
        'inactive': 'badge-inactive',
        'dropped': 'badge-dropped',
        'accepted': 'badge-accepted',
        'absent': 'badge-absent',
        'absent_with_apology': 'badge-absent_with_apology',
        'scheduled': 'badge-scheduled',
        'new': 'badge-new',
        'read': 'badge-read',
        'replied': 'badge-replied',
        'archived': 'badge-archived'
    };
    return statusMap[status] || 'badge-pending';
}

function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

function validatePhone(phone) {
    const re = /^\+?[\d\s-]{10,15}$/;
    return re.test(phone);
}

function getCsrfToken() {
    const cookieValue = document.cookie
        .split('; ')
        .find(function(row) {
            return row.startsWith('csrftoken=');
        });
    
    if (cookieValue) {
        return cookieValue.split('=')[1];
    }
    return null;
}

function showLoading(element) {
    if (element) {
        element.disabled = true;
        element.innerHTML = '<span class="spinner"></span> Loading...';
        element.style.opacity = '0.7';
    }
}

function hideLoading(element, originalText) {
    if (element) {
        element.disabled = false;
        element.innerHTML = originalText || element.innerHTML;
        element.style.opacity = '1';
    }
}

function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(function() {
            showNotification('Copied to clipboard!', 'success');
        }).catch(function() {
            fallbackCopy(text);
        });
    } else {
        fallbackCopy(text);
    }
}

function fallbackCopy(text) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    try {
        document.execCommand('copy');
        showNotification('Copied to clipboard!', 'success');
    } catch (err) {
        showNotification('Failed to copy', 'error');
    }
    document.body.removeChild(textarea);
}