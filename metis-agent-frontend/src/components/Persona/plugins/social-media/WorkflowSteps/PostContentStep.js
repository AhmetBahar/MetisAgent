// 9. src/components/persona/plugins/social-media/WorkflowSteps/PostContentStep.js
// Sosyal Medya Persona içerik oluşturma adımı

import React, { useState } from 'react';
import { Form, Button, Card, Row, Col, Spinner, Tabs, Tab } from 'react-bootstrap';

function PostContentStep({ 
  data = {}, 
  briefingData = {}, 
  creativeData = {},
  onChange, 
  disabled = false 
}) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeTab, setActiveTab] = useState('captions');
  
  // Form verilerini işle
  const handleInputChange = (field, value) => {
    onChange({
      ...data,
      [field]: value
    });
  };
  
  // Sosyal medya mesajlarını güncelle
  const updateSocialPost = (platform, text) => {
    const updatedPosts = {
      ...(data.socialPosts || {}),
      [platform]: text
    };
    
    handleInputChange('socialPosts', updatedPosts);
  };
  
  // AI içerik üretme
  const generateContent = () => {
    setIsGenerating(true);
    
    // Burada gerçek LLM entegrasyonu yapılabilir
    // Şimdilik simüle ediyoruz
    setTimeout(() => {
      const platforms = briefingData.platforms || [];
      const title = creativeData.title || 'İçerik';
      
      // Platformlara göre içerik oluştur
      const socialPosts = {};
      platforms.forEach(platform => {
        if (platform === 'instagram') {
          socialPosts[platform] = `📱 ${title} #NewTech\n\nTeknoloji hayatımızı nasıl değiştiriyor? Günlük rutininizi kolaylaştıran teknolojiler hakkında düşüncelerinizi paylaşın.\n\n#Teknoloji #Dijital #Yenilik`;
        } else if (platform === 'twitter') {
          socialPosts[platform] = `Teknoloji hayatımızı nasıl değiştiriyor? ${title} hakkındaki düşüncelerinizi paylaşın. #Teknoloji #Dijital #Yenilik`;
        } else if (platform === 'facebook') {
          socialPosts[platform] = `📱 ${title}\n\nTeknoloji hayatımızı her geçen gün değiştiriyor. Sizin favori teknolojik yeniliğiniz nedir? Yorumlarda paylaşın!`;
        } else if (platform === 'linkedin') {
          socialPosts[platform] = `${title}\n\nTeknolojinin iş hayatımıza etkileri gün geçtikçe artıyor. Bu değişim sürecinde adaptasyon sağlamak için neler yapıyorsunuz?\n\n#ProfessionalDevelopment #Technology #Innovation`;
        }
      });
      
      handleInputChange('socialPosts', socialPosts);
      setIsGenerating(false);
    }, 2500);
  };
  
  return (
    <div className="post-content-step">
      <h4>İçerik Oluşturma</h4>
      <p className="text-muted">
        Seçtiğiniz platformlar için sosyal medya içeriğini oluşturun.
      </p>
      
      {/* Yaratıcı fikir özeti */}
      {creativeData && Object.keys(creativeData).length > 0 && (
        <Card className="mb-4 bg-light">
          <Card.Body>
            <h5>Yaratıcı Fikir Özeti</h5>
            <p><strong>Başlık:</strong> {creativeData.title}</p>
            <p><strong>Konsept:</strong> {creativeData.concept}</p>
            {creativeData.tags && creativeData.tags.length > 0 && (
              <p>
                <strong>Etiketler:</strong>{' '}
                {(creativeData.tags || []).map((tag, index) => (
                  <span key={index} className="badge bg-light text-dark me-1">#{tag}</span>
                ))}
              </p>
            )}
          </Card.Body>
        </Card>
      )}
      
      {/* AI İçerik Üretici */}
      <Card className="mb-4">
        <Card.Header>
          <div className="d-flex justify-content-between align-items-center">
            <span>AI İçerik Üretici</span>
            <Button 
              variant="outline-primary" 
              size="sm"
              onClick={generateContent}
              disabled={disabled || isGenerating}
            >
              {isGenerating ? (
                <>
                  <Spinner size="sm" animation="border" className="me-2" />
                  İçerik Üretiliyor...
                </>
              ) : 'İçerik Üret'}
            </Button>
          </div>
        </Card.Header>
        <Card.Body>
          {isGenerating ? (
            <div className="text-center py-3">
              <Spinner animation="border" />
              <p className="mt-2">Platform bazlı içerik üretiliyor...</p>
            </div>
          ) : (
            <p className="text-muted">
              AI'dan platform bazlı içerik önerisi almak için "İçerik Üret" butonuna tıklayın.
              Mevcut brifing ve yaratıcı fikir verilerinize göre otomatik içerik oluşturulacaktır.
            </p>
          )}
        </Card.Body>
      </Card>
      
      {/* Platform bazlı içerik formları */}
      <Tabs
        activeKey={activeTab}
        onSelect={(k) => setActiveTab(k)}
        id="platform-tabs"
        className="mb-3"
      >
        {(briefingData.platforms || []).includes('instagram') && (
          <Tab eventKey="instagram" title="Instagram">
            <Form.Group className="mb-3">
              <Form.Label>Instagram Gönderisi</Form.Label>
              <Form.Control 
                as="textarea" 
                rows={4}
                placeholder="Instagram gönderiniz için metin yazın..."
                value={(data.socialPosts || {}).instagram || ''}
                onChange={(e) => updateSocialPost('instagram', e.target.value)}
                disabled={disabled}
              />
              <Form.Text>
                Hashtag'leri # ile işaretleyin. Emoji kullanabilirsiniz.
              </Form.Text>
            </Form.Group>
          </Tab>
        )}
        
        {(briefingData.platforms || []).includes('twitter') && (
          <Tab eventKey="twitter" title="Twitter">
            <Form.Group className="mb-3">
              <Form.Label>Twitter Gönderisi</Form.Label>
              <Form.Control 
                as="textarea" 
                rows={3}
                placeholder="Twitter gönderiniz için metin yazın..."
                value={(data.socialPosts || {}).twitter || ''}
                onChange={(e) => updateSocialPost('twitter', e.target.value)}
                disabled={disabled}
              />
              <Form.Text>
                Karakter limitini aşmayın. Hashtag'leri # ile işaretleyin.
              </Form.Text>
            </Form.Group>
          </Tab>
        )}
        
        {(briefingData.platforms || []).includes('facebook') && (
          <Tab eventKey="facebook" title="Facebook">
            <Form.Group className="mb-3">
              <Form.Label>Facebook Gönderisi</Form.Label>
              <Form.Control 
                as="textarea" 
                rows={4}
                placeholder="Facebook gönderiniz için metin yazın..."
                value={(data.socialPosts || {}).facebook || ''}
                onChange={(e) => updateSocialPost('facebook', e.target.value)}
                disabled={disabled}
              />
            </Form.Group>
          </Tab>
        )}
        
        {(briefingData.platforms || []).includes('linkedin') && (
          <Tab eventKey="linkedin" title="LinkedIn">
            <Form.Group className="mb-3">
              <Form.Label>LinkedIn Gönderisi</Form.Label>
              <Form.Control 
                as="textarea" 
                rows={4}
                placeholder="LinkedIn gönderiniz için metin yazın..."
                value={(data.socialPosts || {}).linkedin || ''}
                onChange={(e) => updateSocialPost('linkedin', e.target.value)}
                disabled={disabled}
              />
              <Form.Text>
                Profesyonel bir ton kullanmaya özen gösterin.
              </Form.Text>
            </Form.Group>
          </Tab>
        )}
      </Tabs>
      
      {/* Görsel önerisi */}
      <Form.Group className="mb-3">
        <Form.Label>Görsel Açıklaması</Form.Label>
        <Form.Control 
          as="textarea" 
          rows={2}
          placeholder="Gönderi için görsel önerisi veya açıklaması..."
          value={data.imageDescription || ''}
          onChange={(e) => handleInputChange('imageDescription', e.target.value)}
          disabled={disabled}
        />
        <Form.Text>
          Gönderinize eşlik edecek görseli tanımlayın.
        </Form.Text>
      </Form.Group>
      
      <div className="mt-4 text-end">
        <Button 
          variant="primary"
          onClick={() => {
            // Form doğrulama
            const socialPosts = data.socialPosts || {};
            const selectedPlatforms = briefingData.platforms || [];
            
            const emptyPlatforms = selectedPlatforms.filter(
              platform => !socialPosts[platform] || socialPosts[platform].trim() === ''
            );
            
            if (emptyPlatforms.length > 0) {
              alert(`Lütfen ${emptyPlatforms.join(', ')} platformları için içerik oluşturun.`);
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
          İçeriği Tamamla
        </Button>
      </div>
    </div>
  );
}

export default PostContentStep;