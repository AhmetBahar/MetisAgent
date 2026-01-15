# mcp_core/adapters/external_tool_adapter.py
import logging
import json
import requests
from typing import Dict, Any, Optional, List, Callable
import time
from os_araci.mcp_core.adapters.adapter_base import (
    ToolAdapterBase, 
    AuthHandlerFactory, 
    RateLimiter, 
    RetryHandler
)

logger = logging.getLogger(__name__)

class ExternalToolConfig:
    """Dış kaynak aracı yapılandırması"""
    
    def __init__(self, config: Dict[str, Any]):
        """Dış kaynak aracı yapılandırması başlatıcı
        
        Args:
            config: Yapılandırma bilgileri
        """
        self.name = config.get("name", "")
        self.version = config.get("version", "1.0.0")
        self.description = config.get("description", "")
        self.base_url = config.get("base_url", "")
        self.auth_type = config.get("auth_type", "none")
        self.auth_info = config.get("auth", {})
        self.endpoints = config.get("endpoints", {})
        self.parameters = config.get("parameters", {})
        self.headers = config.get("headers", {})
        self.timeout = config.get("timeout", 30)
        self.rate_limit = config.get("rate_limit", 60)  # dakikada istek sayısı
        self.retry_count = config.get("retry_count", 3)
        self.capabilities = config.get("capabilities", [])
        self.schema = config.get("schema", {})

class ExternalToolAdapter(ToolAdapterBase):
    """Dış kaynak araçları için adaptör"""
    
    def __init__(self):
        """Dış kaynak adaptörü başlatıcı"""
        super().__init__()
        self.tools = {}  # name -> ExternalToolProxy
        self.rate_limiters = {}  # name -> RateLimiter
        logger.info("ExternalToolAdapter başlatılıyor")
    
    def create_tool(self, name: str, config: Dict[str, Any]) -> Any:
        """Yapılandırma bilgileriyle dış kaynak aracı oluştur
        
        Args:
            name: Aracın adı
            config: Araç yapılandırma bilgileri
            
        Returns:
            Oluşturulan ExternalToolProxy nesnesi
        """
        if name in self.tools:
            logger.info(f"Dış kaynak aracı zaten mevcut: {name}")
            return self.tools[name]
        
        try:
            # Yapılandırma nesnesini oluştur
            tool_config = ExternalToolConfig(config)
            
            # Araç proxy'sini oluştur
            proxy = ExternalToolProxy(name, tool_config)
            
            # Hız sınırlayıcı oluştur
            self.rate_limiters[name] = RateLimiter(tool_config.rate_limit)
            
            # Aracı kaydet
            self.tools[name] = proxy
            
            logger.info(f"Dış kaynak aracı oluşturuldu: {name} ({tool_config.base_url})")
            return proxy
            
        except Exception as e:
            logger.error(f"Dış kaynak aracı oluşturulurken hata: {name}, {str(e)}")
            return None
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Araç yapılandırma bilgilerini doğrula
        
        Args:
            config: Doğrulanacak yapılandırma bilgileri
            
        Returns:
            Doğrulama sonucu (True/False)
        """
        # Gerekli alanların varlığını kontrol et
        required_fields = ["name", "base_url", "endpoints"]
        for field in required_fields:
            if field not in config:
                logger.error(f"Yapılandırmada gerekli alan eksik: {field}")
                return False
        
        # Endpoints yapısını kontrol et
        endpoints = config.get("endpoints", {})
        if not endpoints or not isinstance(endpoints, dict):
            logger.error("Yapılandırmada geçerli 'endpoints' alanı bulunmuyor")
            return False
        
        # En az bir endpoint tanımlanmış olmalı
        if len(endpoints) == 0:
            logger.error("En az bir endpoint tanımlanmalıdır")
            return False
        
        # Her endpoint için method ve path tanımlanmış olmalı
        for action, endpoint in endpoints.items():
            if "method" not in endpoint or "path" not in endpoint:
                logger.error(f"Endpoint tanımında gerekli alanlar eksik: {action}")
                return False
        
        return True
    
    def call_action(self, tool: Any, action_name: str, **kwargs) -> Any:
        """Dış kaynak aracında bir aksiyonu çağır
        
        Args:
            tool: ExternalToolProxy nesnesi
            action_name: Çağrılacak aksiyonun adı
            **kwargs: Aksiyona geçirilecek parametreler
            
        Returns:
            Aksiyon sonucu
        """
        if not isinstance(tool, ExternalToolProxy):
            logger.error(f"Geçersiz araç türü: {type(tool)}")
            return {"error": "Geçersiz araç türü", "status": "error"}, 400
        
        # Hız sınırlayıcıyı al ve gerekliyse bekle
        rate_limiter = self.rate_limiters.get(tool.name)
        if rate_limiter:
            rate_limiter.wait_if_needed()
        
        try:
            # Aksiyonu çağır
            return tool.call_action(action_name, **kwargs)
        except Exception as e:
            logger.error(f"Dış kaynak aksiyonu çağrılırken hata: {tool.name}.{action_name}, {str(e)}")
            return {"error": str(e), "status": "error"}, 500
    
    def get_capabilities(self, tool: Any) -> List[str]:
        """Dış kaynak aracının yeteneklerini listele
        
        Args:
            tool: ExternalToolProxy nesnesi
            
        Returns:
            Yetenekler listesi
        """
        if not isinstance(tool, ExternalToolProxy):
            logger.error(f"Geçersiz araç türü: {type(tool)}")
            return []
        
        return tool.config.capabilities
    
    def test_connection(self, tool: Any) -> bool:
        """Dış kaynak aracı bağlantısını test et
        
        Args:
            tool: ExternalToolProxy nesnesi
            
        Returns:
            Bağlantı durumu (True/False)
        """
        if not isinstance(tool, ExternalToolProxy):
            logger.error(f"Geçersiz araç türü: {type(tool)}")
            return False
        
        try:
            # Test aksiyonunu çağır veya base_url'e basit bir istek gönder
            if "test" in tool.config.endpoints:
                result = tool.call_action("test")
                return result.get("status") == "success"
            else:
                url = tool.config.base_url
                headers = tool.get_headers()
                
                response = requests.get(url, headers=headers, timeout=tool.config.timeout)
                return response.status_code < 400
        except Exception as e:
            logger.error(f"Bağlantı testi başarısız: {tool.name}, {str(e)}")
            return False

class ExternalToolProxy:
    """Dış kaynak aracı proxy'si"""
    
    def __init__(self, name: str, config: ExternalToolConfig):
        """Dış kaynak proxy'si başlatıcı
        
        Args:
            name: Aracın adı
            config: Araç yapılandırması
        """
        self.name = name
        self.config = config
        self.auth_handler = AuthHandlerFactory.create_auth_handler(config.auth_type)
        self.retry_handler = RetryHandler(max_retries=config.retry_count)
        self.session = requests.Session()
        
        # Varsayılan headers'ları ayarla
        self.session.headers.update({
            "User-Agent": "MCPExternalToolAdapter/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json"
        })
        
        # Konfigürasyondan gelen headers'ları ekle
        if config.headers:
            self.session.headers.update(config.headers)
    
    def get_headers(self) -> Dict[str, str]:
        """İstek headers'larını oluştur
        
        Returns:
            HTTP headers sözlüğü
        """
        # Temel headers'ları al
        headers = dict(self.session.headers)
        
        # Auth headers'larını ekle
        auth_headers = self.auth_handler.get_auth_headers(self.config.auth_info)
        if auth_headers:
            headers.update(auth_headers)
        
        return headers
    
    def call_action(self, action_name: str, **kwargs) -> Any:
        """Dış kaynak aracında bir aksiyonu çağır
        
        Args:
            action_name: Çağrılacak aksiyonun adı
            **kwargs: Aksiyona geçirilecek parametreler
            
        Returns:
            Aksiyon sonucu
        """
        # Endpoint bilgilerini kontrol et
        endpoint_info = self.config.endpoints.get(action_name)
        if not endpoint_info:
            logger.error(f"Aksiyon bulunamadı: {action_name}")
            return {"error": f"Aksiyon bulunamadı: {action_name}", "status": "error"}, 404
        
        # HTTP method, path ve base parametreleri al
        method = endpoint_info.get("method", "GET").upper()
        path = endpoint_info.get("path", "")
        
        # Endpoint parametrelerine varsayılanları ekle
        params = {}
        if "parameters" in endpoint_info:
            for param, param_info in endpoint_info["parameters"].items():
                # Varsayılan değeri kontrol et
                if "default" in param_info and param not in kwargs:
                    params[param] = param_info["default"]
        
        # Kullanıcı parametrelerini ekle
        params.update(kwargs)
        
        # URL oluştur
        url = f"{self.config.base_url.rstrip('/')}/{path.lstrip('/')}"
        
        # Path parametrelerini URL'ye yerleştir
        if "{" in url and "}" in url:
            for param, value in params.items():
                placeholder = f"{{{param}}}"
                if placeholder in url:
                    url = url.replace(placeholder, str(value))
                    # Yerleştirilen parametreleri kaldır
                    params.pop(param, None)
        
        # GraphQL için özel işlem
        is_graphql = endpoint_info.get("graphql", False)
        if is_graphql:
            # GraphQL sorgusunu ve değişkenlerini hazırla
            query = endpoint_info.get("query", "")
            variables = params
            data = {"query": query, "variables": variables}
            
            # GraphQL isteği her zaman POST olmalı
            method = "POST"
            params = {}  # Query params kullanma
        else:
            # Normal REST API için veri
            data = params if method in ["POST", "PUT", "PATCH"] else None
            # GET, DELETE, vb. için query params
            params = params if method in ["GET", "DELETE"] else {}
        
        # Headers
        headers = self.get_headers()
        
        # Retry ile istek gönder
        def make_request():
            response = self.session.request(
                method=method,
                url=url,
                params=params if method in ["GET", "DELETE"] else None,
                json=data if method in ["POST", "PUT", "PATCH"] else None,
                headers=headers,
                timeout=self.config.timeout
            )
            
            # Hata kodu kontrol et
            response.raise_for_status()
            
            # Yanıtı JSON'a dönüştür
            if response.content:
                return response.json()
            return {"status": "success"}
        
        try:
            # Retry ile istek gönder
            result = self.retry_handler.execute_with_retry(make_request)
            
            # Sonucu dönüştür
            if "transform" in endpoint_info:
                transform_type = endpoint_info["transform"].get("type", "")
                if transform_type == "extract":
                    # Belirli alanları çıkar
                    path = endpoint_info["transform"].get("path", "")
                    if path:
                        # Nokta notasyonu ile belirtilen path'i izle
                        parts = path.split(".")
                        data = result
                        for part in parts:
                            if part in data:
                                data = data[part]
                            else:
                                logger.warning(f"Transform path bulunamadı: {path}")
                                break
                        result = data
            
            # Başarılı yanıt
            return {"data": result, "status": "success"}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API isteği başarısız: {str(e)}")
            
            # Token yenileme gerekiyor mu kontrol et
            if hasattr(e, "response") and e.response and e.response.status_code in [401, 403]:
                # Token'ı yenilemeyi dene
                new_auth_info = self.auth_handler.refresh_token(self.config.auth_info)
                if new_auth_info != self.config.auth_info:
                    # Yeni token bilgilerini kaydet
                    self.config.auth_info = new_auth_info
                    logger.info(f"Token yenilendi, isteği tekrar deneniyor: {action_name}")
                    
                    # İsteği tekrar dene
                    return self.call_action(action_name, **kwargs)
            
            # Hata yanıtı
            status_code = e.response.status_code if hasattr(e, "response") and e.response else 500
            return {"error": str(e), "status": "error"}, status_code
            
        except Exception as e:
            logger.error(f"Beklenmeyen hata: {str(e)}")
            return {"error": str(e), "status": "error"}, 500
        
    def get_actions(self) -> List[str]:
        """Dış kaynak aracının desteklediği aksiyonları listele
        
        Returns:
            Aksiyon isimleri listesi
        """
        return list(self.config.endpoints.keys())
    
    def get_action_schema(self, action_name: str) -> Dict[str, Any]:
        """Belirli bir aksiyonun şemasını al
        
        Args:
            action_name: Aksiyon adı
            
        Returns:
            Aksiyon şeması
        """
        endpoint_info = self.config.endpoints.get(action_name, {})
        parameters = endpoint_info.get("parameters", {})
        
        schema = {
            "action": action_name,
            "description": endpoint_info.get("description", ""),
            "method": endpoint_info.get("method", "GET"),
            "path": endpoint_info.get("path", ""),
            "parameters": {}
        }
        
        # Her parametre için şema bilgilerini ekle
        for param, param_info in parameters.items():
            schema["parameters"][param] = {
                "type": param_info.get("type", "string"),
                "description": param_info.get("description", ""),
                "required": param_info.get("required", False),
                "default": param_info.get("default", None) if "default" in param_info else None
            }
        
        return schema