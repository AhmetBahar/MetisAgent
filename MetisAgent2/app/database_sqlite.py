"""
Database Manager - SQLite tabanlı kullanıcı ve session yönetimi
ChromaDB'den SQLite'a geçiş versiyonu
"""

import os
import json
import uuid
import time
import secrets
from datetime import datetime
import logging
import sqlite3
from typing import Dict, Any, Optional, List

try:
    from ..tools.internal.user_storage import get_user_storage
except ImportError:
    # Fallback for direct execution or when running as module
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from tools.internal.user_storage import get_user_storage

logger = logging.getLogger(__name__)

class DatabaseManager:
    """SQLite tabanlı veritabanı yöneticisi (ChromaDB replacement)"""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_path: str = "users.db"):
        if self._initialized:
            return
            
        self.db_path = db_path
        self.user_storage = get_user_storage()
        self._init_additional_tables()
        
        self._initialized = True
        logger.info("DatabaseManager (SQLite) başlatıldı")
    
    def _init_additional_tables(self):
        """Database'e ek tablolar ekler (sessions, personas için)"""
        with sqlite3.connect(self.db_path) as conn:
            # Sessions tablosu
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_token TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    status TEXT DEFAULT 'active',
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Index for sessions
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_sessions_user_id 
                ON sessions (user_id)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_sessions_expires 
                ON sessions (expires_at)
            ''')
            
            conn.commit()
    
    # Kullanıcı yönetimi metodları
    def create_user(self, username: str, password_hash: str, email: str = None, permissions: List = None) -> Dict[str, Any]:
        """Yeni kullanıcı oluştur"""
        try:
            # Kullanıcının zaten var olup olmadığını kontrol et
            existing = self.get_user(username)
            if existing:
                return {"status": "error", "message": "Kullanıcı zaten mevcut"}
            
            # User ID oluştur
            user_id = str(uuid.uuid4())
            
            # User storage'da user oluştur
            self.user_storage.create_user(user_id)
            
            # User properties'lerini kaydet
            self.user_storage.set_property(user_id, 'username', username)
            self.user_storage.set_property(user_id, 'password_hash', password_hash, encrypt=True)
            if email:
                self.user_storage.set_property(user_id, 'email', email)
            if permissions:
                self.user_storage.set_property(user_id, 'permissions', permissions, property_type='json')
            
            self.user_storage.set_property(user_id, 'status', 'active')
            
            logger.info(f"Yeni kullanıcı oluşturuldu: {username}")
            return {"status": "success", "user_id": user_id}
            
        except Exception as e:
            logger.error(f"Kullanıcı oluşturma hatası: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Kullanıcı adına göre kullanıcı bilgisini getir"""
        try:
            # Tüm kullanıcıları kontrol et (username ile eşleşen bul)
            users = self.user_storage.list_users()
            
            for user_id in users:
                stored_username = self.user_storage.get_property(user_id, 'username')
                if stored_username == username:
                    # User properties'lerini al
                    properties = self.user_storage.get_all_properties(user_id)
                    
                    return {
                        "user_id": user_id,
                        "username": properties.get('username'),
                        "email": properties.get('email'),
                        "password_hash": properties.get('password_hash'),
                        "permissions": properties.get('permissions', ['user']),
                        "created_at": properties.get('created_at'),
                        "last_login": properties.get('last_login'),
                        "status": properties.get('status', 'active')
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"get_user hatası: {str(e)}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Email adresine göre kullanıcı bilgisini getir"""
        try:
            # Tüm kullanıcıları kontrol et (email ile eşleşen bul)
            users = self.user_storage.list_users()
            
            for user_id in users:
                stored_email = self.user_storage.get_property(user_id, 'email')
                if stored_email == email:
                    properties = self.user_storage.get_all_properties(user_id)
                    
                    return {
                        "user_id": user_id,
                        "username": properties.get('username'),
                        "email": properties.get('email'),
                        "password_hash": properties.get('password_hash'),
                        "permissions": properties.get('permissions', ['user']),
                        "created_at": properties.get('created_at'),
                        "last_login": properties.get('last_login'),
                        "status": properties.get('status', 'active')
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"get_user_by_email hatası: {str(e)}")
            return None
    
    def update_user_login(self, username: str) -> bool:
        """Kullanıcının son oturum açma zamanını günceller"""
        try:
            user = self.get_user(username)
            if not user:
                return False
            
            user_id = user['user_id']
            self.user_storage.set_property(user_id, 'last_login', datetime.now().isoformat())
            
            return True
            
        except Exception as e:
            logger.error(f"update_user_login hatası: {str(e)}")
            return False
    
    def update_user_password(self, username: str, new_password_hash: str) -> bool:
        """Kullanıcının şifresini günceller"""
        try:
            user = self.get_user(username)
            if not user:
                return False
            
            user_id = user['user_id']
            self.user_storage.set_property(user_id, 'password_hash', new_password_hash, encrypt=True)
            
            logger.info(f"Kullanıcı şifresi database'de güncellendi: {username}")
            return True
            
        except Exception as e:
            logger.error(f"update_user_password hatası: {str(e)}")
            return False
    
    # API anahtarı yönetimi (user_storage üzerinden)
    def create_api_key(self, user_id: str, permissions: List = None) -> str:
        """Yeni API anahtarı oluşturur"""
        try:
            api_key = f"metis_{secrets.token_hex(16)}"
            
            api_key_data = {
                'api_key': api_key,
                'user_id': user_id,
                'permissions': permissions or ['read'],
                'created_at': datetime.now().isoformat(),
                'last_used': '',
                'status': 'active'
            }
            
            # User property olarak kaydet
            self.user_storage.set_property(user_id, f'api_key_metis_{api_key[-8:]}', 
                                         api_key_data, encrypt=True, property_type='json')
            
            logger.info(f"Yeni API anahtarı oluşturuldu: {user_id}")
            return api_key
            
        except Exception as e:
            logger.error(f"create_api_key hatası: {str(e)}")
            return None
    
    def validate_api_key(self, api_key: str) -> bool:
        """API anahtarını doğrular"""
        try:
            # Tüm kullanıcıları kontrol et
            users = self.user_storage.list_users()
            
            for user_id in users:
                properties = self.user_storage.get_all_properties(user_id)
                
                # API key properties'lerini kontrol et
                for prop_name, prop_value in properties.items():
                    if prop_name.startswith('api_key_metis_') and isinstance(prop_value, dict):
                        if prop_value.get('api_key') == api_key:
                            if prop_value.get('status') == 'active':
                                # Last used'ı güncelle
                                prop_value['last_used'] = datetime.now().isoformat()
                                self.user_storage.set_property(user_id, prop_name, prop_value, 
                                                             encrypt=True, property_type='json')
                                return True
            
            return False
            
        except Exception as e:
            logger.error(f"validate_api_key hatası: {str(e)}")
            return False
    
    def get_api_key_info(self, api_key: str) -> Optional[Dict[str, Any]]:
        """API anahtarı bilgilerini getirir"""
        try:
            # Tüm kullanıcıları kontrol et
            users = self.user_storage.list_users()
            
            for user_id in users:
                properties = self.user_storage.get_all_properties(user_id)
                
                # API key properties'lerini kontrol et
                for prop_name, prop_value in properties.items():
                    if prop_name.startswith('api_key_metis_') and isinstance(prop_value, dict):
                        if prop_value.get('api_key') == api_key:
                            return {
                                "api_key": api_key,
                                "user_id": user_id,
                                "permissions": prop_value.get('permissions', []),
                                "created_at": prop_value.get('created_at'),
                                "last_used": prop_value.get('last_used'),
                                "status": prop_value.get('status', 'active')
                            }
            
            return None
            
        except Exception as e:
            logger.error(f"get_api_key_info hatası: {str(e)}")
            return None
    
    def revoke_api_key(self, api_key: str) -> bool:
        """API anahtarını iptal eder"""
        try:
            # API key'i bul ve sil
            users = self.user_storage.list_users()
            
            for user_id in users:
                properties = self.user_storage.get_all_properties(user_id)
                
                for prop_name, prop_value in properties.items():
                    if prop_name.startswith('api_key_metis_') and isinstance(prop_value, dict):
                        if prop_value.get('api_key') == api_key:
                            self.user_storage.delete_property(user_id, prop_name)
                            return True
            
            return False
            
        except Exception as e:
            logger.error(f"revoke_api_key hatası: {str(e)}")
            return False
    
    # Oturum yönetimi (SQLite sessions tablosu)
    def create_session(self, user_id: str, expires_in: int = 3600) -> str:
        """Yeni oturum oluşturur"""
        try:
            session_token = secrets.token_hex(32)
            created_at = datetime.now().isoformat()
            expires_at = time.time() + expires_in
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO sessions (session_token, user_id, created_at, expires_at, status)
                    VALUES (?, ?, ?, ?, ?)
                ''', (session_token, user_id, created_at, expires_at, 'active'))
                
                conn.commit()
            
            logger.info(f"Session created for user: {user_id}")
            return session_token
            
        except Exception as e:
            logger.error(f"create_session hatası: {str(e)}")
            return None
    
    def create_session_token(self, user_id: str, session_token: str, expires_at: datetime) -> str:
        """Kullanıcı için session token oluşturur"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO sessions (session_token, user_id, created_at, expires_at, status)
                    VALUES (?, ?, ?, ?, ?)
                ''', (session_token, user_id, datetime.now().isoformat(), expires_at.timestamp(), 'active'))
                
                conn.commit()
            
            logger.info(f"Session token created for user: {user_id}")
            return session_token
            
        except Exception as e:
            logger.error(f"Session token oluşturma hatası: {str(e)}")
            return None
    
    def validate_session(self, session_token: str) -> Optional[str]:
        """Oturum token'ını doğrula"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT user_id, expires_at, status FROM sessions 
                    WHERE session_token = ?
                ''', (session_token,))
                
                row = cursor.fetchone()
                
                if not row:
                    logger.warning(f"Session not found: {session_token}")
                    return None
                
                user_id, expires_at, status = row
                
                # Oturum süresini kontrol et
                current_time = time.time()
                
                if current_time > expires_at:
                    # Süresi dolmuş oturumu sil
                    logger.info(f"Session expired: {session_token}")
                    conn.execute('DELETE FROM sessions WHERE session_token = ?', (session_token,))
                    conn.commit()
                    return None
                
                if status != 'active':
                    logger.warning(f"Session not active: {session_token}")
                    return None
                
                logger.info(f"Session validated successfully: {session_token}")
                return user_id
                
        except Exception as e:
            logger.error(f"Oturum doğrulama hatası: {str(e)}")
            return None
    
    def end_session(self, session_token: str) -> bool:
        """Oturumu sonlandırır"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('DELETE FROM sessions WHERE session_token = ?', (session_token,))
                conn.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"end_session hatası: {str(e)}")
            return False
    
    def cleanup_sessions(self) -> int:
        """Süresi dolmuş oturumları temizler"""
        try:
            current_time = time.time()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    DELETE FROM sessions WHERE expires_at < ?
                ''', (current_time,))
                
                expired_count = cursor.rowcount
                conn.commit()
            
            logger.info(f"{expired_count} süresi dolmuş oturum temizlendi")
            return expired_count
            
        except Exception as e:
            logger.error(f"cleanup_sessions hatası: {str(e)}")
            return 0
    
    # Persona yönetimi (user_storage üzerinden)
    def create_persona(self, persona_data: Dict[str, Any]) -> Dict[str, Any]:
        """Yeni persona oluştur"""
        try:
            persona_id = persona_data.get("id") or persona_data.get("persona_id")
            if not persona_id:
                persona_id = str(uuid.uuid4())
                persona_data["id"] = persona_id
            
            # Persona zaten var mı kontrol et
            existing = self.get_persona(persona_id)
            if existing:
                return {"status": "error", "message": f"Persona zaten mevcut: {persona_id}"}
            
            # Persona verilerini system user'ına kaydet
            persona_data["created_at"] = datetime.now().isoformat()
            persona_data["updated_at"] = datetime.now().isoformat()
            
            self.user_storage.set_property('system', f'persona_{persona_id}', 
                                         persona_data, property_type='json')
            
            logger.info(f"Persona oluşturuldu: {persona_id}")
            return {"status": "success", "persona_id": persona_id, "persona": persona_data}
            
        except Exception as e:
            logger.error(f"Persona oluşturma hatası: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def get_persona(self, persona_id: str) -> Optional[Dict[str, Any]]:
        """Persona ID'ye göre persona bilgisini getir"""
        try:
            persona_data = self.user_storage.get_property('system', f'persona_{persona_id}')
            return persona_data
            
        except Exception as e:
            logger.error(f"Persona getirme hatası: {str(e)}")
            return None
    
    def get_all_personas(self) -> List[Dict[str, Any]]:
        """Tüm personaları getir"""
        try:
            system_properties = self.user_storage.get_all_properties('system')
            
            personas = []
            for prop_name, prop_value in system_properties.items():
                if prop_name.startswith('persona_') and isinstance(prop_value, dict):
                    personas.append(prop_value)
            
            return personas
            
        except Exception as e:
            logger.error(f"Tüm personaları getirme hatası: {str(e)}")
            return []
    
    def init_default_personas(self) -> int:
        """Varsayılan personaları oluştur"""
        default_personas = [
            {
                "id": "assistant",
                "name": "Genel Asistan",
                "description": "Genel amaçlı yardımcı asistan",
                "class_name": "PersonaAgent",
                "icon": "Users",
                "capabilities": ["general", "chat", "information"],
                "priority": 5,
                "owner": "system",
                "status": "active"
            },
            {
                "id": "task-executor",
                "name": "Görev Yürütücü",
                "description": "Sistem görevlerini yürüten asistan",
                "class_name": "TaskExecutorPersona",
                "icon": "Server",
                "capabilities": ["task_execution", "system", "command_execution"],
                "priority": 8,
                "owner": "system",
                "status": "active",
                "settings": {
                    "max_concurrent_tasks": 5,
                    "tool_categories": ["general"],
                    "tool_capabilities": ["file_management", "system_info", "command_execution"]
                }
            }
        ]
        
        created_count = 0
        for persona_data in default_personas:
            existing = self.get_persona(persona_data["id"])
            if not existing:
                result = self.create_persona(persona_data)
                if result["status"] == "success":
                    created_count += 1
        
        logger.info(f"{created_count} varsayılan persona oluşturuldu")
        return created_count

# Global instance
db_manager = DatabaseManager()