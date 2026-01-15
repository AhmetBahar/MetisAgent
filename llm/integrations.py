# llm/integrations.py
import os
import json
import requests
import time
import logging
import subprocess
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv

# .env dosyasından API anahtarlarını yükle
load_dotenv()

# Logger yapılandırması
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LLMProvider(ABC):
    """LLM entegrasyonları için temel sınıf"""
    
    @abstractmethod
    def generate_tasks(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """LLM'den görev listesi oluşturma"""
        pass
    
    @abstractmethod
    def generate_text(self, prompt: str, **kwargs) -> str:
        """LLM'den metin oluşturma"""
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[Dict[str, str]]:
        """Kullanılabilir modelleri getir"""
        pass

class OpenAIProvider(LLMProvider):
    """OpenAI API kullanarak LLM entegrasyonu"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OpenAI API anahtarı bulunamadı.")
        
        self.base_url = "https://api.openai.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def generate_tasks(self, prompt: str, model: str = "gpt-3.5-turbo", **kwargs) -> Dict[str, Any]:
        """OpenAI API ile görev listesi oluştur"""
        system_prompt = """
        Kullanıcı görevinin amacını sana anlatacak. Sen bu görevi yerine getirmek için 
        gerekli olan komutları, kod değişikliklerini ve dosya işlemlerini adım adım listeleyeceksin.
        Çıktını aşağıdaki JSON formatında olmalı:
        
        {
            "tasks": [
                {
                    "name": "Görev adı",
                    "description": "Görev açıklaması",
                    "command": "Çalıştırılacak komut veya yapılacak değişiklik",
                    "type": "command | code_change | file_operation",
                    "dependencies": [0, 1], // Bağımlı olduğu görevlerin indeksleri
                    "estimatedTime": "10s"
                }
            ]
        }
        
        Sadece JSON çıktısı ver, açıklama yapma.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.2)
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            result = response.json()
            
            # JSON yanıtı çıkart
            content = result["choices"][0]["message"]["content"]
            
            # Kodu JSON içinden çıkart
            try:
                # Bazen LLM JSON kodunu ``` içine koyabilir
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    json_str = content.split("```")[1].split("```")[0].strip()
                else:
                    json_str = content.strip()
                
                tasks_data = json.loads(json_str)
                return tasks_data
            except json.JSONDecodeError:
                logger.error(f"JSON ayrıştırma hatası. İçerik: {content}")
                return {"tasks": []}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenAI API hatası: {str(e)}")
            raise Exception(f"OpenAI API isteği başarısız: {str(e)}")
    
    def generate_text(self, prompt: str, model: str = "gpt-3.5-turbo", **kwargs) -> str:
        """OpenAI API ile metin oluştur"""
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7)
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            result = response.json()
            
            return result["choices"][0]["message"]["content"]
            
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenAI API hatası: {str(e)}")
            raise Exception(f"OpenAI API isteği başarısız: {str(e)}")
    
    def get_available_models(self) -> List[Dict[str, str]]:
        """Kullanılabilir OpenAI modellerini getir"""
        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers=self.headers
            )
            response.raise_for_status()
            result = response.json()
            
            # Sadece GPT modelleri filtrele
            gpt_models = [
                {"id": model["id"], "name": model["id"]}
                for model in result["data"]
                if "gpt" in model["id"].lower()
            ]
            
            return gpt_models
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenAI API modelleri alınamadı: {str(e)}")
            # Varsayılan modeller
            return [
                {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo"},
                {"id": "gpt-4", "name": "GPT-4"},
                {"id": "gpt-4-1106-preview", "name": "GPT-4 Turbo"}
            ]

class WebScraperLLM(LLMProvider):
    """Web scraper kullanarak LLM entegrasyonu"""
    
    def __init__(self, service_type: str = "chatgpt"):
        self.service_type = service_type
        self.driver = None
        self._setup_driver()
    
    def _setup_driver(self):
        """Selenium webdriver'ı yapılandır"""
        try:
            options = Options()
            options.add_argument("--headless")  # Başsız mod
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            
            self.driver = webdriver.Chrome(options=options)
            logger.info(f"Web scraper başlatıldı: {self.service_type}")
        except Exception as e:
            logger.error(f"Web driver başlatılamadı: {str(e)}")
            raise Exception(f"Web scraper başlatılamadı: {str(e)}")
    
    def _login_to_chatgpt(self):
        """ChatGPT'ye giriş yap (sadece örnek)"""
        # Not: Bu işlev gerçek uygulamada tamamlanmalıdır
        # Bu bir taslaktır ve kullanıcı tarafından yapılandırılmalıdır
        pass
    
    def generate_tasks(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Web scraper ile görev listesi oluştur"""
        if self.service_type == "chatgpt":
            try:
                # ChatGPT sayfasına git
                self.driver.get("https://chat.openai.com/")
                time.sleep(2)
                
                # Giriş yapmış olduğunuzu varsayalım
                # Gerçek uygulamada _login_to_chatgpt() çağrılmalı
                
                # Prompt'u gir
                task_prompt = f"""
                {prompt}
                
                Lütfen bu görevi yerine getirmek için gerekli komutları JSON formatında listele:
                ```json
                {{
                    "tasks": [
                        {{
                            "name": "Görev adı",
                            "description": "Görev açıklaması",
                            "command": "Çalıştırılacak komut",
                            "type": "command",
                            "dependencies": [],
                            "estimatedTime": "10s"
                        }}
                    ]
                }}
                ```
                Sadece JSON formatında yanıt ver.
                """
                
                # Metin girişi alanını bul ve prompt'u gönder
                input_box = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[tabindex='0']"))
                )
                input_box.clear()
                input_box.send_keys(task_prompt)
                input_box.submit()
                
                # Yanıt için bekle
                response_element = WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".markdown.prose"))
                )
                
                response_text = response_element.text
                
                # JSON yanıtı ayrıştır
                if "```json" in response_text:
                    json_str = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    json_str = response_text.split("```")[1].split("```")[0].strip()
                else:
                    json_str = response_text.strip()
                
                try:
                    tasks_data = json.loads(json_str)
                    return tasks_data
                except json.JSONDecodeError:
                    logger.error(f"JSON ayrıştırma hatası. İçerik: {response_text}")
                    return {"tasks": []}
                
            except Exception as e:
                logger.error(f"Web scraper hatası: {str(e)}")
                return {"tasks": []}
        else:
            logger.error(f"Desteklenmeyen servis türü: {self.service_type}")
            return {"tasks": []}
    
    def generate_text(self, prompt: str, **kwargs) -> str:
        """Web scraper ile metin oluştur"""
        if self.service_type == "chatgpt":
            try:
                # ChatGPT sayfasına git (eğer zaten sayfada değilsek)
                if "chat.openai.com" not in self.driver.current_url:
                    self.driver.get("https://chat.openai.com/")
                    time.sleep(2)
                
                # Prompt'u gir
                input_box = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[tabindex='0']"))
                )
                input_box.clear()
                input_box.send_keys(prompt)
                input_box.submit()
                
                # Yanıt için bekle
                response_element = WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".markdown.prose"))
                )
                
                return response_element.text
                
            except Exception as e:
                logger.error(f"Web scraper hatası: {str(e)}")
                return f"Web scraper hatası: {str(e)}"
        else:
            logger.error(f"Desteklenmeyen servis türü: {self.service_type}")
            return "Desteklenmeyen servis türü"
    
    def get_available_models(self) -> List[Dict[str, str]]:
        """Web scraper ile kullanılabilir modelleri getir"""
        if self.service_type == "chatgpt":
            # Web arayüzünde kullanılabilir modeller
            return [
                {"id": "default", "name": "ChatGPT (Web)"},
                {"id": "gpt-4", "name": "GPT-4 (Web)"}
            ]
        else:
            return [{"id": "default", "name": f"{self.service_type} (Web)"}]
    
    def __del__(self):
        """Temizleme işlevi"""
        if self.driver:
            self.driver.quit()
            logger.info("Web driver kapatıldı")

class LocalLLMProvider(LLMProvider):
    """Ollama veya LM Studio gibi yerel LLM'leri kullanarak entegrasyon"""
    
    def __init__(self, provider: str = "ollama", base_url: Optional[str] = None):
        """
        provider: "ollama" veya "lmstudio"
        base_url: API erişim noktası URL'i
        """
        self.provider = provider.lower()
        
        # Varsayılan URL'leri ayarla
        if self.provider == "ollama":
            self.base_url = base_url or "http://localhost:11434/api"
        elif self.provider == "lmstudio":
            self.base_url = base_url or "http://localhost:1234/v1"
        else:
            logger.error(f"Desteklenmeyen yerel LLM sağlayıcısı: {provider}")
            raise ValueError(f"Desteklenmeyen yerel LLM sağlayıcısı: {provider}")
    
    def generate_tasks(self, prompt: str, model: str = "llama2", **kwargs) -> Dict[str, Any]:
        """Yerel LLM ile görev listesi oluştur"""
        system_prompt = """
        Kullanıcı görevinin amacını sana anlatacak. Sen bu görevi yerine getirmek için 
        gerekli olan komutları, kod değişikliklerini ve dosya işlemlerini adım adım listeleyeceksin.
        Çıktını aşağıdaki JSON formatında olmalı:
        
        {
            "tasks": [
                {
                    "name": "Görev adı",
                    "description": "Görev açıklaması",
                    "command": "Çalıştırılacak komut veya yapılacak değişiklik",
                    "type": "command | code_change | file_operation",
                    "dependencies": [0, 1], // Bağımlı olduğu görevlerin indeksleri
                    "estimatedTime": "10s"
                }
            ]
        }
        
        Sadece JSON çıktısı ver, açıklama yapma.
        """
        
        try:
            if self.provider == "ollama":
                data = {
                    "model": model,
                    "prompt": system_prompt + "\n\n" + prompt,
                    "stream": False
                }
                
                response = requests.post(
                    f"{self.base_url}/generate",
                    json=data
                )
                response.raise_for_status()
                result = response.json()
                
                # Ollama yanıtı
                content = result["response"]
                
            elif self.provider == "lmstudio":
                # LM Studio, OpenAI API formatını kullanır
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ]
                
                data = {
                    "model": model,
                    "messages": messages,
                    "temperature": kwargs.get("temperature", 0.2)
                }
                
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    json=data
                )
                response.raise_for_status()
                result = response.json()
                
                # LM Studio yanıtı
                content = result["choices"][0]["message"]["content"]
            
            # JSON yanıtı çıkart
            try:
                # Bazen LLM JSON kodunu ``` içine koyabilir
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    json_str = content.split("```")[1].split("```")[0].strip()
                else:
                    json_str = content.strip()
                
                tasks_data = json.loads(json_str)
                return tasks_data
            except json.JSONDecodeError:
                logger.error(f"JSON ayrıştırma hatası. İçerik: {content}")
                return {"tasks": []}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Yerel LLM API hatası: {str(e)}")
            raise Exception(f"Yerel LLM API isteği başarısız: {str(e)}")
    
    def generate_text(self, prompt: str, model: str = "llama2", **kwargs) -> str:
        """Yerel LLM ile metin oluştur"""
        try:
            if self.provider == "ollama":
                data = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                }
                
                response = requests.post(
                    f"{self.base_url}/generate",
                    json=data
                )
                response.raise_for_status()
                result = response.json()
                
                # Ollama yanıtı
                return result["response"]
                
            elif self.provider == "lmstudio":
                # LM Studio, OpenAI API formatını kullanır
                messages = [
                    {"role": "user", "content": prompt}
                ]
                
                data = {
                    "model": model,
                    "messages": messages,
                    "temperature": kwargs.get("temperature", 0.7)
                }
                
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    json=data
                )
                response.raise_for_status()
                result = response.json()
                
                # LM Studio yanıtı
                return result["choices"][0]["message"]["content"]
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Yerel LLM API hatası: {str(e)}")
            raise Exception(f"Yerel LLM API isteği başarısız: {str(e)}")
    
    def get_available_models(self) -> List[Dict[str, str]]:
        """Yerel LLM'de kullanılabilir modelleri getir"""
        try:
            if self.provider == "ollama":
                response = requests.get(f"{self.base_url}/tags")
                response.raise_for_status()
                result = response.json()
                
                return [
                    {"id": model["name"], "name": model["name"]}
                    for model in result["models"]
                ]
                
            elif self.provider == "lmstudio":
                # LM Studio modellerini doğrudan alma API'si yok
                # Kullanıcı yapılandırmasından gelmeli
                return [
                    {"id": "default", "name": "LM Studio Default"},
                    {"id": "llama2", "name": "Llama 2"},
                    {"id": "mistral", "name": "Mistral"}
                ]
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Yerel LLM model listesi alınamadı: {str(e)}")
            
            # Varsayılan modelleri döndür
            if self.provider == "ollama":
                return [
                    {"id": "llama2", "name": "Llama 2"},
                    {"id": "mistral", "name": "Mistral"},
                    {"id": "codellama", "name": "Code Llama"}
                ]
            elif self.provider == "lmstudio":
                return [
                    {"id": "default", "name": "LM Studio Default"}
                ]

class LLMFactory:
    """LLM sağlayıcıları oluşturma factory sınıfı"""
    
    @staticmethod
    def create_provider(provider_type: str, **kwargs) -> LLMProvider:
        """
        LLM sağlayıcısı oluştur
        
        provider_type: "openai", "webscraper", "ollama", "lmstudio"
        kwargs: Sağlayıcıya özel parametreler
        """
        if provider_type == "openai":
            return OpenAIProvider(api_key=kwargs.get("api_key"))
        
        elif provider_type == "webscraper":
            return WebScraperLLM(service_type=kwargs.get("service_type", "chatgpt"))
        
        elif provider_type == "ollama":
            return LocalLLMProvider(provider="ollama", base_url=kwargs.get("base_url"))
        
        elif provider_type == "lmstudio":
            return LocalLLMProvider(provider="lmstudio", base_url=kwargs.get("base_url"))
        
        else:
            logger.error(f"Bilinmeyen LLM sağlayıcı türü: {provider_type}")
            raise ValueError(f"Bilinmeyen LLM sağlayıcı türü: {provider_type}")

# Desteklenen sağlayıcılar
SUPPORTED_PROVIDERS = [
    {"id": "openai", "name": "OpenAI API", "needs_key": True, "needs_setup": False},
    {"id": "webscraper", "name": "Web Scraper (ChatGPT)", "needs_key": False, "needs_setup": True},
    {"id": "ollama", "name": "Ollama (Yerel)", "needs_key": False, "needs_setup": True},
    {"id": "lmstudio", "name": "LM Studio (Yerel)", "needs_key": False, "needs_setup": True}
]

def check_local_llm_status(provider: str) -> Dict[str, Union[bool, str]]:
    """Yerel LLM'nin durumunu kontrol et"""
    status = {"running": False, "message": "", "available_models": []}
    
    if provider == "ollama":
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                status["running"] = True
                status["message"] = "Ollama çalışıyor"
                models = response.json().get("models", [])
                status["available_models"] = [model["name"] for model in models]
            else:
                status["message"] = f"Ollama API yanıt verdi, ancak durum kodu hatalı: {response.status_code}"
        except requests.exceptions.RequestException:
            status["message"] = "Ollama API'ye bağlanılamadı. Ollama'nın çalıştığından emin olun."
    
    elif provider == "lmstudio":
        try:
            response = requests.get("http://localhost:1234/v1/models", timeout=2)
            if response.status_code == 200:
                status["running"] = True
                status["message"] = "LM Studio çalışıyor"
                # LM Studio modellerini ekle - API yanıtına göre düzenle
                status["available_models"] = ["default"]
            else:
                status["message"] = f"LM Studio API yanıt verdi, ancak durum kodu hatalı: {response.status_code}"
        except requests.exceptions.RequestException:
            status["message"] = "LM Studio API'ye bağlanılamadı. LM Studio'nun çalıştığından emin olun."
    
    return status