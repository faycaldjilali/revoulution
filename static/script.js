// DOM Ready
document.addEventListener('DOMContentLoaded', function() {
    // Auto-refresh data every 5 minutes
    setInterval(refreshStats, 300000);
    
    // Export button functionality
    const exportBtn = document.getElementById('export-btn');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportData);
    }
    
    // Initialize tooltips
    initTooltips();
    
    // Initialize filters
    initFilters();
});

// Refresh stats and notices
async function refreshStats() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();
        
        // Update stats cards (if they exist)
        updateStatsCards(stats);
        
        // Show notification
        showNotification('Données actualisées', 'success');
    } catch (error) {
        console.error('Error refreshing stats:', error);
    }
}

function updateStatsCards(stats) {
    // Find and update each stat card
    const statElements = {
        'total_notices': document.querySelector('.stat-card.total h3'),
        'urgent_deadlines': document.querySelector('.stat-card.urgent h3'),
        'overdue_deadlines': document.querySelector('.stat-card.overdue h3'),
        'with_dce_link': document.querySelector('.stat-card.dce h3'),
        'with_visite_obligatoire': document.querySelector('.stat-card.visite h3'),
        'unique_keywords': document.querySelector('.stat-card.keywords h3')
    };
    
    for (const [key, element] of Object.entries(statElements)) {
        if (element && stats[key] !== undefined) {
            element.textContent = stats[key];
        }
    }
}

// Export data to CSV
async function exportData() {
    try {
        // Get current filters from URL
        const urlParams = new URLSearchParams(window.location.search);
        
        // Build API URL with current filters
        let apiUrl = '/api/notices?';
        if (urlParams.get('keyword')) {
            apiUrl += `keyword=${encodeURIComponent(urlParams.get('keyword'))}&`;
        }
        if (urlParams.get('department')) {
            apiUrl += `department=${encodeURIComponent(urlParams.get('department'))}&`;
        }
        if (urlParams.get('urgency')) {
            apiUrl += `urgency=${encodeURIComponent(urlParams.get('urgency'))}&`;
        }
        
        // Fetch data
        const response = await fetch(apiUrl);
        const data = await response.json();
        
        if (!data.notices || data.notices.length === 0) {
            showNotification('Aucune donnée à exporter', 'warning');
            return;
        }
        
        // Convert to CSV
        const csv = convertToCSV(data.notices);
        
        // Create download link
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `boamp_export_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        
        showNotification('Export terminé', 'success');
    } catch (error) {
        console.error('Error exporting data:', error);
        showNotification('Erreur lors de l\'export', 'error');
    }
}

function convertToCSV(data) {
    if (data.length === 0) return '';
    
    // Define headers
    const headers = [
        'ID',
        'Objet',
        'Acheteur',
        'Date publication',
        'Date limite',
        'Délai restant',
        'Mots-clés',
        'Lots',
        'Visite obligatoire',
        'Lien DCE',
        'Statut délai'
    ];
    
    // Build CSV rows
    const rows = data.map(item => [
        `"${item.idweb || ''}"`,
        `"${(item.objet || '').replace(/"/g, '""')}"`,
        `"${item.nomacheteur || ''}"`,
        `"${item.dateparution || ''}"`,
        `"${item.deadline_date || ''}"`,
        `"${item.deadline_text || ''}"`,
        `"${item.keywords.join('; ') || ''}"`,
        `"${item.lots.join('; ') || ''}"`,
        `"${item.visite_obligatoire || 'non'}"`,
        `"${item.dce_link || ''}"`,
        `"${item.is_urgent ? 'Urgent' : item.is_overdue ? 'Dépassé' : 'Normal'}"`
    ]);
    
    // Combine headers and rows
    return [headers.join(','), ...rows.map(row => row.join(','))].join('\n');
}

// Initialize tooltips
function initTooltips() {
    const tooltipElements = document.querySelectorAll('[title]');
    tooltipElements.forEach(el => {
        el.addEventListener('mouseenter', showTooltip);
        el.addEventListener('mouseleave', hideTooltip);
    });
}

function showTooltip(e) {
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = this.title;
    tooltip.style.position = 'absolute';
    tooltip.style.background = '#333';
    tooltip.style.color = 'white';
    tooltip.style.padding = '5px 10px';
    tooltip.style.borderRadius = '4px';
    tooltip.style.fontSize = '12px';
    tooltip.style.zIndex = '1000';
    tooltip.style.maxWidth = '200px';
    
    const rect = this.getBoundingClientRect();
    tooltip.style.left = `${rect.left + rect.width / 2}px`;
    tooltip.style.top = `${rect.top - 10}px`;
    tooltip.style.transform = 'translateX(-50%) translateY(-100%)';
    
    document.body.appendChild(tooltip);
    this._tooltip = tooltip;
}

function hideTooltip() {
    if (this._tooltip) {
        this._tooltip.remove();
        this._tooltip = null;
    }
}

// Initialize filters
function initFilters() {
    // Auto-submit filter changes
    const filters = document.querySelectorAll('.filters-form select');
    filters.forEach(filter => {
        filter.addEventListener('change', function() {
            // Add loading indicator
            const form = this.closest('form');
            const submitBtn = form.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Chargement...';
            submitBtn.disabled = true;
            
            // Submit form
            form.submit();
        });
    });
}

// Notification system
function showNotification(message, type = 'info') {
    // Remove existing notifications
    const existing = document.querySelector('.notification');
    if (existing) existing.remove();
    
    // Create notification
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <i class="fas fa-${getNotificationIcon(type)}"></i>
            <span>${message}</span>
        </div>
        <button class="notification-close">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    // Add styles
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${getNotificationColor(type)};
        color: white;
        padding: 15px 20px;
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 15px;
        z-index: 10000;
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        animation: slideIn 0.3s ease-out;
    `;
    
    // Add close button event
    notification.querySelector('.notification-close').addEventListener('click', () => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    });
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }
    }, 5000);
    
    document.body.appendChild(notification);
    
    // Add animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
}

function getNotificationIcon(type) {
    const icons = {
        'success': 'check-circle',
        'error': 'exclamation-circle',
        'warning': 'exclamation-triangle',
        'info': 'info-circle'
    };
    return icons[type] || 'info-circle';
}

function getNotificationColor(type) {
    const colors = {
        'success': '#27ae60',
        'error': '#e74c3c',
        'warning': '#f39c12',
        'info': '#3498db'
    };
    return colors[type] || '#3498db';
}

// Real-time deadline countdown
function updateDeadlineCounters() {
    const deadlineElements = document.querySelectorAll('.notice-deadline');
    deadlineElements.forEach(element => {
        const text = element.textContent;
        if (text.includes('j') && !text.includes('-')) {
            // Extract days number
            const daysMatch = text.match(/(\d+)\s*j/);
            if (daysMatch) {
                const days = parseInt(daysMatch[1]);
                if (days <= 3) {
                    // Add pulsing animation for very urgent deadlines
                    element.style.animation = 'pulse 2s infinite';
                }
            }
        }
    });
    
    // Add pulsing animation style
    if (!document.querySelector('#pulse-style')) {
        const style = document.createElement('style');
        style.id = 'pulse-style';
        style.textContent = `
            @keyframes pulse {
                0% { opacity: 1; }
                50% { opacity: 0.7; }
                100% { opacity: 1; }
            }
        `;
        document.head.appendChild(style);
    }
}

// Initialize deadline counters
setTimeout(updateDeadlineCounters, 1000);