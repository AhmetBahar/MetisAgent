# os_araci/tools/memory_manager.py

from os_araci.mcp_core.tool import MCPTool
import json
import os
from datetime import datetime
import uuid
import logging
import chromadb
from chromadb.config import Settings
from pathlib import Path

logger = logging.getLogger(__name__)

class MemoryManager(MCPTool):
    def __init__(self, registry):
        super().__init__(
            name="memory_manager",
            description="Bellek ve persona context yönetimi aracı",
            version="1.0.0",
            category="general"
        )
        self.registry = registry
        self.base_storage_path = os.path.join(os.getcwd(), "memory_storage")
        self.current_user = "default"
        
        # ChromaDB istemcisini başlat - hatalar ignore edilir
        self.chroma_client = None
        try:
            import chromadb
            from chromadb.config import Settings
            self.chroma_client = chromadb.Client(Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=os.path.join(self.base_storage_path, "chroma_db")
            ))
            logger.info("ChromaDB başarıyla başlatıldı")
        except Exception as e:
            logger.warning(f"ChromaDB başlatılamadı, sadece JSON kullanılacak: {str(e)}")
            self.chroma_client = None
            
        # Vektör modeli yüklemeyi dene - hatalar ignore edilir
        self.embedding_model = None
        self.vector_search_available = False
        
        try:
            from sentence_transformers import SentenceTransformer
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            self.vector_search_available = True
            logger.info("Vektör modeli başarıyla yüklendi")
        except Exception as e:
            logger.warning(f"Vektör modeli yüklenemedi, sadece JSON kullanılacak: {str(e)}")
            self.embedding_model = None
            self.vector_search_available = False
            
        # Düzenli JSON depolama için yolları güncelle
        self.update_paths()
    
    def update_paths(self):
        """Kullanıcıya özel yolları günceller ve ilgili koleksiyonu oluşturur"""
        self.user_storage_path = os.path.join(self.base_storage_path, self.current_user)
        self.memory_file = os.path.join(self.user_storage_path, "memory.json")
        
        # Yedek JSON depolaması için dizini oluştur
        self.ensure_storage_exists()
        
        # ChromaDB koleksiyonunu al (eğer ChromaDB mevcutsa)
        if self.chroma_client:
            try:
                self.collection = self.chroma_client.get_or_create_collection(
                    name=f"memories_{self.current_user}",
                    metadata={"user": self.current_user}
                )
                logger.info(f"ChromaDB koleksiyonu başarıyla açıldı: memories_{self.current_user}")
            except Exception as e:
                logger.error(f"ChromaDB koleksiyonu açılamadı: {str(e)}")
                self.chroma_client = None  # ChromaDB'yi devre dışı bırak ve JSON'a geri dön
    
    def ensure_storage_exists(self):
        """Bellek dosyalarının saklanacağı klasörün varlığını kontrol eder."""
        if not os.path.exists(self.user_storage_path):
            os.makedirs(self.user_storage_path)
        if not os.path.exists(self.memory_file):
            with open(self.memory_file, "w") as f:
                json.dump({"memories": []}, f)
    
    def get_all_actions(self):
        """MCPTool arayüzüne uygun olarak tüm aksiyonları döndürür"""
        return {
            "store_memory": self.store_memory,
            "retrieve_memories": self.retrieve_memories,
            "update_memory": self.update_memory,
            "delete_memory": self.delete_memory,
            "clear_all_memories": self.clear_all_memories,
            "search_by_similarity": self.search_by_similarity,
            "set_user": self.set_user,
            # Persona context metodları
            "save_persona_context": self.save_persona_context,
            "get_persona_context": self.get_persona_context,
            "update_persona_state": self.update_persona_state,
            "clear_persona_session": self.clear_persona_session
        }
    
    def set_user(self, username):
        """Aktif kullanıcıyı değiştirir"""
        self.current_user = username
        self.update_paths()
        return {"status": "success", "message": f"Active user set to {username}"}
    
    def store_memory(self, content, category="general", tags=None):
        """Yeni bir bellek kaydı ekler."""
        if tags is None:
            tags = []
            
        # Bellek için benzersiz ID oluştur
        memory_id = str(len(self.load_memory_data()["memories"]) + 1)
        timestamp = datetime.now().isoformat()
        
        # ChromaDB kullanılabilir mi kontrol et
        if self.chroma_client:
            try:
                # Metadata hazırla
                metadata = {
                    "id": memory_id,
                    "category": category,
                    "tags": json.dumps(tags),
                    "timestamp": timestamp
                }
                
                # İçeriği vektörleştir ve veritabanına ekle
                if self.vector_search_available:
                    # Embedding oluştur
                    embedding = self.embedding_model.encode(content).tolist()
                    
                    # Koleksiyona ekle
                    self.collection.add(
                        ids=[memory_id],
                        embeddings=[embedding],
                        metadatas=[metadata],
                        documents=[content]
                    )
                else:
                    # Vektör desteği yoksa sadece doküman ekle
                    self.collection.add(
                        ids=[memory_id],
                        metadatas=[metadata],
                        documents=[content]
                    )
                    
                logger.info(f"Bellek kaydı ChromaDB'ye eklendi: {memory_id}")
                
                # Yedek JSON depolamasına da ekle
                self._add_to_json_storage(memory_id, content, category, tags, timestamp)
                
                return {"status": "success", "memory_id": memory_id}
            except Exception as e:
                logger.error(f"ChromaDB'ye yazma hatası, JSON kullanılıyor: {str(e)}")
                # ChromaDB başarısız olursa JSON ile devam et
        
        # JSON'a kaydetme yöntemi
        return self._add_to_json_storage(memory_id, content, category, tags, timestamp)
    
    def _add_to_json_storage(self, memory_id, content, category, tags, timestamp):
        """JSON veritabanına bellek kaydeder"""
        memory_data = self.load_memory_data()
        
        new_memory = {
            "id": int(memory_id),
            "timestamp": timestamp,
            "content": content,
            "category": category,
            "tags": tags
        }
        
        memory_data["memories"].append(new_memory)
        
        with open(self.memory_file, "w") as f:
            json.dump(memory_data, f, indent=2)
            
        return {"status": "success", "memory_id": memory_id}
    
    def retrieve_memories(self, query=None, category=None, tags=None, limit=10):
        """Bellek kayıtlarını filtrelerle geri getirir."""
        # ChromaDB kullanılabilir mi kontrol et
        if self.chroma_client:
            try:
                # Filtreleme koşullarını hazırla
                where_clause = {}
                
                if category:
                    where_clause["category"] = category
                
                # Sorgu ve filtreleri uygula
                if query and self.vector_search_available:
                    # Vektör tabanlı benzerlik araması
                    query_embedding = self.embedding_model.encode(query).tolist()
                    results = self.collection.query(
                        query_embeddings=[query_embedding],
                        where=where_clause,
                        n_results=100  # Daha fazla sonuç alıp sonradan filtreleyeceğiz
                    )
                    memories = self._process_chroma_results(results, tags, query, limit)
                    return {"memories": memories}
                else:
                    # Metin tabanlı arama (tüm belgeleri getir ve filtrele)
                    results = self.collection.get(
                        where=where_clause,
                        limit=100
                    )
                    memories = self._process_chroma_results(results, tags, query, limit)
                    return {"memories": memories}
            except Exception as e:
                logger.error(f"ChromaDB sorgu hatası, JSON kullanılıyor: {str(e)}")
        
        # JSON'dan getirme yöntemi
        memory_data = self.load_memory_data()
        filtered_memories = memory_data["memories"]
        
        # Filtreleme işlemleri
        if category:
            filtered_memories = [m for m in filtered_memories if m["category"] == category]
            
        if tags:
            filtered_memories = [m for m in filtered_memories 
                                if any(tag in m["tags"] for tag in tags)]
            
        if query:
            filtered_memories = [m for m in filtered_memories 
                                if query.lower() in m["content"].lower()]
        
        # Son eklenenler başta olacak şekilde sırala
        filtered_memories.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return {"memories": filtered_memories[:limit]}
    
    def _process_chroma_results(self, results, tags=None, query=None, limit=10):
        """ChromaDB sonuçlarını işle ve formatla"""
        memories = []
        
        if not results["ids"]:
            return memories
        
        for i, (id, document, metadata) in enumerate(zip(
            results["ids"],
            results["documents"],
            results["metadatas"]
        )):
            # Etiket filtrelemesi
            if tags:
                memory_tags = json.loads(metadata.get("tags", "[]"))
                if not any(tag in memory_tags for tag in tags):
                    continue
                    
            # İçerik filtrelemesi (vektör araması yoksa ve query varsa)
            if query and not self.vector_search_available:
                if query.lower() not in document.lower():
                    continue
                    
            memories.append({
                "id": int(id),
                "content": document,
                "category": metadata.get("category", "general"),
                "tags": json.loads(metadata.get("tags", "[]")),
                "timestamp": metadata.get("timestamp")
            })
                
        # Son eklenenleri başta göster
        memories.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return memories[:limit]
    
    def update_memory(self, memory_id, content=None, category=None, tags=None):
        """Belirli bir bellek kaydını günceller."""
        # Sayısal memory_id'yi string'e çevir (karşılaştırma için)
        if isinstance(memory_id, int):
            memory_id = str(memory_id)
            
        # ChromaDB kullanılabilir mi kontrol et
        if self.chroma_client:
            try:
                # Mevcut bellek kaydını getir
                results = self.collection.get(ids=[memory_id])
                
                if results["ids"]:
                    existing_document = results["documents"][0]
                    existing_metadata = results["metadatas"][0]
                    
                    # Yeni değerleri hazırla
                    updated_content = content if content is not None else existing_document
                    updated_metadata = dict(existing_metadata)
                    
                    if category is not None:
                        updated_metadata["category"] = category
                        
                    if tags is not None:
                        updated_metadata["tags"] = json.dumps(tags)
                        
                    # Kaydı sil ve güncelle
                    self.collection.delete(ids=[memory_id])
                    
                    # Yeni vektör oluştur
                    if self.vector_search_available:
                        embedding = self.embedding_model.encode(updated_content).tolist()
                        
                        self.collection.add(
                            ids=[memory_id],
                            embeddings=[embedding],
                            metadatas=[updated_metadata],
                            documents=[updated_content]
                        )
                    else:
                        self.collection.add(
                            ids=[memory_id],
                            metadatas=[updated_metadata],
                            documents=[updated_content]
                        )
                        
                    logger.info(f"Bellek kaydı ChromaDB'de güncellendi: {memory_id}")
                    
                    # JSON depolamayı da güncelle
                    self._update_json_storage(int(memory_id), content, category, tags)
                    
                    return {
                        "status": "success", 
                        "memory": {
                            "id": int(memory_id),
                            "content": updated_content,
                            "category": updated_metadata["category"],
                            "tags": json.loads(updated_metadata["tags"]),
                            "timestamp": updated_metadata["timestamp"]
                        }
                    }
            except Exception as e:
                logger.error(f"ChromaDB güncelleme hatası, JSON kullanılıyor: {str(e)}")
        
        # JSON güncelleme yöntemi
        return self._update_json_storage(int(memory_id), content, category, tags)
    
    def _update_json_storage(self, memory_id, content=None, category=None, tags=None):
        """JSON veritabanında bellek günceller"""
        memory_data = self.load_memory_data()
        
        for memory in memory_data["memories"]:
            if memory["id"] == memory_id:
                if content is not None:
                    memory["content"] = content
                if category is not None:
                    memory["category"] = category
                if tags is not None:
                    memory["tags"] = tags
                
                with open(self.memory_file, "w") as f:
                    json.dump(memory_data, f, indent=2)
                
                return {"status": "success", "memory": memory}
        
        return {"status": "error", "message": f"Memory with ID {memory_id} not found"}
    
    def delete_memory(self, memory_id):
        """Belirli bir bellek kaydını siler."""
        # Sayısal memory_id'yi string'e çevir (karşılaştırma için)
        chroma_id = str(memory_id) if isinstance(memory_id, int) else memory_id
        
        # ChromaDB kullanılabilir mi kontrol et
        if self.chroma_client:
            try:
                # Mevcut bellek kaydını kontrol et
                results = self.collection.get(ids=[chroma_id])
                
                if results["ids"]:
                    # Kaydı sil
                    self.collection.delete(ids=[chroma_id])
                    logger.info(f"Bellek kaydı ChromaDB'den silindi: {chroma_id}")
                    
                    # JSON depolamadan da sil
                    self._delete_from_json_storage(int(chroma_id))
                    
                    return {"status": "success", "message": f"Memory {memory_id} deleted"}
            except Exception as e:
                logger.error(f"ChromaDB silme hatası, JSON kullanılıyor: {str(e)}")
        
        # JSON silme yöntemi
        return self._delete_from_json_storage(memory_id)
    
    def _delete_from_json_storage(self, memory_id):
        """JSON veritabanından bellek siler"""
        memory_data = self.load_memory_data()
        
        initial_count = len(memory_data["memories"])
        memory_data["memories"] = [m for m in memory_data["memories"] if m["id"] != memory_id]
        
        if len(memory_data["memories"]) < initial_count:
            with open(self.memory_file, "w") as f:
                json.dump(memory_data, f, indent=2)
            return {"status": "success", "message": f"Memory {memory_id} deleted"}
        else:
            return {"status": "error", "message": f"Memory with ID {memory_id} not found"}
    
    def load_memory_data(self):
        """Bellek verilerini dosyadan yükler."""
        with open(self.memory_file, "r") as f:
            return json.load(f)
    
    def clear_all_memories(self):
        """Tüm bellek kayıtlarını temizler."""
        # ChromaDB kullanılabilir mi kontrol et
        if self.chroma_client:
            try:
                # Tüm kayıtları getir
                results = self.collection.get()
                
                # Tüm kayıtları sil
                if results["ids"]:
                    self.collection.delete(ids=results["ids"])
                    
                logger.info("Tüm bellek kayıtları ChromaDB'den temizlendi")
            except Exception as e:
                logger.error(f"ChromaDB temizleme hatası: {str(e)}")
        
        # JSON depolamayı temizle
        with open(self.memory_file, "w") as f:
            json.dump({"memories": []}, f)
            
        return {"status": "success", "message": "All memories cleared"}
    
    def search_by_similarity(self, query, limit=5):
        """İçerik benzerliğine göre bellek kayıtlarını arar."""
        # ChromaDB ve vektör arama kullanılabilir mi kontrol et
        if self.chroma_client and self.vector_search_available:
            try:
                # Vektör tabanlı arama
                query_embedding = self.embedding_model.encode(query).tolist()
                
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=limit
                )
                
                memories = []
                
                if results["ids"] and len(results["ids"]) > 0:
                    for id, document, metadata in zip(
                        results["ids"][0],  # ChromaDB query birçok sorgu için sonuç döndürebilir
                        results["documents"][0],
                        results["metadatas"][0]
                    ):
                        memories.append({
                            "id": int(id),
                            "content": document,
                            "category": metadata.get("category", "general"),
                            "tags": json.loads(metadata.get("tags", "[]")),
                            "timestamp": metadata.get("timestamp")
                        })
                        
                return {"memories": memories, "method": "vector"}
            except Exception as e:
                logger.error(f"ChromaDB benzerlik araması hatası: {str(e)}")
        
        # Basit kelime eşleşmesi kullan
        memory_data = self.load_memory_data()
        
        # Her belleğin query ile benzerlik puanını hesapla
        scored_memories = []
        query_words = set(query.lower().split())
        
        for memory in memory_data["memories"]:
            content_words = set(memory["content"].lower().split())
            # Basit Jaccard benzerliği
            if len(query_words) > 0 and len(content_words) > 0:
                similarity = len(query_words.intersection(content_words)) / len(query_words.union(content_words))
                scored_memories.append((memory, similarity))
        
        # Benzerlik skoruna göre sırala
        scored_memories.sort(key=lambda x: x[1], reverse=True)
        
        # En benzer olanları döndür
        return {"memories": [m[0] for m in scored_memories[:limit]]}
    
    def save_persona_context(self, persona_id, user_id, context_data):
        """Persona için context bilgilerini saklar"""
        try:
            # Context için benzersiz ID oluştur
            context_key = f"persona_context_{persona_id}_{user_id}"
            
            # Timestamp ekle
            context_data["last_updated"] = datetime.now().isoformat()
            context_data["persona_id"] = persona_id
            context_data["user_id"] = user_id
            
            # ChromaDB'ye kaydet
            if self.chroma_client:
                try:
                    # Metadata hazırla
                    metadata = {
                        "type": "persona_context",
                        "persona_id": persona_id,
                        "user_id": user_id,
                        "timestamp": context_data["last_updated"]
                    }
                    
                    # Context'i string olarak sakla
                    content = json.dumps(context_data)
                    
                    # Vektörleştir ve kaydet
                    if self.vector_search_available:
                        embedding = self.embedding_model.encode(content).tolist()
                        self.collection.upsert(
                            ids=[context_key],
                            embeddings=[embedding],
                            metadatas=[metadata],
                            documents=[content]
                        )
                    else:
                        self.collection.upsert(
                            ids=[context_key],
                            metadatas=[metadata],
                            documents=[content]
                        )
                        
                    logger.info(f"Persona context saved to ChromaDB: {context_key}")
                    
                except Exception as e:
                    logger.error(f"ChromaDB persona context save failed: {str(e)}")
            
            # JSON backup'a da kaydet
            self._save_persona_context_json(context_key, context_data)
            
            return {"status": "success", "context_key": context_key}
            
        except Exception as e:
            logger.error(f"Persona context save error: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def get_persona_context(self, persona_id, user_id):
        """Persona context bilgilerini getirir"""
        try:
            context_key = f"persona_context_{persona_id}_{user_id}"
            
            # Önce ChromaDB'den dene
            if self.chroma_client:
                try:
                    results = self.collection.get(
                        ids=[context_key],
                        include=["documents", "metadatas"]
                    )
                    
                    if results['documents']:
                        context_data = json.loads(results['documents'][0])
                        logger.info(f"Persona context loaded from ChromaDB: {context_key}")
                        return {"status": "success", "context": context_data}
                        
                except Exception as e:
                    logger.error(f"ChromaDB persona context load failed: {str(e)}")
            
            # ChromaDB başarısızsa JSON'dan yükle
            return self._get_persona_context_json(context_key)
            
        except Exception as e:
            logger.error(f"Persona context get error: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def update_persona_state(self, persona_id, user_id, state_updates):
        """Persona state'ini günceller (merge eder)"""
        try:
            # Mevcut context'i al
            current_result = self.get_persona_context(persona_id, user_id)
            
            if current_result["status"] == "success":
                current_context = current_result["context"]
            else:
                current_context = {}
            
            # State güncellemelerini merge et
            updated_context = {**current_context, **state_updates}
            
            # Güncellenmiş context'i kaydet
            return self.save_persona_context(persona_id, user_id, updated_context)
            
        except Exception as e:
            logger.error(f"Persona state update error: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def clear_persona_session(self, persona_id, user_id):
        """Persona session'ını temizler"""
        try:
            context_key = f"persona_context_{persona_id}_{user_id}"
            
            # ChromaDB'den sil
            if self.chroma_client:
                try:
                    self.collection.delete(ids=[context_key])
                    logger.info(f"Persona context deleted from ChromaDB: {context_key}")
                except Exception as e:
                    logger.error(f"ChromaDB persona context delete failed: {str(e)}")
            
            # JSON'dan da sil
            self._clear_persona_context_json(context_key)
            
            return {"status": "success", "message": "Persona session cleared"}
            
        except Exception as e:
            logger.error(f"Persona session clear error: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def _save_persona_context_json(self, context_key, context_data):
        """JSON dosyasına persona context kaydeder"""
        try:
            self.ensure_storage_exists()
            
            # Persona context dosyası
            persona_context_file = os.path.join(self.user_storage_path, "persona_contexts.json")
            
            # Mevcut dosyayı yükle
            if os.path.exists(persona_context_file):
                with open(persona_context_file, 'r', encoding='utf-8') as f:
                    contexts = json.load(f)
            else:
                contexts = {}
            
            # Yeni context'i ekle/güncelle
            contexts[context_key] = context_data
            
            # Dosyaya kaydet
            with open(persona_context_file, 'w', encoding='utf-8') as f:
                json.dump(contexts, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Persona context saved to JSON: {context_key}")
            
        except Exception as e:
            logger.error(f"JSON persona context save error: {str(e)}")
    
    def _get_persona_context_json(self, context_key):
        """JSON dosyasından persona context getirir"""
        try:
            persona_context_file = os.path.join(self.user_storage_path, "persona_contexts.json")
            
            if not os.path.exists(persona_context_file):
                return {"status": "not_found", "context": {}}
            
            with open(persona_context_file, 'r', encoding='utf-8') as f:
                contexts = json.load(f)
            
            if context_key in contexts:
                logger.info(f"Persona context loaded from JSON: {context_key}")
                return {"status": "success", "context": contexts[context_key]}
            else:
                return {"status": "not_found", "context": {}}
                
        except Exception as e:
            logger.error(f"JSON persona context get error: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def _clear_persona_context_json(self, context_key):
        """JSON dosyasından persona context siler"""
        try:
            persona_context_file = os.path.join(self.user_storage_path, "persona_contexts.json")
            
            if os.path.exists(persona_context_file):
                with open(persona_context_file, 'r', encoding='utf-8') as f:
                    contexts = json.load(f)
                
                if context_key in contexts:
                    del contexts[context_key]
                    
                    with open(persona_context_file, 'w', encoding='utf-8') as f:
                        json.dump(contexts, f, ensure_ascii=False, indent=2)
                        
                    logger.info(f"Persona context deleted from JSON: {context_key}")
                    
        except Exception as e:
            logger.error(f"JSON persona context clear error: {str(e)}")

    def check_health(self):
        """Aracın sağlık durumunu kontrol eder."""
        health_status = {
            "status": "healthy",
            "storage_type": "ChromaDB + JSON" if self.chroma_client else "JSON only",
            "vector_search": "available" if self.vector_search_available else "unavailable",
            "current_user": self.current_user
        }
        
        return health_status

# Module-level register function
def register_tool(registry):
    """Memory Manager aracını registry'e kaydeder"""
    memory_manager = MemoryManager(registry)
    return registry.register_local_tool(memory_manager)