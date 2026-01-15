import React, { useState, useEffect } from 'react';

const TypingIndicator = ({ provider = 'AI', context = 'general' }) => {
  const [currentMessage, setCurrentMessage] = useState(0);
  
  const getContextualMessages = () => {
    switch (context) {
      case 'command':
        return [
          'Analyzing command safety...',
          'Checking system permissions...',
          'Executing command securely...',
          'Processing command output...',
          'Validating results...'
        ];
      case 'tool_execution':
        return [
          'Loading appropriate tools...',
          'Configuring tool parameters...',
          'Executing tool functions...',
          'Processing tool results...',
          'Formatting response...'
        ];
      case 'llm_processing':
        return [
          `${provider} is analyzing...`,
          'Processing your request...',
          'Generating thoughtful response...',
          'Refining output...',
          'Almost ready...'
        ];
      case 'file_operation':
        return [
          'Accessing file system...',
          'Reading file contents...',
          'Processing file data...',
          'Applying changes...',
          'Saving results...'
        ];
      case 'visual_generation':
        return [
          'Interpreting visual request...',
          'Preparing image generation...',
          'Creating visual content...',
          'Processing generated image...',
          'Optimizing for display...'
        ];
      case 'email_processing':
        return [
          'Connecting to Gmail...',
          'Fetching email data...',
          'Analyzing email content...',
          'Processing attachments...',
          'Formatting response...'
        ];
      default:
        return [
          `${provider} is thinking...`,
          `Analyzing your request...`,
          `Processing...`,
          `Checking available tools...`,
          `Preparing response...`
        ];
    }
  };
  
  const thinkingMessages = getContextualMessages();

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentMessage((prev) => (prev + 1) % thinkingMessages.length);
    }, 2000);

    return () => clearInterval(interval);
  }, [thinkingMessages.length]);

  return (
    <div className="typing-indicator">
      <div className="typing-content">
        <div className="typing-avatar">
          <img src="/MetisAgent.png" alt="MetisAgent" className="metis-logo-typing" />
        </div>
        <div className="typing-bubble">
          <div className="typing-text">
            {thinkingMessages[currentMessage]}
          </div>
          <div className="typing-dots">
            <span className="dot"></span>
            <span className="dot"></span>
            <span className="dot"></span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TypingIndicator;