// 3. src/components/persona/base/DefaultPersonaView.js
// Varsayılan persona görünümü bileşeni

import React, { useState } from 'react';
import { Card, Alert, Form, Button, Spinner } from 'react-bootstrap';

/**
 * Varsayılan persona görünümü
 * Herhangi bir plugin yüklenemediğinde veya bulunmadığında kullanılır
 */
function DefaultPersonaView({ data = {}, onUpdate, onTask, context = {} }) {
  const [isProcessing, setIsProcessing] = useState(false);
  const [responseText, setResponseText] = useState('');

  // Form verilerini işle
  const handlePromptChange = (value) => {
    if (onUpdate) {
      onUpdate({
        ...data,
        prompt: value
      });
    }
  };
  
  // Görev gönderimi
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!data.prompt || !onTask) return;
    
    setIsProcessing(true);
    setResponseText('');
    
    try {
      // Görevi gönder
      const task = {
        type: 'execute_prompt',
        params: {
          prompt: data.prompt,
          context: context
        }
      };
      
      const response = await onTask(task);
      
      // Başarılı yanıt
      if (response && response.status === 'success') {
        setResponseText(response.result || 'Görev başarıyla tamamlandı.');
      } else {
        setResponseText(response?.error || 'Görev başarısız oldu.');
      }
      
      // Prompt alanını temizle
      handlePromptChange('');
    } catch (error) {
      console.error('Görev gönderme hatası:', error);
      setResponseText(`Hata: ${error.message || 'Bilinmeyen hata'}`);
    } finally {
      setIsProcessing(false);
    }
  };
  
  return (
    <Card className="default-persona h-100">
      <Card.Header>Standart Asistan</Card.Header>
      <Card.Body>
        <Alert variant="info">
          <Alert.Heading>Temel Mod</Alert.Heading>
          <p>
            Sistem şu anda temel modda çalışıyor. Spesifik bir personaya geçiş yapabilir 
            veya bu arayüzü kullanarak temel komutlar gönderebilirsiniz.
          </p>
        </Alert>
        
        {responseText && (
          <Alert variant="success" className="mt-3">
            <pre className="mb-0">{responseText}</pre>
          </Alert>
        )}
        
        <Form onSubmit={handleSubmit}>
          <Form.Group className="mb-3">
            <Form.Label>Komut/Görev</Form.Label>
            <Form.Control
              as="textarea"
              rows={4}
              placeholder="Yapmak istediğiniz görevi yazın..."
              value={data.prompt || ''}
              onChange={(e) => handlePromptChange(e.target.value)}
            />
          </Form.Group>
          
          <div className="d-grid gap-2">
            <Button 
              variant="primary" 
              type="submit"
              disabled={!data.prompt || isProcessing}
            >
              {isProcessing ? (
                <>
                  <Spinner
                    as="span"
                    animation="border"
                    size="sm"
                    role="status"
                    aria-hidden="true"
                    className="me-2"
                  />
                  İşleniyor...
                </>
              ) : 'Gönder'}
            </Button>
          </div>
        </Form>
      </Card.Body>
    </Card>
  );
}

export default DefaultPersonaView;