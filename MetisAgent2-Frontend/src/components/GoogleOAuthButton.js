/**
 * GoogleOAuthButton - Gmail authorization için özel OAuth butonu
 * Backend OAuth2 routes ile entegre çalışır
 */

import React, { useState, useEffect } from 'react';
import './AuthButton.css';

const GoogleOAuthButton = ({ onAuthSuccess, onAuthError, userId = null, services = ['gmail'] }) => {
    const [loading, setLoading] = useState(false);
    const [authStatus, setAuthStatus] = useState('checking');
    const [userInfo, setUserInfo] = useState(null);

    // API base URL
    const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:5001';

    useEffect(() => {
        checkOAuthStatus();
    }, [userId]);

    const checkOAuthStatus = async () => {
        if (!userId) {
            setAuthStatus('no_user');
            return;
        }

        try {
            setAuthStatus('checking');
            console.log(`Checking OAuth status for user: ${userId}`);
            
            const response = await fetch(`${API_BASE}/oauth2/google/status?user_id=${userId}`);
            const data = await response.json();
            
            console.log('OAuth status response:', data);
            
            if (data.success && data.data?.authorized) {
                console.log('User is authorized:', data.data.user_info);
                setAuthStatus('authorized');
                setUserInfo(data.data.user_info);
                if (onAuthSuccess) {
                    onAuthSuccess(data.data);
                }
            } else {
                console.log('User not authorized:', data);
                setAuthStatus('unauthorized');
            }
        } catch (error) {
            console.error('OAuth status check error:', error);
            setAuthStatus('error');
        }
    };

    const startOAuthFlow = async () => {
        try {
            setLoading(true);
            
            // OAuth2 flow başlat
            const response = await fetch(`${API_BASE}/oauth2/google/start`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: userId,
                    services: services
                })
            });

            const data = await response.json();
            
            if (data.success) {
                // Check if already authenticated
                if (data.already_authenticated) {
                    console.log('User already authenticated:', data.message);
                    // Force refresh OAuth status
                    await checkOAuthStatus();
                    return;
                }
                
                if (data.auth_url) {
                    // Yeni pencerede OAuth2 URL'ini aç
                    const authWindow = window.open(
                        data.auth_url,
                        'google_oauth',
                        'width=500,height=600,scrollbars=yes,resizable=yes'
                    );

                    // OAuth callback'ini dinle
                    const checkCallback = setInterval(() => {
                        try {
                            if (authWindow.closed) {
                                clearInterval(checkCallback);
                                // Pencere kapandığında status'u tekrar kontrol et
                                setTimeout(() => {
                                    checkOAuthStatus();
                                }, 1000);
                            }
                        } catch (error) {
                            // Cross-origin error, ignore
                        }
                    }, 1000);

                    // 10 dakika sonra timeout
                    setTimeout(() => {
                        clearInterval(checkCallback);
                        if (!authWindow.closed) {
                            authWindow.close();
                        }
                    }, 600000);
                } else {
                    throw new Error('No auth URL provided');
                }
            } else {
                throw new Error(data.error || 'OAuth flow başlatılamadı');
            }
        } catch (error) {
            console.error('OAuth start error:', error);
            if (onAuthError) {
                onAuthError(error.message);
            }
        } finally {
            setLoading(false);
        }
    };

    const revokeOAuth = async () => {
        try {
            setLoading(true);
            
            const response = await fetch(`${API_BASE}/oauth2/google/revoke`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: userId
                })
            });

            const data = await response.json();
            
            if (data.success) {
                setAuthStatus('unauthorized');
                setUserInfo(null);
            } else {
                throw new Error(data.error || 'OAuth iptal edilemedi');
            }
        } catch (error) {
            console.error('OAuth revoke error:', error);
            if (onAuthError) {
                onAuthError(error.message);
            }
        } finally {
            setLoading(false);
        }
    };

    const refreshToken = async () => {
        try {
            setLoading(true);
            
            const response = await fetch(`${API_BASE}/oauth2/google/refresh`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: userId
                })
            });

            const data = await response.json();
            
            if (data.success) {
                setAuthStatus('authorized');
                if (onAuthSuccess) {
                    onAuthSuccess(data.data);
                }
            } else {
                throw new Error(data.error || 'Token yenilenemedi');
            }
        } catch (error) {
            console.error('Token refresh error:', error);
            if (onAuthError) {
                onAuthError(error.message);
            }
        } finally {
            setLoading(false);
        }
    };

    if (!userId) {
        return (
            <div className="auth-button error">
                <span>⚠️ User ID gerekli</span>
            </div>
        );
    }

    if (authStatus === 'checking') {
        return (
            <div className="auth-button loading">
                <span>🔍 OAuth durumu kontrol ediliyor...</span>
            </div>
        );
    }

    if (authStatus === 'authorized' && userInfo) {
        return (
            <div className="auth-button authenticated">
                <div className="oauth-status">
                    <div className="status-indicator success">✅</div>
                    <div className="auth-info">
                        <div className="auth-title">Gmail Bağlantısı Aktif</div>
                        <div className="auth-details">
                            <div className="user-email">{userInfo.email}</div>
                            <div className="user-name">{userInfo.name}</div>
                            <div className="services">Servisler: {services.join(', ')}</div>
                        </div>
                    </div>
                </div>
                <div className="auth-actions">
                    <button 
                        onClick={refreshToken} 
                        className="refresh-btn"
                        disabled={loading}
                    >
                        🔄 Yenile
                    </button>
                    <button 
                        onClick={revokeOAuth} 
                        className="revoke-btn"
                        disabled={loading}
                    >
                        🚫 İptal Et
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="auth-button unauthenticated">
            <div className="oauth-status">
                <div className="status-indicator error">❌</div>
                <div className="auth-info">
                    <div className="auth-title">Gmail Bağlantısı Gerekli</div>
                    <div className="auth-details">
                        <div>Gmail API erişimi için Google hesabınızı bağlayın</div>
                        <div className="services">İstenen servisler: {services.join(', ')}</div>
                    </div>
                </div>
            </div>
            <div className="auth-actions">
                <button 
                    onClick={startOAuthFlow} 
                    className="oauth-btn google-oauth"
                    disabled={loading}
                >
                    <svg className="google-icon" viewBox="0 0 24 24" width="18" height="18">
                        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                    </svg>
                    {loading ? 'Bağlanıyor...' : 'Gmail\'i Bağla'}
                </button>
            </div>
        </div>
    );
};

export default GoogleOAuthButton;