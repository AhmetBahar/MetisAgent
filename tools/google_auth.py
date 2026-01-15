"""
Google OAuth Authentication Manager

Google OAuth2 ile kimlik doğrulama ve token yönetimi
"""

import logging
import json
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlencode, parse_qs
import requests
from flask import session, request, url_for
from tools.settings_manager import settings_manager

logger = logging.getLogger(__name__)

class GoogleAuthManager:
    """Google OAuth2 kimlik doğrulama yöneticisi"""
    
    def __init__(self):
        """Google Auth Manager başlatır"""
        self.client_id = None
        self.client_secret = None
        self.redirect_uri = None
        self.scope = [
            'openid',
            'email',
            'profile',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile'
        ]
        self.auth_url = 'https://accounts.google.com/o/oauth2/v2/auth'
        self.token_url = 'https://oauth2.googleapis.com/token'
        self.userinfo_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
        
        # Admin kullanıcısından Google OAuth credentials'ı al
        self._load_google_credentials()
    
    def _load_google_credentials(self):
        """Google OAuth credentials'ı yükler"""
        try:
            # Admin kullanıcısından Google OAuth bilgilerini al
            google_creds = settings_manager.get_api_key('admin', 'google_oauth')
            if google_creds:
                additional_info = google_creds.get('additional_info', {})
                self.client_id = additional_info.get('client_id')
                self.client_secret = google_creds.get('api_key')
                self.redirect_uri = additional_info.get('redirect_uri', 'http://localhost:5000/auth/google/callback')
                logger.info("Google OAuth credentials yüklendi")
            else:
                logger.warning("Google OAuth credentials bulunamadı")
                
        except Exception as e:
            logger.error(f"Google credentials yükleme hatası: {e}")
    
    def setup_google_oauth(self, client_id: str, client_secret: str, redirect_uri: str = None) -> bool:
        """
        Google OAuth ayarlarını yapılandırır
        
        Args:
            client_id: Google OAuth Client ID
            client_secret: Google OAuth Client Secret
            redirect_uri: Redirect URI (opsiyonel)
            
        Returns:
            bool: Başarı durumu
        """
        try:
            self.client_id = client_id
            self.client_secret = client_secret
            self.redirect_uri = redirect_uri or 'http://localhost:5000/auth/google/callback'
            
            # Credentials'ı güvenli şekilde kaydet
            additional_info = {
                'client_id': client_id,
                'redirect_uri': self.redirect_uri,
                'setup_date': datetime.now().isoformat()
            }
            
            success = settings_manager.save_api_key(
                'admin', 
                'google_oauth', 
                client_secret, 
                additional_info
            )
            
            if success:
                logger.info("Google OAuth ayarları kaydedildi")
                return True
            else:
                logger.error("Google OAuth ayarları kaydedilemedi")
                return False
                
        except Exception as e:
            logger.error(f"Google OAuth ayarlama hatası: {e}")
            return False
    
    def get_auth_url(self, state: Optional[str] = None) -> str:
        """
        Google OAuth yetkilendirme URL'i oluşturur
        
        Args:
            state: State parametresi (güvenlik için)
            
        Returns:
            str: Yetkilendirme URL'i
        """
        try:
            if not self.client_id:
                logger.error("Google OAuth Client ID ayarlanmamış")
                return None
            
            # State parametresi oluştur
            if not state:
                state = secrets.token_urlsafe(32)
            
            # Session'da state'i sakla
            session['oauth_state'] = state
            
            # Auth URL parametreleri
            params = {
                'client_id': self.client_id,
                'redirect_uri': self.redirect_uri,
                'scope': ' '.join(self.scope),
                'response_type': 'code',
                'state': state,
                'access_type': 'offline',
                'prompt': 'consent'
            }
            
            auth_url = f"{self.auth_url}?{urlencode(params)}"
            logger.info("Google OAuth URL oluşturuldu")
            return auth_url
            
        except Exception as e:
            logger.error(f"Auth URL oluşturma hatası: {e}")
            return None
    
    def handle_callback(self, code: str, state: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Google OAuth callback'i işler
        
        Args:
            code: Authorization code
            state: State parametresi
            
        Returns:
            Tuple[bool, Dict]: (başarı durumu, kullanıcı bilgileri)
        """
        try:
            # State kontrolü
            if 'oauth_state' not in session or session['oauth_state'] != state:
                logger.error("OAuth state mismatch")
                return False, None
            
            # State'i temizle
            session.pop('oauth_state', None)
            
            # Access token al
            token_data = self._exchange_code_for_token(code)
            if not token_data:
                logger.error("Token alınamadı")
                return False, None
            
            # Kullanıcı bilgilerini al
            user_info = self._get_user_info(token_data['access_token'])
            if not user_info:
                logger.error("Kullanıcı bilgileri alınamadı")
                return False, None
            
            # Token'ı kaydet
            user_id = user_info['id']
            self._save_user_tokens(user_id, token_data)
            
            logger.info(f"Google OAuth başarılı: {user_info['email']}")
            return True, user_info
            
        except Exception as e:
            logger.error(f"Callback işleme hatası: {e}")
            return False, None
    
    def _exchange_code_for_token(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Authorization code'u access token ile değiştirir
        
        Args:
            code: Authorization code
            
        Returns:
            Dict veya None: Token bilgileri
        """
        try:
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': self.redirect_uri
            }
            
            response = requests.post(self.token_url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Expire time hesapla
            if 'expires_in' in token_data:
                expires_at = datetime.now() + timedelta(seconds=token_data['expires_in'])
                token_data['expires_at'] = expires_at.isoformat()
            
            return token_data
            
        except Exception as e:
            logger.error(f"Token exchange hatası: {e}")
            return None
    
    def _get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Access token ile kullanıcı bilgilerini alır
        
        Args:
            access_token: Access token
            
        Returns:
            Dict veya None: Kullanıcı bilgileri
        """
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(self.userinfo_url, headers=headers)
            response.raise_for_status()
            
            user_info = response.json()
            return user_info
            
        except Exception as e:
            logger.error(f"Kullanıcı bilgileri alma hatası: {e}")
            return None
    
    def _save_user_tokens(self, user_id: str, token_data: Dict[str, Any]):
        """
        Kullanıcı tokenlarını kaydeder
        
        Args:
            user_id: Kullanıcı ID'si
            token_data: Token bilgileri
        """
        try:
            settings_manager.save_oauth_token(user_id, 'google', token_data)
            logger.info(f"Google token kaydedildi: {user_id}")
        except Exception as e:
            logger.error(f"Token kaydetme hatası: {e}")
    
    def get_user_token(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Kullanıcının Google token'ını getirir
        
        Args:
            user_id: Kullanıcı ID'si
            
        Returns:
            Dict veya None: Token bilgileri
        """
        try:
            return settings_manager.get_oauth_token(user_id, 'google')
        except Exception as e:
            logger.error(f"Token getirme hatası: {e}")
            return None
    
    def refresh_token(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Kullanıcının token'ını yeniler
        
        Args:
            user_id: Kullanıcı ID'si
            
        Returns:
            Dict veya None: Yeni token bilgileri
        """
        try:
            token_data = self.get_user_token(user_id)
            if not token_data or 'refresh_token' not in token_data:
                logger.error("Refresh token bulunamadı")
                return None
            
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'refresh_token': token_data['refresh_token'],
                'grant_type': 'refresh_token'
            }
            
            response = requests.post(self.token_url, data=data)
            response.raise_for_status()
            
            new_token_data = response.json()
            
            # Refresh token'ı koru
            if 'refresh_token' not in new_token_data:
                new_token_data['refresh_token'] = token_data['refresh_token']
            
            # Expire time hesapla
            if 'expires_in' in new_token_data:
                expires_at = datetime.now() + timedelta(seconds=new_token_data['expires_in'])
                new_token_data['expires_at'] = expires_at.isoformat()
            
            # Yeni token'ı kaydet
            self._save_user_tokens(user_id, new_token_data)
            
            logger.info(f"Google token yenilendi: {user_id}")
            return new_token_data
            
        except Exception as e:
            logger.error(f"Token yenileme hatası: {e}")
            return None
    
    def is_user_authenticated(self, user_id: str) -> bool:
        """
        Kullanıcının kimlik doğrulamasını kontrol eder
        
        Args:
            user_id: Kullanıcı ID'si
            
        Returns:
            bool: Kimlik doğrulaması geçerli mi?
        """
        try:
            return settings_manager.is_oauth_token_valid(user_id, 'google')
        except Exception as e:
            logger.error(f"Kimlik doğrulama kontrolü hatası: {e}")
            return False
    
    def get_valid_token(self, user_id: str) -> Optional[str]:
        """
        Kullanıcının geçerli access token'ını getirir (gerekirse yeniler)
        
        Args:
            user_id: Kullanıcı ID'si
            
        Returns:
            str veya None: Geçerli access token
        """
        try:
            token_data = self.get_user_token(user_id)
            if not token_data:
                return None
            
            # Token geçerli mi kontrol et
            if 'expires_at' in token_data:
                expires_at = datetime.fromisoformat(token_data['expires_at'])
                if datetime.now() > expires_at:
                    # Token süresi dolmuş, yenile
                    token_data = self.refresh_token(user_id)
                    if not token_data:
                        return None
            
            return token_data.get('access_token')
            
        except Exception as e:
            logger.error(f"Geçerli token alma hatası: {e}")
            return None
    
    def logout_user(self, user_id: str) -> bool:
        """
        Kullanıcıyı çıkış yapar (tokenları siler)
        
        Args:
            user_id: Kullanıcı ID'si
            
        Returns:
            bool: Başarı durumu
        """
        try:
            # Token'ı sil
            document_id = f"oauth_token_{user_id}_google"
            settings_manager.collection.delete(ids=[document_id])
            
            logger.info(f"Kullanıcı çıkış yaptı: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Çıkış işlemi hatası: {e}")
            return False
    
    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Kullanıcının Google profil bilgilerini getirir
        
        Args:
            user_id: Kullanıcı ID'si
            
        Returns:
            Dict veya None: Profil bilgileri
        """
        try:
            access_token = self.get_valid_token(user_id)
            if not access_token:
                return None
            
            return self._get_user_info(access_token)
            
        except Exception as e:
            logger.error(f"Profil bilgileri alma hatası: {e}")
            return None

# Global instance
google_auth = GoogleAuthManager()