/**
 * Settings Page - Adaptive Cards Based Settings Management
 * 
 * CLAUDE.md COMPLIANT:
 * - Uses adaptive cards system for all settings
 * - Tool-agnostic interface design
 * - Dynamic card discovery from backend
 * - Consistent UX across all tools
 */

import React, { useState, useEffect } from 'react';
import apiService from '../services/apiService';
import authService from '../services/authService';
import ActionCard from '../components/settings/ActionCard';
import ValueCard from '../components/settings/ValueCard';
import StatusCard from '../components/settings/StatusCard';
import './Settings.css';

const Settings = () => {
    const [activeCategory, setActiveCategory] = useState('all');
    const [categories, setCategories] = useState([]);
    const [cards, setCards] = useState([]);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [messageType, setMessageType] = useState('');
    const [cardLoadingStates, setCardLoadingStates] = useState({});
    const [plugins, setPlugins] = useState([]);
    const [pluginsLoading, setPluginsLoading] = useState(false);
    const [togglingPlugin, setTogglingPlugin] = useState(null);

    useEffect(() => {
        loadCategories();
        loadCards();
        loadPlugins();
    }, []);

    useEffect(() => {
        loadCards();
    }, [activeCategory]);

    const showMessage = (msg, type = 'success') => {
        setMessage(msg);
        setMessageType(type);
        setTimeout(() => {
            setMessage('');
            setMessageType('');
        }, 5000);
    };

    const loadCategories = async () => {
        try {
            const result = await apiService.api.get('/settings/cards/categories');
            
            if (result.data.success) {
                setCategories(result.data.categories || []);
            } else {
                console.error('Categories load error:', result.data.error);
                showMessage('Kategoriler yüklenemedi', 'error');
            }
        } catch (error) {
            console.error('Categories load error:', error);
            showMessage('Kategoriler yüklenemedi: ' + error.message, 'error');
        }
    };

    const loadCards = async () => {
        try {
            setLoading(true);

            const params = {};
            if (activeCategory !== 'all') {
                params.category = activeCategory;
            }
            params.user_id = 'ahmetb@minor.com.tr'; // Add logged-in user_id parameter

            const result = await apiService.api.get('/settings/cards', { params });

            if (result.data.success) {
                setCards(result.data.cards || []);
            } else {
                console.error('Cards load error:', result.data.error);
                showMessage('Ayar kartları yüklenemedi', 'error');
            }
        } catch (error) {
            console.error('Cards load error:', error);
            showMessage('Ayar kartları yüklenemedi: ' + error.message, 'error');
        } finally {
            setLoading(false);
        }
    };

    const loadPlugins = async () => {
        try {
            setPluginsLoading(true);
            console.log('🔌 Loading plugins...');
            const result = await apiService.api.get('/plugins');
            console.log('🔌 Plugins API response:', result.data);
            if (result.data.success) {
                console.log('🔌 Setting plugins:', result.data.plugins?.length || 0, 'plugins');
                setPlugins(result.data.plugins || []);
            } else {
                console.error('🔌 Plugins load failed:', result.data.error);
            }
        } catch (error) {
            console.error('🔌 Plugins load error:', error);
        } finally {
            setPluginsLoading(false);
        }
    };

    const togglePlugin = async (pluginName, currentEnabled) => {
        try {
            setTogglingPlugin(pluginName);
            const result = await apiService.api.post(`/plugins/${pluginName}/toggle`, {
                enabled: !currentEnabled
            });
            if (result.data.success) {
                showMessage(`${pluginName} ${result.data.enabled ? 'aktif edildi' : 'devre dışı bırakıldı'}`);
                setPlugins(plugins.map(p =>
                    p.name === pluginName ? { ...p, is_enabled: result.data.enabled } : p
                ));
            } else {
                showMessage(`Hata: ${result.data.error}`, 'error');
            }
        } catch (error) {
            showMessage(`Hata: ${error.message}`, 'error');
        } finally {
            setTogglingPlugin(null);
        }
    };

    const getPluginIcon = (name) => {
        const icons = {
            'rmms_scada_tool': '📊', 'rmms_code_tool': '💻', 'rmms_datasource_tool': '🔌',
            'rmms_task_tool': '📋', 'rmms_workflow_tool': '🔄', 'google_tool': '🔵',
            'ecostar_tool': '🔥', 'test_tool': '🧪'
        };
        return icons[name] || '🔧';
    };

    const handleCardAction = async (cardId, actionId, parameters = {}) => {
        try {
            setCardLoadingStates(prev => ({ ...prev, [cardId]: true }));
            
            const result = await apiService.api.post('/settings/cards/action', {
                card_id: cardId,
                action_id: actionId,
                user_id: 'ahmetb@minor.com.tr',
                parameters
            });
            
            if (result.data.success) {
                showMessage('İşlem başarıyla tamamlandı!');
                
                // Handle special actions
                if (result.data.data && result.data.data.auth_url) {
                    // OAuth redirect
                    window.open(result.data.data.auth_url, '_blank');
                    return;
                }
                
                // Refresh cards to show updated states
                await loadCards();
            } else {
                showMessage(`İşlem başarısız: ${result.data.error}`, 'error');
            }
        } catch (error) {
            console.error('Card action error:', error);
            showMessage(`İşlem hatası: ${error.message}`, 'error');
        } finally {
            setCardLoadingStates(prev => ({ ...prev, [cardId]: false }));
        }
    };

    const handleCardSave = async (cardId, values) => {
        try {
            setCardLoadingStates(prev => ({ ...prev, [cardId]: true }));
            
            const result = await apiService.api.post('/settings/cards/save', {
                card_id: cardId,
                values: values,
                user_id: 'test_user'
            });
            
            if (result.data.success) {
                showMessage('Ayarlar başarıyla kaydedildi!');
                // Refresh cards to show updated states
                await loadCards();
            } else {
                showMessage(`Kaydetme başarısız: ${result.data.error}`, 'error');
            }
        } catch (error) {
            console.error('Card save error:', error);
            showMessage(`Kaydetme hatası: ${error.message}`, 'error');
        } finally {
            setCardLoadingStates(prev => ({ ...prev, [cardId]: false }));
        }
    };

    const handleCardRefresh = async (cardId) => {
        try {
            setCardLoadingStates(prev => ({ ...prev, [cardId]: true }));
            
            // For refresh, just reload all cards
            await loadCards();
            
            showMessage('Kart başarıyla yenilendi!');
        } catch (error) {
            console.error('Card refresh error:', error);
            showMessage(`Yenileme hatası: ${error.message}`, 'error');
        } finally {
            setCardLoadingStates(prev => ({ ...prev, [cardId]: false }));
        }
    };

    const renderCard = (card) => {
        const cardLoading = cardLoadingStates[card.card_id] || false;
        
        switch (card.type) {
            case 'action':
                return (
                    <ActionCard
                        key={card.card_id}
                        card={card}
                        onAction={(actionId, params) => handleCardAction(card.card_id, actionId, params)}
                        loading={cardLoading}
                    />
                );
            
            case 'value':
                return (
                    <ValueCard
                        key={card.card_id}
                        card={card}
                        onSave={(values) => handleCardSave(card.card_id, values)}
                        loading={cardLoading}
                    />
                );
            
            case 'status':
                return (
                    <StatusCard
                        key={card.card_id}
                        card={card}
                        onRefresh={() => handleCardRefresh(card.card_id)}
                        loading={cardLoading}
                    />
                );
            
            default:
                return (
                    <div key={card.card_id} className="unknown-card">
                        <p>Bilinmeyen kart türü: {card.type}</p>
                    </div>
                );
        }
    };

    const groupCardsByCategory = (cards) => {
        const grouped = {};
        cards.forEach(card => {
            const category = card.category || 'other';
            if (!grouped[category]) {
                grouped[category] = [];
            }
            grouped[category].push(card);
        });
        return grouped;
    };

    const getCategoryDisplayName = (categoryId) => {
        const categoryMap = {
            'authentication': 'Kimlik Doğrulama',
            'api_keys': 'API Anahtarları',
            'tools': 'Tool Yönetimi',
            'monitoring': 'İzleme',
            'preferences': 'Tercihler',
            'general': 'Genel',
            'system': 'Sistem'
        };
        return categoryMap[categoryId] || categoryId.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
    };

    const getCategoryIcon = (categoryId) => {
        const iconMap = {
            'authentication': '🔐',
            'api_keys': '🔑',
            'tools': '🔧',
            'monitoring': '📊',
            'preferences': '⚙️',
            'general': '📋',
            'system': '💻'
        };
        return iconMap[categoryId] || '📁';
    };

    return (
        <div className="settings-container">
            <div className="settings-header">
                <h2>⚙️ Ayarlar</h2>
                <p className="settings-subtitle">
                    Tool ayarları, kimlik doğrulama ve sistem yapılandırması
                </p>
                {message && (
                    <div className={`message ${messageType}`}>
                        {message}
                    </div>
                )}
            </div>

            <div className="settings-layout">
                {/* Category Sidebar */}
                <div className="settings-sidebar">
                    <div className="category-list">
                        {categories.map((category) => (
                            <button
                                key={category.id}
                                className={`category-btn ${activeCategory === category.id ? 'active' : ''}`}
                                onClick={() => setActiveCategory(category.id)}
                            >
                                <span className="category-icon">{category.icon}</span>
                                <span className="category-name">{category.name}</span>
                            </button>
                        ))}
                    </div>
                </div>

                {/* Cards Content */}
                <div className="settings-content">
                    {/* Debug info - remove after testing */}
                    {console.log('🔍 Render check:', { activeCategory, pluginsLength: plugins.length, showPlugins: (activeCategory === 'tools' || activeCategory === 'all') && plugins.length > 0 })}

                    {/* Plugin Management Section - Show when tools category */}
                    {(activeCategory === 'tools' || activeCategory === 'all') && plugins.length > 0 && (
                        <div className="plugins-section">
                            <div className="category-header">
                                <span className="category-icon">🔌</span>
                                <h3 className="category-title">Plugin Yönetimi</h3>
                            </div>
                            <p className="plugins-info">
                                LMStudio gibi local LLM'ler için context limiti önemlidir. Sadece ihtiyacınız olan plugin'leri aktif tutun.
                            </p>
                            <div className="plugins-grid">
                                {plugins.map(plugin => (
                                    <div key={plugin.name} className={`plugin-item ${plugin.is_enabled ? 'enabled' : 'disabled'}`}>
                                        <div className="plugin-left">
                                            <span className="plugin-icon">{getPluginIcon(plugin.name)}</span>
                                            <div className="plugin-info">
                                                <span className="plugin-name">{plugin.display_name || plugin.name}</span>
                                                <span className="plugin-caps">{(plugin.capabilities || []).length} yetenek</span>
                                            </div>
                                        </div>
                                        <label className="toggle-switch">
                                            <input
                                                type="checkbox"
                                                checked={plugin.is_enabled}
                                                onChange={() => togglePlugin(plugin.name, plugin.is_enabled)}
                                                disabled={togglingPlugin === plugin.name}
                                            />
                                            <span className="toggle-slider"></span>
                                        </label>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {loading ? (
                        <div className="loading-state">
                            <div className="loading-spinner"></div>
                            <p>Ayarlar yükleniyor...</p>
                        </div>
                    ) : cards.length === 0 && (activeCategory !== 'tools' && activeCategory !== 'all') ? (
                        <div className="empty-state">
                            <div className="empty-icon">📋</div>
                            <h3>Henüz ayar bulunamadı</h3>
                            <p>Bu kategoride henüz ayar kartı bulunmuyor.</p>
                        </div>
                    ) : cards.length > 0 && (
                        <div className="cards-container">
                            {activeCategory === 'all' ? (
                                // Group by categories when showing all
                                Object.entries(groupCardsByCategory(cards)).map(([categoryId, categoryCards]) => (
                                    <div key={categoryId} className="category-section">
                                        <div className="category-header">
                                            <span className="category-icon">{getCategoryIcon(categoryId)}</span>
                                            <h3 className="category-title">{getCategoryDisplayName(categoryId)}</h3>
                                        </div>
                                        <div className="cards-grid">
                                            {categoryCards.map(renderCard)}
                                        </div>
                                    </div>
                                ))
                            ) : (
                                // Show cards directly when filtering by category
                                <div className="cards-grid">
                                    {cards.map(renderCard)}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default Settings;