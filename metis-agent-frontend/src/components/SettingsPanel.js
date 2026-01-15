import React, { useState } from 'react';

const SettingsPanel = ({ isOpen, onClose }) => {
  return (
    <div className={`settings-panel ${isOpen ? 'open' : ''}`}>
      <div className="settings-header">
        <h2>Settings</h2>
        <button onClick={onClose}>×</button>
      </div>
      <div className="settings-content">
        {/* Settings content goes here */}
        <div className="setting-item">
          <label>Setting 1</label>
          <input type="checkbox" />
        </div>
        <div className="setting-item">
          <label>Setting 2</label>
          <input type="checkbox" />
        </div>
      </div>
    </div>
  );
};

export default SettingsPanel;