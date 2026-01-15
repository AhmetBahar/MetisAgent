// src/components/ToolsPanel.js
import React, { useState, useEffect } from 'react';
import { Button, Form, ListGroup, Accordion, Badge, Modal, InputGroup, FormControl, Alert } from 'react-bootstrap';
import { 
  FileText, Wrench as Tool, Code, Database, GitBranch, Server, Globe, Shield,
  Users, HardDrive, Terminal, Activity, Share2, Search, RefreshCw,
  Plus, Trash2, Edit, X, Check, AlertCircle, Cloud, ExternalLink
} from 'lucide-react';
import axios from 'axios';
import './ToolsPanel.css';

// Gerçek API servisi
const ToolsAPI = {
  getAvailableTools: async () => {
    try {
      const response = await axios.get('/api/registry/tools');
      
      // Her bir aracın status değerini kontrol et
      const toolsWithStatus = response.data.tools.map(tool => {
        // Eğer status tanımlı değilse veya aktif değilse
        if (!tool.status) {
          // Sağlık durumunu kontrol et
          return { ...tool, status: 'active' }; // Varsayılan olarak aktif
        }
        return tool;
      });
      
      return { ...response.data, tools: toolsWithStatus };
    } catch (error) {
      console.error('Registry araçları alınırken hata:', error);
      throw error;
    }
  },
  
  getToolStatus: async (toolId) => {
    try {
      const response = await axios.get(`/api/registry/tool/${toolId}/health`);
      return response.data.health;
    } catch (error) {
      console.error(`Araç durumu alınırken hata (${toolId}):`, error);
      throw error;
    }
  },

  getToolDetails: async (toolId) => {
    try {
      const response = await axios.get(`/api/registry/tool/${toolId}`);
      return response.data;
    } catch (error) {
      console.error(`Araç detayları alınırken hata (${toolId}):`, error);
      throw error;
    }
  },

  addExternalTool: async (toolData) => {
    try {
      const response = await axios.post('/api/registry/external/add', {
        name: toolData.name,
        config: {
          base_url: toolData.baseUrl,
          auth_token: toolData.authToken,
          version: toolData.version || '1.0.0'
        },
        capabilities: toolData.capabilities || []
      });
      return response.data;
    } catch (error) {
      console.error('Dış kaynak aracı eklenirken hata:', error);
      throw error;
    }
  },

  addRemoteTool: async (toolData) => {
    try {
      const response = await axios.post('/api/registry/remote/add', {
        name: toolData.name,
        remote_url: toolData.remoteUrl,
        auth_info: toolData.authInfo || {}
      });
      return response.data;
    } catch (error) {
      console.error('Uzak araç eklenirken hata:', error);
      throw error;
    }
  },

  deleteTool: async (toolId) => {
    try {
      const response = await axios.delete(`/api/registry/tool/${toolId}`);
      return response.data;
    } catch (error) {
      console.error(`Araç silinirken hata (${toolId}):`, error);
      throw error;
    }
  },

  syncRemoteTools: async (remoteUrl, authInfo) => {
    try {
      const response = await axios.post('/api/registry/remote/sync', {
        remote_url: remoteUrl,
        auth_info: authInfo || {}
      });
      return response.data;
    } catch (error) {
      console.error('Uzak araçlar senkronize edilirken hata:', error);
      throw error;
    }
  }
};

const ToolsPanel = () => {
  const [tools, setTools] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedTool, setSelectedTool] = useState(null);
  const [toolDetails, setToolDetails] = useState(null);
  const [showOnlyActive, setShowOnlyActive] = useState(false);
  
  // Yeni state değişkenleri
  const [showAddExternalToolModal, setShowAddExternalToolModal] = useState(false);
  const [showAddRemoteToolModal, setShowAddRemoteToolModal] = useState(false);
  const [showDeleteConfirmModal, setShowDeleteConfirmModal] = useState(false);
  const [showSyncModal, setShowSyncModal] = useState(false);
  
  const [newExternalTool, setNewExternalTool] = useState({
    name: '',
    baseUrl: '',
    authToken: '',
    version: '1.0.0',
    capabilities: []
  });
  
  const [newRemoteTool, setNewRemoteTool] = useState({
    name: '',
    remoteUrl: '',
    authInfo: {
      username: '',
      password: ''
    }
  });
  
  const [newCapability, setNewCapability] = useState('');
  const [deletingTool, setDeletingTool] = useState(null);
  const [notification, setNotification] = useState(null);
  const [syncConfig, setSyncConfig] = useState({
    remoteUrl: '',
    authInfo: {
      username: '',
      password: ''
    }
  });
  
  // Bildirim göster
  const showNotification = (message, type = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 5000);
  };
  
  // Araçları yükle
  useEffect(() => {
    const fetchTools = async () => {
      try {
        setLoading(true);
        const data = await ToolsAPI.getAvailableTools();
        
        // Araçlar için varsayılan durum atama
        const updatedTools = (data.tools || []).map(tool => {
          // Eğer status tanımlı değilse veya 'active' değilse ve 'status' yoksa
          if (!tool.status || tool.status === undefined) {
            return { ...tool, status: 'active' }; // Varsayılan olarak 'active' durumu ata
          }
          return tool;
        });
        
        setTools(updatedTools);
      } catch (err) {
        console.error('Araçlar yüklenirken hata oluştu:', err);
        setError('Araçlar yüklenemedi. Lütfen daha sonra tekrar deneyin.');
      } finally {
        setLoading(false);
      }
    };
    
    fetchTools();
  }, []);
  
  // Araç detaylarını yükle
  useEffect(() => {
    if (selectedTool) {
      const fetchToolDetails = async () => {
        try {
          const details = await ToolsAPI.getToolDetails(selectedTool.id);
          const status = await ToolsAPI.getToolStatus(selectedTool.id);
          
          setToolDetails({
            ...details,
            status: status
          });
        } catch (err) {
          console.error(`${selectedTool.name} detayları yüklenirken hata:`, err);
          setToolDetails(null);
        }
      };
      
      fetchToolDetails();
    }
  }, [selectedTool]);
  
  // External Tool ekle
  const handleAddExternalTool = async () => {
    try {
      setLoading(true);
      const result = await ToolsAPI.addExternalTool(newExternalTool);
      
      if (result.status === "success") {
        // Araç listesini güncelle
        const updatedTools = [...tools, result.metadata];
        setTools(updatedTools);
        
        // Formu temizle ve modalı kapat
        setNewExternalTool({
          name: '',
          baseUrl: '',
          authToken: '',
          version: '1.0.0',
          capabilities: []
        });
        setShowAddExternalToolModal(false);
        
        showNotification(`Dış kaynak aracı başarıyla eklendi: ${result.metadata.name}`);
      } else {
        showNotification(`Araç eklenemedi: ${result.message}`, 'danger');
      }
    } catch (err) {
      console.error('Dış kaynak aracı eklenirken hata:', err);
      showNotification(`Araç eklenirken hata oluştu: ${err.message}`, 'danger');
    } finally {
      setLoading(false);
    }
  };
  
  // Remote Tool ekle
  const handleAddRemoteTool = async () => {
    try {
      setLoading(true);
      const result = await ToolsAPI.addRemoteTool(newRemoteTool);
      
      if (result.status === "success") {
        // Araç listesini güncelle
        const updatedTools = [...tools, result.metadata];
        setTools(updatedTools);
        
        // Formu temizle ve modalı kapat
        setNewRemoteTool({
          name: '',
          remoteUrl: '',
          authInfo: {
            username: '',
            password: ''
          }
        });
        setShowAddRemoteToolModal(false);
        
        showNotification(`Uzak araç başarıyla eklendi: ${result.metadata.name}`);
      } else {
        showNotification(`Araç eklenemedi: ${result.message}`, 'danger');
      }
    } catch (err) {
      console.error('Uzak araç eklenirken hata:', err);
      showNotification(`Araç eklenirken hata oluştu: ${err.message}`, 'danger');
    } finally {
      setLoading(false);
    }
  };
  
  // Araç sil
  const handleDeleteTool = async () => {
    if (!deletingTool) return;
    
    try {
      setLoading(true);
      const result = await ToolsAPI.deleteTool(deletingTool.id);
      
      if (result.status === "success") {
        // Araç listesinden sil
        const updatedTools = tools.filter(tool => tool.id !== deletingTool.id);
        setTools(updatedTools);
        
        // Seçili aracı temizle
        if (selectedTool && selectedTool.id === deletingTool.id) {
          setSelectedTool(null);
          setToolDetails(null);
        }
        
        showNotification(`Araç başarıyla silindi: ${deletingTool.name}`);
      } else {
        showNotification(`Araç silinemedi: ${result.message}`, 'danger');
      }
    } catch (err) {
      console.error('Araç silinirken hata:', err);
      showNotification(`Araç silinirken hata oluştu: ${err.message}`, 'danger');
    } finally {
      setDeletingTool(null);
      setShowDeleteConfirmModal(false);
      setLoading(false);
    }
  };
  
  // Uzak araçları senkronize et
  const handleSyncRemoteTools = async () => {
    try {
      setLoading(true);
      const result = await ToolsAPI.syncRemoteTools(
        syncConfig.remoteUrl, 
        syncConfig.authInfo
      );
      
      if (result.status === "success") {
        // Araç listesini yeniden yükle
        const data = await ToolsAPI.getAvailableTools();
        setTools(data.tools || []);
        
        // Modalı kapat
        setShowSyncModal(false);
        
        showNotification(`${result.synced_tools.length} araç başarıyla senkronize edildi`);
      } else {
        showNotification(`Araçlar senkronize edilemedi: ${result.message}`, 'danger');
      }
    } catch (err) {
      console.error('Uzak araçlar senkronize edilirken hata:', err);
      showNotification(`Senkronizasyon hatası: ${err.message}`, 'danger');
    } finally {
      setLoading(false);
    }
  };
  
  // Araçları yenile
  const refreshTools = async () => {
    try {
      setLoading(true);
      const data = await ToolsAPI.getAvailableTools();
      setTools(data.tools || []);
      setError(null);
      showNotification('Araçlar başarıyla yenilendi');
    } catch (err) {
      console.error('Araçlar yüklenirken hata oluştu:', err);
      setError('Araçlar yüklenemedi. Lütfen daha sonra tekrar deneyin.');
    } finally {
      setLoading(false);
    }
  };
  
  // Capability ekleme/silme işlemleri
  const handleAddCapability = (e) => {
    e.preventDefault();
    if (!newCapability.trim()) return;
    
    setNewExternalTool({
      ...newExternalTool,
      capabilities: [...newExternalTool.capabilities, newCapability.trim()]
    });
    setNewCapability('');
  };
  
  const handleRemoveCapability = (capability) => {
    setNewExternalTool({
      ...newExternalTool,
      capabilities: newExternalTool.capabilities.filter(cap => cap !== capability)
    });
  };
  
  // Filtre uygula
  const filteredTools = tools.filter(tool => {
    if (showOnlyActive && tool.status !== 'active') return false;
    
    if (searchTerm) {
      const searchTermLower = searchTerm.toLowerCase();
      return (
        tool.name.toLowerCase().includes(searchTermLower) ||
        tool.description.toLowerCase().includes(searchTermLower) ||
        (tool.capabilities && tool.capabilities.some(cap => 
          typeof cap === 'string' && cap.toLowerCase().includes(searchTermLower))
        )
      );
    }
    
    return true;
  });
  
  // İkon döndürme
  const getToolIcon = (iconName) => {
    switch (iconName) {
      case 'Code': return <Code size={18} />;
      case 'FileText': return <FileText size={18} />;
      case 'Terminal': return <Terminal size={18} />;
      case 'Globe': return <Globe size={18} />;
      case 'Server': return <Server size={18} />;
      case 'Share2': return <Share2 size={18} />;
      case 'Users': return <Users size={18} />;
      case 'HardDrive': return <HardDrive size={18} />;
      case 'Database': return <Database size={18} />;
      case 'Cloud': return <Cloud size={18} />;
      case 'ExternalLink': return <ExternalLink size={18} />;
      default: return <Tool size={18} />;
    }
  };
  
  // Araç tipi simgesini al
  const getToolTypeIcon = (sourceType) => {
    switch (sourceType) {
      case 'LOCAL': return <Server size={16} className="text-primary" />;
      case 'EXTERNAL': return <ExternalLink size={16} className="text-success" />;
      case 'REMOTE': return <Cloud size={16} className="text-info" />;
      default: return <Tool size={16} />;
    }
  };
  
  // Araç tipi rengini al
  const getToolTypeColor = (sourceType) => {
    switch (sourceType) {
      case 'LOCAL': return 'primary';
      case 'EXTERNAL': return 'success';
      case 'REMOTE': return 'info';
      default: return 'secondary';
    }
  };
  
  // Araç için buton açıklaması
  const getToolActionName = (tool) => {
    // id özelliği tanımlı değilse veya null/undefined ise
    if (!tool || !tool.id) return 'Kullan';
    
    if (tool.id.includes('editor')) return 'Editöre Git';
    if (tool.id.includes('task_runner')) return 'Görev Çalıştır';
    if (tool.id.includes('file_manager')) return 'Dosyaları Yönet';
    if (tool.id.includes('social_media')) return 'İş Akışını Başlat';
    return 'Kullan';
  };
  
  // Araç komutu kopyala
  const handleToolClip = (tool) => {
    // Bu fonksiyon chat penceresine "/{toolId}" komutunu enjekte edecek
    console.log(`Araç komutu kopyalandı: /${tool.id}`);
    
    // Örnek: İletişim kanalıyla ana uygulamaya komut gönderimi
    if (window.parent && window.parent.postMessage) {
      window.parent.postMessage({ 
        type: 'TOOL_COMMAND', 
        command: `/${tool.id}` 
      }, '*');
    }
  };
  
  if (loading && tools.length === 0) {
    return (
      <div className="tools-loading">
        <div className="text-center p-4">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Yükleniyor...</span>
          </div>
          <p className="mt-2">Araçlar yükleniyor...</p>
        </div>
      </div>
    );
  }
  
  if (error && tools.length === 0) {
    return (
      <div className="tools-error">
        <div className="alert alert-danger m-3" role="alert">
          <p>{error}</p>
          <Button 
            variant="outline-danger" 
            size="sm" 
            onClick={refreshTools}
            className="mt-2"
          >
            <RefreshCw size={14} className="me-1" />
            Yeniden Dene
          </Button>
        </div>
      </div>
    );
  }
  
  return (
    <div className="tools-panel h-100">
      {/* Bildirim */}
      {notification && (
        <Alert 
          variant={notification.type} 
          className="tools-notification"
          onClose={() => setNotification(null)}
          dismissible
        >
          {notification.message}
        </Alert>
      )}
      
      {/* Başlık ve eylemler */}
      <div className="tools-header d-flex align-items-center justify-content-between mb-3">
        <h5 className="mb-0">Araçlar</h5>
        <div className="tools-actions d-flex flex-wrap">
          <Button 
            variant="outline-primary" 
            size="sm" 
            className="me-2 mb-1"
            onClick={() => setShowAddExternalToolModal(true)}
            title="Dış Kaynak Aracı Ekle"
          >
            <Plus size={16} className="me-1" />
            Dış Kaynak
          </Button>
          <Button 
            variant="outline-info" 
            size="sm"
            className="me-2 mb-1" 
            onClick={() => setShowAddRemoteToolModal(true)}
            title="Uzak MCP Aracı Ekle"
          >
            <Cloud size={16} className="me-1" />
            Uzak MCP
          </Button>
          <Button 
            variant="outline-secondary" 
            size="sm"
            className="mb-1"
            onClick={() => setShowSyncModal(true)}
            title="Uzak Araçları Senkronize Et"
          >
            <RefreshCw size={16} />
          </Button>
        </div>
      </div>
      
      {/* Arama ve filtreler */}
      <div className="tools-search mb-3">
        <div className="input-group">
          <span className="input-group-text">
            <Search size={16} />
          </span>
          <Form.Control
            type="text"
            placeholder="Araçlarda ara..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          {searchTerm && (
            <Button 
              variant="outline-secondary" 
              onClick={() => setSearchTerm('')}
            >
              &times;
            </Button>
          )}
        </div>
        
        <Form.Check
          type="switch"
          id="active-tools-switch"
          label="Sadece aktif araçlar"
          className="mt-2"
          checked={showOnlyActive}
          onChange={(e) => setShowOnlyActive(e.target.checked)}
        />
      </div>
      
      {/* Araç listesi */}
      {filteredTools.length === 0 ? (
        <div className="text-center p-4 text-muted">
          <p>Eşleşen araç bulunamadı.</p>
        </div>
      ) : (
        <div className="tools-list mb-4">
          {filteredTools.map((tool) => (
            <div 
              key={tool.id}
              className={`tool-card ${selectedTool?.id === tool.id ? 'selected' : ''}`}
              onClick={() => setSelectedTool(selectedTool?.id === tool.id ? null : tool)}
            >
              <div className="tool-card-header">
                <div className="tool-icon">{getToolIcon(tool.icon)}</div>
                <div className="tool-title">
                  {tool.name}
                  <Badge 
                    bg={getToolTypeColor(tool.source_type)} 
                    className="ms-2 tool-type-badge"
                    title={tool.source_type}
                  >
                    {getToolTypeIcon(tool.source_type)}
                  </Badge>
                </div>
                <Badge 
                  bg={tool.status && typeof tool.status === 'string' && tool.status.toLowerCase() === 'active' 
                    ? 'success' 
                    : 'warning'}
                  className="ms-auto tool-status"
                >
                  {tool.status && typeof tool.status === 'string' && tool.status.toLowerCase() === 'active' 
                    ? 'Aktif' 
                    : 'Bakımda'}
                </Badge>
              </div>
              
              <div className="tool-description">{tool.description}</div>
              
              <div className="tool-capabilities mt-2">
                {tool.capabilities && tool.capabilities.map((cap, index) => (
                  <Badge 
                    key={index} 
                    bg="light" 
                    text="dark" 
                    className="capability-badge me-1"
                  >
                    {cap}
                  </Badge>
                ))}
              </div>
              
              <div className="tool-actions mt-3">
                <Button 
                  variant="outline-primary" 
                  size="sm" 
                  className="me-2"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleToolClip(tool);
                  }}
                >
                  /{tool.id}
                </Button>
                
                <Button 
                  variant="primary" 
                  size="sm"
                  className="me-2"
                  disabled={tool.status !== 'active'}
                >
                  {getToolActionName(tool)}
                </Button>
                
                {/* Silme butonu */}
                {tool.source_type !== 'LOCAL' && (
                  <Button 
                    variant="outline-danger" 
                    size="sm"
                    title="Aracı Sil"
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeletingTool(tool);
                      setShowDeleteConfirmModal(true);
                    }}
                  >
                    <Trash2 size={16} />
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
      
      {/* Seçili araç detayları */}
      {selectedTool && toolDetails && (
        <div className="tool-details">
          <h5 className="mb-3">{selectedTool.name} Detayları</h5>
          
          <Accordion defaultActiveKey="0">
            <Accordion.Item eventKey="0">
              <Accordion.Header>Genel Bilgiler</Accordion.Header>
              <Accordion.Body>
                <ListGroup variant="flush">
                  <ListGroup.Item className="d-flex justify-content-between align-items-center">
                    <span>ID</span>
                    <span className="text-muted">{selectedTool.id}</span>
                  </ListGroup.Item>
                  <ListGroup.Item className="d-flex justify-content-between align-items-center">
                    <span>Tür</span>
                    <Badge bg={getToolTypeColor(selectedTool.source_type)}>
                      {selectedTool.source_type}
                    </Badge>
                  </ListGroup.Item>
                  <ListGroup.Item className="d-flex justify-content-between align-items-center">
                    <span>Versiyon</span>
                    <span>{selectedTool.version || '1.0.0'}</span>
                  </ListGroup.Item>
                  <ListGroup.Item className="d-flex justify-content-between align-items-center">
                    <span>Durum</span>
                    <Badge bg={toolDetails.status?.status === 'healthy' ? 'success' : 'warning'}>
                      {toolDetails.status?.status === 'healthy' ? 'Sağlıklı' : 'Sorun var'}
                    </Badge>
                  </ListGroup.Item>
                  <ListGroup.Item className="d-flex justify-content-between align-items-center">
                    <span>Durum mesajı</span>
                    <span className="text-muted">{toolDetails.status?.message || '-'}</span>
                  </ListGroup.Item>
                </ListGroup>
              </Accordion.Body>
            </Accordion.Item>
            
            <Accordion.Item eventKey="1">
              <Accordion.Header>Aksiyonlar ve Yetenekler</Accordion.Header>
              <Accordion.Body>
                <div className="mb-3">
                  <h6>Yetenekler</h6>
                  <div>
                    {selectedTool.capabilities && selectedTool.capabilities.length > 0 ? (
                      selectedTool.capabilities.map((cap, index) => (
                        <Badge 
                          key={index} 
                          bg="primary" 
                          className="me-1 mb-1"
                        >
                          {cap}
                        </Badge>
                      ))
                    ) : (
                      <p className="text-muted">Tanımlı yetenek yok</p>
                    )}
                  </div>
                </div>
                
                <div>
                  <h6>Aksiyonlar</h6>
                  <ListGroup variant="flush">
                    {toolDetails.details?.actions ? (
                      Object.keys(toolDetails.details.actions).map((action, index) => (
                        <ListGroup.Item key={index}>
                          <code>/{selectedTool.id} {action}</code>
                          <div className="text-muted small mt-1">
                            {toolDetails.details.actions[action].description || 'Açıklama yok'}
                          </div>
                        </ListGroup.Item>
                      ))
                    ) : (
                      <ListGroup.Item className="text-muted">
                        Tanımlı aksiyon bulunamadı
                      </ListGroup.Item>
                    )}
                  </ListGroup>
                </div>
              </Accordion.Body>
            </Accordion.Item>
          </Accordion>
        </div>
      )}
      
      {/* Hızlı başlangıç */}
      <div className="quick-start mt-4">
        <h6>Hızlı Başlangıç</h6>
        <p className="text-muted small">
          Metis araçlarını chat penceresinde <code>/araç_adı</code> yazarak kullanabilirsiniz.
          Örneğin: <code>/file_manager list /home</code>
        </p>
        
        <div className="quick-commands">
          <Button variant="outline-secondary" size="sm" className="me-2 mb-2">
            /help
          </Button>
          <Button variant="outline-secondary" size="sm" className="me-2 mb-2">
            /file_manager
          </Button>
          <Button variant="outline-secondary" size="sm" className="me-2 mb-2">
            /task_runner
          </Button>
          <Button variant="outline-secondary" size="sm" className="mb-2">
            /system_info
          </Button>
        </div>
      </div>
      
      {/* Dış Kaynak Aracı Ekleme Modalı */}
      <Modal
        show={showAddExternalToolModal}
        onHide={() => setShowAddExternalToolModal(false)}
        backdrop="static"
        size="lg"
      >
        <Modal.Header closeButton>
          <Modal.Title>Dış Kaynak Aracı Ekle</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form>
            <Form.Group className="mb-3">
              <Form.Label>Araç Adı</Form.Label>
              <Form.Control
                type="text"
                placeholder="Örn: GitHub API"
                value={newExternalTool.name}
                onChange={(e) => setNewExternalTool({...newExternalTool, name: e.target.value})}
                required
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Temel URL</Form.Label>
              <Form.Control
                type="text"
                placeholder="Örn: https://api.github.com"
                value={newExternalTool.baseUrl}
                onChange={(e) => setNewExternalTool({...newExternalTool, baseUrl: e.target.value})}
                required
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>API/Auth Token</Form.Label>
              <Form.Control
                type="password"
                placeholder="Kimlik doğrulama için token"
                value={newExternalTool.authToken}
                onChange={(e) => setNewExternalTool({...newExternalTool, authToken: e.target.value})}
              />
              <Form.Text className="text-muted">
                Kimlik doğrulama gerektirmeyen API'ler için boş bırakılabilir.
              </Form.Text>
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Versiyon</Form.Label>
              <Form.Control
                type="text"
                placeholder="1.0.0"
                value={newExternalTool.version}
                onChange={(e) => setNewExternalTool({...newExternalTool, version: e.target.value})}
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Yetenekler</Form.Label>
              <div className="capabilities-section">
                <div className="mb-2">
                  {newExternalTool.capabilities.map((cap, index) => (
                    <Badge 
                      key={index} 
                      bg="primary" 
                      className="me-1 mb-1 capability-badge"
                    >
                      {cap}
                      <X 
                        size={14} 
                        className="ms-1 remove-cap" 
                        onClick={() => handleRemoveCapability(cap)}
                      />
                    </Badge>
                  ))}
                </div>
                
                <InputGroup>
                  <FormControl
                    placeholder="Yeni yetenek ekle"
                    value={newCapability}
                    onChange={(e) => setNewCapability(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleAddCapability(e)}
                  />
                  <Button 
                    variant="outline-secondary" 
                    onClick={handleAddCapability}
                  >
                    <Plus size={16} />
                  </Button>
                </InputGroup>
                <Form.Text className="text-muted">
                  Enter tuşuna basarak ekleyebilirsiniz.
                </Form.Text>
              </div>
            </Form.Group>
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowAddExternalToolModal(false)}>
            İptal
          </Button>
          <Button variant="primary" onClick={handleAddExternalTool} disabled={!newExternalTool.name || !newExternalTool.baseUrl}>
            Aracı Ekle
          </Button>
        </Modal.Footer>
      </Modal>
      
      {/* Uzak MCP Aracı Ekleme Modalı */}
      <Modal
        show={showAddRemoteToolModal}
        onHide={() => setShowAddRemoteToolModal(false)}
        backdrop="static"
      >
        <Modal.Header closeButton>
          <Modal.Title>Uzak MCP Aracı Ekle</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form>
            <Form.Group className="mb-3">
              <Form.Label>Araç Adı</Form.Label>
              <Form.Control
                type="text"
                placeholder="Örn: Uzak Dosya Yöneticisi"
                value={newRemoteTool.name}
                onChange={(e) => setNewRemoteTool({...newRemoteTool, name: e.target.value})}
                required
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Uzak MCP URL</Form.Label>
              <Form.Control
                type="text"
                placeholder="Örn: https://uzak-mcp-sunucu.com"
                value={newRemoteTool.remoteUrl}
                onChange={(e) => setNewRemoteTool({...newRemoteTool, remoteUrl: e.target.value})}
                required
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Kimlik Bilgileri</Form.Label>
              <Form.Control
                type="text"
                placeholder="Kullanıcı adı"
                className="mb-2"
                value={newRemoteTool.authInfo.username}
                onChange={(e) => setNewRemoteTool({
                  ...newRemoteTool, 
                  authInfo: {...newRemoteTool.authInfo, username: e.target.value}
                })}
              />
              <Form.Control
                type="password"
                placeholder="Şifre"
                value={newRemoteTool.authInfo.password}
                onChange={(e) => setNewRemoteTool({
                  ...newRemoteTool, 
                  authInfo: {...newRemoteTool.authInfo, password: e.target.value}
                })}
              />
              <Form.Text className="text-muted">
                Kimlik doğrulama gerektirmeyen sunucular için boş bırakılabilir.
              </Form.Text>
            </Form.Group>
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowAddRemoteToolModal(false)}>
            İptal
          </Button>
          <Button variant="primary" onClick={handleAddRemoteTool} disabled={!newRemoteTool.name || !newRemoteTool.remoteUrl}>
            Aracı Ekle
          </Button>
        </Modal.Footer>
      </Modal>
      
      {/* Araç Silme Onay Modalı */}
      <Modal
        show={showDeleteConfirmModal}
        onHide={() => setShowDeleteConfirmModal(false)}
        backdrop="static"
      >
        <Modal.Header closeButton>
          <Modal.Title>Aracı Sil</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <AlertCircle className="text-danger mb-3" size={28} />
          <p>
            <strong>{deletingTool?.name}</strong> aracını silmek istediğinizden emin misiniz?
          </p>
          <p className="text-muted">
            Bu işlem geri alınamaz ve aracın tüm yapılandırması kaybolacaktır.
          </p>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowDeleteConfirmModal(false)}>
            İptal
          </Button>
          <Button variant="danger" onClick={handleDeleteTool}>
            Aracı Sil
          </Button>
        </Modal.Footer>
      </Modal>
      
      {/* Uzak Araçları Senkronize Etme Modalı */}
      <Modal
        show={showSyncModal}
        onHide={() => setShowSyncModal(false)}
        backdrop="static"
      >
        <Modal.Header closeButton>
          <Modal.Title>Uzak Araçları Senkronize Et</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form>
            <Form.Group className="mb-3">
              <Form.Label>Uzak MCP URL</Form.Label>
              <Form.Control
                type="text"
                placeholder="Örn: https://uzak-mcp-sunucu.com"
                value={syncConfig.remoteUrl}
                onChange={(e) => setSyncConfig({...syncConfig, remoteUrl: e.target.value})}
                required
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Kimlik Bilgileri</Form.Label>
              <Form.Control
                type="text"
                placeholder="Kullanıcı adı"
                className="mb-2"
                value={syncConfig.authInfo.username}
                onChange={(e) => setSyncConfig({
                  ...syncConfig, 
                  authInfo: {...syncConfig.authInfo, username: e.target.value}
                })}
              />
              <Form.Control
                type="password"
                placeholder="Şifre"
                value={syncConfig.authInfo.password}
                onChange={(e) => setSyncConfig({
                  ...syncConfig, 
                  authInfo: {...syncConfig.authInfo, password: e.target.value}
                })}
              />
              <Form.Text className="text-muted">
                Kimlik doğrulama gerektirmeyen sunucular için boş bırakılabilir.
              </Form.Text>
            </Form.Group>
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowSyncModal(false)}>
            İptal
          </Button>
          <Button variant="primary" onClick={handleSyncRemoteTools} disabled={!syncConfig.remoteUrl}>
            Senkronize Et
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
};

export default ToolsPanel;