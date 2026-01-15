/**
 * AuthButton - Google OAuth giriş/çıkış butonu
 */

import React, { useState, useEffect } from 'react';
import authService from '../services/authService';
import './AuthButton.css';

const AuthButton = () => {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        checkAuthStatus();
        
        // URL'den login success/error parametrelerini kontrol et
        const urlParams = new URLSearchParams(window.location.search);
        const loginStatus = urlParams.get('login');
        const error = urlParams.get('error');
        
        if (loginStatus === 'success') {
            // Login başarılı, sayfa yenile
            window.history.replaceState({}, document.title, window.location.pathname);
            checkAuthStatus();
        } else if (error) {
            // Hata mesajı göster
            console.error('Login error:', error);
            alert('Giriş sırasında hata oluştu: ' + error);
            window.history.replaceState({}, document.title, window.location.pathname);
        }
    }, []);

    const checkAuthStatus = async () => {
        try {
            setLoading(true);
            const status = await authService.checkAuthStatus();
            setIsAuthenticated(status.authenticated || false);
            
            if (status.authenticated) {
                await loadUserProfile();
            }
        } catch (error) {
            console.error('Auth status kontrol hatası:', error);
            setIsAuthenticated(false);
            setUser(null);
        } finally {
            setLoading(false);
        }
    };

    const loadUserProfile = async () => {
        try {
            const profile = await authService.loadUserProfile();
            setUser(profile);
        } catch (error) {
            console.error('Profil yükleme hatası:', error);
        }
    };

    const handleLogin = async () => {
        try {
            setLoading(true);
            await authService.loginWithGoogle();
        } catch (error) {
            console.error('Login hatası:', error);
            alert('Giriş sırasında hata oluştu: ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    const handleLogout = async () => {
        try {
            setLoading(true);
            await authService.logout();
            setIsAuthenticated(false);
            setUser(null);
            
            // Tüm session ve cache'i temizle
            sessionStorage.clear();
            localStorage.clear();
            
            // Login sayfasına yönlendir (sayfa yenileme yerine)
            window.location.href = '/login';
        } catch (error) {
            console.error('Logout hatası:', error);
            alert('Çıkış sırasında hata oluştu: ' + error.message);
            
            // Hata durumunda da login sayfasına yönlendir
            window.location.href = '/login';
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="auth-button loading">
                <span>Yükleniyor...</span>
            </div>
        );
    }

    if (isAuthenticated && user) {
        return (
            <div className="auth-button authenticated">
                <div className="user-info">
                    {user.picture && (
                        <img 
                            src={user.picture} 
                            alt={user.name || 'User'} 
                            className="user-avatar"
                        />
                    )}
                    <div className="user-details">
                        <span className="user-name">{user.name || 'Kullanıcı'}</span>
                        <span className="user-email">{user.email}</span>
                    </div>
                </div>
                <button 
                    onClick={handleLogout} 
                    className="logout-btn"
                    disabled={loading}
                >
                    Çıkış
                </button>
            </div>
        );
    }

    return (
        <div className="auth-button unauthenticated">
            <button 
                onClick={handleLogin} 
                className="login-btn google-login"
                disabled={loading}
            >
                <svg className="google-icon" viewBox="0 0 24 24" width="18" height="18">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
                Google ile Giriş Yap
            </button>
        </div>
    );
};

export default AuthButton;