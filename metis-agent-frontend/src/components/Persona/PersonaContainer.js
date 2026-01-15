// PersonaContainer.js - Güncellenmiş
import React, { Suspense, useEffect, useState } from 'react';
import { Card, Alert, Spinner } from 'react-bootstrap';
import { personaRegistry } from './registry';
import DefaultPersonaView from './base/DefaultPersonaView';
import PersonaInfoPanel from './PersonaInfoPanel';

/**
 * Persona içerik container bileşeni
 * Sohbet odaklı etkileşim ve bilgi paneli entegrasyonu
 */
function PersonaContainer({
  personaId,
  data,
  onUpdate,
  onTask,
  context,
  availablePersonas,
  onSelectPersona,
  inChatMode = true // Yeni parametre: sohbet modunda kullanım için
}) {
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  
  // Persona metadata'sını almak için yeni state
  const [personaMetadata, setPersonaMetadata] = useState(null);
  
  // Persona plugin'ini yükle
  useEffect(() => {
    if (!personaId) return;
    
    const loadPersonaPlugin = async () => {
      if (!personaRegistry.getPlugin(personaId)) {
        setLoading(true);
        try {
          const success = await personaRegistry.loadPlugin(personaId);
          if (!success) {
            setError(`Persona yüklenemedi: ${personaId}`);
          } else {
            // Plugin bilgilerini metadata state'ine kaydet
            const plugin = personaRegistry.getPlugin(personaId);
            setPersonaMetadata(plugin);
          }
        } catch (err) {
          setError(`Persona yükleme hatası: ${err.message}`);
        } finally {
          setLoading(false);
        }
      } else {
        // Zaten yüklü ise, metadata'yı al
        const plugin = personaRegistry.getPlugin(personaId);
        setPersonaMetadata(plugin);
      }
    };
    
    loadPersonaPlugin();
  }, [personaId]);
  
  // Yükleme göstergesi
  if (loading) {
    return (
      <Card className="persona-container h-100">
        <Card.Body className="d-flex justify-content-center align-items-center py-5">
          <Spinner animation="border" />
          <span className="ms-2">Persona yükleniyor...</span>
        </Card.Body>
      </Card>
    );
  }
  
  // Hata durumu
  if (error) {
    return (
      <Card className="persona-container h-100">
        <Card.Body>
          <Alert variant="danger">{error}</Alert>
          {!inChatMode && (
            <DefaultPersonaView 
              data={data} 
              onUpdate={onUpdate}
              onTask={onTask}
              context={context}
            />
          )}
        </Card.Body>
      </Card>
    );
  }
  
  // Persona plugin'ini al
  const plugin = personaRegistry.getPlugin(personaId);
  
  // Sohbet modunda ise sadece bilgi panelini göster
  if (inChatMode) {
    // İş akışı adımlarını hazırla
    const workflowSteps = personaMetadata?.workflow_steps || [];
    // Mevcut adım (context'ten veya data'dan al)
    const currentStep = context?.current_step || data?.current_step || 
                       (workflowSteps.length > 0 ? workflowSteps[0].id : null);
    
    return (
      <PersonaInfoPanel
        persona={personaMetadata}
        context={context}
        workflowSteps={workflowSteps}
        currentStep={currentStep}
      />
    );
  }
  
  // Plugin bulunamadıysa varsayılan görünümü göster
  if (!plugin || !plugin.component) {
    return (
      <div className="persona-full-container">
        {/* Persona Seçim Listesi */}
        {availablePersonas && availablePersonas.length > 0 && (
          <div className="persona-selector mb-3">
            <h5>Personalar</h5>
            <div className="persona-list d-flex flex-wrap gap-2">
              {availablePersonas.map(persona => (
                <Card 
                  key={persona.id} 
                  className={`persona-item ${personaId === persona.id ? 'active' : ''}`}
                  style={{ cursor: 'pointer', maxWidth: '150px' }}
                  onClick={() => onSelectPersona(persona.id)}
                >
                  <Card.Body className="p-2">
                    <h6 className="mb-1">{persona.name || persona.id}</h6>
                    <small className="text-muted">{persona.description?.substring(0, 50) || ''}</small>
                  </Card.Body>
                </Card>
              ))}
            </div>
          </div>
        )}
        <DefaultPersonaView 
          data={data} 
          onUpdate={onUpdate}
          onTask={onTask}
          context={context}
        />
      </div>
    );
  }
  
  // Lazy yüklenen komponenti render et
  const PersonaComponent = plugin.component;
  
  return (
    <div className="persona-full-container">
      {/* Persona Seçim Listesi */}
      {availablePersonas && availablePersonas.length > 0 && (
        <div className="persona-selector mb-3">
          <h5>Personalar</h5>
          <div className="persona-list d-flex flex-wrap gap-2">
            {availablePersonas.map(persona => (
              <Card 
                key={persona.id} 
                className={`persona-item ${personaId === persona.id ? 'active' : ''}`}
                style={{ cursor: 'pointer', maxWidth: '150px' }}
                onClick={() => onSelectPersona(persona.id)}
              >
                <Card.Body className="p-2">
                  <h6 className="mb-1">{persona.name || persona.id}</h6>
                  <small className="text-muted">{persona.description?.substring(0, 50) || ''}</small>
                </Card.Body>
              </Card>
            ))}
          </div>
        </div>
      )}
      
      {/* Persona Komponenti */}
      <Suspense fallback={
        <Card className="persona-container h-100">
          <Card.Body className="d-flex justify-content-center align-items-center py-5">
            <Spinner animation="border" />
          </Card.Body>
        </Card>
      }>
        <PersonaComponent
          data={data}
          onUpdate={onUpdate}
          onTask={onTask}
          context={context}
        />
      </Suspense>
    </div>
  );
}

export default PersonaContainer;