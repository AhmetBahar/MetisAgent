import React, { useState, useEffect } from 'react';
import UnifiedChatInterface from './components/UnifiedChatInterface';
import WorkflowPanel from './components/WorkflowPanel';
import ConversationPanel from './components/ConversationPanel';
import Login from './pages/Login';
import SettingsModal from './components/SettingsModal';
import AuthButton from './components/AuthButton';
import { apiService } from './services/apiService';
import AuthAPI from './services/AuthAPI';
import authService from './services/authService';
import './App.css';

function App() {
  const [isConnected, setIsConnected] = useState(false);
  const [providers, setProviders] = useState([]);
  const [connectionStatus, setConnectionStatus] = useState('connecting');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isConversationPanelOpen, setIsConversationPanelOpen] = useState(false);
  const [currentConversationId, setCurrentConversationId] = useState('default');
  const [selectedProvider, setSelectedProvider] = useState('openai');
  const [selectedModel, setSelectedModel] = useState('gpt-4o-mini');

  useEffect(() => {
    // Google OAuth callback'den session token'ı al
    const urlParams = new URLSearchParams(window.location.search);
    const sessionToken = urlParams.get('token');
    
    if (sessionToken) {
      localStorage.setItem('session_token', sessionToken);
      // URL'den token'ı temizle
      window.history.replaceState({}, document.title, window.location.pathname);
    }
    
    initializeApp();
  }, []);

  // Provider değiştiğinde model'i güncelle
  useEffect(() => {
    if (Array.isArray(providers) && providers.length > 0) {
      const availableProvider = providers.find(p => p.available);
      if (availableProvider) {
        setSelectedProvider(availableProvider.id);
        setSelectedModel(availableProvider.default_model);
      }
    }
  }, [providers]);

  // Provider değiştiğinde default model'i ayarla
  useEffect(() => {
    const provider = Array.isArray(providers) ? providers.find(p => p.id === selectedProvider) : null;
    if (provider && Array.isArray(provider.models) && provider.models.length > 0) {
      setSelectedModel(provider.default_model || provider.models[0]);
    }
  }, [selectedProvider, providers]);

  const initializeApp = async () => {
    setConnectionStatus('connecting');
    setAuthLoading(true);
    
    try {
      // Check if user is already authenticated
      await checkAuthentication();
      
      // Check backend connection
      await checkConnection();
      await loadProviders();
      setConnectionStatus('connected');
    } catch (error) {
      setConnectionStatus('error');
      console.error('App initialization failed:', error);
    } finally {
      setAuthLoading(false);
    }
  };

  const checkAuthentication = async () => {
    try {
      // Hem eski hem yeni auth sistemini kontrol et
      const token = AuthAPI.getStoredToken();
      const userData = AuthAPI.getStoredUser();
      
      if (token && userData) {
        // Eski auth sistemi
        setIsAuthenticated(true);
        setCurrentUser(userData);
        
        try {
          const validation = await AuthAPI.validateSession();
          if (!validation.valid) {
            console.log('Session validation failed, redirecting to login');
            AuthAPI.clearAuth();
            setIsAuthenticated(false);
            setCurrentUser(null);
          }
        } catch (validationError) {
          console.warn('Session validation error (network issue?):', validationError.message);
        }
      } else {
        // Yeni Google OAuth sistemini kontrol et
        try {
          const authStatus = await authService.checkAuthStatus();
          if (authStatus.authenticated) {
            setIsAuthenticated(true);
            setCurrentUser(authStatus.user || { username: authStatus.user_email, email: authStatus.user_email });
          } else {
            setIsAuthenticated(false);
            setCurrentUser(null);
          }
        } catch (error) {
          console.log('Google auth check failed:', error);
          setIsAuthenticated(false);
          setCurrentUser(null);
        }
      }
    } catch (error) {
      console.error('Authentication check failed:', error);
      setIsAuthenticated(false);
      setCurrentUser(null);
    }
  };

  const checkConnection = async () => {
    try {
      await apiService.healthCheck();
      setIsConnected(true);
    } catch (error) {
      setIsConnected(false);
      throw error;
    }
  };

  const loadProviders = async () => {
    try {
      const response = await apiService.getProviders();
      if (response.success) {
        setProviders(response.data); // Backend returns providers directly in data array
      }
    } catch (error) {
      console.error('Failed to load providers:', error);
      throw error;
    }
  };

  const handleLogin = async (authData) => {
    try {
      setIsAuthenticated(true);
      setCurrentUser(authData.user);
      
      // Session token'ı localStorage'a kaydet
      if (authData.session_token) {
        localStorage.setItem('session_token', authData.session_token);
        localStorage.setItem('user_data', JSON.stringify(authData.user));
      }
    } catch (error) {
      console.error('Login handler error:', error);
    }
  };

  const handleLogout = async () => {
    try {
      // Google OAuth logout
      await authService.logout();
      
      // Eski auth system logout
      await AuthAPI.logout();
      
      setIsAuthenticated(false);
      setCurrentUser(null);
      console.log('User logged out');
      
      // Sayfayı yenile
      window.location.reload();
    } catch (error) {
      console.error('Logout error:', error);
      // Clear local data even if logout fails
      setIsAuthenticated(false);
      setCurrentUser(null);
      
      // Sayfayı yenile
      window.location.reload();
    }
  };

  const getConnectionStatusDisplay = () => {
    switch (connectionStatus) {
      case 'connecting':
        return <span className="status-connecting">Connecting...</span>;
      case 'connected':
        return <span className="status-connected">Connected</span>;
      case 'error':
        return <span className="status-error">Connection Error</span>;
      default:
        return <span className="status-disconnected">Disconnected</span>;
    }
  };

  // Show loading screen during auth check
  if (authLoading) {
    return (
      <div className="App">
        <div className="app-container">
          <div className="connection-error">
            <div className="error-content">
              <h2>Loading...</h2>
              <p>Checking authentication...</p>
              <div className="loading-spinner"></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Show login page if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="App">
        <div className="app-container">
          <header className="app-header">
            <div className="header-content">
              <div className="header-left">
                <div className="logo-title">
                  <img src="/MetisAgent.png" alt="MetisAgent" className="app-logo" />
                  <div className="title-text">
                    <h1>Metis Agent</h1>
                    <span className="app-subtitle">AI Assistant with Tool Integration</span>
                  </div>
                </div>
              </div>
              <div className="header-right">
                <AuthButton />
              </div>
            </div>
          </header>
          <main className="app-main">
            <Login onLogin={handleLogin} />
          </main>
        </div>
      </div>
    );
  }

  return (
    <div className="App">
      <div className="app-container">
        <header className="app-header">
          <div className="header-content">
            <div className="header-left">
              <div className="logo-title">
                <img src="/MetisAgent.png" alt="MetisAgent" className="app-logo" />
                <div className="title-text">
                  <h1>Metis Agent</h1>
                  <span className="app-subtitle">AI Assistant with Tool Integration</span>
                </div>
              </div>
            </div>
            <div className="header-right">
              
              {/* Conversations Button */}
              <button 
                className="settings-btn"
                onClick={() => setIsConversationPanelOpen(true)}
                title="Conversation History"
              >
                📚
              </button>

              {/* Settings Button */}
              <button 
                className="settings-btn"
                onClick={() => setIsSettingsOpen(true)}
                title="Settings"
              >
                ⚙️
              </button>
              
              <div className="user-info">
                <span className="welcome-text">Welcome!</span>
                <button 
                  onClick={handleLogout} 
                  className="logout-btn"
                >
                  Logout
                </button>
              </div>
              <div className="connection-indicator">
                <div className={`connection-dot ${connectionStatus}`}></div>
                {getConnectionStatusDisplay()}
              </div>
            </div>
          </div>
        </header>

        <main className="app-main">
          {isConnected ? (
            <div className="chat-layout">
              <div className="chat-section">
                <UnifiedChatInterface 
                  providers={providers} 
                  onConnectionChange={setIsConnected}
                  currentUser={currentUser}
                  selectedProvider={selectedProvider}
                  selectedModel={selectedModel}
                  currentConversationId={currentConversationId}
                />
              </div>
              <div className="workflow-section">
                <WorkflowPanel 
                  isVisible={true}
                  onClose={() => {}}
                  currentUser={currentUser}
                />
              </div>
            </div>
          ) : (
            <div className="connection-error">
              <div className="error-content">
                <h2>Connection Failed</h2>
                <p>Unable to connect to MetisAgent2 backend.</p>
                <button onClick={initializeApp} className="retry-button">
                  Retry Connection
                </button>
              </div>
            </div>
          )}
        </main>
        
        {/* Settings Modal */}
        <SettingsModal 
          isOpen={isSettingsOpen}
          onClose={() => setIsSettingsOpen(false)}
          currentUser={currentUser}
          providers={providers}
          selectedProvider={selectedProvider}
          selectedModel={selectedModel}
          onProviderChange={setSelectedProvider}
          onModelChange={setSelectedModel}
          onRefreshProviders={loadProviders}
        />

        {/* Conversation Panel */}
        <ConversationPanel
          isVisible={isConversationPanelOpen}
          onClose={() => setIsConversationPanelOpen(false)}
          currentUser={currentUser}
          onSelectConversation={(conversationId) => {
            setCurrentConversationId(conversationId);
            setIsConversationPanelOpen(false);
            // TODO: Load selected conversation
          }}
          currentConversationId={currentConversationId}
        />
      </div>
    </div>
  );
}

export default App;