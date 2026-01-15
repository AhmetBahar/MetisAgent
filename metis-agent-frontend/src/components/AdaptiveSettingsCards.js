// src/components/AdaptiveSettingsCards.js
import React, { useState, useEffect } from 'react';
import { 
  Save, 
  RotateCcw, 
  CheckCircle, 
  AlertTriangle, 
  Settings as SettingsIcon,
  Key,
  Shield,
  Monitor,
  User,
  ExternalLink
} from 'lucide-react';

const AdaptiveSettingsCards = () => {
  const [cards, setCards] = useState([]);
  const [categories, setCategories] = useState([]);
  const [activeCategory, setActiveCategory] = useState('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionStates, setActionStates] = useState({});
  const [formData, setFormData] = useState({});

  // Load settings cards
  useEffect(() => {
    loadSettingsCards();
    loadCategories();
  }, []);

  const loadSettingsCards = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:5001/api/settings/cards?user_id=test_user');
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setCards(data.cards || []);
      
      // Initialize form data for value cards
      const initialFormData = {};
      data.cards.forEach(card => {
        if (card.type === 'value' && card.current_values) {
          initialFormData[card.card_id] = card.current_values;
        }
      });
      setFormData(initialFormData);
      
    } catch (err) {
      console.error('Error loading settings cards:', err);
      setError('Failed to load settings cards: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadCategories = async () => {
    try {
      const response = await fetch('http://localhost:5001/api/settings/categories');
      if (response.ok) {
        const data = await response.json();
        setCategories(data.categories || []);
      }
    } catch (err) {
      console.error('Error loading categories:', err);
    }
  };

  const getCategoryIcon = (category) => {
    const iconMap = {
      'authentication': Shield,
      'api_keys': Key,
      'tools': SettingsIcon,
      'monitoring': Monitor,
      'preferences': User
    };
    return iconMap[category] || SettingsIcon;
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'authorized':
      case 'healthy':
      case 'connected':
        return 'text-green-600';
      case 'not_authorized':
      case 'error':
      case 'failed':
        return 'text-red-600';
      case 'warning':
        return 'text-yellow-600';
      default:
        return 'text-gray-500';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'authorized':
      case 'healthy':
      case 'connected':
        return '✅';
      case 'not_authorized':
      case 'error':
      case 'failed':
        return '❌';
      case 'warning':
        return '⚠️';
      default:
        return '❓';
    }
  };

  const executeCardAction = async (cardId, actionId) => {
    try {
      setActionStates(prev => ({ ...prev, [`${cardId}_${actionId}`]: 'loading' }));

      const response = await fetch('http://localhost:5001/api/settings/cards/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          card_id: cardId,
          action_id: actionId,
          user_id: 'test_user'
        })
      });

      const result = await response.json();
      
      if (result.success) {
        setActionStates(prev => ({ ...prev, [`${cardId}_${actionId}`]: 'success' }));
        // Refresh cards to show updated status
        await loadSettingsCards();
        
        // If action returns an auth_url, open it
        if (result.data?.auth_url) {
          window.open(result.data.auth_url, '_blank');
        }
      } else {
        setActionStates(prev => ({ ...prev, [`${cardId}_${actionId}`]: 'error' }));
        setError(result.error || 'Action failed');
      }

    } catch (err) {
      console.error('Error executing action:', err);
      setActionStates(prev => ({ ...prev, [`${cardId}_${actionId}`]: 'error' }));
      setError('Failed to execute action: ' + err.message);
    }

    // Clear action state after 3 seconds
    setTimeout(() => {
      setActionStates(prev => {
        const newState = { ...prev };
        delete newState[`${cardId}_${actionId}`];
        return newState;
      });
    }, 3000);
  };

  const saveCardValues = async (cardId) => {
    try {
      setActionStates(prev => ({ ...prev, [`${cardId}_save`]: 'loading' }));

      const response = await fetch('http://localhost:5001/api/settings/cards/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          card_id: cardId,
          values: formData[cardId] || {},
          user_id: 'test_user'
        })
      });

      const result = await response.json();
      
      if (result.success) {
        setActionStates(prev => ({ ...prev, [`${cardId}_save`]: 'success' }));
        // Refresh cards to show updated values
        await loadSettingsCards();
      } else {
        setActionStates(prev => ({ ...prev, [`${cardId}_save`]: 'error' }));
        setError(result.error || 'Save failed');
      }

    } catch (err) {
      console.error('Error saving values:', err);
      setActionStates(prev => ({ ...prev, [`${cardId}_save`]: 'error' }));
      setError('Failed to save values: ' + err.message);
    }

    // Clear action state after 3 seconds
    setTimeout(() => {
      setActionStates(prev => {
        const newState = { ...prev };
        delete newState[`${cardId}_save`];
        return newState;
      });
    }, 3000);
  };

  const updateFormField = (cardId, fieldName, value) => {
    setFormData(prev => ({
      ...prev,
      [cardId]: {
        ...prev[cardId],
        [fieldName]: value
      }
    }));
  };

  const renderActionCard = (card) => (
    <div key={card.card_id} className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center">
          <span className="text-2xl mr-3">{card.icon}</span>
          <div>
            <h3 className="text-lg font-medium text-gray-900">{card.title}</h3>
            <p className="text-sm text-gray-600">{card.description}</p>
          </div>
        </div>
        <div className={`flex items-center ${getStatusColor(card.status)}`}>
          <span className="mr-1">{getStatusIcon(card.status)}</span>
          <span className="text-sm font-medium">{card.status}</span>
        </div>
      </div>

      {/* Actions */}
      <div className="flex flex-wrap gap-2">
        {card.metadata?.actions?.map(action => {
          const actionKey = `${card.card_id}_${action.id}`;
          const actionState = actionStates[actionKey];
          
          return (
            <button
              key={action.id}
              onClick={() => executeCardAction(card.card_id, action.id)}
              disabled={actionState === 'loading'}
              className={`px-4 py-2 rounded-md text-sm font-medium flex items-center ${
                action.type === 'primary'
                  ? 'bg-blue-500 text-white hover:bg-blue-600'
                  : action.type === 'danger'
                  ? 'bg-red-500 text-white hover:bg-red-600'
                  : 'bg-gray-500 text-white hover:bg-gray-600'
              } ${
                actionState === 'loading' ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            >
              {actionState === 'loading' ? (
                <>
                  <RotateCcw size={16} className="animate-spin mr-2" />
                  Loading...
                </>
              ) : actionState === 'success' ? (
                <>
                  <CheckCircle size={16} className="mr-2" />
                  {action.label}
                </>
              ) : actionState === 'error' ? (
                <>
                  <AlertTriangle size={16} className="mr-2" />
                  {action.label}
                </>
              ) : (
                <>
                  {action.id === 'authorize' && <ExternalLink size={16} className="mr-2" />}
                  {action.label}
                </>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );

  const renderValueCard = (card) => (
    <div key={card.card_id} className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center">
          <span className="text-2xl mr-3">{card.icon}</span>
          <div>
            <h3 className="text-lg font-medium text-gray-900">{card.title}</h3>
            <p className="text-sm text-gray-600">{card.description}</p>
          </div>
        </div>
      </div>

      {/* Form Fields */}
      {card.metadata?.form_schema?.fields && (
        <div className="space-y-4">
          {card.metadata.form_schema.fields.map(field => (
            <div key={field.name}>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {field.label}
                {field.required && <span className="text-red-500 ml-1">*</span>}
              </label>
              
              {field.type === 'text' || field.type === 'email' ? (
                <input
                  type={field.type}
                  value={formData[card.card_id]?.[field.name] || ''}
                  onChange={(e) => updateFormField(card.card_id, field.name, e.target.value)}
                  placeholder={field.placeholder}
                  className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required={field.required}
                />
              ) : field.type === 'password' ? (
                <input
                  type="password"
                  value={formData[card.card_id]?.[field.name] || ''}
                  onChange={(e) => updateFormField(card.card_id, field.name, e.target.value)}
                  placeholder={field.placeholder}
                  className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required={field.required}
                />
              ) : field.type === 'checkbox' ? (
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData[card.card_id]?.[field.name] || false}
                    onChange={(e) => updateFormField(card.card_id, field.name, e.target.checked)}
                    className="mr-2"
                  />
                  <span className="text-sm text-gray-600">{field.placeholder}</span>
                </div>
              ) : null}
            </div>
          ))}

          {/* Save Button */}
          <div className="pt-4">
            <button
              onClick={() => saveCardValues(card.card_id)}
              disabled={actionStates[`${card.card_id}_save`] === 'loading'}
              className={`px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 flex items-center ${
                actionStates[`${card.card_id}_save`] === 'loading' ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            >
              {actionStates[`${card.card_id}_save`] === 'loading' ? (
                <>
                  <RotateCcw size={16} className="animate-spin mr-2" />
                  Saving...
                </>
              ) : actionStates[`${card.card_id}_save`] === 'success' ? (
                <>
                  <CheckCircle size={16} className="mr-2" />
                  Saved
                </>
              ) : (
                <>
                  <Save size={16} className="mr-2" />
                  Save
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );

  const renderStatusCard = (card) => (
    <div key={card.card_id} className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center">
          <span className="text-2xl mr-3">{card.icon}</span>
          <div>
            <h3 className="text-lg font-medium text-gray-900">{card.title}</h3>
            <p className="text-sm text-gray-600">{card.description}</p>
          </div>
        </div>
        <div className={`flex items-center ${getStatusColor(card.status)}`}>
          <span className="mr-1">{getStatusIcon(card.status)}</span>
          <span className="text-sm font-medium">{card.status}</span>
        </div>
      </div>

      {/* Metrics */}
      {card.metadata?.metrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {card.metadata.metrics.map((metric, index) => (
            <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-md">
              <div className="flex items-center">
                {metric.icon && <span className="mr-2">{metric.icon}</span>}
                <span className="text-sm font-medium">{metric.name}</span>
              </div>
              <span className={`text-sm font-bold ${getStatusColor(metric.status)}`}>
                {metric.value}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  const filteredCards = cards.filter(card => 
    activeCategory === 'all' || card.category === activeCategory
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <RotateCcw size={24} className="animate-spin mr-2" />
        <span>Loading settings...</span>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      {/* Error Display */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md">
          <div className="flex items-center text-red-600">
            <AlertTriangle size={20} className="mr-2" />
            <span>{error}</span>
          </div>
        </div>
      )}

      {/* Category Tabs */}
      {categories.length > 0 && (
        <div className="mb-6">
          <div className="flex flex-wrap gap-2">
            {categories.map(category => {
              const IconComponent = getCategoryIcon(category.id);
              return (
                <button
                  key={category.id}
                  onClick={() => setActiveCategory(category.id)}
                  className={`px-4 py-2 rounded-md flex items-center text-sm font-medium ${
                    activeCategory === category.id
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  <IconComponent size={16} className="mr-2" />
                  {category.name}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Settings Cards */}
      <div className="space-y-6">
        {filteredCards.length === 0 ? (
          <div className="text-center p-8 text-gray-500">
            <SettingsIcon size={48} className="mx-auto mb-4 opacity-50" />
            <p>No settings cards available for this category.</p>
          </div>
        ) : (
          filteredCards.map(card => {
            switch (card.type) {
              case 'action':
                return renderActionCard(card);
              case 'value':
                return renderValueCard(card);
              case 'status':
                return renderStatusCard(card);
              default:
                return null;
            }
          })
        )}
      </div>

      {/* Refresh Button */}
      <div className="mt-8 text-center">
        <button
          onClick={loadSettingsCards}
          className="px-4 py-2 bg-gray-500 text-white rounded-md hover:bg-gray-600 flex items-center mx-auto"
        >
          <RotateCcw size={16} className="mr-2" />
          Refresh Settings
        </button>
      </div>
    </div>
  );
};

export default AdaptiveSettingsCards;