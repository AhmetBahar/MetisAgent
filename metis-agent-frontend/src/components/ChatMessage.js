// src/components/ChatMessage.js - Geliştirilmiş versiyon
import React, { useState, useEffect } from 'react';
import { Card, Badge, Button, Alert, ProgressBar } from 'react-bootstrap';
import { User, Bot, CheckCircle, ArrowRight, Zap, Copy, ThumbsUp, ThumbsDown, MoreHorizontal, ExternalLink } from 'lucide-react';
import './ChatMessage.css';

/**
 * Geliştirilmiş chat mesaj bileşeni
 * - Workflow güncellemelerini gösterir
 * - İnteraktif eylemler içerir
 * - Animasyonlu geçişler
 * - Mesaj durumu göstergeleri
 */
function ChatMessage({ 
  message, 
  user, 
  isPersonaMessage = false, 
  personaInfo = null,
  onQuickAction = null,
  onFeedback = null 
}) {
  const [showActions, setShowActions] = useState(false);
  const [isCopied, setIsCopied] = useState(false);
  const [expandedContent, setExpandedContent] = useState(false);
  
  // Mesaj türünü belirle
  const isUser = message.sender === 'user';
  const isSystem = message.sender === 'system';
  const isWelcome = message.type === 'welcome';
  const isError = message.type === 'error';
  
  // Persona bilgilerini al
  const displayName = isUser ? (user?.name || 'Sen') 
    : isSystem ? 'Sistem' 
    : (personaInfo?.name || message.sender);
  
  // Workflow güncellemesi varsa
  const workflowUpdate = message.workflow_update;
  const infoUpdates = message.info_updates;
  
  // Debug: Message structure'ı console'a yazdır
  console.log('ChatMessage DEBUG:', {
    message: message,
    hasData: !!message.data,
    dataKeys: message.data ? Object.keys(message.data) : [],
    hasImageUrl: !!(message.data && message.data.image_url),
    hasBase64: !!(message.data && message.data.base64_image),
    messageType: typeof message
  });

  // Mesaj içeriğini işle
  const messageContent = message.content;
  const isLongMessage = messageContent && messageContent.length > 300;
  const displayContent = (isLongMessage && !expandedContent) 
    ? messageContent.substring(0, 300) + "..." 
    : messageContent;
  
  // Kopyalama işlevi
  const handleCopy = () => {
    navigator.clipboard.writeText(messageContent);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };
  
  // Geri bildirim işlevi
  const handleFeedback = (type) => {
    if (onFeedback) {
      onFeedback(message.id, type);
    }
  };
  
  // Hızlı eylem önerileri
  const quickActions = generateQuickActions(message, personaInfo);
  
  return (
    <div 
      className={`chat-message ${isUser ? 'user-message' : 'agent-message'} ${isWelcome ? 'welcome-message' : ''} ${isError ? 'error-message' : ''}`}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      {/* Persona/Kullanıcı Bilgisi */}
      <div className="message-header">
        <div className="sender-info">
          <div className="sender-avatar">
            {isUser ? (
              <User size={20} />
            ) : isSystem ? (
              <Bot size={20} />
            ) : (
              <span className="persona-initial">
                {displayName.charAt(0).toUpperCase()}
              </span>
            )}
          </div>
          <div className="sender-details">
            <span className="sender-name">{displayName}</span>
            <span className="message-time">
              {new Date(message.timestamp).toLocaleTimeString()}
            </span>
          </div>
        </div>
        
        {/* Mesaj Eylemleri */}
        <div className={`message-actions ${showActions ? 'visible' : ''}`}>
          <Button 
            variant="outline-secondary" 
            size="sm" 
            onClick={handleCopy}
            title={isCopied ? 'Kopyalandı!' : 'Kopyala'}
          >
            {isCopied ? <CheckCircle size={14} /> : <Copy size={14} />}
          </Button>
          
          {!isUser && (
            <>
              <Button 
                variant="outline-success" 
                size="sm" 
                onClick={() => handleFeedback('positive')}
                title="Beğen"
              >
                <ThumbsUp size={14} />
              </Button>
              <Button 
                variant="outline-danger" 
                size="sm" 
                onClick={() => handleFeedback('negative')}
                title="Beğenme"
              >
                <ThumbsDown size={14} />
              </Button>
            </>
          )}
          
          <Button variant="outline-secondary" size="sm" title="Daha fazla">
            <MoreHorizontal size={14} />
          </Button>
        </div>
      </div>
      
      {/* Ana Mesaj İçeriği */}
      <div className="message-content">
        <div className={`message-bubble ${isUser ? 'user-bubble' : 'agent-bubble'}`}>
          {/* Workflow Güncellemesi */}
          {workflowUpdate && (
            <Alert variant="info" className="workflow-update mb-2">
              <div className="d-flex align-items-center">
                <ArrowRight size={16} className="me-2" />
                <div>
                  <strong>İş Akışı Güncellendi</strong>
                  <div className="workflow-transition">
                    <Badge bg="secondary">{workflowUpdate.previous}</Badge>
                    <ArrowRight size={12} className="mx-2" />
                    <Badge bg="primary">{workflowUpdate.current}</Badge>
                  </div>
                  {workflowUpdate.message && (
                    <small className="text-muted d-block mt-1">
                      {workflowUpdate.message}
                    </small>
                  )}
                </div>
              </div>
            </Alert>
          )}
          
          {/* Bilgi Güncellemeleri */}
          {infoUpdates && Object.keys(infoUpdates).length > 0 && (
            <Alert variant="success" className="info-updates mb-2">
              <div className="d-flex align-items-center">
                <CheckCircle size={16} className="me-2" />
                <div>
                  <strong>Yeni Bilgiler Eklendi</strong>
                  <div className="info-items">
                    {Object.entries(infoUpdates).map(([key, value]) => (
                      <div key={key} className="info-item">
                        <Badge bg="light" text="dark" className="me-1">
                          {formatFieldName(key)}
                        </Badge>
                        <span>{Array.isArray(value) ? value.join(', ') : value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </Alert>
          )}
          
          {/* Mesaj Metni */}
          <div className="message-text">
            {displayContent}
            
            {isLongMessage && (
              <Button 
                variant="link" 
                size="sm" 
                onClick={() => setExpandedContent(!expandedContent)}
                className="expand-button"
              >
                {expandedContent ? 'Daha az göster' : 'Devamını oku'}
              </Button>
            )}
          </div>
          
          {/* Dosyalar */}
          {message.files && message.files.length > 0 && (
            <div className="message-files">
              {message.files.map((file, index) => (
                <Badge key={index} bg="secondary" className="me-1 mb-1">
                  📎 {file.name}
                </Badge>
              ))}
            </div>
          )}
          
          {/* Generated Images - SimpleAgent Style */}
          {message.data && (message.data.image_url || message.data.base64_image) && (
            <div className="message-images">
              <div className="image-container mb-2">
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
                {message.data.local_filename && (
                  <small className="text-muted d-block mt-1">
                    📁 {message.data.local_filename}
                  </small>
                )}
              </div>
            </div>
          )}
          
          {/* Legacy: Base64 Images Array */}
          {message.images && message.images.length > 0 && (
            <div className="message-images">
              {message.images.map((image, index) => (
                <div key={index} className="image-container mb-2">
                  <img 
                    src={image.startsWith('data:') ? image : `data:image/png;base64,${image}`}
                    alt={`Generated image ${index + 1}`}
                    className="generated-image"
                    style={{ maxWidth: '100%', height: 'auto', borderRadius: '8px' }}
                    onError={(e) => {
                      console.error('Image load error:', e);
                      e.target.style.display = 'none';
                    }}
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      
      {/* Hızlı Eylemler */}
      {quickActions.length > 0 && !isUser && (
        <div className="quick-actions">
          <small className="text-muted mb-2 d-block">Hızlı eylemler:</small>
          <div className="action-buttons">
            {quickActions.map((action, index) => (
              <Button 
                key={index}
                variant="outline-primary" 
                size="sm"
                onClick={() => onQuickAction && onQuickAction(action)}
                className="me-1 mb-1"
              >
                {action.icon && <action.icon size={14} className="me-1" />}
                {action.label}
              </Button>
            ))}
          </div>
        </div>
      )}
      
      {/* İlerleme Göstergesi (Eğer mesajda varsa) */}
      {message.metadata?.progress && (
        <div className="message-progress mt-2">
          <div className="d-flex justify-content-between mb-1">
            <small>İlerleme</small>
            <small>{message.metadata.progress.percentage || 0}%</small>
          </div>
          <ProgressBar 
            now={message.metadata.progress.percentage || 0} 
            variant="primary" 
            size="sm"
          />
        </div>
      )}
    </div>
  );
}

// Yardımcı fonksiyonlar
function formatFieldName(key) {
  const fieldNames = {
    platform: 'Platform',
    target_audience: 'Hedef Kitle',
    main_message: 'Ana Mesaj',
    post_type: 'İçerik Türü',
    tone: 'Ton',
    content_theme: 'Tema',
    visual_ideas: 'Görsel Fikirler',
    hashtags: 'Hashtagler',
    caption: 'Paylaşım Metni'
  };
  
  return fieldNames[key] || key;
}

function generateQuickActions(message, personaInfo) {
  const actions = [];
  
  // Persona türüne göre eylemler
  if (personaInfo?.id === 'social-media') {
    // Sosyal medya personası için özel eylemler
    if (message.content?.includes('Instagram')) {
      actions.push({
        label: 'Instagram İpuçları',
        icon: ExternalLink,
        action: 'instagram_tips'
      });
    }
    
    if (message.content?.includes('hashtag')) {
      actions.push({
        label: 'Hashtag Öner',
        icon: Zap,
        action: 'suggest_hashtags'
      });
    }
    
    if (message.content?.includes('görsel') || message.content?.includes('fotoğraf')) {
      actions.push({
        label: 'Görsel Oluştur',
        icon: Zap,
        action: 'create_visual'
      });
    }
    
    // Her zaman mevcut eylemler
    actions.push({
      label: 'Post Önizle',
      icon: CheckCircle,
      action: 'preview_post'
    });
  }
  
  // Genel eylemler
  if (message.content?.length > 100) {
    actions.push({
      label: 'Özetle',
      icon: Zap,
      action: 'summarize'
    });
  }
  
  return actions.slice(0, 3); // Maksimum 3 eylem göster
}

export default ChatMessage;