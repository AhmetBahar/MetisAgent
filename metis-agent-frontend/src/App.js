// src/App.js - Tüm UX iyileştirmeler entegre edilmiş final versiyon
import React, { useState, useEffect, useRef } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Button, Dropdown, Navbar, Nav, Modal } from 'react-bootstrap';
import { 
  Send, Settings, User, LogOut, Info, Clock, Wrench as Tool, 
  Code, Database, Bell, Menu, ChevronLeft, ChevronRight,
  Zap, GitBranch, Save, Users, Terminal, MessageSquare, 
  Activity, Sliders, Trash2
} from 'lucide-react';
import './App.css';

// Bileşenler - Temel
import Login from './pages/Login';
import ToolsPanel from './components/ToolsPanel';
import SettingsPanel from './components/SettingsPanel';
import MemoryPanel from './components/MemoryPanel';

// Geliştirilmiş bileşenler
import ChatMessage from './components/ChatMessage';
import TypingIndicator from './components/TypingIndicator';
import NotificationSystem, { 
  notificationManager,
  useWorkflowNotifications,
  usePersonaNotifications,
  useSystemNotifications 
} from './components/NotificationSystem';

// Persona sistemi
import PersonaContainer from './components/Persona/PersonaContainer';
import { personaRegistry } from './components/Persona/registry';
import PersonaInfoPanel from './components/Persona/PersonaInfoPanel';

// Servisler
import AuthAPI from './services/AuthAPI';
import MemoryAPI from './services/MemoryAPI';
import { personaService } from './services/personaService';
import AgentWebSocketService from './services/AgentWebSocketService';

function App() {
  // Auth state
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  
  // UI state
  const [showSidebar, setShowSidebar] = useState(true);
  const [currentSidePanel, setCurrentSidePanel] = useState(null);
  const [darkMode, setDarkMode] = useState(false);
  
  // Chat state
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [selectedPersona, setSelectedPersona] = useState('assistant');
  const [conversationId, setConversationId] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [availablePersonas, setAvailablePersonas] = useState([]);
  
  // Persona state
  const [personaData, setPersonaData] = useState({});
  const [personaContext, setPersonaContext] = useState({});
  const [showPersonaPanel, setShowPersonaPanel] = useState(false);
  
  // UX Enhancement state
  const [lastPersonaChange, setLastPersonaChange] = useState(null);
  const [welcomeMessageSent, setWelcomeMessageSent] = useState(new Set());
  const [collectedInfo, setCollectedInfo] = useState({});
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [lastSelectedPersona, setLastSelectedPersona] = useState(null);
  
  // Notification hooks
  const workflowNotifications = useWorkflowNotifications();
  const personaNotifications = usePersonaNotifications();
  const systemNotifications = useSystemNotifications();
  
  // Refs
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const [inChatMode, setInChatMode] = useState(true);

  // Persona Hoş Geldin Mesajları
  const welcomeMessages = {
    'social-media': "👋 Merhaba! Sosyal medya içeriği oluşturmak için buradayım. Hangi platform için içerik hazırlamak istiyorsun? (Instagram, Facebook, LinkedIn, Twitter...)",
    'assistant': "Merhaba! Size nasıl yardımcı olabilirim?",
    'developer': "👨‍💻 Merhaba! Kod geliştirme konusunda size yardımcı olabilirim. Hangi proje üzerinde çalışıyorsunuz?",
    'task-executor': "⚡ Görev yöneticisi olarak hizmetinizdeyim. Hangi görevleri otomatikleştirmek istiyorsunuz?"
  };

  // Auth token kontrolü
  useEffect(() => {
    const token = localStorage.getItem('authToken');
    if (token) {
      const userData = JSON.parse(localStorage.getItem('userData') || '{}');
      setUser(userData);
      setIsAuthenticated(true);
      loadUserData();
    }
  }, []);

  // WebSocket bağlantısı - Geliştirilmiş
  useEffect(() => {
    if (isAuthenticated) {
      if (!AgentWebSocketService.isConnected()) {
        console.log('WebSocket bağlantısı başlatılıyor...');
        setConnectionStatus('connecting');
        AgentWebSocketService.connect();
      }
      
      // Event handlers
      const handleConnected = (data) => {
        console.log('WebSocket bağlandı:', data);
        setConnectionStatus('connected');
        systemNotifications.notifyConnection('connected');
        loadPersonas();
      };
      
      const handleInitialState = (data) => {
        console.log('Initial state alındı:', data);
        if (data && data.data && data.data.personas) {
          const incomingPersonas = data.data.personas;
          console.log(`${incomingPersonas.length} persona alındı`);
          
          setAvailablePersonas(incomingPersonas);
          
          // Registry'ye kaydet
          incomingPersonas.forEach(persona => {
            personaRegistry.register({
              id: persona.id,
              name: persona.name,
              description: persona.description,
              icon: persona.icon || 'User',
              capabilities: persona.capabilities || [],
            });
          });
        }
      };
      
      const handleMessageResponse = (data) => {
        console.log('WebSocket yanıtı alındı:', data);
        
        let responseContent = '';
        let contextUpdates = {};
        let workflowUpdate = null;
        let infoUpdates = {};
        
        if (data.response) {
          if (typeof data.response === 'object') {
            // Context updates
            if (data.response.context_updates) {
              contextUpdates = data.response.context_updates;
              setPersonaContext(prev => ({
                ...prev,
                ...contextUpdates
              }));
              
              setCollectedInfo(prev => ({
                ...prev,
                ...contextUpdates
              }));
              
              // Yeni bilgi bildirimi
              Object.entries(contextUpdates).forEach(([key, value]) => {
                if (key !== 'current_step') {
                  workflowNotifications.notifyInfoCollected(
                    formatFieldName(key), 
                    Array.isArray(value) ? value.join(', ') : value
                  );
                }
              });
            }
            
            // Workflow değişikliği
            if (data.response.next_step || data.response.workflow_step) {
              const nextStep = data.response.next_step || data.response.workflow_step;
              const previousStep = personaContext.current_step || 'briefing';
              
              workflowUpdate = {
                previous: previousStep,
                current: nextStep,
                message: `İş akışı "${nextStep}" adımına güncellendi`
              };
              
              setPersonaContext(prev => ({
                ...prev,
                current_step: nextStep
              }));
              
              // Workflow değişiklik bildirimi
              const personaName = availablePersonas.find(p => p.id === data.persona_id)?.name || 'Persona';
              workflowNotifications.notifyStepChange(previousStep, nextStep, personaName);
            }
            
            responseContent = JSON.stringify(data.response);
          } else {
            responseContent = data.response;
          }
        } else if (data.error) {
          responseContent = data.error;
          systemNotifications.notifyError('Mesaj Hatası', data.error);
        } else {
          responseContent = 'Yanıt alınamadı';
        }
        
        // Mesajı ekle
        const agentMessage = {
          id: `msg-${Date.now()}`,
          sender: data.persona_id || 'assistant',
          content: responseContent,
          timestamp: new Date().toISOString(),
          workflow_update: workflowUpdate,
          info_updates: infoUpdates,
          isPersonaSpecific: true,
          personaId: data.persona_id || 'assistant'
        };
        
        setMessages(prev => [...prev, agentMessage]);
        setIsProcessing(false);
        
        // Persona yanıt bildirimi
        const personaName = availablePersonas.find(p => p.id === data.persona_id)?.name || 'Persona';
        personaNotifications.notifyPersonaResponse(personaName);
      };
      
      const handlePersonaStatus = (data) => {
        console.log('Persona durumu güncellendi:', data);
        // Persona durumu bildirimleri burada eklenebilir
      };
      
      const handleError = (data) => {
        console.error('WebSocket hatası:', data);
        setIsProcessing(false);
        setConnectionStatus('error');
        
        const errorMessage = {
          id: `msg-${Date.now()}`,
          sender: 'system',
          content: `Hata: ${data.message || 'Bilinmeyen hata'}`,
          timestamp: new Date().toISOString(),
          type: 'error'
        };
        
        setMessages(prev => [...prev, errorMessage]);
        systemNotifications.notifyError('Bağlantı Hatası', data.message || 'Bilinmeyen hata');
      };
      
      const handleDisconnected = () => {
        setConnectionStatus('disconnected');
        systemNotifications.notifyConnection('disconnected');
      };
      
      // Event listeners
      AgentWebSocketService.on('connected', handleConnected);
      AgentWebSocketService.on('initial_state', handleInitialState);
      AgentWebSocketService.on('message_response', handleMessageResponse);
      AgentWebSocketService.on('persona_status_update', handlePersonaStatus);
      AgentWebSocketService.on('error', handleError);
      AgentWebSocketService.on('disconnected', handleDisconnected);
      
      return () => {
        AgentWebSocketService.off('connected', handleConnected);
        AgentWebSocketService.off('initial_state', handleInitialState);
        AgentWebSocketService.off('message_response', handleMessageResponse);
        AgentWebSocketService.off('persona_status_update', handlePersonaStatus);
        AgentWebSocketService.off('error', handleError);
        AgentWebSocketService.off('disconnected', handleDisconnected);
      };
    }
  }, [isAuthenticated, availablePersonas, personaContext]);
  
  // Persona değişikliği - Otomatik hoş geldin mesajı
  useEffect(() => {
    if (selectedPersona && !welcomeMessageSent.has(selectedPersona) && availablePersonas.length > 0) {
      const timer = setTimeout(() => {
        sendWelcomeMessage(selectedPersona);
        setWelcomeMessageSent(prev => new Set([...prev, selectedPersona]));
      }, 500);
      
      return () => clearTimeout(timer);
    }
  }, [selectedPersona, availablePersonas]);
  
  // Dark mode
  useEffect(() => {
    if (darkMode) {
      document.body.classList.add('dark-theme');
    } else {
      document.body.classList.remove('dark-theme');
    }
  }, [darkMode]);
  
  // Auto scroll
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Responsive handling
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 768) {
        setShowSidebar(false);
        if (showPersonaPanel) {
          setShowPersonaPanel(false);
        }
      }
    };
    
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [showPersonaPanel]);
  
  // Hoş geldin mesajı gönder
  const sendWelcomeMessage = (personaId) => {
    const welcomeText = welcomeMessages[personaId] || welcomeMessages['assistant'];
    const persona = availablePersonas.find(p => p.id === personaId);
    
    const welcomeMessage = {
      id: `welcome-${Date.now()}`,
      sender: personaId,
      content: welcomeText,
      timestamp: new Date().toISOString(),
      type: 'welcome',
      isWelcome: true,
      personaId: personaId
    };
    
    setMessages(prev => [...prev, welcomeMessage]);
    
    // Persona aktivasyon bildirimi
    if (persona) {
      personaNotifications.notifyPersonaOnline(persona.name);
    }
  };
  
  // Kullanıcı verilerini yükle
  const loadUserData = async () => {
    try {
      const response = await MemoryAPI.retrieveMemories(null, 'conversation', [], 20);
      const conversationsResult = response.data;
      
      if (conversationsResult.status === 'success') {
        setConversations(conversationsResult.memories || []);
      }
      
      if (user?.username) {
        await MemoryAPI.setUser(user.username);
      }
    } catch (error) {
      console.error('Kullanıcı verileri yüklenirken hata:', error);
    }
  };
  
  // Personaları yükle
  const loadPersonas = async () => {
    try {
      const result = await personaService.getPersonas();
      const response = result.data;
      
      if (response.status === 'success') {
        console.log('Backend API\'dan personalar yüklendi:', response.personas.length);
        setAvailablePersonas(response.personas);
        
        response.personas.forEach(persona => {
          if (!personaRegistry.hasPlugin(persona.id)) {
            personaRegistry.register({
              id: persona.id,
              name: persona.name,
              description: persona.description,
              icon: persona.icon || 'User',
              capabilities: persona.capabilities || [],
              component: null
            });
          }
        });
      }
    } catch (error) {
      console.error('Personalar yüklenirken hata:', error);
      systemNotifications.notifyError('Persona Yükleme Hatası', error.message);
    }
  };
  
  // Persona verilerini yükle
  const loadPersonaData = async (personaId) => {
    if (!personaId) return;
    
    try {
      console.log(`${personaId} persona verileri yükleniyor`);
      
      const personaResult = await personaService.getPersona(personaId);
      const personaResponse = personaResult.data;
      
      if (personaResponse.status === 'success' && personaResponse.persona) {
        console.log('Persona bilgileri başarıyla alındı:', personaResponse.persona);
        
        setPersonaData({
          ...personaResponse.persona,
          workflow_steps: personaResponse.persona.workflow_steps || [],
          current_step: personaResponse.persona.current_step || 'briefing'
        });
        
        try {
          const result = await personaService.getPersonaData(personaId);
          const response = result.data;
          
          if (response.status === 'success') {
            console.log('Persona context verileri alındı:', response);
            setPersonaContext(response.context || {});
          }
        } catch (contextError) {
          console.warn('Persona context bilgileri alınamadı:', contextError);
          setPersonaContext({});
        }
      } else {
        console.warn(`Persona bilgileri alınamadı: ${personaId}`);
        setPersonaData({});
        setPersonaContext({});
      }
    } catch (error) {
      console.error(`Persona verileri yüklenemedi: ${personaId}`, error);
      setPersonaData({});
      setPersonaContext({});
    }
  };
  
  // Persona değişikliğini izle
  useEffect(() => {
    if (selectedPersona) {
      setCollectedInfo({});
      setPersonaContext({});
      
      loadPersonaData(selectedPersona);
      setLastPersonaChange(Date.now());
    }
  }, [selectedPersona]);
  
  // Login işlemi
  const handleLogin = async (loginData) => {
    try {
      console.log('Login attempting with:', { username: loginData.username });
      
      if (loginData.response && loginData.response.status === 'success') {
        const result = loginData.response;
        
        setUser({
          id: loginData.username,
          name: loginData.username,
          email: `${loginData.username}@example.com`,
          ...result.user
        });
        setIsAuthenticated(true);
        
        if (result.token) {
          localStorage.setItem('authToken', result.token);
        }
        localStorage.setItem('userData', JSON.stringify(result.user || {}));
        
        loadUserData();
        notificationManager.success('Giriş Başarılı', `Hoş geldiniz, ${loginData.username}!`);
      } else {
        const response = await AuthAPI.login(loginData.username, loginData.password);
        console.log('Login response:', response);
        
        const result = response.data;
        
        if (result.status === 'success') {
          setUser({
            id: loginData.username,
            name: loginData.username,
            email: `${loginData.username}@example.com`,
            ...result.user
          });
          setIsAuthenticated(true);
          
          if (result.token) {
            localStorage.setItem('authToken', result.token);
          }
          localStorage.setItem('userData', JSON.stringify(result.user || {}));
          
          loadUserData();
          notificationManager.success('Giriş Başarılı', `Hoş geldiniz, ${loginData.username}!`);
        } else {
          throw new Error(result.message || 'Giriş başarısız');
        }
      }
    } catch (error) {
      console.error('Login hatası detayları:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status
      });
      
      const errorMessage = error.response?.data?.message || error.message || 'Giriş başarısız';
      systemNotifications.notifyError('Giriş Hatası', errorMessage);
      throw new Error(errorMessage);
    }
  };
  
  // Logout işlemi
  const handleLogout = () => {
    AgentWebSocketService.disconnect();
    
    setUser(null);
    setIsAuthenticated(false);
    setMessages([]);
    setConversationId(null);
    setConversations([]);
    setCollectedInfo({});
    setPersonaContext({});
    setWelcomeMessageSent(new Set());
    setConnectionStatus('disconnected');
    setLastSelectedPersona(null);
    
    localStorage.removeItem('authToken');
    localStorage.removeItem('userData');
    
    notificationManager.info('Çıkış Yapıldı', 'Güvenli bir şekilde çıkış yaptınız');
  };

  // Chat temizleme fonksiyonu
  const clearChatHistory = () => {
    setMessages([]);
    setCollectedInfo({});
    setPersonaContext({});
    setWelcomeMessageSent(new Set());
    
    // Current persona için welcome mesajını tekrar gönder
    if (selectedPersona) {
      setTimeout(() => {
        sendWelcomeMessage(selectedPersona);
        setWelcomeMessageSent(prev => new Set([...prev, selectedPersona]));
      }, 300);
    }
    
    notificationManager.success('Chat Temizlendi', 'Konuşma geçmişi temizlendi');
  };
  
  // Yeni konuşma başlat
  const startNewConversation = async () => {
    const newConversationId = `conv-${Date.now()}`;
    setMessages([]);
    setConversationId(newConversationId);
    setSelectedPersona('assistant');
    setCollectedInfo({});
    setPersonaContext({});
    setWelcomeMessageSent(new Set());
    setLastSelectedPersona(null);
    
    try {
      await MemoryAPI.store({
        content: JSON.stringify({
          id: newConversationId,
          title: 'Yeni Konuşma',
          timestamp: new Date().toISOString(),
          lastMessage: ''
        }),
        category: 'conversation',
        tags: ['chat', 'new']
      });
      
      loadUserData();
      notificationManager.info('Yeni Konuşma', 'Yeni konuşma başlatıldı');
    } catch (error) {
      console.error('Konuşma kaydedilemedi:', error);
    }
  };
  
  // Persona seçimi değiştiğinde - İyileştirilmiş
  const handlePersonaChange = (newPersonaId) => {
    // Eğer farklı bir persona seçildiyse chat'i temizle
    if (lastSelectedPersona && lastSelectedPersona !== newPersonaId) {
      // Welcome mesajları ve persona-specific mesajları temizle
      setMessages(prev => prev.filter(msg => 
        msg.type !== 'welcome' && 
        !msg.isPersonaSpecific &&
        msg.sender === 'user' // Sadece user mesajlarını sakla
      ));
      
      // Context'leri resetle
      setCollectedInfo({});
      setPersonaContext({});
      setWelcomeMessageSent(new Set());
      
      // Notification göster
      const newPersona = availablePersonas.find(p => p.id === newPersonaId);
      if (newPersona) {
        notificationManager.info(
          'Persona Değiştirildi', 
          `${newPersona.name} personasına geçildi - Chat geçmişi temizlendi`
        );
      }
    }

    setSelectedPersona(newPersonaId);
    setLastSelectedPersona(newPersonaId);
    
    if (!showPersonaPanel && newPersonaId !== 'assistant') {
      setShowPersonaPanel(true);
    }
    
    const persona = availablePersonas.find(p => p.id === newPersonaId);
    if (persona && (!lastSelectedPersona || lastSelectedPersona === newPersonaId)) {
      notificationManager.info('Persona Seçildi', `${persona.name} aktif`);
    }
  };
  
  // Mesaj gönder
  const sendMessage = async () => {
    if (!inputValue.trim()) return;
    
    const userMessage = {
      id: `msg-${Date.now()}`,
      sender: 'user',
      content: inputValue,
      timestamp: new Date().toISOString(),
      isPersonaSpecific: true,
      personaId: selectedPersona
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsProcessing(true);
    
    try {
      console.log('Mesaj gönderiliyor:', { persona: selectedPersona, message: inputValue });
      AgentWebSocketService.sendMessage(selectedPersona, inputValue);
    } catch (error) {
      console.error('Mesaj gönderme hatası:', error);
      setIsProcessing(false);
      
      const errorMessage = {
        id: `msg-${Date.now()}`,
        sender: 'system',
        content: `Hata: ${error.message || 'Mesaj gönderilemedi'}`,
        timestamp: new Date().toISOString(),
        type: 'error'
      };
      
      setMessages(prev => [...prev, errorMessage]);
      systemNotifications.notifyError('Mesaj Gönderme Hatası', error.message || 'Mesaj gönderilemedi');
    }
  };
  
  // Hızlı eylem işleyici
  const handleQuickAction = (action) => {
    console.log('Hızlı eylem:', action);
    
    if (action.action === 'preview_post') {
      notificationManager.info('Post Önizleme', 'Post önizlemesi hazırlanıyor...');
      setInputValue('Mevcut post bilgilerini özetle ve önizleme göster');
    } else if (action.action === 'suggest_hashtags') {
      setInputValue('Bu içerik için en uygun hashtagleri öner');
    } else if (action.action === 'create_visual') {
      setInputValue('Bu post için görsel oluşturma önerilerini ver');
    } else {
      setInputValue(action.label);
    }
  };
  
  
  
  // Mesaj geri bildirimi - İyileştirilmiş
  const handleMessageFeedback = (messageId, feedbackType) => {
    console.log('Mesaj geri bildirimi:', { messageId, feedbackType });
    
    const message = messages.find(msg => msg.id === messageId);
    const feedbackMessage = feedbackType === 'positive' ? 
      '👍 Olumlu geri bildirim alındı' : 
      '👎 Geri bildirim alındı, iyileştireceğiz';
      
    notificationManager.success('Geri Bildirim', feedbackMessage);
    
    // Message'a feedback işareti ekle
    setMessages(prev => 
      prev.map(msg => 
        msg.id === messageId 
          ? { ...msg, feedback: feedbackType, feedbackTime: Date.now() }
          : msg
      )
    );
  };
  
  // Dosya yükleme
  const handleFileUpload = async (e) => {
    const files = e.target.files;
    if (files.length > 0) {
      const file = files[0];
      
      const fileMessage = {
        id: `msg-${Date.now()}`,
        sender: 'system',
        content: `"${file.name}" dosyası yüklendi (${(file.size / 1024).toFixed(1)} KB)`,
        timestamp: new Date().toISOString(),
        files: [{name: file.name, size: file.size}]
      };
      
      setMessages(prev => [...prev, fileMessage]);
      notificationManager.success('Dosya Yüklendi', `${file.name} başarıyla yüklendi`);
    }
  };
  
  // Enter tuşu ile mesaj gönderme - Geliştirilmiş
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
    
    // Keyboard shortcuts
    if (e.key === 'Escape') {
      if (showPersonaPanel) {
        setShowPersonaPanel(false);
      } else if (currentSidePanel) {
        setCurrentSidePanel(null);
      }
    }
    
    // Ctrl+/ ile quick commands
    if (e.ctrlKey && e.key === '/') {
      e.preventDefault();
      setInputValue('/help ');
    }
    
    // Ctrl+L ile chat temizleme
    if (e.ctrlKey && e.key === 'l') {
      e.preventDefault();
      clearChatHistory();
    }
  };
  
  // Persona panel toggle
  const togglePersonaPanel = () => {
    setShowPersonaPanel(!showPersonaPanel);
  };
  
  // Alan adı formatlama
  const formatFieldName = (key) => {
    const fieldNames = {
      platform: 'Platform',
      target_audience: 'Hedef Kitle',
      main_message: 'Ana Mesaj',
      post_type: 'İçerik Türü',
      tone: 'Ton',
      content_theme: 'Tema',
      visual_ideas: 'Görsel Fikirler',
      hashtags: 'Hashtagler',
      caption: 'Paylaşım Metni'
    };
    
    return fieldNames[key] || key;
  };
  
  // Eğer login değilse, login sayfasını göster
  if (!isAuthenticated) {
    return <Login onLogin={handleLogin} />;
  }
  
  return (
    <div className={`app-container ${darkMode ? 'dark-theme' : ''}`}>
      {/* Notification System */}
      <NotificationSystem position="top-end" />
      
      {/* Top Navbar */}
      <Navbar className="app-navbar" expand="lg">
        <div className="d-flex align-items-center">
          <Button 
            variant="transparent" 
            className="sidebar-toggle me-2"
            onClick={() => setShowSidebar(!showSidebar)}
          >
            <Menu size={20} />
          </Button>
          <Navbar.Brand className="d-flex align-items-center">
            <img 
              src="/logo192.png" 
              height="30" 
              className="me-2" 
              alt="Metis Agent" 
            />
            <span>Metis Agent</span>
          </Navbar.Brand>
        </div>
        
        {/* Persona Seçim Butonları */}
        <div className="persona-selector d-flex flex-wrap mb-2">
          {availablePersonas.map(persona => (
            <div 
              key={persona.id}
              className={`persona-avatar ${selectedPersona === persona.id ? 'active' : ''}`}
              onClick={() => handlePersonaChange(persona.id)}
              title={persona.name}
            >
              <span className="avatar-initial">
                {persona.name?.charAt(0) || persona.id.charAt(0)}
              </span>
            </div>
          ))}
        </div>
        
        <div className="ms-auto d-flex align-items-center">
          {/* Connection Status - İyileştirilmiş */}
          <div className={`connection-status me-2 ${connectionStatus}`} title={`WebSocket: ${connectionStatus}`}>
            <div className="d-flex align-items-center">
              <div className={`status-dot ${connectionStatus}`}></div>
              <span className="status-text ms-1 d-none d-lg-inline">
                {connectionStatus === 'connected' ? 'Bağlı' : 
                 connectionStatus === 'connecting' ? 'Bağlanıyor...' :
                 connectionStatus === 'reconnecting' ? 'Yeniden bağlanıyor...' :
                 connectionStatus === 'error' ? 'Hata' : 'Bağlantısız'}
              </span>
            </div>
          </div>

          {/* Chat Clear Button */}
          <Button 
            variant="outline-warning" 
            className="me-2"
            onClick={clearChatHistory}
            title="Chat geçmişini temizle (Ctrl+L)"
          >
            <Trash2 size={16} className="me-1" />
            <span className="d-none d-md-inline">Temizle</span>
          </Button>
          
          {/* Persona Panel Toggle Button */}
          <Button 
            variant={showPersonaPanel ? 'primary' : 'outline-secondary'} 
            className="me-2"
            onClick={togglePersonaPanel}
          >
            <Users size={16} className="me-1" />
            <span className="d-none d-md-inline">Persona Paneli</span>
          </Button>
          
          {/* Memory Button */}
          <Button 
            variant={currentSidePanel === 'memory' ? 'primary' : 'outline-secondary'} 
            className="me-2"
            onClick={() => setCurrentSidePanel(currentSidePanel === 'memory' ? null : 'memory')}
          >
            <Clock size={16} className="me-1" />
            <span className="d-none d-md-inline">Bellek</span>
          </Button>
          
          {/* Tools Button */}
          <Button 
            variant={currentSidePanel === 'tools' ? 'primary' : 'outline-primary'} 
            className="me-2"
            onClick={() => setCurrentSidePanel(currentSidePanel === 'tools' ? null : 'tools')}
          >
            <Tool size={16} className="me-1" />
            <span className="d-none d-md-inline">Araçlar</span>
          </Button>
          
          {/* Settings Button */}
          <Button 
            variant={currentSidePanel === 'settings' ? 'primary' : 'outline-secondary'} 
            className="me-2"
            onClick={() => setCurrentSidePanel(currentSidePanel === 'settings' ? null : 'settings')}
          >
            <Settings size={16} className="me-1" />
            <span className="d-none d-md-inline">Ayarlar</span>
          </Button>
          
          {/* Notifications */}
          <Dropdown align="end" className="me-2">
            <Dropdown.Toggle variant="outline-secondary" id="notification-dropdown">
              <Bell size={16} />
            </Dropdown.Toggle>
            
            <Dropdown.Menu>
              <Dropdown.Header>Bildirimler</Dropdown.Header>
              <Dropdown.Item>Yeni özellikler eklendi</Dropdown.Item>
              <Dropdown.Item>Sistem güncellemesi mevcut</Dropdown.Item>
              <Dropdown.Divider />
              <Dropdown.Item className="text-center">Tümünü Gör</Dropdown.Item>
            </Dropdown.Menu>
          </Dropdown>
          
          {/* User Menu */}
          <Dropdown align="end">
            <Dropdown.Toggle variant="outline-secondary" id="user-dropdown">
              <User size={16} className="me-1" />
              <span className="d-none d-md-inline">{user?.name}</span>
            </Dropdown.Toggle>
            
            <Dropdown.Menu>
              <Dropdown.Header>{user?.email}</Dropdown.Header>
              <Dropdown.Item>
                <User size={14} className="me-2" />
                Profil
              </Dropdown.Item>
              <Dropdown.Item onClick={() => setDarkMode(!darkMode)}>
                {darkMode ? '☀️ Açık Tema' : '🌙 Koyu Tema'}
              </Dropdown.Item>
              <Dropdown.Divider />
              <Dropdown.Item onClick={handleLogout}>
                <LogOut size={14} className="me-2" />
                Çıkış Yap
              </Dropdown.Item>
            </Dropdown.Menu>
          </Dropdown>
        </div>
      </Navbar>
      
      <div className="app-content">
        {/* Left Sidebar - Conversations */}
        <div className={`conversations-sidebar ${showSidebar ? 'show' : 'hide'}`}>
          <div className="p-3">
            <Button 
              variant="primary" 
              className="w-100 mb-3"
              onClick={startNewConversation}
            >
              <MessageSquare size={16} className="me-2" />
              Yeni Konuşma
            </Button>
            
            <div className="conversations-list">
              {conversations.map(conv => {
                const convData = typeof conv.content === 'string' 
                  ? JSON.parse(conv.content) 
                  : conv.content;
                
                return (
                  <div 
                    key={convData.id} 
                    className={`conversation-item ${conversationId === convData.id ? 'active' : ''}`}
                    onClick={() => {/* selectConversation logic */}}
                  >
                    <div className="conversation-icon">
                      <MessageSquare size={16} />
                    </div>
                    <div className="conversation-details">
                      <div className="conversation-title">{convData.title}</div>
                      <div className="conversation-preview">{convData.lastMessage}</div>
                    </div>
                    <div className="conversation-time">
                      {new Date(convData.timestamp).toLocaleDateString()}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
        
        {/* Main Chat Area */}
        <div className="chat-area">
          {/* Chat Messages */}
          <div className={`chat-messages ${showPersonaPanel ? 'persona-panel-open' : ''} ${window.innerWidth < 768 ? 'mobile-view' : ''}`}>
            {messages.length === 0 ? (
              <div className="welcome-screen">
                <img src="/logo192.png" className="welcome-logo" alt="Metis Agent" />
                <h2>Metis Agent'a Hoş Geldiniz</h2>
                <p>Size nasıl yardımcı olabilirim?</p>
                <div className="suggestion-buttons">
                  <Button variant="outline-primary" onClick={() => setInputValue("Sosyal medya içeriği oluştur")}>
                    Sosyal Medya İçeriği Oluştur
                  </Button>
                  <Button variant="outline-primary" onClick={() => setInputValue("Kod geliştirme görevi oluştur")}>
                    Kod Geliştirme Görevi Oluştur
                  </Button>
                  <Button variant="outline-primary" onClick={() => setInputValue("Sistem durumunu kontrol et")}>
                    Sistem Durumunu Kontrol Et
                  </Button>
                </div>
              </div>
            ) : (
              <>
                {messages.map(message => (
                  <ChatMessage 
                    key={message.id}
                    message={message}
                    user={user}
                    isPersonaMessage={message.sender !== 'user' && message.sender !== 'system'}
                    personaInfo={availablePersonas.find(p => p.id === message.sender)}
                    onQuickAction={handleQuickAction}
                    onFeedback={handleMessageFeedback}
                  />
                ))}
                
                {/* Typing Indicator */}
                {isProcessing && (
                  <TypingIndicator 
                    persona={availablePersonas.find(p => p.id === selectedPersona)}
                    messages={
                      selectedPersona === 'social-media' ? [
                        "Yaratıcı fikir hazırlanıyor...",
                        "İçerik geliştiriliyor...", 
                        "Post taslağı oluşturuluyor...",
                        "Hashtag önerileri üretiliyor...",
                        "Görsel konsepti tasarlanıyor..."
                      ] : [
                        "Düşünüyorum...",
                        "Analiz ediyorum...",
                        "Yanıt hazırlanıyor..."
                      ]
                    }
                  />
                )}
              </>
            )}
            <div ref={messagesEndRef} />
          </div>
          
          {/* Persona Panel */}
          {showPersonaPanel && (
            <div className="persona-panel">
              <PersonaInfoPanel
                persona={availablePersonas.find(p => p.id === selectedPersona)}
                context={personaContext}
                workflowSteps={personaData?.workflow_steps || []}
                currentStep={personaContext?.current_step || personaData?.current_step || 'briefing'}
                collectedInfo={collectedInfo}
              />
            </div>
          )}
          
          
          {/* Input Area */}
          <div className="chat-input-area">
            <div className="chat-input-container">
              <textarea
                className="chat-input"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Bir mesaj yazın veya komut gönderin... (Ctrl+L: temizle, Ctrl+/: komutlar)"
                rows={1}
              />
              
              <div className="chat-input-buttons">
                <Button 
                  variant="light" 
                  className="upload-button"
                  onClick={() => fileInputRef.current.click()}
                >
                  <i className="bi bi-paperclip"></i>
                </Button>
                <input 
                  type="file" 
                  hidden 
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                />
                
                <Button 
                  variant="primary" 
                  className="send-button"
                  onClick={sendMessage}
                  disabled={!inputValue.trim() || isProcessing}
                >
                  {isProcessing ? (
                    <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                  ) : (
                    <Send size={16} />
                  )}
                </Button>
              </div>
            </div>
            
            <div className="chat-footer">
              <div className="chat-footer-info">
                <small>
                  Metis Agent, doğal dil işleme ile çalışan bir yardımcıdır. 
                  <a href="#" className="ms-1">Daha fazla bilgi</a>
                </small>
              </div>
            </div>
          </div>
        </div>
        
        {/* Right Side Panel */}
        {currentSidePanel && (
          <div className="side-panel">
            <div className="side-panel-header">
              <h4>
                {currentSidePanel === 'tools' && (
                  <>
                    <Tool size={18} className="me-2" />
                    Araçlar
                  </>
                )}
                {currentSidePanel === 'settings' && (
                  <>
                    <Settings size={18} className="me-2" />
                    Ayarlar
                  </>
                )}
                {currentSidePanel === 'memory' && (
                  <>
                    <Clock size={18} className="me-2" />
                    Bellek & Geçmiş
                  </>
                )}
              </h4>
              <Button 
                variant="transparent" 
                className="side-panel-close"
                onClick={() => setCurrentSidePanel(null)}
              >
                <ChevronRight size={20} />
              </Button>
            </div>
            
            <div className="side-panel-content">
              {currentSidePanel === 'tools' && <ToolsPanel />}
              {currentSidePanel === 'settings' && <SettingsPanel />}
              {currentSidePanel === 'memory' && <MemoryPanel />}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;