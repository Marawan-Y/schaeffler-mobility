// Dashboard JavaScript - Enhanced Features
let socket = null;
let charts = {};
let currentAnalysisId = null;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    initializeSocketConnection();
    initializeEventListeners();
    loadDashboardData();
    initializeCharts();
});

// Socket.IO connection
function initializeSocketConnection() {
    socket = io();
    
    socket.on('connect', function() {
        console.log('Connected to Schaeffler Mobility Insights');
        showNotification('Connected to real-time monitoring', 'success');
    });
    
    socket.on('disconnect', function() {
        showNotification('Connection lost. Reconnecting...', 'warning');
    });
    
    socket.on('new_alert', function(data) {
        handleNewAlert(data);
    });
    
    socket.on('new_analysis', function(data) {
        handleNewAnalysis(data);
    });
}

// Event listeners
function initializeEventListeners() {
    // Tab navigation
    document.querySelectorAll('.nav-item[data-tab]').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            switchTab(this.dataset.tab);
        });
    });
    
    // Report type selector
    document.querySelectorAll('.report-type-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.report-type-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            loadReport(this.dataset.type);
        });
    });
    
    // Analysis filter
    const analysisFilter = document.getElementById('analysis-filter');
    if (analysisFilter) {
        analysisFilter.addEventListener('change', function() {
            filterAnalyses(this.value);
        });
    }
    
    // Feedback sliders
    const accuracySlider = document.getElementById('accuracy-slider');
    const usefulnessSlider = document.getElementById('usefulness-slider');
    
    if (accuracySlider) {
        accuracySlider.addEventListener('input', function() {
            document.getElementById('accuracy-value').textContent = this.value;
        });
    }
    
    if (usefulnessSlider) {
        usefulnessSlider.addEventListener('input', function() {
            document.getElementById('usefulness-value').textContent = this.value;
        });
    }
}

// Tab switching
function switchTab(tabName) {
    // Update nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    
    // Update content
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.getElementById(`${tabName}-tab`).classList.add('active');
    
    // Load tab-specific data
    switch(tabName) {
        case 'monitoring':
            loadDashboardData();
            break;
        case 'analyses':
            loadAnalyses();
            break;
        case 'reports':
            loadLatestReport();
            break;
        case 'learning':
            loadLearningInsights();
            break;
    }
}

// Load dashboard data
async function loadDashboardData() {
    try {
        // Load metrics
        const metricsResponse = await fetch('/api/metrics');
        const metrics = await metricsResponse.json();
        updateMetrics(metrics);
        
        // Load alerts
        const alertsResponse = await fetch('/api/alerts');
        const alerts = await alertsResponse.json();
        displayAlerts(alerts);
        
        // Update last update time
        document.getElementById('last-update-time').textContent = new Date().toLocaleTimeString();
        
        // Update trend chart
        updateTrendChart();
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        showNotification('Error loading dashboard data', 'error');
    }
}

// Update metrics display
function updateMetrics(metrics) {
    document.getElementById('active-alerts-count').textContent = metrics.active_alerts || 0;
    document.getElementById('trends-analyzed').textContent = metrics.total_analyses || 0;
    document.getElementById('avg-confidence').textContent = `${Math.round((metrics.avg_confidence || 0) * 100)}%`;
    document.getElementById('pending-approval').textContent = metrics.pending_analyses || 0;
}

// Display alerts
function displayAlerts(alerts) {
    const container = document.getElementById('alerts-container');
    
    if (alerts.length === 0) {
        container.innerHTML = '<div class="text-center text-muted py-4">No active alerts</div>';
        return;
    }
    
    container.innerHTML = alerts.map(alert => `
        <div class="alert-item ${alert.severity} fade-in">
            <div>
                <h6 class="mb-1">${alert.title}</h6>
                <small class="text-muted">
                    <span class="me-3">📁 ${alert.category}</span>
                    <span class="me-3">⏰ ${formatTime(alert.timestamp)}</span>
                    <span>📊 ${Math.round(alert.confidence * 100)}% confidence</span>
                </small>
            </div>
            <div>
                ${alert.requires_action ? '<span class="badge bg-warning">Action Required</span>' : ''}
            </div>
        </div>
    `).join('');
}

// Load analyses
async function loadAnalyses() {
    try {
        const response = await fetch('/api/pending-analyses');
        const analyses = await response.json();
        displayAnalyses(analyses);
    } catch (error) {
        console.error('Error loading analyses:', error);
    }
}

// Display analyses
function displayAnalyses(analyses) {
    const container = document.getElementById('pending-analyses-container');
    
    if (analyses.length === 0) {
        container.innerHTML = '<div class="text-center text-muted py-4">No pending analyses</div>';
        return;
    }
    
    container.innerHTML = analyses.map(analysis => `
        <div class="analysis-card fade-in">
            <div class="d-flex justify-content-between align-items-start mb-3">
                <div>
                    <h5 class="mb-1">${analysis.title}</h5>
                    <small class="text-muted">
                        Impact: <strong>${analysis.predicted_impact}</strong> | 
                        Confidence: <strong>${Math.round(analysis.confidence_score * 100)}%</strong>
                    </small>
                </div>
                <span class="badge bg-${analysis.predicted_impact === 'high' ? 'danger' : analysis.predicted_impact === 'medium' ? 'warning' : 'secondary'}">
                    ${analysis.predicted_impact.toUpperCase()} IMPACT
                </span>
            </div>
            
            <div class="mb-3">
                <h6>Recommended Actions:</h6>
                <ul class="mb-0">
                    ${analysis.recommended_actions.map(action => `<li>${action}</li>`).join('')}
                </ul>
            </div>
            
            <div class="d-flex gap-2">
                <button class="btn btn-success btn-sm" onclick="approveAnalysis('${analysis.trend_id}')">
                    ✓ Approve
                </button>
                <button class="btn btn-warning btn-sm" onclick="openFeedbackModal('${analysis.trend_id}')">
                    ✏️ Review & Feedback
                </button>
                <button class="btn btn-danger btn-sm" onclick="rejectAnalysis('${analysis.trend_id}')">
                    ✗ Reject
                </button>
            </div>
        </div>
    `).join('');
}

// Generate report
async function generateReport() {
    try {
        showNotification('Generating report...', 'info');
        const response = await fetch('/api/weekly-report');
        const report = await response.json();
        displayReport(report);
        showNotification('Report generated successfully', 'success');
    } catch (error) {
        console.error('Error generating report:', error);
        showNotification('Error generating report', 'error');
    }
}

// Display report
function displayReport(report) {
    const container = document.getElementById('report-content');
    
    container.innerHTML = `
        <div class="report-header mb-4">
            <div class="d-flex justify-content-between align-items-center">
                <h3>Executive Summary</h3>
                <button class="btn btn-sm btn-outline-secondary" onclick="exportReport()">
                    📥 Export PDF
                </button>
            </div>
        </div>
        
        <div class="report-section">
            ${report.executive_summary}
        </div>
        
        <div class="report-section mt-4">
            <h4>Key Recommendations</h4>
            <div class="recommendations-list">
                ${report.key_recommendations.map((rec, i) => `
                    <div class="recommendation-item">
                        <div class="d-flex justify-content-between">
                            <strong>${i + 1}. ${rec.action}</strong>
                            <span class="badge bg-${rec.impact === 'high' ? 'danger' : 'warning'}">
                                ${rec.impact.toUpperCase()}
                            </span>
                        </div>
                        <small class="text-muted">
                            From: ${rec.trend} | Confidence: ${Math.round(rec.confidence * 100)}%
                        </small>
                    </div>
                `).join('')}
            </div>
        </div>
        
        <div class="report-section mt-4">
            <h4>Risk Overview</h4>
            <div class="risk-grid">
                ${Object.entries(report.risk_overview).map(([category, risks]) => `
                    <div class="risk-category">
                        <h5 class="text-danger">${category}</h5>
                        <p>${risks.length} trends affected</p>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

// Load learning insights
async function loadLearningInsights() {
    try {
        const response = await fetch('/api/learning-insights');
        const insights = await response.json();
        displayLearningInsights(insights);
    } catch (error) {
        console.error('Error loading learning insights:', error);
    }
}

// Display learning insights
function displayLearningInsights(insights) {
    // Update metrics
    document.getElementById('total-feedback').textContent = insights.total_feedback || 0;
    document.getElementById('model-accuracy').textContent = 
        `${Math.round((insights.average_accuracy || 0) * 100)}%`;
    
    // Calculate improvement rate
    const improvementRate = insights.weight_evolution ? 
        calculateImprovementRate(insights.weight_evolution) : 0;
    document.getElementById('improvement-rate').textContent = `${improvementRate}%`;
    
    // Display weight evolution
    const weightContainer = document.getElementById('weight-evolution');
    if (insights.weight_evolution) {
        weightContainer.innerHTML = Object.entries(insights.weight_evolution).map(([factor, data]) => `
            <div class="weight-item">
                <strong>${formatFactorName(factor)}</strong>
                <div class="weight-value">${data.current.toFixed(3)}</div>
                <div class="weight-trend ${data.trend}">
                    ${data.trend === 'increasing' ? '📈' : data.trend === 'decreasing' ? '📉' : '➡️'} 
                    ${data.trend}
                </div>
            </div>
        `).join('');
    }
    
    // Update learning chart
    updateLearningChart(insights);
}

// Initialize charts
function initializeCharts() {
    // Trend Overview Chart
    const trendCtx = document.getElementById('trend-overview-chart');
    if (trendCtx) {
        charts.trendOverview = new Chart(trendCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Alerts',
                    data: [],
                    borderColor: '#00B140',
                    backgroundColor: 'rgba(0, 177, 64, 0.1)',
                    tension: 0.3
                }, {
                    label: 'Analyses',
                    data: [],
                    borderColor: '#0066CC',
                    backgroundColor: 'rgba(0, 102, 204, 0.1)',
                    tension: 0.3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
    
    // Learning Chart
    const learningCtx = document.getElementById('learning-chart');
    if (learningCtx) {
        charts.learning = new Chart(learningCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Model Accuracy',
                    data: [],
                    borderColor: '#00B140',
                    backgroundColor: 'rgba(0, 177, 64, 0.1)',
                    tension: 0.3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 1
                    }
                }
            }
        });
    }
}

// Helper functions
function formatTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 3600000) {
        return `${Math.floor(diff / 60000)} minutes ago`;
    } else if (diff < 86400000) {
        return `${Math.floor(diff / 3600000)} hours ago`;
    } else {
        return date.toLocaleDateString();
    }
}

function formatFactorName(factor) {
    return factor.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function calculateImprovementRate(weightEvolution) {
    // Simple calculation based on trend direction
    const trends = Object.values(weightEvolution).map(w => w.trend);
    const increasing = trends.filter(t => t === 'increasing').length;
    const total = trends.length;
    return Math.round((increasing / total) * 100);
}

// Action handlers
async function approveAnalysis(analysisId) {
    try {
        const response = await fetch('/api/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                analysis_id: analysisId,
                feedback: {
                    type: 'approval',
                    accuracy: 0.9,
                    usefulness: 0.9
                }
            })
        });
        
        if (response.ok) {
            showNotification('Analysis approved', 'success');
            loadAnalyses();
        }
    } catch (error) {
        console.error('Error approving analysis:', error);
        showNotification('Error approving analysis', 'error');
    }
}

async function rejectAnalysis(analysisId) {
    try {
        const response = await fetch('/api/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                analysis_id: analysisId,
                feedback: {
                    type: 'rejection',
                    accuracy: 0.3,
                    usefulness: 0.3
                }
            })
        });
        
        if (response.ok) {
            showNotification('Analysis rejected', 'success');
            loadAnalyses();
        }
    } catch (error) {
        console.error('Error rejecting analysis:', error);
        showNotification('Error rejecting analysis', 'error');
    }
}

function openFeedbackModal(analysisId) {
    currentAnalysisId = analysisId;
    const modal = new bootstrap.Modal(document.getElementById('feedbackModal'));
    modal.show();
}

async function submitFeedback(feedbackType) {
    try {
        const response = await fetch('/api/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                analysis_id: currentAnalysisId,
                feedback: {
                    type: feedbackType,
                    accuracy: parseInt(document.getElementById('accuracy-slider').value) / 100,
                    usefulness: parseInt(document.getElementById('usefulness-slider').value) / 100,
                    comments: document.getElementById('feedback-comments').value
                }
            })
        });
        
        if (response.ok) {
            showNotification(`Feedback submitted: ${feedbackType}`, 'success');
            bootstrap.Modal.getInstance(document.getElementById('feedbackModal')).hide();
            loadAnalyses();
        }
    } catch (error) {
        console.error('Error submitting feedback:', error);
        showNotification('Error submitting feedback', 'error');
    }
}

// Notification system
function showNotification(message, type = 'info') {
    const container = document.getElementById('notification-container');
    const notification = document.createElement('div');
    notification.className = `notification notification-${type} show`;
    notification.innerHTML = `
        <div class="notification-content">
            <span>${message}</span>
            <button class="notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
    `;
    container.appendChild(notification);
    
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

// Refresh dashboard
function refreshDashboard() {
    loadDashboardData();
    showNotification('Dashboard refreshed', 'success');
}

// Export functions
function exportReport() {
    window.print();
}

// Update charts with real data
function updateTrendChart() {
    if (charts.trendOverview) {
        // Generate sample data - replace with real data
        const labels = [];
        const alertsData = [];
        const analysesData = [];
        
        for (let i = 6; i >= 0; i--) {
            const date = new Date();
            date.setDate(date.getDate() - i);
            labels.push(date.toLocaleDateString('en-US', { weekday: 'short' }));
            alertsData.push(Math.floor(Math.random() * 10) + 5);
            analysesData.push(Math.floor(Math.random() * 8) + 3);
        }
        
        charts.trendOverview.data.labels = labels;
        charts.trendOverview.data.datasets[0].data = alertsData;
        charts.trendOverview.data.datasets[1].data = analysesData;
        charts.trendOverview.update();
    }
}

function updateLearningChart(insights) {
    if (charts.learning) {
        // Generate sample data - replace with real data from insights
        const labels = ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Current'];
        const data = [0.6, 0.65, 0.7, 0.75, insights.average_accuracy || 0.8];
        
        charts.learning.data.labels = labels;
        charts.learning.data.datasets[0].data = data;
        charts.learning.update();
    }
}

// Auto-refresh every 30 seconds
setInterval(() => {
    if (document.querySelector('.tab-content.active').id === 'monitoring-tab') {
        loadDashboardData();
    }
}, 30000);