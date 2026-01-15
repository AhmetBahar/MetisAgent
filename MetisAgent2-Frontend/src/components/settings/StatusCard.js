/**
 * Status Card Component - Health checks, connection status, monitoring
 */

import React from 'react';
import './StatusCard.css';

const StatusCard = ({ card, onRefresh, loading }) => {
    const getMetricStatusClass = (status) => {
        const statusMap = {
            'healthy': 'success',
            'warning': 'warning', 
            'error': 'danger',
            'unknown': 'secondary'
        };
        return statusMap[status] || 'secondary';
    };

    const getOverallStatus = () => {
        if (!card.metrics || card.metrics.length === 0) {
            return 'unknown';
        }

        const hasError = card.metrics.some(m => m.status === 'error');
        const hasWarning = card.metrics.some(m => m.status === 'warning');

        if (hasError) return 'error';
        if (hasWarning) return 'warning';
        return 'healthy';
    };

    const getStatusIcon = (status) => {
        const icons = {
            'healthy': '✅',
            'warning': '⚠️',
            'error': '❌',
            'unknown': '❓'
        };
        return icons[status] || '❓';
    };

    const formatMetricValue = (value, metric) => {
        // Handle percentage values
        if (value.includes('%')) {
            const percentage = parseFloat(value);
            if (percentage > 80) return { value, class: 'warning' };
            if (percentage > 90) return { value, class: 'danger' };
            return { value, class: 'success' };
        }

        // Handle numeric values with units
        if (metric.name.toLowerCase().includes('memory') || 
            metric.name.toLowerCase().includes('disk') ||
            metric.name.toLowerCase().includes('cpu')) {
            return { value, class: getMetricStatusClass(metric.status) };
        }

        // Default formatting
        return { value, class: getMetricStatusClass(metric.status) };
    };

    const handleRefresh = () => {
        if (onRefresh && !loading) {
            onRefresh(card.card_id);
        }
    };

    const overallStatus = getOverallStatus();

    return (
        <div className={`settings-card status-card ${overallStatus}`}>
            <div className="card-header">
                <div className="card-title-section">
                    <span className="card-icon">{card.icon}</span>
                    <div className="card-text">
                        <h3 className="card-title">{card.title}</h3>
                        <p className="card-description">{card.description}</p>
                    </div>
                </div>

                <div className="card-controls">
                    {onRefresh && (
                        <button
                            className={`refresh-btn ${loading ? 'loading' : ''}`}
                            onClick={handleRefresh}
                            disabled={loading}
                            title="Yenile"
                        >
                            {loading ? (
                                <span className="loading-spinner"></span>
                            ) : (
                                '🔄'
                            )}
                        </button>
                    )}

                    <div className={`overall-status ${overallStatus}`}>
                        <span className="status-icon">
                            {getStatusIcon(overallStatus)}
                        </span>
                    </div>
                </div>
            </div>

            <div className="card-content">
                {card.metrics && card.metrics.length > 0 ? (
                    <div className="metrics-grid">
                        {card.metrics.map((metric, index) => {
                            const formattedValue = formatMetricValue(metric.value, metric);
                            
                            return (
                                <div 
                                    key={index} 
                                    className={`metric-item ${getMetricStatusClass(metric.status)}`}
                                >
                                    <div className="metric-header">
                                        <span className="metric-name">{metric.name}</span>
                                        {metric.icon && (
                                            <span className="metric-icon">{metric.icon}</span>
                                        )}
                                    </div>
                                    
                                    <div className="metric-value-container">
                                        <span className={`metric-value ${formattedValue.class}`}>
                                            {formattedValue.value}
                                        </span>
                                        <span className={`metric-status-indicator ${getMetricStatusClass(metric.status)}`}>
                                            {getStatusIcon(metric.status)}
                                        </span>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                ) : (
                    <div className="no-metrics">
                        <span className="no-metrics-icon">📊</span>
                        <p className="no-metrics-text">Metrik bilgisi bulunamadı</p>
                    </div>
                )}

                {/* Show last updated time if available */}
                {card.last_updated && (
                    <div className="card-footer">
                        <small className="last-updated">
                            Son güncelleme: {new Date(card.last_updated).toLocaleString('tr-TR')}
                        </small>
                    </div>
                )}
            </div>
        </div>
    );
};

export default StatusCard;