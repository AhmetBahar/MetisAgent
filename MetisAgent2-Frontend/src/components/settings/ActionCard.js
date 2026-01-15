/**
 * Action Card Component - OAuth2, registrations, system actions
 */

import React, { useState } from 'react';
import './ActionCard.css';

const ActionCard = ({ card, onAction, loading }) => {
    const [actionLoading, setActionLoading] = useState({});

    const handleAction = async (action) => {
        // Check condition if specified
        if (action.condition && !evaluateCondition(action.condition, card)) {
            return;
        }

        // Confirm if required
        if (action.confirm_message && !window.confirm(action.confirm_message)) {
            return;
        }

        try {
            setActionLoading(prev => ({ ...prev, [action.id]: true }));
            await onAction(card.card_id, action.id, action.tool_call.parameters || {});
        } finally {
            setActionLoading(prev => ({ ...prev, [action.id]: false }));
        }
    };

    const evaluateCondition = (condition, card) => {
        try {
            // Simple condition evaluation - replace with proper evaluator if needed
            const code = condition.replace(/status/g, `"${card.status}"`);
            return Function('"use strict"; return (' + code + ')')();
        } catch (error) {
            console.warn('Failed to evaluate condition:', condition, error);
            return true;
        }
    };

    const getStatusDisplay = () => {
        if (!card.status_display || !card.status_display[card.status]) {
            return null;
        }

        const display = card.status_display[card.status];
        return (
            <div className={`status-display ${display.color}`}>
                <span className="status-icon">{display.icon}</span>
                <span className="status-message">{display.message}</span>
            </div>
        );
    };

    const getActionButtonClass = (action) => {
        let className = `action-btn ${action.type}`;
        
        if (actionLoading[action.id] || loading) {
            className += ' loading';
        }

        // Check if action should be shown based on condition
        if (action.condition && !evaluateCondition(action.condition, card)) {
            className += ' hidden';
        }

        return className;
    };

    return (
        <div className={`settings-card action-card ${card.status}`}>
            <div className="card-header">
                <div className="card-title-section">
                    <span className="card-icon">{card.icon}</span>
                    <div className="card-text">
                        <h3 className="card-title">{card.title}</h3>
                        <p className="card-description">{card.description}</p>
                    </div>
                </div>
                {getStatusDisplay()}
            </div>

            <div className="card-content">
                {card.actions && card.actions.length > 0 && (
                    <div className="card-actions">
                        {card.actions.map((action) => {
                            // Don't render if condition evaluates to false
                            if (action.condition && !evaluateCondition(action.condition, card)) {
                                return null;
                            }

                            return (
                                <button
                                    key={action.id}
                                    className={getActionButtonClass(action)}
                                    onClick={() => handleAction(action)}
                                    disabled={actionLoading[action.id] || loading}
                                >
                                    {actionLoading[action.id] ? (
                                        <>
                                            <span className="loading-spinner"></span>
                                            İşleniyor...
                                        </>
                                    ) : (
                                        action.label
                                    )}
                                </button>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
};

export default ActionCard;