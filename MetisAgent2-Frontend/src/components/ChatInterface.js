import React, { useState, useEffect, useRef } from 'react';
import { apiService } from '../services/apiService';

const ChatInterface = ({ providers }) => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState('openai');
  const [selectedModel, setSelectedModel] = useState('');
  const [conversationId, setConversationId] = useState('default');
  const [systemPrompt, setSystemPrompt] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (providers.length > 0) {
      const availableProvider = providers.find(p => p.available);
      if (availableProvider) {
        setSelectedProvider(availableProvider.id);
        setSelectedModel(availableProvider.default_model);
      }
    }
  }, [providers]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = inputMessage.trim();
    setInputMessage('');
    setIsLoading(true);

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
        system_prompt: systemPrompt || undefined,
      });

      if (response.success) {
        const assistantMessage = {
          role: 'assistant',
          content: response.data.response,
          timestamp: new Date().toISOString(),
        };
        setMessages(prev => [...prev, assistantMessage]);
      } else {
        const errorMessage = {
          role: 'system',
          content: `Error: ${response.error}`,
          timestamp: new Date().toISOString(),
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      const errorMessage = {
        role: 'system',
        content: `Error: ${error.message}`,
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const clearChat = async () => {
    try {
      await apiService.clearConversation(conversationId);
      setMessages([]);
    } catch (error) {
      console.error('Failed to clear conversation:', error);
    }
  };

  const getProviderModels = () => {
    const provider = providers.find(p => p.id === selectedProvider);
    return provider ? provider.models : [];
  };

  return (
    <div className="chat-container">
      <div className="chat-controls">
        <div className="control-group">
          <label>Provider:</label>
          <select 
            value={selectedProvider} 
            onChange={(e) => setSelectedProvider(e.target.value)}
            disabled={isLoading}
          >
            {providers.map(provider => (
              <option 
                key={provider.id} 
                value={provider.id}
                disabled={!provider.available}
              >
                {provider.name} {!provider.available && '(Not Available)'}
              </option>
            ))}
          </select>
        </div>

        <div className="control-group">
          <label>Model:</label>
          <select 
            value={selectedModel} 
            onChange={(e) => setSelectedModel(e.target.value)}
            disabled={isLoading}
          >
            {getProviderModels().map(model => (
              <option key={model} value={model}>
                {model}
              </option>
            ))}
          </select>
        </div>

        <div className="control-group">
          <label>Conversation ID:</label>
          <input
            type="text"
            value={conversationId}
            onChange={(e) => setConversationId(e.target.value)}
            disabled={isLoading}
            placeholder="default"
          />
        </div>

        <button onClick={clearChat} disabled={isLoading}>
          Clear Chat
        </button>
      </div>

      <div className="system-prompt-container">
        <textarea
          placeholder="System prompt (optional)"
          value={systemPrompt}
          onChange={(e) => setSystemPrompt(e.target.value)}
          disabled={isLoading}
          rows="3"
        />
      </div>

      <div className="messages-container">
        {messages.map((message, index) => (
          <div key={index} className={`message ${message.role}`}>
            <div className="message-header">
              <span className="role">{message.role}</span>
              <span className="timestamp">
                {new Date(message.timestamp).toLocaleTimeString()}
              </span>
            </div>
            <div className="message-content">
              {message.content}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="message assistant">
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="input-container">
        <input
          type="text"
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          placeholder="Type your message..."
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading || !inputMessage.trim()}>
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </form>
    </div>
  );
};

export default ChatInterface;