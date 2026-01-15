# tools/llm_tool.py
from os_araci.mcp_core.tool import MCPTool
from os_araci.mcp_core.registry import MCPRegistry
from typing import Dict, Any, List, Optional, Union, Tuple
import json
import requests
import logging
import os
import time
import uuid
import threading
import websocket
import platform
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from abc import ABC, abstractmethod
from dotenv import load_dotenv

# .env dosyasından API anahtarlarını yükle
#load_dotenv()

# Logger yapılandırması
logger = logging.getLogger(__name__)

# WebSocket bağlantıları
ws_connections = {}

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
    def generate_stream(self, prompt: str, ws_id: str, **kwargs) -> None:
        """LLM'den stream ile metin oluşturma"""
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[Dict[str, str]]:
        """Kullanılabilir modelleri getir"""
        pass

    @property
    def supports_streaming(self) -> bool:
        """Provider'ın streaming desteği var mı?"""
        return False


class OpenAIProvider(LLMProvider):
    """OpenAI API kullanarak LLM entegrasyonu"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OpenAI API anahtarı bulunamadı.")
        
        self.base_url = base_url or os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def generate_tasks(self, prompt: str, model: str = "gpt-4o-mini", **kwargs) -> Dict[str, Any]:
        """OpenAI API ile görev listesi oluştur"""
        # Eğer dışarıdan system_prompt geldiyse onu kullan
        if "system_prompt" in kwargs:
            system_prompt = kwargs["system_prompt"]
        else:
            system_prompt = (
                "Sen bir otomasyon aracısın. Aşağıdaki araçları kullanarak kullanıcının isteklerini yerine getirmelisin:\n"
                + self.get_tool_capabilities()
                + "\n\nKullanıcı tarafından istenen görevi gerçekleştirmek için yukarıdaki araçları kullanmalısın."
                + "\n\nÖNEMLİ: Yanıtını SADECE ve KESİNLİKLE aşağıdaki JSON formatında vermelisin, başka formatta yanıt VERME:\n"
                + '{\n  "tasks": [\n    { "name": "Görev adı", "description": "Görev açıklaması", "command": "mkdir -p /home/ahmet/test2", "type": "command", "dependencies": [], "estimatedTime": "1s" }\n  ]\n}'
                + "\n\nBaşka formatta yanıt verirsen, sistem yanıtını işleyemeyecektir. 'task', 'steps' veya diğer formatları KULLANMA, sadece yukarıdaki 'tasks' dizisi formatını kullan."
            )

            # SYSTEM PROMPT LOGLAMA
            logger.info(f"LLM System Prompt:\n{system_prompt}")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.2),
            "response_format": {"type": "json_object"}
        }
        
        try:
            response = requests.post(
                f"{self.base_url}",
                headers=self.headers,
                json=data,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            
            # JSON yanıtı çıkart
            content = result["choices"][0]["message"]["content"]
            
            # Kodu JSON içinden çıkart
            try:
                tasks_data = json.loads(content)
                return tasks_data
            except json.JSONDecodeError:
                logger.error(f"JSON ayrıştırma hatası. İçerik: {content}")
                return {"tasks": []}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenAI API hatası: {str(e)}")
            raise Exception(f"OpenAI API isteği başarısız: {str(e)}")
    
    def generate_text(self, prompt, model="gpt-4o-mini", temperature=0.7, max_tokens=None, **kwargs):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature
        }
        
        url = "https://api.openai.com/v1/chat/completions"
        
        logger.info(f"OpenAI base_url: {url}")
        logger.info(f"OpenAI istek verisi: {json.dumps(data)}")
        
        try:
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code != 200:
                logger.error(f"OpenAI API hatası: Status {response.status_code}")
                logger.error(f"Response body: {response.text}")
                logger.error(f"API Key format: {self.api_key[:8]}...{self.api_key[-4:]}")
                # Hata durumunda string döndür
                return f"Hata: {response.text}"
            
            response.raise_for_status()
            result = response.json()
            
            # Başarılı yanıtı döndür
            return result["choices"][0]["message"]["content"]
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"OpenAI API hatası: {e}")
            logger.error(f"Response status: {response.status_code}")
            logger.error(f"Response body: {response.text}")
            logger.error(f"API Key format: {self.api_key[:8]}...{self.api_key[-4:]}")
            # Hata durumunda string döndür
            return f"API Hatası: {response.text}"   

    def generate_stream(self, prompt: str, ws_id: str, model: str = "gpt-4o-mini", **kwargs) -> None:
        """OpenAI API ile stream olarak metin oluştur"""
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        # System prompt ekle (varsa)
        if "system_prompt" in kwargs and kwargs["system_prompt"]:
            messages = [{"role": "system", "content": kwargs["system_prompt"]}] + messages
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "stream": True
        }
        
        try:
            # WebSocket bağlantısını kontrol et
            if ws_id not in ws_connections:
                logger.error(f"WebSocket bağlantısı bulunamadı: {ws_id}")
                return
            
            ws = ws_connections[ws_id]
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=data,
                timeout=120,
                stream=True
            )
            
            # Hemen response durumunu kontrol et
            if response.status_code != 200:
                logger.error(f"OpenAI API streaming hatası: Status {response.status_code}")
                logger.error(f"Response headers: {response.headers}")
                # Streaming response'da body okumak için:
                error_body = response.text
                logger.error(f"Response body: {error_body}")
                logger.error(f"API Key format: {self.api_key[:8]}...{self.api_key[-4:]}")
                response.raise_for_status()
            
            # Streaming başarılı ise devam et
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    
                    # SSE formatını işle
                    if line.startswith('data: '):
                        data_str = line[6:]
                        
                        # '[DONE]' kontrolü
                        if data_str == '[DONE]':
                            break
                        
                        try:
                            data_json = json.loads(data_str)
                            delta = data_json.get('choices', [{}])[0].get('delta', {})
                            content = delta.get('content', '')
                            
                            if content:
                                complete_text += content
                                # WebSocket üzerinden gönder
                                ws.send(json.dumps({
                                    "type": "content",
                                    "content": content
                                }))
                        except json.JSONDecodeError:
                            continue
            
            # Tamamlandı mesajı
            ws.send(json.dumps({
                "type": "done",
                "content": complete_text
            }))
            
        except Exception as e:
            logger.error(f"Stream üretme hatası: {str(e)}")
            logger.error(f"API Key format: {self.api_key[:8]}...{self.api_key[-4:]}")
            # WebSocket üzerinden hata mesajı gönder
            if ws_id in ws_connections:
                ws_connections[ws_id].send(json.dumps({
                    "type": "error",
                    "content": str(e)
                }))

    def get_available_models(self) -> List[Dict[str, str]]:
        """Kullanılabilir OpenAI modellerini getir"""
        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            # Modelleri filtrele
            valid_models = []
            for model in result.get("data", []):
                model_id = model["id"]
                if any(keyword in model_id.lower() for keyword in ["gpt", "text-embedding", "whisper", "tts", "dall-e"]):
                    valid_models.append({
                        "id": model_id,
                        "name": model_id
                    })
            
            # Boşsa varsayılan modelleri ekle
            if not valid_models:
                valid_models = [
                    {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo"},
                    {"id": "gpt-4", "name": "GPT-4"},
                    {"id": "gpt-4o", "name": "GPT-4o"},
                    {"id": "gpt-4o-mini", "name": "GPT-4o Mini"}
                ]
            
            return valid_models
            
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenAI API modelleri alınamadı: {str(e)}")
            # Varsayılan modeller
            return [
                {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo"},
                {"id": "gpt-4", "name": "GPT-4"},
                {"id": "gpt-4o", "name": "GPT-4o"},
                {"id": "gpt-4o-mini", "name": "GPT-4o Mini"}
            ]
    
    @property
    def supports_streaming(self) -> bool:
        return True


class AnthropicProvider(LLMProvider):
    """Anthropic API kullanarak LLM entegrasyonu"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            logger.warning("Anthropic API anahtarı bulunamadı.")
        
        self.base_url = "https://api.anthropic.com/v1"
        self.headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
    
    def generate_tasks(self, prompt: str, model: str = "claude-3-haiku-20240307", **kwargs) -> Dict[str, Any]:
        """Anthropic API ile görev listesi oluştur"""
        if "system_prompt" in kwargs:
            system_prompt = kwargs["system_prompt"]
        else:
            system_prompt = """
            Kullanıcı görevinin amacını sana anlatacak. Sen bu görevi yerine getirmek için 
            gerekli olan komutları, kod değişikliklerini ve dosya işlemlerini adım adım listeleyeceksin.
            Çıktın aşağıdaki JSON formatında olmalı:
                    {
                        "tasks": [
                            {
                                "name": "Görev adı",
                                "description": "Görev açıklaması",
                                "command": "Çalıştırılacak komut veya yapılacak değişiklik",
                                "type": "command | code_change | file_operation",
                                "dependencies": [0, 1], 
                                "estimatedTime": "10s"
                            }
                        ]
                    }
            ...
            """
        
        data = {
            "model": model,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": kwargs.get("temperature", 0.2),
            "max_tokens": 4000
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/messages",
                headers=self.headers,
                json=data,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            
            # JSON yanıtı çıkart
            content = result["content"][0]["text"]
            
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
            logger.error(f"Anthropic API hatası: {str(e)}")
            raise Exception(f"Anthropic API isteği başarısız: {str(e)}")
    
    def generate_text(self, prompt: str, model: str = "claude-3-haiku-20240307", **kwargs) -> str:
        """Anthropic API ile metin oluştur"""
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4000)
        }
        
        # System prompt ekle (varsa)
        if "system_prompt" in kwargs and kwargs["system_prompt"]:
            data["system"] = kwargs["system_prompt"]
        
        try:
            response = requests.post(
                f"{self.base_url}/messages",
                headers=self.headers,
                json=data,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            
            return result["content"][0]["text"]
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Anthropic API hatası: {str(e)}")
            raise Exception(f"Anthropic API isteği başarısız: {str(e)}")
    
    def generate_stream(self, prompt: str, ws_id: str, model: str = "claude-3-haiku-20240307", **kwargs) -> None:
        """Anthropic API ile stream olarak metin oluştur"""
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4000),
            "stream": True
        }
        
        # System prompt ekle (varsa)
        if "system_prompt" in kwargs and kwargs["system_prompt"]:
            data["system"] = kwargs["system_prompt"]
        
        try:
            # WebSocket bağlantısını kontrol et
            if ws_id not in ws_connections:
                logger.error(f"WebSocket bağlantısı bulunamadı: {ws_id}")
                return
            
            ws = ws_connections[ws_id]
            
            with requests.post(
                f"{self.base_url}/messages",
                headers=self.headers,
                json=data,
                timeout=120,
                stream=True
            ) as response:
                response.raise_for_status()
                
                # Stream yanıtını işle
                complete_text = ""
                
                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        
                        # SSE formatını işle
                        if line.startswith('data: '):
                            data_str = line[6:]
                            
                            # '[DONE]' kontrolü
                            if data_str == '[DONE]':
                                break
                            
                            try:
                                data_json = json.loads(data_str)
                                delta = data_json.get('delta', {})
                                content = delta.get('text', '')
                                
                                if content:
                                    complete_text += content
                                    # WebSocket üzerinden gönder
                                    ws.send(json.dumps({
                                        "type": "content",
                                        "content": content
                                    }))
                            except json.JSONDecodeError:
                                continue
                
                # Tamamlandı mesajı
                ws.send(json.dumps({
                    "type": "done",
                    "content": complete_text
                }))
                
        except Exception as e:
            logger.error(f"Stream üretme hatası: {str(e)}")
            # WebSocket üzerinden hata mesajı gönder
            if ws_id in ws_connections:
                ws_connections[ws_id].send(json.dumps({
                    "type": "error",
                    "content": str(e)
                }))
    
    def get_available_models(self) -> List[Dict[str, str]]:
        """Kullanılabilir Anthropic modellerini getir"""
        # Anthropic'in model listesi API'si yok, varsayılan modelleri döndür
        return [
            {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus"},
            {"id": "claude-3-sonnet-20240229", "name": "Claude 3 Sonnet"},
            {"id": "claude-3-haiku-20240307", "name": "Claude 3 Haiku"},
            {"id": "claude-3.5-sonnet-20240229", "name": "Claude 3.5 Sonnet"}
        ]
    
    @property
    def supports_streaming(self) -> bool:
        return True


class GeminiProvider(LLMProvider):
    """Google Gemini AI API kullanarak LLM entegrasyonu"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("Gemini API anahtarı bulunamadı.")
        
        self.base_url = "https://generativelanguage.googleapis.com/v1"
    
    def generate_tasks(self, prompt: str, model: str = "gemini-1.5-pro", **kwargs) -> Dict[str, Any]:
        """Gemini API ile görev listesi oluştur"""
        if "system_prompt" in kwargs:
            system_prompt = kwargs["system_prompt"]
        else:
            system_prompt = """
            Kullanıcı görevinin amacını sana anlatacak. Sen bu görevi yerine getirmek için 
            gerekli olan komutları, kod değişikliklerini ve dosya işlemlerini adım adım listeleyeceksin.
            Çıktın aşağıdaki JSON formatında olmalı:
                    {
                        "tasks": [
                            {
                                "name": "Görev adı",
                                "description": "Görev açıklaması",
                                "command": "Çalıştırılacak komut veya yapılacak değişiklik",
                                "type": "command | code_change | file_operation",
                                "dependencies": [0, 1], 
                                "estimatedTime": "10s"
                            }
                        ]
                    }
            ...
            """
        
        contents = [
            {"role": "user", "parts": [{"text": system_prompt + "\n\n" + prompt}]}
        ]
        
        data = {
            "contents": contents,
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.2),
                "maxOutputTokens": 4000
            }
        }
        
        try:
            url = f"{self.base_url}/models/{model}:generateContent?key={self.api_key}"
            response = requests.post(
                url,
                json=data,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            
            # JSON yanıtı çıkart
            content = result["candidates"][0]["content"]["parts"][0]["text"]
            
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
            logger.error(f"Gemini API hatası: {str(e)}")
            raise Exception(f"Gemini API isteği başarısız: {str(e)}")
    
    def generate_text(self, prompt: str, model: str = "gemini-1.5-pro", **kwargs) -> str:
        """Gemini API ile metin oluştur"""
        contents = []
        
        # System prompt ekle (varsa)
        if "system_prompt" in kwargs and kwargs["system_prompt"]:
            contents.append({"role": "system", "parts": [{"text": kwargs["system_prompt"]}]})
        
        contents.append({"role": "user", "parts": [{"text": prompt}]})
        
        data = {
            "contents": contents,
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.7),
                "maxOutputTokens": kwargs.get("max_tokens", 4000)
            }
        }
        
        try:
            url = f"{self.base_url}/models/{model}:generateContent?key={self.api_key}"
            response = requests.post(
                url,
                json=data,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            
            return result["candidates"][0]["content"]["parts"][0]["text"]
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Gemini API hatası: {str(e)}")
            raise Exception(f"Gemini API isteği başarısız: {str(e)}")
    
    def generate_stream(self, prompt: str, ws_id: str, model: str = "gemini-1.5-pro", **kwargs) -> None:
        """Gemini API ile stream olarak metin oluştur"""
        contents = []
        
        # System prompt ekle (varsa)
        if "system_prompt" in kwargs and kwargs["system_prompt"]:
            contents.append({"role": "system", "parts": [{"text": kwargs["system_prompt"]}]})
        
        contents.append({"role": "user", "parts": [{"text": prompt}]})
        
        data = {
            "contents": contents,
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.7),
                "maxOutputTokens": kwargs.get("max_tokens", 4000)
            }
        }
        
        try:
            # WebSocket bağlantısını kontrol et
            if ws_id not in ws_connections:
                logger.error(f"WebSocket bağlantısı bulunamadı: {ws_id}")
                return
            
            ws = ws_connections[ws_id]
            
            url = f"{self.base_url}/models/{model}:streamGenerateContent?key={self.api_key}&alt=sse"
            response = requests.post(
                url,
                json=data,
                timeout=120,
                stream=True
            )
            response.raise_for_status()
            
            # Stream yanıtını işle
            complete_text = ""
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    
                    # SSE formatını işle
                    if line.startswith('data: '):
                        data_str = line[6:]
                        
                        if data_str == "[DONE]":
                            break
                        
                        try:
                            data_json = json.loads(data_str)
                            
                            # Gemini stream yanıt formatı biraz farklı
                            delta = data_json.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                            
                            if delta:
                                complete_text += delta
                                # WebSocket üzerinden gönder
                                ws.send(json.dumps({
                                    "type": "content",
                                    "content": delta
                                }))
                        except json.JSONDecodeError:
                            continue
            
            # Tamamlandı mesajı
            ws.send(json.dumps({
                "type": "done",
                "content": complete_text
            }))
            
        except Exception as e:
            logger.error(f"Stream üretme hatası: {str(e)}")
            # WebSocket üzerinden hata mesajı gönder
            if ws_id in ws_connections:
                ws_connections[ws_id].send(json.dumps({
                    "type": "error",
                    "content": str(e)
                }))
    
    def get_available_models(self) -> List[Dict[str, str]]:
        """Kullanılabilir Gemini modellerini getir"""
        try:
            url = f"{self.base_url}/models?key={self.api_key}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            # Gemini modellerini filtrele
            gemini_models = []
            for model in result.get("models", []):
                if "gemini" in model["name"].lower():
                    model_id = model["name"].split("/")[-1]
                    gemini_models.append({
                        "id": model_id,
                        "name": model_id
                    })
            
            return gemini_models if gemini_models else [
                {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash"},
                {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro"}
            ]
            
        except requests.exceptions.RequestException:
            # Varsayılan modeller
            return [
                {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash"},
                {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro"}
            ]
    
    @property
    def supports_streaming(self) -> bool:
        return True


class DeepSeekProvider(LLMProvider):
    """DeepSeek API kullanarak LLM entegrasyonu"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            logger.warning("DeepSeek API anahtarı bulunamadı.")
        
        self.base_url = "https://api.deepseek.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def generate_tasks(self, prompt: str, model: str = "deepseek-chat", **kwargs) -> Dict[str, Any]:
        """DeepSeek API ile görev listesi oluştur"""
        if "system_prompt" in kwargs:
            system_prompt = kwargs["system_prompt"]
        else:
            system_prompt = """
            Kullanıcı görevinin amacını sana anlatacak. Sen bu görevi yerine getirmek için 
            gerekli olan komutları, kod değişikliklerini ve dosya işlemlerini adım adım listeleyeceksin.
            Çıktın aşağıdaki JSON formatında olmalı:
                    {
                        "tasks": [
                            {
                                "name": "Görev adı",
                                "description": "Görev açıklaması",
                                "command": "Çalıştırılacak komut veya yapılacak değişiklik",
                                "type": "command | code_change | file_operation",
                                "dependencies": [0, 1], 
                                "estimatedTime": "10s"
                            }
                        ]
                    }
            ...
            """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.2),
            "response_format": {"type": "json_object"}
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=data,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            
            # JSON yanıtı çıkart
            content = result["choices"][0]["message"]["content"]
            
            try:
                tasks_data = json.loads(content)
                return tasks_data
            except json.JSONDecodeError:
                logger.error(f"JSON ayrıştırma hatası. İçerik: {content}")
                return {"tasks": []}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"DeepSeek API hatası: {str(e)}")
            raise Exception(f"DeepSeek API isteği başarısız: {str(e)}")
    
    def generate_text(self, prompt: str, model: str = "deepseek-chat", **kwargs) -> str:
        """DeepSeek API ile metin oluştur"""
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        # System prompt ekle (varsa)
        if "system_prompt" in kwargs and kwargs["system_prompt"]:
            messages = [{"role": "system", "content": kwargs["system_prompt"]}] + messages
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7)
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=data,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            
            return result["choices"][0]["message"]["content"]
            
        except requests.exceptions.RequestException as e:
            logger.error(f"DeepSeek API hatası: {str(e)}")
            raise Exception(f"DeepSeek API isteği başarısız: {str(e)}")
    
    def generate_stream(self, prompt: str, ws_id: str, model: str = "deepseek-chat", **kwargs) -> None:
        """DeepSeek API ile stream olarak metin oluştur"""
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        # System prompt ekle (varsa)
        if "system_prompt" in kwargs and kwargs["system_prompt"]:
            messages = [{"role": "system", "content": kwargs["system_prompt"]}] + messages
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "stream": True
        }
        
        try:
            # WebSocket bağlantısını kontrol et
            if ws_id not in ws_connections:
                logger.error(f"WebSocket bağlantısı bulunamadı: {ws_id}")
                return
            
            ws = ws_connections[ws_id]
            
            with requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=data,
                timeout=120,
                stream=True
            ) as response:
                response.raise_for_status()
                
                # Stream yanıtını işle
                complete_text = ""
                
                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        
                        # SSE formatını işle
                        if line.startswith('data: '):
                            data_str = line[6:]
                            
                            # '[DONE]' kontrolü
                            if data_str == '[DONE]':
                                break
                            
                            try:
                                data_json = json.loads(data_str)
                                delta = data_json.get('choices', [{}])[0].get('delta', {})
                                content = delta.get('content', '')
                                
                                if content:
                                    complete_text += content
                                    # WebSocket üzerinden gönder
                                    ws.send(json.dumps({
                                        "type": "content",
                                        "content": content
                                    }))
                            except json.JSONDecodeError:
                                continue
                
                # Tamamlandı mesajı
                ws.send(json.dumps({
                    "type": "done",
                    "content": complete_text
                }))
                
        except Exception as e:
            logger.error(f"Stream üretme hatası: {str(e)}")
            # WebSocket üzerinden hata mesajı gönder
            if ws_id in ws_connections:
                ws_connections[ws_id].send(json.dumps({
                    "type": "error",
                    "content": str(e)
                }))
    
    def get_available_models(self) -> List[Dict[str, str]]:
        """Kullanılabilir DeepSeek modellerini getir"""
        # DeepSeek'in model listesi API'si yok, varsayılan modelleri döndür
        return [
            {"id": "deepseek-chat", "name": "DeepSeek Chat"},
            {"id": "deepseek-coder", "name": "DeepSeek Coder"},
            {"id": "deepseek-lite", "name": "DeepSeek Lite"}
        ]
    
    @property
    def supports_streaming(self) -> bool:
        return True


class WebScraperLLM(LLMProvider):
    """Web scraper kullanarak LLM entegrasyonu"""
    
    def __init__(self, service_type: str = "chatgpt", username: str = None, password: str = None):
        self.service_type = service_type.lower()  # Büyük/küçük harf hassasiyetini önlemek için
        self.driver = None
        self.username = username
        self.password = password
        self.is_logged_in = False
        self._setup_driver()


    def _login(self):
        """LLM servisine giriş yap"""
        if self.is_logged_in:
            return True
            
        if not self.username or not self.password:
            logger.warning(f"{self.service_type} için kullanıcı adı veya şifre belirtilmedi. Oturum açılmadan devam edilecek.")
            return False
        
        try:
            if self.service_type == "chatgpt":
                # ChatGPT login sayfasına git
                self.driver.get("https://chat.openai.com/auth/login")
                time.sleep(2)
                
                # Login butonuna tıkla
                login_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Log in')]"))
                )
                login_button.click()
                
                # Email giriş alanını bekle ve doldur
                email_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "username"))
                )
                email_input.clear()
                email_input.send_keys(self.username)
                
                # Devam butonuna tıkla
                continue_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue')]"))
                )
                continue_button.click()
                
                # Şifre giriş alanını bekle ve doldur
                password_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "password"))
                )
                password_input.clear()
                password_input.send_keys(self.password)
                
                # Giriş yap butonuna tıkla
                sign_in_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue')]"))
                )
                sign_in_button.click()
                
                # Giriş yapıldığını kontrol et
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[tabindex='0']"))
                )
                
                self.is_logged_in = True
                logger.info("ChatGPT'ye başarıyla giriş yapıldı")
                return True
                
            elif self.service_type == "claude":
                # Claude login sayfasına git
                self.driver.get("https://claude.ai/login")
                time.sleep(2)
                
                # Email giriş alanını bekle ve doldur
                email_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "email"))
                )
                email_input.clear()
                email_input.send_keys(self.username)
                
                # Devam butonuna tıkla
                continue_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue')]"))
                )
                continue_button.click()
                
                # Şifre giriş alanını bekle ve doldur
                password_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "password"))
                )
                password_input.clear()
                password_input.send_keys(self.password)
                
                # Giriş yap butonuna tıkla
                sign_in_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue')]"))
                )
                sign_in_button.click()
                
                # Giriş yapıldığını kontrol et
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[contenteditable='true']"))
                )
                
                self.is_logged_in = True
                logger.info("Claude'a başarıyla giriş yapıldı")
                return True
                
            elif self.service_type == "deepseek":
                # DeepSeek login sayfasına git
                self.driver.get("https://chat.deepseek.com/login")
                time.sleep(2)
                
                # Email giriş alanını bekle ve doldur
                email_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
                )
                email_input.clear()
                email_input.send_keys(self.username)
                
                # Şifre giriş alanını bekle ve doldur
                password_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']"))
                )
                password_input.clear()
                password_input.send_keys(self.password)
                
                # Giriş yap butonuna tıkla
                sign_in_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Sign In') or contains(text(), 'Login')]"))
                )
                sign_in_button.click()
                
                # Giriş yapıldığını kontrol et - ana sayfada sohbet alanının görünmesini bekle
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "textarea, div[contenteditable='true']"))
                )
                
                self.is_logged_in = True
                logger.info("DeepSeek'e başarıyla giriş yapıldı")
                return True
            else:
                logger.error(f"Desteklenmeyen servis türü: {self.service_type}")
                return False
                
        except Exception as e:
            logger.error(f"Oturum açma hatası ({self.service_type}): {str(e)}")
            return False
    
    def _setup_driver(self):
        """Selenium webdriver'ı yapılandır"""
        try:
            options = Options()
            options.add_argument("--headless=new")  # Başsız mod
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-notifications")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            
            # User agent
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
            
            self.driver = webdriver.Chrome(options=options)
            logger.info(f"Web scraper başlatıldı: {self.service_type}")
        except Exception as e:
            logger.error(f"Web driver başlatılamadı: {str(e)}")
            raise Exception(f"Web scraper başlatılamadı: {str(e)}")
    
    def generate_tasks(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Web scraper ile görev listesi oluştur"""
            # Dışarıdan gelen system_prompt varsa onu kullan

        if not self.is_logged_in:
            self._login()

        if "system_prompt" in kwargs and kwargs["system_prompt"]:
            system_prompt_content = kwargs["system_prompt"]
        else:
            system_prompt_content = """
            Sen bir otomasyon aracısın. Kullanıcının istediği görevi yerine getirmek için gerekli araçları kullan.
            Yanıtını KESİNLİKLE aşağıdaki JSON formatında ver:
            
            {
            "tasks": [
                {
                "tool": "araç_adı",  
                "action": "eylem_adı",
                "params": { "parametre1": "değer1" },
                "name": "Görev adı",
                "description": "Görev açıklaması",
                "dependencies": []
                }
            ]
            }
            
            Örnek yanıt:
            {
            "tasks": [
                {
                "tool": "file_manager",
                "action": "create_folder",
                "params": { "path": "/home/user/dizin" },
                "name": "Dizin oluştur",
                "description": "Kullanıcı için test dizini oluştur"
                }
            ]
            }
            
            SADECE JSON formatında yanıt ver, açıklama ekleme!
            """

        if self.service_type == "chatgpt":
            try:
                # ChatGPT sayfasına git
                self.driver.get("https://chat.openai.com/")
                time.sleep(2)
                
                # Prompt'u gir
                task_prompt = f"""
                {system_prompt_content}
                
                Kullanıcı isteği: {prompt}
                
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
        
        elif self.service_type == "claude":
            try:
                # Claude sayfasına git
                self.driver.get("https://claude.ai/chats")
                time.sleep(2)
                
                # Prompt'u gir
                task_prompt = f"""
                {system_prompt_content}
                
                Kullanıcı isteği: {prompt}
                
                Sadece JSON formatında yanıt ver.
                """
                
                # Metin girişi alanını bul ve prompt'u gönder
                input_box = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[contenteditable='true']"))
                )
                input_box.clear()
                input_box.send_keys(task_prompt)
                
                # Gönder butonunu bul ve tıkla
                send_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Send message']"))
                )
                send_button.click()
                
                # Yanıt için bekle
                time.sleep(5)  # Claude'un yanıt vermeye başlaması için bekle
                
                # Yanıt elementini bul (Claude'un yanıtı genellikle son mesajdır)
                response_element = WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".prose:last-of-type"))
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
        
        elif self.service_type == "deepseek":
            try:
                # DeepSeek chat sayfasına git
                self.driver.get("https://chat.deepseek.com/")
                time.sleep(2)
                
                # Prompt'u gir
                task_prompt = f"""
                {system_prompt_content}
                
                Kullanıcı isteği: {prompt}
                
                Sadece JSON formatında yanıt ver.
                """
                
                # Metin girişi alanını bul ve prompt'u gönder
                input_box = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "textarea, div[contenteditable='true']"))
                )
                input_box.clear()
                input_box.send_keys(task_prompt)
                
                # Gönder butonunu bul ve tıkla
                send_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Send message'], button.send-button"))
                )
                send_button.click()
                
                # Yanıt için bekle
                time.sleep(5)  # DeepSeek'in yanıt vermeye başlaması için bekle
                
                # Yanıt elementini bul
                response_element = WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".message-content, .response-content"))
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
                logger.error(f"Web scraper hatası (DeepSeek): {str(e)}")
                return {"tasks": []}
        
        else:
            logger.error(f"Desteklenmeyen servis türü: {self.service_type}")
            return {"tasks": []}
    
    def generate_text(self, prompt: str, **kwargs) -> str:
        """Web scraper ile metin oluştur"""
        if not self.is_logged_in:
            self._login()
        
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
        
        elif self.service_type == "claude":
            try:
                # Claude sayfasına git (eğer zaten sayfada değilsek)
                if "claude.ai" not in self.driver.current_url:
                    self.driver.get("https://claude.ai/chats")
                    time.sleep(2)
                
                # Prompt'u gir
                input_box = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[contenteditable='true']"))
                )
                input_box.clear()
                input_box.send_keys(prompt)
                
                # Gönder butonunu bul ve tıkla
                send_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Send message']"))
                )
                send_button.click()
                
                # Yanıt için bekle
                time.sleep(5)  # Claude'un yanıt vermeye başlaması için bekle
                
                # Yanıt elementini bul
                response_element = WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".prose:last-of-type"))
                )
                
                return response_element.text
                
            except Exception as e:
                logger.error(f"Web scraper hatası: {str(e)}")
                return f"Web scraper hatası: {str(e)}"
        
        elif self.service_type == "deepseek":
            try:
                # DeepSeek sayfasına git (eğer zaten sayfada değilsek)
                if "deepseek.com" not in self.driver.current_url:
                    self.driver.get("https://chat.deepseek.com/")
                    time.sleep(2)
                
                # Prompt'u gir
                input_box = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "textarea, div[contenteditable='true']"))
                )
                input_box.clear()
                input_box.send_keys(prompt)
                
                # Gönder butonunu bul ve tıkla
                send_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Send message'], button.send-button"))
                )
                send_button.click()
                
                # Yanıt için bekle
                time.sleep(5)  # DeepSeek'in yanıt vermeye başlaması için bekle
                
                # Yanıt elementini bul
                response_element = WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".message-content, .response-content"))
                )
                
                return response_element.text
                
            except Exception as e:
                logger.error(f"Web scraper hatası (DeepSeek): {str(e)}")
                return f"Web scraper hatası: {str(e)}"
        else:
            logger.error(f"Desteklenmeyen servis türü: {self.service_type}")
            return "Desteklenmeyen servis türü"
    
    def generate_stream(self, prompt: str, ws_id: str, **kwargs) -> None:
        """Web scraper ile stream olarak metin oluştur"""
        if ws_id not in ws_connections:
            logger.error(f"WebSocket bağlantısı bulunamadı: {ws_id}")
            return
        
        ws = ws_connections[ws_id]
        
        # Web scraper streaming desteği yok, standart generate_text kullan ve bitince tamamı gönder
        try:
            result = self.generate_text(prompt, **kwargs)
            
            # WebSocket üzerinden gönder
            ws.send(json.dumps({
                "type": "content",
                "content": result
            }))
            
            # Tamamlandı mesajı
            ws.send(json.dumps({
                "type": "done",
                "content": result
            }))
        except Exception as e:
            logger.error(f"Web scraper stream hatası: {str(e)}")
            ws.send(json.dumps({
                "type": "error",
                "content": str(e)
            }))
    
    def get_available_models(self) -> List[Dict[str, str]]:
        """Web scraper ile kullanılabilir modelleri getir"""
        if self.service_type == "chatgpt":
            # Web arayüzünde kullanılabilir modeller
            return [
                {"id": "gpt-4", "name": "GPT-4 (Web)"},
                {"id": "gpt-4o", "name": "GPT-4o (Web)"},
                {"id": "gpt-3.5", "name": "GPT-3.5 (Web)"}
            ]
        elif self.service_type == "claude":
            return [
                {"id": "claude-3-opus", "name": "Claude 3 Opus (Web)"},
                {"id": "claude-3-sonnet", "name": "Claude 3 Sonnet (Web)"},
                {"id": "claude-3-haiku", "name": "Claude 3 Haiku (Web)"}
            ]
        elif self.service_type == "deepseek":
            return [
                {"id": "deepseek-chat", "name": "DeepSeek Chat (Web)"},
                {"id": "deepseek-coder", "name": "DeepSeek Coder (Web)"}
            ]
        else:
            return [{"id": "default", "name": f"{self.service_type} (Web)"}]
    
    @property
    def supports_streaming(self) -> bool:
        return False
    
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
            self.base_url = base_url or os.getenv("OLLAMA_API_BASE", "http://localhost:11434/api")
        elif self.provider == "lmstudio":
            self.base_url = base_url or os.getenv("LMSTUDIO_API_BASE", "http://localhost:1234/v1")
        else:
            logger.error(f"Desteklenmeyen yerel LLM sağlayıcısı: {provider}")
            raise ValueError(f"Desteklenmeyen yerel LLM sağlayıcısı: {provider}")
    
    def generate_tasks(self, prompt: str, model: str = "llama2", **kwargs) -> Dict[str, Any]:
        """Yerel LLM ile görev listesi oluştur"""
        if "system_prompt" in kwargs:
            system_prompt = kwargs["system_prompt"]
        else:
            system_prompt = """
            Kullanıcı görevinin amacını sana anlatacak. Sen bu görevi yerine getirmek için 
            gerekli olan komutları, kod değişikliklerini ve dosya işlemlerini adım adım listeleyeceksin.
            ...
            """
        
        try:
            if self.provider == "ollama":
                data = {
                    "model": model,
                    "prompt": system_prompt + "\n\n" + prompt,
                    "stream": False,
                    "temperature": kwargs.get("temperature", 0.2)
                }
                
                response = requests.post(
                    f"{self.base_url}/generate",
                    json=data,
                    timeout=60
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
                    json=data,
                    timeout=60
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
                # System prompt ekle (varsa)
                if "system_prompt" in kwargs and kwargs["system_prompt"]:
                    full_prompt = f"<s>[INST] <<SYS>>\n{kwargs['system_prompt']}\n<</SYS>>\n\n{prompt} [/INST]"
                else:
                    full_prompt = prompt
                
                data = {
                    "model": model,
                    "prompt": full_prompt,
                    "stream": False,
                    "temperature": kwargs.get("temperature", 0.7)
                }
                
                response = requests.post(
                    f"{self.base_url}/generate",
                    json=data,
                    timeout=60
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
                
                # System prompt ekle (varsa)
                if "system_prompt" in kwargs and kwargs["system_prompt"]:
                    messages = [{"role": "system", "content": kwargs["system_prompt"]}] + messages
                
                data = {
                    "model": model,
                    "messages": messages,
                    "temperature": kwargs.get("temperature", 0.7)
                }
                
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    json=data,
                    timeout=60
                )
                response.raise_for_status()
                result = response.json()
                
                # LM Studio yanıtı
                return result["choices"][0]["message"]["content"]
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Yerel LLM API hatası: {str(e)}")
            raise Exception(f"Yerel LLM API isteği başarısız: {str(e)}")
    
    def generate_stream(self, prompt: str, ws_id: str, model: str = "llama2", **kwargs) -> None:
        """Yerel LLM ile stream olarak metin oluştur"""
        try:
            # WebSocket bağlantısını kontrol et
            if ws_id not in ws_connections:
                logger.error(f"WebSocket bağlantısı bulunamadı: {ws_id}")
                return
            
            ws = ws_connections[ws_id]
            
            if self.provider == "ollama":
                # System prompt ekle (varsa)
                if "system_prompt" in kwargs and kwargs["system_prompt"]:
                    full_prompt = f"<s>[INST] <<SYS>>\n{kwargs['system_prompt']}\n<</SYS>>\n\n{prompt} [/INST]"
                else:
                    full_prompt = prompt
                
                data = {
                    "model": model,
                    "prompt": full_prompt,
                    "stream": True,
                    "temperature": kwargs.get("temperature", 0.7)
                }
                
                with requests.post(
                    f"{self.base_url}/generate",
                    json=data,
                    timeout=120,
                    stream=True
                ) as response:
                    response.raise_for_status()
                    
                    # Stream yanıtını işle
                    complete_text = ""
                    
                    for line in response.iter_lines():
                        if line:
                            line = line.decode('utf-8')
                            try:
                                data_json = json.loads(line)
                                
                                # Ollama streaming JSON formatı
                                if "response" in data_json:
                                    content = data_json["response"]
                                    complete_text += content
                                    
                                    # WebSocket üzerinden gönder
                                    ws.send(json.dumps({
                                        "type": "content",
                                        "content": content
                                    }))
                                
                                # Son mesaj kontrolü
                                if data_json.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                continue
                    
                    # Tamamlandı mesajı
                    ws.send(json.dumps({
                        "type": "done",
                        "content": complete_text
                    }))
                    
            elif self.provider == "lmstudio":
                # LM Studio, OpenAI API formatını kullanır
                messages = [
                    {"role": "user", "content": prompt}
                ]
                
                # System prompt ekle (varsa)
                if "system_prompt" in kwargs and kwargs["system_prompt"]:
                    messages = [{"role": "system", "content": kwargs["system_prompt"]}] + messages
                
                data = {
                    "model": model,
                    "messages": messages,
                    "temperature": kwargs.get("temperature", 0.7),
                    "stream": True
                }
                
                with requests.post(
                    f"{self.base_url}/chat/completions",
                    json=data,
                    timeout=120,
                    stream=True
                ) as response:
                    response.raise_for_status()
                    
                    # Stream yanıtını işle
                    complete_text = ""
                    
                    for line in response.iter_lines():
                        if line:
                            line = line.decode('utf-8')
                            
                            # SSE formatını işle
                            if line.startswith('data: '):
                                data_str = line[6:]
                                
                                # '[DONE]' kontrolü
                                if data_str == '[DONE]':
                                    break
                                
                                try:
                                    data_json = json.loads(data_str)
                                    delta = data_json.get('choices', [{}])[0].get('delta', {})
                                    content = delta.get('content', '')
                                    
                                    if content:
                                        complete_text += content
                                        # WebSocket üzerinden gönder
                                        ws.send(json.dumps({
                                            "type": "content",
                                            "content": content
                                        }))
                                except json.JSONDecodeError:
                                    continue
                    
                    # Tamamlandı mesajı
                    ws.send(json.dumps({
                        "type": "done",
                        "content": complete_text
                    }))
                
        except Exception as e:
            logger.error(f"Stream üretme hatası: {str(e)}")
            # WebSocket üzerinden hata mesajı gönder
            if ws_id in ws_connections:
                ws_connections[ws_id].send(json.dumps({
                    "type": "error",
                    "content": str(e)
                }))
    
    def get_available_models(self) -> List[Dict[str, str]]:
        """Yerel LLM'de kullanılabilir modelleri getir"""
        try:
            if self.provider == "ollama":
                response = requests.get(f"{self.base_url.replace('/api', '')}/api/tags", timeout=30)
                response.raise_for_status()
                result = response.json()
                
                return [
                    {"id": model["name"], "name": model["name"]}
                    for model in result.get("models", [])
                ]
                
            elif self.provider == "lmstudio":
                # LM Studio modellerini doğrudan alma API'si yok
                # Kullanıcı yapılandırmasından gelmeli
                return [
                    {"id": "default", "name": "LM Studio Default"},
                    {"id": "llama2", "name": "Llama 2"},
                    {"id": "mistral", "name": "Mistral"},
                    {"id": "phi2", "name": "Phi-2"}
                ]
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Yerel LLM model listesi alınamadı: {str(e)}")
            
            # Varsayılan modelleri döndür
            if self.provider == "ollama":
                return [
                    {"id": "llama2", "name": "Llama 2"},
                    {"id": "mistral", "name": "Mistral"},
                    {"id": "codellama", "name": "Code Llama"},
                    {"id": "phi2", "name": "Phi-2"}
                ]
            elif self.provider == "lmstudio":
                return [
                    {"id": "default", "name": "LM Studio Default"}
                ]
    
    @property
    def supports_streaming(self) -> bool:
        return True


class LLMFactory:
    """LLM sağlayıcıları oluşturma factory sınıfı"""
    
    @staticmethod
    def create_provider(provider_type: str, **kwargs) -> LLMProvider:
        """
        LLM sağlayıcısı oluştur
        
        provider_type: "openai", "anthropic", "gemini", "deepseek", "webscraper", "ollama", "lmstudio"
        kwargs: Sağlayıcıya özel parametreler
        """
        if provider_type == "openai":
            return OpenAIProvider(api_key=kwargs.get("api_key"), base_url=kwargs.get("base_url"))
        
        elif provider_type == "anthropic":
            return AnthropicProvider(api_key=kwargs.get("api_key"))
        
        elif provider_type == "gemini":
            return GeminiProvider(api_key=kwargs.get("api_key"))
        
        elif provider_type == "deepseek":
            return DeepSeekProvider(api_key=kwargs.get("api_key"))
        
        elif provider_type == "webscraper":
            service_type = kwargs.get('service_type', 'chatgpt')
            username = kwargs.get('username') or os.getenv(f"{service_type.upper()}_USERNAME")
            password = kwargs.get('password') or os.getenv(f"{service_type.upper()}_PASSWORD")
            
            return WebScraperLLM(service_type=service_type, username=username, password=password)

        
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
    {"id": "anthropic", "name": "Anthropic API", "needs_key": True, "needs_setup": False},
    {"id": "gemini", "name": "Google Gemini", "needs_key": True, "needs_setup": False},
    {"id": "deepseek", "name": "DeepSeek API", "needs_key": True, "needs_setup": False},
    {"id": "webscraper", "name": "Web Scraper (ChatGPT)", "needs_key": False, "needs_setup": True},
    {"id": "webscraper_claude", "name": "Web Scraper (Claude)", "needs_key": False, "needs_setup": True},
    {"id": "webscraper_deepseek", "name": "Web Scraper (DeepSeek)", "needs_key": False, "needs_setup": True},
    {"id": "ollama", "name": "Ollama (Yerel)", "needs_key": False, "needs_setup": True},
    {"id": "lmstudio", "name": "LM Studio (Yerel)", "needs_key": False, "needs_setup": True}
]


class LLMTool(MCPTool):
    """LLM entegrasyonu için MCP aracı"""
    
    def __init__(self):
        """LLM Tool başlatıcı"""
        super().__init__(
            name="llm_tool",
            description="LLM entegrasyonu ve görev oluşturma aracı",
            version="2.0.0"
        )
        self.llm_providers = {}  # Önbelleğe alınan LLM sağlayıcıları
        self.ws_server = None  # WebSocket sunucusu
        self.registry = None  # Boş registry başlat
    
    def initialize(self):
        """Aracı başlat"""
        logger.info("LLM Tool başlatılıyor...")
        
        # MCPRegistry'ye erişim alın
        from os_araci.mcp_core.registry import MCPRegistry
        self.registry = MCPRegistry()
        # API endpoints'leri kaydet
        self.register_action("generate_tasks", self.generate_tasks, ["prompt", "provider", "model", "temperature"], "LLM ile görev üret")
        self.register_action("generate_text", self.generate_text, ["prompt", "provider", "model", "temperature", "system_prompt"], "LLM ile metin üret")
        self.register_action("stream_start", self.stream_start, ["prompt", "provider", "model", "temperature", "system_prompt"], "Stream başlat")
        self.register_action("stream_stop", self.stream_stop, ["ws_id"], "Stream durdur")
        self.register_action("get_models", self.get_models, ["provider"], "Model listesini getir")
        self.register_action("get_providers", self.get_providers, [], "Tüm sağlayıcıları getir")
        self.register_action("check_status", self.check_status, ["provider"], "Sağlayıcı durumu kontrol et")
        self.register_action("setup_provider", self.setup_provider, ["provider", "api_key", "base_url"], "LLM sağlayıcıyı yapılandır")
        
        # WebSocket bağlantılarını temizle
        global ws_connections
        ws_connections = {}
        
        logger.info("LLM Tool başlatıldı")
        return True
    
    def _get_provider(self, provider_type: str, **kwargs) -> LLMProvider:
        """LLM sağlayıcısını getir veya oluştur"""
        if provider_type not in self.llm_providers:
            # Webscraper için özel durum
            if provider_type == "webscraper_claude":
                provider_type = "webscraper"
                kwargs["service_type"] = "claude"
            elif provider_type == "webscraper_deepseek":
                provider_type = "webscraper"
                kwargs["service_type"] = "deepseek"
            
            # Sağlayıcıya özel parametre ayarları
            provider_params = {}
            
            if provider_type == "openai":
                api_key = kwargs.get('api_key') or os.getenv("OPENAI_API_KEY")
                base_url = kwargs.get('base_url') or os.getenv("OPENAI_API_BASE")
                provider_params["api_key"] = api_key
                if base_url:
                    provider_params["base_url"] = base_url
            
            elif provider_type == "anthropic":
                api_key = kwargs.get('api_key') or os.getenv("ANTHROPIC_API_KEY")
                provider_params["api_key"] = api_key
            
            elif provider_type == "gemini":
                api_key = kwargs.get('api_key') or os.getenv("GEMINI_API_KEY")
                provider_params["api_key"] = api_key
            
            elif provider_type == "deepseek":
                api_key = kwargs.get('api_key') or os.getenv("DEEPSEEK_API_KEY")
                provider_params["api_key"] = api_key
            
            elif provider_type == "webscraper":
                service_type = kwargs.get('service_type', 'chatgpt')
                provider_params["service_type"] = service_type
            
            elif provider_type in ["ollama", "lmstudio"]:
                base_url = kwargs.get('base_url')
                if base_url:
                    provider_params["base_url"] = base_url
            
            # Sağlayıcıyı oluştur
            self.llm_providers[provider_type] = LLMFactory.create_provider(provider_type, **provider_params)
        
        return self.llm_providers[provider_type]
    
    def get_tool_capabilities(self) -> str:
        result = []
        for tool_name, tool in self.registry.get_all_tools().items():
            actions = tool.get_all_actions()
            for action_name, meta in actions.items():
                param_list = ", ".join(meta.get("params", []))
                desc = meta.get("description", "")
                result.append(f"- {tool_name}.{action_name}({param_list}): {desc}")
        print(result)
        return "\n".join(result)
    
    def generate_tasks(self, **kwargs) -> Dict[str, Any]:
        """LLM kullanarak görev listesi oluştur"""
        try:
            prompt = kwargs.get('prompt')
            if not prompt:
                logger.error("Boş prompt hatası")
                return {"error": "Prompt gerekli", "status": "error"}, 400
            
            provider_type = kwargs.get('provider', 'openai')
            model = kwargs.get('model')
            temperature = kwargs.get('temperature', 0.2)
            
            logger.info(f"LLM görev oluşturma isteği: Prompt='{prompt}', Provider={provider_type}, Model={model}")
            
            # Sağlayıcı örneğini al
            try:
                provider = self._get_provider(provider_type, **kwargs)
                logger.info(f"Provider başarıyla oluşturuldu: {provider_type}")
            except Exception as provider_err:
                logger.error(f"Provider oluşturma hatası: {str(provider_err)}")
                return {"error": f"Provider oluşturma hatası: {str(provider_err)}", "status": "error"}, 500
            
            system_prompt = (
                "Sen Metis Agent sisteminde görev üreten, araç odaklı bir otomasyon asistanısın. Kullanıcının doğal dildeki isteğini analiz eder, aşağıdaki araçları kullanarak uygun görevleri JSON formatında üretirsin.\n\n"
                + "Kullanabileceğin araçlar ve fonksiyonlar şunlardır:\n"
                + self.get_tool_capabilities() +
                "\n\n"
                + "⛔️ KURALLAR:\n"
                + "- Mümkün olduğunda sistem araçlarını (file_manager, network_manager, system_info vb.) kullan.\n"
                + "- Eğer mevcut araçlarla yapılamayan bir görev varsa, terminal komutu da kullanabilirsin. Bu durumda 'tool' alanı 'command_executor' olmalı.\n"
                + "- Her görev için benzersiz bir ID kullan (task-1, task-2 gibi)\n"
                + "- Doğrudan terminal komutları yazmak yerine tool'ları tercih et. Sadece gerekli durumlarda shell komutlarına başvur.\n"
                + "- Görevler arası veri aktarımı için, önceki görevlerin çıktılarını context değişkenleri olarak kullanabilirsin.\n"
                + "- Bir görevin çıktısına başka bir görevde şu şekilde referans ver: <task_ID_output>.\n\n"
                + "✅ GÖREV YAPISI:\n"
                + '{\n  "tasks": [\n    { "tool": "tool_adı", "action": "eylem_adı", "params": { "param1": "değer1" }, "name": "Görev başlığı", "description": "Açıklama", "dependencies": [], "id": "benzersiz-id" }\n  ]\n}\n'
                + "\n📌 ÖRNEKLER:\n"
                + '{ "tool": "command_executor", "action": "execute_command", "params": { "command": "cat /etc/resolv.conf" }, "name": "DNS bilgisini oku", "description": "DNS ayarlarını okur", "dependencies": [], "id": "task-1" }\n'
                + '{ "tool": "in_memory_editor", "action": "write_file", "params": { "filename": "dns.txt", "content": "DNS Ayarları: <task_task-1_output>" }, "name": "DNS bilgisini kaydet", "description": "Okunan DNS ayarlarını dosyaya kaydeder", "dependencies": ["task-1"], "id": "task-2" }\n'
                + '{ "tool": "file_manager", "action": "create_folder", "params": { "path": "/home/user/dns-backup" }, "name": "Klasör oluştur", "description": "Yedek klasörü oluşturur", "dependencies": [], "id": "task-3" }\n'
                + '{ "tool": "in_memory_editor", "action": "save_to_disk", "params": { "filename": "dns.txt", "disk_path": "/home/user/dns-backup/dns.txt" }, "name": "Dosyayı diske kaydet", "description": "DNS ayarlarını diske kaydeder", "dependencies": ["task-2", "task-3"], "id": "task-4" }\n'
            )
            
            logger.info(f"System prompt oluşturuldu, uzunluk: {len(system_prompt)}")
            logger.info(f"System prompt içeriği: {system_prompt[:100]}...")  # İlk 100 karakter
            
            # Görev listesi oluştur
            try:
                tasks_data = provider.generate_tasks(
                    prompt,
                    model=model,
                    temperature=temperature,
                    system_prompt=system_prompt
                )
                logger.info(f"LLM yanıtı alındı: {json.dumps(tasks_data)[:200]}...")  # İlk 200 karakter
            except Exception as gen_err:
                logger.error(f"LLM yanıt üretme hatası: {str(gen_err)}")
                return {"error": f"LLM yanıt üretme hatası: {str(gen_err)}", "status": "error"}, 500
            
            # İşletim sistemi bilgisini ekle (eğer görev listesine eklemek istersen)
            tasks_data["os"] = platform.system()
            
            return {"data": tasks_data, "status": "success"}
        
        except Exception as e:
            import traceback
            logger.error(f"Görev oluşturma hatası: {str(e)}")
            logger.error(f"Hata detayları: {traceback.format_exc()}")
            return {"error": str(e), "status": "error"}, 500    
    
    def generate_text(self, **kwargs) -> Dict[str, Any]:
        """LLM kullanarak metin oluştur"""
        try:
            prompt = kwargs.get('prompt')
            if not prompt:
                return {"error": "Prompt gerekli", "status": "error"}, 400
            
            provider_type = kwargs.get('provider', 'openai')
            model = kwargs.get('model')
            temperature = kwargs.get('temperature', 0.7)
            system_prompt = kwargs.get('system_prompt', '')
            
            # Debug: Tüm parametreleri logla
            logger.info(f"LLM metin oluşturma isteği: provider={provider_type}, model={model}, system_prompt='{system_prompt}'")
            
            # Sağlayıcı örneğini al
            provider = self._get_provider(provider_type, **kwargs)
            
            # OpenAI sağlayıcısı için URL'i doğrula (eğer OpenAI ise)
            if provider_type == 'openai':
                if isinstance(provider, OpenAIProvider):
                    # URL kontrolü
                    logger.info(f"OpenAI base_url: {provider.base_url}")
                    
                    # Örnek olarak OpenAI istek verisini logla
                    messages = [{"role": "user", "content": prompt}]
                    if system_prompt:
                        messages = [{"role": "system", "content": system_prompt}] + messages
                    request_data = {
                        "model": model or "gpt-4o-mini",
                        "messages": messages,
                        "temperature": temperature
                    }
                    logger.info(f"OpenAI istek verisi: {json.dumps(request_data)}")
            
            # Metin oluştur
            text = provider.generate_text(
                prompt,
                model=model,
                temperature=temperature,
                system_prompt=system_prompt
            )
            
            return {"text": text, "status": "success"}
        
        except Exception as e:
            logger.error(f"Metin oluşturma hatası: {str(e)}")
            # Hata ayrıntılarını logla
            import traceback
            logger.error(f"Hata detayı: {traceback.format_exc()}")
            return {"error": str(e), "status": "error"}, 500
    
    def stream_start(self, **kwargs) -> Dict[str, Any]:
        """Stream başlat ve WebSocket ID döndür"""
        try:
            # WebSocket ID oluştur
            ws_id = str(uuid.uuid4())
            
            # Diğer parametreleri al
            prompt = kwargs.get('prompt')
            provider_type = kwargs.get('provider', 'openai')
            model = kwargs.get('model')
            temperature = kwargs.get('temperature', 0.7)
            system_prompt = kwargs.get('system_prompt', '')
            
            if not prompt:
                return {"error": "Prompt gerekli", "status": "error"}, 400
            
            # Sağlayıcı örneğini al
            provider = self._get_provider(provider_type, **kwargs)
            
            # Streaming desteği kontrolü
            if not provider.supports_streaming and provider_type not in ["webscraper", "webscraper_claude"]:
                return {
                    "error": f"{provider_type} sağlayıcısı streaming desteklemiyor",
                    "status": "error"
                }, 400
            
            # WebSocket bağlantı verisi oluştur
            ws_data = {
                "id": ws_id,
                "provider_type": provider_type,
                "model": model,
                "prompt": prompt,
                "temperature": temperature,
                "system_prompt": system_prompt
            }
            
            return {
                "ws_id": ws_id,
                "status": "success",
                "message": "Stream başlatıldı. WebSocket ID ile bağlantı kurun."
            }
        
        except Exception as e:
            logger.error(f"Stream başlatma hatası: {str(e)}")
            return {"error": str(e), "status": "error"}, 500
    
    def stream_stop(self, **kwargs) -> Dict[str, Any]:
        """Stream durdur"""
        try:
            ws_id = kwargs.get('ws_id')
            if not ws_id:
                return {"error": "WebSocket ID gerekli", "status": "error"}, 400
            
            # WebSocket bağlantısını kapat
            if ws_id in ws_connections:
                try:
                    ws_connections[ws_id].close()
                except Exception as e:
                    logger.warning(f"WebSocket kapatma hatası: {str(e)}")
                
                # Bağlantıyı sözlükten kaldır
                del ws_connections[ws_id]
                
                return {"status": "success", "message": "Stream durduruldu"}
            else:
                return {"status": "warning", "message": "WebSocket bağlantısı bulunamadı"}
        
        except Exception as e:
            logger.error(f"Stream durdurma hatası: {str(e)}")
            return {"error": str(e), "status": "error"}, 500
    
    def handle_ws_connection(self, ws, ws_id, data):
        """WebSocket bağlantısını işle"""
        try:
            # WebSocket bağlantısını sakla
            ws_connections[ws_id] = ws
            logger.info(f"WebSocket bağlantısında alınan veri: {json.dumps(data)}")
            # Sağlayıcı örneğini al
            provider = self._get_provider(data["provider_type"])
            
            # Streaming başlat
            threading.Thread(
                target=provider.generate_stream,
                args=(data["prompt"], ws_id),
                kwargs={
                    "model": data["model"],
                    "temperature": data["temperature"],
                    "system_prompt": data["system_prompt"]
                }
            ).start()
            
        except Exception as e:
            logger.error(f"WebSocket işleme hatası: {str(e)}")
            try:
                ws.send(json.dumps({
                    "type": "error",
                    "content": str(e)
                }))
            except:
                pass
    
    def get_models(self, **kwargs) -> Dict[str, Any]:
        """Kullanılabilir modelleri getir"""
        try:
            provider_type = kwargs.get('provider', 'openai')
            
            # Sağlayıcı örneğini al
            provider = self._get_provider(provider_type, **kwargs)
            
            # Modelleri al
            models = provider.get_available_models()
            
            return {"models": models, "status": "success"}
        
        except Exception as e:
            logger.error(f"Model listesi alınamadı: {str(e)}")
            return {"error": str(e), "models": [], "status": "error"}, 500
    
    def get_providers(self, **kwargs) -> Dict[str, Any]:
        """Desteklenen LLM sağlayıcılarını getir"""
        return {"providers": SUPPORTED_PROVIDERS, "status": "success"}
    
    def check_status(self, **kwargs) -> Dict[str, Any]:
        """LLM sağlayıcısının durumunu kontrol et"""
        provider_type = kwargs.get('provider', 'openai')
        
        if provider_type == "openai":
            # OpenAI API anahtarını kontrol et
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                return {
                    "status": "ready", 
                    "message": "OpenAI API anahtarı mevcut",
                    "provider_status": "success"
                }
            else:
                return {
                    "status": "not_configured", 
                    "message": "OpenAI API anahtarı bulunamadı",
                    "provider_status": "warning"
                }
        
        elif provider_type == "anthropic":
            # Anthropic API anahtarını kontrol et
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                return {
                    "status": "ready", 
                    "message": "Anthropic API anahtarı mevcut",
                    "provider_status": "success"
                }
            else:
                return {
                    "status": "not_configured", 
                    "message": "Anthropic API anahtarı bulunamadı",
                    "provider_status": "warning"
                }
        
        elif provider_type == "gemini":
            # Gemini API anahtarını kontrol et
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                return {
                    "status": "ready", 
                    "message": "Gemini API anahtarı mevcut",
                    "provider_status": "success"
                }
            else:
                return {
                    "status": "not_configured", 
                    "message": "Gemini API anahtarı bulunamadı",
                    "provider_status": "warning"
                }
        
        elif provider_type == "deepseek":
            # DeepSeek API anahtarını kontrol et
            api_key = os.getenv("DEEPSEEK_API_KEY")
            if api_key:
                return {
                    "status": "ready", 
                    "message": "DeepSeek API anahtarı mevcut",
                    "provider_status": "success"
                }
            else:
                return {
                    "status": "not_configured", 
                    "message": "DeepSeek API anahtarı bulunamadı",
                    "provider_status": "warning"
                }
        
        elif provider_type in ["ollama", "lmstudio"]:
            # Yerel LLM durumunu kontrol et
            status_data = self._check_local_llm_status(provider_type)
            return {
                "status": "ready" if status_data["running"] else "not_running",
                "message": status_data["message"],
                "available_models": status_data["available_models"],
                "provider_status": "success" if status_data["running"] else "error"
            }
        
        elif provider_type in ["webscraper", "webscraper_claude"]:
            # Web scraper durumunu kontrol et (basit kontrol)
            try:
                # Chrome sürücüsünün yüklü olup olmadığını kontrol et
                from selenium.webdriver.chrome.options import Options
                
                return {
                    "status": "ready", 
                    "message": "Web scraper kullanıma hazır",
                    "provider_status": "success"
                }
            except ImportError:
                return {
                    "status": "not_configured", 
                    "message": "Selenium veya webdriver yüklü değil",
                    "provider_status": "error"
                }
        
        else:
            return {
                "status": "unknown", 
                "message": f"Bilinmeyen sağlayıcı türü: {provider_type}",
                "provider_status": "error"
            }
    
    def setup_provider(self, **kwargs) -> Dict[str, Any]:
        """LLM sağlayıcısını yapılandır"""
        try:
            provider_type = kwargs.get('provider')
            if not provider_type:
                return {"error": "Sağlayıcı türü gerekli", "status": "error"}, 400
            
            # Mevcut sağlayıcıyı temizle
            if provider_type in self.llm_providers:
                del self.llm_providers[provider_type]
            
            # Sağlayıcıya özel yapılandırma
            if provider_type == "openai":
                api_key = kwargs.get('api_key')
                base_url = kwargs.get('base_url')
                
                if not api_key:
                    return {"error": "API anahtarı gerekli", "status": "error"}, 400
                
                # API anahtarını geçici olarak kaydet (gerçek uygulamada .env veya güvenli depolama kullanılmalı)
                os.environ["OPENAI_API_KEY"] = api_key
                if base_url:
                    os.environ["OPENAI_API_BASE"] = base_url
                
                # Sağlayıcıyı test et
                provider = LLMFactory.create_provider(provider_type, api_key=api_key, base_url=base_url)
                # Basit bir test
                models = provider.get_available_models()
                
                return {
                    "status": "configured",
                    "message": "OpenAI API yapılandırıldı",
                    "models": models,
                    "provider_status": "success"
                }
            
            elif provider_type == "anthropic":
                api_key = kwargs.get('api_key')
                
                if not api_key:
                    return {"error": "API anahtarı gerekli", "status": "error"}, 400
                
                # API anahtarını geçici olarak kaydet
                os.environ["ANTHROPIC_API_KEY"] = api_key
                
                # Sağlayıcıyı test et
                provider = LLMFactory.create_provider(provider_type, api_key=api_key)
                # Basit bir test - modelleri döndür
                models = provider.get_available_models()
                
                return {
                    "status": "configured",
                    "message": "Anthropic API yapılandırıldı",
                    "models": models,
                    "provider_status": "success"
                }
            
            elif provider_type == "gemini":
                api_key = kwargs.get('api_key')
                
                if not api_key:
                    return {"error": "API anahtarı gerekli", "status": "error"}, 400
                
                # API anahtarını geçici olarak kaydet
                os.environ["GEMINI_API_KEY"] = api_key
                
                # Sağlayıcıyı test et
                provider = LLMFactory.create_provider(provider_type, api_key=api_key)
                # Basit bir test - modelleri döndür
                models = provider.get_available_models()
                
                return {
                    "status": "configured",
                    "message": "Gemini API yapılandırıldı",
                    "models": models,
                    "provider_status": "success"
                }
            
            elif provider_type == "deepseek":
                api_key = kwargs.get('api_key')
                
                if not api_key:
                    return {"error": "API anahtarı gerekli", "status": "error"}, 400
                
                # API anahtarını geçici olarak kaydet
                os.environ["DEEPSEEK_API_KEY"] = api_key
                
                # Sağlayıcıyı test et
                provider = LLMFactory.create_provider(provider_type, api_key=api_key)
                # Basit bir test - modelleri döndür
                models = provider.get_available_models()
                
                return {
                    "status": "configured",
                    "message": "DeepSeek API yapılandırıldı",
                    "models": models,
                    "provider_status": "success"
                }
            
            elif provider_type in ["ollama", "lmstudio"]:
                base_url = kwargs.get('base_url')
                
                # Bağlantıyı test et
                status_data = self._check_local_llm_status(provider_type)
                
                if status_data["running"]:
                    # Sağlayıcıyı yükle
                    provider = LLMFactory.create_provider(provider_type, base_url=base_url)
                    self.llm_providers[provider_type] = provider
                    
                    # Base URL'i kaydet
                    if base_url:
                        if provider_type == "ollama":
                            os.environ["OLLAMA_API_BASE"] = base_url
                        elif provider_type == "lmstudio":
                            os.environ["LMSTUDIO_API_BASE"] = base_url
                    
                    return {
                        "status": "configured",
                        "message": f"{provider_type.capitalize()} başarıyla yapılandırıldı",
                        "available_models": status_data["available_models"],
                        "provider_status": "success"
                    }
                else:
                    return {
                        "status": "not_running",
                        "message": status_data["message"],
                        "provider_status": "error"
                    }, 400
            
            elif provider_type in ["webscraper", "webscraper_claude", "webscraper_deepseek"]:
                service_type = "chatgpt"
                if provider_type == "webscraper_claude":
                    service_type = "claude"
                elif provider_type == "webscraper_deepseek":
                    service_type = "deepseek"
                
                # Kullanıcı adı ve şifre parametrelerini al
                username = kwargs.get('username')
                password = kwargs.get('password')  

                # Web scraper'ı başlatmaya çalış
                try:
                    provider_params = {
                        "service_type": service_type,
                        "username": username, 
                        "password": password
                    }

                    provider = LLMFactory.create_provider("webscraper", **provider_params)
                    self.llm_providers["webscraper"] = provider
                    
                    login_success = provider._login() if username and password else False

                    return {
                        "status": "configured",
                        "message": f"Web scraper ({service_type}) başarıyla yapılandırıldı" + 
                                (", oturum açıldı" if login_success else ", oturum açılmadı"),
                        "provider_status": "success" if login_success else "warning"
                    }
                except Exception as e:
                    return {
                        "status": "error",
                        "message": f"Web scraper başlatılamadı: {str(e)}",
                        "provider_status": "error"
                    }, 400
            
            else:
                return {
                    "status": "error",
                    "message": f"Bilinmeyen sağlayıcı türü: {provider_type}",
                    "provider_status": "error"
                }, 400
        
        except Exception as e:
            logger.error(f"Sağlayıcı yapılandırma hatası: {str(e)}")
            return {"error": str(e), "status": "error"}, 500
    
    def _check_local_llm_status(self, provider: str) -> Dict[str, Union[bool, str, List]]:
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
    
    def shutdown(self):
        """Aracı kapat ve kaynakları temizle"""
        logger.info("LLM Tool kapatılıyor...")
        
        # Sağlayıcıların kaynaklarını temizle
        for provider_type, provider in self.llm_providers.items():
            # WebScraperLLM için browser oturumunu kapat
            if provider_type == "webscraper" and hasattr(provider, 'driver') and provider.driver:
                try:
                    provider.driver.quit()
                    logger.info("Web driver kapatıldı")
                except Exception as e:
                    logger.error(f"Web driver kapatılırken hata: {str(e)}")
        
        # WebSocket bağlantılarını kapat
        for ws_id, ws in ws_connections.items():
            try:
                ws.close()
            except:
                pass
        

# Sağlayıcı önbelleğini temizle
        self.llm_providers.clear()
        
        logger.info("LLM Tool kapatıldı")
        return True