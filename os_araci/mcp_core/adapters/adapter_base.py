# mcp_core/adapters/adapter_base.py
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable

logger = logging.getLogger(__name__)

class ToolAdapterBase(ABC):
    """Farklı araç adaptörleri için temel sınıf"""

    def __init__(self):
        """Adaptör temel sınıfı başlatıcı"""
        self.adapters = {}  # Adaptör önbelleği
        logger.info(f"{self.__class__.__name__} adaptörü başlatılıyor")

    @abstractmethod
    def create_tool(self, name: str, config: Dict[str, Any]) -> Any:
        """Yapılandırmadan bir araç örneği oluştur
        
        Args:
            name: Aracın adı
            config: Araç yapılandırma bilgileri
            
        Returns:
            Oluşturulan araç örneği
        """
        pass
    
    @abstractmethod
    def call_action(self, tool: Any, action_name: str, **kwargs) -> Any:
        """Araç üzerinde bir aksiyonu çağır
        
        Args:
            tool: Araç örneği
            action_name: Çağrılacak aksiyonun adı
            **kwargs: Aksiyona geçirilecek parametreler
            
        Returns:
            Aksiyon sonucu
        """
        pass
    
    @abstractmethod
    def get_capabilities(self, tool: Any) -> List[str]:
        """Aracın yeteneklerini (capabilities) listele
        
        Args:
            tool: Araç örneği
            
        Returns:
            Araç yeteneklerinin listesi
        """
        pass

class AuthHandler(ABC):
    """Farklı kimlik doğrulama yöntemleri için temel sınıf"""
    
    @abstractmethod
    def get_auth_headers(self, auth_info: Dict[str, Any]) -> Dict[str, str]:
        """Kimlik doğrulama bilgilerinden HTTP başlıkları oluştur
        
        Args:
            auth_info: Kimlik doğrulama bilgileri
            
        Returns:
            HTTP başlıkları sözlüğü
        """
        pass
    
    @abstractmethod
    def refresh_token(self, auth_info: Dict[str, Any]) -> Dict[str, Any]:
        """Kimlik doğrulama token'ını yenile
        
        Args:
            auth_info: Mevcut kimlik doğrulama bilgileri
            
        Returns:
            Yenilenmiş kimlik doğrulama bilgileri
        """
        pass

class BearerAuthHandler(AuthHandler):
    """Bearer token kimlik doğrulama işleyicisi"""
    
    def get_auth_headers(self, auth_info: Dict[str, Any]) -> Dict[str, str]:
        """Bearer token için HTTP başlıkları oluştur"""
        token = auth_info.get("token")
        if not token:
            logger.warning("Bearer token bulunamadı")
            return {}
        
        return {"Authorization": f"Bearer {token}"}
    
    def refresh_token(self, auth_info: Dict[str, Any]) -> Dict[str, Any]:
        """Bearer token'ı yenile"""
        refresh_token = auth_info.get("refresh_token")
        if not refresh_token:
            logger.warning("Yenileme token'ı bulunamadı")
            return auth_info
        
        refresh_url = auth_info.get("refresh_url")
        client_id = auth_info.get("client_id")
        client_secret = auth_info.get("client_secret")
        
        if not refresh_url or not client_id:
            logger.warning("Token yenileme için gerekli bilgiler eksik")
            return auth_info
        
        try:
            import requests
            data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id
            }
            
            if client_secret:
                data["client_secret"] = client_secret
            
            response = requests.post(refresh_url, data=data)
            response.raise_for_status()
            
            response_data = response.json()
            new_token = response_data.get("access_token")
            new_refresh_token = response_data.get("refresh_token", refresh_token)
            
            if new_token:
                # Yeni token bilgilerini döndür
                new_auth_info = auth_info.copy()
                new_auth_info["token"] = new_token
                new_auth_info["refresh_token"] = new_refresh_token
                
                expires_in = response_data.get("expires_in")
                if expires_in:
                    import time
                    new_auth_info["expiry_time"] = time.time() + int(expires_in)
                
                return new_auth_info
            
        except Exception as e:
            logger.error(f"Token yenileme hatası: {str(e)}")
        
        return auth_info

class BasicAuthHandler(AuthHandler):
    """Basic Auth kimlik doğrulama işleyicisi"""
    
    def get_auth_headers(self, auth_info: Dict[str, Any]) -> Dict[str, str]:
        """Basic Auth için HTTP başlıkları oluştur"""
        username = auth_info.get("username")
        password = auth_info.get("password")
        
        if not username or not password:
            logger.warning("Basic Auth için kullanıcı adı veya şifre bulunamadı")
            return {}
        
        import base64
        auth_string = f"{username}:{password}"
        encoded_auth = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
        
        return {"Authorization": f"Basic {encoded_auth}"}
    
    def refresh_token(self, auth_info: Dict[str, Any]) -> Dict[str, Any]:
        """Basic Auth için token yenileme (gerekli değil)"""
        # Basic Auth için token yenileme gerekmez
        return auth_info

class ApiKeyAuthHandler(AuthHandler):
    """API Key kimlik doğrulama işleyicisi"""
    
    def get_auth_headers(self, auth_info: Dict[str, Any]) -> Dict[str, str]:
        """API Key için HTTP başlıkları oluştur"""
        api_key = auth_info.get("api_key")
        header_name = auth_info.get("header_name", "X-API-Key")
        
        if not api_key:
            logger.warning("API Key bulunamadı")
            return {}
        
        return {header_name: api_key}
    
    def refresh_token(self, auth_info: Dict[str, Any]) -> Dict[str, Any]:
        """API Key için token yenileme (gerekli değil)"""
        # API Key için token yenileme gerekmez
        return auth_info

class NoAuthHandler(AuthHandler):
    """Kimlik doğrulama gerektirmeyen durum işleyicisi"""
    
    def get_auth_headers(self, auth_info: Dict[str, Any]) -> Dict[str, str]:
        """Kimliksiz durum için boş başlıklar"""
        return {}
    
    def refresh_token(self, auth_info: Dict[str, Any]) -> Dict[str, Any]:
        """Kimliksiz durum için token yenileme (gerekli değil)"""
        return auth_info

class AuthHandlerFactory:
    """Kimlik doğrulama işleyicisi fabrikası"""
    
    @staticmethod
    def create_auth_handler(auth_type: str) -> AuthHandler:
        """Auth tipine göre uygun kimlik doğrulama işleyicisi oluştur
        
        Args:
            auth_type: Kimlik doğrulama tipi (bearer, basic, apikey, none)
            
        Returns:
            Kimlik doğrulama işleyicisi
        """
        auth_type = auth_type.lower()
        
        if auth_type == "bearer":
            return BearerAuthHandler()
        elif auth_type == "basic":
            return BasicAuthHandler()
        elif auth_type == "apikey":
            return ApiKeyAuthHandler()
        else:
            return NoAuthHandler()

class RateLimiter:
    """API isteklerini hız sınırlama için yardımcı sınıf"""
    
    def __init__(self, requests_per_minute: int = 60):
        """Hız sınırlayıcı başlatıcı
        
        Args:
            requests_per_minute: İzin verilen dakikalık istek sayısı
        """
        self.requests_per_minute = requests_per_minute
        self.request_times = []
    
    def wait_if_needed(self):
        """Gerekliyse istekleri sınırlamak için bekle"""
        import time
        current_time = time.time()
        
        # 1 dakikadan eski istekleri kaldır
        one_minute_ago = current_time - 60
        self.request_times = [t for t in self.request_times if t > one_minute_ago]
        
        # İstek sayısını kontrol et ve gerekirse bekle
        if len(self.request_times) >= self.requests_per_minute:
            # En eski isteğin zamanını al
            oldest_request = min(self.request_times)
            # Bekleme süresi: en eski istek + 60s - şu an
            wait_time = oldest_request + 60 - current_time
            
            if wait_time > 0:
                logger.info(f"Hız sınırlaması nedeniyle {wait_time:.2f} saniye bekleniyor")
                time.sleep(wait_time)
        
        # Yeni istek zamanını kaydet
        self.request_times.append(time.time())

class RetryHandler:
    """API isteklerini yeniden deneme stratejileri için yardımcı sınıf"""
    
    def __init__(self, max_retries: int = 3, initial_backoff: float = 1.0, backoff_factor: float = 2.0):
        """Yeniden deneme işleyicisi başlatıcı
        
        Args:
            max_retries: Maksimum yeniden deneme sayısı
            initial_backoff: İlk yeniden deneme için bekleme süresi (saniye)
            backoff_factor: Sonraki denemeler için bekleyerek arttırma faktörü
        """
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.backoff_factor = backoff_factor
    
    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Belirli bir fonksiyonu yeniden deneme stratejisi ile çalıştır
        
        Args:
            func: Çalıştırılacak fonksiyon
            *args, **kwargs: Fonksiyona geçirilecek parametreler
            
        Returns:
            Fonksiyon sonucu
            
        Raises:
            Exception: Tüm denemeler başarısız olursa
        """
        import time
        import random
        
        last_exception = None
        backoff = self.initial_backoff
        
        # Yeniden denemeleri yap
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                # Son denemeyi geçtiyse hatayı yükselt
                if attempt >= self.max_retries:
                    raise
                
                # Rastgele bir jitter ile exponential backoff uygula
                jitter = random.uniform(0.8, 1.2)
                wait_time = backoff * jitter
                
                logger.warning(f"Deneme {attempt+1}/{self.max_retries} başarısız. {wait_time:.2f} saniye sonra tekrar denenecek. Hata: {str(e)}")
                time.sleep(wait_time)
                
                # Backoff süresini arttır
                backoff *= self.backoff_factor