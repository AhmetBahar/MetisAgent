// src/pages/Login.js
import React, { useState } from 'react';
import AuthAPI from '../services/AuthAPI';
import AuthButton from '../components/AuthButton';
import './Login.css';

const Login = ({ onLogin }) => {
  const [activeTab, setActiveTab] = useState('login'); // 'login' veya 'register'
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  
  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
    // Clear errors when user starts typing
    if (error) setError(null);
    if (success) setSuccess(null);
  };
  
  const handleLogin = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await AuthAPI.login(formData.username, formData.password);
      
      if (response.data.success) {
        setSuccess('Giriş başarılı!');

        // Call onLogin callback with user data - this will update App.js state
        if (onLogin) {
          onLogin({
            user: response.data.user,
            session_token: response.data.token
          });
        }
        // No page reload needed - React state handles the transition
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Giriş yapılırken bir hata oluştu');
      console.error('Login error:', err);
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleRegister = async (e) => {
    e.preventDefault();
    
    if (formData.password !== formData.confirmPassword) {
      setError('Şifreler eşleşmiyor');
      return;
    }
    
    if (formData.password.length < 6) {
      setError('Şifre en az 6 karakter olmalıdır');
      return;
    }
    
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await AuthAPI.register(
        formData.username, 
        formData.email, 
        formData.password
      );
      
      if (response.data.status === 'success') {
        setSuccess('Kayıt başarılı! Giriş yapabilirsiniz.');
        
        // Switch to login tab and clear form
        setActiveTab('login');
        setFormData({
          ...formData,
          password: '',
          confirmPassword: ''
        });
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Kayıt olurken bir hata oluştu');
      console.error('Register error:', err);
    } finally {
      setIsLoading(false);
    }
  };
  
  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <div className="logo-section">
            <div className="logo-icon">
              <img src="/MetisAgent.png" alt="MetisAgent" className="metis-logo-login" />
            </div>
            <h1>MetisAgent2</h1>
            <p>Akıllı asistanınıza hoş geldiniz</p>
          </div>
        </div>
        
        <div className="tab-buttons">
          <button 
            className={`tab-button ${activeTab === 'login' ? 'active' : ''}`}
            onClick={() => setActiveTab('login')}
          >
            <span className="tab-icon">🔑</span>
            Giriş
          </button>
          <button 
            className={`tab-button ${activeTab === 'register' ? 'active' : ''}`}
            onClick={() => setActiveTab('register')}
          >
            <span className="tab-icon">👤</span>
            Kayıt
          </button>
        </div>
        
        {error && (
          <div className="alert alert-error">
            <span className="alert-icon">⚠️</span>
            {error}
          </div>
        )}
        
        {success && (
          <div className="alert alert-success">
            <span className="alert-icon">✅</span>
            {success}
          </div>
        )}
        
        {activeTab === 'login' ? (
          <form onSubmit={handleLogin} className="auth-form">
            <div className="form-group">
              <label htmlFor="username">Kullanıcı Adı</label>
              <input
                id="username"
                type="text"
                name="username"
                value={formData.username}
                onChange={handleChange}
                required
                disabled={isLoading}
                placeholder="Kullanıcı adınızı girin"
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="password">Şifre</label>
              <input
                id="password"
                type="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                required
                disabled={isLoading}
                placeholder="Şifrenizi girin"
              />
            </div>
            
            <button 
              type="submit" 
              className="auth-button"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <div className="loading-spinner"></div>
                  Giriş yapılıyor...
                </>
              ) : (
                <>
                  <span className="button-icon">🔓</span>
                  Giriş Yap
                </>
              )}
            </button>
          </form>
        ) : (
          <form onSubmit={handleRegister} className="auth-form">
            <div className="form-group">
              <label htmlFor="reg-username">Kullanıcı Adı</label>
              <input
                id="reg-username"
                type="text"
                name="username"
                value={formData.username}
                onChange={handleChange}
                required
                disabled={isLoading}
                placeholder="Kullanıcı adı seçin"
                minLength="3"
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="email">E-posta</label>
              <input
                id="email"
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                required
                disabled={isLoading}
                placeholder="E-posta adresinizi girin"
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="reg-password">Şifre</label>
              <input
                id="reg-password"
                type="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                required
                disabled={isLoading}
                placeholder="En az 6 karakter"
                minLength="6"
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="confirm-password">Şifre Tekrar</label>
              <input
                id="confirm-password"
                type="password"
                name="confirmPassword"
                value={formData.confirmPassword}
                onChange={handleChange}
                required
                disabled={isLoading}
                placeholder="Şifrenizi tekrar girin"
              />
            </div>
            
            <button 
              type="submit" 
              className="auth-button"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <div className="loading-spinner"></div>
                  Kayıt oluşturuluyor...
                </>
              ) : (
                <>
                  <span className="button-icon">📝</span>
                  Kayıt Ol
                </>
              )}
            </button>
          </form>
        )}
        
        {/* Google OAuth Giriş */}
        <div className="oauth-section">
          <div className="divider">
            <span>veya</span>
          </div>
          <AuthButton />
        </div>
        
        <div className="login-footer">
          <p>Test hesabı: <strong>admin / admin</strong></p>
        </div>
      </div>
    </div>
  );
};

export default Login;