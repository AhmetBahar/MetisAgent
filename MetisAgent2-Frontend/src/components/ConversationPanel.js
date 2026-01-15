import React, { useState, useEffect } from 'react';
import './ConversationPanel.css';
import { apiService } from '../services/apiService';

const ConversationPanel = ({ isVisible, onClose, currentUser, onSelectConversation, currentConversationId }) => {
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isVisible && currentUser) {
      fetchConversations();
    }
  }, [isVisible, currentUser]);

  const fetchConversations = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const userId = currentUser?.email || currentUser?.id;
      const response = await apiService.listConversations(userId);
      
      if (response.success) {
        setConversations(response.data.conversations || []);
      } else {
        setError(response.error || 'Failed to load conversations');
      }
    } catch (err) {
      setError(err.message || 'Failed to load conversations');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectConversation = (conversationId) => {
    if (onSelectConversation) {
      onSelectConversation(conversationId);
    }
    onClose();
  };

  const handleDeleteConversation = async (conversationId, e) => {
    e.stopPropagation();
    
    if (!window.confirm('Are you sure you want to delete this conversation?')) {
      return;
    }
    
    try {
      await apiService.clearConversation(conversationId);
      setConversations(prev => prev.filter(conv => conv.id !== conversationId));
    } catch (err) {
      setError(err.message || 'Failed to delete conversation');
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown';
    try {
      return new Date(dateString).toLocaleDateString('tr-TR', {
        day: '2-digit',
        month: '2-digit', 
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return 'Invalid date';
    }
  };

  if (!isVisible) return null;

  return (
    <div className="conversation-panel-overlay" onClick={onClose}>
      <div className="conversation-panel" onClick={(e) => e.stopPropagation()}>
        <div className="conversation-panel-header">
          <h3>📚 Conversation History</h3>
          <button className="close-button" onClick={onClose}>×</button>
        </div>
        
        <div className="conversation-panel-content">
          {loading && (
            <div className="loading-container">
              <div className="loading-spinner"></div>
              <p>Loading conversations...</p>
            </div>
          )}
          
          {error && (
            <div className="error-container">
              <p className="error-message">⚠️ {error}</p>
              <button onClick={fetchConversations} className="retry-button">
                🔄 Retry
              </button>
            </div>
          )}
          
          {!loading && !error && conversations.length === 0 && (
            <div className="empty-state">
              <p>💭 No conversations found</p>
              <p className="empty-subtitle">Start a new conversation to see it here.</p>
            </div>
          )}
          
          {!loading && conversations.length > 0 && (
            <div className="conversations-list">
              {conversations.map((conversation) => (
                <div
                  key={conversation.id}
                  className={`conversation-item ${
                    conversation.id === currentConversationId ? 'active' : ''
                  }`}
                  onClick={() => handleSelectConversation(conversation.id)}
                >
                  <div className="conversation-header">
                    <h4 className="conversation-title">{conversation.title}</h4>
                    <button
                      className="delete-conversation"
                      onClick={(e) => handleDeleteConversation(conversation.id, e)}
                      title="Delete conversation"
                    >
                      🗑️
                    </button>
                  </div>
                  
                  <div className="conversation-meta">
                    <span className="message-count">
                      💬 {conversation.message_count} messages
                    </span>
                    <span className="conversation-date">
                      📅 {formatDate(conversation.updated_at)}
                    </span>
                  </div>
                  
                  {conversation.preview && (
                    <div className="conversation-preview">
                      {conversation.preview}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
        
        <div className="conversation-panel-footer">
          <button onClick={fetchConversations} className="refresh-button">
            🔄 Refresh
          </button>
          <span className="conversation-count">
            {conversations.length} conversation{conversations.length !== 1 ? 's' : ''}
          </span>
        </div>
      </div>
    </div>
  );
};

export default ConversationPanel;