// src/components/Persona/PersonaInfoPanel.js
import React, { useState, useEffect } from 'react';
import { Card, Badge, ProgressBar, Alert } from 'react-bootstrap';
import { User, CheckCircle, Clock, ArrowRight, Zap, Target, MessageSquare } from 'lucide-react';

/**
 * Persona bilgi paneli - Sohbet sırasında toplanan bilgileri ve iş akışını gösterir
 */
function PersonaInfoPanel({ 
  persona, 
  context = {}, 
  workflowSteps = [], 
  currentStep = 'briefing',
  collectedInfo = {},
  onStepClick 
}) {
  const [animatedProgress, setAnimatedProgress] = useState(0);
  const [lastUpdate, setLastUpdate] = useState(null);
  
  // İlerleme hesaplama
  const currentStepIndex = workflowSteps.findIndex(step => step.id === currentStep);
  const progressPercentage = workflowSteps.length > 0 
    ? ((currentStepIndex + 1) / workflowSteps.length) * 100 
    : 0;
  
  // Animasyonlu ilerleme güncellemesi
  useEffect(() => {
    const timer = setTimeout(() => {
      setAnimatedProgress(progressPercentage);
    }, 300);
    return () => clearTimeout(timer);
  }, [progressPercentage]);
  
  // Context değişikliklerini izle
  useEffect(() => {
    if (Object.keys(context).length > 0) {
      setLastUpdate(new Date());
    }
  }, [context]);
  
  // Toplanan bilgileri normalize et
  const normalizedInfo = {
    ...collectedInfo,
    ...context,
    // Sosyal medya personası için özel alanlar
    platform: context.platforms || context.platform || collectedInfo.platform,
    target_audience: context.target_audience || collectedInfo.target_audience,
    main_message: context.main_message || collectedInfo.main_message,
    post_type: context.post_type || collectedInfo.post_type,
    tone: context.tone || collectedInfo.tone
  };
  
  // Boş değerleri filtrele
  const validInfo = Object.entries(normalizedInfo)
    .filter(([key, value]) => value && value !== '' && key !== 'current_step')
    .reduce((acc, [key, value]) => {
      acc[key] = value;
      return acc;
    }, {});
  
  // Alan adlarını türkçeleştir
  const fieldLabels = {
    platform: '📱 Platform',
    platforms: '📱 Platformlar', 
    target_audience: '👥 Hedef Kitle',
    main_message: '💬 Ana Mesaj',
    post_type: '📄 İçerik Türü',
    tone: '🎭 Ton',
    content_theme: '🎨 Tema',
    visual_ideas: '🖼️ Görsel Fikirler',
    hashtags: '# Hashtagler',
    use_emojis: '😊 Emoji Kullanımı',
    caption: '📝 Paylaşım Metni'
  };
  
  return (
    <div className="persona-info-panel p-3">
      {/* Persona Başlığı */}
      <div className="persona-header mb-3">
        <div className="d-flex align-items-center mb-2">
          <div className="persona-avatar me-2">
            <User size={20} />
          </div>
          <div>
            <h6 className="mb-0">{persona?.name || 'Sosyal Medya Uzmanı'}</h6>
            <small className="text-muted">{persona?.description || 'İçerik oluşturuyor'}</small>
          </div>
        </div>
        
        {lastUpdate && (
          <div className="last-update">
            <small className="text-success">
              <CheckCircle size={12} className="me-1" />
              Son güncelleme: {lastUpdate.toLocaleTimeString()}
            </small>
          </div>
        )}
      </div>
      
      {/* İlerleme Çubuğu */}
      {workflowSteps.length > 0 && (
        <Card className="mb-3">
          <Card.Header className="py-2">
            <div className="d-flex justify-content-between align-items-center">
              <small className="fw-bold">İş Akışı İlerlemesi</small>
              <Badge bg="primary">{Math.round(animatedProgress)}%</Badge>
            </div>
          </Card.Header>
          <Card.Body className="py-2">
            <ProgressBar 
              now={animatedProgress} 
              variant={animatedProgress === 100 ? "success" : "primary"}
              animated={animatedProgress > 0 && animatedProgress < 100}
              className="mb-2"
            />
            <div className="current-step">
              <small>
                <strong>Mevcut Adım:</strong> {
                  workflowSteps.find(step => step.id === currentStep)?.label || currentStep
                }
              </small>
            </div>
          </Card.Body>
        </Card>
      )}
      
      {/* Toplanan Bilgiler */}
      <Card className="mb-3">
        <Card.Header className="py-2">
          <div className="d-flex justify-content-between align-items-center">
            <small className="fw-bold">Toplanan Bilgiler</small>
            <Badge bg="info">{Object.keys(validInfo).length}</Badge>
          </div>
        </Card.Header>
        <Card.Body className="py-2">
          {Object.keys(validInfo).length === 0 ? (
            <div className="text-center text-muted py-3">
              <MessageSquare size={24} className="mb-2 d-block mx-auto opacity-50" />
              <small>
                Henüz bilgi toplanmadı<br />
                Sohbete başlayın!
              </small>
            </div>
          ) : (
            <div className="collected-info">
              {Object.entries(validInfo).map(([key, value]) => (
                <div key={key} className="info-item d-flex justify-content-between align-items-start mb-2">
                  <small className="fw-bold text-muted me-2">
                    {fieldLabels[key] || key}:
                  </small>
                  <small className="text-end flex-grow-1">
                    {Array.isArray(value) ? value.join(', ') : String(value)}
                  </small>
                </div>
              ))}
            </div>
          )}
        </Card.Body>
      </Card>
      
      {/* İş Akışı Adımları */}
      {workflowSteps.length > 0 && (
        <Card>
          <Card.Header className="py-2">
            <small className="fw-bold">İş Akışı Adımları</small>
          </Card.Header>
          <Card.Body className="py-2">
            <div className="workflow-steps">
              {workflowSteps.map((step, index) => {
                const isActive = step.id === currentStep;
                const isCompleted = index < currentStepIndex;
                const isPending = index > currentStepIndex;
                
                return (
                  <div 
                    key={step.id} 
                    className={`workflow-step d-flex align-items-center mb-2 ${
                      isActive ? 'active' : ''
                    } ${isCompleted ? 'completed' : ''} ${
                      onStepClick ? 'clickable' : ''
                    }`}
                    onClick={() => onStepClick && onStepClick(step.id)}
                    style={{ cursor: onStepClick ? 'pointer' : 'default' }}
                  >
                    <div className="step-icon me-2">
                      {isCompleted ? (
                        <CheckCircle size={16} className="text-success" />
                      ) : isActive ? (
                        <Zap size={16} className="text-primary" />
                      ) : (
                        <Clock size={16} className="text-muted" />
                      )}
                    </div>
                    <div className="step-info flex-grow-1">
                      <div className={`step-label ${isActive ? 'fw-bold' : ''}`}>
                        <small>{step.label || step.name}</small>
                      </div>
                      {step.description && isActive && (
                        <div className="step-description">
                          <small className="text-muted">{step.description}</small>
                        </div>
                      )}
                    </div>
                    {isActive && (
                      <ArrowRight size={14} className="text-primary" />
                    )}
                  </div>
                );
              })}
            </div>
          </Card.Body>
        </Card>
      )}
      
      {/* Yardım İpucu */}
      {Object.keys(validInfo).length < 3 && (
        <Alert variant="light" className="mt-3 p-2">
          <Target size={16} className="me-2" />
          <small>
            <strong>İpucu:</strong> Daha fazla bilgi vererek post oluşturma sürecini hızlandırabilirsiniz.
          </small>
        </Alert>
      )}
    </div>
  );
}

export default PersonaInfoPanel;