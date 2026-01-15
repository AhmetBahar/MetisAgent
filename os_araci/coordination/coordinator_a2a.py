# coordination/coordinator_a2a.py
import asyncio
import logging
import time
import os
import json
from typing import Dict, Any, List, Optional, Union
from os_araci.a2a_protocol.registry import A2ARegistry
from os_araci.a2a_protocol.message import A2AMessage
from os_araci.mcp_core.registry import MCPRegistry
from os_araci.personas.persona_agent import PersonaAgent
from os_araci.coordination.coordinator import MCPCoordinator
from os_araci.db.chroma_manager import ChromaManager
from os_araci.websocket.event_emitter import EventEmitter

logger = logging.getLogger(__name__)

class MCPCoordinatorA2A:
    """MCPCoordinator için A2A protokolü entegrasyonu"""
    
    def __init__(self, coordinator: MCPCoordinator, event_emitter=None):
        """MCPCoordinator A2A entegrasyonu başlatıcı"""
        self.coordinator = coordinator
        self.event_emitter = event_emitter
        self.db_manager = ChromaManager()
        self.a2a_registry = A2ARegistry()
        self.mcp_registry = MCPRegistry()

        self.active_personas = {} 
        self._persona_classes = {}  
        self._initialized = False  
        self._load_persona_classes()
        # İçsel A2A persona ID'si
        self.persona_id = "system.coordinator"
        
        # Yanıt bekleme listesi
        self._reply_waiters = {}  # message_id -> asyncio.Future
        
        # Personalar için dosya yolu
        self.personas_file = os.path.join(os.getcwd(), 'personas.json')
    
    def _load_persona_classes(self):
        """Mevcut persona sınıflarını yükle"""
        try:
            # PersonaFactory kullan
            from os_araci.personas.persona_factory import PersonaFactory
            self.persona_factory = PersonaFactory()
            
            # Otomatik keşfet ve kaydet
            count = self.persona_factory.auto_discover_and_register()
            
            # Factory'den sınıfları al
            self._persona_classes = {}
            for class_name in self.persona_factory.list_available_classes():
                # Dinamik olarak sınıfı al
                self._persona_classes[class_name] = self.persona_factory._persona_classes[class_name]
            
            logger.info(f"{len(self._persona_classes)} persona sınıfı yüklendi")
        except Exception as e:
            logger.error(f"Persona sınıfları yüklenirken hata: {str(e)}", exc_info=True)

    async def initialize(self) -> bool:
        """A2A protokolü entegrasyonunu başlat"""
        try:
            if self._initialized:
                return True
                
            # A2A Registry'yi başlat
            await self.a2a_registry.start()
            
            # Coordinator personasını kaydet
            await self._register_coordinator_persona()
            
            # ChromaDB'den personaları yükle
            await self._load_personas_from_db()
            
            # Eğer DB boşsa, JSON dosyasından yükle
            personas = self.db_manager.get_all_personas()
            if not personas:
                await self._load_personas_from_file_to_db()
            
            # Dinleyicileri kaydet
            self._register_listeners()
            
            self._initialized = True
            logger.info("MCPCoordinator A2A protokolü entegrasyonu başlatıldı")
            return True
        except Exception as e:
            logger.error(f"A2A protokolü başlatma hatası: {str(e)}")
            return False    
        
    async def get_runtime_info(self):
        """Tüm personaların runtime bilgilerini getir"""
        runtime_info = {}
        for persona_id, persona_agent in self.active_personas.items():
            runtime_info[persona_id] = {
                'status': persona_agent.status,
                'is_online': persona_agent.is_initialized,
                'active_tasks': len(persona_agent._current_tasks),
                'last_activity': persona_agent.task_metrics.get('last_task_time')
            }
        return runtime_info
        
    async def get_persona_runtime_info(self, persona_id):
        """Belirli bir personanın runtime bilgilerini getir"""
        if persona_id in self.active_personas:
            agent = self.active_personas[persona_id]
            return {
                'is_online': agent.is_initialized,
                'status': agent.status,
                'current_tasks': list(agent._current_tasks.keys()),
                'metrics': agent.task_metrics
            }
        return None
    
    async def register_new_persona(self, persona_data):
        """Yeni personayı A2A sistemine kaydet ve başlat"""
        try:
            class_name = persona_data.get('class_name', 'PersonaAgent')
            # Dinamik olarak sınıfı yükle
            agent_class = self._load_persona_class(class_name)
            # Agent örneği oluştur
            agent = agent_class(**persona_data)
            # Başlat
            await agent.initialize()
            # Registry'e ekle
            self.active_personas[persona_data['id']] = agent
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def _load_personas_from_file(self) -> bool:
        """Personaları JSON dosyasından yükle"""
        try:
            if os.path.exists(self.personas_file):
                with open(self.personas_file, 'r', encoding='utf-8') as f:
                    personas_data = json.load(f)
                
                # Basit persona sınıfı
                class SimplePersona:
                    def __init__(self, data):
                        self.id = data.get("id")
                        self.name = data.get("name", "Unnamed")
                        self.description = data.get("description", "")
                        self.capabilities = data.get("capabilities", [])
                        self.status = data.get("status", "active")
                        self.icon = data.get("icon", "Users")
                    
                    def to_dict(self):
                        return {
                            "id": self.id,
                            "name": self.name,
                            "description": self.description,
                            "capabilities": self.capabilities,
                            "status": self.status,
                            "icon": self.icon
                        }
                    
                    async def handle_message(self, message):
                        # Varsayılan mesaj işleyici
                        logger.warning(f"Varsayılan persona mesaj işleyici çağrıldı: {self.id}")
                
                # Her bir personayı registry'e kaydet
                for persona_data in personas_data:
                    persona_id = persona_data.get("id")
                    if not persona_id:
                        continue
                    
                    # Persona zaten registry'de var mı?
                    if persona_id in self.a2a_registry._personas:
                        continue
                    
                    # Yeni persona oluştur ve kaydet
                    persona = SimplePersona(persona_data)
                    
                    # Registry'e kaydet
                    self.a2a_registry._personas[persona_id] = persona
                    
                    # Yetenek indeksini güncelle
                    for capability in persona_data.get("capabilities", []):
                        if capability not in self.a2a_registry._capability_index:
                            self.a2a_registry._capability_index[capability] = []
                        if persona_id not in self.a2a_registry._capability_index[capability]:
                            self.a2a_registry._capability_index[capability].append(persona_id)
                
                logger.info(f"{len(personas_data)} persona dosyadan yüklendi")
                return True
            else:
                logger.info("Persona dosyası bulunamadı, varsayılan personalar oluşturulacak")
                return False
        except Exception as e:
            logger.error(f"Personalar dosyadan yüklenemedi: {str(e)}")
            return False
    
    async def _save_personas_to_file(self) -> bool:
        """Personaları JSON dosyasına kaydet"""
        try:
            # Tüm personaları al
            personas = await self.get_personas()
            
            # JSON dosyasına yaz
            with open(self.personas_file, 'w', encoding='utf-8') as f:
                json.dump(personas, f, ensure_ascii=False, indent=2)
            
            logger.info(f"{len(personas)} persona dosyaya kaydedildi")
            return True
        except Exception as e:
            logger.error(f"Personalar dosyaya kaydedilemedi: {str(e)}")
            return False
    
    async def _register_coordinator_persona(self) -> None:
        """Coordinator'u A2A protokolüne kaydet"""
        # Bu bir gerçek persona değil, sadece mesaj gönderme/alma için
        # Coordinator A2A "persona" bilgileri
        coordinator_info = {
            "persona_id": self.persona_id,
            "name": "System Coordinator",
            "description": "Görev koordinasyonu ve sistem yönetimi",
            "capabilities": ["task_coordination", "registry_management", "persona_discovery"]
        }
        
        # Coordinator'ü registry'ye kaydet
        if self.persona_id in self.a2a_registry._personas:
            logger.info(f"Coordinator persona zaten kayıtlı: {self.persona_id}")
        else:
            # Sahte bir persona referansı ekle
            self.a2a_registry._personas[self.persona_id] = lambda: self
            
            # Yetenekler indeksini güncelle
            for capability in coordinator_info["capabilities"]:
                if capability not in self.a2a_registry._capability_index:
                    self.a2a_registry._capability_index[capability] = []
                self.a2a_registry._capability_index[capability].append(self.persona_id)
            
            logger.info(f"Coordinator persona kaydedildi: {self.persona_id}")
    
    def _register_listeners(self) -> None:
        """A2A protokolü için mesaj dinleyicileri kaydet"""
        # Coordinator için özel mesaj tipleri
        self.a2a_registry.register_listener("task.request", self.handle_task_request)
        self.a2a_registry.register_listener("tool.request", self.handle_tool_request)
        self.a2a_registry.register_listener("registry.query", self.handle_registry_query)
        self.a2a_registry.register_listener("persona.discovery", self.handle_persona_discovery)
    
    async def handle_message(self, message: A2AMessage) -> None:
        """Coordinator A2A persona mesaj işleyicisi"""
        # Bu sahte "persona" için mesaj işleyicisi
        # Zaten register_listener ile tüm mesaj tipleri için dinleyiciler kaydedilmiş olduğundan
        # bu metod nadiren çağrılır (sadece özel durumlar için)
        logger.warning(f"Beklenmeyen doğrudan mesaj: {message.message_type}, gönderen: {message.sender}")

    async def initialize(self) -> bool:
        """A2A protokolü entegrasyonunu başlat"""
        try:
            # A2A Registry'yi başlat
            await self.a2a_registry.start()
            
            # Coordinator personasını kaydet
            await self._register_coordinator_persona()
            
            # Varsayılan personaları kaydet
            await self._register_default_personas()
            
            # Dinleyicileri kaydet
            self._register_listeners()
            
            logger.info("MCPCoordinator A2A protokolü entegrasyonu başlatıldı")
            return True
        except Exception as e:
            logger.error(f"A2A protokolü başlatma hatası: {str(e)}")
            return False

    async def create_persona(self, persona_data: Dict[str, Any]) -> Dict[str, Any]:
        """Yeni bir persona oluştur (ChromaDB + A2A)"""
        persona_id = persona_data.get("id")
        if not persona_id:
            return {"status": "error", "message": "ID alanı zorunludur"}
        
        # Varsayılan personaları kontrol et
        default_ids = ["assistant", "social-media", "developer", "system"]
        if persona_id in default_ids:
            return {"status": "error", "message": f"Bu ID zaten varsayılan bir persona için kullanılıyor: {persona_id}"}
        
        try:
            # ChromaDB'ye ekle
            result = self.db_manager.create_persona(persona_data)
            
            if result["status"] == "success":
                # A2A registry'ye de ekle
                class SimplePersona:
                    def __init__(self, data):
                        self.id = data.get("id")
                        self.name = data.get("name", "Unnamed")
                        self.description = data.get("description", "")
                        self.capabilities = data.get("capabilities", [])
                        self.status = data.get("status", "active")
                        self.icon = data.get("icon", "Users")
                    
                    def to_dict(self):
                        return {
                            "id": self.id,
                            "name": self.name,
                            "description": self.description,
                            "capabilities": self.capabilities,
                            "status": self.status,
                            "icon": self.icon
                        }
                
                        # A2A registry'ye ekle
                import weakref
                self.a2a_registry._personas[persona_id] = weakref.ref(persona)
                
                if not hasattr(self, '_created_personas'):
                    self._created_personas = {}
                self._created_personas[persona_id] = persona

                # Yetenek indeksini güncelle
                for capability in persona_data.get("capabilities", []):
                    if capability not in self.a2a_registry._capability_index:
                        self.a2a_registry._capability_index[capability] = []
                    if persona_id not in self.a2a_registry._capability_index[capability]:
                        self.a2a_registry._capability_index[capability].append(persona_id)
                
                # JSON dosyasına kaydet
                await self._save_personas_to_file()
                
                # Otomatik başlat
                if persona_data.get('status') == 'active':
                    start_result = await self.start_persona(persona_id, persona_data)
                    result['started'] = start_result.get('status') == 'success'
                else:
                    result['started'] = False
                
                return result
            
            return result
            
        except Exception as e:
            logger.error(f"Persona oluşturulurken hata: {str(e)}")
            return {"status": "error", "message": f"Persona oluşturulurken hata: {str(e)}"}    

    async def delete_persona(self, persona_id: str) -> Dict[str, Any]:
        """Bir personayı sil"""
        # Varsayılan personaları kontrol et
        default_ids = ["assistant", "social-media", "developer", "system"]
        if persona_id in default_ids:
            return {"status": "error", "message": f"Varsayılan personalar silinemez: {persona_id}"}
        
        try:
            # A2A registry'den personayı sil
            if hasattr(self.a2a_registry, 'unregister_persona'):
                # Önce personayı al
                persona = self.a2a_registry.get_persona(persona_id)
                if not persona:
                    return {"status": "error", "message": f"Persona bulunamadı: {persona_id}"}
                
                # Personayı sil
                del self.a2a_registry._personas[persona_id]
                
                # Yetenek indeksinden de sil
                for capability, persona_list in list(self.a2a_registry._capability_index.items()):
                    if persona_id in persona_list:
                        self.a2a_registry._capability_index[capability].remove(persona_id)
                
                # Personaları dosyaya kaydet
                await self._save_personas_to_file()
                
                return {
                    "status": "success",
                    "message": f"Persona başarıyla silindi: {persona_id}"
                }
            else:
                return {"status": "error", "message": f"A2A registry persona silmeyi desteklemiyor"}
        except Exception as e:
            logger.error(f"Persona silinirken hata: {str(e)}")
            return {"status": "error", "message": f"Persona silinirken hata: {str(e)}"}
        
    async def _register_default_personas(self) -> None:
        """Varsayılan personaları registry'e kaydet"""
        # Varsayılan personaların tanımları
        default_personas = [
            {
                "id": "assistant",
                "name": "Genel Asistan",
                "description": "Genel amaçlı yardımcı asistan",
                "icon": "Users",
                "capabilities": ["general", "chat", "information"],
                "status": "active"
            },
            {
                "id": "social-media",
                "name": "Sosyal Medya",
                "description": "Sosyal medya içeriği oluşturma ve yönetme",
                "icon": "Share2",
                "capabilities": ["social-media", "content-creation", "marketing"],
                "status": "active"
            },
            {
                "id": "developer",
                "name": "Geliştirici",
                "description": "Kod geliştirme ve teknik görevler",
                "icon": "Code",
                "capabilities": ["development", "coding", "debugging"],
                "status": "active"
            },
            {
                "id": "system",
                "name": "Sistem Yöneticisi",
                "description": "Sistem işlemleri ve yönetimi",
                "icon": "Server",
                "capabilities": ["system", "administration", "monitoring"],
                "status": "active"
            }
        ]
        
        # Basit persona sınıfı
        class SimplePersona:
            def __init__(self, data):
                self.id = data.get("id")
                self.name = data.get("name", "Unnamed")
                self.description = data.get("description", "")
                self.capabilities = data.get("capabilities", [])
                self.status = data.get("status", "active")
                self.icon = data.get("icon", "Users")
            
            def to_dict(self):
                return {
                    "id": self.id,
                    "name": self.name,
                    "description": self.description,
                    "capabilities": self.capabilities,
                    "status": self.status,
                    "icon": self.icon
                }
        
        # Her bir varsayılan personayı registry'e kaydet
        for persona_data in default_personas:
            persona_id = persona_data["id"]
            
            # Persona zaten registry'de var mı?
            if persona_id in self.a2a_registry._personas:
                logger.info(f"Varsayılan persona zaten registry'de: {persona_id}")
                continue
            
            # Yeni persona oluştur ve kaydet
            try:
                # SimplePersona nesnesi oluştur
                persona = SimplePersona(persona_data)
                
                # Registry'e weakref olarak kaydet
                import weakref
                self.a2a_registry._personas[persona_id] = weakref.ref(persona)
                
                # Personayı ayrıca sakla ki garbage collection'a gitmesin
                if not hasattr(self, '_default_personas'):
                    self._default_personas = {}
                self._default_personas[persona_id] = persona
                
                # Yetenek indeksini güncelle
                for capability in persona_data["capabilities"]:
                    if not hasattr(self.a2a_registry, '_capability_index'):
                        self.a2a_registry._capability_index = {}
                    
                    if capability not in self.a2a_registry._capability_index:
                        self.a2a_registry._capability_index[capability] = []
                    
                    if persona_id not in self.a2a_registry._capability_index[capability]:
                        self.a2a_registry._capability_index[capability].append(persona_id)
                
                logger.info(f"Varsayılan persona kaydedildi: {persona_id}")
            except Exception as e:
                logger.error(f"Varsayılan persona kaydedilemedi {persona_id}: {str(e)}")
                
    async def get_personas(self) -> List[Dict[str, Any]]:
        """Tüm personaları döndür (ChromaDB + Runtime)"""
        try:
            # Önce ChromaDB'den personaları al
            personas = self.db_manager.get_all_personas()
            
            # Eğer ChromaDB boşsa, JSON dosyasından yükle
            if not personas:
                personas = await self._load_personas_from_file_to_db()
            
            # Runtime bilgileri ekle
            for persona in personas:
                persona_id = persona.get('id')
                if persona_id in self.active_personas:
                    agent = self.active_personas[persona_id]
                    persona['is_online'] = True
                    persona['runtime_status'] = agent.status
                    persona['active_tasks'] = len(agent._current_tasks)
                else:
                    persona['is_online'] = False
                    persona['runtime_status'] = 'offline'
                    persona['active_tasks'] = 0
            
            # Herhangi bir persona bulunamadıysa varsayılanları kaydet
            if not personas:
                await self._register_default_personas()
                personas = self.db_manager.get_all_personas()
            
            return personas
            
        except Exception as e:
            logger.error(f"Personalar alınırken hata: {str(e)}")
            # Varsayılan personaları döndür
            return self._get_default_personas()

    def _get_default_personas(self):
        """Varsayılan personaları döndür"""
        return [
            {
                "id": "assistant",
                "name": "Genel Asistan",
                "description": "Genel amaçlı yardımcı asistan",
                "icon": "Users",
                "capabilities": ["general", "chat", "information"],
                "status": "active"
            },
            {
                "id": "social-media",
                "name": "Sosyal Medya",
                "description": "Sosyal medya içeriği oluşturma ve yönetme",
                "icon": "Share2",
                "capabilities": ["social-media", "content-creation", "marketing"],
                "status": "active"
            },
            {
                "id": "developer",
                "name": "Geliştirici",
                "description": "Kod geliştirme ve teknik görevler",
                "icon": "Code",
                "capabilities": ["development", "coding", "debugging"],
                "status": "active"
            },
            {
                "id": "system",
                "name": "Sistem Yöneticisi",
                "description": "Sistem işlemleri ve yönetimi",
                "icon": "Server",
                "capabilities": ["system", "administration", "monitoring"],
                "status": "active"
            }
        ]    
    
    async def handle_task_request(self, message: A2AMessage) -> None:
        """Görev isteği mesajlarını işle"""
        if message.receiver != self.persona_id:
            # Bu mesaj bize değil, atlat
            return
        
        # İstek içeriğini al
        task = message.content.get("task", {})
        context = message.content.get("context", {})
        
        if not task:
            # Geçersiz istek
            reply = message.create_reply(
                content={"status": "error", "message": "No task specified in request"},
                message_type="task.response"
            )
            await self.a2a_registry.send_message(reply)
            return
        
        try:
            # MCPCoordinator ile görevi çalıştır
            logger.info(f"MCPCoordinator ile görev çalıştırılıyor: {task.get('name', 'Unnamed Task')}")
            
            # Coordinator metodunu asenkron çağır
            if hasattr(self.coordinator, "execute_task_async"):
                result = await self.coordinator.execute_task_async(task, context)
            else:
                # Senkron metodu asenkron event loop içinde çağır
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(None, lambda: self.coordinator.execute_task(task))
            
            # Context güncellemeleri
            context_updates = {}
            if isinstance(result, dict) and "context_updates" in result:
                context_updates = result.get("context_updates", {})
            
            # Yanıt gönder
            reply = message.create_reply(
                content={
                    "status": "success" if result.get("status") != "error" else "error",
                    "task_id": task.get("id", ""),
                    "result": result,
                    "context_updates": context_updates
                },
                message_type="task.response"
            )
            await self.a2a_registry.send_message(reply)
            
        except Exception as e:
            logger.error(f"Görev çalıştırma hatası: {str(e)}")
            
            # Hata yanıtı
            reply = message.create_reply(
                content={
                    "status": "error",
                    "message": f"Error executing task: {str(e)}"
                },
                message_type="task.response"
            )
            await self.a2a_registry.send_message(reply)
    
    async def handle_tool_request(self, message: A2AMessage) -> None:
        """Araç talebi mesajlarını işle"""
        if message.receiver != self.persona_id:
            # Bu mesaj bize değil, atlat
            return
        
        # İstek içeriğini al
        tool_id = message.content.get("tool_id")
        action = message.content.get("action")
        params = message.content.get("params", {})
        
        if not tool_id or not action:
            # Geçersiz istek
            reply = message.create_reply(
                content={"status": "error", "message": "Missing tool_id or action"},
                message_type="tool.response"
            )
            await self.a2a_registry.send_message(reply)
            return
        
        try:
            # MCP Registry ile aracı çağır
            logger.info(f"MCP aracı çağrılıyor: {tool_id}.{action}")
            result = self.mcp_registry.call_handler(tool_id, action, **params)
            
            # Yanıt gönder
            reply = message.create_reply(
                content={
                    "status": "success" if not isinstance(result, tuple) else "error",
                    "result": result[0] if isinstance(result, tuple) else result
                },
                message_type="tool.response"
            )
            await self.a2a_registry.send_message(reply)
            
        except Exception as e:
            logger.error(f"Araç çağırma hatası: {str(e)}")
            
            # Hata yanıtı
            reply = message.create_reply(
                content={
                    "status": "error",
                    "message": f"Error calling tool: {str(e)}"
                },
                message_type="tool.response"
            )
            await self.a2a_registry.send_message(reply)
    
# coordination/coordinator_a2a.py (devam)
    async def handle_registry_query(self, message: A2AMessage) -> None:
        """Registry sorgusu mesajlarını işle"""
        if message.receiver != self.persona_id:
            # Bu mesaj bize değil, atlat
            return
        
        # İstek tipini al
        query_type = message.content.get("query_type")
        filters = message.content.get("filters", {})
        
        try:
            result = {}
            
            if query_type == "list_tools":
                # Tüm araçları listele
                all_metadata = self.mcp_registry.get_all_metadata()
                tools_data = []
                
                for tool_id, metadata in all_metadata.items():
                    # Filtreleme yapılacak mı?
                    if "source_type" in filters and metadata.source_type.value != filters["source_type"]:
                        continue
                    if "category" in filters and metadata.category != filters["category"]:
                        continue
                    
                    tools_data.append(metadata.to_dict())
                
                result = {"tools": tools_data, "count": len(tools_data)}
                
            elif query_type == "get_tool":
                # Belirli bir aracın detaylarını getir
                tool_id = filters.get("tool_id")
                if not tool_id:
                    raise ValueError("Missing tool_id in filters")
                
                metadata = self.mcp_registry.get_metadata(tool_id)
                if not metadata:
                    raise ValueError(f"Tool not found: {tool_id}")
                
                tool = self.mcp_registry.get_tool_by_id(tool_id)
                details = {}
                
                if hasattr(tool, 'describe') and callable(getattr(tool, 'describe')):
                    details = tool.describe()
                
                result = {
                    "tool_id": tool_id,
                    "metadata": metadata.to_dict(),
                    "details": details
                }
                
            elif query_type == "get_actions":
                # Aracın aksiyonlarını listele
                tool_id = filters.get("tool_id")
                if not tool_id:
                    raise ValueError("Missing tool_id in filters")
                
                tool = self.mcp_registry.get_tool_by_id(tool_id)
                if not tool:
                    raise ValueError(f"Tool not found: {tool_id}")
                
                actions = []
                if hasattr(tool, 'get_all_actions') and callable(getattr(tool, 'get_all_actions')):
                    actions = list(tool.get_all_actions().keys())
                
                result = {
                    "tool_id": tool_id,
                    "actions": actions
                }
                
            elif query_type == "get_capabilities":
                # Tüm araçların yeteneklerini listele
                capabilities = set()
                
                for tool_id, metadata in self.mcp_registry.get_all_metadata().items():
                    capabilities.update(metadata.capabilities)
                
                result = {
                    "capabilities": sorted(list(capabilities))
                }
                
            else:
                # Desteklenmeyen sorgu tipi
                raise ValueError(f"Unsupported query type: {query_type}")
            
            # Yanıt gönder
            reply = message.create_reply(
                content={
                    "status": "success",
                    "result": result
                },
                message_type="registry.response"
            )
            await self.a2a_registry.send_message(reply)
            
        except Exception as e:
            logger.error(f"Registry sorgusu hatası: {str(e)}")
            
            # Hata yanıtı
            reply = message.create_reply(
                content={
                    "status": "error",
                    "message": f"Error processing registry query: {str(e)}"
                },
                message_type="registry.response"
            )
            await self.a2a_registry.send_message(reply)
    
    async def handle_persona_discovery(self, message: A2AMessage) -> None:
        """Persona keşif mesajlarını işle"""
        if message.receiver != self.persona_id:
            # Bu mesaj bize değil, atlat
            return
        
        # İstek içeriğini al
        discovery_type = message.content.get("discovery_type", "list_all")
        filters = message.content.get("filters", {})
        
        try:
            result = {}
            
            if discovery_type == "list_all":
                # Tüm personaları listele
                persona_ids = self.a2a_registry.list_personas()
                personas = []
                
                for persona_id in persona_ids:
                    persona = self.a2a_registry.get_persona(persona_id)
                    if persona and hasattr(persona, 'to_dict'):
                        personas.append(persona.to_dict())
                    elif persona:
                        # Basit bilgi
                        personas.append({
                            "persona_id": persona_id,
                            "name": getattr(persona, 'name', 'Unknown'),
                            "status": getattr(persona, 'status', 'unknown')
                        })
                
                result = {"personas": personas, "count": len(personas)}
                
            elif discovery_type == "find_by_capability":
                # Belirli yeteneklere sahip personaları bul
                capabilities = filters.get("capabilities", [])
                match_all = filters.get("match_all", True)
                
                if not capabilities:
                    raise ValueError("No capabilities specified in filters")
                
                persona_ids = self.a2a_registry.find_personas_by_capabilities(capabilities, match_all)
                personas = []
                
                for persona_id in persona_ids:
                    persona = self.a2a_registry.get_persona(persona_id)
                    if persona and hasattr(persona, 'to_dict'):
                        personas.append(persona.to_dict())
                    elif persona:
                        # Basit bilgi
                        personas.append({
                            "persona_id": persona_id,
                            "name": getattr(persona, 'name', 'Unknown'),
                            "capabilities": getattr(persona, 'capabilities', []),
                            "status": getattr(persona, 'status', 'unknown')
                        })
                
                result = {"personas": personas, "count": len(personas)}
                
            elif discovery_type == "get_persona":
                # Belirli bir personanın detaylarını getir
                persona_id = filters.get("persona_id")
                if not persona_id:
                    raise ValueError("Missing persona_id in filters")
                
                persona = self.a2a_registry.get_persona(persona_id)
                if not persona:
                    raise ValueError(f"Persona not found: {persona_id}")
                
                if hasattr(persona, 'to_dict'):
                    result = {"persona": persona.to_dict()}
                else:
                    # Basit bilgi
                    result = {
                        "persona": {
                            "persona_id": persona_id,
                            "name": getattr(persona, 'name', 'Unknown'),
                            "capabilities": getattr(persona, 'capabilities', []),
                            "status": getattr(persona, 'status', 'unknown')
                        }
                    }
            
            else:
                # Desteklenmeyen keşif tipi
                raise ValueError(f"Unsupported discovery type: {discovery_type}")
            
            # Yanıt gönder
            reply = message.create_reply(
                content={
                    "status": "success",
                    "result": result
                },
                message_type="persona.discovery.response"
            )
            await self.a2a_registry.send_message(reply)
            
        except Exception as e:
            logger.error(f"Persona keşif hatası: {str(e)}")
            
            # Hata yanıtı
            reply = message.create_reply(
                content={
                    "status": "error",
                    "message": f"Error processing persona discovery: {str(e)}"
                },
                message_type="persona.discovery.response"
            )
            await self.a2a_registry.send_message(reply)
    
    async def execute_task_with_persona(self, 
                                      task: Dict[str, Any], 
                                      context: Dict[str, Any] = None, 
                                      target_persona: str = None,
                                      timeout: float = 120.0) -> Dict[str, Any]:
        """Görevi belirli bir persona ile çalıştır veya uygun persona seç"""
        if context is None:
            context = {}
        
        # Uygun persona bul (özel belirtilmemişse)
        if not target_persona:
            target_persona = await self._find_best_persona_for_task(task)
            
            if not target_persona:
                logger.error("Görev için uygun persona bulunamadı")
                return {
                    "status": "error",
                    "message": "No suitable persona found for task execution"
                }
        
        # Görev isteği gönder
        logger.info(f"Görev {target_persona} personasına gönderiliyor: {task.get('name', 'Unnamed Task')}")
        
        try:
            # İstek-yanıt modeli ile görev çalıştır
            response = await self.a2a_registry.request_reply(
                sender=self.persona_id,
                receiver=target_persona,
                message_type="task.request",
                content={
                    "task": task,
                    "context": context
                },
                timeout=timeout
            )
            
            if not response:
                logger.error(f"Görev yanıtı zaman aşımına uğradı: {target_persona}")
                return {
                    "status": "error",
                    "message": f"Task response timed out after {timeout}s"
                }
            
            # Yanıtı dönüştür
            result = response.content
            
            # Context güncellemelerini uygula
            if "context_updates" in result:
                context.update(result["context_updates"])
            
            return result
            
        except Exception as e:
            logger.error(f"Görev çalıştırma hatası: {str(e)}")
            return {
                "status": "error",
                "message": f"Error executing task with persona: {str(e)}"
            }
    
    async def _find_best_persona_for_task(self, task: Dict[str, Any]) -> Optional[str]:
        """Görev için en uygun personayı bul"""
        # Görev tipine göre gerekli yetenekleri belirle
        required_capabilities = ["task_execution"]  # Temel yetenek
        
        # Özel görev tiplerine göre yetenekler ekle
        if "tool" in task and task["tool"]:
            # Araç kullanımı gerektiren görev
            tool_name = task["tool"]
            required_capabilities.append("tool_execution")
            
            # Araç kategorisine göre ek yetenekler
            tool_id = self.mcp_registry.get_latest_version(tool_name)
            if tool_id:
                metadata = self.mcp_registry.get_metadata(tool_id)
                if metadata and metadata.category:
                    required_capabilities.append(f"{metadata.category}_expertise")
        
        elif "command" in task and task["command"]:
            # Komut çalıştırma görevi
            required_capabilities.append("command_execution")
            
            # Komut içeriğine göre ek yetenekler
            command = task["command"].lower()
            if "file" in command or "dir" in command:
                required_capabilities.append("file_management")
            if "network" in command or "ping" in command or "curl" in command:
                required_capabilities.append("network_management")
        
        # En uygun personayı bul
        matching_personas = self.a2a_registry.find_personas_by_capabilities(required_capabilities, match_all=False)
        
        if not matching_personas:
            # Hiç uygun persona bulunamadı
            logger.warning(f"Gerekli yeteneklere sahip persona bulunamadı: {required_capabilities}")
            
            # Sadece temel task_execution yeteneğini ara
            matching_personas = self.a2a_registry.find_personas_by_capability("task_execution")
            
            if not matching_personas:
                logger.error("Görev çalıştırabilecek hiçbir persona bulunamadı")
                return None
        
        # Personaları durumlarına göre filtreleme
        available_personas = []
        
        for persona_id in matching_personas:
            persona = self.a2a_registry.get_persona(persona_id)
            if persona and hasattr(persona, 'status') and persona.status != "disabled":
                available_personas.append(persona_id)
        
        if not available_personas:
            logger.warning("Uygun durumda persona bulunamadı")
            return None
        
        # İdeal olarak "idle" durumundaki bir persona seç
        idle_personas = []
        
        for persona_id in available_personas:
            persona = self.a2a_registry.get_persona(persona_id)
            if persona and hasattr(persona, 'status') and persona.status == "idle":
                idle_personas.append(persona_id)
        
        if idle_personas:
            # En yüksek öncelikli "idle" personayı seç
            best_persona = None
            best_priority = -1
            
            for persona_id in idle_personas:
                persona = self.a2a_registry.get_persona(persona_id)
                if persona and hasattr(persona, 'priority'):
                    priority = getattr(persona, 'priority', 0)
                    if priority > best_priority:
                        best_priority = priority
                        best_persona = persona_id
            
            return best_persona or idle_personas[0]
        
        # Idle persona yoksa, herhangi bir uygun personayı seç
        return available_personas[0]
    
    # os_araci/coordination/coordinator_a2a.py dosyasında
# message_handlers yapısına bellek işlemi desteği ekleyin

    async def handle_memory_operations(self, message):
        """Memory işlemlerini yönetir"""
        try:
            # Registry'den memory_manager aracını bul
            memory_tool = None
            for tool_id, metadata in self.coordinator.registry.get_all_metadata().items():
                if metadata.name == 'memory_manager':
                    memory_tool = self.coordinator.registry.get_tool_by_id(tool_id)
                    break
                    
            if not memory_tool:
                return {"status": "error", "message": "Memory manager not found"}
            
            # İstenilen aksiyonu belirle
            action = message.content.get("action")
            params = message.content.get("params", {})
            
            # Aksiyon tipine göre işlem yap
            if action == "store":
                result = self.coordinator.registry.call_handler(tool_id, "store_memory", 
                                        content=params.get("content"),
                                        category=params.get("category", "general"),
                                        tags=params.get("tags", []))
                
            elif action == "retrieve":
                result = self.coordinator.registry.call_handler(tool_id, "retrieve_memories", 
                                        query=params.get("query"),
                                        category=params.get("category"),
                                        tags=params.get("tags"),
                                        limit=params.get("limit", 10))
                
            elif action == "update":
                result = self.coordinator.registry.call_handler(tool_id, "update_memory", 
                                        memory_id=params.get("memory_id"),
                                        content=params.get("content"),
                                        category=params.get("category"),
                                        tags=params.get("tags"))
                
            elif action == "delete":
                result = self.coordinator.registry.call_handler(tool_id, "delete_memory", 
                                        memory_id=params.get("memory_id"))
                
            elif action == "clear":
                result = self.coordinator.registry.call_handler(tool_id, "clear_all_memories")
                
            elif action == "search":
                result = self.coordinator.registry.call_handler(tool_id, "search_by_similarity", 
                                        query=params.get("query"),
                                        limit=params.get("limit", 5))
                
            elif action == "set_user":
                result = self.coordinator.registry.call_handler(tool_id, "set_user", 
                                        username=params.get("username"))
                
            else:
                result = {"status": "error", "message": f"Unknown memory action: {action}"}
            
            return result
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def shutdown(self) -> None:
        """A2A protokolü entegrasyonunu kapat"""
        try:
            # A2A Registry'yi durdur
            await self.a2a_registry.stop()
            
            # Coordinator personasını kaldır
            self.a2a_registry.unregister_persona(self.persona_id)
            
            logger.info("MCPCoordinator A2A protokolü entegrasyonu kapatıldı")
        except Exception as e:
            logger.error(f"A2A protokolü kapatma hatası: {str(e)}")

    async def start_persona(self, persona_id: str, persona_data: Optional[Dict] = None):
        """Personayı başlat"""
        try:
            # Eğer zaten aktifse
            if persona_id in self.active_personas:
                logger.info(f"Persona zaten aktif: {persona_id}")
                return {"status": "success", "message": f"Persona zaten aktif: {persona_id}"}
            
            # Persona verilerini al
            if not persona_data:
                # Önce DB'den dene
                persona_data = self.db_manager.get_persona(persona_id)
                
                # DB'de yoksa varsayılan personalardan al
                if not persona_data:
                    default_personas = self._get_default_personas()
                    persona_data = next((p for p in default_personas if p.get('id') == persona_id), None)
            
            if not persona_data:
                logger.error(f"Persona verisi bulunamadı: {persona_id}")
                return {"status": "error", "message": f"Persona bulunamadı: {persona_id}"}
            
            # Persona sınıfını belirle
            class_name = persona_data.get('class_name')
            if not class_name:
                # Varsayılan mapping
                class_mapping = {
                    'social-media': 'SocialMediaPersona',
                    'task-executor': 'TaskExecutorPersona',
                    'developer': 'TaskExecutorPersona',
                    'system': 'TaskExecutorPersona',
                    'assistant': 'PersonaAgent'
                }
                class_name = class_mapping.get(persona_id, 'PersonaAgent')
            
            logger.info(f"Persona sınıfı belirlendi: {class_name} için {persona_id}")
            
            agent = None
            
            # Factory pattern kullan
            if hasattr(self, 'persona_factory') and self.persona_factory:
                try:
                    # Önce template olarak dene
                    agent = self.persona_factory.create_persona(
                        template_id=persona_id,
                        persona_id=persona_id,
                        name=persona_data.get('name'),
                        description=persona_data.get('description'),
                        **persona_data.get('settings', {})
                    )
                except Exception as e:
                    logger.warning(f"Factory'den persona oluşturulamadı: {str(e)}")
            
            # Factory başarısızsa veya yoksa, doğrudan sınıfı kullan
            if not agent and class_name in self._persona_classes:
                try:
                    PersonaClass = self._persona_classes[class_name]
                    # capabilities'i ayrı tutun
                    capabilities = persona_data.get('capabilities', [])
                    
                    # Diğer parametreleri hazırla
                    constructor_params = {
                        'persona_id': persona_id,
                        'name': persona_data.get('name'),
                        'description': persona_data.get('description'),
                        'settings': persona_data.get('settings', {}),
                        'priority': persona_data.get('priority', 5),
                        'owner': persona_data.get('owner', 'system')
                    }
                    
                    # Eğer SocialMediaPersona veya TaskExecutorPersona ise capabilities'i ekleme
                    if class_name not in ['SocialMediaPersona', 'TaskExecutorPersona']:
                        constructor_params['capabilities'] = capabilities
                    
                    agent = PersonaClass(**constructor_params)
                    
                    # Registry'leri sonradan set et
                    agent.mcp_registry = self.mcp_registry
                    agent.a2a_registry = self.a2a_registry
                    agent.coordinator = self.coordinator
                    logger.info(f"Persona doğrudan sınıftan oluşturuldu: {class_name}")
                except Exception as e:
                    logger.error(f"Sınıftan persona oluşturma hatası: {str(e)}")
            
            # Hala oluşturulamadıysa, import et ve dene
            if not agent:
                try:
                    if class_name == 'SocialMediaPersona':
                        from os_araci.personas.social_media_persona import SocialMediaPersona
                        agent = SocialMediaPersona(
                            persona_id=persona_id,
                            name=persona_data.get('name'),
                            description=persona_data.get('description'),
                            **persona_data.get('settings', {})
                        )
                        # Registry'leri sonradan set et
                        agent.mcp_registry = self.mcp_registry
                        agent.a2a_registry = self.a2a_registry
                        agent.coordinator = self.coordinator
                        
                    elif class_name == 'TaskExecutorPersona':
                        from os_araci.personas.task_executor_persona import TaskExecutorPersona
                        agent = TaskExecutorPersona(
                            persona_id=persona_id,
                            name=persona_data.get('name'),
                            description=persona_data.get('description'),
                            **persona_data.get('settings', {})
                        )
                        # Registry'leri sonradan set et
                        agent.mcp_registry = self.mcp_registry
                        agent.a2a_registry = self.a2a_registry
                        agent.coordinator = self.coordinator
                    else:
                        raise ImportError(f"Bilinmeyen persona sınıfı: {class_name}")
                        
                    logger.info(f"Persona import edilerek oluşturuldu: {class_name}")
                except ImportError as e:
                    logger.warning(f"{class_name} import edilemedi: {str(e)}")
            
            # Son çare: varsayılan PersonaAgent
            if not agent:
                logger.info(f"Varsayılan PersonaAgent kullanılıyor: {persona_id}")
                from os_araci.personas.persona_agent import PersonaAgent
                agent = PersonaAgent(
                    persona_id=persona_id,
                    name=persona_data.get('name'),
                    description=persona_data.get('description'),
                    capabilities=persona_data.get('capabilities', []),
                    settings=persona_data.get('settings', {}),
                    priority=persona_data.get('priority', 5),
                    owner=persona_data.get('owner', 'system')
                )
                # Registry'leri sonradan set et
                agent.mcp_registry = self.mcp_registry
                agent.a2a_registry = self.a2a_registry
                agent.coordinator = self.coordinator
                            
            # Agent oluşturulduysa işlemlere devam et
            if agent:
                try:
                    # Registry'e kaydet
                    if not self.a2a_registry.register_persona(persona_id, agent):
                        logger.warning(f"Persona registry'e tekrar kaydediliyor: {persona_id}")
                        # Zaten kayıtlıysa, önce sil sonra tekrar kaydet
                        self.a2a_registry.unregister_persona(persona_id)
                        self.a2a_registry.register_persona(persona_id, agent)
                    
                    # Persona'yı başlat
                    logger.info(f"Persona başlatılıyor: {persona_id}")
                    success = await agent.initialize()
                    
                    if success:
                        # Aktif personalar listesine ekle
                        self.active_personas[persona_id] = agent
                        logger.info(f"Persona başarıyla başlatıldı: {persona_id} ({type(agent).__name__})")
                        
                        # Event emit et
                        if self.event_emitter:
                            self.event_emitter.emit('persona_started', {
                                'persona_id': persona_id,
                                'name': agent.name,
                                'status': agent.status
                            })
                        
                        return {
                            "status": "success", 
                            "message": f"Persona başlatıldı: {persona_id}",
                            "persona_type": type(agent).__name__
                        }
                    else:
                        # Başlatma başarısız
                        logger.error(f"Persona başlatılamadı: {persona_id}")
                        # Registry'den temizle
                        self.a2a_registry.unregister_persona(persona_id)
                        return {
                            "status": "error", 
                            "message": f"Persona başlatılamadı: {persona_id}"
                        }
                        
                except Exception as e:
                    logger.error(f"Persona başlatma sırasında hata: {str(e)}", exc_info=True)
                    # Hata durumunda temizlik yap
                    if persona_id in self.active_personas:
                        del self.active_personas[persona_id]
                    self.a2a_registry.unregister_persona(persona_id)
                    return {
                        "status": "error",
                        "message": f"Persona başlatma hatası: {str(e)}"
                    }
            else:
                # Agent oluşturulamadı
                logger.error(f"Persona agent'ı oluşturulamadı: {persona_id}")
                return {
                    "status": "error",
                    "message": f"Persona oluşturulamadı: {persona_id}"
                }
            
        except Exception as e:
            logger.error(f"Persona başlatma hatası: {str(e)}", exc_info=True)
            return {"status": "error", "message": str(e)}
    
    async def stop_persona(self, persona_id: str):
        """Personayı durdur"""
        try:
            if persona_id not in self.active_personas:
                return {"status": "error", "message": f"Persona zaten aktif değil: {persona_id}"}
            
            agent = self.active_personas[persona_id]
            
            # Durdur
            success = await agent.shutdown()
            
            if success:
                # Listeden kaldır
                del self.active_personas[persona_id]
                logger.info(f"Persona durduruldu: {persona_id}")
                return {"status": "success", "message": f"Persona durduruldu: {persona_id}"}
            else:
                return {"status": "error", "message": f"Persona durdurulamadı: {persona_id}"}
            
        except Exception as e:
            logger.error(f"Persona durdurma hatası: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def update_persona(self, persona_id: str, update_data: Dict[str, Any]):
        """Personayı güncelle"""
        try:
            # ChromaDB'de güncelle
            result = self.db_manager.update_persona(persona_id, update_data)
            
            if result["status"] == "success":
                # JSON dosyasında da güncelle
                await self._update_persona_in_file(persona_id, update_data)
                
                # Eğer aktifse ve kritik değişiklikler varsa yeniden başlat
                if persona_id in self.active_personas:
                    critical_fields = ['capabilities', 'settings', 'priority', 'class_name']
                    needs_restart = any(field in update_data for field in critical_fields)
                    
                    if needs_restart:
                        await self.stop_persona(persona_id)
                        await self.start_persona(persona_id)
                        result['restarted'] = True
                    else:
                        # Sadece metadata güncelle
                        agent = self.active_personas[persona_id]
                        if 'name' in update_data:
                            agent.name = update_data['name']
                        if 'description' in update_data:
                            agent.description = update_data['description']
                        result['restarted'] = False
            
            return result
        except Exception as e:
            logger.error(f"Persona güncelleme hatası: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def get_persona_status(self, persona_id: str):
        """Personanın runtime durumunu getir"""
        try:
            if persona_id in self.active_personas:
                agent = self.active_personas[persona_id]
                return {
                    "status": "success",
                    "persona_id": persona_id,
                    "is_online": True,
                    "runtime_status": agent.status,
                    "active_tasks": list(agent._current_tasks.keys()),
                    "metrics": agent.task_metrics
                }
            else:
                return {
                    "status": "success",
                    "persona_id": persona_id,
                    "is_online": False,
                    "runtime_status": "offline"
                }
        except Exception as e:
            logger.error(f"Persona durumu alınırken hata: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def _load_personas_from_db(self):
        """ChromaDB'deki personaları yükle ve başlat"""
        try:
            personas = self.db_manager.get_all_personas()
            
            for persona_data in personas:
                if persona_data.get('status') == 'active':
                    result = await self.start_persona(persona_data.get('id'), persona_data)
                    if result.get('status') == 'success':
                        logger.info(f"Persona DB'den yüklendi: {persona_data.get('id')}")
                    else:
                        logger.warning(f"Persona DB'den yüklenemedi: {persona_data.get('id')}")
        except Exception as e:
            logger.error(f"Personalar DB'den yüklenirken hata: {str(e)}")

    async def _load_personas_from_file_to_db(self):
        """JSON dosyasındaki personaları ChromaDB'ye aktar"""
        try:
            # Önce JSON dosyasından yükle
            await self._load_personas_from_file()
            
            # Sonra ChromaDB'ye aktar
            personas = []
            for persona_id, persona_obj in self.a2a_registry._personas.items():
                if hasattr(persona_obj, 'to_dict'):
                    persona_data = persona_obj.to_dict()
                    # ChromaDB'ye ekle
                    result = self.db_manager.create_persona(persona_data)
                    if result["status"] == "success":
                        logger.info(f"Persona DB'ye aktarıldı: {persona_id}")
                    personas.append(persona_data)
            
            return personas
        except Exception as e:
            logger.error(f"Personalar DB'ye aktarılırken hata: {str(e)}")
            return []

    async def _update_persona_in_file(self, persona_id: str, update_data: Dict[str, Any]):
        """JSON dosyasındaki personayı güncelle"""
        try:
            # Mevcut personaları al
            personas = await self.get_personas()
            
            # Güncelle
            for i, persona in enumerate(personas):
                if persona.get('id') == persona_id:
                    personas[i].update(update_data)
                    break
            
            # Dosyaya kaydet
            await self._save_personas_to_file()
            
        except Exception as e:
            logger.error(f"Persona dosyada güncellenirken hata: {str(e)}")

    async def send_message_to_persona(self, persona_id: str, message: str, user_id: str = None) -> Dict[str, Any]:
        """Persona'ya chat mesajı gönder ve yanıt al"""
        try:
            # Mesaj içeriğini hazırla
            message_content = {
                "type": "chat",
                "message": message,
                "user_id": user_id,
                "timestamp": time.time()
            }
            
            # A2A mesajı oluştur ve gönder
            response = await self.a2a_registry.request_reply(
                sender=self.persona_id,
                receiver=persona_id,
                message_type="chat.request",
                content=message_content,
                timeout=30.0
            )
            
            if response:
                return {
                    "status": "success",
                    "response": response.content.get("response", ""),
                    "metadata": response.content.get("metadata", {})
                }
            else:
                return {
                    "status": "error",
                    "response": "Yanıt alınamadı",
                    "error": "Timeout"
                }
                
        except Exception as e:
            logger.error(f"Persona'ya mesaj gönderme hatası: {str(e)}")
            return {
                "status": "error",
                "response": f"Hata: {str(e)}",
                "error": str(e)
            }