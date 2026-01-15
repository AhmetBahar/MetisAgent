/**
 * Value Card Component - API keys, preferences, configuration values
 */

import React, { useState, useEffect } from 'react';
import './ValueCard.css';

const ValueCard = ({ card, onSave, loading }) => {
    const [formValues, setFormValues] = useState({});
    const [formErrors, setFormErrors] = useState({});
    const [saving, setSaving] = useState(false);

    // Initialize form values from card current values
    useEffect(() => {
        if (card.current_values) {
            setFormValues(card.current_values);
        }
    }, [card.current_values]);

    const handleInputChange = (fieldName, value) => {
        setFormValues(prev => ({
            ...prev,
            [fieldName]: value
        }));

        // Clear error for this field if exists
        if (formErrors[fieldName]) {
            setFormErrors(prev => ({
                ...prev,
                [fieldName]: null
            }));
        }
    };

    const validateForm = () => {
        const errors = {};
        const fields = card.form_schema?.fields || [];

        for (const field of fields) {
            const value = formValues[field.name];

            // Required field validation
            if (field.required && (!value || value.trim() === '')) {
                errors[field.name] = `${field.label} gereklidir`;
                continue;
            }

            if (value) {
                // Type-specific validation
                switch (field.type) {
                    case 'email':
                        if (!value.includes('@')) {
                            errors[field.name] = 'Geçerli bir email adresi girin';
                        }
                        break;
                    case 'password':
                        if (value.length < 8) {
                            errors[field.name] = 'Şifre en az 8 karakter olmalı';
                        }
                        break;
                    case 'number':
                        if (isNaN(value)) {
                            errors[field.name] = 'Geçerli bir sayı girin';
                        }
                        break;
                }

                // Custom validation
                if (field.validation) {
                    const validation = field.validation;
                    
                    if (validation.min_length && value.length < validation.min_length) {
                        errors[field.name] = `En az ${validation.min_length} karakter gerekli`;
                    }
                    
                    if (validation.pattern) {
                        const regex = new RegExp(validation.pattern);
                        if (!regex.test(value)) {
                            errors[field.name] = `Geçersiz format`;
                        }
                    }
                }
            }
        }

        setFormErrors(errors);
        return Object.keys(errors).length === 0;
    };

    const handleSave = async () => {
        if (!validateForm()) {
            return;
        }

        try {
            setSaving(true);
            await onSave(card.card_id, formValues);
        } finally {
            setSaving(false);
        }
    };

    const renderField = (field) => {
        const value = formValues[field.name] || '';
        const error = formErrors[field.name];

        switch (field.type) {
            case 'select':
                return (
                    <select
                        value={value}
                        onChange={(e) => handleInputChange(field.name, e.target.value)}
                        className={error ? 'error' : ''}
                        disabled={saving || loading}
                    >
                        <option value="">Seçiniz...</option>
                        {field.options?.map((option) => (
                            <option key={option.value} value={option.value}>
                                {option.label}
                            </option>
                        ))}
                    </select>
                );

            case 'checkbox':
                return (
                    <label className="checkbox-label">
                        <input
                            type="checkbox"
                            checked={value}
                            onChange={(e) => handleInputChange(field.name, e.target.checked)}
                            disabled={saving || loading}
                        />
                        <span className="checkbox-text">{field.label}</span>
                    </label>
                );

            case 'textarea':
                return (
                    <textarea
                        value={value}
                        onChange={(e) => handleInputChange(field.name, e.target.value)}
                        placeholder={field.placeholder}
                        className={error ? 'error' : ''}
                        disabled={saving || loading}
                        rows={4}
                    />
                );

            default: // text, password, email, number
                return (
                    <input
                        type={field.type}
                        value={value}
                        onChange={(e) => handleInputChange(field.name, e.target.value)}
                        placeholder={field.placeholder}
                        className={error ? 'error' : ''}
                        disabled={saving || loading}
                    />
                );
        }
    };

    const hasChanges = () => {
        const currentValues = card.current_values || {};
        return JSON.stringify(formValues) !== JSON.stringify(currentValues);
    };

    const isFormValid = () => {
        return Object.keys(formErrors).length === 0 && hasChanges();
    };

    return (
        <div className="settings-card value-card">
            <div className="card-header">
                <div className="card-title-section">
                    <span className="card-icon">{card.icon}</span>
                    <div className="card-text">
                        <h3 className="card-title">{card.title}</h3>
                        <p className="card-description">{card.description}</p>
                    </div>
                </div>
            </div>

            <div className="card-content">
                <div className="form-container">
                    {card.form_schema?.fields?.map((field) => (
                        <div key={field.name} className="form-field">
                            {field.type !== 'checkbox' && (
                                <label className="field-label">
                                    {field.label}
                                    {field.required && <span className="required">*</span>}
                                </label>
                            )}
                            
                            <div className="field-input">
                                {renderField(field)}
                            </div>
                            
                            {formErrors[field.name] && (
                                <div className="field-error">
                                    {formErrors[field.name]}
                                </div>
                            )}
                        </div>
                    ))}
                </div>

                <div className="card-actions">
                    <button
                        className="save-btn primary"
                        onClick={handleSave}
                        disabled={!isFormValid() || saving || loading}
                    >
                        {saving ? (
                            <>
                                <span className="loading-spinner"></span>
                                Kaydediliyor...
                            </>
                        ) : (
                            'Kaydet'
                        )}
                    </button>
                    
                    {hasChanges() && (
                        <button
                            className="reset-btn secondary"
                            onClick={() => {
                                setFormValues(card.current_values || {});
                                setFormErrors({});
                            }}
                            disabled={saving || loading}
                        >
                            Sıfırla
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
};

export default ValueCard;