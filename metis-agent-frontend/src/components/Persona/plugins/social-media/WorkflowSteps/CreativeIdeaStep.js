// 8. src/components/persona/plugins/social-media/WorkflowSteps/CreativeIdeaStep.js
// Sosyal Medya Persona yaratıcı fikir adımı

import React, { useState } from 'react';
import { Form, Button, Card, Row, Col, Spinner } from 'react-bootstrap';

function CreativeIdeaStep({ data = {}, briefingData = {}, onChange, disabled = false }) {
  const [isGenerating, setIsGenerating] = useState(false);
  
  // Form verilerini işle
  const handleInputChange = (field, value) => {
    onChange({
      ...data,
      [field]: value
    });
  };
  
  // AI önerisi iste
  const generateIdea = () => {
    setIsGenerating(true);
    
    // Burada gerçek LLM entegrasyonu yapılabilir
    // Şimdilik simüle ediyoruz
    setTimeout(() => {
      const platforms = briefingData.platforms || [];
      const targetAudience = briefingData.target_audience || 'genel kullanıcılar';
      
      const generatedIdea = {
        title: 'Yenilikçi Teknoloji Güncellemesi',
        concept: `${targetAudience} için ${platforms.join(', ')} platformlarında paylaşılabilecek içerik. Yeni teknolojilerin günlük hayata etkisini vurgulayan bir seri oluşturulabilir.`,
        tags: ['teknoloji', 'yenilik', 'dijital', 'günlük hayat']
      };
      
      handleInputChange('ai_suggestion', generatedIdea);
      setIsGenerating(false);
    }, 2000);
  };
  
  // AI önerisini kabul et
  const acceptSuggestion = () => {
    if (data.ai_suggestion) {
      handleInputChange('title', data.ai_suggestion.title);
      handleInputChange('concept', data.ai_suggestion.concept);
      handleInputChange('tags', data.ai_suggestion.tags);
    }
  };
  
  return (
    <div className="creative-idea-step">
      <h4>Yaratıcı Fikir Geliştirme</h4>
      <p className="text-muted">
        Brifing bilgilerinize göre içerik fikri oluşturun veya AI önerisi alın.
      </p>
      
      {/* Brifing özeti */}
      {briefingData && Object.keys(briefingData).length > 0 && (
        <Card className="mb-4 bg-light">
          <Card.Body>
            <h5>Brifing Özeti</h5>
            <Row>
              <Col sm={6}>
                <p><strong>Amaç:</strong> {briefingData.purpose === 'engagement' ? 'Etkileşim' : 
                briefingData.purpose === 'awareness' ? 'Marka Bilinirliği' : 
                briefingData.purpose === 'conversion' ? 'Dönüşüm' : 
                briefingData.purpose === 'education' ? 'Eğitim' : briefingData.purpose}</p>
                <p><strong>Hedef Kitle:</strong> {briefingData.target_audience}</p>
              </Col>
              <Col sm={6}>
                <p><strong>Ana Mesaj:</strong> {briefingData.main_message}</p>
                <p><strong>Platformlar:</strong> {(briefingData.platforms || []).join(', ')}</p>
              </Col>
            </Row>
          </Card.Body>
        </Card>
      )}
      
      <Form>
        {/* AI Önerisi */}
        <Card className="mb-4">
          <Card.Header>
            <div className="d-flex justify-content-between align-items-center">
              <span>AI Önerisi</span>
              <Button 
                variant="outline-primary" 
                size="sm"
                onClick={generateIdea}
                disabled={disabled || isGenerating}
              >
                {isGenerating ? (
                  <>
                    <Spinner size="sm" animation="border" className="me-2" />
                    Fikir Üretiliyor...
                  </>
                ) : 'Öneri Al'}
              </Button>
            </div>
          </Card.Header>
          <Card.Body>
            {isGenerating ? (
              <div className="text-center py-3">
                <Spinner animation="border" />
                <p className="mt-2">Yaratıcı fikirler üretiliyor...</p>
              </div>
            ) : data.ai_suggestion ? (
              <div>
                <h5>{data.ai_suggestion.title}</h5>
                <p>{data.ai_suggestion.concept}</p>
                <div className="mb-2">
                  <strong>Önerilen Etiketler:</strong>{' '}
                  {(data.ai_suggestion.tags || []).map((tag, index) => (
                    <span key={index} className="badge bg-light text-dark me-1">#{tag}</span>
                  ))}
                </div>
                <div className="text-end">
                  <Button 
                    variant="success" 
                    size="sm"
                    onClick={acceptSuggestion}
                    disabled={disabled}
                  >
                    Bu Öneriyi Kullan
                  </Button>
                </div>
              </div>
            ) : (
              <p className="text-muted">
                AI'dan yaratıcı fikir önerisi almak için "Öneri Al" butonuna tıklayın.
              </p>
            )}
          </Card.Body>
        </Card>
        
        {/* Manuel form */}
        <Form.Group className="mb-3">
          <Form.Label>İçerik Başlığı</Form.Label>
          <Form.Control 
            type="text" 
            placeholder="İçeriğinize bir başlık verin"
            value={data.title || ''}
            onChange={(e) => handleInputChange('title', e.target.value)}
            disabled={disabled}
          />
        </Form.Group>
        
        <Form.Group className="mb-3">
          <Form.Label>İçerik Konsepti</Form.Label>
          <Form.Control 
            as="textarea" 
            rows={3}
            placeholder="İçeriğinizin temel fikrini açıklayın..."
            value={data.concept || ''}
            onChange={(e) => handleInputChange('concept', e.target.value)}
            disabled={disabled}
          />
        </Form.Group>
        
        <Form.Group className="mb-3">
          <Form.Label>Etiketler (virgülle ayırın)</Form.Label>
          <Form.Control 
            type="text" 
            placeholder="Örn: teknoloji, trend, dijital"
            value={(data.tags || []).join(', ')}
            onChange={(e) => handleInputChange('tags', 
              e.target.value.split(',')
                .map(tag => tag.trim().toLowerCase())
                .filter(Boolean)
            )}
            disabled={disabled}
          />
        </Form.Group>
        
        <div className="mt-4 text-end">
          <Button 
            variant="primary"
            onClick={() => {
              // Form doğrulama
              if (!data.title) {
                alert("Lütfen bir başlık girin.");
                return;
              }
              if (!data.concept) {
                alert("Lütfen içerik konseptini açıklayın.");
                return;
              }
              
              // Verileri kaydet
              onChange({
                ...data,
                completed: true
              });
            }}
            disabled={disabled}
          >
            Fikri Kaydet ve İlerle
          </Button>
        </div>
      </Form>
    </div>
  );
}

export default CreativeIdeaStep;