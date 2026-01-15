# os_araci/mcp_core/tool_discovery.py
import importlib
import pkgutil
import inspect
import logging
import os
from typing import List, Dict, Any, Type
from os_araci.mcp_core.tool import MCPTool
from os_araci.mcp_core.registry import MCPRegistry

logger = logging.getLogger(__name__)

class ToolDiscovery:
    """MCP araçlarını keşfetme ve kaydedilmesi için sınıf"""
    
    def __init__(self, registry: MCPRegistry, scan_packages: List[str] = None):
        """
        ToolDiscovery başlatıcı
        
        Args:
            registry: MCP araçlarının kaydedileceği registry
            scan_packages: Taranacak paketlerin listesi
        """
        self.registry = registry
        self.scan_packages = scan_packages or ["os_araci.tools"]
        self.discovered_tools = {}  # tool_name -> tool_class
        self.registered_tools = {}  # tool_name -> tool_instance
    
    def discover_tools(self) -> Dict[str, Type[MCPTool]]:
        """
        Belirtilen paketlerdeki tüm MCP araçlarını keşfet
        
        Returns:
            Dict[str, Type[MCPTool]]: Keşfedilen araç sınıflarının sözlüğü
        """
        discovered = {}
        
        for package_name in self.scan_packages:
            try:
                # Paketi içe aktar
                package = importlib.import_module(package_name)
                
                # Paket içindeki tüm modülleri tara
                for _, name, is_pkg in pkgutil.iter_modules(package.__path__, package.__name__ + '.'):
                    try:
                        # Modülü yükle
                        module = importlib.import_module(name)
                        
                        # Modül içindeki sınıfları bul
                        for item_name, item in inspect.getmembers(module, inspect.isclass):
                            # MCPTool sınıfları ara (ancak temel sınıfı değil)
                            if (issubclass(item, MCPTool) and 
                                item is not MCPTool):
                                
                                # Araç adını belirle (sınıf adı veya override edilmiş adı)
                                if hasattr(item, 'tool_name'):
                                    tool_name = item.tool_name
                                else:
                                    tool_name = item_name
                                
                                # Keşfedilen araçları kaydet
                                discovered[tool_name] = item
                                logger.debug(f"MCP aracı keşfedildi: {tool_name} ({name})")
                    
                    except Exception as e:
                        logger.error(f"Modül yüklenirken hata: {name}, {str(e)}")
            
            except ImportError as e:
                logger.error(f"Paket yüklenemedi: {package_name}, {str(e)}")
        
        self.discovered_tools = discovered
        logger.info(f"{len(discovered)} MCP aracı keşfedildi")
        return discovered
    
    def register_tools(self, tool_classes: Dict[str, Type[MCPTool]] = None) -> Dict[str, MCPTool]:
        """
        Keşfedilen araçları registry'ye kaydet
        
        Args:
            tool_classes: Kaydedilecek araç sınıflarının sözlüğü (None ise discover_tools'un sonuçları kullanılır)
            
        Returns:
            Dict[str, MCPTool]: Kaydedilen araç örneklerinin sözlüğü
        """
        if tool_classes is None:
            tool_classes = self.discovered_tools
        
        registered = {}
        
        for tool_name, tool_class in tool_classes.items():
            try:
                # Aracın bir örneğini oluştur
                tool_instance = tool_class()
                
                # Registry'ye kaydet
                if self.registry.register_local_tool(tool_instance):
                    registered[tool_name] = tool_instance
                    logger.info(f"MCP aracı kaydedildi: {tool_name}")
            except Exception as e:
                logger.error(f"Araç başlatılamadı: {tool_name}, {str(e)}")
        
        self.registered_tools = registered
        logger.info(f"{len(registered)} MCP aracı registry'ye kaydedildi")
        return registered
    
    def auto_discover_and_register(self) -> Dict[str, MCPTool]:
        """
        Araçları otomatik olarak keşfet ve kaydet
        
        Returns:
            Dict[str, MCPTool]: Kaydedilen araç örneklerinin sözlüğü
        """
        # Araçları keşfet
        discovered = self.discover_tools()
        
        # Keşfedilen araçları kaydet
        return self.register_tools(discovered)
    
    def load_config_for_tools(self, config_directory: str = "config/tools") -> int:
        """
        Araçlar için yapılandırma dosyalarını yükle
        
        Args:
            config_directory: Yapılandırma dosyalarının bulunduğu dizin
            
        Returns:
            int: Yüklenen yapılandırma dosyası sayısı
        """
        if not os.path.exists(config_directory) or not os.path.isdir(config_directory):
            logger.warning(f"Yapılandırma dizini bulunamadı: {config_directory}")
            return 0
        
        config_count = 0
        
        # Dizindeki tüm .json dosyalarını tara
        for filename in os.listdir(config_directory):
            if filename.endswith('.json'):
                try:
                    # Araç adını belirle (dosya adından)
                    tool_name = os.path.splitext(filename)[0]
                    
                    # Yapılandırma dosyasını oku
                    config_path = os.path.join(config_directory, filename)
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    
                    # Kayıtlı araçları kontrol et
                    for registered_name, tool in self.registered_tools.items():
                        if registered_name.lower() == tool_name.lower():
                            # Aracın yapılandırmasını ayarla
                            if hasattr(tool, 'configure') and callable(tool.configure):
                                tool.configure(config)
                                logger.info(f"Araç yapılandırması yüklendi: {registered_name}")
                                config_count += 1
                
                except Exception as e:
                    logger.error(f"Yapılandırma dosyası yüklenirken hata: {filename}, {str(e)}")
        
        logger.info(f"{config_count} araç yapılandırması yüklendi")
        return config_count