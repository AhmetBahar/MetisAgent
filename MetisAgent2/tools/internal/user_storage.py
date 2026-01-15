"""
SQLite tabanlı esnek user storage sistemi
EAV (Entity-Attribute-Value) modeli ile tüm user verileri
"""

import sqlite3
import json
import logging
import os
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, List
from cryptography.fernet import Fernet
import base64

logger = logging.getLogger(__name__)

class UserStorage:
    """SQLite tabanlı esnek kullanıcı veri depolama sistemi"""
    
    def __init__(self, db_path: str = "users.db"):
        """
        User Storage başlatır
        
        Args:
            db_path: SQLite veritabanı dosya yolu
        """
        self.db_path = db_path
        self.encryption_key = None
        self._init_encryption()
        self._init_database()
        
        logger.info(f"User Storage initialized: {db_path}")
    
    def _init_encryption(self):
        """Encryption key başlatır"""
        key_file = "storage.key"
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                self.encryption_key = f.read()
        else:
            self.encryption_key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(self.encryption_key)
            os.chmod(key_file, 0o600)
    
    def _init_database(self):
        """Database tabloları oluşturur"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_properties (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    property_name TEXT NOT NULL,
                    property_value TEXT,
                    is_encrypted INTEGER DEFAULT 0,
                    property_type TEXT DEFAULT 'string',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    UNIQUE(user_id, property_name)
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_properties_user_id 
                ON user_properties (user_id)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_properties_name 
                ON user_properties (property_name)
            ''')
            
            conn.commit()
    
    def _encrypt_value(self, value: str) -> str:
        """Değeri şifreler"""
        try:
            f = Fernet(self.encryption_key)
            encrypted = f.encrypt(value.encode('utf-8'))
            return base64.b64encode(encrypted).decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            return value
    
    def _decrypt_value(self, encrypted_value: str) -> str:
        """Şifreli değeri çözer"""
        try:
            f = Fernet(self.encryption_key)
            decoded = base64.b64decode(encrypted_value.encode('utf-8'))
            decrypted = f.decrypt(decoded)
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            return encrypted_value
    
    def create_user(self, user_id: str) -> bool:
        """
        Yeni kullanıcı oluşturur
        
        Args:
            user_id: Kullanıcı ID'si
            
        Returns:
            bool: Başarı durumu
        """
        try:
            now = datetime.now().isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR IGNORE INTO users (user_id, created_at, updated_at)
                    VALUES (?, ?, ?)
                ''', (user_id, now, now))
                
                conn.commit()
                
            logger.info(f"User created: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}")
            return False
    
    def set_property(self, user_id: str, property_name: str, property_value: Any,
                    encrypt: bool = False, property_type: str = 'string') -> bool:
        """
        Kullanıcı özelliği ayarlar
        
        Args:
            user_id: Kullanıcı ID'si
            property_name: Özellik adı
            property_value: Özellik değeri
            encrypt: Şifrelensin mi?
            property_type: Değer tipi (string, json, int, bool)
            
        Returns:
            bool: Başarı durumu
        """
        try:
            # User'ı oluştur (yoksa)
            self.create_user(user_id)
            
            # Değeri serialize et
            if property_type == 'json':
                value_str = json.dumps(property_value)
            elif property_type == 'bool':
                value_str = str(bool(property_value))
            elif property_type == 'int':
                value_str = str(int(property_value))
            else:
                value_str = str(property_value)
            
            # Şifreleme
            if encrypt:
                value_str = self._encrypt_value(value_str)
            
            now = datetime.now().isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO user_properties 
                    (user_id, property_name, property_value, is_encrypted, 
                     property_type, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, 
                           COALESCE((SELECT created_at FROM user_properties 
                                   WHERE user_id = ? AND property_name = ?), ?), 
                           ?)
                ''', (user_id, property_name, value_str, int(encrypt), 
                     property_type, user_id, property_name, now, now))
                
                # User updated_at güncelle
                conn.execute('''
                    UPDATE users SET updated_at = ? WHERE user_id = ?
                ''', (now, user_id))
                
                conn.commit()
                
            logger.info(f"Property set: {user_id}.{property_name} ({property_type})")
            return True
            
        except Exception as e:
            logger.error(f"Error setting property {user_id}.{property_name}: {e}")
            return False
    
    def get_property(self, user_id: str, property_name: str, 
                    default: Any = None) -> Any:
        """
        Kullanıcı özelliği getirir
        
        Args:
            user_id: Kullanıcı ID'si
            property_name: Özellik adı
            default: Varsayılan değer
            
        Returns:
            Any: Özellik değeri
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT property_value, is_encrypted, property_type
                    FROM user_properties
                    WHERE user_id = ? AND property_name = ?
                ''', (user_id, property_name))
                
                row = cursor.fetchone()
                
                if not row:
                    return default
                
                value_str, is_encrypted, property_type = row
                
                # Decrypt if needed
                if is_encrypted:
                    value_str = self._decrypt_value(value_str)
                
                # Deserialize
                if property_type == 'json':
                    return json.loads(value_str)
                elif property_type == 'bool':
                    return value_str.lower() in ('true', '1', 'yes')
                elif property_type == 'int':
                    return int(value_str)
                else:
                    return value_str
                    
        except Exception as e:
            logger.error(f"Error getting property {user_id}.{property_name}: {e}")
            return default
    
    def get_all_properties(self, user_id: str) -> Dict[str, Any]:
        """
        Kullanıcının tüm özelliklerini getirir
        
        Args:
            user_id: Kullanıcı ID'si
            
        Returns:
            Dict: Tüm özellikler
        """
        try:
            properties = {}
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT property_name, property_value, is_encrypted, property_type
                    FROM user_properties
                    WHERE user_id = ?
                ''', (user_id,))
                
                for row in cursor.fetchall():
                    prop_name, value_str, is_encrypted, prop_type = row
                    
                    # Decrypt if needed
                    if is_encrypted:
                        value_str = self._decrypt_value(value_str)
                    
                    # Deserialize
                    if prop_type == 'json':
                        properties[prop_name] = json.loads(value_str)
                    elif prop_type == 'bool':
                        properties[prop_name] = value_str.lower() in ('true', '1', 'yes')
                    elif prop_type == 'int':
                        properties[prop_name] = int(value_str)
                    else:
                        properties[prop_name] = value_str
                        
            return properties
            
        except Exception as e:
            logger.error(f"Error getting all properties for {user_id}: {e}")
            return {}
    
    def delete_property(self, user_id: str, property_name: str) -> bool:
        """
        Kullanıcı özelliğini siler
        
        Args:
            user_id: Kullanıcı ID'si  
            property_name: Özellik adı
            
        Returns:
            bool: Başarı durumu
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    DELETE FROM user_properties
                    WHERE user_id = ? AND property_name = ?
                ''', (user_id, property_name))
                
                conn.commit()
                
            logger.info(f"Property deleted: {user_id}.{property_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting property {user_id}.{property_name}: {e}")
            return False
    
    def delete_user(self, user_id: str) -> bool:
        """
        Kullanıcıyı ve tüm özelliklerini siler
        
        Args:
            user_id: Kullanıcı ID'si
            
        Returns:
            bool: Başarı durumu
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('DELETE FROM user_properties WHERE user_id = ?', (user_id,))
                conn.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
                conn.commit()
                
            logger.info(f"User deleted: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            return False
    
    def list_users(self) -> List[str]:
        """
        Tüm kullanıcıları listeler
        
        Returns:
            List[str]: Kullanıcı ID'leri
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('SELECT user_id FROM users ORDER BY created_at')
                return [row[0] for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return []
    
    def user_exists(self, user_id: str) -> bool:
        """
        Kullanıcının var olup olmadığını kontrol eder
        
        Args:
            user_id: Kullanıcı ID'si
            
        Returns:
            bool: Kullanıcı var mı?
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,))
                return cursor.fetchone() is not None
                
        except Exception as e:
            logger.error(f"Error checking user existence {user_id}: {e}")
            return False
    
    # Convenience methods for common use cases
    
    def set_api_key(self, user_id: str, provider: str, api_key: str, **metadata) -> bool:
        """API key kaydet (şifreli)"""
        key_data = {
            'api_key': api_key,
            'provider': provider,
            'metadata': metadata
        }
        return self.set_property(user_id, f'api_key_{provider}', key_data, 
                               encrypt=True, property_type='json')
    
    def get_api_key(self, user_id: str, provider: str) -> Optional[Dict]:
        """API key getir"""
        return self.get_property(user_id, f'api_key_{provider}')
    
    def set_oauth_token(self, user_id: str, provider: str, token_data: Dict) -> bool:
        """OAuth token kaydet (şifreli)"""
        return self.set_property(user_id, f'oauth_{provider}', token_data,
                               encrypt=True, property_type='json')
    
    def get_oauth_token(self, user_id: str, provider: str) -> Optional[Dict]:
        """OAuth token getir"""
        return self.get_property(user_id, f'oauth_{provider}')
    
    def set_user_mapping(self, user_id: str, external_service: str, external_id: str) -> bool:
        """User mapping kaydet"""
        return self.set_property(user_id, f'mapping_{external_service}', external_id)
    
    def get_user_mapping(self, user_id: str, external_service: str) -> Optional[str]:
        """User mapping getir"""
        return self.get_property(user_id, f'mapping_{external_service}')

# Global instance
_user_storage = UserStorage()

def get_user_storage() -> UserStorage:
    """Global user storage instance"""
    return _user_storage