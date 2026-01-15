import React, { useState } from 'react';
import { apiService } from '../services/apiService';

const ToolsInterface = ({ tools }) => {
  const [selectedTool, setSelectedTool] = useState(null);
  const [toolResult, setToolResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleToolSelect = (tool) => {
    setSelectedTool(tool);
    setToolResult(null);
  };

  const handleActionExecute = async (toolName, actionName, params = {}) => {
    setIsLoading(true);
    setToolResult(null);

    try {
      const response = await apiService.executeToolAction(toolName, actionName, params);
      setToolResult(response);
    } catch (error) {
      setToolResult({
        success: false,
        error: error.message,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const renderToolActions = (tool) => {
    if (!tool.actions) return null;

    return Object.entries(tool.actions).map(([actionName, actionInfo]) => (
      <div key={actionName} className="action-item">
        <h4>{actionName}</h4>
        <p>Required params: {actionInfo.required_params.join(', ') || 'None'}</p>
        <p>Optional params: {actionInfo.optional_params.join(', ') || 'None'}</p>
        <button
          onClick={() => handleActionExecute(tool.name, actionName)}
          disabled={isLoading}
        >
          Execute
        </button>
      </div>
    ));
  };

  return (
    <div className="tools-container">
      <h2>Available Tools</h2>
      
      <div className="tools-layout">
        <div className="tools-list">
          <h3>Tools ({tools.length})</h3>
          {tools.map((tool) => (
            <div
              key={tool.name}
              className={`tool-item ${selectedTool?.name === tool.name ? 'selected' : ''}`}
              onClick={() => handleToolSelect(tool)}
            >
              <h4>{tool.name}</h4>
              <p>{tool.description}</p>
              <div className="tool-meta">
                <span>Version: {tool.version}</span>
                <span className={`status ${tool.is_enabled ? 'enabled' : 'disabled'}`}>
                  {tool.is_enabled ? 'Enabled' : 'Disabled'}
                </span>
              </div>
              <div className="capabilities">
                {tool.capabilities.map((capability, index) => (
                  <span key={index} className="capability-tag">
                    {capability}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="tool-details">
          {selectedTool ? (
            <div>
              <h3>{selectedTool.name}</h3>
              <p>{selectedTool.description}</p>
              
              <div className="tool-info">
                <h4>Information</h4>
                <ul>
                  <li>Version: {selectedTool.version}</li>
                  <li>Status: {selectedTool.is_enabled ? 'Enabled' : 'Disabled'}</li>
                  <li>Capabilities: {selectedTool.capabilities.join(', ')}</li>
                </ul>
              </div>

              <div className="tool-actions">
                <h4>Actions</h4>
                {renderToolActions(selectedTool)}
              </div>

              {toolResult && (
                <div className="tool-result">
                  <h4>Result</h4>
                  <div className={`result-content ${toolResult.success ? 'success' : 'error'}`}>
                    <pre>{JSON.stringify(toolResult, null, 2)}</pre>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="no-selection">
              <p>Select a tool to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ToolsInterface;