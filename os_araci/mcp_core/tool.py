# mcp_core/tool.py
from typing import Dict, Any, Callable, Optional, List
import logging

logger = logging.getLogger(__name__)

class MCPTool:
    """MCP araçları için temel sınıf – action tabanlı ve yetenekler desteği ile"""

    def __init__(self, name: str, description: str, version: str = "1.0.0", category: str = "general"):
        """
        MCPTool başlatıcı

        Args:
            name: Araç adı (benzersiz olmalı)
            description: Araç açıklaması
            version: Araç sürümü
            category: Araç kategorisi
        """
        self.name = name
        self.description = description
        self.version = version
        self.category = category
        self._actions: Dict[str, Dict[str, Any]] = {}
        self._capabilities: List[str] = []
        
    def register_action(
        self,
        name: str,
        handler: Callable,
        params: Optional[list] = None,
        description: str = "",
        required_capabilities: List[str] = None
    ) -> bool:
        """
        Bir action fonksiyonu kaydet

        Args:
            name: Action adı
            handler: Çağrılacak fonksiyon
            params: Beklenen parametre isimleri
            description: Açıklama
            required_capabilities: Bu aksiyon için gereken yetenekler

        Returns:
            bool: Kayıt başarılı mı?
        """
        if name in self._actions:
            logger.warning(f"Aksiyon zaten kayıtlı: {name}, araç: {self.name}")
            return False

        self._actions[name] = {
            "func": handler,
            "params": params or [],
            "description": description,
            "required_capabilities": required_capabilities or []
        }
        logger.info(f"Aksiyon kaydedildi: {name}, araç: {self.name}")
        return True

    def register_capability(self, capability: str, description: str = "") -> bool:
        """
        Bir yetenek kaydeder

        Args:
            capability: Yetenek adı (benzersiz olmalı)
            description: Yetenek açıklaması

        Returns:
            bool: Kayıt başarılı mı?
        """
        if capability in self._capabilities:
            logger.warning(f"Yetenek zaten kayıtlı: {capability}, araç: {self.name}")
            return False
            
        self._capabilities.append(capability)
        logger.info(f"Yetenek kaydedildi: {capability}, araç: {self.name}")
        return True
    
    def has_capability(self, capability: str) -> bool:
        """
        Aracın belirli bir yeteneğe sahip olup olmadığını kontrol eder

        Args:
            capability: Kontrol edilecek yetenek

        Returns:
            bool: Yetenek mevcut mu?
        """
        return capability in self._capabilities
    
    def get_capabilities(self) -> List[str]:
        """
        Aracın desteklediği tüm yetenekleri döndürür

        Returns:
            List[str]: Yetenekler listesi
        """
        return self._capabilities.copy()

    def standardize_result(self, result: Any, status: str = "success", message: str = None) -> Dict[str, Any]:
        """Aksiyon sonucunu standart formata dönüştür
        
        Args:
            result: Aksiyon sonucu
            status: Durum (success/error)
            message: İsteğe bağlı mesaj
        
        Returns:
            Standardize edilmiş sonuç
        """
        if isinstance(result, dict) and "status" in result:
            # Zaten standart formatta
            return result
        
        standard_result = {
            "status": status,
            "result": result
        }
        
        if message:
            standard_result["message"] = message
            
        return standard_result

    def execute_action(self, name: str, **kwargs) -> Any:
        """
        Kayıtlı bir action'ı çalıştır

        Args:
            name: Action adı
            kwargs: Parametreler

        Returns:
            Any: Action çıktısı
        """
        action = self._actions.get(name)
        if not action:
            raise ValueError(f"Aksiyon bulunamadı: {name}")

        # Aksiyon için gerekli yetenekleri kontrol et
        required_capabilities = action.get("required_capabilities", [])
        for capability in required_capabilities:
            if not self.has_capability(capability):
                raise ValueError(f"Aksiyon {name} için gerekli yetenek eksik: {capability}")

        return action["func"](**kwargs)

    def get_action(self, name: str) -> Optional[Callable]:
        """
        Belirli bir action fonksiyonunu getir

        Args:
            name: Action adı

        Returns:
            Callable: Fonksiyon
        """
        action = self._actions.get(name)
        return action["func"] if action else None

    def get_action_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Belirli bir action hakkında detaylı bilgi getir

        Args:
            name: Action adı

        Returns:
            Dict: Action metadata
        """
        if name not in self._actions:
            return None
            
        action = self._actions[name].copy()
        # Fonksiyonu kaldır, sadece metadata dön
        action.pop("func", None)
        return action

    def get_all_actions(self) -> Dict[str, Dict[str, Any]]:
        """
        Tüm kayıtlı action'ları döndür (metadata dahil, fonksiyon hariç)

        Returns:
            Dict: action adı → dict(params, description, required_capabilities)
        """
        result = {}
        for name, action in self._actions.items():
            action_info = action.copy()
            # Fonksiyonu kaldır, sadece metadata dön
            action_info.pop("func", None)
            result[name] = action_info
            
        return result

    def get_metadata(self) -> Dict[str, Any]:
        """
        Araç hakkında metadata bilgilerini döndürür

        Returns:
            Dict: Metadata bilgileri
        """
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "category": self.category,
            "capabilities": self.get_capabilities(),
            "actions": list(self._actions.keys())
        }

    def describe(self) -> Dict[str, Any]:
        """
        Araç ve aksiyonları hakkında detaylı açıklama döndürür

        Returns:
            Dict: Araç açıklaması
        """
        return {
            "metadata": self.get_metadata(),
            "actions": self.get_all_actions()
        }

    def initialize(self) -> bool:
        """Araç başlatıldığında çağrılır"""
        logger.info(f"Araç başlatıldı: {self.name}")
        return True

    def shutdown(self) -> bool:
        """Araç kapanırken çağrılır"""
        logger.info(f"Araç kapatıldı: {self.name}")
        return True
        
    def check_health(self) -> Dict[str, Any]:
        """
        Aracın sağlık durumunu kontrol eder

        Returns:
            Dict: Sağlık durumu bilgileri
        """
        return {
            "status": "healthy",
            "message": f"{self.name} aracı çalışıyor",
            "version": self.version
        }

    def __repr__(self) -> str:
        return f"MCPTool(name={self.name}, version={self.version}, capabilities={self._capabilities}, actions={list(self._actions.keys())})"