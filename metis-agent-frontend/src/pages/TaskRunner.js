// src/pages/TaskRunner.js
import React, { useState, useEffect, useRef } from 'react';
import { 
  Play, CheckCircle, XCircle, Clock, AlertTriangle, 
  RotateCcw, Loader, List, RefreshCw, StopCircle, 
  Pause, SkipForward, FileText, Download, Edit, Trash,
  ChevronDown, ChevronUp, Unlock, Lock, MessageSquare,
  ArrowRightCircle, Info, Eye, EyeOff, Save, FolderOpen,
  Globe, Cpu, Code, HardDrive, Settings
} from 'lucide-react';
import { Card, Tab, Tabs, Button, Form, ProgressBar, Badge, Accordion, Modal, Dropdown } from 'react-bootstrap';
import { TaskRunnerAPI, CommandExecutorAPI, LlmAPI, EditorAPI, NetworkManagerAPI } from '../services/api';
import { runTasksWithLLMFeedback } from '../services/api';
import ReportSummaryModal from '../components/ReportSummaryModal';

// LLM servisini içe aktar
import llmService from '../services/llmService';

// Statü simgesini alır
const getStatusIcon = (status) => {
  switch (status) {
    case 'completed':
      return <CheckCircle className="text-success" size={20} />;
    case 'failed':
      return <XCircle className="text-danger" size={20} />;
    case 'running':
      return <RotateCcw className="text-primary animate-spin" size={20} />;
    case 'paused':
      return <Pause className="text-warning" size={20} />;
    case 'skipped':
      return <SkipForward className="text-info" size={20} />;
    default:
      return <Clock className="text-secondary" size={20} />;
  }
};

// Görev öğesi bileşeni (liste öğesi)
const TaskItem = ({ 
  task, 
  index,
  onSelect,
  isSelected,
  onStatusChange,
  onEdit,
  onDelete,
  onToggleLock,
  onRunTask,
  dependencies,
  allTasks,
  failStrategy,
  isRunning
}) => {
  // Görev için bağımlılıkları kontrol eder
  // 
  //     // TaskItem bileşeni içindeki canRun() fonksiyonunu düzeltelim
    const canRun = () => {
      if (!task.dependencies || task.dependencies.length === 0) return true;
      
      // Bağımlılıkları ID tabanlı kontrol et
      return task.dependencies.every(depId => {
        // ID ile görevi bul
        const depTask = allTasks.find(t => t.id === depId);
        return depTask && (depTask.status === 'completed' || 
          (failStrategy === 'ignore-dependencies' && depTask.status === 'failed'));
      });
    };

    // TaskItem bileşeni içindeki getDependencyState() fonksiyonunu da düzeltelim
    const getDependencyState = () => {
      if (!task.dependencies || task.dependencies.length === 0) return null;
      
      const unmetDependencies = task.dependencies.filter(depId => {
        // ID ile görevi bul
        const depTask = allTasks.find(t => t.id === depId);
        return !depTask || depTask.status !== 'completed';
      });
      
      if (unmetDependencies.length === 0) {
        return <Badge bg="success" className="ms-2">Bağımlılıklar tamam</Badge>;
      } else {
        return <Badge bg="warning" className="ms-2">{unmetDependencies.length} bağımlılık bekliyor</Badge>;
      }
    };
  
  // Task çalıştırma durumuna göre buton görünümü
  const getActionButton = () => {
    if (task.status === 'running') {
      return (
        <Button 
          variant="warning" 
          size="sm" 
          onClick={() => onStatusChange(task.id, 'paused')}
          className="me-1"
        >
          <Pause size={14} />
        </Button>
      );
    } else if (task.status === 'paused') {
      return (
        <Button 
          variant="primary" 
          size="sm" 
          onClick={() => onStatusChange(task.id, 'running')}
          className="me-1"
        >
          <Play size={14} />
        </Button>
      );
    } else if (task.status === 'pending') {
      return (
        <Button 
          variant="primary" 
          size="sm" 
          onClick={() => onRunTask(task.id)}
          disabled={!canRun() || isRunning}
          className="me-1"
        >
          <Play size={14} />
        </Button>
      );
    }
    
    return null;
  };
  
  return (
    <div 
      className={`border rounded mb-2 ${isSelected ? 'border-primary border-2' : 'border'} ${
        task.locked ? 'bg-light' : ''
      }`}
      onClick={() => onSelect(task.id)}
    >
      <div className="p-3">
        <div className="d-flex align-items-start">
          <div className="me-3 mt-1">
            {getStatusIcon(task.status)}
          </div>
          
          <div className="flex-grow-1">
            <div className="d-flex justify-content-between align-items-start">
              <div>
                <h5 className="mb-1 d-flex align-items-center">
                  {task.name}
                  {task.locked && <Lock size={14} className="ms-2 text-secondary" />}
                  {getDependencyState()}
                </h5>
                <p className="text-muted mb-1 small">{task.description}</p>
              </div>
              
              <div className="d-flex">
                {getActionButton()}
                
                <Button 
                  variant="light" 
                  size="sm" 
                  onClick={(e) => {
                    e.stopPropagation();
                    onToggleLock(task.id);
                  }}
                  className="me-1"
                  disabled={isRunning}
                >
                  {task.locked ? <Unlock size={14} /> : <Lock size={14} />}
                </Button>
                
                <Button 
                  variant="light" 
                  size="sm" 
                  onClick={(e) => {
                    e.stopPropagation();
                    onEdit(task.id);
                  }}
                  className="me-1"
                  disabled={isRunning || task.locked}
                >
                  <Edit size={14} />
                </Button>
                
                <Button 
                  variant="light" 
                  size="sm" 
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(task.id);
                  }}
                  disabled={isRunning || task.locked}
                >
                  <Trash size={14} />
                </Button>
              </div>
            </div>
            
            <div className="d-flex align-items-center">
              <div className="code-badge small bg-light text-dark p-1 rounded">
                <code>{task.command}</code>
              </div>
              
              {task.startTime && (
                <span className="ms-2 small badge bg-secondary">
                  {task.endTime 
                    ? `${((task.endTime - task.startTime) / 1000).toFixed(1)}s` 
                    : 'Çalışıyor...'}
                </span>
              )}
            </div>
            
            {/* Bağımlılıklar */}
            {task.dependencies && task.dependencies.length > 0 && (
              <div className="mt-2 small text-muted">
                <strong>Bağımlılıklar:</strong> {task.dependencies.map(depIndex => (
                  <span key={depIndex} className="badge bg-light text-dark me-1">
                    {allTasks[depIndex]?.name || `Görev ${depIndex + 1}`}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// Görev düzenleme modal bileşeni
const TaskEditModal = ({ show, task, onHide, onSave, allTasks }) => {
  const [editedTask, setEditedTask] = useState(task || {});
  
  useEffect(() => {
    if (task) {
      setEditedTask(task);
    }
  }, [task]);
  
  const handleChange = (e) => {
    const { name, value } = e.target;
    setEditedTask(prev => ({
      ...prev,
      [name]: value
    }));
  };
  
  const handleDependencyChange = (e) => {
    const value = Array.from(e.target.selectedOptions, option => parseInt(option.value));
    setEditedTask(prev => ({
      ...prev,
      dependencies: value
    }));
  };
  
  return (
    <Modal show={show} onHide={onHide} size="lg">
      <Modal.Header closeButton>
        <Modal.Title>Görev Düzenle</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        {editedTask && (
          <Form>
            <Form.Group className="mb-3">
              <Form.Label>Görev Adı</Form.Label>
              <Form.Control 
                type="text" 
                name="name" 
                value={editedTask.name || ''} 
                onChange={handleChange} 
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Açıklama</Form.Label>
              <Form.Control 
                as="textarea" 
                name="description" 
                value={editedTask.description || ''} 
                onChange={handleChange} 
                rows={2}
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Komut</Form.Label>
              <Form.Control 
                as="textarea" 
                name="command" 
                value={editedTask.command || ''} 
                onChange={handleChange} 
                rows={3}
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Görev Tipi</Form.Label>
              <Form.Select 
                name="type" 
                value={editedTask.type || 'command'} 
                onChange={handleChange}
              >
                <option value="command">Komut Çalıştır</option>
                <option value="code_change">Kod Değişikliği</option>
                <option value="file_operation">Dosya İşlemi</option>
              </Form.Select>
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Bağımlılıklar</Form.Label>
              <Form.Select 
                multiple 
                value={editedTask.dependencies || []} 
                onChange={handleDependencyChange}
                style={{ height: '120px' }}
              >
                {allTasks && allTasks.map((t, i) => {
                  if (t.id === editedTask.id) return null; // Kendisini bağımlılık olarak gösterme
                  return (
                    <option key={t.id} value={i}>
                      {t.name} (Görev {i + 1})
                    </option>
                  );
                })}
              </Form.Select>
              <Form.Text className="text-muted">
                Birden fazla seçim için Ctrl tuşunu basılı tutun
              </Form.Text>
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Tahmini Süre</Form.Label>
              <Form.Control 
                type="text" 
                name="estimatedTime" 
                value={editedTask.estimatedTime || ''} 
                onChange={handleChange} 
                placeholder="1s, 2m, 5h"
              />
            </Form.Group>
            
            {(editedTask.type === 'code_change' || editedTask.type === 'file_operation') && (
              <Form.Group className="mb-3">
                <Form.Label>Dosya Yolu</Form.Label>
                <Form.Control 
                  type="text" 
                  name="filePath" 
                  value={editedTask.filePath || ''} 
                  onChange={handleChange} 
                  placeholder="/path/to/file.py"
                />
              </Form.Group>
            )}
          </Form>
        )}
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onHide}>İptal</Button>
        <Button 
          variant="primary" 
          onClick={() => onSave(editedTask)}
        >
          Kaydet
        </Button>
      </Modal.Footer>
    </Modal>
  );
};

// LLM ayarları modal bileşeni
const LlmSettingsModal = ({ show, onHide, providers, models, selectedProvider, selectedModel, onProviderChange, onModelChange, onApplySettings }) => {
  const [apiKey, setApiKey] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [statusMessage, setStatusMessage] = useState(null);
  const [temperature, setTemperature] = useState(0.7);
  const [streamingEnabled, setStreamingEnabled] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  // Model listesini yükle
  useEffect(() => {
    if (selectedProvider) {
      checkProviderStatus();
    }
  }, [selectedProvider]);
  
  const checkProviderStatus = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const status = await llmService.checkProviderStatus(selectedProvider);
      
      if (status.provider_status === 'success') {
        setStatusMessage(`Bağlantı durumu: ${status.message}`);
      } else {
        setStatusMessage(`Dikkat: ${status.message}`);
      }
      
      setIsLoading(false);
    } catch (err) {
      setError('Servis durumu kontrol edilirken hata oluştu');
      setIsLoading(false);
    }
  };
  
  const setupProvider = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const setupData = {
        provider: selectedProvider
      };
      
      // API anahtarı gerektiren sağlayıcılar için
      if (['openai', 'anthropic', 'gemini', 'deepseek'].includes(selectedProvider) && apiKey) {
        setupData.api_key = apiKey;
      }
      // Web scraper için kullanıcı adı ve şifre
      if (['webscraper', 'webscraper_claude'].includes(selectedProvider)) {
        if (username) setupData.username = username;
        if (password) setupData.password = password;
      }
      const result = await llmService.setupProvider(setupData);
      
      if (result.status === 'configured') {
        setStatusMessage(`Başarılı: ${result.message}`);
        
        // Yeni modelleri yükle
        if (result.models) {
          onModelChange(result.models[0]?.id || '');
        }
      } else {
        setError(`Yapılandırma hatası: ${result.message}`);
      }
      
      setIsLoading(false);
    } catch (err) {
      setError(`Yapılandırma hatası: ${err.message}`);
      setIsLoading(false);
    }
  };
  
  const handleApplySettings = () => {
    onApplySettings({
      provider: selectedProvider,
      model: selectedModel,
      temperature,
      streaming: streamingEnabled
    });
    onHide();
  };
  
  return (
    <Modal show={show} onHide={onHide}>
      <Modal.Header closeButton>
        <Modal.Title>LLM Ayarları</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <Form>
          <Form.Group className="mb-3">
            <Form.Label>LLM Sağlayıcı</Form.Label>
            <Form.Select 
              value={selectedProvider}
              onChange={(e) => onProviderChange(e.target.value)}
              disabled={isLoading}
            >
              {providers.map(provider => (
                <option key={provider.id} value={provider.id}>
                  {provider.name}
                </option>
              ))}
            </Form.Select>
          </Form.Group>
          
          {['openai', 'anthropic', 'gemini', 'deepseek'].includes(selectedProvider) && (
            <Form.Group className="mb-3">
              <Form.Label>API Anahtarı</Form.Label>
              <Form.Control 
                type="password" 
                placeholder="sk-..." 
                value={apiKey} 
                onChange={(e) => setApiKey(e.target.value)}
                disabled={isLoading}
              />
              <Form.Text muted>
                {selectedProvider === 'openai' && 'OpenAI API anahtarı'}
                {selectedProvider === 'anthropic' && 'Anthropic API anahtarı'}
                {selectedProvider === 'gemini' && 'Google Gemini API anahtarı'}
                {selectedProvider === 'deepseek' && 'DeepSeek API anahtarı'}
              </Form.Text>
            </Form.Group>
          )}
          {['webscraper', 'webscraper_claude'].includes(selectedProvider) && (
            <>
              <Form.Group className="mb-3">
                <Form.Label>Kullanıcı Adı</Form.Label>
                <Form.Control 
                  type="text" 
                  placeholder="E-posta adresiniz" 
                  value={username} 
                  onChange={(e) => setUsername(e.target.value)}
                  disabled={isLoading}
                />
                <Form.Text muted>
                  {selectedProvider === 'webscraper' && 'ChatGPT hesap e-postası'}
                  {selectedProvider === 'webscraper_claude' && 'Claude hesap e-postası'}
                </Form.Text>
              </Form.Group>
              
              <Form.Group className="mb-3">
                <Form.Label>Şifre</Form.Label>
                <Form.Control 
                  type="password" 
                  placeholder="Şifreniz" 
                  value={password} 
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                />
                <Form.Text muted>
                  Şifreniz sadece web sürümüne giriş yapmak için kullanılır ve saklanmaz
                </Form.Text>
              </Form.Group>
            </>
          )}
          <div className="d-grid gap-2 mb-3">
            <Button 
              variant="secondary"
              onClick={setupProvider}
              disabled={isLoading || ((['openai', 'anthropic', 'gemini', 'deepseek'].includes(selectedProvider) && !apiKey))}
            >
              {isLoading ? 
                <>
                  <Loader className="spinner-border spinner-border-sm me-2" />
                  Kontrol Ediliyor...
                </> : 
                'Sağlayıcıyı Yapılandır'
              }
            </Button>
          </div>
          
          {statusMessage && (
            <div className={`alert ${error ? 'alert-danger' : 'alert-info'}`}>
              {statusMessage}
            </div>
          )}
          
          <Form.Group className="mb-3">
            <Form.Label>Model</Form.Label>
            <Form.Select 
              value={selectedModel}
              onChange={(e) => onModelChange(e.target.value)}
              disabled={isLoading || models.length === 0}
            >
              {models.length === 0 ? (
                <option value="">Kullanılabilir model yok</option>
              ) : (
                models.map(model => (
                  <option key={model.id} value={model.id}>
                    {model.name}
                  </option>
                ))
              )}
            </Form.Select>
          </Form.Group>
          
          <Form.Group className="mb-3">
            <Form.Label>
              Sıcaklık: {temperature}
            </Form.Label>
            <Form.Range 
              min={0} 
              max={1} 
              step={0.1}
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
            />
            <div className="d-flex justify-content-between">
              <span className="text-muted small">Kararlı</span>
              <span className="text-muted small">Yaratıcı</span>
            </div>
          </Form.Group>
          
          <Form.Group className="mb-3">
            <Form.Check 
              type="switch"
              id="streaming-switch"
              label="Streaming etkinleştir"
              checked={streamingEnabled}
              onChange={() => setStreamingEnabled(!streamingEnabled)}
              disabled={!['openai', 'anthropic', 'gemini', 'ollama', 'lmstudio'].includes(selectedProvider)}
            />
            <Form.Text muted>
              Yanıtları gerçek zamanlı almak için streaming'i etkinleştirin
            </Form.Text>
          </Form.Group>
        </Form>
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onHide}>İptal</Button>
        <Button 
          variant="primary" 
          onClick={handleApplySettings}
          disabled={!selectedModel || isLoading}
        >
          Ayarları Uygula
        </Button>
      </Modal.Footer>
    </Modal>
  );
};

// Ana TaskRunner bileşeni
const TaskRunner = () => {
  const [tasks, setTasks] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [currentTaskIndex, setCurrentTaskIndex] = useState(-1);
  const [selectedTaskId, setSelectedTaskId] = useState(null);
  const [taskOutput, setTaskOutput] = useState({});
  const [showOutput, setShowOutput] = useState({});
  const [prompt, setPrompt] = useState('');
  const [llmResponse, setLlmResponse] = useState(null);
  const [error, setError] = useState(null);
  const [isLoadingLlm, setIsLoadingLlm] = useState(false);
  const [runMode, setRunMode] = useState('sequential'); // 'sequential', 'parallel', 'manual'
  const [failStrategy, setFailStrategy] = useState('continue'); // 'stop', 'continue', 'ask'
  const [savedTaskSets, setSavedTaskSets] = useState([]);
  const [currentTaskSetName, setCurrentTaskSetName] = useState('');
  const [editingTask, setEditingTask] = useState(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [logEntries, setLogEntries] = useState([]);
  const [showUserConfirmModal, setShowUserConfirmModal] = useState(false);
  const [pendingConfirmation, setPendingConfirmation] = useState(null);
  const [activeTab, setActiveTab] = useState("taskList"); // "taskList", "details", "logs"
  const [contextValues, setContextValues] = useState({});

  const [showReportModal, setShowReportModal] = useState(false);
  const [reportStartTime, setReportStartTime] = useState(null);
  const [reportEndTime, setReportEndTime] = useState(null);

  const maxParallelTasks = useRef(4);
  const activeTasks = useRef(new Set());
  const logRef = useRef(null);
  
  // LLM ayarları için state
  const [llmProviders, setLlmProviders] = useState([]);
  const [llmModels, setLlmModels] = useState([]);
  const [selectedProvider, setSelectedProvider] = useState('openai');
  const [selectedModel, setSelectedModel] = useState('');
  const [llmSettings, setLlmSettings] = useState({
    provider: 'openai',
    model: '',
    temperature: 0.7,
    streaming: true
  });
  const [showLlmSettingsModal, setShowLlmSettingsModal] = useState(false);
  const [llmResponseText, setLlmResponseText] = useState('');
  const [isStreamingResponse, setIsStreamingResponse] = useState(false);
  
  // Sayfa yüklendiğinde LLM sağlayıcılarını getir
  useEffect(() => {
    const fetchProviders = async () => {
      try {
        const providers = await llmService.getProviders();
        setLlmProviders(providers);
        
        if (providers.length > 0) {
          setSelectedProvider(providers[0].id);
        }
      } catch (err) {
        console.error('LLM sağlayıcıları alınamadı:', err);
        addLog('LLM sağlayıcıları alınamadı', 'ERROR');
      }
    };
    
    fetchProviders();
  }, []);
  
  // Seçili sağlayıcı değiştiğinde modelleri getir
  useEffect(() => {
    const fetchModels = async () => {
      if (!selectedProvider) return;
      
      try {
        const models = await llmService.getModels(selectedProvider);
        setLlmModels(models);
        
        if (models.length > 0) {
          setSelectedModel(models[0].id);
        } else {
          setSelectedModel('');
        }
      } catch (err) {
        console.error(`${selectedProvider} için modeller alınamadı:`, err);
        addLog(`${selectedProvider} için modeller alınamadı`, 'ERROR');
        setLlmModels([]);
        setSelectedModel('');
      }
    };
    
    fetchModels();
  }, [selectedProvider]);
  
  const handleRunSequentially = async () => {
    setRunning(true);
    setLogs([...logs, { level: 'info', message: 'Running tasks with LLM feedback...' }]);
    
    try {
        const result = await runTasksWithLLMFeedback(tasks);
        
        // Sonuçları işle ve logları güncelle
        const newLogs = [...logs];
        result.result.forEach(taskResult => {
            newLogs.push({
                level: taskResult.status === 'success' ? 'success' : 'error',
                message: `Task ${taskResult.task.name}: ${
                    taskResult.status === 'success' ? 'Completed' : 'Failed'
                }`,
                details: taskResult.result
            });
        });
        
        setLogs(newLogs);
    } catch (error) {
        setLogs([...logs, { 
            level: 'error', 
            message: `Error running tasks with LLM feedback: ${error.message}` 
        }]);
    } finally {
        setRunning(false);
    }
  };

  // LLM ayarları değişikliğini kabul et
  const applyLlmSettings = (settings) => {
    setLlmSettings(settings);
  };
  
  // Log dosyası oluşturma ve indirme
  const downloadLog = () => {
    const logContent = logEntries.map(entry => 
      `[${new Date(entry.timestamp).toLocaleString()}] [${entry.level}] ${entry.message}`
    ).join('\n');
    
    const blob = new Blob([logContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `task-log-${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };
  
  // Log ekleme fonksiyonu
  const addLog = (message, level = 'INFO') => {
    const newEntry = {
      timestamp: new Date().getTime(),
      message,
      level
    };
    
    setLogEntries(prev => [...prev, newEntry]);
    
    // Log alanını otomatik kaydır
    if (logRef.current) {
      setTimeout(() => {
        logRef.current.scrollTop = logRef.current.scrollHeight;
      }, 10);
    }
  };
  
  // Görev setini kaydetme
  const saveTaskSet = () => {
    if (!currentTaskSetName.trim()) {
      setError('Lütfen görev seti için bir isim girin');
      return;
    }
    
    // Görev setini oluştur
    const taskSet = {
      name: currentTaskSetName,
      tasks: tasks.map(task => ({
        name: task.name,
        description: task.description,
        command: task.command,
        type: task.type,
        dependencies: task.dependencies,
        estimatedTime: task.estimatedTime,
        locked: task.locked || false
      })),
      timestamp: new Date().getTime()
    };
    
    // Lokalde kaydet
    const existingSets = JSON.parse(localStorage.getItem('savedTaskSets') || '[]');
    const updatedSets = [...existingSets, taskSet];
    localStorage.setItem('savedTaskSets', JSON.stringify(updatedSets));
    
    // State'i güncelle
    setSavedTaskSets(updatedSets);
    addLog(`Görev seti kaydedildi: ${currentTaskSetName}`, 'INFO');
  };
  
  // Kaydedilmiş görev setini yükleme
  const loadTaskSet = (index) => {
    if (index < 0 || index >= savedTaskSets.length) return;
    
    const selectedSet = savedTaskSets[index];
    
    // Mevcut görevleri temizle ve yeni görevleri yükle
    resetTaskStates();
    
    // Görevleri formatlayarak yükle
    const loadedTasks = selectedSet.tasks.map((task, index) => ({
      ...task,
      id: `task-${index}`,
      status: 'pending',
      output: '',
      startTime: null,
      endTime: null
    }));
    
    setTasks(loadedTasks);
    setCurrentTaskSetName(selectedSet.name);
    addLog(`Görev seti yüklendi: ${selectedSet.name}`, 'INFO');
  };
  
  // Görev düzenleme
  const editTask = (taskId) => {
    const taskIndex = tasks.findIndex(task => task.id === taskId);
    if (taskIndex === -1) return;
    
    setEditingTask({
      ...tasks[taskIndex],
      index: taskIndex
    });
    
    setShowEditModal(true);
  };
  
  // Görev silme
  const deleteTask = (taskId) => {
    if (window.confirm('Bu görevi silmek istediğinizden emin misiniz?')) {
      setTasks(prevTasks => prevTasks.filter(task => task.id !== taskId));
      addLog(`Görev silindi: ${tasks.find(t => t.id === taskId)?.name}`, 'INFO');
    }
  };
  
  // Görev kilitleme/kilidini açma
  const toggleTaskLock = (taskId) => {
    setTasks(prevTasks => 
      prevTasks.map(task => 
        task.id === taskId 
          ? { ...task, locked: !task.locked } 
          : task
      )
    );
    
    const task = tasks.find(t => t.id === taskId);
    if (task) {
      addLog(`Görev ${task.locked ? 'kilidi açıldı' : 'kilitlendi'}: ${task.name}`, 'INFO');
    }
  };
  
  // Düzenleme modalini kaydetme
  const saveEditedTask = (editedTask) => {
    const newTasks = [...tasks];
    newTasks[editedTask.index] = {
      ...newTasks[editedTask.index],
      name: editedTask.name,
      description: editedTask.description,
      command: editedTask.command,
      dependencies: editedTask.dependencies,
      estimatedTime: editedTask.estimatedTime
    };
    
    setTasks(newTasks);
    setShowEditModal(false);
    setEditingTask(null);
    addLog(`Görev düzenlendi: ${editedTask.name}`, 'INFO');
  };
  
  const changeTaskStatus = (taskId, newStatus) => {
    console.log(`Task status değişiyor: ${taskId} -> ${newStatus}`);
    
    setTasks(prevTasks => {
      const updatedTasks = prevTasks.map(task => 
        task.id === taskId 
          ? { 
              ...task, 
              status: newStatus,
              ...(newStatus === 'running' && task.status !== 'running' ? { startTime: new Date() } : {}),
              ...(newStatus === 'completed' || newStatus === 'failed' || newStatus === 'skipped' ? { endTime: new Date() } : {})
            } 
          : task
      );
      
      // Task değiştiğinde hemen log ekle
      const task = prevTasks.find(t => t.id === taskId);
      if (task) {
        addLog(`Görev durumu değiştirildi: ${task.name} → ${newStatus}`, 
          newStatus === 'completed' ? 'SUCCESS' : 
          newStatus === 'failed' ? 'ERROR' : 'INFO');
      }
      
      return updatedTasks;
    });
  };
    
    // LLM'den görev oluşturma (WebSocket streaming desteği ile)
    const submitPrompt = async () => {
      if (!prompt.trim()) {
        setError('Lütfen LLM için bir açıklama girin');
        return;
      }
      
      setError(null);
      setIsLoadingLlm(true);
      setLlmResponseText('');
      
      // Önceki streaming bağlantısını kapat
      llmService.stopStreaming();
      
      addLog(`LLM isteği gönderiliyor: "${prompt.substring(0, 50)}${prompt.length > 50 ? '...' : ''}"`, 'INFO');
      addLog(`Kullanılan model: ${llmSettings.provider}/${llmSettings.model || 'default'}`, 'INFO');
      
      try {
        if (llmSettings.streaming) {
          // Streaming ile görev oluşturma
          setIsStreamingResponse(true);
          
          // Streaming callback'lerini hazırla
          const callbacks = {
            onContent: (content) => {
              setLlmResponseText(prev => prev + content);
            },
            onDone: async (fullContent) => {
              setIsStreamingResponse(false);
              processLlmResponse(fullContent);
            },
            onError: (errorMsg) => {
              setIsStreamingResponse(false);
              setIsLoadingLlm(false);
              setError('LLM hatası: ' + errorMsg);
              addLog(`LLM hatası: ${errorMsg}`, 'ERROR');
            }
          };
          
          // Streaming başlat
          await llmService.startStreaming({
            prompt,
            provider: llmSettings.provider,
            model: llmSettings.model,
            temperature: llmSettings.temperature,
            system_prompt: "Verilen görevi gerçekleştirmek için JSON formatında görev adımları oluştur."
          }, callbacks);
          
        } else {
          // Normal görev oluşturma (streaming olmadan)
          const tasks = await llmService.generateTasks(
            prompt,
            llmSettings.provider,
            llmSettings.model,
            llmSettings.temperature
          );
          
          processLlmResponse(tasks);
        }
      } catch (err) {
        console.error('LLM yanıtı alınamadı:', err);
        setError('Backend\'ten yanıt alınamadı: ' + err.message);
        addLog(`LLM hatası: ${err.message}`, 'ERROR');
        setIsLoadingLlm(false);
        setIsStreamingResponse(false);
        
        // Geliştirme amaçlı örnek yanıt
        if (process.env.NODE_ENV === 'development') {
          addLog('Geliştirme modu: Mock veriler kullanılıyor', 'WARNING');
          
          // Mock yanıt - üretimde LLM entegrasyonu backend'den gelecek
          const mockResponse = {
            tasks: [
              {
                name: 'Mevcut dizin dosyalarını listele',
                description: 'Mevcut çalışma dizinindeki tüm dosyaları listele',
                command: 'ls -la',
                type: 'command',
                dependencies: [],
                estimatedTime: '1s'
              },
              {
                name: 'Disk alanını kontrol et',
                description: 'Sistemdeki kullanılabilir disk alanını kontrol et',
                command: 'df -h',
                type: 'command',
                dependencies: [],
                estimatedTime: '1s'
              },
              {
                name: 'Bellek kullanımını kontrol et',
                description: 'Sistem bellek kullanımını göster',
                command: 'free -h',
                type: 'command',
                dependencies: [],
                estimatedTime: '1s'
              },
              {
                name: 'Yedekleme dizini oluştur',
                description: 'Yedeklemeler için bir dizin oluştur',
                command: 'mkdir -p backup',
                type: 'command',
                dependencies: [0], // Görev 0'a bağımlı (dizin listeleme)
                estimatedTime: '1s'
              },
              {
                name: 'Yapılandırma dosyalarını yedekle',
                description: 'Yapılandırma dosyalarını yedekle',
                command: 'cp *.conf backup/ || echo "Conf dosyası bulunamadı"',
                type: 'command',
                dependencies: [3], // Görev 3'e bağımlı (yedekleme dizini oluşturma)
                estimatedTime: '2s'
              }
            ]
          };
          
          processLlmResponse(mockResponse);
        }
      }
    };
    

    const processLlmResponse = (response) => {
      try {
        // Yanıt string ise JSON olarak parse et
        let parsedResponse;
        if (typeof response === 'string') {
          // JSON içeriğini çıkarmaya çalış
          let jsonContent = response;
          
          if (response.includes('```json')) {
            jsonContent = response.split('```json')[1].split('```')[0].trim();
          } else if (response.includes('```')) {
            jsonContent = response.split('```')[1].split('```')[0].trim();
          }
          
          try {
            parsedResponse = JSON.parse(jsonContent);
          } catch (jsonError) {
            console.error('JSON parse hatası:', jsonError);
            addLog(`JSON parse hatası: ${jsonError.message}`, 'ERROR');
            throw new Error('Geçersiz JSON formatı: ' + jsonError.message);
          }
        } else {
          parsedResponse = response;
        }
        
        // 'data' içinde geliyorsa, data'yı çıkar
        if (parsedResponse.data && parsedResponse.data.tasks) {
          parsedResponse = parsedResponse.data;
        }
        
        // "tasks" anahtarını kontrol et, yoksa dönüştür
        if (!parsedResponse.hasOwnProperty('tasks')) {
          console.warn('Yanıtta "tasks" anahtarı bulunamadı, dönüştürülüyor...');
          
          // Farklı formatları standardize et
          if (parsedResponse.actions && Array.isArray(parsedResponse.actions)) {
            parsedResponse = {
              tasks: parsedResponse.actions.map((action, index) => ({
                name: action.name || `Görev ${index + 1}`,
                description: action.description || "Görev açıklaması",
                tool: action.tool,
                action: action.action,
                params: action.params || {},
                type: action.tool === "command_executor" ? "command" : "tool_action",
                dependencies: action.dependencies || []
              }))
            };
          } else if (parsedResponse.steps && Array.isArray(parsedResponse.steps)) {
            parsedResponse = {
              tasks: parsedResponse.steps.map((step, index) => ({
                name: `Adım ${step.step || (index + 1)}`,
                description: step.description || "Adım açıklaması",
                command: step.command || `echo "${step.description}"`,
                type: "command",
                dependencies: index > 0 ? [index - 1] : []
              }))
            };
          } else {
            throw new Error('Yanıt formatı uyumlu değil: "tasks" veya bilinen alternatif format bulunamadı');
          }
        }
        
        // Her göreve benzersiz ID ata (varsa olanı koru)
        const tasksWithIds = (parsedResponse.tasks || []).map((task, index) => {
          return {
            ...task,
            id: task.id || `task-${Date.now()}-${index}`
          };
        });
        
        // Bağımlılık indekslerini ID'lere dönüştür
        const normalizedTasks = tasksWithIds.map((task, currentIndex) => {
          // Bağımlılıkları işle
          let idBasedDependencies = [];
          if (task.dependencies && Array.isArray(task.dependencies)) {
            idBasedDependencies = task.dependencies.map(dep => {
              // Eğer dep zaten bir ID ise olduğu gibi kullan
              if (typeof dep === 'string' && dep.startsWith('task-')) {
                return dep;
              }
              
              // Eğer dep bir indeks ise ilgili ID'yi bul
              if (typeof dep === 'number' || (typeof dep === 'string' && !isNaN(parseInt(dep)))) {
                const depIndex = parseInt(dep);
                if (depIndex >= 0 && depIndex < tasksWithIds.length) {
                  return tasksWithIds[depIndex].id;
                }
              }
              return null;
            }).filter(Boolean); // null değerleri filtrele
          }
          
          // Görev tipini düzgün belirle
          let taskType = task.type || 'command';
          if (task.tool && task.action && !task.command) {
            taskType = 'tool_action';
          } else if (task.command) {
            taskType = 'command';
          }
          
          return {
            ...task,
            status: 'pending',
            output: '',
            startTime: null,
            endTime: null,
            locked: false,
            type: taskType,
            dependencies: idBasedDependencies,
            // Eğer command_executor tool'u kullanılıyorsa, command alanını doldur
            ...(task.tool === 'command_executor' && task.params?.command && {
              command: task.params.command
            })
          };
        });
        
        setTasks(normalizedTasks);
        addLog(`${normalizedTasks.length} görev LLM tarafından oluşturuldu`, 'SUCCESS');
        
        // Debug: Bağımlılık yapısını logla
        console.log("Oluşturulan görevler ve bağımlılıklar:", normalizedTasks);
        
      } catch (err) {
        setError('LLM yanıtı işlenemedi: ' + err.message);
        addLog(`LLM yanıtı işleme hatası: ${err.message}`, 'ERROR');
        console.error('LLM yanıtı işlenemedi:', err, response);
      } finally {
        setIsLoadingLlm(false);
        setIsStreamingResponse(false);
      }
    };
    
    // Görev durumlarını sıfırlama
    const resetTaskStates = () => {
      setIsRunning(false);
      setCurrentTaskIndex(-1);
      setSelectedTaskId(null);
      setTaskOutput({});
      setShowOutput({});
      activeTasks.current.clear();
      
      // Görevleri sıfırla (kilitli olanları koruyarak)
      setTasks(prevTasks => 
        prevTasks.map(task => ({
          ...task,
          status: 'pending',
          output: '',
          startTime: null,
          endTime: null,
          // Kilitli durumu koru
        }))
      );
      
      addLog('Tüm görev durumları sıfırlandı', 'INFO');
    };
    



    const executeTask = async (taskId) => {
      try {
        const taskToExecute = tasks.find(t => t.id === taskId);
        
        if (!taskToExecute) {
          console.error(`Task not found with ID: ${taskId}`);
          throw new Error(`Task not found with ID: ${taskId}`);
        }
        
        console.log("Executing task:", taskToExecute);
        
        // Task durumunu çalışıyor olarak güncelle
        changeTaskStatus(taskToExecute.id, 'running');
        
        // Backend'de context ile çalıştır
        const result = await TaskRunnerAPI.executeWithContext(taskToExecute, llmSettings);
        
        if (result.error) {
          throw new Error(result.error);
        }
        
        // Güncel context değerlerini al
        setContextValues(result.context || {});
        
        // Çıktıyı doğru şekilde çıkart ve işle
        let outputText = '';
        
        // Backend'den gelen yanıt formatına göre çıktıyı çıkart
        if (result.result) {
          if (typeof result.result.output === 'string') {
            // Doğrudan output alanı var
            outputText = result.result.output;
          } else if (result.result.connections) {
            // Network manager gibi özel format
            outputText = JSON.stringify(result.result.connections, null, 2);
          } else if (result.result.active_users) {
            // User manager gibi özel format
            outputText = JSON.stringify(result.result.active_users, null, 2);
          } else if (result.result.message) {
            // Durum mesajı içeren yanıt
            outputText = result.result.message;
            if (result.result.details) {
              outputText += "\n\n" + result.result.details;
            }
          } else {
            // Diğer tüm yanıt tipleri için JSON formatında göster
            outputText = JSON.stringify(result.result, null, 2);
          }
        } else {
          outputText = 'Çıktı yok';
        }
        
        console.log("Task output:", outputText);
        
        // UI taskOutput state'ini güncelle
        setTaskOutput(prev => ({...prev, [taskToExecute.id]: outputText}));
        
        // Task'ın output alanını tasks state'inde güncelle
        setTasks(prevTasks => prevTasks.map(task => 
          task.id === taskId 
            ? {...task, output: outputText}
            : task
        ));
        
        // Değerlendirmeyi logla
        if (result.evaluation) {
          const evaluation = result.evaluation;
          addLog(`LLM Değerlendirmesi (${taskToExecute.name}): ${evaluation.success ? 'Başarılı' : 'Başarısız'}`, 
            evaluation.success ? 'SUCCESS' : 'WARNING');
          
          if (evaluation.error) {
            addLog(`Değerlendirme Hatası: ${evaluation.error}`, 'WARNING');
          }
          
          addLog(`Özet: ${evaluation.summary}`, 'INFO');
          
          // LLM devam etmememizi öneriyorsa ve otomatik çalışıyorsak
          if (!evaluation.shouldContinue && isRunning && runMode !== 'manual') {
            addLog(`UYARI: LLM, sonraki adımlara devam edilmemesini öneriyor: ${evaluation.recommendation}`, 'WARNING');
            
            // Stratejiye göre karar ver
            if (failStrategy === 'ask') {
              // Kullanıcıya sor
              setPendingConfirmation({
                type: 'llmRecommendation',
                taskId: taskToExecute.id,
                message: `LLM, sonraki adımlara devam edilmemesini öneriyor: ${evaluation.recommendation}\n\nDevam etmek istiyor musunuz?`
              });
              setShowUserConfirmModal(true);
              setIsRunning(false); // Geçici olarak durdur
            } else if (failStrategy === 'stop') {
              // Otomatik durdur
              addLog('LLM önerisi nedeniyle çalışma durduruldu', 'WARNING');
              setIsRunning(false);
            }
          }
        }
        
        // Task durumunu tamamlandı olarak güncelle
        changeTaskStatus(taskToExecute.id, 'completed');
        
        return result.result;
      } catch (error) {
        console.error(`Error executing task ${taskId}:`, error);
        
        // Hata durumunda task durumunu güncelle
        changeTaskStatus(taskId, 'failed');
        
        // Hata mesajını task çıktısına ekle
        const errorOutput = `Hata: ${error.message}\n\n${error.stack || ''}`;
        
        // Task çıktısını güncelle
        setTasks(prevTasks => prevTasks.map(task => 
          task.id === taskId 
            ? {...task, output: errorOutput}
            : task
        ));
        
        // TaskOutput state'ini güncelle
        setTaskOutput(prev => ({
          ...prev, 
          [taskId]: errorOutput
        }));
        
        throw error;
      }
    };


    const executeTasksSequentially = async () => {
      setIsRunning(true);
      setCurrentTaskIndex(-1);
      addLog('Görevler sıralı olarak çalıştırılıyor', 'INFO');
      
      try {
        // Backend'de sıralı çalıştırma
        const result = await TaskRunnerAPI.executeSequential(tasks, failStrategy);
        
        if (result.error) {
          throw new Error(result.error);
        }
        
        // Context'i güncelle
        setContextValues(result.context || {});
        
        // Task durumlarını ve çıktılarını güncelle
        result.results.forEach((taskResult, index) => {
          const taskId = tasks[index].id;
          
          // Çıktıyı taskOutput state'ine ekle
          const output = taskResult.result?.output || JSON.stringify(taskResult.result);
          setTaskOutput(prev => ({...prev, [taskId]: output}));
          
          // Task durumunu güncelle
          changeTaskStatus(
            taskId, 
            taskResult.status === 'error' ? 'failed' : 'completed'
          );
          
          // Log kaydı ekle
          if (taskResult.status === 'error') {
            addLog(`Görev başarısız: ${tasks[index].name}`, 'ERROR');
          } else {
            addLog(`Görev tamamlandı: ${tasks[index].name}`, 'SUCCESS');
          }
        });
        
        addLog('Tüm görevler çalıştırıldı', 'SUCCESS');
      } catch (error) {
        console.error('Görevleri çalıştırma hatası:', error);
        addLog(`Görevleri çalıştırma hatası: ${error.message}`, 'ERROR');
      } finally {
        setIsRunning(false);
        setReportEndTime(new Date());
      }
    };

    // TaskRunner.js içindeki processTaskWithContext fonksiyonunu geliştirelim
    const processTaskWithContext = (task) => {
      const processedTask = {...task};
      
      // Komut içindeki placeholder'ları değiştir
      if (processedTask.command && typeof processedTask.command === 'string') {
        processedTask.command = applyContext(processedTask.command);
      }
      
      // Params objesi içindeki tüm string değerleri işle
      if (processedTask.params) {
        const processedParams = {...processedTask.params};
        
        // Tüm string parametreleri kontrol et
        Object.keys(processedParams).forEach(key => {
          if (typeof processedParams[key] === 'string') {
            // Placeholder'ları değiştir
            processedParams[key] = applyContext(processedParams[key]);
          }
        });
        
        processedTask.params = processedParams;
      }
      
      return processedTask;
    };

    const applyContext = (text) => {
      if (typeof text !== 'string') return text;
      
      let result = text;
      
      // <task_xyz_output> formatındaki placeholder'ları ara ve değiştir
      const placeholderRegex = /<([^>]+)>/g;
      let match;
      
      while ((match = placeholderRegex.exec(text)) !== null) {
        const placeholder = match[0]; // <task_xyz_output>
        const key = match[1]; // task_xyz_output
        
        if (contextValues[key]) {
          result = result.replace(placeholder, contextValues[key]);
          console.log(`Placeholder değiştirildi: ${placeholder} -> ${
            contextValues[key].substr(0, 30)}${contextValues[key].length > 30 ? '...' : ''}`);
        }
      }
      
      return result;
    };

    // Hata durumunda strateji
    const handleTaskFailure = (failedTaskId) => {
      if (failStrategy === 'stop') {
        // Tüm çalışmayı durdur
        setIsRunning(false);
        addLog('Hata nedeniyle tüm görevler durduruldu', 'WARNING');
      } else if (failStrategy === 'ask') {
        // Kullanıcıya sor
        setPendingConfirmation({
          type: 'taskFailure',
          taskId: failedTaskId,
          message: 'Bir görev başarısız oldu. Devam etmek istiyor musunuz?'
        });
        setShowUserConfirmModal(true);
      } 
      // 'continue' stratejisi varsayılan davranıştır, hiçbir şey yapmadan devam eder
    };
    

    
  const executeTasksInParallel = async () => {
    setIsRunning(true);
    addLog(`Görevler paralel olarak çalıştırılıyor (max ${maxParallelTasks.current})`, 'INFO');
    
    // Aktif görevleri takip et
    activeTasks.current.clear();
    
    // Çalıştırılabilir görevleri bul
    const findExecutableTasks = () => {
      return tasks.filter(task => {
        if (task.status !== 'pending') return false;
        if (task.locked) return false;
        if (activeTasks.current.has(task.id)) return false;
        
        // Bağımlılıkları kontrol et - ID bazlı
        if (!task.dependencies || task.dependencies.length === 0) return true;
        
        return task.dependencies.every(depId => {
          const depTask = tasks.find(t => t.id === depId);
          return depTask && depTask.status === 'completed';
        });
      });
    };
    
    // Görevleri çalıştır
    const runParallelTasks = async () => {
      if (!isRunning) return; // Çalışma durdurulduysa çık
      
      // Çalıştırılabilir görevleri bul
      const executableTasks = findExecutableTasks();
      
      // Maksimum paralel görev sayısını aşmayacak şekilde boşluk var mı kontrol et
      const numSlotsAvailable = maxParallelTasks.current - activeTasks.current.size;
      
      if (numSlotsAvailable > 0 && executableTasks.length > 0) {
        // Boş slotları doldur
        const tasksToRun = executableTasks.slice(0, numSlotsAvailable);
        
        // Bu görevleri çalıştır
        for (const task of tasksToRun) {
          // Aktif görevlere ekle
          activeTasks.current.add(task.id);
          
          // Görevi asenkron olarak çalıştır
          executeTask(task.id)
            .finally(() => {
              // Aktif görevlerden çıkar
              activeTasks.current.delete(task.id);
            });
            
          // API çağrılarını dengelemek için kısa bir gecikme ekle
          await new Promise(resolve => setTimeout(resolve, 50));
        }
      }
      
      // Tamamlanma durumunu kontrol et
      const allDone = tasks.every(t => 
        t.locked || t.status === 'completed' || t.status === 'failed' || t.status === 'skipped'
      );
      
      if (allDone && activeTasks.current.size === 0) {
        // Tüm görevler tamamlandı
        addLog('Tüm görevler tamamlandı', 'SUCCESS');
        setIsRunning(false);
        setReportEndTime(new Date());
      } else if (executableTasks.length === 0 && activeTasks.current.size === 0) {
        // Çalıştırılabilir görev kalmadı
        addLog('Çalıştırılabilir görev kalmadı, bağımlılık zincirinde sorun olabilir', 'WARNING');
        setIsRunning(false);
        setReportEndTime(new Date());
      } else {
        // Hala çalışıyor, kısa bir süre sonra tekrar kontrol et
        setTimeout(runParallelTasks, 200);
      }
    };
    
    // Paralel görevi başlat
    runParallelTasks();
  };
    
    // Görevleri manuel olarak çalıştır
    const executeTasksManually = async (taskId) => {
      // Tek görevi manuel olarak çalıştır
      await executeTask(taskId);
    };
    
    // Görevleri başlat
    const startExecution = () => {
      if (isRunning) return; // Çoklu çalıştırmayı engelle
      
      if (tasks.length === 0) {
        setError('Çalıştırılacak görev yok');
        return;
      }

      const now = new Date();
      // Rapor başlangıç zamanını ayarla
      setReportStartTime(now);
      
       // Tüm görevlerin başlangıç zamanını temizle (resetleme için)
      setTasks(prevTasks => 
        prevTasks.map(task => ({
          ...task,
          startTime: null,
          endTime: null,
          output: task.status === 'pending' ? '' : task.output
        }))
      );

      if (runMode === 'sequential') {
        executeTasksSequentially();
      } else if (runMode === 'parallel') {
        executeTasksInParallel();
      }
    };
    
    // Çalıştırmayı durdur
    const stopExecution = () => {
      setIsRunning(false);
      addLog('Görev çalıştırma manuel olarak durduruldu', 'WARNING');
    };
    
    // Çıktıyı göster/gizle
    const toggleOutput = (taskId) => {
      setShowOutput(prev => ({
        ...prev,
        [taskId]: !prev[taskId]
      }));
    };
    
    const openReportModal = () => {
      // Görev çıktılarını tasks array'ine senkronize et
      const updatedTasks = tasks.map(task => ({
        ...task,
        output: taskOutput[task.id] || task.output
      }));
      
      setTasks(updatedTasks);
      setShowReportModal(true);
    };
    // Görevleri yükle
    useEffect(() => {
      // Kaydedilmiş görev setlerini localStorage'dan yükle
      const savedSets = JSON.parse(localStorage.getItem('savedTaskSets') || '[]');
      setSavedTaskSets(savedSets);
      
      // Development ortamında örnek görevleri yükle
      if (process.env.NODE_ENV === 'development' && tasks.length === 0) {
        const exampleTasks = [
          {
            id: 'task-example-1',
            name: 'Proje bağımlılıklarını kurma',
            description: 'Node modüllerini kurar.',
            command: 'npm install',
            type: 'command',
            dependencies: [],
            estimatedTime: '1m',
            status: 'pending',
            output: '',
            startTime: null,
            endTime: null,
            locked: false
          },
          {
            id: 'task-example-2',
            name: 'Eski build dosyalarını temizleme',
            description: 'Derleme klasörünü temizler.',
            command: 'rm -rf dist',
            type: 'command',
            dependencies: [],
            estimatedTime: '1s',
            status: 'pending',
            output: '',
            startTime: null,
            endTime: null,
            locked: false
          },
          {
            id: 'task-example-3',
            name: 'Projeyi derleme',
            description: 'TypeScript kodunu derler.',
            command: 'npm run build',
            type: 'command',
            dependencies: [0, 1],
            estimatedTime: '30s',
            status: 'pending',
            output: '',
            startTime: null,
            endTime: null,
            locked: false
          }
        ];
        
        setTasks(exampleTasks);
        addLog('Örnek görevler yüklendi', 'INFO');
      }
    }, []);
    
    // Seçili görevi göster
    const selectedTask = selectedTaskId ? tasks.find(task => task.id === selectedTaskId) : null;
    
    // Tamamlanan ve başarısız görevleri say
    const completedCount = tasks.filter(task => task.status === 'completed').length;
    const failedCount = tasks.filter(task => task.status === 'failed').length;
    const skippedCount = tasks.filter(task => task.status === 'skipped').length;
    const pendingCount = tasks.filter(task => task.status === 'pending' || task.status === 'running' || task.status === 'paused').length;
    
    return (
      <div className="container-fluid p-0">
        {/* Chat alanı - üst bölüm */}
        <div className="bg-gradient-to-r from-primary to-primary-dark p-4 mb-4">
          <div className="container-fluid">
            <div className="row">
              <div className="col-12">
                <Card className="shadow-sm">
                  <Card.Header className="bg-white">
                    <div className="d-flex justify-content-between align-items-center">
                      <h5 className="m-0">
                        <MessageSquare className="me-2" size={18} />
                        Chat ve Görev İsteği
                      </h5>
                      {!isRunning && completedCount + failedCount + skippedCount > 0 && (
                        <Button
                          variant="info"
                          onClick={() => {
                            // Tüm görev çıktılarının senkronize edildiğinden emin ol
                            const updatedTasks = tasks.map(task => {
                              // Mevcut çıktı değerini kontrol et
                              console.log(`Task '${task.name}' (${task.id}) mevcut output:`, task.output ? task.output.substring(0, 100) + "..." : "Yok");
                              
                              // taskOutput'ta kayıtlı değeri kontrol et
                              console.log(`Task '${task.name}' (${task.id}) taskOutput'ta kayıtlı değer:`, 
                                taskOutput[task.id] ? taskOutput[task.id].substring(0, 100) + "..." : "Yok");
                        
                              // Güncellenen task değerini döndür
                              return {
                                ...task,
                                output: taskOutput[task.id] || task.output
                              };
                            });
                                                       
                            setTasks(updatedTasks);
                            setShowReportModal(true);
                          }}
                          className="me-2 d-flex align-items-center"
                        >
                          <FileText size={16} className="me-1" />
                          Rapor Özeti
                        </Button>
                      )}
                      <Button 
                        variant="outline-secondary" 
                        size="sm"
                        onClick={() => setShowLlmSettingsModal(true)}
                      >
                        <Settings size={16} className="me-1" />
                        LLM Ayarları
                      </Button>
                    </div>
                  </Card.Header>
                  <Card.Body>
                    <Form.Group className="mb-3">
                      <Form.Control
                        as="textarea"
                        value={prompt}
                        onChange={(e) => setPrompt(e.target.value)}
                        placeholder="Bir görev tanımı veya soru yazın..."
                        rows={3}
                        disabled={isLoadingLlm || isRunning}
                      />
                    </Form.Group>
                    
                    <div className="d-flex flex-wrap justify-content-between align-items-center">
                      <div className="mb-3">
                        <Button
                          variant="primary"
                          onClick={submitPrompt}
                          disabled={isLoadingLlm || !prompt.trim() || isRunning}
                          className="d-flex align-items-center"
                        >
                          {isLoadingLlm ? (
                            <>
                              <Loader className="me-2 spinner-border spinner-border-sm" size={16} />
                              {isStreamingResponse ? 'İşleniyor...' : 'İşleniyor...'}
                            </>
                          ) : (
                            <>
                              <ArrowRightCircle className="me-2" size={16} />
                              Görevleri Oluştur
                            </>
                          )}
                        </Button>
                      </div>
                      
                      <div className="d-flex flex-wrap gap-2">
                        <Dropdown>
                          <Dropdown.Toggle variant="outline-secondary" size="sm">
                            <HardDrive className="me-1" size={14} />
                            Dosya İşlemleri
                          </Dropdown.Toggle>
                          <Dropdown.Menu>
                            <Dropdown.Item onClick={() => setPrompt("Aşağıdaki dizinlerdeki tüm dosyaları listele ve bir yedek dizini oluştur: /home/user/project")}>
                              Dosyaları listeleme ve yedekleme
                            </Dropdown.Item>
                            <Dropdown.Item onClick={() => setPrompt("Tüm .txt dosyalarını bulup içlerinde 'error' kelimesi geçenleri filtrele")}>
                              Dosya içeriklerini arama
                            </Dropdown.Item>
                            <Dropdown.Item onClick={() => setPrompt("Bir zip arşivi oluştur ve belirtilen dosyaları içine ekle")}>
                              Arşiv oluşturma
                            </Dropdown.Item>
                          </Dropdown.Menu>
                        </Dropdown>
                        
                        <Dropdown>
                          <Dropdown.Toggle variant="outline-secondary" size="sm">
                            <Cpu className="me-1" size={14} />
                            Sistem İşlemleri
                          </Dropdown.Toggle>
                          <Dropdown.Menu>
                            <Dropdown.Item onClick={() => setPrompt("Sistem durumunu kontrol et: disk, bellek ve CPU kullanımı")}>
                              Sistem durumu kontrol
                            </Dropdown.Item>
                            <Dropdown.Item onClick={() => setPrompt("Sistemi güncellemek için gereken komutları çalıştır")}>
                              Sistem güncelleme
                            </Dropdown.Item>
                            <Dropdown.Item onClick={() => setPrompt("Açık portları ve çalışan servisleri listele")}>
                              Açık port ve servisleri listeleme
                            </Dropdown.Item>
                          </Dropdown.Menu>
                        </Dropdown>
                        
                        <Dropdown>
                          <Dropdown.Toggle variant="outline-secondary" size="sm">
                            <Code className="me-1" size={14} />
                            Kod İşlemleri
                          </Dropdown.Toggle>
                          <Dropdown.Menu>
                            <Dropdown.Item onClick={() => setPrompt("Python dosyalarındaki tüm TODO yorumlarını bul ve listele")}>
                              TODO yorumlarını bulma
                            </Dropdown.Item>
                            <Dropdown.Item onClick={() => setPrompt("Git deposunun durumunu kontrol et ve değişiklikleri commitleyecek bir görev oluştur")}>
                              Git işlemleri
                            </Dropdown.Item>
                            <Dropdown.Item onClick={() => setPrompt("Projeyi derle ve testleri çalıştır")}>
                              Derleme ve test
                            </Dropdown.Item>
                          </Dropdown.Menu>
                        </Dropdown>
                        
                        <Dropdown>
                          <Dropdown.Toggle variant="outline-secondary" size="sm">
                            <Globe className="me-1" size={14} />
                            Ağ İşlemleri
                          </Dropdown.Toggle>
                          <Dropdown.Menu>
                            <Dropdown.Item onClick={() => setPrompt("Belirtilen web servislerinin ayakta olup olmadığını kontrol et")}>
                              Servis kontrol
                            </Dropdown.Item>
                            <Dropdown.Item onClick={() => setPrompt("DNS kayıtlarını sorgula ve IP adreslerini göster")}>
                              DNS sorgusu
                            </Dropdown.Item>
                            <Dropdown.Item onClick={() => setPrompt("API endpoint'lerine HTTP istekleri gönder ve yanıtları kontrol et")}>
                              API testi
                            </Dropdown.Item>
                          </Dropdown.Menu>
                        </Dropdown>
                      </div>
                    </div>
                    
                    {/* LLM yanıt alanı - streaming için */}
                    {isStreamingResponse && (
                      <div className="mt-3">
                      <div className="border rounded p-2 bg-light">
                        <p className="mb-1 text-muted small">LLM yanıtı işleniyor...</p>
                        <div className="small">
                          {llmResponseText || (
                            <div className="text-center my-3">
                              <Loader className="spinner-border spinner-border-sm text-primary" />
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </Card.Body>
              </Card>
            </div>
          </div>
        </div>
      </div>
      
      {/* Görev yönetimi paneli - alt bölüm */}
      <div className="container-fluid">
        <div className="row mb-4">
          <div className="col-12">
            <Card>
              <Card.Header>
                <div className="d-flex justify-content-between align-items-center">
                  <h5 className="m-0">
                    <List className="me-2" size={18} />
                    Görev Yönetimi
                  </h5>
                  
                  <div className="d-flex align-items-center">
                    <Form.Group className="me-3 mb-0">
                      <Form.Select 
                        value={runMode} 
                        onChange={(e) => setRunMode(e.target.value)}
                        className="me-2 d-inline-block"
                        style={{ width: 'auto' }}
                        disabled={isRunning}
                      >
                        <option value="sequential">Sıralı Çalıştırma</option>
                        <option value="parallel">Paralel Çalıştırma</option>
                        <option value="manual">Manuel Çalıştırma</option>
                      </Form.Select>
                    </Form.Group>
                    
                    <Button
                      variant="success"
                      onClick={startExecution}
                      disabled={isRunning || tasks.length === 0 || runMode === 'manual'}
                      className="me-2 d-flex align-items-center"
                    >
                      <Play size={16} className="me-1" />
                      Çalıştır
                    </Button>
                    
                    {isRunning && (
                      <Button
                        variant="danger"
                        onClick={stopExecution}
                        className="me-2 d-flex align-items-center"
                      >
                        <StopCircle size={16} className="me-1" />
                        Durdur
                      </Button>
                    )}
                    
                    <Button
                      variant="secondary"
                      onClick={resetTaskStates}
                      disabled={isRunning}
                      className="d-flex align-items-center"
                    >
                      <RefreshCw size={16} className="me-1" />
                      Sıfırla
                    </Button>
                  </div>
                </div>
              </Card.Header>
              
              <Card.Body className="p-0">
                {/* Ayarlar ve kontroller */}
                <div className="px-3 py-2 bg-light border-bottom d-flex justify-content-between align-items-center">
                  <div className="d-flex align-items-center">
                    <Form.Group className="me-3 mb-0">
                      <Form.Label className="me-2 mb-0">Hata Stratejisi:</Form.Label>
                      <Form.Select 
                        value={failStrategy} 
                        onChange={(e) => setFailStrategy(e.target.value)}
                        className="d-inline-block"
                        style={{ width: 'auto' }}
                        disabled={isRunning}
                      >
                        <option value="continue">Devam Et</option>
                        <option value="stop">Durdur</option>
                        <option value="ask">Sor</option>
                        <option value="ignore-dependencies">Bağımlılıkları Yoksay</option>
                      </Form.Select>
                    </Form.Group>
                    
                    {runMode === 'parallel' && (
                      <Form.Group className="me-3 mb-0">
                        <Form.Label className="me-2 mb-0">Paralel Görevler:</Form.Label>
                        <Form.Select
                          value={maxParallelTasks.current}
                          onChange={(e) => {
                            maxParallelTasks.current = parseInt(e.target.value);
                          }}
                          style={{ width: 'auto' }}
                          className="d-inline-block"
                          disabled={isRunning}
                        >
                          <option value="2">2</option>
                          <option value="4">4</option>
                          <option value="8">8</option>
                          <option value="16">16</option>
                        </Form.Select>
                      </Form.Group>
                    )}
                  </div>
                  
                  <div>
                    <Form.Group className="d-inline-block me-2">
                      <Form.Control
                        type="text"
                        placeholder="Görev seti adı"
                        value={currentTaskSetName}
                        onChange={(e) => setCurrentTaskSetName(e.target.value)}
                        disabled={isRunning || tasks.length === 0}
                        style={{ width: '200px' }}
                      />
                    </Form.Group>
                    
                    <Button
                      variant="primary"
                      size="sm"
                      className="me-2"
                      onClick={saveTaskSet}
                      disabled={isRunning || tasks.length === 0 || !currentTaskSetName.trim()}
                    >
                      <Save size={14} className="me-1" />
                      Kaydet
                    </Button>
                    
                    <Form.Select
                      size="sm"
                      style={{ width: 'auto' }}
                      className="d-inline-block"
                      onChange={(e) => loadTaskSet(parseInt(e.target.value))}
                      disabled={isRunning || savedTaskSets.length === 0}
                      defaultValue=""
                    >
                      <option value="" disabled>Kayıtlı Setler</option>
                      {savedTaskSets.map((set, idx) => (
                        <option key={idx} value={idx}>
                          {set.name} ({set.tasks.length} görev)
                        </option>
                      ))}
                    </Form.Select>
                  </div>
                </div>
                
                {/* İlerleme çubuğu */}
                {tasks.length > 0 && (
                  <div className="px-3 py-2">
                    <ProgressBar>
                      <ProgressBar 
                        variant="success" 
                        now={(completedCount / tasks.length) * 100} 
                        key={1} 
                      />
                      <ProgressBar 
                        variant="danger" 
                        now={(failedCount / tasks.length) * 100} 
                        key={2} 
                      />
                      <ProgressBar 
                        variant="warning" 
                        now={(skippedCount / tasks.length) * 100} 
                        key={3} 
                      />
                    </ProgressBar>
                    
                    <div className="d-flex justify-content-between mt-2 text-muted small">
                      <div>
                        <span className="badge bg-success me-1">{completedCount}</span> tamamlandı
                      </div>
                      <div>
                        <span className="badge bg-danger me-1">{failedCount}</span> başarısız
                      </div>
                      <div>
                        <span className="badge bg-warning me-1">{skippedCount}</span> atlandı
                      </div>
                      <div>
                        <span className="badge bg-secondary me-1">{pendingCount}</span> bekliyor
                      </div>
                    </div>
                  </div>
                )}
                
                {/* Sekmeler */}
                <Tabs
                  activeKey={activeTab}
                  onSelect={(k) => setActiveTab(k)}
                  className="border-bottom mb-3 px-3"
                >
                  <Tab eventKey="taskList" title="Görev Listesi">
                    <div className="px-3">
                      {tasks.length === 0 ? (
                        <div className="text-center py-5 text-muted">
                          <List size={48} className="mb-3" />
                          <h5>Henüz görev oluşturulmadı</h5>
                          <p>Bir görev oluşturmak için LLM isteği gönderin veya kayıtlı bir görev seti yükleyin.</p>
                        </div>
                      ) : (
                        <div className="task-list mb-3">
                          {tasks.map((task, index) => (
                            <TaskItem
                              key={task.id}
                              task={task}
                              index={index}
                              onSelect={setSelectedTaskId}
                              isSelected={selectedTaskId === task.id}
                              onStatusChange={changeTaskStatus}
                              onEdit={editTask}
                              onDelete={deleteTask}
                              onToggleLock={toggleTaskLock}
                              onRunTask={executeTasksManually}
                              dependencies={task.dependencies}
                              allTasks={tasks}
                              failStrategy={failStrategy}
                              isRunning={isRunning}
                            />
                          ))}
                        </div>
                      )}
                    </div>
                  </Tab>
                  
                  <Tab eventKey="details" title="Görev Detayları">
                    <div className="px-3 py-3">
                      {selectedTask ? (
                        <div>
                          <h4>{selectedTask.name}</h4>
                          <p className="text-muted">{selectedTask.description}</p>
                          
                          <div className="mb-3">
                            <h6>Komut:</h6>
                            <pre className="bg-light p-2 rounded">{selectedTask.command}</pre>
                          </div>
                          
                          <div className="mb-3">
                            <h6>Durum:</h6>
                            <div className="d-flex align-items-center">
                              {getStatusIcon(selectedTask.status)}
                              <span className="ms-2">
                                {selectedTask.status === 'completed' && 'Tamamlandı'}
                                {selectedTask.status === 'failed' && 'Başarısız'}
                                {selectedTask.status === 'running' && 'Çalışıyor'}
                                {selectedTask.status === 'pending' && 'Bekliyor'}
                                {selectedTask.status === 'paused' && 'Duraklatıldı'}
                                {selectedTask.status === 'skipped' && 'Atlandı'}
                              </span>
                            </div>
                          </div>
                          
                          {(selectedTask.status === 'completed' || selectedTask.status === 'failed') && (
                            <div className="mb-3">
                              <div className="d-flex justify-content-between align-items-center mb-2">
                                <h6 className="mb-0">Çıktı:</h6>
                                <Button 
                                  variant="link" 
                                  size="sm" 
                                  onClick={() => toggleOutput(selectedTask.id)}
                                  className="p-0"
                                >
                                  {showOutput[selectedTask.id] ? (
                                    <><EyeOff size={14} className="me-1" /> Gizle</>
                                  ) : (
                                    <><Eye size={14} className="me-1" /> Göster</>
                                  )}
                                </Button>
                              </div>
                              
                              {showOutput[selectedTask.id] && (
                                <pre className="bg-dark text-light p-2 rounded small" style={{ maxHeight: '300px', overflow: 'auto' }}>
                                  {taskOutput[selectedTask.id] || selectedTask.output || 'Çıktı yok'}
                                </pre>
                              )}
                            </div>
                          )}
                          
                          {selectedTask.dependencies && selectedTask.dependencies.length > 0 && (
                            <div className="mb-3">
                              <h6>Bağımlılıklar:</h6>
                              <ul className="list-group">
                                {selectedTask.dependencies.map(depIndex => {
                                  const depTask = tasks[depIndex];
                                  return depTask ? (
                                    <li key={depIndex} className="list-group-item d-flex justify-content-between align-items-center">
                                      {depTask.name}
                                      <span>
                                        {getStatusIcon(depTask.status)}
                                      </span>
                                    </li>
                                  ) : null;
                                })}
                              </ul>
                            </div>
                          )}
                          
                          {selectedTask.startTime && (
                            <div className="small text-muted">
                              <div>Başlangıç: {new Date(selectedTask.startTime).toLocaleTimeString()}</div>
                              {selectedTask.endTime && (
                                <>
                                  <div>Bitiş: {new Date(selectedTask.endTime).toLocaleTimeString()}</div>
                                  <div>Süre: {((selectedTask.endTime - selectedTask.startTime) / 1000).toFixed(2)} saniye</div>
                                </>
                              )}
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="text-center py-5 text-muted">
                          <Info size={48} className="mb-3" />
                          <h5>Görev seçilmedi</h5>
                          <p>Detayları görüntülemek için görev listesinden bir görev seçin.</p>
                        </div>
                      )}
                    </div>
                  </Tab>
                  
                  <Tab eventKey="logs" title="Log Kayıtları">
                    <div className="d-flex justify-content-between px-3 py-2">
                      <h6 className="mb-0">İşlem Kayıtları</h6>
                      
                      <Button 
                        variant="link" 
                        className="p-0 text-dark" 
                        onClick={downloadLog}
                        disabled={logEntries.length === 0}
                      >
                        <Download size={16} />
                      </Button>
                    </div>
                    
                    <div 
                      ref={logRef} 
                      className="px-3 py-2" 
                      style={{ 
                        maxHeight: '300px', 
                        overflowY: 'auto',
                        fontSize: '0.85rem',
                        fontFamily: 'monospace'
                      }}
                    >
                      {logEntries.length === 0 ? (
                        <div className="text-center text-muted py-4">
                          Log kayıtları burada görünecek
                        </div>
                      ) : (
                        logEntries.map((entry, index) => (
                          <div 
                            key={index} 
                            className={`log-entry mb-1 ${
                              entry.level === 'ERROR' ? 'text-danger' :
                              entry.level === 'WARNING' ? 'text-warning' :
                              entry.level === 'SUCCESS' ? 'text-success' :
                              'text-secondary'
                            }`}
                          >
                            <small className="me-2 text-muted">
                              {new Date(entry.timestamp).toLocaleTimeString()}
                            </small>
                            <span className="badge me-1" style={{
                              backgroundColor: 
                                entry.level === 'ERROR' ? '#dc3545' :
                                entry.level === 'WARNING' ? '#ffc107' :
                                entry.level === 'SUCCESS' ? '#198754' :
                                '#6c757d'
                            }}>
                              {entry.level}
                            </span>
                            {entry.message}
                          </div>
                        ))
                      )}
                    </div>
                  </Tab>
                </Tabs>
              </Card.Body>
            </Card>
          </div>
        </div>
      </div>
      
      {/* Görev düzenleme modal */}
      <TaskEditModal
        show={showEditModal}
        task={editingTask}
        onHide={() => setShowEditModal(false)}
        onSave={saveEditedTask}
        allTasks={tasks}
      />
      
      {/* LLM ayarları modal */}
      <LlmSettingsModal 
        show={showLlmSettingsModal}
        onHide={() => setShowLlmSettingsModal(false)}
        providers={llmProviders}
        models={llmModels}
        selectedProvider={selectedProvider}
        selectedModel={selectedModel}
        onProviderChange={setSelectedProvider}
        onModelChange={setSelectedModel}
        onApplySettings={applyLlmSettings}
      />
      
      {/* Kullanıcı onay modalı */}
      <Modal show={showUserConfirmModal} onHide={() => setShowUserConfirmModal(false)}>
        <Modal.Header closeButton>
          <Modal.Title>Onay Gerekiyor</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {pendingConfirmation?.message}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => {
              setShowUserConfirmModal(false);
              
              // Hata durumunda çalışmayı durdur
              if (pendingConfirmation?.type === 'taskFailure') {
                setIsRunning(false);
              }
            }}>
              Durdur
            </Button>
            <Button variant="primary" onClick={() => {
              setShowUserConfirmModal(false);
                
              // Hata durumunda devam et
              if (pendingConfirmation?.type === 'taskFailure') {
                // Devam et - zaten varsayılan davranıştır
              }
            }}>
              Devam Et
            </Button>
          </Modal.Footer>
        </Modal>
        
        {/* Hata mesajı */}
        {error && (
          <div className="position-fixed top-0 start-50 translate-middle-x mt-3" style={{ zIndex: 1050 }}>
            <div className="alert alert-danger alert-dismissible fade show">
              <strong>Hata:</strong> {error}
              <button 
                type="button" 
                className="btn-close" 
                onClick={() => setError(null)}
              ></button>
            </div>
          </div>
        )}

        <ReportSummaryModal
          show={showReportModal}
          onHide={() => setShowReportModal(false)}
          tasks={tasks}
          startTime={reportStartTime}
          endTime={reportEndTime}
        />
      </div>
    );
  };
  
  export default TaskRunner;