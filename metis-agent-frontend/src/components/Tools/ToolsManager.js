// src/components/Tools/ToolsManager.js
import React, { useState, useEffect } from 'react';
import { Card, Button, Form, InputGroup, Badge, Row, Col, Modal, Alert, Spinner } from 'react-bootstrap';
import { Tool, Plus, Database, Wrench, Trash, Edit, Search, Settings, Server } from 'lucide-react';
import ToolsAPI from '../../services/ToolsAPI';
import './ToolsManager.css';

const ToolsManager = () => {
  const [tools, setTools] = useState([]);
  const [categories, setCategories] = useState([]);
  const [capabilities, setCapabilities] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedCapability, setSelectedCapability] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [showExternalToolModal, setShowExternalToolModal] = useState(false);
  const [showRemoteToolModal, setShowRemoteToolModal] = useState(false);
  const [error, setError] = useState(null);
  
  // Form states
  const [externalToolForm, setExternalToolForm] = useState({
    name: '',
    config: '',
    capabilities: []
  });
  
  const [remoteToolForm, setRemoteToolForm] = useState({
    name: '',
    remoteUrl: '',
    authInfo: ''
  });
  
  // Load tools, categories and capabilities
  useEffect(() => {
    loadTools();
    loadCategories();
    loadCapabilities();
  }, []);
  
  const loadTools = async () => {
    setIsLoading(true);
    try {
      let url = `/api/registry/tools`;
      
      // Add filters if provided
      if (selectedCategory) url += `?category=${selectedCategory}`;
      if (selectedCapability) url += `${selectedCategory ? '&' : '?'}capability=${selectedCapability}`;
      
      const response = await ToolsAPI.getTools(url);
      setTools(response.data.tools);
      setError(null);
    } catch (err) {
      setError('Araçlar yüklenirken hata oluştu');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };
  
  const loadCategories = async () => {
    try {
      const response = await ToolsAPI.getCategories();
      setCategories(response.data.categories);
    } catch (err) {
      console.error('Kategoriler yüklenirken hata:', err);
    }
  };
  
  const loadCapabilities = async () => {
    try {
      const response = await ToolsAPI.getCapabilities();
      setCapabilities(response.data.capabilities);
    } catch (err) {
      console.error('Yetenekler yüklenirken hata:', err);
    }
  };
  
  const handleAddExternalTool = async () => {
    setIsLoading(true);
    try {
      // Parse JSON config
      const configObj = JSON.parse(externalToolForm.config);
      
      const response = await ToolsAPI.addExternalTool({
        name: externalToolForm.name,
        config: configObj,
        capabilities: externalToolForm.capabilities
      });
      
      // Reset form and close modal
      setExternalToolForm({ name: '', config: '', capabilities: [] });
      setShowExternalToolModal(false);
      
      // Reload tools
      loadTools();
      
    } catch (err) {
      setError('Dış kaynak aracı eklenirken hata oluştu: ' + (err.message || ''));
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleAddRemoteTool = async () => {
    setIsLoading(true);
    try {
      // Parse auth info if provided
      let authInfoObj = {};
      if (remoteToolForm.authInfo.trim()) {
        authInfoObj = JSON.parse(remoteToolForm.authInfo);
      }
      
      const response = await ToolsAPI.addRemoteTool({
        name: remoteToolForm.name,
        remote_url: remoteToolForm.remoteUrl,
        auth_info: authInfoObj
      });
      
      // Reset form and close modal
      setRemoteToolForm({ name: '', remoteUrl: '', authInfo: '' });
      setShowRemoteToolModal(false);
      
      // Reload tools
      loadTools();
      
    } catch (err) {
      setError('Uzak araç eklenirken hata oluştu: ' + (err.message || ''));
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleRemoveTool = async (toolId) => {
    if (!window.confirm('Bu aracı kaldırmak istediğinizden emin misiniz?')) return;
    
    setIsLoading(true);
    try {
      await ToolsAPI.removeTool(toolId);
      loadTools();
    } catch (err) {
      setError('Araç kaldırılırken hata oluştu');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleSearch = () => {
    loadTools();
  };
  
  return (
    <div className="tools-manager">
      <div className="panel-section-title mb-3">
        <Tool size={18} className="me-2" />
        Araç Yönetimi
      </div>
      
      {error && <Alert variant="danger">{error}</Alert>}
      
      <div className="tools-header mb-3">
        <Row>
          <Col>
            <InputGroup>
              <Form.Control
                placeholder="Araçlarda ara..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              />
              <Button variant="outline-secondary" onClick={handleSearch}>
                <Search size={16} />
              </Button>
              <Button variant="primary" onClick={() => setShowAddModal(true)}>
                <Plus size={16} className="me-1" />
                Araç Ekle
              </Button>
            </InputGroup>
          </Col>
        </Row>
      </div>
      
      {/* Filtreler */}
      <div className="filters-section mb-3">
        <Row>
          <Col md={6}>
            <Form.Group>
              <Form.Label>Kategori</Form.Label>
              <Form.Select 
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
              >
                <option value="">Tüm Kategoriler</option>
                {categories.map(category => (
                  <option key={category} value={category}>{category}</option>
                ))}
              </Form.Select>
            </Form.Group>
          </Col>
          <Col md={6}>
            <Form.Group>
              <Form.Label>Yetenek</Form.Label>
              <Form.Select 
                value={selectedCapability}
                onChange={(e) => setSelectedCapability(e.target.value)}
              >
                <option value="">Tüm Yetenekler</option>
                {capabilities.map(capability => (
                  <option key={capability} value={capability}>{capability}</option>
                ))}
              </Form.Select>
            </Form.Group>
          </Col>
        </Row>
      </div>
      
      {/* Araçlar Listesi */}
      {isLoading ? (
        <div className="text-center py-4">
          <Spinner animation="border" />
        </div>
      ) : (
        <div className="tools-list">
          {tools.length === 0 ? (
            <div className="text-center py-4 text-muted">
              <p>Araç bulunamadı. Yeni bir araç ekleyin veya filtrelerinizi değiştirin.</p>
              <Button 
                variant="outline-primary"
                onClick={() => setShowAddModal(true)}
              >
                <Plus size={16} className="me-1" />
                Yeni Araç Ekle
              </Button>
            </div>
          ) : (
            <Row xs={1} md={2} lg={3} className="g-4">
              {tools.map(tool => (
                <Col key={tool.id || tool.tool_id}>
                  <Card className="tool-card h-100">
                    <Card.Body>
                      <div className="d-flex justify-content-between align-items-start mb-2">
                        <div className="tool-icon">
                          {tool.source_type === 'LOCAL' && <Wrench size={20} />}
                          {tool.source_type === 'EXTERNAL' && <Database size={20} />}
                          {tool.source_type === 'REMOTE' && <Server size={20} />}
                        </div>
                        <div>
                          <Badge bg="secondary">{tool.source_type}</Badge>
                        </div>
                      </div>
                      
                      <Card.Title>{tool.name}</Card.Title>
                      <Card.Text className="text-muted small">{tool.description}</Card.Text>
                      
                      {tool.capabilities && tool.capabilities.length > 0 && (
                        <div className="tool-capabilities mb-2">
                          {tool.capabilities.map(cap => (
                            <Badge key={cap} bg="info" className="me-1">{cap}</Badge>
                          ))}
                        </div>
                      )}
                      
                      <div className="d-flex justify-content-between align-items-center mt-auto">
                        <Badge bg="dark">{tool.category}</Badge>
                        <div className="tool-actions">
                          <Button 
                            variant="outline-primary" 
                            size="sm" 
                            className="me-1"
                            onClick={() => window.location.href = `/tools/${tool.id || tool.tool_id}`}
                          >
                            <Settings size={14} />
                          </Button>
                          {(tool.source_type === 'EXTERNAL' || tool.source_type === 'REMOTE') && (
                            <Button 
                              variant="outline-danger" 
                              size="sm"
                              onClick={() => handleRemoveTool(tool.id || tool.tool_id)}
                            >
                              <Trash size={14} />
                            </Button>
                          )}
                        </div>
                      </div>
                    </Card.Body>
                  </Card>
                </Col>
              ))}
            </Row>
          )}
        </div>
      )}
      
      {/* Araç Ekleme Modal */}
      <Modal
        show={showAddModal}
        onHide={() => setShowAddModal(false)}
        centered
      >
        <Modal.Header closeButton>
          <Modal.Title>Araç Ekle</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <div className="d-grid gap-2">
            <Button 
              variant="outline-primary" 
              size="lg" 
              onClick={() => {
                setShowAddModal(false);
                setShowExternalToolModal(true);
              }}
            >
              <Database size={20} className="me-2" />
              Dış Kaynak Aracı Ekle
            </Button>
            <Button 
              variant="outline-primary" 
              size="lg"
              onClick={() => {
                setShowAddModal(false);
                setShowRemoteToolModal(true);
              }}
            >
              <Server size={20} className="me-2" />
              Uzak MCP Aracı Ekle
            </Button>
          </div>
        </Modal.Body>
      </Modal>
      
      {/* Dış Kaynak Aracı Ekleme Modal */}
      <Modal
        show={showExternalToolModal}
        onHide={() => setShowExternalToolModal(false)}
        centered
        size="lg"
      >
        <Modal.Header closeButton>
          <Modal.Title>
            <Database size={20} className="me-2" />
            Dış Kaynak Aracı Ekle
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form>
            <Form.Group className="mb-3">
              <Form.Label>Araç Adı</Form.Label>
              <Form.Control
                type="text"
                value={externalToolForm.name}
                onChange={(e) => setExternalToolForm({...externalToolForm, name: e.target.value})}
                required
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Yapılandırma (JSON)</Form.Label>
              <Form.Control
                as="textarea"
                rows={5}
                value={externalToolForm.config}
                onChange={(e) => setExternalToolForm({...externalToolForm, config: e.target.value})}
                placeholder='{"version": "1.0.0", "endpoint": "https://api.example.com", ...}'
                required
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Yetenekler</Form.Label>
              <div className="d-flex flex-wrap gap-2 mb-2">
                {capabilities.map(capability => (
                  <Badge 
                    key={capability}
                    bg={externalToolForm.capabilities.includes(capability) ? "primary" : "secondary"}
                    style={{ cursor: 'pointer' }}
                    onClick={() => {
                      if (externalToolForm.capabilities.includes(capability)) {
                        setExternalToolForm({
                          ...externalToolForm,
                          capabilities: externalToolForm.capabilities.filter(c => c !== capability)
                        });
                      } else {
                        setExternalToolForm({
                          ...externalToolForm,
                          capabilities: [...externalToolForm.capabilities, capability]
                        });
                      }
                    }}
                  >
                    {capability}
                  </Badge>
                ))}
              </div>
            </Form.Group>
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowExternalToolModal(false)}>
            İptal
          </Button>
          <Button 
            variant="primary" 
            onClick={handleAddExternalTool}
            disabled={isLoading || !externalToolForm.name || !externalToolForm.config}
          >
            {isLoading ? (
              <Spinner animation="border" size="sm" />
            ) : (
              <>
                <Plus size={16} className="me-1" />
                Ekle
              </>
            )}
          </Button>
        </Modal.Footer>
      </Modal>
      
      {/* Uzak MCP Aracı Ekleme Modal */}
      <Modal
        show={showRemoteToolModal}
        onHide={() => setShowRemoteToolModal(false)}
        centered
      >
        <Modal.Header closeButton>
          <Modal.Title>
            <Server size={20} className="me-2" />
            Uzak MCP Aracı Ekle
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form>
            <Form.Group className="mb-3">
              <Form.Label>Araç Adı</Form.Label>
              <Form.Control
                type="text"
                value={remoteToolForm.name}
                onChange={(e) => setRemoteToolForm({...remoteToolForm, name: e.target.value})}
                required
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Uzak URL</Form.Label>
              <Form.Control
                type="url"
                value={remoteToolForm.remoteUrl}
                onChange={(e) => setRemoteToolForm({...remoteToolForm, remoteUrl: e.target.value})}
                placeholder="https://example.com/api/mcp"
                required
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Kimlik Doğrulama Bilgisi (JSON)</Form.Label>
              <Form.Control
                as="textarea"
                rows={3}
                value={remoteToolForm.authInfo}
                onChange={(e) => setRemoteToolForm({...remoteToolForm, authInfo: e.target.value})}
                placeholder='{"api_key": "your-api-key"}'
              />
            </Form.Group>
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowRemoteToolModal(false)}>
            İptal
          </Button>
          <Button 
            variant="primary" 
            onClick={handleAddRemoteTool}
            disabled={isLoading || !remoteToolForm.name || !remoteToolForm.remoteUrl}
          >
            {isLoading ? (
              <Spinner animation="border" size="sm" />
            ) : (
              <>
                <Plus size={16} className="me-1" />
                Ekle
              </>
            )}
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
};

export default ToolsManager;