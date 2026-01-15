# mcp_core/monitoring/health_monitor.py
import logging
import threading
import time
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class ToolHealthMonitor:
    """Araç sağlık durumunu izleme servisi"""
    
    def __init__(self, registry, check_interval: int = 300):
        """
        Sağlık izleme servisi başlatıcı
        
        Args:
            registry: MCP Registry örneği
            check_interval: Kontrol aralığı (saniye)
        """
        self.registry = registry
        self.check_interval = check_interval
        self.health_status = {}  # tool_id -> health_status
        self.running = False
        self.thread = None
    
    def start(self):
        """Sağlık izleme servisini başlat"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop)
        self.thread.daemon = True
        self.thread.start()
        logger.info(f"Araç sağlık izleme servisi başlatıldı (kontrol aralığı: {self.check_interval}s)")
    
    def stop(self):
        """Sağlık izleme servisini durdur"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        logger.info("Araç sağlık izleme servisi durduruldu")
    
    def _monitor_loop(self):
        """Sağlık izleme döngüsü"""
        while self.running:
            try:
                self._check_all_tools()
            except Exception as e:
                logger.error(f"Sağlık izleme hatası: {str(e)}")
            
            # Bir sonraki kontrole kadar bekle
            time.sleep(self.check_interval)
    
    def _check_all_tools(self):
        """Tüm araçların sağlık durumunu kontrol et"""
        # Registry'deki ToolSourceType sınıfını kullanmak için import
        try:
            from os_araci.mcp_core.registry import ToolSourceType
        except ImportError:
            # Registry modülünü import edemezse
            logger.error("ToolSourceType import edilemedi")
            return
            
        # Dış kaynak ve uzak araçları kontrol et
        for tool_id, metadata in self.registry.get_all_metadata().items():
            if metadata.source_type in [ToolSourceType.EXTERNAL, ToolSourceType.REMOTE]:
                tool = self.registry.get_tool_by_id(tool_id)
                if not tool:
                    continue
                
                try:
                    # Sağlık kontrolü yap
                    if hasattr(tool, 'check_health') and callable(tool.check_health):
                        health_status = tool.check_health()
                    else:
                        # Özel sağlık kontrolü yoksa basit bir kontrol yap
                        if metadata.source_type == ToolSourceType.REMOTE:
                            if hasattr(tool, 'remote_url') and hasattr(self.registry._remote_proxy, 'ping'):
                                health_status = {
                                    "status": "healthy" if self.registry._remote_proxy.ping(tool.remote_url, tool.auth_info) else "unhealthy",
                                    "timestamp": time.time()
                                }
                            else:
                                health_status = {"status": "unknown", "timestamp": time.time()}
                        else:  # EXTERNAL
                            health_status = {"status": "unknown", "timestamp": time.time()}
                    
                    # Sağlık durumunu güncelle
                    self.health_status[tool_id] = health_status
                    
                    # Durumu logla
                    status = health_status.get("status", "unknown")
                    if status != "healthy":
                        logger.warning(f"Araç sağlık durumu: {tool_id} - {status}")
                    
                except Exception as e:
                    logger.error(f"Araç sağlık kontrolü başarısız: {tool_id}, {str(e)}")
                    self.health_status[tool_id] = {
                        "status": "error",
                        "message": str(e),
                        "timestamp": time.time()
                    }
    
    def get_status(self, tool_id: str = None) -> Dict[str, Any]:
        """Araç(lar)ın sağlık durumunu getir"""
        if tool_id:
            return self.health_status.get(tool_id, {"status": "unknown"})
        return self.health_status
    
    def is_healthy(self, tool_id: str) -> bool:
        """Aracın sağlıklı olup olmadığını kontrol et"""
        status = self.health_status.get(tool_id, {}).get("status", "unknown")
        return status == "healthy"
    
    def get_unhealthy_tools(self) -> List[str]:
        """Sağlıksız araçların listesini getir"""
        unhealthy = []
        for tool_id, status in self.health_status.items():
            if status.get("status", "unknown") != "healthy":
                unhealthy.append(tool_id)
        return unhealthy