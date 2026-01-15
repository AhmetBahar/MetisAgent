// src/components/TypingIndicator.js
import React, { useState, useEffect } from 'react';
import './TypingIndicator.css';

/**
 * Typing indicator bileşeni - LLM yanıtı beklenirken gösterilir
 */
function TypingIndicator({ 
  persona = null,
  messages = [
    "Yaratıcı fikir hazırlanıyor...",
    "İçerik geliştiriliyor...", 
    "Post taslağı oluşturuluyor...",
    "Hashtag önerileri üretiliyor...",
    "Görsel konsepti tasarlanıyor...",
    "Sosyal medya stratejisi analiz ediliyor..."
  ],
  interval = 3000 
}) {
  const [currentMessageIndex, setCurrentMessageIndex] = useState(0);
  const [isVisible, setIsVisible] = useState(true);
  
  // Mesajları döngüsel olarak değiştir
  useEffect(() => {
    if (messages.length <= 1) return;
    
    const timer = setInterval(() => {
      setIsVisible(false);
      
      setTimeout(() => {
        setCurrentMessageIndex(prev => (prev + 1) % messages.length);
        setIsVisible(true);
      }, 300);
    }, interval);
    
    return () => clearInterval(timer);
  }, [messages, interval]);
  
  const currentMessage = messages[currentMessageIndex] || messages[0];
  
  return (
    <div className="typing-indicator-container">
      <div className="typing-message d-flex align-items-center">
        {/* Persona Avatar */}
        {persona && (
          <div className="typing-avatar me-2">
            <div className="avatar-circle">
              {persona.name?.charAt(0) || 'A'}
            </div>
          </div>
        )}
        
        {/* Typing Animation */}
        <div className="typing-bubble">
          <div className="typing-dots">
            <span className="dot"></span>
            <span className="dot"></span>
            <span className="dot"></span>
          </div>
        </div>
        
        {/* Status Message */}
        <div className={`typing-status ms-3 ${isVisible ? 'visible' : 'hidden'}`}>
          <small className="text-muted fst-italic">
            {currentMessage}
          </small>
        </div>
      </div>
    </div>
  );
}

export default TypingIndicator;