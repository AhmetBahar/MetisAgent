# a2a_protocol/registry.py
import asyncio
import logging
import time
import weakref
import json
from typing import Dict, Any, List, Callable, Awaitable, Optional, Set
from os_araci.a2a_protocol.message import A2AMessage

logger = logging.getLogger(__name__)

class A2ARegistry:
    """A2A protokolü için mesaj yönlendirme ve persona yönetimi"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(A2ARegistry, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            logger.info("A2A Registry başlatılıyor...")
            
            # Kayıtlı personalar
            self._personas = {}  # persona_id -> persona
            
            # Persona yetenekleri indexi
            self._capability_index = {}  # capability -> [persona_ids]
            
            # Mesaj yönlendirme kuyruğu
            self._message_queue = asyncio.Queue()
            
            # Mesaj tipleri için dinleyiciler
            self._message_listeners = {}  # message_type -> [callbacks]
            
            # Mesaj işleme için event loop ve task
            self._processing_task = None
            self._loop = None
            
            # Yanıt bekleyen mesajlar
            self._reply_waiters = {}  # message_id -> asyncio.Future
            
            # Aktif mesaj korelasyon ID'leri
            self._active_correlations = set()
            
            self._initialized = True
    
    async def start(self):
        """Mesaj işleme servisini başlat"""
        if self._processing_task is None:
            # Event loop'u kaydet
            self._loop = asyncio.get_running_loop()
            self._processing_task = self._loop.create_task(self._process_messages())
            logger.info("A2A mesaj işleme servisi başlatıldı")
    
    async def stop(self):
        """Mesaj işleme servisini durdur"""
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            self._processing_task = None
            logger.info("A2A mesaj işleme servisi durduruldu")
    
    def register_persona(self, persona_id: str, persona: Any) -> bool:
        """Yeni bir personayı kaydet"""
        if persona_id in self._personas:
            logger.warning(f"Persona zaten kayıtlı: {persona_id}")
            return False
        
        # Personayı kaydet (weakref veya doğrudan obje olarak)
        import weakref
        try:
            # Önce weakref olarak kaydetmeyi dene
            self._personas[persona_id] = weakref.ref(persona)
        except TypeError:
            # weakref oluşturulamıyorsa doğrudan obje olarak kaydet
            self._personas[persona_id] = persona
        
        # Yetenekler indeksini güncelle
        if hasattr(persona, 'capabilities'):
            for capability in persona.capabilities:
                if capability not in self._capability_index:
                    self._capability_index[capability] = []
                if persona_id not in self._capability_index[capability]:
                    self._capability_index[capability].append(persona_id)
        
        logger.info(f"Persona kaydedildi: {persona_id}")
        return True

    def unregister_persona(self, persona_id: str) -> bool:
        """Bir personanın kaydını kaldır"""
        if persona_id not in self._personas:
            logger.warning(f"Persona bulunamadı: {persona_id}")
            return False
        
        # Personayı al (yetenek indeksini güncellemek için)
        persona_ref = self._personas[persona_id]
        persona = persona_ref() if persona_ref else None
        
        # Yetenek indeksini güncelle
        if persona and hasattr(persona, 'capabilities'):
            for capability in persona.capabilities:
                if capability in self._capability_index and persona_id in self._capability_index[capability]:
                    self._capability_index[capability].remove(persona_id)
                    # Boş listeleri temizle
                    if not self._capability_index[capability]:
                        del self._capability_index[capability]
        
        # Personayı sil
        del self._personas[persona_id]
        logger.info(f"Persona kaydı kaldırıldı: {persona_id}")
        return True
    
    def get_persona(self, persona_id: str) -> Optional[Any]:
        """ID ile bir personayı getir"""
        persona_ref = self._personas.get(persona_id)
        if persona_ref:
            # Önce obje mi yoksa weakref mi kontrol et
            if hasattr(persona_ref, '__call__'):
                # Bu bir weakref
                persona = persona_ref()
                if persona:
                    return persona
                else:
                    # Referans geçersiz olmuş, temizle
                    self.unregister_persona(persona_id)
            else:
                # Bu doğrudan obje
                return persona_ref
        return None
    
    def list_personas(self) -> List[str]:
        """Tüm kayıtlı persona ID'lerini listele"""
        # Geçersiz referansları temizle
        valid_personas = []
        for persona_id, persona_ref in list(self._personas.items()):
            if persona_ref() is None:
                self.unregister_persona(persona_id)
            else:
                valid_personas.append(persona_id)
        
        return valid_personas
    
    def find_personas_by_capability(self, capability: str) -> List[str]:
        """Belirli bir yeteneğe sahip personaları bul"""
        # Index ile hızlı erişim
        return self._capability_index.get(capability, []).copy()
    
    def find_personas_by_capabilities(self, capabilities: List[str], match_all: bool = True) -> List[str]:
        """Belirli yeteneklere sahip personaları bul
        
        Args:
            capabilities: Aranan yetenekler listesi
            match_all: True ise tüm yeteneklere sahip personaları, False ise herhangi birine sahip olanları döndür
        
        Returns:
            Persona ID'leri listesi
        """
        if not capabilities:
            return []
        
        if match_all:
            # Tüm yeteneklere sahip personaları bul (kesişim)
            result = set(self.find_personas_by_capability(capabilities[0]))
            for capability in capabilities[1:]:
                result.intersection_update(self.find_personas_by_capability(capability))
            return list(result)
        else:
            # Herhangi bir yeteneğe sahip personaları bul (birleşim)
            result = set()
            for capability in capabilities:
                result.update(self.find_personas_by_capability(capability))
            return list(result)
    
    async def register_listener(self, message_type: str, callback) -> None:
        """Belirli bir mesaj tipi için dinleyici kaydet"""
        if message_type not in self._message_listeners:
            self._message_listeners[message_type] = []
        
        # Callback'in async olup olmadığını kontrol et
        import inspect
        if not inspect.iscoroutinefunction(callback):
            logger.warning(f"Callback async değil: {message_type}")
        
        self._message_listeners[message_type].append(callback)
        logger.info(f"Mesaj dinleyici kaydedildi: {message_type} (toplam: {len(self._message_listeners[message_type])})")
    
    def unregister_listener(self, message_type: str, callback: Callable[[A2AMessage], Awaitable[None]]) -> bool:
        """Bir mesaj dinleyicisini kaldır"""
        if message_type not in self._message_listeners:
            return False
        
        try:
            self._message_listeners[message_type].remove(callback)
            logger.debug(f"Mesaj dinleyici kaldırıldı: {message_type}")
            return True
        except ValueError:
            return False
    
    async def send_message(self, message: A2AMessage) -> str:
        """Bir mesaj gönder (kuyruğa ekle)"""
        # Mesaj süresi geçmiş mi kontrol et
        if message.is_expired():
            logger.warning(f"Süresi dolmuş mesaj gönderilmeye çalışıldı: {message.message_id}")
            return None
        
        # Mesaj korelasyon ID'sini kaydet (eğer varsa)
        if message.correlation_id:
            self._active_correlations.add(message.correlation_id)
        
        # Mesajı kuyruğa ekle
        await self._message_queue.put(message)
        logger.debug(f"Mesaj kuyruğa eklendi: {message.message_id}, tip: {message.message_type}")
        
        return message.message_id
    
    async def _process_messages(self):
        """Mesaj kuyruğunu sürekli olarak işle"""
        logger.info("Mesaj işleme döngüsü başlatıldı")
        while True:
            try:
                # Kuyruktan bir mesaj al
                message = await self._message_queue.get()
                
                # Mesaj süresinin dolup dolmadığını kontrol et
                if message.is_expired():
                    logger.warning(f"Süresi dolmuş mesaj atlandı: {message.message_id}")
                    self._message_queue.task_done()
                    continue
                
                # Bu mesaj bir yanıt mı?
                is_reply = bool(message.reply_to) and message.reply_to in self._reply_waiters
                
                # Alıcı persona var mı kontrol et (broadcast veya reply değilse)
                if (message.receiver != "broadcast" and not is_reply and 
                    message.receiver not in self._personas):
                    logger.warning(f"Alıcı persona bulunamadı: {message.receiver}")
                    self._message_queue.task_done()
                    continue
                
                # Mesajı işle
                try:
                    # Yanıt beklenen bir mesaja cevap mı?
                    if is_reply:
                        waiter = self._reply_waiters.get(message.reply_to)
                        if waiter and not waiter.done():
                            waiter.set_result(message)
                            logger.debug(f"Beklenen yanıt alındı: {message.message_id}, cevap: {message.reply_to}")
                    
                    # Tüm kayıtlı dinleyicileri çağır
                    await self._call_listeners(message)
                    
                    # Mesajı alıcıya ilet (waiter tarafından işlendiyse veya broadcast ise alıcıya ayrıca iletmeye gerek yok)
                    if not is_reply and message.receiver != "broadcast":
                        persona_ref = self._personas.get(message.receiver)
                        if persona_ref:
                            # Güvenli persona erişimi
                            if hasattr(persona_ref, '__call__'):
                                # Bu bir weakref
                                persona = persona_ref()
                                if not persona:
                                    # Referans geçersiz olmuş, temizle
                                    self.unregister_persona(message.receiver)
                                    self._message_queue.task_done()
                                    continue
                            else:
                                # Bu doğrudan obje
                                persona = persona_ref
                            
                            # Persona hala geçerli
                            if hasattr(persona, 'handle_message') and callable(persona.handle_message):
                                await persona.handle_message(message)
                    
                    # Broadcast mesajı ise tüm personaları bilgilendir
                    if message.receiver == "broadcast":
                        for persona_id, persona_ref in list(self._personas.items()):
                            # Güvenli persona erişimi
                            if hasattr(persona_ref, '__call__'):
                                # Bu bir weakref
                                persona = persona_ref()
                                if not persona:
                                    # Referans geçersiz olmuş, temizle
                                    self.unregister_persona(persona_id)
                                    continue
                            else:
                                # Bu doğrudan obje
                                persona = persona_ref
                            
                            # Mesajı gönderene tekrar iletme
                            if persona_id != message.sender:
                                if hasattr(persona, 'handle_message') and callable(persona.handle_message):
                                    await persona.handle_message(message)
                    
                    logger.debug(f"Mesaj başarıyla işlendi: {message.message_id}")
                    
                except Exception as e:
                    logger.error(f"Mesaj işlenirken hata: {str(e)}, mesaj ID: {message.message_id}")
                finally:
                    self._message_queue.task_done()
                    
            except asyncio.CancelledError:
                # İşleme görevi iptal edildi
                logger.info("Mesaj işleme görevi iptal edildi")
                break
            except Exception as e:
                logger.error(f"Mesaj işleme döngüsünde beklenmeyen hata: {str(e)}")
                # Kısa bir süre bekle ve devam et
                await asyncio.sleep(0.1)
        
        logger.info("Mesaj işleme döngüsü sonlandı") 
    
    async def _call_listeners(self, message: A2AMessage) -> None:
        """Mesaj için tüm kayıtlı dinleyicileri çağır"""
        listeners_to_call = []
        
        logger.debug(f"Dinleyiciler çağrılıyor - Mesaj tipi: {message.message_type}")
        
        # Tam mesaj tipi eşleşmesi
        if message.message_type in self._message_listeners:
            listeners_to_call.extend(self._message_listeners[message.message_type])
            logger.debug(f"Tam eşleşme bulundu: {len(self._message_listeners[message.message_type])} dinleyici")
        
        # Wildcard dinleyiciler ('*' ile tüm mesaj tipleri)
        if "*" in self._message_listeners:
            listeners_to_call.extend(self._message_listeners["*"])
        
        # Özel wildcard desenleri (örn. 'task.*' gibi)
        for pattern, listeners in self._message_listeners.items():
            if pattern.endswith(".*") and message.message_type.startswith(pattern[:-1]):
                listeners_to_call.extend(listeners)
        
        logger.debug(f"Toplam {len(listeners_to_call)} dinleyici çağrılacak")
        
        # Tüm dinleyicileri çağır
        for listener in listeners_to_call:
            try:
                await listener(message)
            except Exception as e:
                logger.error(f"Dinleyici çağrılırken hata: {str(e)}") 

    async def wait_for_reply(self, message_id: str, timeout: float = 60.0) -> Optional[A2AMessage]:
        """Belirli bir mesaja yanıt gelene kadar bekle"""
        if not self._loop:
            self._loop = asyncio.get_running_loop()
        
        # Yeni bir future oluştur
        future = self._loop.create_future()
        self._reply_waiters[message_id] = future
        
        try:
            # Yanıtı bekle
            return await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Yanıt bekleme zaman aşımına uğradı: {message_id}")
            return None
        finally:
            # Future'ı temizle
            self._reply_waiters.pop(message_id, None)
    
    async def request_reply(self, 
                          sender: str, 
                          receiver: str, 
                          message_type: str, 
                          content: Dict[str, Any],
                          timeout: float = 60.0,
                          priority: int = 5) -> Optional[A2AMessage]:
        """Bir mesaj gönder ve yanıt bekle (senkron istek-yanıt modeli)"""
        # Mesaj oluştur
        message = A2AMessage(
            sender=sender,
            receiver=receiver,
            message_type=message_type,
            content=content,
            priority=priority
        )
        
        # Mesajı gönder
        message_id = await self.send_message(message)
        
        if not message_id:
            logger.error("Mesaj gönderilemedi")
            return None
        
        # Yanıtı bekle
        return await self.wait_for_reply(message_id, timeout)
    
    def save_state(self, file_path: str) -> bool:
        """Registry durumunu kaydet"""
        try:
            # Kaydedilecek verileri hazırla
            state = {
                "active_correlations": list(self._active_correlations),
                "capability_index": self._capability_index
            }
            
            # JSON olarak dosyaya yaz
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Registry durumu kaydedildi: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Registry durumu kaydedilirken hata: {str(e)}")
            return False
    
    def load_state(self, file_path: str) -> bool:
        """Registry durumunu yükle"""
        try:
            # Dosyadan JSON yükle
            with open(file_path, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            # Aktif korelasyonları yükle
            self._active_correlations = set(state.get("active_correlations", []))
            
            # Yetenek indeksini yükle (geçerli personaları kontrol ederek)
            capability_index = state.get("capability_index", {})
            self._capability_index = {}
            
            for capability, persona_ids in capability_index.items():
                valid_ids = []
                for persona_id in persona_ids:
                    if persona_id in self._personas:
                        valid_ids.append(persona_id)
                
                if valid_ids:
                    self._capability_index[capability] = valid_ids
            
            logger.info(f"Registry durumu yüklendi: {file_path}")
            return True
        except FileNotFoundError:
            logger.warning(f"Registry durum dosyası bulunamadı: {file_path}")
            return False
        except Exception as e:
            logger.error(f"Registry durumu yüklenirken hata: {str(e)}")
            return False
        
    async def send_message(self, message: A2AMessage) -> str:
        """Bir mesaj gönder (kuyruğa ekle)"""
        # Mesaj süresi geçmiş mi kontrol et
        if message.is_expired():
            logger.warning(f"Süresi dolmuş mesaj gönderilmeye çalışıldı: {message.message_id}")
            return None
        
        # Mesaj korelasyon ID'sini kaydet (eğer varsa)
        if message.correlation_id:
            self._active_correlations.add(message.correlation_id)
        
        # Mesajı kuyruğa ekle
        await self._message_queue.put(message)
        logger.debug(f"Mesaj kuyruğa eklendi: {message.message_id}, tip: {message.message_type}")
        
        return message.message_id
    
    def register_listener(self, message_type: str, callback: Callable[[A2AMessage], Awaitable[None]]) -> None:
        """Belirli bir mesaj tipi için dinleyici kaydet"""
        if message_type not in self._message_listeners:
            self._message_listeners[message_type] = []
        
        self._message_listeners[message_type].append(callback)
        logger.info(f"Mesaj dinleyici kaydedildi: {message_type} (toplam dinleyici: {len(self._message_listeners[message_type])})")
