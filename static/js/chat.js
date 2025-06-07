// Chat JavaScript - Enhanced functionality for the main workflow
document.addEventListener("DOMContentLoaded", function() {
    // Initialize marked.js for markdown rendering if available
    if (typeof marked !== 'undefined') {
        marked.setOptions({
            breaks: true,
            gfm: true
        });
        renderMarkdown();
    }
    
    // Initialize tooltips
    initializeTooltips();
    
    // Auto-scroll to relevant section
    scrollToActiveSection();
    
    // Initialize form enhancements
    enhanceForms();
});

// Render markdown content
function renderMarkdown() {
    document.querySelectorAll('[data-markdown]').forEach(element => {
        const content = element.textContent || element.innerText;
        element.innerHTML = marked.parse(content);
    });
}

// Initialize Bootstrap tooltips
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Scroll to active section
function scrollToActiveSection() {
    const activeCard = document.querySelector('.card.shadow-lg');
    if (activeCard) {
        setTimeout(() => {
            activeCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
    }
}

// Enhance form interactions
function enhanceForms() {
    // Add loading state to submit buttons
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"]:not([formnovalidate])');
            if (submitBtn && form.checkValidity()) {
                // Store original text
                const originalText = submitBtn.innerHTML;
                
                // Add loading state
                submitBtn.disabled = true;
                submitBtn.innerHTML = `
                    <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                    Processing...
                `;
                
                // Re-enable after timeout (in case of error)
                setTimeout(() => {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalText;
                }, 30000);
            }
        });
    });
    
    // Enhance textarea auto-resize
    document.querySelectorAll('textarea').forEach(textarea => {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = this.scrollHeight + 'px';
        });
    });
}

// Confidence score extraction
function extractConfidence(text) {
    const match = text.match(/Confidence\s*Score:\s*([0-9.]+)/i);
    return match ? parseFloat(match[1]) : 0.5;
}

// Format confidence badge
function getConfidenceBadgeClass(confidence) {
    if (confidence > 0.7) return 'high';
    if (confidence > 0.5) return 'medium';
    return 'low';
}

// Export functionality
function exportContent(elementId, filename) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const content = element.innerHTML;
    const blob = new Blob([wrapInHtml(content)], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || `schaeffler-export-${new Date().toISOString().split('T')[0]}.html`;
    a.click();
    
    URL.revokeObjectURL(url);
    showNotification('Content exported successfully', 'success');
}

// Wrap content in HTML template
function wrapInHtml(content) {
    return `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Schaeffler Mobility Insight - Export</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        .logo { height: 40px; margin-bottom: 20px; }
        .header { background: #00B140; color: white; padding: 20px; margin-bottom: 30px; }
        @media print { .no-print { display: none !important; } }
    </style>
</head>
<body>
    <div class="header text-center">
        <h1>Schaeffler Mobility Insight Platform</h1>
        <p>Generated: ${new Date().toLocaleString()}</p>
    </div>
    <div class="container">
        ${content}
    </div>
</body>
</html>`;
}

// Copy to clipboard
function copyToClipboard(text, button) {
    navigator.clipboard.writeText(text).then(() => {
        const originalText = button.textContent;
        button.textContent = 'Copied!';
        button.classList.add('btn-success');
        
        setTimeout(() => {
            button.textContent = originalText;
            button.classList.remove('btn-success');
        }, 2000);
    }).catch(err => {
        showNotification('Failed to copy to clipboard', 'error');
    });
}

// Print specific section
function printSection(elementId) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const printWindow = window.open('', '_blank');
    printWindow.document.write(wrapInHtml(element.innerHTML));
    printWindow.document.close();
    
    printWindow.onload = function() {
        printWindow.print();
        printWindow.close();
    };
}

// Session storage helpers
function saveFormData(formId) {
    const form = document.getElementById(formId);
    if (!form) return;
    
    const formData = new FormData(form);
    const data = {};
    
    for (let [key, value] of formData.entries()) {
        data[key] = value;
    }
    
    sessionStorage.setItem(`schaeffler_form_${formId}`, JSON.stringify(data));
}

function restoreFormData(formId) {
    const savedData = sessionStorage.getItem(`schaeffler_form_${formId}`);
    if (!savedData) return;
    
    try {
        const data = JSON.parse(savedData);
        const form = document.getElementById(formId);
        
        if (form) {
            Object.keys(data).forEach(key => {
                const field = form.elements[key];
                if (field) {
                    field.value = data[key];
                }
            });
        }
    } catch (e) {
        console.error('Error restoring form data:', e);
    }
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + S to save/export
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        const exportBtn = document.querySelector('[onclick*="export"]');
        if (exportBtn) exportBtn.click();
    }
    
    // Ctrl/Cmd + P to print
    if ((e.ctrlKey || e.metaKey) && e.key === 'p') {
        e.preventDefault();
        const printableSection = document.querySelector('.card.shadow-lg');
        if (printableSection) {
            printSection(printableSection.id || 'main-content');
        }
    }
});

// Utility function to format numbers
function formatNumber(num) {
    return new Intl.NumberFormat('en-US').format(num);
}

// Format date relative to now
function formatRelativeDate(date) {
    const now = new Date();
    const past = new Date(date);
    const diffMs = now - past;
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);
    
    if (diffDays > 7) {
        return past.toLocaleDateString();
    } else if (diffDays > 0) {
        return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    } else if (diffHours > 0) {
        return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    } else if (diffMins > 0) {
        return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
    } else {
        return 'Just now';
    }
}

// Progress animation
function animateProgress(progressBar, targetValue) {
    const currentValue = parseInt(progressBar.style.width) || 0;
    const increment = (targetValue - currentValue) / 20;
    let current = currentValue;
    
    const animation = setInterval(() => {
        current += increment;
        if ((increment > 0 && current >= targetValue) || (increment < 0 && current <= targetValue)) {
            current = targetValue;
            clearInterval(animation);
        }
        progressBar.style.width = current + '%';
        progressBar.setAttribute('aria-valuenow', current);
        progressBar.textContent = Math.round(current) + '%';
    }, 50);
}

// Enhanced trend card selection
function enhanceTrendCards() {
    const trendCards = document.querySelectorAll('.trend-card');
    const selectElement = document.getElementById('selected_trend_idx');
    
    trendCards.forEach((card, index) => {
        // Add hover effects
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = '';
        });
        
        // Enhanced click behavior
        card.addEventListener('click', function() {
            // Remove previous selection
            trendCards.forEach(c => c.classList.remove('selected'));
            
            // Add selection
            this.classList.add('selected');
            
            // Update select element
            if (selectElement) {
                selectElement.value = index;
                selectElement.dispatchEvent(new Event('change'));
            }
            
            // Smooth scroll to action buttons
            const formSection = this.closest('.card').querySelector('form');
            if (formSection) {
                formSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            
            // Show selection feedback
            showNotification(`Selected: ${this.querySelector('h4').textContent}`, 'info');
        });
    });
}

// Call enhancement function if trend cards exist
if (document.querySelector('.trend-card')) {
    enhanceTrendCards();
}

// Auto-save form data
let autoSaveTimer;
function enableAutoSave(formId) {
    const form = document.getElementById(formId);
    if (!form) return;
    
    form.addEventListener('input', function() {
        clearTimeout(autoSaveTimer);
        autoSaveTimer = setTimeout(() => {
            saveFormData(formId);
            // Show subtle save indicator
            const indicator = document.createElement('span');
            indicator.className = 'text-muted small ms-2';
            indicator.textContent = 'Saved';
            indicator.style.opacity = '0';
            
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn && !submitBtn.querySelector('.text-muted')) {
                submitBtn.appendChild(indicator);
                
                // Fade in
                setTimeout(() => {
                    indicator.style.transition = 'opacity 0.3s';
                    indicator.style.opacity = '1';
                }, 10);
                
                // Fade out and remove
                setTimeout(() => {
                    indicator.style.opacity = '0';
                    setTimeout(() => indicator.remove(), 300);
                }, 2000);
            }
        }, 1000);
    });
}

// Enable auto-save for main forms
['identification-form', 'scouting-form', 'validation-form'].forEach(formId => {
    if (document.getElementById(formId)) {
        enableAutoSave(formId);
        restoreFormData(formId);
    }
});

// Real-time character count for textareas
document.querySelectorAll('textarea').forEach(textarea => {
    const maxLength = textarea.getAttribute('maxlength');
    if (maxLength) {
        const counter = document.createElement('div');
        counter.className = 'form-text text-end';
        counter.textContent = `0 / ${maxLength}`;
        textarea.parentElement.appendChild(counter);
        
        textarea.addEventListener('input', function() {
            const length = this.value.length;
            counter.textContent = `${length} / ${maxLength}`;
            counter.classList.toggle('text-danger', length > maxLength * 0.9);
        });
    }
});

// Smooth scroll navigation
function smoothScrollTo(targetId) {
    const target = document.getElementById(targetId);
    if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

// Add navigation helpers
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
        e.preventDefault();
        const targetId = this.getAttribute('href').substring(1);
        smoothScrollTo(targetId);
    });
});

// Export all functions for use in other scripts
window.schaefflerChat = {
    showNotification,
    exportContent,
    copyToClipboard,
    printSection,
    saveFormData,
    restoreFormData,
    formatNumber,
    formatRelativeDate,
    animateProgress,
    smoothScrollTo
};