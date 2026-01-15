"""
Authentication Manager - Kullanıcı kimlik doğrulama ve yetkilendirme
"""

import os
import logging
import hashlib
import secrets
import datetime
import json
import uuid
from .database import db_manager

logger = logging.getLogger(__name__)

class AuthManager:
    """ChromaDB tabanlı API erişim ve yetkilendirme yöneticisi"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AuthManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            logger.info("AuthManager başlatılıyor...")
            
            # Database manager'a erişim
            self.db = db_manager
            
            # İlk kullanıcıyı oluştur (yoksa)
            if not self.db.get_user("admin"):
                password_hash = self._hash_password("admin")
                result = self.db.create_user("admin", password_hash, "admin@metis.local", ["*"])
                if result["status"] == "success":
                    logger.info("Admin kullanıcısı oluşturuldu")
                else:
                    logger.error(f"Admin kullanıcısı oluşturulamadı: {result.get('message')}")
            
            # Varsayılan personaları oluştur
            self.db.init_default_personas()
                
            self._initialized = True
    
    def get_user(self, username):
        """Kullanıcı adına göre kullanıcı bilgisini getir"""
        return self.db.get_user(username)
    
    def get_user_by_email(self, email):
        """Email adresine göre kullanıcı bilgisini getir"""
        return self.db.get_user_by_email(email)

    def _hash_password(self, password):
        """Parola için güvenli hash oluşturur"""
        salt = secrets.token_hex(16)
        hash_obj = hashlib.pbkdf2_hmac(
            'sha256', 
            password.encode('utf-8'), 
            salt.encode('utf-8'), 
            100000
        )
        return f"{salt}${hash_obj.hex()}"
    
    def _verify_password(self, stored_hash, provided_password):
        """Parolayı doğrular"""
        try:
            salt, hash_value = stored_hash.split('$')
            computed_hash = hashlib.pbkdf2_hmac(
                'sha256',
                provided_password.encode('utf-8'),
                salt.encode('utf-8'),
                100000
            ).hex()
            return computed_hash == hash_value
        except Exception as e:
            logger.error(f"Password verification error: {str(e)}")
            return False

    def create_user(self, username, password, email=None, permissions=None):
        """Yeni kullanıcı oluşturur"""
        try:
            password_hash = self._hash_password(password)
            result = self.db.create_user(username, password_hash, email, permissions)
            
            if result["status"] == "success":
                logger.info(f"Yeni kullanıcı oluşturuldu: {username}")
                return {"status": "success", "user_id": result["user_id"]}
            else:
                logger.warning(f"Kullanıcı oluşturma başarısız: {username}, {result.get('message')}")
                return result
        except Exception as e:
            logger.error(f"create_user hatası: {str(e)}")
            return {"status": "error", "message": str(e)}
        
    def authenticate_user(self, username, password):
        """Kullanıcı kimlik doğrulaması"""
        try:
            user = self.db.get_user(username)
            
            if not user:
                logger.warning(f"Kimlik doğrulama başarısız (kullanıcı yok): {username}")
                return {"status": "error", "message": "Invalid credentials"}
            
            if user.get("status") != "active":
                logger.warning(f"Kimlik doğrulama başarısız (kullanıcı pasif): {username}")
                return {"status": "error", "message": "Account is not active"}
                
            if not self._verify_password(user["password_hash"], password):
                logger.warning(f"Kimlik doğrulama başarısız (yanlış parola): {username}")
                return {"status": "error", "message": "Invalid credentials"}
                
            # Son giriş zamanını güncelle
            self.db.update_user_login(username)
            
            # Oturum oluştur (24 saat)
            session_token = self.db.create_session(user["user_id"], expires_in=86400)
            
            logger.info(f"Kullanıcı oturum açtı: {username}")
            
            return {
                "status": "success",
                "user_id": user["user_id"],
                "username": username,
                "email": user.get("email"),
                "session_token": session_token,
                "permissions": user["permissions"]
            }
        except Exception as e:
            logger.error(f"authenticate_user hatası: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def create_api_key(self, username, permissions=None):
        """Yeni API anahtarı oluştur"""
        try:
            user = self.db.get_user(username)
            
            if not user:
                logger.warning(f"API anahtarı oluşturma başarısız (kullanıcı yok): {username}")
                return {"status": "error", "message": "User not found"}
                
            api_key = self.db.create_api_key(user["user_id"], permissions)
            
            logger.info(f"Yeni API anahtarı oluşturuldu: {username}")
            
            return {"status": "success", "api_key": api_key}
        except Exception as e:
            logger.error(f"create_api_key hatası: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def validate_api_key(self, api_key):
        """API anahtarını doğrula"""
        return self.db.validate_api_key(api_key)
    
    def create_session_token(self, user_id):
        """Kullanıcı için session token oluşturur"""
        try:
            session_token = secrets.token_urlsafe(32)
            expires_at = datetime.datetime.now() + datetime.timedelta(hours=24)
            
            return self.db.create_session_token(user_id, session_token, expires_at)
        except Exception as e:
            logger.error(f"create_session_token hatası: {str(e)}")
            return None
    
    def validate_session(self, session_token):
        """Oturum token'ını doğrula"""
        try:
            user_id = self.db.validate_session(session_token)
            
            if not user_id:
                return None
            
            # Kullanıcı bilgilerini user storage'dan al
            try:
                properties = self.db.user_storage.get_all_properties(user_id)
                
                if properties:
                    permissions = properties.get('permissions', ['user'])
                    if isinstance(permissions, str):
                        import json
                        permissions = json.loads(permissions)
                    
                    return {
                        "user_id": user_id,
                        "username": properties.get("username", user_id),
                        "email": properties.get("email"),
                        "permissions": permissions
                    }
            except Exception as e:
                logger.error(f"User properties alma hatası: {str(e)}")
                return None
                    
            return None
        except Exception as e:
            logger.error(f"validate_session hatası: {str(e)}")
            return None
    
    def check_permission(self, api_key, permission):
        """API anahtarının belirli bir izne sahip olup olmadığını kontrol et"""
        try:
            key_info = self.db.get_api_key_info(api_key)
            
            if not key_info:
                return False
                
            # Tüm izinlere sahip mi?
            if "*" in key_info["permissions"]:
                return True
                
            # Belirli izne sahip mi?
            return permission in key_info["permissions"]
        except Exception as e:
            logger.error(f"check_permission hatası: {str(e)}")
            return False
    
    def revoke_api_key(self, api_key):
        """API anahtarını iptal et"""
        return self.db.revoke_api_key(api_key)
    
    def logout_user(self, session_token):
        """Kullanıcı çıkışı"""
        return self.db.end_session(session_token)
    
    def cleanup_sessions(self):
        """Süresi dolmuş oturumları temizle"""
        return self.db.cleanup_sessions()
    
    def get_user_by_session(self, session_token):
        """Session token'dan kullanıcı bilgilerini getir"""
        try:
            user_id = self.db.validate_session(session_token)
            if not user_id:
                return None
                
            # User ID'den kullanıcı bilgilerini al
            try:
                properties = self.db.user_storage.get_all_properties(user_id)
                
                if properties:
                    permissions = properties.get('permissions', ['user'])
                    if isinstance(permissions, str):
                        permissions = json.loads(permissions)
                    
                    return {
                        "user_id": user_id,
                        "username": properties.get("username", user_id),
                        "email": properties.get("email"),
                        "permissions": permissions,
                        "status": properties.get("status", "active")
                    }
            except Exception as e:
                logger.error(f"User properties alma hatası (validate_api_key): {str(e)}")
                return None
                    
            return None
        except Exception as e:
            logger.error(f"get_user_by_session hatası: {str(e)}")
            return None

    def update_password(self, username, old_password, new_password):
        """Kullanıcının şifresini günceller"""
        try:
            # Önce mevcut şifreyi doğrula
            auth_result = self.authenticate_user(username, old_password)
            if auth_result.get("status") != "success":
                logger.warning(f"Şifre güncelleme başarısız (yanlış eski şifre): {username}")
                return {"status": "error", "message": "Mevcut şifre yanlış"}
            
            # Yeni şifre validasyonu
            if len(new_password) < 6:
                return {"status": "error", "message": "Yeni şifre en az 6 karakter olmalıdır"}
            
            # Yeni şifreyi hash'le
            new_password_hash = self._hash_password(new_password)
            
            # Database'de güncelle
            result = self.db.update_user_password(username, new_password_hash)
            
            if result:
                logger.info(f"Kullanıcı şifresi başarıyla güncellendi: {username}")
                return {"status": "success", "message": "Şifre başarıyla güncellendi"}
            else:
                return {"status": "error", "message": "Şifre güncellenemedi"}
            
        except Exception as e:
            logger.error(f"update_password hatası: {str(e)}")
            return {"status": "error", "message": str(e)}

# Global instance
auth_manager = AuthManager()