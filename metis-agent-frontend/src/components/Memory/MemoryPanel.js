// src/components/Memory/MemoryPanel.js
import React, { useState, useEffect } from 'react';
import { Card, Button, Form, InputGroup, Badge, Alert, Spinner, Row, Col } from 'react-bootstrap';
import { Search, Plus, Trash, Edit, Tag, Clock, Save, X, Filter } from 'lucide-react';
import MemoryAPI from '../../services/MemoryAPI';
import './MemoryPanel.css';

const MemoryPanel = () => {
  const [memories, setMemories] = useState([]);
  const [categories, setCategories] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedTags, setSelectedTags] = useState([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingMemory, setEditingMemory] = useState(null);
  const [error, setError] = useState(null);
  const [formData, setFormData] = useState({
    content: '',
    category: 'general',
    tags: []
  });
  const [tagInput, setTagInput] = useState('');

  // Bellekleri yükle
  useEffect(() => {
    loadMemories();
  }, []);

  const loadMemories = async () => {
    setIsLoading(true);
    try {
      const response = await MemoryAPI.retrieveMemories(
        searchQuery,
        selectedCategory,
        selectedTags
      );
      setMemories(response.data.memories);
      
      // Kategorileri topla
      const uniqueCategories = [...new Set(response.data.memories.map(m => m.category))];
      setCategories(['general', ...uniqueCategories.filter(c => c !== 'general')]);
      
      setError(null);
    } catch (err) {
      setError('Bellek kayıtları yüklenirken hata oluştu');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = () => {
    loadMemories();
  };

  const handleAddTag = () => {
    if (tagInput.trim() && !formData.tags.includes(tagInput.trim())) {
      setFormData({
        ...formData,
        tags: [...formData.tags, tagInput.trim()]
      });
      setTagInput('');
    }
  };

  const handleRemoveTag = (tag) => {
    setFormData({
      ...formData,
      tags: formData.tags.filter(t => t !== tag)
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    
    try {
      if (editingMemory) {
        await MemoryAPI.updateMemory(
          editingMemory.id,
          formData.content,
          formData.category,
          formData.tags
        );
        setEditingMemory(null);
      } else {
        await MemoryAPI.storeMemory(
          formData.content,
          formData.category,
          formData.tags
        );
      }
      
      // Reset form
      setFormData({
        content: '',
        category: 'general',
        tags: []
      });
      setShowAddForm(false);
      
      // Reload memories
      loadMemories();
    } catch (err) {
      setError('Bellek kaydedilirken hata oluştu');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleEdit = (memory) => {
    setEditingMemory(memory);
    setFormData({
      content: memory.content,
      category: memory.category,
      tags: memory.tags
    });
    setShowAddForm(true);
  };

  const handleDelete = async (memoryId) => {
    if (!window.confirm('Bu bellek kaydını silmek istediğinizden emin misiniz?')) return;
    
    setIsLoading(true);
    try {
      await MemoryAPI.deleteMemory(memoryId);
      loadMemories();
    } catch (err) {
      setError('Bellek silinirken hata oluştu');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCategoryFilter = (category) => {
    setSelectedCategory(category === selectedCategory ? '' : category);
  };

  const handleTagFilter = (tag) => {
    setSelectedTags(
      selectedTags.includes(tag)
        ? selectedTags.filter(t => t !== tag)
        : [...selectedTags, tag]
    );
  };

  return (
    <div className="memory-panel">
      <div className="panel-section-title mb-3">
        <Clock size={18} className="me-2" />
        Bellek Yönetimi
      </div>
      
      {error && <Alert variant="danger">{error}</Alert>}
      
      <div className="memory-panel-header mb-3">
        <InputGroup>
          <Form.Control
            placeholder="Bellekte ara..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          />
          <Button variant="outline-secondary" onClick={handleSearch}>
            <Search size={16} />
          </Button>
          <Button 
            variant="primary" 
            onClick={() => {
              setShowAddForm(true);
              setEditingMemory(null);
              setFormData({ content: '', category: 'general', tags: [] });
            }}
          >
            <Plus size={16} className="me-1" />
            <span>Yeni</span>
          </Button>
        </InputGroup>
      </div>
      
      {/* Kategori filtreleri */}
      {categories.length > 0 && (
        <div className="category-filters mb-3">
          <Form.Label className="mb-2 d-flex align-items-center">
            <Filter size={14} className="me-1" /> Kategoriler
          </Form.Label>
          <div className="d-flex flex-wrap gap-2">
            {categories.map(category => (
              <Badge 
                key={category}
                bg={selectedCategory === category ? "primary" : "secondary"}
                className="category-badge"
                style={{ cursor: 'pointer' }}
                onClick={() => handleCategoryFilter(category)}
              >
                {category}
              </Badge>
            ))}
          </div>
        </div>
      )}
      
      {/* Bellek Ekleme Formu */}
      {showAddForm && (
        <Card className="mb-3">
          <Card.Body>
            <Card.Title className="d-flex align-items-center mb-3">
              {editingMemory ? 'Bellek Düzenle' : 'Yeni Bellek Oluştur'}
            </Card.Title>
            
            <Form onSubmit={handleSubmit}>
              <Form.Group className="mb-3">
                <Form.Label>İçerik</Form.Label>
                <Form.Control
                  as="textarea"
                  rows={3}
                  value={formData.content}
                  onChange={(e) => setFormData({...formData, content: e.target.value})}
                  required
                />
              </Form.Group>
              
              <Row>
                <Col md={6}>
                  <Form.Group className="mb-3">
                    <Form.Label>Kategori</Form.Label>
                    <Form.Control
                      type="text"
                      placeholder="general"
                      value={formData.category}
                      onChange={(e) => setFormData({...formData, category: e.target.value})}
                    />
                  </Form.Group>
                </Col>
                <Col md={6}>
                  <Form.Group className="mb-3">
                    <Form.Label>Etiketler</Form.Label>
                    <InputGroup>
                      <Form.Control
                        type="text"
                        placeholder="Etiket ekle"
                        value={tagInput}
                        onChange={(e) => setTagInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddTag())}
                      />
                      <Button variant="outline-secondary" onClick={handleAddTag}>
                        <Plus size={16} />
                      </Button>
                    </InputGroup>
                  </Form.Group>
                </Col>
              </Row>
              
              {/* Etiket listesi */}
              {formData.tags.length > 0 && (
                <div className="mt-2 mb-3 d-flex flex-wrap gap-2">
                  {formData.tags.map(tag => (
                    <Badge key={tag} bg="info" className="p-2">
                      {tag}
                      <X 
                        size={14} 
                        className="ms-1" 
                        onClick={() => handleRemoveTag(tag)}
                        style={{ cursor: 'pointer' }}
                      />
                    </Badge>
                  ))}
                </div>
              )}
              
              <div className="d-flex justify-content-end gap-2">
                <Button 
                  variant="outline-secondary" 
                  onClick={() => setShowAddForm(false)}
                >
                  İptal
                </Button>
                <Button 
                  type="submit" 
                  variant="primary"
                  disabled={isLoading || !formData.content.trim()}
                >
                  {isLoading ? (
                    <Spinner animation="border" size="sm" />
                  ) : (
                    <>
                      <Save size={16} className="me-1" />
                      {editingMemory ? 'Güncelle' : 'Kaydet'}
                    </>
                  )}
                </Button>
              </div>
            </Form>
          </Card.Body>
        </Card>
      )}
      
      {/* Bellek Listesi */}
      {isLoading && !showAddForm ? (
        <div className="text-center py-4">
          <Spinner animation="border" />
        </div>
      ) : (
        <div className="memories-list">
          {memories.length === 0 ? (
            <div className="text-center py-4 text-muted">
              <p>Bellek kaydı bulunamadı.</p>
              <Button 
                variant="outline-primary" 
                size="sm"
                onClick={() => {
                  setShowAddForm(true);
                  setEditingMemory(null);
                }}
              >
                <Plus size={16} className="me-1" />
                Yeni Bellek Oluştur
              </Button>
            </div>
          ) : (
            memories.map(memory => (
              <Card key={memory.id} className="memory-card mb-3">
                <Card.Body>
                  <div className="d-flex justify-content-between">
                    <Badge bg="secondary" className="mb-2">{memory.category}</Badge>
                    <div className="memory-actions">
                      <Button 
                        variant="outline-primary" 
                        size="sm" 
                        className="me-1"
                        onClick={() => handleEdit(memory)}
                      >
                        <Edit size={14} />
                      </Button>
                      <Button 
                        variant="outline-danger" 
                        size="sm"
                        onClick={() => handleDelete(memory.id)}
                      >
                        <Trash size={14} />
                      </Button>
                    </div>
                  </div>
                  
                  <Card.Text>{memory.content}</Card.Text>
                  
                  {memory.tags.length > 0 && (
                    <div className="memory-tags mt-2">
                      {memory.tags.map(tag => (
                        <Badge 
                          key={tag} 
                          bg="info" 
                          className="me-1"
                          style={{ cursor: 'pointer' }}
                          onClick={() => handleTagFilter(tag)}
                        >
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  )}
                  
                  <div className="text-muted mt-2 small">
                    {new Date(memory.timestamp).toLocaleString()}
                  </div>
                </Card.Body>
              </Card>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default MemoryPanel;