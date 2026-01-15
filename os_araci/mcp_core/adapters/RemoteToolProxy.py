# mcp_core/adapters/remote_tool_proxy.py
import logging
import json
import requests
from typing import Dict, Any, Optional, List, Callable, Union
from os_araci.mcp_core.adapters.adapter_base import (
    ToolAdapterBase,
    AuthHandlerFactory,
    RateLimiter,
    RetryHandler
)

logger = logging.getLogger(__name__)

class RemoteToolProxy(ToolAdapterBase):
    """Uzak MCP sunucularındaki araçlar için proxy sınıfı"""
    
    def __init__(self):
        """Uzak araç proxy'si başlatıcı"""
        super().__init__()
        self.proxies = {}  # name -> MCPRemoteProxy
        self.rate_limiters = {}  # url -> RateLimiter
        self.retry_handler = RetryHandler()
        logger.info("RemoteToolProxy başlatılıyor")
    
    def create_tool(self, name: str, config: Dict[str, Any]) -> Any:
        """Bu metod bu sınıf için geçersizdir, create_proxy kullanılmalıdır"""
        logger.warning("RemoteToolProxy için create_tool değil, create_proxy kullanılmalıdır")
        return None
    
    def create_proxy(self, name: str, remote_url: str, auth_info: Dict = None) -> Any:
        """Uzak MCP sunucusundaki bir araç için proxy oluştur
        
        Args:
            name: Aracın adı
            remote_url: Uzak MCP sunucusunun URL'si
            auth_info: Kimlik doğrulama bilgileri
            
        Returns:
            Oluşturulan MCPRemoteProxy nesnesi
        """
        # Proxy zaten oluşturulmuş mu kontrol et
        proxy_key = f"{remote_url}:{name}"
        if proxy_key in self.proxies:
            logger.info(f"Uzak araç proxy'si zaten mevcut: {proxy_key}")
            return self.proxies[proxy_key]
        
        try:
            # Uzak sunucu ile handshake yap
            if not self._handshake(remote_url, auth_info):
                logger.error(f"Uzak sunucu ile handshake başarısız: {remote_url}")
                return None
            
            # Rate limiter'ı kontrol et veya oluştur
            if remote_url not in self.rate_limiters:
                # Varsayılan olarak dakikada 100 istek
                self.rate_limiters[remote_url] = RateLimiter(100)
            
            # Proxy'yi oluştur
            proxy = MCPRemoteProxy(name, remote_url, auth_info, self.rate_limiters[remote_url])
            
            # Proxy'yi cache'e ekle
            self.proxies[proxy_key] = proxy
            
            logger.info(f"Uzak araç proxy'si oluşturuldu: {name} ({remote_url})")
            return proxy
            
        except Exception as e:
            logger.error(f"Uzak araç proxy'si oluşturulurken hata: {name}, {str(e)}")
            return None
    
    def _handshake(self, remote_url: str, auth_info: Dict = None) -> bool:
        """Uzak MCP sunucusu ile handshake yap
        
        Args:
            remote_url: Uzak MCP sunucusunun URL'si
            auth_info: Kimlik doğrulama bilgileri
            
        Returns:
            Handshake durumu (True/False)
        """
        try:
            url = f"{remote_url.rstrip('/')}/api/handshake"
            
            # Auth headers'ları oluştur
            headers = {
                "User-Agent": "MCPRemoteToolProxy/1.0",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            
            if auth_info:
                auth_type = auth_info.get("type", "bearer")
                auth_handler = AuthHandlerFactory.create_auth_handler(auth_type)
                auth_headers = auth_handler.get_auth_headers(auth_info)
                headers.update(auth_headers)
            
            # Handshake isteği gönder
            response = requests.post(
                url,
                json={"client": "mcp_remote_proxy", "version": "1.0.0"},
                headers=headers,
                timeout=10
            )
            
            # Yanıtı kontrol et
            if response.status_code == 200:
                data = response.json()
                # Sunucu versiyonunu ve uyumluluğu kontrol et
                server_version = data.get("version", "")
                compatible = data.get("compatible", False)
                
                if not compatible:
                    logger.warning(f"Uzak sunucu uyumlu değil: {remote_url}, version: {server_version}")
                    return False
                
                logger.info(f"Uzak sunucu ile handshake başarılı: {remote_url}, version: {server_version}")
                return True
            else:
                logger.error(f"Handshake başarısız, HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Handshake sırasında hata: {str(e)}")
            return False
    
    def list_remote_tools(self, remote_url: str, auth_info: Dict = None) -> List[Dict[str, Any]]:
        """Uzak MCP sunucusundaki tüm araçları listele
        
        Args:
            remote_url: Uzak MCP sunucusunun URL'si
            auth_info: Kimlik doğrulama bilgileri
            
        Returns:
            Araç bilgilerinin listesi
        """
        try:
            # Önce handshake yap
            if not self._handshake(remote_url, auth_info):
                return []
            
            url = f"{remote_url.rstrip('/')}/api/registry/tools"
            
            # Auth headers'ları oluştur
            headers = {
                "User-Agent": "MCPRemoteToolProxy/1.0",
                "Accept": "application/json"
            }
            
            if auth_info:
                auth_type = auth_info.get("type", "bearer")
                auth_handler = AuthHandlerFactory.create_auth_handler(auth_type)
                auth_headers = auth_handler.get_auth_headers(auth_info)
                headers.update(auth_headers)
            
            # İstek gönder
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Araç listesini döndür
            return response.json().get("tools", [])
            
        except Exception as e:
            logger.error(f"Uzak araçları listelerken hata: {str(e)}")
            return []
    
    def get_tool_metadata(self, remote_url: str, tool_name: str, auth_info: Dict = None) -> Dict[str, Any]:
        """Uzak MCP sunucusundaki bir aracın metadata bilgilerini al
        
        Args:
            remote_url: Uzak MCP sunucusunun URL'si
            tool_name: Aracın adı
            auth_info: Kimlik doğrulama bilgileri
            
        Returns:
            Aracın metadata bilgileri
        """
        try:
            url = f"{remote_url.rstrip('/')}/api/registry/tool/{tool_name}"
            
            # Auth headers'ları oluştur
            headers = {
                "User-Agent": "MCPRemoteToolProxy/1.0",
                "Accept": "application/json"
            }
            
            if auth_info:
                auth_type = auth_info.get("type", "bearer")
                auth_handler = AuthHandlerFactory.create_auth_handler(auth_type)
                auth_headers = auth_handler.get_auth_headers(auth_info)
                headers.update(auth_headers)
            
            # İstek gönder
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Metadata'yı döndür
            return response.json()
            
        except Exception as e:
            logger.error(f"Araç metadata'sı alınırken hata: {tool_name}, {str(e)}")
            return {}
    
    def call_action(self, tool: Any, action_name: str, **kwargs) -> Any:
        """Uzak araç üzerinde bir aksiyonu çağır
        
        Args:
            tool: MCPRemoteProxy nesnesi
            action_name: Çağrılacak aksiyonun adı
            **kwargs: Aksiyona geçirilecek parametreler
            
        Returns:
            Aksiyon sonucu
        """
        if not isinstance(tool, MCPRemoteProxy):
            logger.error(f"Geçersiz araç türü: {type(tool)}")
            return {"error": "Geçersiz araç türü", "status": "error"}, 400
        
        try:
            # Aksiyonu çağır
            return tool.call_action(action_name, **kwargs)
        except Exception as e:
            logger.error(f"Uzak aksiyon çağrılırken hata: {tool.name}.{action_name}, {str(e)}")
            return {"error": str(e), "status": "error"}, 500
    
    def get_capabilities(self, tool: Any) -> List[str]:
        """Uzak aracın yeteneklerini listele
        
        Args:
            tool: MCPRemoteProxy nesnesi
            
        Returns:
            Yetenekler listesi
        """
        if not isinstance(tool, MCPRemoteProxy):
            logger.error(f"Geçersiz araç türü: {type(tool)}")
            return []
        
        try:
            # Yetenekleri çek
            return tool.get_capabilities()
        except Exception as e:
            logger.error(f"Yetenekler alınırken hata: {tool.name}, {str(e)}")
            return []
    
    def ping(self, remote_url: str, auth_info: Dict = None) -> bool:
        """Uzak MCP sunucusunu ping'le
        
        Args:
            remote_url: Uzak MCP sunucusunun URL'si
            auth_info: Kimlik doğrulama bilgileri
            
        Returns:
            Ping durumu (True/False)
        """
        try:
            url = f"{remote_url.rstrip('/')}/api/ping"
            
            # Auth headers'ları oluştur
            headers = {
                "User-Agent": "MCPRemoteToolProxy/1.0",
                "Accept": "application/json"
            }
            
            if auth_info:
                auth_type = auth_info.get("type", "bearer")
                auth_handler = AuthHandlerFactory.create_auth_handler(auth_type)
                auth_headers = auth_handler.get_auth_headers(auth_info)
                headers.update(auth_headers)
            
            # İstek gönder
            response = requests.get(url, headers=headers, timeout=5)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Ping başarısız: {str(e)}")
            return False
    
    def get_remote_schema(self, remote_url: str, auth_info: Dict = None) -> Dict[str, Any]:
        """Uzak MCP sunucusunun API şemasını al
        
        Args:
            remote_url: Uzak MCP sunucusunun URL'si
            auth_info: Kimlik doğrulama bilgileri
            
        Returns:
            API şeması
        """
        try:
            url = f"{remote_url.rstrip('/')}/api/schema"
            
            # Auth headers'ları oluştur
            headers = {
                "User-Agent": "MCPRemoteToolProxy/1.0",
                "Accept": "application/json"
            }
            
            if auth_info:
                auth_type = auth_info.get("type", "bearer")
                auth_handler = AuthHandlerFactory.create_auth_handler(auth_type)
                auth_headers = auth_handler.get_auth_headers(auth_info)
                headers.update(auth_headers)
            
            # İstek gönder
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Şemayı döndür
            return response.json()
            
        except Exception as e:
            logger.error(f"API şeması alınırken hata: {str(e)}")
            return {}


class MCPRemoteProxy:
    """Uzak MCP aracını temsil eden proxy sınıfı"""
    
    def __init__(self, name: str, remote_url: str, auth_info: Dict = None, rate_limiter: RateLimiter = None):
        """Uzak MCP aracı proxy'si başlatıcı
        
        Args:
            name: Aracın adı
            remote_url: Uzak MCP sunucusunun URL'si
            auth_info: Kimlik doğrulama bilgileri
            rate_limiter: İstek hızı sınırlayıcı
        """
        self.name = name
        self.remote_url = remote_url.rstrip('/')
        self.auth_info = auth_info or {}
        self.rate_limiter = rate_limiter or RateLimiter()
        self.retry_handler = RetryHandler()
        self.session = requests.Session()
        
        # Varsayılan headers'ları ayarla
        self.session.headers.update({
            "User-Agent": "MCPRemoteToolProxy/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json"
        })
        
        # Metadata ve capabilities önbelleği
        self._metadata_cache = None
        self._capabilities_cache = None
        self._actions_cache = None
    
    def get_headers(self) -> Dict[str, str]:
        """İstek headers'larını oluştur
        
        Returns:
            HTTP headers sözlüğü
        """
        # Temel headers'ları al
        headers = dict(self.session.headers)
        
        # Auth headers'larını ekle
        if self.auth_info:
            auth_type = self.auth_info.get("type", "bearer")
            auth_handler = AuthHandlerFactory.create_auth_handler(auth_type)
            auth_headers = auth_handler.get_auth_headers(self.auth_info)
            if auth_headers:
                headers.update(auth_headers)
        
        return headers
    
    def call_action(self, action_name: str, **kwargs) -> Any:
        """Uzak araç üzerinde bir aksiyonu çağır
        
        Args:
            action_name: Çağrılacak aksiyonun adı
            **kwargs: Aksiyona geçirilecek parametreler
            
        Returns:
            Aksiyon sonucu
        """
        # Hız sınırlayıcıyı kontrol et
        if self.rate_limiter:
            self.rate_limiter.wait_if_needed()
        
        # İstek URL'sini oluştur
        url = f"{self.remote_url}/api/registry/call/{self.name}/{action_name}"
        
        # Headers
        headers = self.get_headers()
        
        # İstek gövdesi
        payload = {"params": kwargs}
        
        # Retry ile istek gönder
        def make_request():
            response = self.session.post(
                url=url,
                json=payload,
                headers=headers,
                timeout=30
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
            
            # Sonucu döndür
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API isteği başarısız: {str(e)}")
            
            # Token yenileme gerekiyor mu kontrol et
            if hasattr(e, "response") and e.response and e.response.status_code in [401, 403]:
                # Token'ı yenilemeyi dene
                if self.auth_info:
                    auth_type = self.auth_info.get("type", "bearer")
                    auth_handler = AuthHandlerFactory.create_auth_handler(auth_type)
                    new_auth_info = auth_handler.refresh_token(self.auth_info)
                    
                    if new_auth_info != self.auth_info:
                        # Yeni token bilgilerini kaydet
                        self.auth_info = new_auth_info
                        logger.info(f"Token yenilendi, isteği tekrar deneniyor: {action_name}")
                        
                        # İsteği tekrar dene
                        return self.call_action(action_name, **kwargs)
            
            # Hata yanıtı
            status_code = e.response.status_code if hasattr(e, "response") and e.response else 500
            return {"error": str(e), "status": "error"}, status_code
            
        except Exception as e:
            logger.error(f"Beklenmeyen hata: {str(e)}")
            return {"error": str(e), "status": "error"}, 500
    
    def get_metadata(self) -> Dict[str, Any]:
        """Uzak aracın metadata bilgilerini getir
        
        Returns:
            Metadata bilgileri
        """
        # Önbellekten kontrol et
        if self._metadata_cache:
            return self._metadata_cache
        
        try:
            url = f"{self.remote_url}/api/registry/tool/{self.name}"
            
            # Headers
            headers = self.get_headers()
            
            # İstek gönder
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Metadata'yı önbelleğe al ve döndür
            self._metadata_cache = response.json()
            return self._metadata_cache
            
        except Exception as e:
            logger.error(f"Metadata alınırken hata: {str(e)}")
            return {}
    
    def get_capabilities(self) -> List[str]:
        """Uzak aracın yeteneklerini getir
        
        Returns:
            Yetenekler listesi
        """
        # Önbellekten kontrol et
        if self._capabilities_cache:
            return self._capabilities_cache
        
        try:
            # Metadata'dan yetenekleri al
            metadata = self.get_metadata()
            capabilities = metadata.get("capabilities", [])
            
            # Yetenekleri önbelleğe al ve döndür
            self._capabilities_cache = capabilities
            return capabilities
            
        except Exception as e:
            logger.error(f"Yetenekler alınırken hata: {str(e)}")
            return []
    
    def get_actions(self) -> List[str]:
        """Uzak aracın desteklediği aksiyonları getir
        
        Returns:
            Aksiyon isimleri listesi
        """
        # Önbellekten kontrol et
        if self._actions_cache:
            return self._actions_cache
        
        try:
            url = f"{self.remote_url}/api/registry/tool/{self.name}/actions"
            
            # Headers
            headers = self.get_headers()
            
            # İstek gönder
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Aksiyonları önbelleğe al ve döndür
            self._actions_cache = response.json().get("actions", [])
            return self._actions_cache
            
        except Exception as e:
            logger.error(f"Aksiyonlar alınırken hata: {str(e)}")
            return []
    
    def get_action_schema(self, action_name: str) -> Dict[str, Any]:
        """Belirli bir aksiyonun şemasını al
        
        Args:
            action_name: Aksiyon adı
            
        Returns:
            Aksiyon şeması
        """
        try:
            url = f"{self.remote_url}/api/registry/tool/{self.name}/action/{action_name}"
            
            # Headers
            headers = self.get_headers()
            
            # İstek gönder
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Aksiyon şemasını döndür
            return response.json()
            
        except Exception as e:
            logger.error(f"Aksiyon şeması alınırken hata: {action_name}, {str(e)}")
            return {}
    
    def check_health(self) -> bool:
        """Uzak aracın sağlık durumunu kontrol et
        
        Returns:
            Sağlık durumu (True/False)
        """
        try:
            url = f"{self.remote_url}/api/registry/tool/{self.name}/health"
            
            # Headers
            headers = self.get_headers()
            
            # İstek gönder
            response = requests.get(url, headers=headers, timeout=5)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Sağlık kontrolü başarısız: {str(e)}")
            return False
    
    def streaming_call(self, action_name: str, callback: Callable[[str], None], **kwargs) -> bool:
        """Streaming API çağrısı yap (WebSocket üzerinden)
        
        Args:
            action_name: Çağrılacak aksiyonun adı
            callback: Her chunk için çağrılacak callback fonksiyonu
            **kwargs: Aksiyona geçirilecek parametreler
            
        Returns:
            İşlem durumu (True/False)
        """
        try:
            import websocket
            import json
            import uuid
            
            # WebSocket URL'sini oluştur
            ws_protocol = "wss" if self.remote_url.startswith("https") else "ws"
            base_url = self.remote_url.replace("https://", "").replace("http://", "")
            ws_url = f"{ws_protocol}://{base_url}/api/ws/registry/stream/{self.name}/{action_name}"
            
            # Mesaj ID'si oluştur
            message_id = str(uuid.uuid4())
            
            # Bağlantı açıldığında
            def on_open(ws):
                # Parametreleri gönder
                ws.send(json.dumps({
                    "id": message_id,
                    "params": kwargs
                }))
            
            # Mesaj alındığında
            def on_message(ws, message):
                try:
                    data = json.loads(message)
                    # Veri türünü kontrol et
                    if data.get("type") == "chunk":
                        # Chunk'ı callback fonksiyonuna gönder
                        content = data.get("content", "")
                        if content:
                            callback(content)
                    elif data.get("type") == "end":
                        # Streaming bitti, bağlantıyı kapat
                        ws.close()
                    elif data.get("type") == "error":
                        # Hata durumu
                        error = data.get("error", "Bilinmeyen hata")
                        logger.error(f"Streaming hatası: {error}")
                        callback(f"HATA: {error}")
                        ws.close()
                except Exception as e:
                    logger.error(f"Mesaj işlenirken hata: {str(e)}")
                    ws.close()
            
            # Hata durumunda
            def on_error(ws, error):
                logger.error(f"WebSocket hatası: {str(error)}")
                callback(f"BAĞLANTI HATASI: {str(error)}")
            
            # Bağlantı kapandığında
            def on_close(ws, close_status_code, close_msg):
                logger.info(f"WebSocket bağlantısı kapandı: {close_status_code} {close_msg}")
            
            # Headers
            headers = self.get_headers()
            
            # WebSocket bağlantısı kur
            ws = websocket.WebSocketApp(
                ws_url,
                header=list(f"{k}: {v}" for k, v in headers.items()),
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            
            # Bağlantıyı başlat (bloke etmeden)
            import threading
            wst = threading.Thread(target=ws.run_forever)
            wst.daemon = True
            wst.start()
            
            return True
            
        except Exception as e:
            logger.error(f"Streaming başlatılamadı: {str(e)}")
            callback(f"STREAMING BAŞLATILAMADI: {str(e)}")
            return False