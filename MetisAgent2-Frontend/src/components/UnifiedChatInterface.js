import React, { useState, useEffect, useRef } from 'react';
import ChatMessage from './ChatMessage';
import TypingIndicator from './TypingIndicator';
import { apiService } from '../services/apiService';
import { workflowWebSocket } from '../services/workflowWebSocket';
// import { userManager } from '../utils/userManager'; // Disabled for authenticated users

const UnifiedChatInterface = ({ providers = [], onConnectionChange, currentUser, selectedProvider, selectedModel, currentConversationId }) => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [conversationId, setConversationId] = useState('default');
  const [conversations, setConversations] = useState([]);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);


  useEffect(() => {
    // Load conversation when user is available
    if (currentUser && conversationId) {
      loadConversation(conversationId);
    }
    
    // Connect WebSocket with user ID for workflow updates
    if (currentUser) {
      const userId = currentUser.email || currentUser.id;
      workflowWebSocket.connect(userId);
    }
  }, [currentUser, conversationId]);

  // Handle conversation selection from parent
  useEffect(() => {
    if (currentConversationId && currentConversationId !== conversationId) {
      console.log('📚 Loading selected conversation:', currentConversationId);
      setConversationId(currentConversationId);
    }
  }, [currentConversationId]);

  useEffect(() => {
    // Add welcome message if no messages are loaded
    if (currentUser && Array.isArray(messages) && messages.length === 0) {
      const displayName = currentUser.email || currentUser.username || currentUser.name || 'User';
      setMessages([{
        role: 'system',
        content: `Welcome to MetisAgent, ${displayName}! I can help you with various tasks including running commands, file operations, and more. Just ask me what you need to do.`,
        timestamp: new Date().toISOString(),
        type: 'welcome'
      }]);
    }
  }, [currentUser, Array.isArray(messages) ? messages.length : 0]);

  const loadConversation = async (convId) => {
    try {
      const userId = currentUser?.email || currentUser?.id;
      console.log(`📚 Loading conversation ${convId} for user ${userId}`);
      const response = await apiService.getConversation(convId, userId);
      if (response.success && response.data?.messages) {
        console.log(`📚 Loaded ${response.data.messages.length} messages`);
        // Load last 100 messages for performance
        const recentMessages = response.data.messages.slice(-100);
        setMessages(recentMessages);
      }
    } catch (error) {
      console.log('No existing conversation found, starting fresh:', error);
      // This is expected for new conversations
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleDecisionChoice = async (choice, decisionId) => {
    console.log('🤔 Decision choice made:', { choice, decisionId });
    
    try {
      const response = await apiService.submitDecision(decisionId, choice, {
        provider: selectedProvider,
        model: selectedModel,
        user_id: currentUser?.user_id || currentUser?.id || 'anonymous'
      });
      
      if (response.success) {
        // Add decision response to chat
        const decisionResponse = {
          role: 'assistant',
          content: response.data.response || `Decision processed: ${typeof choice === 'string' ? choice : choice.text || choice.label}`,
          timestamp: new Date().toISOString(),
          provider: selectedProvider,
          model: selectedModel,
          tool_calls: response.data.tool_calls || [],
          tool_results: response.data.tool_results || [],
          has_tool_calls: (response.data.tool_calls && Array.isArray(response.data.tool_calls) && response.data.tool_calls.length > 0),
          data: response.data
        };
        setMessages(prev => [...prev, decisionResponse]);
      } else {
        console.error('Decision submission failed:', response.error);
        const errorMessage = {
          role: 'system',
          content: `Decision error: ${response.error}`,
          timestamp: new Date().toISOString(),
          type: 'error'
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      console.error('Decision submission error:', error);
      const errorMessage = {
        role: 'system',
        content: `Decision connection error: ${error.message}`,
        timestamp: new Date().toISOString(),
        type: 'error'
      };
      setMessages(prev => [...prev, errorMessage]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = inputMessage.trim();
    setInputMessage('');
    setIsLoading(true);
    setError(null);

    // Clear todos at the start of each new command
    try {
      if (workflowWebSocket && workflowWebSocket.socket) {
        workflowWebSocket.socket.emit('clear_todos', {
          user_id: currentUser?.user_id || currentUser?.id || 'anonymous',
          timestamp: new Date().toISOString()
        });
      }
    } catch (error) {
      console.warn('Failed to clear todos:', error);
    }

    // Add user message to chat
    const newUserMessage = {
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, newUserMessage]);

    try {
      const response = await apiService.chat(userMessage, {
        provider: selectedProvider,
        model: selectedModel,
        conversation_id: conversationId,
        enable_tools: true,
        user_id: currentUser?.email || currentUser?.id
        // Authentication token is automatically added by apiService interceptor
      });

      if (response.success) {
        // Check if the response has tool calls and results
        const hasToolCalls = response.data.tool_calls && Array.isArray(response.data.tool_calls) && response.data.tool_calls.length > 0;
        const hasToolResults = response.data.tool_results && Array.isArray(response.data.tool_results) && response.data.tool_results.length > 0;
        
        let displayContent = response.data.response || "I'm processing your request...";
        
        // If we have tool results, enhance the display content
        if (hasToolResults) {
          const successfulResults = (response.data.tool_results || []).filter(r => r.success);
          if (successfulResults.length > 0) {
            // Add a brief summary if there are successful tool executions
            displayContent += "\n\n✅ Command executed successfully. See details below.";
          }
        }
        
        const assistantMessage = {
          role: 'assistant',
          content: displayContent,
          timestamp: new Date().toISOString(),
          provider: selectedProvider,
          model: selectedModel,
          tool_calls: response.data.tool_calls || [],
          tool_results: response.data.tool_results || [],
          has_tool_calls: hasToolCalls,
          has_workflow: response.data.has_workflow || false,
          workflow_id: response.data.workflow_id,
          workflow_status: response.data.workflow_status,
          // **FINAL FIX**: Transfer ALL workflow image data from response.data
          data: response.data,  // Add complete response.data
          base64_image: response.data.base64_image,
          has_image: response.data.has_image,
          filename: response.data.filename,
          image_data: response.data.image_data
        };
        setMessages(prev => [...prev, assistantMessage]);
        
        // Ensure WebSocket is connected for workflow updates when tools are used
        if (response.data.has_workflow || hasToolCalls) {
          const userId = currentUser?.user_id || currentUser?.id || 'anonymous';
          if (!workflowWebSocket.getConnectionStatus().isConnected) {
            console.log('🔌 Ensuring WebSocket connection for workflow updates...');
            workflowWebSocket.connect(userId);
          }
        }
      } else {
        const errorMessage = {
          role: 'system',
          content: `Error: ${response.error}`,
          timestamp: new Date().toISOString(),
          type: 'error'
        };
        setMessages(prev => [...prev, errorMessage]);
        setError(response.error);
      }
    } catch (error) {
      const errorMessage = {
        role: 'system',
        content: `Connection Error: ${error.message}`,
        timestamp: new Date().toISOString(),
        type: 'error'
      };
      setMessages(prev => [...prev, errorMessage]);
      setError(error.message);
      onConnectionChange && onConnectionChange(false);
    } finally {
      setIsLoading(false);
    }
  };

  const clearChat = async () => {
    try {
      setMessages([{
        role: 'system',
        content: `Chat cleared. How can I help you, ${currentUser?.username || currentUser?.name || 'User'}?`,
        timestamp: new Date().toISOString(),
        type: 'welcome'
      }]);
      setError(null);
    } catch (error) {
      console.error('Failed to clear conversation:', error);
    }
  };


  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="unified-chat-interface">
      {/* Chat Header */}
      <div className="chat-header">
        <div className="chat-title">
          <h2>AI Assistant</h2>
          <div className="provider-info">
            <span className="provider-badge">{selectedProvider}</span>
            <span className="model-badge">{selectedModel}</span>
          </div>
        </div>
        
        {/* User Session Info */}
        {currentUser && (
          <div className="user-session-info">
            <div className="user-display">
              <span className="user-name">{currentUser.username}</span>
              <span className="session-id" title={`User ID: ${currentUser.user_id || 'N/A'}`}>
                #{currentUser.user_id ? currentUser.user_id.slice(-6) : 'N/A'}
              </span>
            </div>
            <div className="session-stats">
              <span className="message-count" title="Messages in conversation">
                {Array.isArray(messages) ? messages.length : 0} msgs
              </span>
            </div>
          </div>
        )}
        
        <div className="chat-controls">
          <button 
            onClick={clearChat} 
            disabled={isLoading}
            className="clear-button"
            title="Clear conversation"
          >
            Clear
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="error-banner">
          <span className="error-text">{error}</span>
          <button 
            onClick={() => setError(null)}
            className="error-dismiss"
          >
            ×
          </button>
        </div>
      )}

      {/* Messages Container */}
      <div className="messages-container">
        <div className="messages-list">
          {Array.isArray(messages) && messages.map((message, index) => (
            <ChatMessage 
              key={index} 
              message={message} 
              isLast={index === messages.length - 1}
              onDecisionChoice={handleDecisionChoice}
            />
          ))}
          
          {isLoading && (
            <div className="message-container assistant">
              <TypingIndicator provider={selectedProvider} />
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="input-area">
        <form onSubmit={handleSubmit} className="input-form">
          <div className="input-container">
            <textarea
              ref={inputRef}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask me anything... I can run commands, help with files, and more!"
              disabled={isLoading}
              className="message-input"
              rows="1"
            />
            <button 
              type="submit" 
              disabled={isLoading || !inputMessage.trim()}
              className="send-button"
            >
              {isLoading ? (
                <div className="loading-spinner" />
              ) : (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <line x1="22" y1="2" x2="11" y2="13"></line>
                  <polygon points="22,2 15,22 11,13 2,9"></polygon>
                </svg>
              )}
            </button>
          </div>
          
          <div className="input-footer">
            <div className="input-hint">
              💡 Try: "list files in current directory" or "check system status"
            </div>
            <div className="input-stats">
              {inputMessage && inputMessage.length > 0 && (
                <span className="char-count">{inputMessage.length} chars</span>
              )}
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

export default UnifiedChatInterface;