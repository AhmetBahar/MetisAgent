# os_araci/auth/auth_manager.py
import os
import logging
import hashlib
import secrets
import datetime
import json
import uuid
from os_araci.db.chroma_manager import ChromaManager

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
            logger.info("ChromaDB AuthManager başlatılıyor...")
            
            # ChromaDB yöneticisine erişim
            self.db = ChromaManager()
            
            # İlk kullanıcıyı oluştur (yoksa)
            if not self.db.get_user("admin"):
                password_hash = self._hash_password("admin")
                self.db.create_user("admin", password_hash, ["*"])
                logger.info("Admin kullanıcısı oluşturuldu")
                
            self._initialized = True
    
    def get_user(self, username):
        """Kullanıcı adına göre kullanıcı bilgisini getir"""
        return self.db.get_user(username)

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
        salt, hash_value = stored_hash.split('$')
        computed_hash = hashlib.pbkdf2_hmac(
            'sha256',
            provided_password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()
        return computed_hash == hash_value


    def create_user(self, username, password, permissions=None):
        """Yeni kullanıcı oluşturur"""
        password_hash = self._hash_password(password)
        result = self.db.create_user(username, password_hash, permissions)
        
        if result["status"] == "success":
            logger.info(f"Yeni kullanıcı oluşturuldu: {username}")
            return {"status": "success", "user_id": result["user_id"]}
        else:
            logger.warning(f"Kullanıcı oluşturma başarısız: {username}, {result.get('message')}")
            return result
        
    def authenticate_user(self, username, password):
        """Kullanıcı kimlik doğrulaması"""
        user = self.db.get_user(username)
        
        if not user:
            logger.warning(f"Kimlik doğrulama başarısız (kullanıcı yok): {username}")
            return {"status": "error", "message": "Invalid credentials"}
            
        if not self._verify_password(user["password_hash"], password):
            logger.warning(f"Kimlik doğrulama başarısız (yanlış parola): {username}")
            return {"status": "error", "message": "Invalid credentials"}
            
        # Son giriş zamanını güncelle
        self.db.update_user_login(username)
        
        # Oturum oluştur
        session_token = self.db.create_session(user["user_id"])
        
        logger.info(f"Kullanıcı oturum açtı: {username}")
        
        return {
            "status": "success",
            "user_id": user["user_id"],
            "username": username,
            "session_token": session_token,
            "permissions": user["permissions"]
        }
    
    def create_api_key(self, username, permissions=None):
        """Yeni API anahtarı oluştur"""
        user = self.db.get_user(username)
        
        if not user:
            logger.warning(f"API anahtarı oluşturma başarısız (kullanıcı yok): {username}")
            return {"status": "error", "message": "User not found"}
            
        api_key = self.db.create_api_key(user["user_id"], permissions)
        
        logger.info(f"Yeni API anahtarı oluşturuldu: {username}")
        
        return {"status": "success", "api_key": api_key}
    
    def validate_api_key(self, api_key):
        """API anahtarını doğrula"""
        return self.db.validate_api_key(api_key)
    
    def validate_session(self, session_token):
        """Oturum token'ını doğrula"""
        user_id = self.db.validate_session(session_token)
        
        if not user_id:
            return None
            
        # Kullanıcı ID'den kullanıcı bilgilerini bul
        all_users = self.db.users_collection.get()
        
        for i, (_id, metadata) in enumerate(zip(all_users["ids"], all_users["metadatas"])):
            if _id == user_id:
                return {
                    "user_id": user_id,
                    "username": metadata["username"],
                    "permissions": json.loads(metadata["permissions"])
                }
                
        return None
    
    def check_permission(self, api_key, permission):
        """API anahtarının belirli bir izne sahip olup olmadığını kontrol et"""
        key_info = self.db.get_api_key_info(api_key)
        
        if not key_info:
            return False
            
        # Tüm izinlere sahip mi?
        if "*" in key_info["permissions"]:
            return True
            
        # Belirli izne sahip mi?
        return permission in key_info["permissions"]
    
    def revoke_api_key(self, api_key):
        """API anahtarını iptal et"""
        return self.db.revoke_api_key(api_key)
    
    def logout_user(self, session_token):
        """Kullanıcı çıkışı"""
        return self.db.end_session(session_token)
    
    def cleanup_sessions(self):
        """Süresi dolmuş oturumları temizle"""
        return self.db.cleanup_sessions()