// Main JavaScript for Insurance Reporting System Web UI

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Insurance Reporting System Web UI loaded');
    
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
    
    // Table search functionality
    initializeTableSearch();
    
    // File upload enhancements
    initializeFileUpload();
});

// Table search functionality
function initializeTableSearch() {
    const searchInputs = document.querySelectorAll('.table-search');
    
    searchInputs.forEach(function(input) {
        input.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const tableId = this.getAttribute('data-table');
            const table = document.getElementById(tableId);
            
            if (table) {
                const rows = table.querySelectorAll('tbody tr');
                
                rows.forEach(function(row) {
                    const text = row.textContent.toLowerCase();
                    if (text.includes(searchTerm)) {
                        row.style.display = '';
                    } else {
                        row.style.display = 'none';
                    }
                });
                
                // Update result count
                const visibleRows = table.querySelectorAll('tbody tr:not([style*="display: none"])');
                const countElement = document.getElementById(tableId + '-count');
                if (countElement) {
                    countElement.textContent = `Mostrando ${visibleRows.length} resultados`;
                }
            }
        });
    });
}

// File upload enhancements
function initializeFileUpload() {
    const uploadAreas = document.querySelectorAll('.upload-area');
    
    uploadAreas.forEach(function(area) {
        // Drag and drop functionality
        area.addEventListener('dragover', function(e) {
            e.preventDefault();
            this.classList.add('dragover');
        });
        
        area.addEventListener('dragleave', function(e) {
            e.preventDefault();
            this.classList.remove('dragover');
        });
        
        area.addEventListener('drop', function(e) {
            e.preventDefault();
            this.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            const fileInput = this.querySelector('input[type="file"]');
            
            if (fileInput && files.length > 0) {
                fileInput.files = files;
                // Trigger change event
                const event = new Event('change', { bubbles: true });
                fileInput.dispatchEvent(event);
            }
        });
    });
}

// Utility functions
function showLoading() {
    const overlay = document.createElement('div');
    overlay.className = 'spinner-overlay';
    overlay.innerHTML = `
        <div class="text-center text-white">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Cargando...</span>
            </div>
            <p class="mt-2">Procesando...</p>
        </div>
    `;
    document.body.appendChild(overlay);
    return overlay;
}

function hideLoading(overlay) {
    if (overlay && overlay.parentNode) {
        overlay.parentNode.removeChild(overlay);
    }
}

// Form validation helpers
function validateRequired(form) {
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(function(field) {
        if (!field.value.trim()) {
            field.classList.add('is-invalid');
            isValid = false;
        } else {
            field.classList.remove('is-invalid');
        }
    });
    
    return isValid;
}

// Confirmation dialogs
function confirmDelete(message = '¿Está seguro de que desea eliminar este elemento?') {
    return confirm(message);
}

// Format numbers
function formatNumber(num) {
    return new Intl.NumberFormat('es-AR').format(num);
}

// Period formatting
function formatPeriod(period) {
    if (!period || period.toString().length !== 6) return period;
    
    const periodStr = period.toString();
    const year = periodStr.substring(0, 4);
    const quarter = parseInt(periodStr.substring(4));
    
    const quarterNames = {
        1: 'Marzo',
        2: 'Junio', 
        3: 'Septiembre',
        4: 'Diciembre'
    };
    
    return `${quarterNames[quarter] || 'T' + quarter} ${year}`;
}

// Export functions for global use
window.AppUtils = {
    showLoading,
    hideLoading,
    validateRequired,
    confirmDelete,
    formatNumber,
    formatPeriod
};