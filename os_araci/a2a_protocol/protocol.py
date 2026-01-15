# a2a_protocol/protocol.py
import asyncio
import logging
import os
import json
import time
from typing import Dict, Any, List, Optional, Union
from a2a_protocol.registry import A2ARegistry
from a2a_protocol.message import A2AMessage
from personas.persona_agent import PersonaAgent
from personas.persona_factory import PersonaFactory

logger = logging.getLogger(__name__)

class A2AProtocol:
    """A2A protokolünü yönetmek için ana sınıf"""
    
    def __init__(self, config_path: str = None):
        """A2A protokolü başlatıcı"""
        self.registry = A2ARegistry()
        self.persona_factory = PersonaFactory()
        self.active_personas = {}  # persona_id -> persona
        self.config_path = config_path
    
    async def initialize(self) -> bool:
        """A2A protokolünü başlat"""
        try:
            # Mesaj işleme servisini başlat
            await self.registry.start()
            
            # Persona sınıflarını keşfet
            self.persona_factory.discover_persona_classes('personas')
            
            # Yapılandırmayı yükle (varsa)
            if self.config_path and os.path.exists(self.config_path):
                self.load_config(self.config_path)
            
            logger.info("A2A protokolü başlatıldı")
            return True
        except Exception as e:
            logger.error(f"A2A protokolü başlatma hatası: {str(e)}")
            return False
    
    async def shutdown(self) -> bool:
        """A2A protokolünü kapat"""
        try:
            # Aktif tüm personaları kapat
            for persona_id, persona in list(self.active_personas.items()):
                await persona.shutdown()
            
            # Mesaj işleme servisini durdur
            await self.registry.stop()
            
            logger.info("A2A protokolü kapatıldı")
            return True
        except Exception as e:
            logger.error(f"A2A protokolü kapatma hatası: {str(e)}")
            return False
    
    def load_config(self, config_path: str) -> bool:
        """A2A protokolü yapılandırmasını yükle"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Yapılandırmayı işle
            if "templates_directory" in config:
                templates_dir = config["templates_directory"]
                self.persona_factory.load_templates_from_directory(templates_dir)
            
            # Otomatik başlatılacak personaları yükle
            if "auto_start_personas" in config:
                for persona_config in config["auto_start_personas"]:
                    template_id = persona_config.get("template_id")
                    overrides = persona_config.get("config", {})
                    
                    if template_id:
                        # Asenkron görevi oluştur ve ekle
                        asyncio.create_task(self.create_and_start_persona(template_id, **overrides))
            
            logger.info(f"A2A protokolü yapılandırması yüklendi: {config_path}")
            return True
        except Exception as e:
            logger.error(f"A2A yapılandırması yüklenirken hata: {str(e)}")
            return False
    
    async def create_and_start_persona(self, template_id: str, **kwargs) -> Optional[PersonaAgent]:
        """Şablona göre persona oluştur ve başlat"""
        persona = self.persona_factory.create_persona(template_id, **kwargs)
        
        if not persona:
            logger.error(f"Persona oluşturulamadı: {template_id}")
            return None
        
        # Personayı başlat
        success = await persona.initialize()
        
        if success:
            # Aktif personalar listesine ekle
            self.active_personas[persona.persona_id] = persona
            logger.info(f"Persona başlatıldı: {persona.persona_id}")
            return persona
        else:
            logger.error(f"Persona başlatılamadı: {persona.persona_id}")
            return None
    
    async def stop_persona(self, persona_id: str) -> bool:
        """Belirli bir personayı durdur"""
        if persona_id not in self.active_personas:
            logger.warning(f"Persona bulunamadı: {persona_id}")
            return False
        
        persona = self.active_personas[persona_id]
        
        # Personayı kapat
        success = await persona.shutdown()
        
        if success:
            # Aktif personalar listesinden kaldır
            del self.active_personas[persona_id]
            logger.info(f"Persona durduruldu: {persona_id}")
        else:
            logger.error(f"Persona durdurulamadı: {persona_id}")
        
        return success
    
    async def get_persona_status(self, persona_id: str = None) -> Dict[str, Any]:
        """Persona(lar) durumunu al"""
        if persona_id:
            # Belirli bir personanın durumu
            if persona_id not in self.active_personas:
                return {"error": f"Persona not found: {persona_id}"}
            
            persona = self.active_personas[persona_id]
            
            return {
                "persona_id": persona_id,
                "status": getattr(persona, 'status', 'unknown'),
                "name": getattr(persona, 'name', 'Unknown'),
                "metrics": getattr(persona, 'task_metrics', {})
            }
        else:
            # Tüm personaların durumu
            statuses = {}
            
            for pid, persona in self.active_personas.items():
                statuses[pid] = {
                    "status": getattr(persona, 'status', 'unknown'),
                    "name": getattr(persona, 'name', 'Unknown'),
                    "metrics": getattr(persona, 'task_metrics', {})
                }
            
            return statuses
    
    async def send_message(self, 
                         sender: str, 
                         receiver: str, 
                         message_type: str, 
                         content: Dict[str, Any]) -> str:
        """Bir mesaj gönder"""
        message = A2AMessage(
            sender=sender,
            receiver=receiver,
            message_type=message_type,
            content=content
        )
        
        return await self.registry.send_message(message)
    
    async def broadcast(self, 
                      sender: str, 
                      message_type: str, 
                      content: Dict[str, Any]) -> str:
        """Tüm personaların dinleyebileceği bir broadcast mesajı gönder"""
        message = A2AMessage(
            sender=sender,
            receiver="broadcast",
            message_type=message_type,
            content=content
        )
        
        return await self.registry.send_message(message)