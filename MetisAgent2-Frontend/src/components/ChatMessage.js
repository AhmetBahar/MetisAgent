import React, { useState } from 'react';

const ChatMessage = ({ message, isLast, onDecisionChoice }) => {
  const [showDetails, setShowDetails] = useState(false);
  const [copied, setCopied] = useState(false);
  const [selectedChoice, setSelectedChoice] = useState(null);

  const handleCopy = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy text:', err);
    }
  };

  const handleImageDownload = (base64Data, filename) => {
    try {
      // Create download link
      const link = document.createElement('a');
      link.href = `data:image/png;base64,${base64Data}`;
      link.download = filename || 'generated-image.png';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.error('Failed to download image:', err);
    }
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  const renderToolCalls = (toolCalls, toolResults) => {
    if (!toolCalls || !Array.isArray(toolCalls) || toolCalls.length === 0) return null;

    return (
      <div className="tool-calls-section">
        <div className="tool-calls-header">
          <span className="tool-calls-title">🔧 Tool Usage</span>
          <button 
            className="toggle-details"
            onClick={() => setShowDetails(!showDetails)}
          >
            {showDetails ? 'Hide Details' : 'Show Details'}
          </button>
        </div>
        
        {/* Always show command output first */}
        {toolResults && Array.isArray(toolResults) && toolResults.length > 0 && (
          <div className="tool-results-summary">
            {toolResults.map((result, index) => {
              if (result.success && result.data?.stdout) {
                return (
                  <div key={index} className="command-result">
                    <div className="command-info">
                      <strong>Command:</strong> <code>{toolCalls[index]?.params?.command}</code>
                    </div>
                    <pre className="command-output">{result.data.stdout}</pre>
                    {result.data.stderr && (
                      <pre className="command-error">{result.data.stderr}</pre>
                    )}
                  </div>
                );
              }
              return null;
            })}
          </div>
        )}
        
        {showDetails && (
          <div className="tool-calls-details">
            {toolCalls.map((call, index) => {
              const result = toolResults[index];
              return (
                <div key={index} className="tool-call-item">
                  <div className="tool-call-header">
                    <span className="tool-name">{call.tool}</span>
                    <span className="action-name">{call.action}</span>
                    <span className={`status ${result?.success ? 'success' : 'error'}`}>
                      {result?.success ? '✓' : '✗'}
                    </span>
                  </div>
                  
                  {call.params && typeof call.params === 'object' && Object.keys(call.params).length > 0 && (
                    <div className="tool-params">
                      <strong>Parameters:</strong>
                      <pre>{JSON.stringify(call.params, null, 2)}</pre>
                    </div>
                  )}
                  
                  {result && (
                    <div className="tool-result">
                      <strong>Result:</strong>
                      {result.success ? (
                        <div className="result-success">
                          {result.data?.stdout && (
                            <div className="output-section">
                              <strong>Output:</strong>
                              <pre className="command-output">{result.data.stdout}</pre>
                            </div>
                          )}
                          {result.data?.stderr && (
                            <div className="error-section">
                              <strong>Error Output:</strong>
                              <pre className="command-error">{result.data.stderr}</pre>
                            </div>
                          )}
                          {result.data?.return_code !== undefined && (
                            <div className="return-code">
                              <strong>Exit Code:</strong> {result.data.return_code}
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="result-error">
                          <pre>{result.error}</pre>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  };

  const getMessageIcon = () => {
    switch (message.role) {
      case 'user':
        return '👤';
      case 'assistant':
        return <img src="/MetisAgent.png" alt="MetisAgent" className="metis-logo-chat" />;
      case 'system':
        return message.type === 'welcome' ? '👋' : '⚠️';
      default:
        return '💬';
    }
  };

  const handleDecisionChoice = (choice) => {
    setSelectedChoice(choice);
    if (onDecisionChoice) {
      onDecisionChoice(choice, message.decision_id);
    }
  };

  const renderDecisionPanel = () => {
    if (!message.requires_decision || !message.decision_options) return null;
    
    return (
      <div className="decision-panel" style={{
        backgroundColor: '#f8f9fa',
        border: '2px solid #007bff',
        borderRadius: '12px',
        padding: '16px',
        marginTop: '12px',
        boxShadow: '0 2px 8px rgba(0,123,255,0.15)'
      }}>
        <div className="decision-header" style={{
          display: 'flex',
          alignItems: 'center',
          marginBottom: '12px',
          paddingBottom: '8px',
          borderBottom: '1px solid #dee2e6'
        }}>
          <span style={{ fontSize: '18px', marginRight: '8px' }}>🤔</span>
          <h4 style={{ margin: 0, color: '#495057', fontSize: '14px' }}>
            {message.decision_title || 'Please choose an option:'}
          </h4>
        </div>
        
        {message.decision_description && (
          <p style={{ 
            fontSize: '13px', 
            color: '#6c757d', 
            marginBottom: '12px',
            lineHeight: '1.4'
          }}>
            {message.decision_description}
          </p>
        )}
        
        <div className="decision-options" style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '8px'
        }}>
          {message.decision_options.map((option, index) => (
            <button
              key={index}
              onClick={() => handleDecisionChoice(option)}
              disabled={selectedChoice !== null}
              style={{
                backgroundColor: selectedChoice === option ? '#28a745' : '#ffffff',
                color: selectedChoice === option ? 'white' : '#495057',
                border: selectedChoice === option ? '2px solid #28a745' : '2px solid #dee2e6',
                borderRadius: '8px',
                padding: '12px 16px',
                fontSize: '13px',
                cursor: selectedChoice === null ? 'pointer' : 'not-allowed',
                textAlign: 'left',
                transition: 'all 0.2s ease',
                opacity: selectedChoice !== null && selectedChoice !== option ? 0.5 : 1,
                boxShadow: selectedChoice === option ? '0 2px 4px rgba(40,167,69,0.2)' : 'none'
              }}
              onMouseEnter={(e) => {
                if (selectedChoice === null) {
                  e.target.style.backgroundColor = '#f8f9fa';
                  e.target.style.borderColor = '#007bff';
                }
              }}
              onMouseLeave={(e) => {
                if (selectedChoice !== option) {
                  e.target.style.backgroundColor = '#ffffff';
                  e.target.style.borderColor = '#dee2e6';
                }
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <span style={{ 
                  marginRight: '8px',
                  fontSize: '16px'
                }}>
                  {selectedChoice === option ? '✅' : `${index + 1}.`}
                </span>
                <span>{typeof option === 'string' ? option : option.text || option.label}</span>
              </div>
              {typeof option === 'object' && option.description && (
                <div style={{
                  fontSize: '11px',
                  color: selectedChoice === option ? 'rgba(255,255,255,0.8)' : '#6c757d',
                  marginTop: '4px',
                  marginLeft: '24px'
                }}>
                  {option.description}
                </div>
              )}
            </button>
          ))}
        </div>
        
        {selectedChoice && (
          <div style={{
            marginTop: '12px',
            padding: '8px 12px',
            backgroundColor: '#d4edda',
            border: '1px solid #c3e6cb',
            borderRadius: '6px',
            fontSize: '12px',
            color: '#155724'
          }}>
            ✅ Choice selected: <strong>{typeof selectedChoice === 'string' ? selectedChoice : selectedChoice.text || selectedChoice.label}</strong>
          </div>
        )}
      </div>
    );
  };

  const getMessageClass = () => {
    let baseClass = `message-container ${message.role}`;
    if (message.type) {
      baseClass += ` ${message.type}`;
    }
    if (message.has_tool_calls) {
      baseClass += ' with-tools';
    }
    if (message.requires_decision) {
      baseClass += ' with-decision';
    }
    return baseClass;
  };

  return (
    <div className={getMessageClass()}>
      <div className="message-bubble">
        <div className="message-header">
          <div className="message-info">
            <span className="message-icon">{getMessageIcon()}</span>
            <span className="message-role">
              {message.role === 'assistant' && message.provider 
                ? `${message.provider} (${message.model})` 
                : message.role}
            </span>
          </div>
          <div className="message-actions">
            <span className="message-timestamp">
              {formatTimestamp(message.timestamp)}
            </span>
            <button 
              className="copy-button"
              onClick={() => handleCopy(message.content)}
              title="Copy message"
            >
              {copied ? '✓' : '📋'}
            </button>
          </div>
        </div>
        
        <div className="message-content">
          <div className="message-text">
            {message.content}
          </div>
          
          
          {/* Multi-Provider Generated Images */}
          {message.data && message.data.generation_type === 'multi_provider_parallel' && message.data.successful_generations && (
            <div className="multi-provider-images" style={{ marginTop: '15px' }}>
              <div style={{ 
                backgroundColor: '#f8f9fa', 
                padding: '10px', 
                borderRadius: '8px', 
                marginBottom: '15px',
                border: '1px solid #e9ecef'
              }}>
                <h4 style={{ margin: '0 0 5px 0', color: '#495057', fontSize: '14px' }}>
                  🎨 {message.data.generation_summary}
                </h4>
                <small style={{ color: '#6c757d' }}>
                  Success rate: {Math.round(message.data.success_rate * 100)}% • 
                  Choose your favorite from {message.data.success_count} options below
                </small>
              </div>
              
              <div style={{ 
                display: 'grid', 
                gridTemplateColumns: message.data.success_count === 1 ? '1fr' : 
                                   message.data.success_count === 2 ? '1fr 1fr' : 
                                   '1fr 1fr 1fr',
                gap: '15px',
                marginBottom: '10px'
              }}>
                {message.data.successful_generations.map((generation, index) => (
                  <div key={index} style={{
                    border: '2px solid #dee2e6',
                    borderRadius: '12px',
                    overflow: 'hidden',
                    backgroundColor: 'white',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                    transition: 'transform 0.2s, box-shadow 0.2s'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'translateY(-2px)';
                    e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
                  }}>
                    {/* Provider Header */}
                    <div style={{
                      padding: '8px 12px',
                      backgroundColor: generation.provider === 'openai' ? '#10a37f' :
                                     generation.provider === 'gemini' ? '#4285f4' :
                                     generation.provider === 'huggingface' ? '#ff6b35' : '#6c757d',
                      color: 'white',
                      fontSize: '12px',
                      fontWeight: 'bold',
                      textAlign: 'center'
                    }}>
                      {generation.provider === 'openai' ? '🤖 OpenAI GPT-4o' :
                       generation.provider === 'gemini' ? '💎 Google Gemini' :
                       generation.provider === 'huggingface' ? '🤗 HuggingFace' : generation.provider}
                    </div>
                    
                    {/* Image */}
                    <img 
                      src={generation.data.base64_image 
                        ? `data:image/png;base64,${generation.data.base64_image}` 
                        : generation.data.image_url}
                      alt={`Generated by ${generation.provider}`}
                      style={{ 
                        width: '100%', 
                        height: 'auto',
                        display: 'block'
                      }}
                      onError={(e) => {
                        console.error(`${generation.provider} image load error:`, e);
                        e.target.style.display = 'none';
                      }}
                    />
                    
                    {/* Download Section */}
                    <div style={{ padding: '8px 12px', backgroundColor: '#f8f9fa' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <small style={{ color: '#6c757d', fontSize: '10px' }}>
                          📁 {generation.data.local_filename || 'image.png'}
                        </small>
                        <button
                          onClick={() => handleImageDownload(generation.data.base64_image, generation.data.local_filename)}
                          style={{
                            backgroundColor: '#28a745',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            padding: '4px 8px',
                            fontSize: '10px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '3px'
                          }}
                          title="Download image"
                        >
                          💾 Download
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              
              {/* Failed Generations Info */}
              {message.data.failed_generations && Array.isArray(message.data.failed_generations) && message.data.failed_generations.length > 0 && (
                <details style={{ marginTop: '10px' }}>
                  <summary style={{ color: '#dc3545', fontSize: '12px', cursor: 'pointer' }}>
                    ⚠️ {message.data.failed_generations.length} provider(s) failed (click to see details)
                  </summary>
                  <div style={{ marginTop: '5px', fontSize: '11px', color: '#6c757d' }}>
                    {message.data.failed_generations.map((failed, index) => (
                      <div key={index} style={{ margin: '2px 0' }}>
                        • {failed.provider}: {failed.error}
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </div>
          )}
          
          {/* Workflow Image Display - Check for workflow image data */}
          {(() => {
            console.log('🔍 WORKFLOW IMAGE DEBUG - MESSAGE KEYS:', Object.keys(message));
            console.log('🔍 WORKFLOW IMAGE DEBUG - FULL MESSAGE:', message);
            console.log('🔍 WORKFLOW IMAGE DEBUG - DATA OBJECT:', message.data);
            // Check if this is the workflow completion message with image data
            if (message.workflow_id && message.workflow_status === 'completed' && message.data?.has_image) {
              console.log('🎯 WORKFLOW COMPLETION MESSAGE DETECTED!');
              
              // Direct access to base64 - bypass console truncation
              const base64Data = message.data.base64_image;
              console.log('🔍 BASE64 DATA TYPE:', typeof base64Data);
              console.log('🔍 BASE64 DATA LENGTH:', base64Data ? base64Data.length : 0);
              console.log('🔍 BASE64 STARTS WITH:', base64Data ? base64Data.substring(0, 50) : 'N/A');
              console.log('🔍 IS TRUNCATED:', base64Data ? base64Data.includes('[BASE64_IMAGE_DATA_REMOVED') : false);
              
              // Store in window for testing
              window.workflowImageData = {
                base64: base64Data,
                filename: message.data.filename,
                hasImage: message.data.has_image
              };
              console.log('🔍 STORED IN WINDOW.workflowImageData for manual testing');
            }
            return null;
          })()}
          {(
            (message.data && message.data.has_image && (message.data.base64_image || message.data.image_url)) ||
            (message.base64_image) ||
            (message.response_data && message.response_data.base64_image) ||
            (message.workflow_data && message.workflow_data.base64_image)
          ) && (
            <div className="workflow-image" style={{ marginTop: '15px' }}>
              <div style={{
                backgroundColor: '#f8f9fa',
                padding: '10px',
                borderRadius: '8px',
                marginBottom: '10px',
                border: '1px solid #e9ecef'
              }}>
                <h4 style={{ margin: '0 0 5px 0', color: '#495057', fontSize: '14px' }}>
                  🖼️ Generated Image
                </h4>
                <small style={{ color: '#6c757d' }}>
                  Workflow completed with image result
                </small>
              </div>
              
              <div className="image-container">
                <img 
                  src={(() => {
                    // **EFFICIENT FIX**: Prefer file URL over base64 transfer
                    const imageUrl = message.data?.image_url;
                    if (imageUrl) {
                      console.log('🔗 Using efficient file URL:', imageUrl);
                      return imageUrl;
                    }
                    
                    const base64Data = message.data?.base64_image ||
                                     message.base64_image ||
                                     message.response_data?.base64_image ||
                                     message.workflow_data?.base64_image;
                    
                    // Check if it's the truncated placeholder
                    if (base64Data && base64Data.includes('[BASE64_IMAGE_DATA_REMOVED')) {
                      console.log('🔍 TRUNCATED BASE64 DETECTED - FETCHING REAL DATA...');
                      // Try to get real data from data object
                      const realData = message.data?.base64_image;
                      if (realData && !realData.includes('[BASE64_IMAGE_DATA_REMOVED')) {
                        return `data:image/png;base64,${realData}`;
                      }
                    }
                    
                    return `data:image/png;base64,${base64Data}`;
                  })()}
                  alt="Workflow generated image"
                  style={{ 
                    maxWidth: '100%', 
                    height: 'auto', 
                    borderRadius: '8px',
                    border: '1px solid #e0e0e0',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                  }}
                  onError={(e) => {
                    console.error('Workflow image load error:', e);
                    e.target.style.display = 'none';
                  }}
                />
                <div style={{ marginTop: '8px', display: 'flex', gap: '10px', alignItems: 'center' }}>
                  {message.data.filename && (
                    <small style={{ color: '#666', flex: 1 }}>
                      📁 {message.data.filename}
                    </small>
                  )}
                  <button
                    onClick={() => handleImageDownload(
                      message.data?.base64_image ||
                      message.base64_image ||
                      message.response_data?.base64_image ||
                      message.workflow_data?.base64_image,
                      message.data?.filename ||
                      message.filename ||
                      message.response_data?.filename ||
                      message.workflow_data?.filename ||
                      'workflow-image.png'
                    )}
                    style={{
                      backgroundColor: '#007bff',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      padding: '4px 8px',
                      fontSize: '12px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                    title="Download image"
                  >
                    💾 Download
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Single Generated Image (fallback for non-multi-provider) */}
          {message.data && (message.data.image_url || message.data.base64_image) && message.data.generation_type !== 'multi_provider_parallel' && !message.data.has_image && (
            <div className="message-images" style={{ marginTop: '10px' }}>
              <div className="image-container">
                <img 
                  src={message.data.base64_image 
                    ? `data:image/png;base64,${message.data.base64_image}` 
                    : message.data.image_url}
                  alt="Generated image"
                  className="generated-image"
                  style={{ 
                    maxWidth: '100%', 
                    height: 'auto', 
                    borderRadius: '8px',
                    border: '1px solid #e0e0e0',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                  }}
                  onError={(e) => {
                    console.error('Image load error:', e);
                    // Fallback to URL if base64 fails
                    if (message.data.base64_image && message.data.image_url) {
                      e.target.src = message.data.image_url;
                    } else {
                      e.target.style.display = 'none';
                    }
                  }}
                />
                <div style={{ marginTop: '8px', display: 'flex', gap: '10px', alignItems: 'center' }}>
                  {message.data.local_filename && (
                    <small style={{ color: '#666', flex: 1 }}>
                      📁 {message.data.local_filename}
                    </small>
                  )}
                  {message.data.base64_image && (
                    <button
                      onClick={() => handleImageDownload(message.data.base64_image, message.data.local_filename)}
                      style={{
                        backgroundColor: '#007bff',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        padding: '4px 8px',
                        fontSize: '12px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}
                      title="Download image"
                    >
                      💾 Download
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}
          

          {/* Tool Results Images */}
          {message.tool_results && message.tool_results.map((result, index) => {
            // Check for multi-provider first
            if (result.success && result.data && result.data.generation_type === 'multi_provider_parallel') {
              return (
                <div key={index} className="multi-provider-images" style={{ marginTop: '15px' }}>
                  <div style={{ 
                    backgroundColor: '#f8f9fa', 
                    padding: '10px', 
                    borderRadius: '8px', 
                    marginBottom: '15px',
                    border: '1px solid #e9ecef'
                  }}>
                    <h4 style={{ margin: '0 0 5px 0', color: '#495057', fontSize: '14px' }}>
                      🎨 {result.data.generation_summary}
                    </h4>
                    <small style={{ color: '#6c757d' }}>
                      Success rate: {Math.round(result.data.success_rate * 100)}% • 
                      Choose your favorite from {result.data.success_count} options below
                    </small>
                  </div>
                  
                  <div style={{ 
                    display: 'grid', 
                    gridTemplateColumns: result.data.success_count === 1 ? '1fr' : 
                                       result.data.success_count === 2 ? '1fr 1fr' : 
                                       '1fr 1fr 1fr',
                    gap: '15px',
                    marginBottom: '10px'
                  }}>
                    {result.data.successful_generations && result.data.successful_generations.map((generation, genIndex) => (
                      <div key={genIndex} style={{
                        border: '2px solid #dee2e6',
                        borderRadius: '12px',
                        overflow: 'hidden',
                        backgroundColor: 'white',
                        boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                        transition: 'transform 0.2s, box-shadow 0.2s'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.transform = 'translateY(-2px)';
                        e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.transform = 'translateY(0)';
                        e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
                      }}>
                        {/* Provider Header */}
                        <div style={{
                          padding: '8px 12px',
                          backgroundColor: generation.provider === 'openai' ? '#10a37f' :
                                         generation.provider === 'gemini' ? '#4285f4' :
                                         generation.provider === 'huggingface' ? '#ff6b35' : '#6c757d',
                          color: 'white',
                          fontSize: '12px',
                          fontWeight: 'bold',
                          textAlign: 'center'
                        }}>
                          {generation.provider === 'openai' ? '🤖 OpenAI GPT-4o' :
                           generation.provider === 'gemini' ? '💎 Google Gemini' :
                           generation.provider === 'huggingface' ? '🤗 HuggingFace' : generation.provider}
                        </div>
                        
                        {/* Image */}
                        <img 
                          src={generation.data.base64_image 
                            ? `data:image/png;base64,${generation.data.base64_image}` 
                            : generation.data.image_url}
                          alt={`Generated by ${generation.provider}`}
                          style={{ 
                            width: '100%', 
                            height: 'auto',
                            display: 'block'
                          }}
                          onError={(e) => {
                            console.error(`${generation.provider} image load error:`, e);
                            e.target.style.display = 'none';
                          }}
                        />
                        
                        {/* Download Section */}
                        <div style={{ padding: '8px 12px', backgroundColor: '#f8f9fa' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <small style={{ color: '#6c757d', fontSize: '10px' }}>
                              📁 {generation.data.local_filename || 'image.png'}
                            </small>
                            <button
                              onClick={() => handleImageDownload(generation.data.base64_image, generation.data.local_filename)}
                              style={{
                                backgroundColor: '#28a745',
                                color: 'white',
                                border: 'none',
                                borderRadius: '4px',
                                padding: '4px 8px',
                                fontSize: '10px',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '3px'
                              }}
                              title="Download image"
                            >
                              💾 Download
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                  
                  {/* Failed Generations Info */}
                  {result.data.failed_generations && Array.isArray(result.data.failed_generations) && result.data.failed_generations.length > 0 && (
                    <details style={{ marginTop: '10px' }}>
                      <summary style={{ color: '#dc3545', fontSize: '12px', cursor: 'pointer' }}>
                        ⚠️ {result.data.failed_generations.length} provider(s) failed (click to see details)
                      </summary>
                      <div style={{ marginTop: '5px', fontSize: '11px', color: '#6c757d' }}>
                        {result.data.failed_generations.map((failed, failIndex) => (
                          <div key={failIndex} style={{ margin: '2px 0' }}>
                            • {failed.provider}: {failed.error}
                          </div>
                        ))}
                      </div>
                    </details>
                  )}
                </div>
              );
            }
            
            // Check for regular images
            return result.success && result.data && (result.data.image_url || result.data.base64_image) && (
              <div key={index} className="message-images" style={{ marginTop: '10px' }}>
                <div className="image-container">
                  <img 
                    src={result.data.base64_image 
                      ? `data:image/png;base64,${result.data.base64_image}` 
                      : result.data.image_url}
                    alt="Generated image"
                    className="generated-image"
                    style={{ 
                      maxWidth: '100%', 
                      height: 'auto', 
                      borderRadius: '8px',
                      border: '1px solid #e0e0e0',
                      boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                    }}
                    onError={(e) => {
                      console.error('Image load error:', e);
                      if (result.data.base64_image && result.data.image_url) {
                        e.target.src = result.data.image_url;
                      } else {
                        e.target.style.display = 'none';
                      }
                    }}
                  />
                  <div style={{ marginTop: '8px', display: 'flex', gap: '10px', alignItems: 'center' }}>
                    {result.data.local_filename && (
                      <small style={{ color: '#666', flex: 1 }}>
                        📁 {result.data.local_filename}
                      </small>
                    )}
                    {result.data.base64_image && (
                      <button
                        onClick={() => handleImageDownload(result.data.base64_image, result.data.local_filename)}
                        style={{
                          backgroundColor: '#007bff',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          padding: '4px 8px',
                          fontSize: '12px',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px'
                        }}
                        title="Download image"
                      >
                        💾 Download
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
          
          {message.tool_calls && message.tool_results && 
           renderToolCalls(message.tool_calls, message.tool_results)}
          
          {/* Decision Panel - Sequential Thinking Integration */}
          {renderDecisionPanel()}
        </div>
      </div>
    </div>
  );
};

export default ChatMessage;