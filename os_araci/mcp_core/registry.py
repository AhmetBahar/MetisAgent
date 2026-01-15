# mcp_core/registry.py
import logging
import json
from typing import Dict, Any, Callable, List, Optional, Union
import importlib
import pkgutil
import inspect
import requests
import time
import os
from enum import Enum
from os_araci.mcp_core.tool import MCPTool
from os_araci.mcp_core.monitoring.health_monitor import ToolHealthMonitor

logger = logging.getLogger(__name__)

class ToolSourceType(Enum):
    """Araç kaynağı tipini tanımlayan enum"""
    LOCAL = "local"         # Yerel MCP aracı
    EXTERNAL = "external"   # Dış kaynaklı REST/GraphQL servisi
    REMOTE = "remote"       # Uzak MCP sunucusu

class ToolMetadata:
    """Araç metadata bilgilerini saklayan sınıf"""
    
    def __init__(self, 
                tool_id: str, 
                name: str, 
                version: str,
                source_type: ToolSourceType,
                description: str = "",
                capabilities: List[str] = None,
                endpoint: str = None,
                auth_info: Dict = None,
                category: str = "general",
                access_level: str = "standard",
                tags: List[str] = None,
                owner: str = None,
                created_at: float = None,
                updated_at: float = None):
        
        self.tool_id = tool_id
        self.name = name
        self.version = version
        self.source_type = source_type
        self.description = description
        self.capabilities = capabilities or []
        self.endpoint = endpoint
        self.auth_info = auth_info or {}
        self.category = category
        self.access_level = access_level
        self.tags = tags or []
        self.owner = owner or "system"
        self.created_at = created_at or time.time()
        self.updated_at = updated_at or time.time()
    
    def to_dict(self) -> Dict:
        """Metadata bilgilerini sözlüğe dönüştür"""
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "version": self.version,
            "source_type": self.source_type.value,
            "description": self.description,
            "capabilities": self.capabilities,
            "endpoint": self.endpoint,
            "category": self.category,
            "access_level": self.access_level,
            "tags": self.tags,
            "owner": self.owner,
            "created_at": self.created_at,
            "updated_at": self.updated_at
            # auth_info güvenlik amacıyla dışarıda bırakılıyor
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ToolMetadata':
        """Sözlükten metadata oluştur"""
        source_type = ToolSourceType(data.get("source_type", "local"))
        return cls(
            tool_id=data.get("tool_id"),
            name=data.get("name"),
            version=data.get("version", "1.0.0"),
            source_type=source_type,
            description=data.get("description", ""),
            capabilities=data.get("capabilities", []),
            endpoint=data.get("endpoint"),
            auth_info=data.get("auth_info", {}),
            category=data.get("category", "general"),
            access_level=data.get("access_level", "standard"),
            tags=data.get("tags", []),
            owner=data.get("owner", "system"),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time())
        )
    
    def find_tools_by_tags(self, tags: List[str], match_all: bool = False) -> List[str]:
        """Belirli etiketlere sahip araçların ID'lerini bul
        
        Args:
            tags: Aranacak etiketler
            match_all: True ise tüm etiketlerle eşleşen araçları, False ise herhangi biriyle eşleşenleri döndür
        
        Returns:
            Eşleşen araç ID'leri listesi
        """
        matching_tools = []
        
        for tool_id, metadata in self._tool_metadata.items():
            # Hiç tag yoksa atla
            if not hasattr(metadata, 'tags') or not metadata.tags:
                continue
            
            # Tüm tagler ile eşleşme kontrolü
            if match_all:
                if all(tag in metadata.tags for tag in tags):
                    matching_tools.append(tool_id)
            # Herhangi bir tag ile eşleşme kontrolü
            else:
                if any(tag in metadata.tags for tag in tags):
                    matching_tools.append(tool_id)
        
        return matching_tools

class MCPRegistry:
    """Genişletilmiş MCP araçlarını yönetme ve kaydetme için registry sınıfı"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MCPRegistry, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config_path=None):
        if not self._initialized:
            logger.info("Genişletilmiş MCPRegistry başlatılıyor...")
            # Araçları kaynak tipine göre ayırma
            self._local_tools = {}     # Yerel MCP araçları
            self._external_tools = {}  # Dış kaynak araçları
            self._remote_tools = {}    # Uzak MCP araçları
            
            # Tüm araçların metadata bilgileri
            self._tool_metadata = {}   # tool_id -> metadata
            
            # Adaptör ve proxy sınıflarını yükle
            self._initialize_adapters()
            
            # Kalıcı yapılandırma dosya yolu
            self._config_path = config_path or os.path.join(os.getcwd(), 'registry_config.json')
            
            self.health_monitor = ToolHealthMonitor(self)
            self.health_monitor.start()
            
            # Kaydedilmiş yapılandırmayı yükle
            self._load_configuration()
            
            self._initialized = True

    # Yeni metod: Yapılandırmayı yükle
    def _load_configuration(self):
        """Kayıtlı yapılandırmayı yükle"""
        if os.path.exists(self._config_path):
            try:
                logger.info(f"Yapılandırma dosyası yükleniyor: {self._config_path}")
                self.import_configuration(self._config_path)
            except Exception as e:
                logger.error(f"Yapılandırma yüklenirken hata: {str(e)}")

    # Yeni metod: Yapılandırmayı otomatik kaydet
    def _save_configuration(self):
        """Mevcut yapılandırmayı otomatik kaydet"""
        try:
            self.export_configuration(self._config_path)
            logger.info(f"Yapılandırma kaydedildi: {self._config_path}")
            return True
        except Exception as e:
            logger.error(f"Yapılandırma kaydedilirken hata: {str(e)}")
            return False
    
    def _initialize_adapters(self):
        """Adaptör ve proxy sınıflarını yükle"""
        try:
            # Adaptör sınıflarını lazy-loading ile yükle
            from os_araci.mcp_core.adapters.external_tool_adapter import ExternalToolAdapter
            from os_araci.mcp_core.adapters.remote_tool_proxy import RemoteToolProxy
            
            self._external_adapter = ExternalToolAdapter()
            self._remote_proxy = RemoteToolProxy()
            logger.info("Adaptör ve proxy sınıfları başarıyla yüklendi")
        except ImportError as e:
            logger.warning(f"Adaptör sınıfları yüklenemedi: {str(e)}")
            # Adaptör sınıfları yoksa stub sınıflar tanımla
            self._external_adapter = None
            self._remote_proxy = None
    
    def register_local_tool(self, tool: MCPTool) -> bool:
        """Yerel bir MCP aracını kaydet"""
        if tool.name in self._local_tools:
            logger.warning(f"Araç zaten kayıtlı: {tool.name}")
            return False
        
        # Araç için benzersiz ID oluştur
        tool_id = f"local.{tool.name}.{tool.version}"
        
        # Araç yeteneklerini (capabilities) al
        capabilities = []
        if hasattr(tool, 'get_capabilities') and callable(tool.get_capabilities):
            capabilities = tool.get_capabilities()
        
        # Metadata oluştur
        metadata = ToolMetadata(
            tool_id=tool_id,
            name=tool.name,
            version=tool.version,
            source_type=ToolSourceType.LOCAL,
            description=tool.description if hasattr(tool, 'description') else "",
            capabilities=capabilities,
            category=tool.category if hasattr(tool, 'category') else "general"
        )
        
        # Aracı kaydet
        self._local_tools[tool.name] = tool
        self._tool_metadata[tool_id] = metadata
        
        self._save_configuration()  # Her kayıt işleminden sonra yapılandırmayı kaydet

        logger.info(f"Yerel araç kaydedildi: {tool.name} (v{tool.version})")
        return True
    
    def register_external_tool(self, 
                              name: str, 
                              config: Dict[str, Any],
                              capabilities: List[str] = None) -> bool:
        """Dış kaynak aracını kaydet"""
        if name in self._external_tools:
            logger.warning(f"Dış kaynak aracı zaten kayıtlı: {name}")
            return False
        
        if not self._external_adapter:
            logger.error("ExternalToolAdapter sınıfı yüklenemedi")
            return False
        
        # Araç için benzersiz ID oluştur
        version = config.get("version", "1.0.0")
        tool_id = f"external.{name}.{version}"
        
        # Metadata oluştur
        metadata = ToolMetadata(
            tool_id=tool_id,
            name=name,
            version=version,
            source_type=ToolSourceType.EXTERNAL,
            description=config.get("description", ""),
            capabilities=capabilities or [],
            endpoint=config.get("base_url"),
            auth_info=config.get("auth", {}),
            category=config.get("category", "external")
        )
        
        # Adaptör aracılığıyla aracı oluştur
        tool = self._external_adapter.create_tool(name, config)
        if not tool:
            logger.error(f"Dış kaynak aracı oluşturulamadı: {name}")
            return False
        
        # Aracı kaydet
        self._external_tools[name] = tool
        self._tool_metadata[tool_id] = metadata
        
        self._save_configuration()  # Her kayıt işleminden sonra yapılandırmayı kaydet

        logger.info(f"Dış kaynak aracı kaydedildi: {name} (v{version})")
        return True
    
    def register_remote_tool(self, 
                            name: str, 
                            remote_url: str,
                            auth_info: Dict = None) -> bool:
        """Uzak MCP sunucusundaki bir aracı kaydet"""
        if name in self._remote_tools:
            logger.warning(f"Uzak araç zaten kayıtlı: {name}")
            return False
        
        if not self._remote_proxy:
            logger.error("RemoteToolProxy sınıfı yüklenemedi")
            return False
        
        # Uzak sunucu ile handshake ve araç meta verilerini al
        try:
            remote_metadata = self._remote_proxy.get_tool_metadata(remote_url, name, auth_info)
            if not remote_metadata:
                logger.error(f"Uzak araç meta verileri alınamadı: {name}")
                return False
            
            # Araç için benzersiz ID oluştur
            version = remote_metadata.get("version", "1.0.0")
            tool_id = f"remote.{name}.{version}"
            
            # Metadata oluştur
            metadata = ToolMetadata(
                tool_id=tool_id,
                name=name,
                version=version,
                source_type=ToolSourceType.REMOTE,
                description=remote_metadata.get("description", ""),
                capabilities=remote_metadata.get("capabilities", []),
                endpoint=remote_url,
                auth_info=auth_info or {},
                category=remote_metadata.get("category", "remote")
            )
            
            # Proxy aracılığıyla uzak aracı oluştur
            tool = self._remote_proxy.create_proxy(name, remote_url, auth_info)
            if not tool:
                logger.error(f"Uzak araç proxy'si oluşturulamadı: {name}")
                return False
            
            # Aracı kaydet
            self._remote_tools[name] = tool
            self._tool_metadata[tool_id] = metadata
            
            self._save_configuration()  # Her kayıt işleminden sonra yapılandırmayı kaydet

            logger.info(f"Uzak araç kaydedildi: {name} (v{version})")
            return True
            
        except Exception as e:
            logger.error(f"Uzak araç kaydedilemedi: {name}, {str(e)}")
            return False
    
    def sync_remote_tools(self, remote_url: str, auth_info: Dict = None) -> List[str]:
        """Uzak MCP sunucusundan tüm araçları senkronize et"""
        if not self._remote_proxy:
            logger.error("RemoteToolProxy sınıfı yüklenemedi")
            return []
        
        try:
            # Uzak sunucudaki tüm araçları listele
            remote_tools = self._remote_proxy.list_remote_tools(remote_url, auth_info)
            if not remote_tools:
                logger.warning(f"Uzak sunucuda araç bulunamadı: {remote_url}")
                return []
            
            # Her birini kaydet
            registered = []
            for tool_info in remote_tools:
                name = tool_info.get("name")
                if name and self.register_remote_tool(name, remote_url, auth_info):
                    registered.append(name)
            
            logger.info(f"Uzak sunucudan {len(registered)} araç senkronize edildi: {remote_url}")
            return registered
            
        except Exception as e:
            logger.error(f"Uzak sunucu ile senkronizasyon hatası: {remote_url}, {str(e)}")
            return []
    
    def unregister(self, tool_id: str) -> bool:
        """Bir aracın kaydını kaldır"""
        if tool_id not in self._tool_metadata:
            logger.warning(f"Araç bulunamadı: {tool_id}")
            return False
        
        metadata = self._tool_metadata[tool_id]
        name = metadata.name
        source_type = metadata.source_type
        
        # Kaynağına göre aracı bul
        if source_type == ToolSourceType.LOCAL and name in self._local_tools:
            tool = self._local_tools[name]
            # Araç kapanış fonksiyonunu çağır
            if hasattr(tool, 'shutdown') and callable(tool.shutdown):
                try:
                    tool.shutdown()
                except Exception as e:
                    logger.error(f"Araç kapatılırken hata: {name}, {str(e)}")
            
            # Aracı registry'den kaldır
            del self._local_tools[name]
            del self._tool_metadata[tool_id]
            self._save_configuration()  # Her kayıt işleminden sonra yapılandırmayı kaydet
            logger.info(f"Yerel araç kaydı kaldırıldı: {name}")
            return True
            
        elif source_type == ToolSourceType.EXTERNAL and name in self._external_tools:
            # Dış kaynak aracını kaldır
            del self._external_tools[name]
            del self._tool_metadata[tool_id]
            self._save_configuration()  # Her kayıt işleminden sonra yapılandırmayı kaydet
            logger.info(f"Dış kaynak aracı kaydı kaldırıldı: {name}")
            return True
            
        elif source_type == ToolSourceType.REMOTE and name in self._remote_tools:
            # Uzak aracı kaldır
            del self._remote_tools[name]
            del self._tool_metadata[tool_id]
            self._save_configuration()  # Her kayıt işleminden sonra yapılandırmayı kaydet
            logger.info(f"Uzak araç kaydı kaldırıldı: {name}")
            return True
        
        logger.warning(f"Araç kaydı kaldırılamadı: {tool_id}")
        return False
    
    def get_tool(self, tool_name: str, source_type: ToolSourceType = None) -> Any:
        """İsimle bir aracı getir, kaynak tipi belirtilirse sadece o kaynakta ara"""
        # Kaynak tipi belirtilmişse sadece o kaynakta ara
        if source_type == ToolSourceType.LOCAL:
            return self._local_tools.get(tool_name)
        elif source_type == ToolSourceType.EXTERNAL:
            return self._external_tools.get(tool_name)
        elif source_type == ToolSourceType.REMOTE:
            return self._remote_tools.get(tool_name)
        
        # Kaynak tipi belirtilmemişse tüm kaynaklarda ara
        tool = self._local_tools.get(tool_name)
        if tool:
            return tool
        
        tool = self._external_tools.get(tool_name)
        if tool:
            return tool
        
        return self._remote_tools.get(tool_name)
    
    def get_tool_by_id(self, tool_id: str) -> Any:
        """ID ile bir aracı getir"""
        if tool_id not in self._tool_metadata:
            return None
        
        metadata = self._tool_metadata[tool_id]
        return self.get_tool(metadata.name, metadata.source_type)
    
    def get_metadata(self, tool_id: str) -> Optional[ToolMetadata]:
        """Araç metadata bilgilerini getir"""
        return self._tool_metadata.get(tool_id)
    
    def get_all_metadata(self) -> Dict[str, ToolMetadata]:
        """Tüm araçların metadata bilgilerini getir"""
        return self._tool_metadata.copy()
    
    def get_all_tools(self, source_type: ToolSourceType = None) -> Dict[str, Any]:
        """Kayıtlı tüm araçları getir, kaynak tipi belirtilirse sadece o kaynaktakileri getir"""
        if source_type == ToolSourceType.LOCAL:
            return self._local_tools.copy()
        elif source_type == ToolSourceType.EXTERNAL:
            return self._external_tools.copy()
        elif source_type == ToolSourceType.REMOTE:
            return self._remote_tools.copy()
        
        # Tüm araçları birleştir
        all_tools = {}
        all_tools.update(self._local_tools)
        all_tools.update(self._external_tools)
        all_tools.update(self._remote_tools)
        
        return all_tools
    
    def find_tools_by_capabilities(self, capabilities: List[str]) -> List[str]:
        """Belirli yeteneklere sahip araçların ID'lerini bul"""
        matching_tools = []
        
        for tool_id, metadata in self._tool_metadata.items():
            # Tüm istenen yeteneklere sahip mi kontrol et
            if all(cap in metadata.capabilities for cap in capabilities):
                matching_tools.append(tool_id)
        
        return matching_tools
    
    def find_tools_by_category(self, category: str) -> List[str]:
        """Belirli kategorideki araçların ID'lerini bul"""
        return [tool_id for tool_id, metadata in self._tool_metadata.items() 
                if metadata.category == category]
    
    def call_handler(self, tool_id: str, action_name: str, **kwargs) -> Any:
        """Bir araç üzerinde belirli bir aksiyonu çağır"""
        # Önce tool_id ile aracı bul
        tool = self.get_tool_by_id(tool_id)
        if not tool:
            logger.error(f"Araç bulunamadı: {tool_id}")
            return {"status": "error", "message": f"Araç bulunamadı: {tool_id}"}, 404
        
        # Metadata bilgisini al
        metadata = self._tool_metadata.get(tool_id)
        if not metadata:
            logger.error(f"Araç metadata bilgileri bulunamadı: {tool_id}")
            return {"status": "error", "message": f"Araç metadata bilgileri bulunamadı: {tool_id}"}, 500
        
        # Aksiyon şemasını kontrol et ve parametreleri doğrula
        if metadata.source_type == ToolSourceType.LOCAL:
            # Yerel araç için aksiyon bilgilerini al
            if hasattr(tool, 'get_action_info') and callable(tool.get_action_info):
                action_info = tool.get_action_info(action_name)
                if action_info and 'params' in action_info:
                    # Zorunlu parametreleri kontrol et
                    missing_params = []
                    for param in action_info.get('params', []):
                        if param.get('required', False) and param.get('name') not in kwargs:
                            missing_params.append(param.get('name'))
                    
                    if missing_params:
                        logger.error(f"Eksik parametreler: {', '.join(missing_params)}")
                        return {
                            "status": "error", 
                            "message": f"Eksik parametreler: {', '.join(missing_params)}"
                        }, 400
        
        # Kaynak tipine göre işlemi yönlendir ve standardize edilmiş yanıt formatı
        try:
            result = None
            if metadata.source_type == ToolSourceType.LOCAL:
                # Yerel araç için direkt aksiyonu çağır
                action = tool.get_action(action_name)
                if not action:
                    logger.error(f"Aksiyon bulunamadı: {action_name}, araç: {tool_id}")
                    return {"status": "error", "message": f"Aksiyon bulunamadı: {action_name}"}, 404
                    
                result = action(**kwargs)
                    
            elif metadata.source_type == ToolSourceType.EXTERNAL:
                # Dış kaynak aracı için adaptörü kullan
                if not self._external_adapter:
                    logger.error("ExternalToolAdapter sınıfı yüklenemedi")
                    return {"status": "error", "message": "Dış kaynak adaptörü kullanılamıyor"}, 500
                    
                result = self._external_adapter.call_action(tool, action_name, **kwargs)
                    
            elif metadata.source_type == ToolSourceType.REMOTE:
                # Uzak araç için proxy'yi kullan
                if not self._remote_proxy:
                    logger.error("RemoteToolProxy sınıfı yüklenemedi")
                    return {"status": "error", "message": "Uzak araç proxy'si kullanılamıyor"}, 500
                    
                result = self._remote_proxy.call_action(tool, action_name, **kwargs)
            
            # Yanıt formatını standardize et
            if isinstance(result, tuple) and len(result) == 2 and isinstance(result[1], int):
                # (response, status_code) formatı
                return result
            elif isinstance(result, dict) and "status" in result:
                # Zaten standardize edilmiş
                return result
            else:
                # Sonucu standardize et
                return {"status": "success", "result": result}
        except Exception as e:
            logger.error(f"Aksiyon çağrılırken hata: {tool_id}.{action_name}, {str(e)}")
            return {"status": "error", "message": str(e)}, 500

    def get_tool_versions(self, name: str) -> List[Dict[str, Any]]:
        """Belirli bir aracın tüm versiyonlarını getir"""
        versions = []
        
        for tool_id, metadata in self._tool_metadata.items():
            if metadata.name == name:
                versions.append({
                    "tool_id": tool_id,
                    "version": metadata.version,
                    "source_type": metadata.source_type.value
                })
        
        # Versiyon numarasına göre sırala
        versions.sort(key=lambda x: [int(v) if v.isdigit() else v 
                                    for v in x['version'].split('.')])
        
        return versions

    def get_latest_version(self, name: str) -> Optional[str]:
        """Belirli bir aracın en son versiyonunun ID'sini getir"""
        versions = self.get_tool_versions(name)
        return versions[-1]["tool_id"] if versions else None
    
    def initialize_all(self) -> bool:
        """Tüm kayıtlı araçları başlat"""
        success = True
    
        # Yerel araçları başlat
        for name, tool in self._local_tools.items():
            try:
                if hasattr(tool, 'initialize') and callable(tool.initialize):
                    if not tool.initialize():
                        logger.error(f"Yerel araç başlatılamadı: {name}")
                        success = False
            except Exception as e:
                logger.error(f"Yerel araç başlatılırken hata: {name}, {str(e)}")
                success = False
            
            # External ve Remote araçlar için özel başlatma işlemleri gerekiyorsa burada yapılabilir
        
        return success
    
    def shutdown_all(self) -> bool:
        """Tüm kayıtlı araçları kapat"""
        success = True
        
        # Yerel araçları kapat
        for name, tool in self._local_tools.items():
            try:
                if hasattr(tool, 'shutdown') and callable(tool.shutdown):
                    if not tool.shutdown():
                        logger.error(f"Yerel araç kapatılamadı: {name}")
                        success = False
            except Exception as e:
                logger.error(f"Yerel araç kapatılırken hata: {name}, {str(e)}")
                success = False
        
        # External ve Remote araçlar için özel kapatma işlemleri gerekiyorsa burada yapılabilir
        # Sağlık izleme servisini durdur
        if hasattr(self, 'health_monitor') and self.health_monitor:
            self.health_monitor.stop()

        return success
    
    def get_tool_health(self, tool_id: str = None) -> Dict[str, Any]:
        """Araç(lar)ın sağlık durumunu getir"""
        if hasattr(self, 'health_monitor') and self.health_monitor:
            return self.health_monitor.get_status(tool_id)
        return {"status": "unknown", "message": "Sağlık izleme servisi aktif değil"}
    
    def is_tool_healthy(self, tool_id: str) -> bool:
        """Aracın sağlıklı olup olmadığını kontrol et"""
        if hasattr(self, 'health_monitor') and self.health_monitor:
            return self.health_monitor.is_healthy(tool_id)
        return False
    
    def discover_tools(self, package_name: str = 'tools') -> List[str]:
        """Belirtilen paketteki tüm MCP araçlarını keşfet ve kaydet"""
        discovered = []
        
        try:
            package = importlib.import_module(package_name)
            for _, name, is_pkg in pkgutil.iter_modules(package.__path__, package.__name__ + '.'):
                try:
                    module = importlib.import_module(name)
                    for item_name, item in inspect.getmembers(module):
                        # MCPTool sınıfları ara (ancak temel sınıfı değil)
                        if (inspect.isclass(item) and 
                            issubclass(item, MCPTool) and 
                            item is not MCPTool):
                            try:
                                # Sınıfın bir örneğini oluştur
                                tool_instance = item()
                                # Registry'ye kaydet
                                if self.register_local_tool(tool_instance):
                                    discovered.append(tool_instance.name)
                            except Exception as e:
                                logger.error(f"Araç başlatılamadı: {item_name}, {str(e)}")
                except Exception as e:
                    logger.error(f"Modül yüklenemedi: {name}, {str(e)}")
        except ImportError as e:
            logger.error(f"Paket yüklenemedi: {package_name}, {str(e)}")
        
        return discovered
    
    def export_configuration(self, file_path: str) -> bool:
        """Registry yapılandırmasını dışa aktar"""
        try:
            config = {
                "local_tools": [],
                "external_tools": [],
                "remote_tools": []
            }
            
            # Metadata bilgilerini kaydet
            for tool_id, metadata in self._tool_metadata.items():
                if metadata.source_type == ToolSourceType.LOCAL:
                    config["local_tools"].append(metadata.to_dict())
                elif metadata.source_type == ToolSourceType.EXTERNAL:
                    config["external_tools"].append(metadata.to_dict())
                elif metadata.source_type == ToolSourceType.REMOTE:
                    config["remote_tools"].append(metadata.to_dict())
            
            # JSON olarak dışa aktar
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            
            logger.info(f"Registry yapılandırması dışa aktarıldı: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Registry yapılandırması dışa aktarılırken hata: {str(e)}")
            return False
    
    def import_configuration(self, file_path: str) -> bool:
        """Registry yapılandırmasını içe aktar"""
        try:
            # JSON yapılandırmasını oku
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Yerel araçları içe aktar (bu sadece referans olarak kullanılır, gerçek yerel araçlar discover_tools ile yüklenir)
            # Burada sadece metadata bilgileri için
            
            # Dış kaynak araçlarını içe aktar
            for tool_config in config.get("external_tools", []):
                name = tool_config.get("name")
                if name:
                    # Dış kaynak aracı yapılandırması için ek bilgileri al
                    # Bu bilgiler ayrı bir dosyada saklanmalı
                    config_file = f"configs/external/{name}.json"
                    try:
                        with open(config_file, 'r', encoding='utf-8') as f:
                            ext_config = json.load(f)
                            self.register_external_tool(
                                name=name, 
                                config=ext_config,
                                capabilities=tool_config.get("capabilities", [])
                            )
                    except Exception as e:
                        logger.error(f"Dış kaynak aracı yapılandırması okunamadı: {name}, {str(e)}")
            
            # Uzak araçları içe aktar
            for tool_config in config.get("remote_tools", []):
                name = tool_config.get("name")
                endpoint = tool_config.get("endpoint")
                if name and endpoint:
                    # Uzak araç için auth bilgilerini al
                    # Bu bilgiler ayrı bir dosyada saklanmalı
                    auth_file = f"configs/remote/{name}_auth.json"
                    auth_info = {}
                    try:
                        with open(auth_file, 'r', encoding='utf-8') as f:
                            auth_info = json.load(f)
                    except Exception as e:
                        logger.warning(f"Uzak araç auth bilgileri okunamadı: {name}, {str(e)}")
                    
                    self.register_remote_tool(
                        name=name,
                        remote_url=endpoint,
                        auth_info=auth_info
                    )
            
            logger.info(f"Registry yapılandırması içe aktarıldı: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Registry yapılandırması içe aktarılırken hata: {str(e)}")
            return False