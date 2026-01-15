import React, { useState, useEffect } from 'react';
import GoogleOAuthButton from './GoogleOAuthButton';
import './UserSettings.css';

const PROPERTY_PRESETS = [
  // API Keys
  { name: 'api_key_openai', label: 'OpenAI API Key', type: 'string', encrypted: true, category: 'API Keys', placeholder: 'sk-...', description: 'OpenAI GPT API key' },
  { name: 'api_key_anthropic', label: 'Anthropic API Key', type: 'string', encrypted: true, category: 'API Keys', placeholder: 'sk-ant-...', description: 'Claude API key' },
  { name: 'api_key_huggingface', label: 'HuggingFace API Key', type: 'string', encrypted: true, category: 'API Keys', placeholder: 'hf_...', description: 'HuggingFace Hub API key' },
  { name: 'api_key_google', label: 'Google API Key', type: 'string', encrypted: true, category: 'API Keys', placeholder: 'AIza...', description: 'Google Cloud API key' },
  
  // OAuth Mappings
  { name: 'mapping_google', label: 'Google Account', type: 'string', encrypted: false, category: 'Account Mapping', placeholder: 'user@gmail.com', description: 'Linked Gmail account' },
  { name: 'mapping_github', label: 'GitHub Account', type: 'string', encrypted: false, category: 'Account Mapping', placeholder: 'username', description: 'GitHub username' },
  
  // User Info
  { name: 'display_name', label: 'Display Name', type: 'string', encrypted: false, category: 'Profile', placeholder: 'John Doe', description: 'Your display name' },
  { name: 'email', label: 'Email', type: 'string', encrypted: false, category: 'Profile', placeholder: 'user@example.com', description: 'Primary email address' },
  { name: 'timezone', label: 'Timezone', type: 'string', encrypted: false, category: 'Profile', placeholder: 'Europe/Istanbul', description: 'Your timezone' },
  
  // Settings
  { name: 'email_notifications', label: 'Email Notifications', type: 'bool', encrypted: false, category: 'Settings', description: 'Receive email notifications' },
  { name: 'max_tokens', label: 'Max Tokens', type: 'int', encrypted: false, category: 'Settings', placeholder: '1000', description: 'Maximum tokens per request' },
];

const UserSettings = () => {
  const [properties, setProperties] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  
  // Add/Edit Dialog
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingProperty, setEditingProperty] = useState(null);
  const [dialogData, setDialogData] = useState({
    property_name: '',
    property_value: '',
    property_type: 'string',
    is_encrypted: false,
    isCustom: false
  });
  
  // Visibility toggles for encrypted values
  const [visibleProperties, setVisibleProperties] = useState(new Set());
  
  // Password change dialog
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false);
  const [passwordData, setPasswordData] = useState({
    old_password: '',
    new_password: '',
    confirm_password: ''
  });
  
  const currentUserId = 'ahmetb@minor.com.tr'; // This should come from auth context

  useEffect(() => {
    loadProperties();
  }, []);

  const loadProperties = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/user-storage/properties/${currentUserId}`);
      if (response.ok) {
        const data = await response.json();
        setProperties(data.properties || {});
      } else {
        throw new Error('Failed to load properties');
      }
    } catch (err) {
      setError('Failed to load user properties');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveProperty = async () => {
    try {
      const endpoint = editingProperty 
        ? `/api/user-storage/property/${currentUserId}/${editingProperty}`
        : `/api/user-storage/property/${currentUserId}`;
      
      const response = await fetch(endpoint, {
        method: editingProperty ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          property_name: dialogData.property_name,
          property_value: dialogData.property_value,
          property_type: dialogData.property_type,
          encrypt: dialogData.is_encrypted
        })
      });

      if (response.ok) {
        setSuccess(`Property ${editingProperty ? 'updated' : 'added'} successfully`);
        loadProperties();
        handleCloseDialog();
      } else {
        throw new Error('Failed to save property');
      }
    } catch (err) {
      setError('Failed to save property');
      console.error(err);
    }
  };

  const handleDeleteProperty = async (propertyName) => {
    if (!window.confirm(`Are you sure you want to delete "${propertyName}"?`)) return;
    
    try {
      const response = await fetch(`/api/user-storage/property/${currentUserId}/${propertyName}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        setSuccess('Property deleted successfully');
        loadProperties();
      } else {
        throw new Error('Failed to delete property');
      }
    } catch (err) {
      setError('Failed to delete property');
      console.error(err);
    }
  };

  const handleOpenDialog = (propertyName) => {
    if (propertyName) {
      // Edit existing property
      const property = properties[propertyName];
      
      // API key object'leri için özel handling
      let displayValue = property.property_value;
      if (typeof property.property_value === 'object' && property.property_value?.api_key) {
        displayValue = property.property_value.api_key;
      }
      
      setEditingProperty(propertyName);
      setDialogData({
        property_name: propertyName,
        property_value: displayValue,
        property_type: property.property_type,
        is_encrypted: property.is_encrypted,
        isCustom: !PROPERTY_PRESETS.some(p => p.name === propertyName)
      });
    } else {
      // Add new property
      setEditingProperty(null);
      setDialogData({
        property_name: '',
        property_value: '',
        property_type: 'string',
        is_encrypted: false,
        isCustom: false
      });
    }
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingProperty(null);
    setDialogData({
      property_name: '',
      property_value: '',
      property_type: 'string',
      is_encrypted: false,
      isCustom: false
    });
  };

  const toggleVisibility = (propertyName) => {
    const newVisible = new Set(visibleProperties);
    if (newVisible.has(propertyName)) {
      newVisible.delete(propertyName);
    } else {
      newVisible.add(propertyName);
    }
    setVisibleProperties(newVisible);
  };

  const handlePresetSelect = (preset) => {
    if (preset) {
      setDialogData({
        property_name: preset.name,
        property_value: '',
        property_type: preset.type,
        is_encrypted: preset.encrypted,
        isCustom: false
      });
    } else {
      setDialogData({
        ...dialogData,
        isCustom: true
      });
    }
  };

  const handleChangePassword = async () => {
    if (!passwordData.old_password || !passwordData.new_password || !passwordData.confirm_password) {
      setError('Tüm alanlar gereklidir');
      return;
    }

    if (passwordData.new_password !== passwordData.confirm_password) {
      setError('Yeni şifreler eşleşmiyor');
      return;
    }

    if (passwordData.new_password.length < 6) {
      setError('Yeni şifre en az 6 karakter olmalıdır');
      return;
    }

    try {
      const sessionToken = localStorage.getItem('session_token');
      const response = await fetch('/api/auth/change-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${sessionToken}`
        },
        body: JSON.stringify(passwordData)
      });

      const result = await response.json();

      if (response.ok && result.status === 'success') {
        setSuccess('Şifre başarıyla güncellendi');
        setPasswordDialogOpen(false);
        setPasswordData({
          old_password: '',
          new_password: '',
          confirm_password: ''
        });
      } else {
        setError(result.message || 'Şifre güncellenirken hata oluştu');
      }
    } catch (err) {
      setError('Şifre güncellenirken hata oluştu');
      console.error(err);
    }
  };

  const handleClosePasswordDialog = () => {
    setPasswordDialogOpen(false);
    setPasswordData({
      old_password: '',
      new_password: '',
      confirm_password: ''
    });
  };

  const formatPropertyValue = (property, propertyName) => {
    if (property.is_encrypted) {
      if (visibleProperties.has(propertyName)) {
        // API key object'leri için api_key field'ını al
        if (typeof property.property_value === 'object' && property.property_value?.api_key) {
          return property.property_value.api_key;
        }
        return String(property.property_value);
      } else {
        return '••••••••';
      }
    }
    
    if (property.property_type === 'json') {
      return JSON.stringify(property.property_value);
    }
    
    // Object ise ve api_key field'ı varsa onu göster
    if (typeof property.property_value === 'object' && property.property_value?.api_key) {
      return property.property_value.api_key;
    }
    
    return String(property.property_value);
  };

  const getPropertyCategory = (propertyName) => {
    const preset = PROPERTY_PRESETS.find(p => p.name === propertyName);
    return preset?.category || 'Custom';
  };

  const groupedProperties = Object.entries(properties).reduce((groups, [name, property]) => {
    const category = getPropertyCategory(name);
    if (!groups[category]) groups[category] = [];
    groups[category].push([name, property]);
    return groups;
  }, {});

  if (loading) return <div className="user-settings-loading">Loading user settings...</div>;

  return (
    <div className="user-settings">
      <div className="user-settings-header">
        <h2>User Settings</h2>
        <div className="header-buttons">
          <button className="password-btn" onClick={() => setPasswordDialogOpen(true)}>
            🔐 Change Password
          </button>
          <button className="add-btn" onClick={() => handleOpenDialog()}>
            + Add Property
          </button>
        </div>
      </div>

      {error && (
        <div className="alert alert-error">
          {error}
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      {success && (
        <div className="alert alert-success">
          {success}
          <button onClick={() => setSuccess(null)}>×</button>
        </div>
      )}

      <div className="user-id">User ID: {currentUserId}</div>

      {/* Gmail OAuth Authorization Section */}
      <div className="oauth-section">
        <h3>Gmail Authorization</h3>
        <GoogleOAuthButton 
          userId={currentUserId}
          services={['gmail']}
          onAuthSuccess={(data) => {
            setSuccess('Gmail authorization başarılı!');
            console.log('Gmail OAuth success:', data);
          }}
          onAuthError={(error) => {
            setError(`Gmail authorization hatası: ${error}`);
            console.error('Gmail OAuth error:', error);
          }}
        />
      </div>

      {Object.keys(properties).length === 0 ? (
        <div className="no-properties">
          No properties configured. Click "Add Property" to get started.
        </div>
      ) : (
        Object.entries(groupedProperties).map(([category, categoryProperties]) => (
          <div key={category} className="property-category">
            <h3 className="category-title">{category}</h3>
            <table className="properties-table">
              <thead>
                <tr>
                  <th>Property</th>
                  <th>Value</th>
                  <th>Type</th>
                  <th>Updated</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {categoryProperties.map(([propertyName, property]) => (
                  <tr key={propertyName}>
                    <td>
                      <div className="property-name">
                        <strong>{propertyName}</strong>
                        {property.is_encrypted && (
                          <span className="encrypted-badge">Encrypted</span>
                        )}
                      </div>
                    </td>
                    <td>
                      <div className="property-value">
                        <span className={property.is_encrypted ? 'monospace' : ''}>
                          {formatPropertyValue(property, propertyName)}
                        </span>
                        {property.is_encrypted && (
                          <button
                            className="visibility-btn"
                            onClick={() => toggleVisibility(propertyName)}
                            title={visibleProperties.has(propertyName) ? 'Hide' : 'Show'}
                          >
                            {visibleProperties.has(propertyName) ? '👁️' : '👁️‍🗨️'}
                          </button>
                        )}
                      </div>
                    </td>
                    <td>
                      <span className={`type-badge type-${property.property_type}`}>
                        {property.property_type}
                      </span>
                    </td>
                    <td className="updated-time">
                      {new Date(property.updated_at).toLocaleString()}
                    </td>
                    <td>
                      <div className="actions">
                        <button
                          className="edit-btn"
                          onClick={() => handleOpenDialog(propertyName)}
                          title="Edit"
                        >
                          ✏️
                        </button>
                        <button
                          className="delete-btn"
                          onClick={() => handleDeleteProperty(propertyName)}
                          title="Delete"
                        >
                          🗑️
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))
      )}

      {/* Add/Edit Dialog */}
      {dialogOpen && (
        <div className="dialog-overlay">
          <div className="dialog">
            <div className="dialog-header">
              <h3>{editingProperty ? `Edit Property: ${editingProperty}` : 'Add New Property'}</h3>
              <button className="close-btn" onClick={handleCloseDialog}>×</button>
            </div>
            
            <div className="dialog-content">
              {!editingProperty && (
                <div className="form-group">
                  <label>Property Template</label>
                  <select 
                    onChange={(e) => {
                      if (e.target.value === 'custom') {
                        setDialogData({
                          property_name: '',
                          property_value: '',
                          property_type: 'string',
                          is_encrypted: false,
                          isCustom: true
                        });
                      } else if (e.target.value) {
                        const preset = PROPERTY_PRESETS.find(p => p.name === e.target.value);
                        if (preset) handlePresetSelect(preset);
                      }
                    }}
                    value=""
                  >
                    <option value="">Select a preset or choose Custom</option>
                    {PROPERTY_PRESETS.map(preset => (
                      <option key={preset.name} value={preset.name}>
                        {preset.label} ({preset.category})
                      </option>
                    ))}
                    <option value="custom">Custom Property</option>
                  </select>
                </div>
              )}

              <div className="form-group">
                <label>Property Name *</label>
                <input
                  type="text"
                  value={dialogData.property_name || ''}
                  onChange={(e) => setDialogData({ ...dialogData, property_name: e.target.value })}
                  disabled={editingProperty || (!dialogData.isCustom && dialogData.property_name)}
                  placeholder="e.g., api_key_openai"
                />
                <small>Use lowercase with underscores</small>
              </div>

              <div className="form-group">
                <label>Property Value *</label>
                {dialogData.property_type === 'json' ? (
                  <textarea
                    value={dialogData.property_value || ''}
                    onChange={(e) => setDialogData({ ...dialogData, property_value: e.target.value })}
                    placeholder="Enter valid JSON"
                    rows={4}
                  />
                ) : (
                  <input
                    type={dialogData.property_type === 'int' ? 'number' : 'text'}
                    value={dialogData.property_value || ''}
                    onChange={(e) => setDialogData({ ...dialogData, property_value: e.target.value })}
                    placeholder={PROPERTY_PRESETS.find(p => p.name === dialogData.property_name)?.placeholder || 'Enter value...'}
                  />
                )}
              </div>

              <div className="form-group">
                <label>Property Type</label>
                <select
                  value={dialogData.property_type}
                  onChange={(e) => setDialogData({ ...dialogData, property_type: e.target.value })}
                  disabled={!dialogData.isCustom}
                >
                  <option value="string">String</option>
                  <option value="int">Integer</option>
                  <option value="bool">Boolean</option>
                  <option value="json">JSON</option>
                </select>
              </div>

              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={dialogData.is_encrypted}
                    onChange={(e) => setDialogData({ ...dialogData, is_encrypted: e.target.checked })}
                    disabled={editingProperty !== null}
                  />
                  Encrypt this property
                  {editingProperty && (
                    <small style={{color: '#666', marginLeft: '10px'}}>
                      (Cannot change encryption for existing properties)
                    </small>
                  )}
                </label>
              </div>
            </div>
            
            <div className="dialog-actions">
              <button onClick={handleCloseDialog}>Cancel</button>
              <button 
                onClick={handleSaveProperty}
                disabled={!dialogData.property_name || !dialogData.property_value}
                className="primary"
              >
                {editingProperty ? 'Update' : 'Add'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Password Change Dialog */}
      {passwordDialogOpen && (
        <div className="dialog-overlay">
          <div className="dialog">
            <div className="dialog-header">
              <h3>Change Password</h3>
              <button className="close-btn" onClick={handleClosePasswordDialog}>×</button>
            </div>
            
            <div className="dialog-content">
              <div className="form-group">
                <label>Current Password *</label>
                <input
                  type="password"
                  value={passwordData.old_password}
                  onChange={(e) => setPasswordData({ ...passwordData, old_password: e.target.value })}
                  placeholder="Enter your current password"
                />
              </div>

              <div className="form-group">
                <label>New Password *</label>
                <input
                  type="password"
                  value={passwordData.new_password}
                  onChange={(e) => setPasswordData({ ...passwordData, new_password: e.target.value })}
                  placeholder="Enter new password (min 6 characters)"
                />
              </div>

              <div className="form-group">
                <label>Confirm New Password *</label>
                <input
                  type="password"
                  value={passwordData.confirm_password}
                  onChange={(e) => setPasswordData({ ...passwordData, confirm_password: e.target.value })}
                  placeholder="Confirm your new password"
                />
              </div>
            </div>
            
            <div className="dialog-actions">
              <button onClick={handleClosePasswordDialog}>Cancel</button>
              <button 
                onClick={handleChangePassword}
                disabled={!passwordData.old_password || !passwordData.new_password || !passwordData.confirm_password}
                className="primary"
              >
                Change Password
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserSettings;