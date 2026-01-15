// src/pages/Settings.js
import React, { useState } from 'react';
import AdaptiveSettingsCards from '../components/AdaptiveSettingsCards';

const Settings = () => {
  const [showLegacySettings, setShowLegacySettings] = useState(false);

  return (
    <div>
      {/* Toggle between new adaptive cards and legacy settings */}
      <div className="mb-4 text-center">
        <button
          onClick={() => setShowLegacySettings(!showLegacySettings)}
          className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 text-sm"
        >
          {showLegacySettings ? 'Use Adaptive Settings Cards' : 'Use Legacy Settings'}
        </button>
      </div>

      {showLegacySettings ? (
        <LegacySettings />
      ) : (
        <AdaptiveSettingsCards />
      )}
    </div>
  );
};

// Legacy settings component (existing code)
const LegacySettings = () => {
  // All the existing settings code goes here...
  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">Legacy Settings</h1>
      <div className="p-6 bg-gray-50 rounded-lg">
        <p className="text-gray-600">
          Legacy hardcoded settings interface. Switch to Adaptive Settings Cards for dynamic, tool-based configuration.
        </p>
      </div>
    </div>
  );
};

export default Settings;