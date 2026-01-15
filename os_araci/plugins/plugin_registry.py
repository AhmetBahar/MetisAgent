# os_araci/plugins/plugin_registry.py
import os
import json
import importlib.util
import logging
from typing import Dict, List, Any, Optional, Union
from os_araci.personas.persona_agent import PersonaAgent
from os_araci.a2a_protocol.registry import A2ARegistry

logger = logging.getLogger(__name__)

class PluginRegistry:
    """Plugin kayıt ve yönetim sistemi"""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(PluginRegistry, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, plugin_dir: str = "./plugins"):
        if not self._initialized:
            self.plugin_dir = plugin_dir
            self.plugins = {}  # plugin_id -> plugin_info
            self.loaded_plugins = {}  # plugin_id -> plugin_instance
            self.a2a_registry = A2ARegistry() 
            
            # Eklentiler dizinini oluştur
            if not os.path.exists(plugin_dir):
                os.makedirs(plugin_dir)
                logger.info(f"Plugin dizini oluşturuldu: {plugin_dir}")
            
            # Metadata dizinini oluştur
            metadata_dir = os.path.join(plugin_dir, "metadata")
            if not os.path.exists(metadata_dir):
                os.makedirs(metadata_dir)
                logger.info(f"Plugin metadata dizini oluşturuldu: {metadata_dir}")
            
            # Mevcut eklentileri yükle
            self._discover_plugins()
            self._initialized = True
    
    def _discover_plugins(self) -> None:
        """Mevcut eklentileri tespit et"""
        metadata_dir = os.path.join(self.plugin_dir, "metadata")
        
        for filename in os.listdir(metadata_dir):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(metadata_dir, filename), 'r', encoding='utf-8') as f:
                        plugin_info = json.load(f)
                        plugin_id = plugin_info.get("id")
                        if plugin_id:
                            self.plugins[plugin_id] = plugin_info
                            logger.info(f"Plugin metadata yüklendi: {plugin_id}")
                except Exception as e:
                    logger.error(f"Plugin metadata yüklenirken hata: {filename}, {str(e)}")
    
    def get_all_plugins(self) -> List[Dict[str, Any]]:
        """Tüm kayıtlı eklentileri döndür"""
        return list(self.plugins.values())
    
    def get_plugin(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """Belirli bir eklentinin bilgilerini döndür"""
        return self.plugins.get(plugin_id)
    
    def register_plugin(self, plugin_info: Dict[str, Any]) -> str:
        """Yeni bir eklenti kaydet"""
        plugin_id = plugin_info.get("id")
        if not plugin_id:
            raise ValueError("Plugin ID is required")
        
        if plugin_id in self.plugins:
            raise ValueError(f"Plugin with ID '{plugin_id}' already exists")
        
        # Metadata dosyasını kaydet
        metadata_path = os.path.join(self.plugin_dir, "metadata", f"{plugin_id}.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(plugin_info, f, ensure_ascii=False, indent=2)
        
        # Registry'e ekle
        self.plugins[plugin_id] = plugin_info
        logger.info(f"Plugin kaydedildi: {plugin_id}")
        
        return plugin_id
    
    def unregister_plugin(self, plugin_id: str) -> bool:
        """Bir eklentiyi kayıttan kaldır"""
        if plugin_id not in self.plugins:
            return False
        
        # Önce yüklü ise kaldır
        if plugin_id in self.loaded_plugins:
            self.unload_plugin(plugin_id)
        
        # Metadata dosyasını sil
        metadata_path = os.path.join(self.plugin_dir, "metadata", f"{plugin_id}.json")
        if os.path.exists(metadata_path):
            os.remove(metadata_path)
        
        # Registry'den kaldır
        del self.plugins[plugin_id]
        logger.info(f"Plugin kaldırıldı: {plugin_id}")
        
        return True
    
    async def load_plugin(self, plugin_id: str) -> Optional[PersonaAgent]:
        """Bir eklentiyi yükle ve başlat"""
        if plugin_id not in self.plugins:
            logger.error(f"Plugin bulunamadı: {plugin_id}")
            return None
        
        if plugin_id in self.loaded_plugins:
            logger.warning(f"Plugin zaten yüklenmiş: {plugin_id}")
            return self.loaded_plugins[plugin_id]
        
        plugin_info = self.plugins[plugin_id]
        module_path = plugin_info.get("module_path")
        class_name = plugin_info.get("class_name")
        
        if not module_path or not class_name:
            logger.error(f"Plugin bilgileri eksik: {plugin_id}")
            return None
        
        try:
            # Modülü dinamik olarak yükle
            module_spec = importlib.util.spec_from_file_location("plugin_module", module_path)
            if not module_spec or not module_spec.loader:
                logger.error(f"Modül yüklenemedi: {module_path}")
                return None
                
            module = importlib.util.module_from_spec(module_spec)
            module_spec.loader.exec_module(module)
            
            # Sınıfı çıkar
            plugin_class = getattr(module, class_name)
            
            # Eklenti örneğini oluştur
            plugin_instance = plugin_class(
                persona_id=plugin_id,
                name=plugin_info.get("name", plugin_id),
                description=plugin_info.get("description", ""),
                workflow_steps=plugin_info.get("workflow_steps", []),
                workflow_transitions=plugin_info.get("workflow_transitions", []),
                **plugin_info.get("init_params", {})
            )
            
            # Persona'yı başlat
            success = await plugin_instance.initialize()
            
            if success:
                # Yüklü eklentilere ekle
                self.loaded_plugins[plugin_id] = plugin_instance
                logger.info(f"Plugin yüklendi ve başlatıldı: {plugin_id}")
                return plugin_instance
            else:
                logger.error(f"Plugin başlatılamadı: {plugin_id}")
                return None
            
        except Exception as e:
            logger.error(f"Plugin yüklenirken hata: {plugin_id}, {str(e)}")
            return None
    
    async def unload_plugin(self, plugin_id: str) -> bool:
        """Bir eklentiyi kaldır"""
        if plugin_id not in self.loaded_plugins:
            return False
        
        try:
            # Eklentiyi durdur
            plugin_instance = self.loaded_plugins[plugin_id]
            await plugin_instance.shutdown()
            
            # Yüklü eklentilerden kaldır
            del self.loaded_plugins[plugin_id]
            logger.info(f"Plugin kaldırıldı: {plugin_id}")
            
            return True
        except Exception as e:
            logger.error(f"Plugin kaldırılırken hata: {plugin_id}, {str(e)}")
            return False
    
    async def update_plugin_status(self, plugin_id: str, enabled: bool) -> bool:
        """Eklenti durumunu güncelle (etkinleştir/devre dışı bırak)"""
        if plugin_id not in self.plugins:
            return False
        
        plugin_info = self.plugins[plugin_id]
        plugin_info["enabled"] = enabled
        
        # Metadata dosyasını güncelle
        metadata_path = os.path.join(self.plugin_dir, "metadata", f"{plugin_id}.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(plugin_info, f, ensure_ascii=False, indent=2)
        
        # Eğer etkinleştirildi ve henüz yüklü değilse yükle
        if enabled and plugin_id not in self.loaded_plugins:
            await self.load_plugin(plugin_id)
        
        # Eğer devre dışı bırakıldı ve yüklü ise kaldır
        elif not enabled and plugin_id in self.loaded_plugins:
            await self.unload_plugin(plugin_id)
        
        logger.info(f"Plugin durumu güncellendi: {plugin_id}, enabled={enabled}")
        return True
    
    async def update_plugin_workflow(self, plugin_id: str, workflow_steps: List[Dict], workflow_transitions: List[Dict] = None) -> bool:
        """Eklentinin iş akışını güncelle"""
        if plugin_id not in self.plugins:
            return False
        
        plugin_info = self.plugins[plugin_id]
        plugin_info["workflow_steps"] = workflow_steps
        
        if workflow_transitions is not None:
            plugin_info["workflow_transitions"] = workflow_transitions
        
        # Metadata dosyasını güncelle
        metadata_path = os.path.join(self.plugin_dir, "metadata", f"{plugin_id}.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(plugin_info, f, ensure_ascii=False, indent=2)
        
        # Eğer plugin yüklü ise, iş akışını güncelle
        if plugin_id in self.loaded_plugins:
            plugin_instance = self.loaded_plugins[plugin_id]
            plugin_instance.workflow_steps = workflow_steps
            
            if workflow_transitions is not None:
                plugin_instance.workflow_transitions = workflow_transitions
                
            logger.info(f"Plugin iş akışı güncellendi: {plugin_id}")
            
        return True