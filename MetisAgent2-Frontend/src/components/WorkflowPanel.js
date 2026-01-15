import React, { useState, useEffect } from 'react';
import './WorkflowPanel.css';
import { workflowWebSocket } from '../services/workflowWebSocket';

const API_BASE_URL = (process.env.REACT_APP_API_URL || 'http://localhost:5001') + '/api';

const WorkflowPanel = ({ isVisible, onClose, currentUser }) => {
  const [workflows, setWorkflows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState({ connected: false });

  useEffect(() => {
    if (isVisible) {
      // FETCH EXISTING WORKFLOWS FROM HTTP API
      fetchWorkflows();
      
      // Debug currentUser
      console.log('🧑 WorkflowPanel currentUser:', currentUser);
      console.log('🧑 WorkflowPanel props:', { isVisible, onClose, currentUser });
      
      // Initialize WebSocket connection for real-time updates
      const userId = currentUser?.email || currentUser?.user_id || currentUser?.id || 'anonymous';
      console.log('🆔 WorkflowPanel resolved userId:', userId);
      console.log('🔍 WorkflowPanel full currentUser object:', JSON.stringify(currentUser, null, 2));
      workflowWebSocket.connect(userId);
      
      // Setup WebSocket event handlers
      const handleConnectionStatus = (status) => {
        setConnectionStatus(status);
        console.log('WebSocket connection status:', status.connected ? 'CONNECTED' : 'DISCONNECTED');
      };
      
      const handleWorkflowStarted = (data) => {
        console.log('🚀 Workflow started event received in WorkflowPanel:', data);
        console.log('🔍 Event data keys:', Object.keys(data || {}));
        console.log('🔍 Workflow object:', data?.workflow);
        console.log('🔍 Steps array:', data?.workflow?.steps);
        
        // Enhanced null safety checks
        if (!data || !data.workflow || !data.workflow.workflow_id) {
          console.warn('Invalid workflow started data:', data);
          return;
        }
        
        // Ensure workflow has required properties with defaults
        const workflow = {
          ...data.workflow,
          steps: data.workflow.steps || [],
          status: data.workflow.status || 'pending',
          title: data.workflow.title || 'Untitled Workflow',
          description: data.workflow.description || 'No description',
          progress_percentage: data.workflow.progress_percentage || 0,
          completed_steps: data.workflow.completed_steps || 0,
          total_steps: data.workflow.total_steps || 0
        };
        
        setWorkflows(prev => {
          const exists = prev.find(w => w && w.workflow_id === workflow.workflow_id);
          if (exists) {
            return prev.map(w => (w && w.workflow_id === workflow.workflow_id) ? workflow : w);
          }
          return [...prev, workflow];
        });
      };
      
      const handleWorkflowUpdate = (data) => {
        console.log('🔄 Workflow update event:', data);
        console.log('🔄 Update - workflow object:', data?.workflow);
        console.log('🔄 Update - steps array:', data?.workflow?.steps);
        console.log('🔄 Update - progress:', data?.workflow?.progress_percentage);
        
        // Enhanced null safety checks
        if (!data || !data.workflow || !data.workflow.workflow_id) {
          console.warn('Invalid workflow update data:', data);
          return;
        }
        
        // Ensure workflow has required properties with defaults
        const workflow = {
          ...data.workflow,
          steps: data.workflow.steps || [],
          status: data.workflow.status || 'pending',
          title: data.workflow.title || 'Untitled Workflow',
          description: data.workflow.description || 'No description',
          progress_percentage: data.workflow.progress_percentage || 0,
          completed_steps: data.workflow.completed_steps || 0,
          total_steps: data.workflow.total_steps || 0
        };
        
        setWorkflows(prev => 
          prev.map(w => (w && w.workflow_id === workflow.workflow_id) ? workflow : w)
        );
      };
      
      const handleStepUpdate = (data) => {
        console.log('📝 Step update event:', data);
        
        // Enhanced null safety checks
        if (!data || !data.step || !data.workflow_id) {
          console.warn('Invalid step update data:', data);
          return;
        }
        
        setWorkflows(prev =>
          prev.map(w => {
            if (w.workflow_id === data.workflow_id && w.steps && Array.isArray(w.steps)) {
              const updatedSteps = w.steps.map(s => 
                (s && s.id === data.step.id) ? { ...data.step } : s
              ).filter(Boolean); // Remove any null/undefined steps
              
              const completedCount = updatedSteps.filter(s => s && s.status === 'completed').length;
              return {
                ...w,
                steps: updatedSteps,
                updated_at: data.timestamp,
                completed_steps: completedCount,
                progress_percentage: updatedSteps.length > 0 ? (completedCount / updatedSteps.length) * 100 : 0
              };
            }
            return w;
          })
        );
      };
      
      const handleWorkflowCompleted = (data) => {
        console.log('✅ Workflow completed event:', data);
        setWorkflows(prev =>
          prev.map(w => 
            w.workflow_id === data.workflow_id 
              ? { ...w, status: data.status, updated_at: data.timestamp }
              : w
          )
        );
      };
      
      // Subscribe to events
      workflowWebSocket.on('connection_status', handleConnectionStatus);
      workflowWebSocket.on('workflow_started', handleWorkflowStarted);
      workflowWebSocket.on('workflow_update', handleWorkflowUpdate);
      workflowWebSocket.on('workflow_step_update', handleStepUpdate);
      workflowWebSocket.on('workflow_completed', handleWorkflowCompleted);
      
      // Cleanup on unmount
      return () => {
        workflowWebSocket.off('connection_status', handleConnectionStatus);
        workflowWebSocket.off('workflow_started', handleWorkflowStarted);
        workflowWebSocket.off('workflow_update', handleWorkflowUpdate);
        workflowWebSocket.off('workflow_step_update', handleStepUpdate);
        workflowWebSocket.off('workflow_completed', handleWorkflowCompleted);
      };
    } else {
      // Disconnect when panel is hidden
      workflowWebSocket.disconnect();
    }
  }, [isVisible, currentUser]);

  // FETCH WORKFLOWS FROM HTTP API
  const fetchWorkflows = async () => {
    setLoading(true);
    setError(null);
    
    try {
      console.log('📡 Fetching workflows from HTTP API...');
      const response = await fetch(`${API_BASE_URL}/workflows`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include'
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('✅ Workflows API Response:', data);
      
      if (data.success && data.data && Array.isArray(data.data.workflows)) {
        // Transform API data to match frontend expected format
        const transformedWorkflows = data.data.workflows.map(wf => ({
          workflow_id: wf.id,
          title: wf.name || wf.user_request,
          description: wf.user_request,
          status: wf.status,
          progress_percentage: wf.progress || 0,
          completed_steps: wf.steps_completed || 0,
          total_steps: wf.steps_total || 0,
          created_at: wf.start_time,
          updated_at: wf.start_time,
          steps: (wf.steps || []).map((step, index) => ({
            id: step.step_id || `step_${index + 1}`,
            title: step.name,
            description: step.description,
            status: step.status,
            tool_name: step.tool_name,
            capability: step.capability,
            error: step.error,
            result: step.result
          }))
        }));
        
        console.log('✅ Transformed workflows:', transformedWorkflows);
        setWorkflows(transformedWorkflows);
      } else {
        console.warn('⚠️ Invalid API response format:', data);
        setWorkflows([]);
      }
    } catch (err) {
      console.error('❌ Error fetching workflows:', err);
      setError(`Failed to load workflows: ${err.message}`);
      setWorkflows([]);
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'planning': return '🎯';
      case 'running': return '⚡';
      case 'completed': return '✅';
      case 'failed': return '❌';
      case 'paused': return '⏸️';
      case 'cancelled': return '🚫';
      default: return '📋';
    }
  };

  const getStepStatusIcon = (status) => {
    switch (status) {
      case 'pending': return '⏳';
      case 'running': return '🔄';
      case 'completed': return '✅';
      case 'failed': return '❌';
      case 'skipped': return '⏭️';
      case 'requires_approval': return '✋';
      default: return '📝';
    }
  };

  const getProgressColor = (percentage) => {
    if (percentage >= 80) return '#4CAF50';
    if (percentage >= 50) return '#FF9800';
    if (percentage >= 20) return '#2196F3';
    return '#9E9E9E';
  };

  const formatDuration = (seconds) => {
    if (!seconds) return 'N/A';
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  };

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'N/A';
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  const cancelWorkflow = async (workflowId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/workflows/${workflowId}/cancel`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        console.log(`Workflow ${workflowId} cancellation requested`);
        // WebSocket will handle the status update automatically
      } else {
        console.error('Failed to cancel workflow');
      }
    } catch (error) {
      console.error('Error cancelling workflow:', error);
    }
  };

  return (
    <div className={`workflow-panel ${!isVisible ? 'hidden' : ''}`}>
      <div className="workflow-header">
        <div className="workflow-title">
          <h2>🔄 Active Workflows</h2>
          <div className="connection-status">
            <span className={`connection-indicator ${connectionStatus.connected ? 'connected' : 'disconnected'}`}>
              {connectionStatus.connected ? '🟢' : '🔴'}
            </span>
            <small>{connectionStatus.connected ? 'Live' : 'Offline'}</small>
          </div>
        </div>
      </div>

      <div className="workflow-content">
        {loading && <div className="loading">Loading workflows...</div>}
        
        {error && (
          <div className="error-message">
            <span className="error-icon">⚠️</span>
            {error}
          </div>
        )}

        {workflows.length === 0 && !loading && !error && (
          <div className="empty-state">
            <div className="empty-icon">📋</div>
            <p>No active workflows</p>
            <small>
              {connectionStatus.connected 
                ? 'Workflows will appear here in real-time when you start multi-step tasks'
                : 'Connecting to real-time updates...'}
            </small>
          </div>
        )}

        {workflows.map((workflow) => (
          <div key={workflow.workflow_id} className="workflow-card">
            <div className="workflow-header-info">
              <div className="workflow-title">
                <span className="status-icon">{getStatusIcon(workflow?.status || 'pending')}</span>
                <h3>{workflow?.title || 'Untitled Workflow'}</h3>
              </div>
              <div className="workflow-meta">
                <span className={`status-badge status-${workflow?.status || 'pending'}`}>
                  {(workflow?.status || 'pending').toUpperCase()}
                </span>
                <span className="progress-text">
                  {workflow?.completed_steps || 0}/{workflow?.total_steps || 0} steps
                </span>
              </div>
            </div>

            <div className="workflow-description">
              <p>{workflow?.description || 'No description available'}</p>
            </div>

            <div className="progress-section">
              <div className="progress-bar">
                <div 
                  className="progress-fill" 
                  style={{ 
                    width: `${workflow?.progress_percentage || 0}%`,
                    backgroundColor: getProgressColor(workflow?.progress_percentage || 0)
                  }}
                ></div>
              </div>
              <span className="progress-percentage">
                {Math.round(workflow?.progress_percentage || 0)}%
              </span>
            </div>

            <div className="workflow-steps">
              <h4>Steps ({workflow?.completed_steps || 0}/{workflow?.total_steps || 0}):</h4>
              <div className="steps-list">
                {(workflow?.steps || []).slice(0, 5).map((step, index) => (
                  <div key={step?.id || index} className={`step-item step-${step?.status || 'pending'}`}>
                    <div className="step-number">{index + 1}</div>
                    <div className="step-content">
                      <div className="step-header">
                        <span className="step-status-icon">
                          {getStepStatusIcon(step?.status || 'pending')}
                        </span>
                        <span className="step-title">{step?.title || step?.name || 'Untitled Step'}</span>
                        {step?.tool_name && (
                          <span className="step-tool">🛠️{step.tool_name}</span>
                        )}
                      </div>
                      {step?.error && (
                        <div className="step-error">
                          ⚠️ {step.error.substring(0, 50)}...
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {(workflow?.steps || []).length > 5 && (
                  <div className="steps-more">
                    +{(workflow?.steps || []).length - 5} more steps...
                  </div>
                )}
              </div>
            </div>

            <div className="workflow-footer">
              <div className="workflow-timestamps">
                <small>
                  <strong>Created:</strong> {formatTimestamp(workflow?.created_at)}
                </small>
                <small>
                  <strong>Updated:</strong> {formatTimestamp(workflow?.updated_at)}
                </small>
              </div>
              <div className="workflow-actions">
                <button 
                  className="btn btn-sm btn-secondary"
                  onClick={fetchWorkflows}
                  disabled={loading}
                >
                  🔄 {loading ? 'Loading...' : 'Refresh'}
                </button>
                {workflow?.status === 'running' && (
                  <button 
                    className="btn btn-sm btn-danger"
                    onClick={() => cancelWorkflow(workflow?.workflow_id)}
                  >
                    🚫 Cancel
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default WorkflowPanel;