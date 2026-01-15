// src/components/PersonaSelector.js
import React, { useState, useEffect } from 'react';
import { Card, Button, Badge, Modal, Form, Alert } from 'react-bootstrap';
import { 
  Users, Code, Server, Share2, Edit, Trash2, Plus, Save, RefreshCw
} from 'lucide-react';
import axios from 'axios';
import './PersonaSelector.css';

const PersonaAPI = {
  getPersonas: async () => {
    try {
      const response = await axios.get('/api/personas');
      return response.data;
    } catch (error) {
      console.error('Personalar alınırken hata:', error);
      throw error;
    }
  },
  
  createPersona: async (personaData) => {
    try {
      const response = await axios.post('/api/personas', personaData);
      return response.data;
    } catch (error) {
      console.error('Persona oluşturulurken hata:', error);
      throw error;
    }
  },
  
  deletePersona: async (personaId) => {
    try {
      const response = await axios.delete(`/api/personas/${personaId}`);
      return response.data;
    } catch (error) {
      console.error('Persona silinirken hata:', error);
      throw error;
    }
  }
};

const getPersonaIcon = (iconName) => {
  switch (iconName) {
    case 'Users': return <Users size={24} />;
    case 'Code': return <Code size={24} />;
    case 'Server': return <Server size={24} />;
    case 'Share2': return <Share2 size={24} />;
    default: return <Users size={24} />;
  }
};

const PersonaSelector = ({ selectedPersona, onSelectPersona }) => {
  const [personas, setPersonas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deletingPersona, setDeletingPersona] = useState(null);
  const [notification, setNotification] = useState(null);
  
  const [newPersona, setNewPersona] = useState({
    id: '',
    name: '',
    description: '',
    icon: 'Users',
    capabilities: [],
    status: 'active'
  });
   
  const fetchPersonas = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await PersonaAPI.getPersonas();
      
      if (response.status === "success") {
        setPersonas(response.personas || []);
        console.log("Personalar yüklendi:", response.personas);
      } else {
        setError(response.message || 'Personalar yüklenemedi');
      }
    } catch (err) {
      console.error('Personalar yüklenirken hata oluştu:', err);
      setError('Personalar yüklenemedi. Lütfen daha sonra tekrar deneyin.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPersonas();
  }, []);

  // Bildirim göster
  const showNotification = (message, type = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 3000);
  };
  
  // Yeni persona ekle
  const handleAddPersona = async () => {
    try {
      if (!newPersona.id || !newPersona.name) {
        showNotification('ID ve isim alanları zorunludur.', 'danger');
        return;
      }
      
      const result = await PersonaAPI.createPersona(newPersona);
      
      if (result.status === "success") {
        setPersonas([...personas, result.persona]);
        setNewPersona({
          id: '',
          name: '',
          description: '',
          icon: 'Users',
          capabilities: [],
          status: 'active'
        });
        setShowAddModal(false);
        showNotification(`Persona başarıyla eklendi: ${result.persona.name}`);
      } else {
        showNotification(`Persona eklenemedi: ${result.message}`, 'danger');
      }
    } catch (err) {
      console.error('Persona eklenirken hata:', err);
      showNotification('Persona eklenirken bir hata oluştu.', 'danger');
    }
  };
  
  // Persona sil
  const handleDeletePersona = async () => {
    if (!deletingPersona) return;
    
    try {
      const result = await PersonaAPI.deletePersona(deletingPersona.id);
      
      if (result.status === "success") {
        setPersonas(personas.filter(p => p.id !== deletingPersona.id));
        setShowDeleteModal(false);
        setDeletingPersona(null);
        showNotification(`Persona başarıyla silindi: ${deletingPersona.name}`);
      } else {
        showNotification(`Persona silinemedi: ${result.message}`, 'danger');
      }
    } catch (err) {
      console.error('Persona silinirken hata:', err);
      showNotification('Persona silinirken bir hata oluştu.', 'danger');
    }
  };
  
  if (loading) {
    return (
      <div className="text-center p-4">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Yükleniyor...</span>
        </div>
        <p className="mt-2">Personalar yükleniyor...</p>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="alert alert-danger m-3" role="alert">
        <p>{error}</p>
        <Button 
          variant="outline-danger" 
          size="sm" 
          onClick={() => window.location.reload()}
          className="mt-2"
        >
          Yeniden Dene
        </Button>
      </div>
    );
  }
  
  return (
    <div className="persona-selector">
      {/* Bildirim */}
      {notification && (
        <Alert 
          variant={notification.type} 
          className="notification"
          onClose={() => setNotification(null)}
          dismissible
        >
          {notification.message}
        </Alert>
      )}
      
      {/* Başlık ve yenile butonu */}
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h5 className="mb-0">Personalar</h5>
        <Button 
          variant="outline-secondary" 
          size="sm" 
          onClick={fetchPersonas}
          disabled={loading}
        >
          {loading ? <span className="spinner-border spinner-border-sm" /> : <RefreshCw size={16} />}
          {' '}
          Yenile
        </Button>
      </div>

      <div className="personas-grid">
        {personas.map(persona => (
          <Card 
            key={persona.id}
            className={`persona-card ${selectedPersona === persona.id ? 'selected' : ''}`}
            onClick={() => onSelectPersona(persona.id)}
          >
            <Card.Body>
              <div className="persona-icon">
                {getPersonaIcon(persona.icon)}
              </div>
              <Card.Title>{persona.name}</Card.Title>
              <Card.Text>{persona.description}</Card.Text>
              
              <div className="persona-capabilities">
                {persona.capabilities && persona.capabilities.map((cap, index) => (
                  <Badge key={index} bg="light" text="dark" className="me-1">
                    {cap}
                  </Badge>
                ))}
              </div>
              
              <div className="persona-actions mt-3">
                {/* Varsayılan personalar için silme butonu gösterme */}
                {!['assistant', 'social-media', 'developer', 'system'].includes(persona.id) && (
                  <Button 
                    variant="outline-danger" 
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeletingPersona(persona);
                      setShowDeleteModal(true);
                    }}
                  >
                    <Trash2 size={16} />
                  </Button>
                )}
              </div>
            </Card.Body>
          </Card>
        ))}
        
        {/* Yeni Persona Ekle Kartı */}
        <Card 
          className="persona-card add-card"
          onClick={() => setShowAddModal(true)}
        >
          <Card.Body className="d-flex flex-column align-items-center justify-content-center">
            <Plus size={32} className="mb-2" />
            <Card.Title>Yeni Persona Ekle</Card.Title>
          </Card.Body>
        </Card>
      </div>
      
      {/* Yeni Persona Ekleme Modalı */}
      <Modal
        show={showAddModal}
        onHide={() => setShowAddModal(false)}
        backdrop="static"
        size="lg"
      >
        <Modal.Header closeButton>
          <Modal.Title>Yeni Persona Ekle</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form>
            <Form.Group className="mb-3">
              <Form.Label>Persona ID</Form.Label>
              <Form.Control
                type="text"
                placeholder="Örn: analytics"
                value={newPersona.id}
                onChange={(e) => setNewPersona({...newPersona, id: e.target.value})}
                required
              />
              <Form.Text className="text-muted">
                Özel bir ID belirleyin (boşluk içermemeli, küçük harflerle)
              </Form.Text>
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>İsim</Form.Label>
              <Form.Control
                type="text"
                placeholder="Örn: Analitik Asistan"
                value={newPersona.name}
                onChange={(e) => setNewPersona({...newPersona, name: e.target.value})}
                required
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Açıklama</Form.Label>
              <Form.Control
                as="textarea"
                rows={2}
                placeholder="Bu persona ne yapar?"
                value={newPersona.description}
                onChange={(e) => setNewPersona({...newPersona, description: e.target.value})}
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>İkon</Form.Label>
              <Form.Select
                value={newPersona.icon}
                onChange={(e) => setNewPersona({...newPersona, icon: e.target.value})}
              >
                <option value="Users">Kullanıcılar (Users)</option>
                <option value="Code">Kod (Code)</option>
                <option value="Server">Sunucu (Server)</option>
                <option value="Share2">Paylaşım (Share2)</option>
              </Form.Select>
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Yetenekler (virgülle ayırın)</Form.Label>
              <Form.Control
                type="text"
                placeholder="Örn: analytics, reporting, data-visualization"
                value={newPersona.capabilities.join(', ')}
                onChange={(e) => setNewPersona({
                  ...newPersona, 
                  capabilities: e.target.value.split(',').map(cap => cap.trim()).filter(Boolean)
                })}
              />
            </Form.Group>
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowAddModal(false)}>
            İptal
          </Button>
          <Button variant="primary" onClick={handleAddPersona}>
            Persona Ekle
          </Button>
        </Modal.Footer>
      </Modal>
      
      {/* Persona Silme Onay Modalı */}
      <Modal
        show={showDeleteModal}
        onHide={() => {
          setShowDeleteModal(false);
          setDeletingPersona(null);
        }}
        backdrop="static"
      >
        <Modal.Header closeButton>
          <Modal.Title>Personayı Sil</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <p>
            <strong>{deletingPersona?.name}</strong> personasını silmek istediğinizden emin misiniz?
          </p>
          <p className="text-muted">
            Bu işlem geri alınamaz ve personanın tüm yapılandırması kaybolacaktır.
          </p>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => {
            setShowDeleteModal(false);
            setDeletingPersona(null);
          }}>
            İptal
          </Button>
          <Button variant="danger" onClick={handleDeletePersona}>
            Personayı Sil
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
};

export default PersonaSelector;