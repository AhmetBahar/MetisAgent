// 7. src/components/persona/plugins/social-media/WorkflowSteps/BriefingStep.js
// Sosyal Medya Persona brifing adımı

import React from 'react';
import { Form, Button, Row, Col } from 'react-bootstrap';

function BriefingStep({ data = {}, onChange, disabled = false }) {
  // Form verilerini işle
  const handleInputChange = (field, value) => {
    onChange({
      ...data,
      [field]: value
    });
  };
  
  // Platform seçimi
  const handlePlatformChange = (platform, checked) => {
    const currentPlatforms = data.platforms || [];
    
    if (checked && !currentPlatforms.includes(platform)) {
      // Platform ekle
      handleInputChange('platforms', [...currentPlatforms, platform]);
    } else if (!checked && currentPlatforms.includes(platform)) {
      // Platform çıkar
      handleInputChange('platforms', currentPlatforms.filter(p => p !== platform));
    }
  };
  
  return (
    <div className="briefing-step">
      <h4>Sosyal Medya İçerik Brifingi</h4>
      <p className="text-muted">
        İçerik oluşturma sürecinin ilk adımı. Hedef kitlenizi, içeriğin amacını ve 
        hedeflenen platformları belirleyin.
      </p>
      
      <Form>
        <Form.Group className="mb-3">
          <Form.Label>İçerik Amacı</Form.Label>
          <Form.Select 
            value={data.purpose || ''} 
            onChange={(e) => handleInputChange('purpose', e.target.value)}
            disabled={disabled}
          >
            <option value="">Seçiniz...</option>
            <option value="engagement">Etkileşim</option>
            <option value="awareness">Marka Bilinirliği</option>
            <option value="conversion">Dönüşüm</option>
            <option value="education">Eğitim</option>
          </Form.Select>
          <Form.Text>İçeriğinizin ana amacını seçin</Form.Text>
        </Form.Group>
        
        <Form.Group className="mb-3">
          <Form.Label>Hedef Kitle</Form.Label>
          <Form.Control 
            type="text" 
            placeholder="Örn: 25-34 yaş arası, teknoloji meraklısı profesyoneller"
            value={data.target_audience || ''}
            onChange={(e) => handleInputChange('target_audience', e.target.value)}
            disabled={disabled}
          />
        </Form.Group>
        
        <Form.Group className="mb-3">
          <Form.Label>Ana Mesaj</Form.Label>
          <Form.Control 
            as="textarea" 
            rows={3}
            placeholder="İçeriğinizin iletmek istediği ana mesaj..."
            value={data.main_message || ''}
            onChange={(e) => handleInputChange('main_message', e.target.value)}
            disabled={disabled}
          />
        </Form.Group>
        
        <Form.Group className="mb-3">
          <Form.Label>Platformlar</Form.Label>
          <div>
            <Form.Check 
              inline
              type="checkbox"
              id="platform-instagram"
              label="Instagram"
              checked={(data.platforms || []).includes('instagram')}
              onChange={(e) => handlePlatformChange('instagram', e.target.checked)}
              disabled={disabled}
            />
            <Form.Check 
              inline
              type="checkbox"
              id="platform-facebook"
              label="Facebook"
              checked={(data.platforms || []).includes('facebook')}
              onChange={(e) => handlePlatformChange('facebook', e.target.checked)}
              disabled={disabled}
            />
            <Form.Check 
              inline
              type="checkbox"
              id="platform-twitter"
              label="Twitter"
              checked={(data.platforms || []).includes('twitter')}
              onChange={(e) => handlePlatformChange('twitter', e.target.checked)}
              disabled={disabled}
            />
            <Form.Check 
              inline
              type="checkbox"
              id="platform-linkedin"
              label="LinkedIn"
              checked={(data.platforms || []).includes('linkedin')}
              onChange={(e) => handlePlatformChange('linkedin', e.target.checked)}
              disabled={disabled}
            />
          </div>
        </Form.Group>
        
        <div className="mt-4 text-end">
          <Button 
            variant="primary"
            onClick={() => {
              // Form doğrulama
              if (!data.purpose) {
                alert("Lütfen bir amaç seçin.");
                return;
              }
              if (!data.target_audience) {
                alert("Lütfen hedef kitle belirtin.");
                return;
              }
              if (!data.main_message) {
                alert("Lütfen ana mesajınızı yazın.");
                return;
              }
              if (!(data.platforms || []).length) {
                alert("Lütfen en az bir platform seçin.");
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
            Brifing Bilgilerini Kaydet
          </Button>
        </div>
      </Form>
    </div>
  );
}

export default BriefingStep;