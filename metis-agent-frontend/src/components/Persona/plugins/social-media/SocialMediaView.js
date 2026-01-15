// 6. src/components/persona/plugins/social-media/SocialMediaView.js
// Sosyal Medya Persona görünümü

import React, { useState } from 'react';
import { Card, Tabs, Tab, Alert, Spinner } from 'react-bootstrap';
import BriefingStep from './WorkflowSteps/BriefingStep';
import CreativeIdeaStep from './WorkflowSteps/CreativeIdeaStep';
import PostContentStep from './WorkflowSteps/PostContentStep';

function SocialMediaView({ data = {}, onUpdate, onTask, context = {} }) {
  const [activeStep, setActiveStep] = useState(data?.currentStep || 'briefing');
  const [isProcessing, setIsProcessing] = useState(false);
  const [feedback, setFeedback] = useState(null); // {message, type}
  
  // Workflow verileri
  const workflow = data?.workflow || {};
  
  // Feedback gösterme
  const showFeedback = (message, type = 'success') => {
    setFeedback({ message, type });
    setTimeout(() => setFeedback(null), 5000);
  };
  
  // Adım değişikliği
  const handleStepChange = (step) => {
    setActiveStep(step);
    if (onUpdate) {
      onUpdate({
        ...data,
        currentStep: step
      });
    }
  };
  
  // Adım verilerini güncelle
  const updateStepData = async (step, stepData) => {
    const updatedWorkflow = {
      ...workflow,
      [step]: stepData
    };
    
    if (onUpdate) {
      onUpdate({
        ...data,
        workflow: updatedWorkflow
      });
    }
    
    // İlgili adım için görev oluştur ve çalıştır
    if (onTask) {
      setIsProcessing(true);
      try {
        const response = await onTask({
          type: 'process_workflow_step',
          params: {
            post_id: context.post_id || `post_${Date.now()}`,
            step_id: step,
            step_data: stepData
          }
        });
        
        if (response && response.status === 'success') {
          showFeedback('Adım başarıyla işlendi.', 'success');
        } else {
          showFeedback(response?.error || 'Adım işlenirken hata oluştu.', 'danger');
        }
      } catch (error) {
        console.error('Adım işleme hatası:', error);
        showFeedback(`Hata: ${error.message || 'Bilinmeyen hata'}`, 'danger');
      } finally {
        setIsProcessing(false);
      }
    }
  };
  
  return (
    <Card className="social-media-persona h-100">
      <Card.Header>
        <Tabs
          activeKey={activeStep}
          onSelect={(k) => handleStepChange(k)}
          className="card-header-tabs"
        >
          <Tab eventKey="briefing" title="Brifing" />
          <Tab eventKey="creative_idea" title="Yaratıcı Fikir" />
          <Tab eventKey="post_content" title="İçerik" />
        </Tabs>
      </Card.Header>
      <Card.Body>
        {/* Feedback gösterimi */}
        {feedback && (
          <Alert variant={feedback.type} dismissible onClose={() => setFeedback(null)}>
            {feedback.message}
          </Alert>
        )}
        
        {/* Yükleniyor göstergesi */}
        {isProcessing && (
          <div className="text-center mb-3">
            <Spinner animation="border" size="sm" className="me-2" />
            İşleniyor...
          </div>
        )}
        
        {/* Adım bileşenleri */}
        {activeStep === 'briefing' && (
          <BriefingStep
            data={workflow.briefing || {}}
            onChange={(stepData) => updateStepData('briefing', stepData)}
            disabled={isProcessing}
          />
        )}
        
        {activeStep === 'creative_idea' && (
          <CreativeIdeaStep
            data={workflow.creative_idea || {}}
            briefingData={workflow.briefing || {}}
            onChange={(stepData) => updateStepData('creative_idea', stepData)}
            disabled={isProcessing}
          />
        )}
        
        {activeStep === 'post_content' && (
          <PostContentStep
            data={workflow.post_content || {}}
            briefingData={workflow.briefing || {}}
            creativeData={workflow.creative_idea || {}}
            onChange={(stepData) => updateStepData('post_content', stepData)}
            disabled={isProcessing}
          />
        )}
      </Card.Body>
    </Card>
  );
}

export default SocialMediaView;