"""
Settings Manager - ChromaDB tabanlı ayarlar ve API key yönetimi

Bu modül kullanıcı ayarlarını, API keylerini ve authentication bilgilerini
ChromaDB üzerinde güvenli bir şekilde saklar ve yönetir.
"""

import json
import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
import chromadb
from chromadb.config import Settings as ChromaSettings

logger = logging.getLogger(__name__)

class SettingsManager:
    """ChromaDB tabanlı settings ve API key yönetimi"""
    
    def __init__(self, db_path: str = "metis_data/chroma_db"):
        """
        Settings Manager başlatır
        
        Args:
            db_path: ChromaDB veritabanı yolu
        """
        self.db_path = db_path
        self.client = None
        self.collection = None
        self.encryption_key = None
        self._initialize_db()
        self._initialize_encryption()
    
    def _initialize_db(self):
        """ChromaDB bağlantısını başlatır"""
        try:
            self.client = chromadb.PersistentClient(
                path=self.db_path,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Settings collection'ı oluştur veya al
            self.collection = self.client.get_or_create_collection(
                name="user_settings",
                metadata={"hnsw:space": "cosine"}
            )
            
            logger.info("ChromaDB settings collection başarıyla yüklendi")
            
        except Exception as e:
            logger.error(f"ChromaDB başlatma hatası: {e}")
            raise
    
    def _initialize_encryption(self):
        """Şifreleme anahtarını yükler veya oluşturur"""
        try:
            key_file = os.path.join(self.db_path, "encryption.key")
            
            if os.path.exists(key_file):
                with open(key_file, 'rb') as f:
                    self.encryption_key = f.read()
            else:
                # Yeni anahtar oluştur
                self.encryption_key = Fernet.generate_key()
                os.makedirs(os.path.dirname(key_file), exist_ok=True)
                with open(key_file, 'wb') as f:
                    f.write(self.encryption_key)
                    
            logger.info("Şifreleme anahtarı yüklendi")
            
        except Exception as e:
            logger.error(f"Şifreleme anahtarı hatası: {e}")
            raise
    
    def _encrypt_data(self, data: str) -> str:
        """Veriyi şifreler"""
        try:
            fernet = Fernet(self.encryption_key)
            encrypted = fernet.encrypt(data.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Şifreleme hatası: {e}")
            raise
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """Şifreli veriyi çözer"""
        try:
            fernet = Fernet(self.encryption_key)
            decoded = base64.b64decode(encrypted_data.encode())
            decrypted = fernet.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Şifre çözme hatası: {e}")
            raise
    
    def save_user_settings(self, user_id: str, settings: Dict[str, Any]) -> bool:
        """
        Kullanıcı ayarlarını kaydeder
        
        Args:
            user_id: Kullanıcı ID'si
            settings: Ayarlar dictionary'si
            
        Returns:
            bool: Başarı durumu
        """
        try:
            # Ayarları JSON'a çevir ve şifrele
            settings_json = json.dumps(settings)
            encrypted_settings = self._encrypt_data(settings_json)
            
            # Metadata
            metadata = {
                "user_id": user_id,
                "type": "user_settings",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # ChromaDB'ye kaydet
            document_id = f"user_settings_{user_id}"
            
            # Önce mevcut kaydı kontrol et
            try:
                existing = self.collection.get(ids=[document_id])
                if existing['ids']:
                    # Güncelle
                    self.collection.update(
                        ids=[document_id],
                        documents=[encrypted_settings],
                        metadatas=[metadata]
                    )
                else:
                    # Yeni kayıt
                    self.collection.add(
                        ids=[document_id],
                        documents=[encrypted_settings],
                        metadatas=[metadata]
                    )
            except:
                # Yeni kayıt
                self.collection.add(
                    ids=[document_id],
                    documents=[encrypted_settings],
                    metadatas=[metadata]
                )
            
            logger.info(f"Kullanıcı ayarları kaydedildi: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ayar kaydetme hatası: {e}")
            return False
    
    def get_user_settings(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Kullanıcı ayarlarını getirir
        
        Args:
            user_id: Kullanıcı ID'si
            
        Returns:
            Dict veya None: Kullanıcı ayarları
        """
        try:
            document_id = f"user_settings_{user_id}"
            result = self.collection.get(ids=[document_id])
            
            if not result['ids']:
                return None
            
            # Şifreli veriyi çöz
            encrypted_data = result['documents'][0]
            decrypted_data = self._decrypt_data(encrypted_data)
            settings = json.loads(decrypted_data)
            
            return settings
            
        except Exception as e:
            logger.error(f"Ayar getirme hatası: {e}")
            return None
    
    def save_api_key(self, user_id: str, service: str, api_key: str, 
                     additional_info: Optional[Dict[str, Any]] = None) -> bool:
        """
        API key'i güvenli şekilde kaydeder
        
        Args:
            user_id: Kullanıcı ID'si
            service: Servis adı (openai, huggingface, google, etc.)
            api_key: API anahtarı
            additional_info: Ek bilgiler
            
        Returns:
            bool: Başarı durumu
        """
        try:
            # API key'i şifrele
            encrypted_key = self._encrypt_data(api_key)
            
            # Ek bilgileri de şifrele
            if additional_info:
                additional_encrypted = self._encrypt_data(json.dumps(additional_info))
            else:
                additional_encrypted = None
            
            # Metadata
            metadata = {
                "user_id": user_id,
                "service": service,
                "type": "api_key",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # ChromaDB'ye kaydet
            document_id = f"api_key_{user_id}_{service}"
            
            api_data = {
                "encrypted_key": encrypted_key,
                "additional_info": additional_encrypted
            }
            
            try:
                existing = self.collection.get(ids=[document_id])
                if existing['ids']:
                    # Güncelle
                    self.collection.update(
                        ids=[document_id],
                        documents=[json.dumps(api_data)],
                        metadatas=[metadata]
                    )
                else:
                    # Yeni kayıt
                    self.collection.add(
                        ids=[document_id],
                        documents=[json.dumps(api_data)],
                        metadatas=[metadata]
                    )
            except:
                # Yeni kayıt
                self.collection.add(
                    ids=[document_id],
                    documents=[json.dumps(api_data)],
                    metadatas=[metadata]
                )
            
            logger.info(f"API key kaydedildi: {user_id} - {service}")
            return True
            
        except Exception as e:
            logger.error(f"API key kaydetme hatası: {e}")
            return False
    
    def get_api_key(self, user_id: str, service: str) -> Optional[Dict[str, Any]]:
        """
        API key'i getirir
        
        Args:
            user_id: Kullanıcı ID'si
            service: Servis adı
            
        Returns:
            Dict veya None: API key bilgileri
        """
        try:
            document_id = f"api_key_{user_id}_{service}"
            result = self.collection.get(ids=[document_id])
            
            if not result['ids']:
                return None
            
            # Veriyi çöz
            api_data = json.loads(result['documents'][0])
            decrypted_key = self._decrypt_data(api_data['encrypted_key'])
            
            response = {
                "api_key": decrypted_key,
                "service": service,
                "metadata": result['metadatas'][0]
            }
            
            # Ek bilgiler varsa çöz
            if api_data.get('additional_info'):
                additional_info = self._decrypt_data(api_data['additional_info'])
                response['additional_info'] = json.loads(additional_info)
            
            return response
            
        except Exception as e:
            logger.error(f"API key getirme hatası: {e}")
            return None
    
    def list_user_api_keys(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Kullanıcının tüm API keylerini listeler
        
        Args:
            user_id: Kullanıcı ID'si
            
        Returns:
            List: API key listesi (şifreli anahtarlar olmadan)
        """
        try:
            # Kullanıcının tüm API keylerini getir
            results = self.collection.get(
                where={"user_id": user_id, "type": "api_key"}
            )
            
            api_keys = []
            for i, doc_id in enumerate(results['ids']):
                metadata = results['metadatas'][i]
                api_keys.append({
                    "service": metadata['service'],
                    "created_at": metadata['created_at'],
                    "updated_at": metadata['updated_at'],
                    "has_key": True
                })
            
            return api_keys
            
        except Exception as e:
            logger.error(f"API key listesi hatası: {e}")
            return []
    
    def delete_api_key(self, user_id: str, service: str) -> bool:
        """
        API key'i siler
        
        Args:
            user_id: Kullanıcı ID'si
            service: Servis adı
            
        Returns:
            bool: Başarı durumu
        """
        try:
            document_id = f"api_key_{user_id}_{service}"
            self.collection.delete(ids=[document_id])
            
            logger.info(f"API key silindi: {user_id} - {service}")
            return True
            
        except Exception as e:
            logger.error(f"API key silme hatası: {e}")
            return False
    
    def save_oauth_token(self, user_id: str, provider: str, token_data: Dict[str, Any]) -> bool:
        """
        OAuth token'ı güvenli şekilde kaydeder
        
        Args:
            user_id: Kullanıcı ID'si
            provider: OAuth provider (google, github, etc.)
            token_data: Token bilgileri
            
        Returns:
            bool: Başarı durumu
        """
        try:
            # Token'ı şifrele
            encrypted_token = self._encrypt_data(json.dumps(token_data))
            
            # Metadata
            metadata = {
                "user_id": user_id,
                "provider": provider,
                "type": "oauth_token",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # ChromaDB'ye kaydet
            document_id = f"oauth_token_{user_id}_{provider}"
            
            try:
                existing = self.collection.get(ids=[document_id])
                if existing['ids']:
                    # Güncelle
                    self.collection.update(
                        ids=[document_id],
                        documents=[encrypted_token],
                        metadatas=[metadata]
                    )
                else:
                    # Yeni kayıt
                    self.collection.add(
                        ids=[document_id],
                        documents=[encrypted_token],
                        metadatas=[metadata]
                    )
            except:
                # Yeni kayıt
                self.collection.add(
                    ids=[document_id],
                    documents=[encrypted_token],
                    metadatas=[metadata]
                )
            
            logger.info(f"OAuth token kaydedildi: {user_id} - {provider}")
            return True
            
        except Exception as e:
            logger.error(f"OAuth token kaydetme hatası: {e}")
            return False
    
    def get_oauth_token(self, user_id: str, provider: str) -> Optional[Dict[str, Any]]:
        """
        OAuth token'ı getirir
        
        Args:
            user_id: Kullanıcı ID'si
            provider: OAuth provider
            
        Returns:
            Dict veya None: Token bilgileri
        """
        try:
            document_id = f"oauth_token_{user_id}_{provider}"
            result = self.collection.get(ids=[document_id])
            
            if not result['ids']:
                return None
            
            # Şifreli veriyi çöz
            encrypted_data = result['documents'][0]
            decrypted_data = self._decrypt_data(encrypted_data)
            token_data = json.loads(decrypted_data)
            
            return token_data
            
        except Exception as e:
            logger.error(f"OAuth token getirme hatası: {e}")
            return None
    
    def is_oauth_token_valid(self, user_id: str, provider: str) -> bool:
        """
        OAuth token'ın geçerliliğini kontrol eder
        
        Args:
            user_id: Kullanıcı ID'si
            provider: OAuth provider
            
        Returns:
            bool: Token geçerli mi?
        """
        try:
            token_data = self.get_oauth_token(user_id, provider)
            if not token_data:
                return False
            
            # Expire kontrolü
            if 'expires_at' in token_data:
                expires_at = datetime.fromisoformat(token_data['expires_at'])
                if datetime.now() > expires_at:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"OAuth token geçerlilik kontrolü hatası: {e}")
            return False
    
    def cleanup_expired_tokens(self) -> int:
        """
        Süresi dolmuş tokenları temizler
        
        Returns:
            int: Temizlenen token sayısı
        """
        try:
            # Tüm OAuth tokenları getir
            results = self.collection.get(
                where={"type": "oauth_token"}
            )
            
            expired_ids = []
            for i, doc_id in enumerate(results['ids']):
                try:
                    encrypted_data = results['documents'][i]
                    decrypted_data = self._decrypt_data(encrypted_data)
                    token_data = json.loads(decrypted_data)
                    
                    if 'expires_at' in token_data:
                        expires_at = datetime.fromisoformat(token_data['expires_at'])
                        if datetime.now() > expires_at:
                            expired_ids.append(doc_id)
                except:
                    continue
            
            # Süresi dolmuş tokenları sil
            if expired_ids:
                self.collection.delete(ids=expired_ids)
            
            logger.info(f"Süresi dolmuş {len(expired_ids)} token temizlendi")
            return len(expired_ids)
            
        except Exception as e:
            logger.error(f"Token temizleme hatası: {e}")
            return 0

# Global instance
settings_manager = SettingsManager()