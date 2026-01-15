# os_araci/db/chroma_manager.py

import os
import json
import uuid
import time
import secrets
from datetime import datetime
import logging
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class ChromaManager:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ChromaManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, base_path=None):
        if self._initialized:
            return
            
        self.base_path = base_path or os.path.join(os.getcwd(), "metis_data")
        os.makedirs(self.base_path, exist_ok=True)
        
        # ChromaDB istemcisini başlat
        #self.client = chromadb.Client(Settings(
        #    chroma_db_impl="duckdb+parquet",
        #    persist_directory=os.path.join(self.base_path, "chroma_db")
        #))
        self.client = chromadb.PersistentClient(path="./chroma_db")
        
        # Koleksiyonlar
        self.users_collection = self.client.get_or_create_collection("users")
        self.api_keys_collection = self.client.get_or_create_collection("api_keys")
        self.sessions_collection = self.client.get_or_create_collection("sessions")
        self.personas_collection = self.client.get_or_create_collection("personas")  # Yeni
        self.memories_collection = {} # Kullanıcı bellek koleksiyonları
        
        # Vektör modelini yükle
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            self.vector_search_available = True
        except ImportError:
            self.embedding_model = None
            self.vector_search_available = False
            print("SentenceTransformer yüklenemedi, vektör araması devre dışı.")
            
        self._initialized = True
    
    def get_memory_collection(self, username):
        """Kullanıcıya özel bellek koleksiyonunu getirir"""
        if username not in self.memories_collection:
            collection = self.client.get_or_create_collection(f"memories_{username}")
            self.memories_collection[username] = collection
        return self.memories_collection[username]
    
    # Kullanıcı yönetimi metodları
    def create_user(self, username, password_hash, permissions=None):
        """Yeni kullanıcı oluştur"""
        try:
            # Kullanıcının zaten var olup olmadığını kontrol et
            existing = self.get_user(username)
            if existing:
                return {"status": "error", "message": "Kullanıcı zaten mevcut"}
                
            # NULL değer hatalarından kaçınmak için JSON'u dizgeye çevir
            permissions_str = json.dumps(permissions or [])
            
            # Kullanıcı ID'si oluştur
            user_id = str(uuid.uuid4())
            
            # Kullanıcı bilgisini ekle
            self.users_collection.add(
                ids=[user_id],
                documents=[username],  # Kullanıcı adını döküman olarak kullan
                metadatas=[{
                    "username": username,
                    "password_hash": password_hash,
                    "permissions": permissions_str,  # JSON string olarak sakla
                    "created_at": datetime.now().isoformat(),
                    "last_login": ""  # NULL yerine boş string kullan
                }]
            )
            
            return {"status": "success", "user_id": user_id}
        except Exception as e:
            logger.error(f"Kullanıcı oluşturma hatası: {str(e)}")
            return {"status": "error", "message": str(e)} 
        
    def get_user(self, username):
        """Kullanıcı adına göre kullanıcı bilgisini getir"""
        try:
            logger.info(f"get_user çağrıldı: {username}")
            
            # Tam eşleşme için filtreleme kullanın
            results = self.users_collection.get(
                where={"username": username}
            )
            
            logger.info(f"get_user sorgu sonuçları: {results}")
            
            if results["ids"] and len(results["ids"]) > 0:
                user_id = results["ids"][0]
                metadata = results["metadatas"][0]
                
                try:
                    permissions = json.loads(metadata.get("permissions", "[]"))
                except:
                    permissions = []
                
                return {
                    "user_id": user_id,
                    "username": metadata.get("username"),
                    "password_hash": metadata.get("password_hash"),
                    "permissions": permissions,
                    "created_at": metadata.get("created_at"),
                    "last_login": metadata.get("last_login") if metadata.get("last_login") else None
                }
            logger.info(f"get_user: {username} için kullanıcı bulunamadı")
            return None
        except Exception as e:
            logger.error(f"get_user hatası: {str(e)}")
            return None
        
    def update_user_login(self, username):
        """Kullanıcının son oturum açma zamanını günceller"""
        user = self.get_user(username)
        if not user:
            return False
            
        # Son giriş zamanını güncelle
        metadata = self.users_collection.get(
            ids=[user["user_id"]]
        )["metadatas"][0]
        
        metadata["last_login"] = datetime.now().isoformat()
        
        # ChromaDB'de güncelleme - mevcut kaydı sil ve yeniden ekle
        self.users_collection.delete(ids=[user["user_id"]])
        
        dummy_vector = [0.0] * 384 if self.vector_search_available else None
        
        self.users_collection.add(
            ids=[user["user_id"]],
            embeddings=[dummy_vector] if dummy_vector else None,
            metadatas=[metadata],
            documents=[username]
        )
        
        return True
    
    # API anahtarı yönetimi
    def create_api_key(self, user_id, permissions=None):
        """Yeni API anahtarı oluşturur"""
        api_key = f"metis_{secrets.token_hex(16)}"
        created_at = datetime.now().isoformat()
        
        metadata = {
            "user_id": user_id,
            "permissions": json.dumps(permissions or ["read"]),
            "created_at": created_at,
            "last_used": None
        }
        
        dummy_vector = [0.0] * 384 if self.vector_search_available else None
        
        self.api_keys_collection.add(
            ids=[api_key],
            embeddings=[dummy_vector] if dummy_vector else None,
            metadatas=[metadata],
            documents=[api_key]
        )
        
        return api_key
    
    def validate_api_key(self, api_key):
        """API anahtarını doğrular"""
        results = self.api_keys_collection.get(
            ids=[api_key]
        )
        
        if not results["ids"]:
            return False
            
        # Son kullanım zamanını güncelle
        metadata = results["metadatas"][0]
        metadata["last_used"] = datetime.now().isoformat()
        
        # Güncelleme
        self.api_keys_collection.delete(ids=[api_key])
        
        dummy_vector = [0.0] * 384 if self.vector_search_available else None
        
        self.api_keys_collection.add(
            ids=[api_key],
            embeddings=[dummy_vector] if dummy_vector else None,
            metadatas=[metadata],
            documents=[api_key]
        )
        
        return True
    
    def get_api_key_info(self, api_key):
        """API anahtarı bilgilerini getirir"""
        results = self.api_keys_collection.get(
            ids=[api_key]
        )
        
        if not results["ids"]:
            return None
            
        metadata = results["metadatas"][0]
        
        return {
            "api_key": api_key,
            "user_id": metadata["user_id"],
            "permissions": json.loads(metadata["permissions"]),
            "created_at": metadata["created_at"],
            "last_used": metadata["last_used"]
        }
    
    def revoke_api_key(self, api_key):
        """API anahtarını iptal eder"""
        try:
            self.api_keys_collection.delete(ids=[api_key])
            return True
        except:
            return False
    
    # Oturum yönetimi
    def create_session(self, user_id, expires_in=3600):
        """Yeni oturum oluşturur"""
        session_token = secrets.token_hex(32)
        created_at = datetime.now().isoformat()
        expires_at = time.time() + expires_in
        
        metadata = {
            "user_id": user_id,
            "created_at": created_at,
            "expires_at": str(expires_at)
        }
        
        dummy_vector = [0.0] * 384 if self.vector_search_available else None
        
        self.sessions_collection.add(
            ids=[session_token],
            embeddings=[dummy_vector] if dummy_vector else None,
            metadatas=[metadata],
            documents=[session_token]
        )
        
        return session_token
    
    def validate_session(self, session_token):
        """Oturum token'ını doğrula"""
        try:
            results = self.sessions_collection.query(
                query_texts=[session_token],
                n_results=1
            )
            
            if results["ids"] and len(results["ids"][0]) > 0:
                session_id = results["ids"][0][0]
                metadata = results["metadatas"][0][0]
                
                # Oturum süresini kontrol et
                expires_at = datetime.fromisoformat(metadata.get("expires_at"))
                if datetime.now() > expires_at:
                    # Süresi dolmuş oturumu sil
                    self.sessions_collection.delete(ids=[session_id])
                    return None
                
                return metadata.get("user_id")
            return None
        except Exception as e:
            logger.error(f"Oturum doğrulama hatası: {str(e)}")
            return None
    
    def end_session(self, session_token):
        """Oturumu sonlandırır"""
        try:
            self.sessions_collection.delete(ids=[session_token])
            return True
        except:
            return False
    
    def cleanup_sessions(self):
        """Süresi dolmuş oturumları temizler"""
        current_time = time.time()
        expired_count = 0
        
        # Tüm oturumları getir
        all_sessions = self.sessions_collection.get()
        
        for i, (session_id, metadata) in enumerate(zip(all_sessions["ids"], all_sessions["metadatas"])):
            if current_time > float(metadata["expires_at"]):
                self.sessions_collection.delete(ids=[session_id])
                expired_count += 1
                
        return expired_count
    
    def create_persona(self, persona_data):
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
            
            # Persona verilerini hazırla
            metadata = {
                "persona_id": persona_id,
                "name": persona_data.get("name", ""),
                "description": persona_data.get("description", ""),
                "class_name": persona_data.get("class_name", "PersonaAgent"),
                "icon": persona_data.get("icon", "Users"),
                "capabilities": json.dumps(persona_data.get("capabilities", [])),
                "priority": str(persona_data.get("priority", 5)),
                "owner": persona_data.get("owner", "system"),
                "status": persona_data.get("status", "active"),
                "settings": json.dumps(persona_data.get("settings", {})),
                "personality_traits": json.dumps(persona_data.get("personality_traits", {})),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # ChromaDB'ye ekle
            self.personas_collection.add(
                ids=[persona_id],
                documents=[json.dumps(persona_data)],  # Tam veriyi doküman olarak sakla
                metadatas=[metadata]
            )
            
            logger.info(f"Persona oluşturuldu: {persona_id}")
            return {"status": "success", "persona_id": persona_id, "persona": persona_data}
            
        except Exception as e:
            logger.error(f"Persona oluşturma hatası: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def get_persona(self, persona_id):
        """Persona ID'ye göre persona bilgisini getir"""
        try:
            results = self.personas_collection.get(
                where={"persona_id": persona_id}
            )
            
            if results["ids"] and len(results["ids"]) > 0:
                metadata = results["metadatas"][0]
                document = results["documents"][0]
                
                # JSON'dan persona verisini parse et
                try:
                    persona_data = json.loads(document)
                except:
                    # Eğer doküman JSON değilse, metadata'dan oluştur
                    persona_data = {
                        "id": metadata.get("persona_id"),
                        "persona_id": metadata.get("persona_id"),
                        "name": metadata.get("name"),
                        "description": metadata.get("description"),
                        "class_name": metadata.get("class_name"),
                        "icon": metadata.get("icon"),
                        "capabilities": json.loads(metadata.get("capabilities", "[]")),
                        "priority": int(metadata.get("priority", 5)),
                        "owner": metadata.get("owner"),
                        "status": metadata.get("status"),
                        "settings": json.loads(metadata.get("settings", "{}")),
                        "personality_traits": json.loads(metadata.get("personality_traits", "{}")),
                        "created_at": metadata.get("created_at"),
                        "updated_at": metadata.get("updated_at")
                    }
                
                return persona_data
            return None
        except Exception as e:
            logger.error(f"Persona getirme hatası: {str(e)}")
            return None
    
    def get_all_personas(self):
        """Tüm personaları getir"""
        try:
            results = self.personas_collection.get()
            
            personas = []
            for i, (doc_id, document, metadata) in enumerate(zip(results["ids"], results["documents"], results["metadatas"])):
                try:
                    persona_data = json.loads(document)
                except:
                    # Eğer doküman JSON değilse, metadata'dan oluştur
                    persona_data = {
                        "id": metadata.get("persona_id"),
                        "persona_id": metadata.get("persona_id"),
                        "name": metadata.get("name"),
                        "description": metadata.get("description"),
                        "class_name": metadata.get("class_name"),
                        "icon": metadata.get("icon"),
                        "capabilities": json.loads(metadata.get("capabilities", "[]")),
                        "priority": int(metadata.get("priority", 5)),
                        "owner": metadata.get("owner"),
                        "status": metadata.get("status"),
                        "settings": json.loads(metadata.get("settings", "{}")),
                        "personality_traits": json.loads(metadata.get("personality_traits", "{}")),
                        "created_at": metadata.get("created_at"),
                        "updated_at": metadata.get("updated_at")
                    }
                
                personas.append(persona_data)
            
            return personas
        except Exception as e:
            logger.error(f"Tüm personaları getirme hatası: {str(e)}")
            return []
    
    def update_persona(self, persona_id, persona_data):
        """Mevcut personayı güncelle"""
        try:
            # Persona var mı kontrol et
            existing = self.get_persona(persona_id)
            if not existing:
                return {"status": "error", "message": f"Persona bulunamadı: {persona_id}"}
            
            # Mevcut veriyi yeni veriyle birleştir
            updated_data = existing.copy()
            updated_data.update(persona_data)
            updated_data["id"] = persona_id
            updated_data["persona_id"] = persona_id
            updated_data["updated_at"] = datetime.now().isoformat()
            
            # Metadata'yı hazırla
            metadata = {
                "persona_id": persona_id,
                "name": updated_data.get("name", ""),
                "description": updated_data.get("description", ""),
                "class_name": updated_data.get("class_name", "PersonaAgent"),
                "icon": updated_data.get("icon", "Users"),
                "capabilities": json.dumps(updated_data.get("capabilities", [])),
                "priority": str(updated_data.get("priority", 5)),
                "owner": updated_data.get("owner", "system"),
                "status": updated_data.get("status", "active"),
                "settings": json.dumps(updated_data.get("settings", {})),
                "personality_traits": json.dumps(updated_data.get("personality_traits", {})),
                "created_at": existing.get("created_at", datetime.now().isoformat()),
                "updated_at": updated_data["updated_at"]
            }
            
            # ChromaDB'de güncelle - önce sil, sonra ekle
            self.personas_collection.delete(where={"persona_id": persona_id})
            
            self.personas_collection.add(
                ids=[persona_id],
                documents=[json.dumps(updated_data)],
                metadatas=[metadata]
            )
            
            logger.info(f"Persona güncellendi: {persona_id}")
            return {"status": "success", "persona_id": persona_id, "persona": updated_data}
            
        except Exception as e:
            logger.error(f"Persona güncelleme hatası: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def delete_persona(self, persona_id):
        """Personayı sil"""
        try:
            # Varsayılan personaları silmeyi engelle
            default_personas = ["assistant", "social-media", "developer", "system", "task-executor"]
            if persona_id in default_personas:
                return {"status": "error", "message": "Varsayılan personalar silinemez"}
            
            # Persona var mı kontrol et
            existing = self.get_persona(persona_id)
            if not existing:
                return {"status": "error", "message": f"Persona bulunamadı: {persona_id}"}
            
            # ChromaDB'den sil
            self.personas_collection.delete(where={"persona_id": persona_id})
            
            logger.info(f"Persona silindi: {persona_id}")
            return {"status": "success", "message": f"Persona silindi: {persona_id}"}
            
        except Exception as e:
            logger.error(f"Persona silme hatası: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def init_default_personas(self):
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
                "id": "social-media",
                "name": "Sosyal Medya",
                "description": "Sosyal medya içeriği oluşturma ve yönetme",
                "class_name": "SocialMediaPersona",
                "icon": "Share2",
                "capabilities": ["social-media", "content-creation", "marketing"],
                "priority": 7,
                "owner": "system",
                "status": "active",
                "settings": {
                    "supported_platforms": ["instagram", "facebook", "linkedin", "twitter", "tiktok"],
                    "content_tone": "professional",
                    "default_language": "tr",
                    "max_posts_per_day": 15
                }
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
                    "tool_capabilities": ["file_management", "system_info"]
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