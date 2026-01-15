# personas/persona_agent.py
import asyncio
import logging
import json
import time
import os
from typing import Dict, Any, List, Optional, Callable, Awaitable, Union
from os_araci.a2a_protocol.message import A2AMessage
from os_araci.a2a_protocol.registry import A2ARegistry

logger = logging.getLogger(__name__)

class PersonaAgent:
    """A2A protokolünü destekleyen persona ajanı temel sınıfı"""
    
    def __init__(self, 
                persona_id: str, 
                name: str,
                description: str,
                capabilities: List[str] = None,
                settings: Dict[str, Any] = None,
                personality_traits: Dict[str, Any] = None,
                priority: int = 5,
                owner: str = None):
        
        self.persona_id = persona_id
        self.name = name
        self.description = description
        self.capabilities = capabilities or []
        self.settings = settings or {}
        self.personality_traits = personality_traits or {}
        self.priority = min(max(priority, 1), 10)  # 1-10 arası (10 en yüksek)
        self.owner = owner or "system"
        
        # Durum ve metrikler
        self.status = "idle"  # idle, busy, disabled
        self.task_metrics = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "last_task_time": None,
            "average_response_time": 0
        }
        
        # A2A Registry
        self._registry = A2ARegistry()
        self._registry.register_persona(persona_id, self)
        
        # Mesaj işleyicileri
        self._message_handlers = {}  # message_type -> handler
        self._is_initialized = False
        self._handlers_registered = False
        
        # Eşzamanlılık kontrolü
        self._lock = asyncio.Lock()
        self._current_tasks = {}  # task_id -> asyncio.Task
        
        # Çalışma dizini
        self._working_dir = self.settings.get("working_dir", os.getcwd())
        
        # Mesaj tipi işleyicilerini otomatik kaydet
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Varsayılan mesaj işleyicilerini kaydet"""
        if self._handlers_registered:
            return
        
        # Yaygın mesaj tipleri için varsayılan işleyiciler
        for message_type, handler_name in [
            ("task.request", "handle_task_request"),
            ("chat.request", "handle_chat_request"),
            ("task.response", "handle_task_response"),
            ("query.request", "handle_query_request"),
            ("query.response", "handle_query_response"),
            ("ping", "handle_ping"),
            ("shutdown", "handle_shutdown"),
            ("status.request", "handle_status_request"),
            ("heartbeat", "handle_heartbeat")
        ]:
            if hasattr(self, handler_name) and callable(getattr(self, handler_name)):
                self.register_message_handler(message_type, getattr(self, handler_name))
        
        self._handlers_registered = True
    
    def register_message_handler(self, message_type: str, handler: Callable[[A2AMessage], Awaitable[None]]) -> None:
        """Belirli bir mesaj tipi için işleyici kaydet"""
        self._message_handlers[message_type] = handler
        logger.debug(f"Mesaj işleyici kaydedildi: {message_type}, persona: {self.persona_id}")
    
    async def handle_message(self, message: A2AMessage) -> None:
        """Gelen mesajı işle"""
        # İşleyici mevcut mu?
        if message.message_type in self._message_handlers:
            handler = self._message_handlers[message.message_type]
            
            # İşleyiciyi çağır (hata işleme ile)
            try:
                await handler(message)
            except Exception as e:
                logger.error(f"Mesaj işleyicisi hata verdi: {message.message_type}, persona: {self.persona_id}, hata: {str(e)}")
                
                # Hata yanıtı gönder
                if message.reply_to:
                    error_reply = message.create_reply(
                        content={"status": "error", "message": f"Error processing message: {str(e)}"},
                        message_type="error.processing"
                    )
                    await self._registry.send_message(error_reply)
        else:
            # Bilinmeyen mesaj tipi
            await self.handle_unknown_message(message)
    
    async def handle_chat_request(self, message: A2AMessage) -> None:
        """Chat isteği mesajlarını işle"""
        try:
            logger.info(f"Chat mesajı alındı: {self.persona_id}")
            chat_message = message.content.get("message", "")
            user_id = message.content.get("user_id")
            
            # generate_chat_response async ise await kullan
            if asyncio.iscoroutinefunction(self.generate_chat_response):
                response_text = await self.generate_chat_response(chat_message)
            else:
                response_text = self.generate_chat_response(chat_message)
            
            # Yanıt gönder
            reply = message.create_reply(
                content={
                    "response": response_text,
                    "metadata": {
                        "persona_id": self.persona_id,
                        "timestamp": time.time()
                    }
                },
                message_type="chat.response"
            )
            
            await self.a2a_registry.send_message(reply)
            
        except Exception as e:
            logger.error(f"Chat mesajı işleme hatası: {str(e)}", exc_info=True)

    async def generate_chat_response(self, message: str) -> str:
        """Chat yanıtı oluştur"""
        # LLM varsa kullan
        if hasattr(self, 'llm_tool') and self.llm_tool:
            try:
                system_prompt = f"""Sen {self.name} adlı bir persona ajanısın.
    Açıklama: {self.description}
    Yeteneklerin: {', '.join(self.capabilities)}

    Kullanıcının mesajına uygun bir yanıt ver."""
                
                response = self.llm_tool.generate_text(
                    prompt=message,
                    system_prompt=system_prompt,
                    temperature=0.7
                )
                
                if isinstance(response, dict) and 'text' in response:
                    return response['text']
                elif isinstance(response, str):
                    return response
                else:
                    return "Yanıt oluşturulamadı."
                    
            except Exception as e:
                logger.error(f"LLM yanıt hatası: {str(e)}")
        
        # LLM yoksa varsayılan yanıt
        return f"Merhaba! Ben {self.name}. '{message}' mesajınızı aldım. Şu anda LLM bağlantım olmadığı için detaylı yanıt veremiyorum."
    
    async def send_message(self, 
                          receiver: str, 
                          message_type: str, 
                          content: Dict[str, Any],
                          correlation_id: Optional[str] = None,
                          reply_to: Optional[str] = None,
                          expires_in: Optional[float] = None,
                          priority: Optional[int] = None) -> str:
        """Bir mesaj oluştur ve gönder"""
        expires_at = None
        if expires_in:
            expires_at = time.time() + expires_in
        
        message = A2AMessage(
            sender=self.persona_id,
            receiver=receiver,
            message_type=message_type,
            content=content,
            correlation_id=correlation_id,
            reply_to=reply_to,
            expires_at=expires_at,
            priority=priority or self.priority
        )
        
        return await self._registry.send_message(message)
    
    async def send_and_wait_reply(self,
                                 receiver: str,
                                 message_type: str,
                                 content: Dict[str, Any],
                                 timeout: float = 60.0,
                                 priority: Optional[int] = None) -> Optional[A2AMessage]:
        """Bir mesaj gönder ve yanıt bekle (otomatik korelasyon ile)"""
        return await self._registry.request_reply(
            sender=self.persona_id,
            receiver=receiver,
            message_type=message_type,
            content=content,
            timeout=timeout,
            priority=priority or self.priority
        )
    
    async def broadcast(self,
                      message_type: str,
                      content: Dict[str, Any],
                      expires_in: Optional[float] = None,
                      priority: Optional[int] = None) -> str:
        """Tüm personaların dinleyebileceği bir broadcast mesajı gönder"""
        return await self.send_message(
            receiver="broadcast",
            message_type=message_type,
            content=content,
            expires_in=expires_in,
            priority=priority
        )
    
    async def initialize(self) -> bool:
        """Ajanı başlat"""
        try:
            logger.info(f"Persona başlatılıyor: {self.persona_id}")
            
            # MCP Registry'den araçları sorgula
            self._tools = self.get_available_tools()
            
            # LLM tool'u bul
            llm_tool_id = None
            for tool_id, metadata in self.mcp_registry.get_all_metadata().items():
                if metadata.name == 'llm_tool':
                    llm_tool_id = tool_id
                    logger.info(f"LLM tool bulundu: {tool_id}")
                    break
            
            if llm_tool_id:
                self.llm_tool = self.mcp_registry.get_tool_by_id(llm_tool_id)
            else:
                logger.warning(f"LLM tool bulunamadı, persona {self.persona_id} sınırlı işlevsellikle çalışacak")
            
            # A2A registry ile kayıt ol
            if self.a2a_registry:
                # Mesaj dinleyicileri kaydet - await KALDIRIN
                self.a2a_registry.register_listener("chat.request", self.handle_chat_request)
                logger.info(f"{self.persona_id} için A2A dinleyicileri kaydedildi")
            
            if hasattr(self, '_async_init'):
                await self._async_init()

            self.is_initialized = True
            self.status = "idle"
            logger.info(f"Persona başarıyla başlatıldı: {self.persona_id}")
            return True
            
        except Exception as e:
            logger.error(f"Persona başlatma hatası: {self.persona_id}, {str(e)}", exc_info=True)
            self.is_initialized = False
            self.status = "error"
            return False
    
    def _find_llm_tool(self):
        """LLM tool'u bul ve kaydet"""
        try:
            # MCP Registry'yi al
            from os_araci.mcp_core.registry import MCPRegistry
            self.mcp_registry = MCPRegistry()
            
            # Registry'nin başlatıldığından emin ol
            if not hasattr(self.mcp_registry, 'get_all_metadata'):
                logger.error("MCP Registry henüz başlatılmamış")
                self.llm_tool = None
                return
            
            # LLM tool'u bul
            all_tools = self.mcp_registry.get_all_metadata()
            for tool_id, metadata in all_tools.items():
                if metadata.name == 'llm_tool':
                    self.llm_tool = self.mcp_registry.get_tool_by_id(tool_id)
                    logger.info(f"LLM tool bulundu: {tool_id}")
                    return
            
            logger.warning("LLM tool bulunamadı")
            self.llm_tool = None
        except Exception as e:
            logger.error(f"LLM tool arama hatası: {str(e)}", exc_info=True)
            self.llm_tool = None

    def _find_coordinator(self):
        """MCPCoordinator'ı bul"""
        # Coordinator'ı al
        from os_araci.coordination.coordinator import MCPCoordinator
        self.coordinator = MCPCoordinator(self.mcp_registry)
        return self.coordinator

    def get_available_tools(self) -> Dict[str, Any]:
        """Kullanılabilir MCP araçlarını getir"""
        if not hasattr(self, 'mcp_registry') or not self.mcp_registry:
            return {}
        
        tools = {}
        for tool_id, metadata in self.mcp_registry.get_all_metadata().items():
            tool = self.mcp_registry.get_tool_by_id(tool_id)
            if tool:
                tools[metadata.name] = {
                    "id": tool_id,
                    "metadata": metadata,
                    "tool": tool
                }
        return tools

    async def _initialize(self) -> bool:
        """Alt sınıflar tarafından override edilebilir"""
        return True
    
    async def shutdown(self) -> bool:
        """Persona kapanırken çağrılır"""
        if not self._is_initialized:
            return True
        
        logger.info(f"Persona kapatılıyor: {self.persona_id}")
        
        try:
            # Aktif görevleri iptal et
            for task_id, task in list(self._current_tasks.items()):
                task.cancel()
                logger.info(f"Görev iptal edildi: {task_id}")
            
            # Kapanış bildirimi gönder
            await self.broadcast("status.update", {
                "status": "shutdown",
                "message": f"Persona {self.name} kapatılıyor",
                "timestamp": time.time()
            })
            
            # Registry'den kaydı sil
            self._registry.unregister_persona(self.persona_id)
            
            # Özel kapatma işlemleri alt sınıflarda override edilebilir
            result = await self._shutdown()
            
            self._is_initialized = False
            self.status = "disabled"
            return result
        except Exception as e:
            logger.error(f"Persona kapatma hatası: {self.persona_id}, {str(e)}")
            return False
    
    async def _shutdown(self) -> bool:
        """Alt sınıflar tarafından override edilebilir"""
        return True
    
    # Yaygın mesaj tipleri için varsayılan işleyiciler
    
    async def handle_ping(self, message: A2AMessage) -> None:
        """Ping mesajına yanıt ver"""
        reply = message.create_reply(
            content={
                "status": "success", 
                "timestamp": time.time(),
                "persona_status": self.status
            },
            message_type="pong"
        )
        await self._registry.send_message(reply)
    
    async def handle_shutdown(self, message: A2AMessage) -> None:
        """Kapatma mesajını işle"""
        # Eğer auth_token varsa kontrol et
        auth_token = message.content.get("auth_token")
        if auth_token and auth_token != self.settings.get("auth_token"):
            reply = message.create_reply(
                content={"status": "error", "message": "Unauthorized shutdown request"},
                message_type="error.unauthorized"
            )
            await self._registry.send_message(reply)
            return
        
        # Kapanmaya başla
        reply = message.create_reply(
            content={"status": "success", "message": "Shutting down..."},
            message_type="shutdown.accepted"
        )
        await self._registry.send_message(reply)
        
        # Kapanma işlemini gerçekleştir
        asyncio.create_task(self.shutdown())
    
    async def handle_status_request(self, message: A2AMessage) -> None:
        """Durum sorgusu mesajını işle"""
        status_info = {
            "status": self.status,
            "name": self.name,
            "persona_id": self.persona_id,
            "capabilities": self.capabilities,
            "timestamp": time.time(),
            "metrics": self.task_metrics,
            "active_tasks": len(self._current_tasks)
        }
        
        reply = message.create_reply(
            content=status_info,
            message_type="status.response"
        )
        await self._registry.send_message(reply)
    
    async def handle_heartbeat(self, message: A2AMessage) -> None:
        """Heartbeat mesajını işle (diğer personaların durumlarını takip etmek için)"""
        # Bu metodun varsayılan implementasyonu sadece log tutar
        # Alt sınıflar daha fazla işlem yapabilir
        logger.debug(f"Heartbeat alındı: {message.sender}, durum: {message.content.get('status', 'unknown')}")
    
    async def handle_task_request(self, message: A2AMessage) -> None:
        """Görev isteklerini işle - alt sınıflar override etmeli"""
        logger.warning(f"Varsayılan task.request işleyicisi çağrıldı, override edilmeli: {self.persona_id}")
        
        # Varsayılan olarak desteklenmediğini bildir
        reply = message.create_reply(
            content={
                "status": "error",
                "message": f"Persona {self.name} does not support task execution"
            },
            message_type="task.response"
        )
        await self._registry.send_message(reply)
    
    async def update_status(self, new_status: str, broadcast_update: bool = True) -> None:
        """Persona durumunu güncelle ve isteğe bağlı olarak broadcast et"""
        # Durumu güncelle
        old_status = self.status
        self.status = new_status
        
        logger.info(f"Persona durumu güncellendi: {self.persona_id}, {old_status} -> {new_status}")
        
        # Durumu broadcast et (isteğe bağlı)
        if broadcast_update:
            await self.broadcast("status.update", {
                "persona_id": self.persona_id,
                "name": self.name,
                "status": new_status,
                "previous_status": old_status,
                "timestamp": time.time()
            })
    
    def to_dict(self) -> Dict[str, Any]:
        """Persona bilgilerini sözlüğe dönüştür"""
        return {
            "persona_id": self.persona_id,
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "priority": self.priority,
            "owner": self.owner,
            "status": self.status,
            "metrics": self.task_metrics,
            "is_initialized": self._is_initialized
        }
    
    @classmethod
    def from_json(cls, json_file: str) -> 'PersonaAgent':
        """JSON dosyasından persona oluştur"""
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return cls(
            persona_id=data.get("persona_id"),
            name=data.get("name"),
            description=data.get("description"),
            capabilities=data.get("capabilities", []),
            settings=data.get("settings", {}),
            personality_traits=data.get("personality_traits", {}),
            priority=data.get("priority", 5),
            owner=data.get("owner", "system")
        )
    
    def save_to_json(self, json_file: str) -> bool:
        """Persona bilgilerini JSON dosyasına kaydet"""
        try:
            data = self.to_dict()
            
            # Ayarları ve kişilik özelliklerini ekle
            data["settings"] = self.settings
            data["personality_traits"] = self.personality_traits
            
            # JSON'a dönüştür ve dosyaya yaz
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Persona JSON'a kaydedildi: {json_file}")
            return True
        except Exception as e:
            logger.error(f"Persona JSON'a kaydedilirken hata: {str(e)}")
            return False