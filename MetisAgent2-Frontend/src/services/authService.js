/**
 * Authentication Service - Google OAuth ve kullanıcı kimlik doğrulama
 */

const API_BASE_URL = (process.env.REACT_APP_API_URL || 'http://localhost:5001') + '/api';

class AuthService {
    constructor() {
        this.user = null;
        this.isAuthenticated = false;
        this.checkAuthStatus();
    }

    /**
     * Authentication durumunu kontrol eder
     */
    async checkAuthStatus() {
        try {
            // First check if we have a session token in localStorage
            const token = localStorage.getItem('session_token');
            if (!token) {
                return { authenticated: false };
            }
            
            const response = await fetch(`${API_BASE_URL}/auth/validate`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ session_token: token })
            });

            if (response.ok) {
                const data = await response.json();
                this.isAuthenticated = data.valid || false;
                
                if (this.isAuthenticated && data.user) {
                    this.user = data.user;
                }
                
                return { authenticated: this.isAuthenticated, user: this.user };
            } else {
                this.isAuthenticated = false;
                this.user = null;
                return { authenticated: false };
            }
        } catch (error) {
            console.error('Auth status kontrolü hatası:', error);
            this.isAuthenticated = false;
            this.user = null;
            return { authenticated: false };
        }
    }

    /**
     * Google OAuth giriş URL'ini alır (Temporarily disabled)
     */
    async getGoogleAuthUrl() {
        throw new Error('Google OAuth şu anda devre dışı');
    }

    /**
     * Google OAuth ile giriş yapar (Temporarily disabled)
     */
    async loginWithGoogle() {
        throw new Error('Google OAuth şu anda devre dışı. Normal giriş formunu kullanın.');
    }

    /**
     * Kullanıcı profil bilgilerini yükler
     */
    async loadUserProfile() {
        try {
            const token = localStorage.getItem('session_token');
            if (!token) {
                throw new Error('Session token bulunamadı');
            }
            
            const response = await fetch(`${API_BASE_URL}/auth/me`, {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.user = data.user;
                return this.user;
            } else {
                throw new Error('Profil bilgileri alınamadı');
            }
        } catch (error) {
            console.error('Profil yükleme hatası:', error);
            this.user = null;
            throw error;
        }
    }

    /**
     * Çıkış yapar
     */
    async logout() {
        try {
            // Session token'ı al
            const sessionToken = localStorage.getItem('session_token');
            
            // Backend'e logout isteği gönder (tek endpoint kullan)
            const response = await fetch(`${API_BASE_URL}/auth/logout`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': sessionToken ? `Bearer ${sessionToken}` : ''
                },
                body: JSON.stringify({
                    session_token: sessionToken
                })
            });

            // Her durumda local state'i temizle
            this.isAuthenticated = false;
            this.user = null;
            
            // Session storage ve local storage'ı temizle
            if (typeof(Storage) !== "undefined") {
                sessionStorage.clear();
                localStorage.clear();
            }
            
            // Cookie'leri temizle (session cookie'si için)
            document.cookie.split(";").forEach(function(c) { 
                document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/"); 
            });

            if (response.ok) {
                console.log('Backend logout successful');
                return true;
            } else {
                console.warn('Backend logout failed, but local state cleared');
                return true; // Local state temizlendiği için true dön
            }
        } catch (error) {
            console.error('Çıkış hatası:', error);
            // Network hatası olsa bile local state temizlenmiştir
            this.isAuthenticated = false;
            this.user = null;
            return true;
        }
    }

    /**
     * Kullanıcı ayarlarını getirir
     */
    async getUserSettings() {
        try {
            const sessionToken = localStorage.getItem('session_token');
            const response = await fetch(`${API_BASE_URL}/user/settings`, {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': sessionToken ? `Bearer ${sessionToken}` : ''
                }
            });

            if (response.ok) {
                const data = await response.json();
                return data.settings;
            } else {
                throw new Error('Ayarlar alınamadı');
            }
        } catch (error) {
            console.error('Ayarları getirme hatası:', error);
            throw error;
        }
    }

    /**
     * Kullanıcı ayarlarını kaydeder
     */
    async saveUserSettings(settings) {
        try {
            const response = await fetch(`${API_BASE_URL}/user/settings`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ settings })
            });

            if (response.ok) {
                return await response.json();
            } else {
                throw new Error('Ayarlar kaydedilemedi');
            }
        } catch (error) {
            console.error('Ayarları kaydetme hatası:', error);
            throw error;
        }
    }

    /**
     * API keylerini listeler
     */
    async listApiKeys() {
        try {
            const sessionToken = localStorage.getItem('session_token');
            const response = await fetch(`${API_BASE_URL}/api-keys`, {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': sessionToken ? `Bearer ${sessionToken}` : ''
                }
            });

            if (response.ok) {
                const data = await response.json();
                return data.api_keys;
            } else {
                console.error('API keys response error:', response.status);
                throw new Error('API keyler alınamadı');
            }
        } catch (error) {
            console.error('API key listesi hatası:', error);
            throw error;
        }
    }

    /**
     * API key kaydeder
     */
    async saveApiKey(service, apiKey, additionalInfo = {}) {
        try {
            const response = await fetch(`${API_BASE_URL}/api-keys`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    service,
                    api_key: apiKey,
                    additional_info: additionalInfo
                })
            });

            if (response.ok) {
                return await response.json();
            } else {
                throw new Error('API key kaydedilemedi');
            }
        } catch (error) {
            console.error('API key kaydetme hatası:', error);
            throw error;
        }
    }

    /**
     * Belirli bir servis için API key getirir
     */
    async getApiKey(service) {
        try {
            const response = await fetch(`${API_BASE_URL}/api-keys/${service}`, {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (response.ok) {
                return await response.json();
            } else {
                throw new Error('API key alınamadı');
            }
        } catch (error) {
            console.error('API key getirme hatası:', error);
            throw error;
        }
    }

    /**
     * API key siler
     */
    async deleteApiKey(service) {
        try {
            const response = await fetch(`${API_BASE_URL}/api-keys/${service}`, {
                method: 'DELETE',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (response.ok) {
                return await response.json();
            } else {
                throw new Error('API key silinemedi');
            }
        } catch (error) {
            console.error('API key silme hatası:', error);
            throw error;
        }
    }

    /**
     * Google OAuth ayarlarını yapılandırır
     */
    async setupGoogleOAuth(clientId, clientSecret, redirectUri) {
        try {
            const response = await fetch(`${API_BASE_URL}/auth/google/setup`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    client_id: clientId,
                    client_secret: clientSecret,
                    redirect_uri: redirectUri
                })
            });

            if (response.ok) {
                return await response.json();
            } else {
                throw new Error('Google OAuth ayarlanamadı');
            }
        } catch (error) {
            console.error('Google OAuth setup hatası:', error);
            throw error;
        }
    }

    /**
     * Google credentials kaydeder
     */
    async saveGoogleCredentials(credentials) {
        try {
            const sessionToken = localStorage.getItem('session_token');
            const response = await fetch(`${API_BASE_URL}/google-credentials`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': sessionToken ? `Bearer ${sessionToken}` : ''
                },
                body: JSON.stringify({
                    email: credentials.email,
                    password: credentials.password,
                    recovery_email: credentials.recoveryEmail,
                    phone_number: credentials.phoneNumber
                })
            });

            if (response.ok) {
                return await response.json();
            } else {
                throw new Error('Google hesap bilgileri kaydedilemedi');
            }
        } catch (error) {
            console.error('Google credentials kaydetme hatası:', error);
            throw error;
        }
    }

    /**
     * Google credentials getirir
     */
    async getGoogleCredentials() {
        try {
            const sessionToken = localStorage.getItem('session_token');
            const response = await fetch(`${API_BASE_URL}/google-credentials`, {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': sessionToken ? `Bearer ${sessionToken}` : ''
                }
            });

            if (response.ok) {
                const data = await response.json();
                return data.credentials;
            } else if (response.status === 404) {
                return null; // Henüz credentials kaydedilmemiş
            } else {
                throw new Error('Google hesap bilgileri alınamadı');
            }
        } catch (error) {
            console.error('Google credentials getirme hatası:', error);
            throw error;
        }
    }

    /**
     * Google credentials siler
     */
    async deleteGoogleCredentials() {
        try {
            const sessionToken = localStorage.getItem('session_token');
            const response = await fetch(`${API_BASE_URL}/google-credentials`, {
                method: 'DELETE',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': sessionToken ? `Bearer ${sessionToken}` : ''
                }
            });

            if (response.ok) {
                return await response.json();
            } else {
                throw new Error('Google hesap bilgileri silinemedi');
            }
        } catch (error) {
            console.error('Google credentials silme hatası:', error);
            throw error;
        }
    }

    /**
     * Authentication durumunu döndürür
     */
    getAuthStatus() {
        return {
            isAuthenticated: this.isAuthenticated,
            user: this.user
        };
    }
}

// Global instance export
const authService = new AuthService();
export default authService;