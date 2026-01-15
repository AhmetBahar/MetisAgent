import React, { useState } from 'react';
import { apiService } from '../services/apiService';

const CommandInterface = () => {
  const [command, setCommand] = useState('');
  const [output, setOutput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [validationResult, setValidationResult] = useState(null);
  const [commandHistory, setCommandHistory] = useState([]);

  const handleValidateCommand = async () => {
    if (!command.trim()) return;

    try {
      const response = await apiService.validateCommand(command);
      setValidationResult(response);
    } catch (error) {
      setValidationResult({
        success: false,
        error: error.message,
      });
    }
  };

  const handleExecuteCommand = async (e) => {
    e.preventDefault();
    if (!command.trim() || isLoading) return;

    setIsLoading(true);
    setOutput('');

    try {
      const response = await apiService.executeCommand(command, {
        timeout: 120, // Extended timeout for longer operations
        allow_dangerous: false,
      });

      const result = {
        command,
        response,
        timestamp: new Date().toISOString(),
      };

      setCommandHistory(prev => [result, ...prev.slice(0, 9)]); // Keep last 10 commands
      
      if (response.success) {
        const data = response.data;
        let outputText = '';
        
        if (data.stdout) {
          outputText += `STDOUT:\n${data.stdout}\n`;
        }
        
        if (data.stderr) {
          outputText += `STDERR:\n${data.stderr}\n`;
        }
        
        outputText += `\nReturn Code: ${data.return_code}`;
        outputText += `\nPlatform: ${data.platform}`;
        
        setOutput(outputText);
      } else {
        setOutput(`Error: ${response.error}`);
      }
    } catch (error) {
      setOutput(`Error: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleHistoryClick = (historicalCommand) => {
    setCommand(historicalCommand);
    setValidationResult(null);
    setOutput('');
  };

  const getValidationStatusColor = () => {
    if (!validationResult) return '';
    if (validationResult.success) {
      return validationResult.data.is_safe ? 'success' : 'error';
    }
    return 'error';
  };

  return (
    <div className="command-container">
      <h2>Command Executor</h2>
      
      <div className="command-form">
        <form onSubmit={handleExecuteCommand}>
          <div className="input-group">
            <input
              type="text"
              value={command}
              onChange={(e) => {
                setCommand(e.target.value);
                setValidationResult(null);
              }}
              placeholder="Enter command to execute..."
              disabled={isLoading}
            />
            <button
              type="button"
              onClick={handleValidateCommand}
              disabled={isLoading || !command.trim()}
            >
              Validate
            </button>
            <button
              type="submit"
              disabled={isLoading || !command.trim()}
            >
              {isLoading ? 'Executing...' : 'Execute'}
            </button>
          </div>
        </form>
      </div>

      {validationResult && (
        <div className={`validation-result ${getValidationStatusColor()}`}>
          {validationResult.success ? (
            <div>
              <strong>Validation:</strong> {validationResult.data.is_safe ? 'Safe' : 'Unsafe'}
              {validationResult.data.reason && (
                <div>Reason: {validationResult.data.reason}</div>
              )}
              {validationResult.data.severity && (
                <div>Severity: {validationResult.data.severity}</div>
              )}
            </div>
          ) : (
            <div>Validation Error: {validationResult.error}</div>
          )}
        </div>
      )}

      {output && (
        <div className="command-output">
          <strong>Output:</strong>
          <pre>{output}</pre>
        </div>
      )}

      {commandHistory.length > 0 && (
        <div className="command-history">
          <h3>Command History</h3>
          {commandHistory.map((item, index) => (
            <div key={index} className="history-item">
              <div className="history-command">
                <button
                  onClick={() => handleHistoryClick(item.command)}
                  className="history-button"
                >
                  {item.command}
                </button>
                <span className="history-timestamp">
                  {new Date(item.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <div className={`history-status ${item.response.success ? 'success' : 'error'}`}>
                {item.response.success ? 'Success' : 'Failed'}
                {item.response.data && (
                  <span> (Exit Code: {item.response.data.return_code})</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default CommandInterface;