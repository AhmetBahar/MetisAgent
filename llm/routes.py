# llm/routes.py
from flask import Blueprint, request, jsonify
from llm.integrations import LLMFactory, SUPPORTED_PROVIDERS, check_local_llm_status
import logging
import os
from dotenv import load_dotenv

# .env dosyasından API anahtarlarını yükle
load_dotenv()

# Logger yapılandırması
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Blueprint oluştur
llm_bp = Blueprint('llm', __name__, url_prefix='/api/llm')

# LLM sağlayıcılarını saklama
llm_providers = {}

@llm_bp.route('/generate-tasks', methods=['POST'])
def generate_tasks():
    """LLM kullanarak görev listesi oluştur"""
    data = request.json
    
    if not data or 'prompt' not in data:
        return jsonify({"error": "Prompt gerekli"}), 400
    
    prompt = data.get('prompt')
    provider_type = data.get('provider', 'openai')
    model = data.get('model')
    
    # Diğer parametreler
    temperature = data.get('temperature', 0.2)
    
    try:
        # Sağlayıcı örneğini al veya oluştur
        if provider_type not in llm_providers:
            # Sağlayıcıya özel parametre ayarları
            provider_params = {}
            
            if provider_type == "openai":
                api_key = data.get('api_key') or os.getenv("OPENAI_API_KEY")
                provider_params["api_key"] = api_key
            
            elif provider_type == "webscraper":
                service_type = data.get('service_type', 'chatgpt')
                provider_params["service_type"] = service_type
            
            elif provider_type in ["ollama", "lmstudio"]:
                base_url = data.get('base_url')
                if base_url:
                    provider_params["base_url"] = base_url
            
            # Sağlayıcıyı oluştur
            llm_providers[provider_type] = LLMFactory.create_provider(provider_type, **provider_params)
        
        # Sağlayıcı örneğini al
        provider = llm_providers[provider_type]
        
        # Görev listesi oluştur
        tasks_data = provider.generate_tasks(
            prompt,
            model=model,
            temperature=temperature
        )
        
        return jsonify(tasks_data)
    
    except Exception as e:
        logger.error(f"Görev oluşturma hatası: {str(e)}")
        return jsonify({"error": str(e)}), 500

@llm_bp.route('/generate-text', methods=['POST'])
def generate_text():
    """LLM kullanarak metin oluştur"""
    data = request.json
    
    if not data or 'prompt' not in data:
        return jsonify({"error": "Prompt gerekli"}), 400
    
    prompt = data.get('prompt')
    provider_type = data.get('provider', 'openai')
    model = data.get('model')
    
    # Diğer parametreler
    temperature = data.get('temperature', 0.7)
    
    try:
        # Sağlayıcı örneğini al veya oluştur
        if provider_type not in llm_providers:
            # Sağlayıcıya özel parametre ayarları
            provider_params = {}
            
            if provider_type == "openai":
                api_key = data.get('api_key') or os.getenv("OPENAI_API_KEY")
                provider_params["api_key"] = api_key
            
            elif provider_type == "webscraper":
                service_type = data.get('service_type', 'chatgpt')
                provider_params["service_type"] = service_type
            
            elif provider_type in ["ollama", "lmstudio"]:
                base_url = data.get('base_url')
                if base_url:
                    provider_params["base_url"] = base_url
            
            # Sağlayıcıyı oluştur
            llm_providers[provider_type] = LLMFactory.create_provider(provider_type, **provider_params)
        
        # Sağlayıcı örneğini al
        provider = llm_providers[provider_type]
        
        # Metin oluştur
        text = provider.generate_text(
            prompt,
            model=model,
            temperature=temperature
        )
        
        return jsonify({"text": text})
    
    except Exception as e:
        logger.error(f"Metin oluşturma hatası: {str(e)}")
        return jsonify({"error": str(e)}), 500

@llm_bp.route('/models', methods=['GET'])
def get_models():
    """Kullanılabilir modelleri getir"""
    provider_type = request.args.get('provider', 'openai')
    
    try:
        # Sağlayıcı örneğini al veya oluştur
        if provider_type not in llm_providers:
            # Sağlayıcıya özel parametre ayarları
            provider_params = {}
            
            if provider_type == "openai":
                api_key = os.getenv("OPENAI_API_KEY")
                provider_params["api_key"] = api_key
            
            elif provider_type in ["ollama", "lmstudio"]:
                # Varsayılan yapılandırma
                pass
            
            # Sağlayıcıyı oluştur
            llm_providers[provider_type] = LLMFactory.create_provider(provider_type, **provider_params)
        
        # Sağlayıcı örneğini al
        provider = llm_providers[provider_type]
        
        # Modelleri al
        models = provider.get_available_models()
        
        return jsonify({"models": models})
    
    except Exception as e:
        logger.error(f"Model listesi alınamadı: {str(e)}")
        return jsonify({"error": str(e), "models": []}), 500

@llm_bp.route('/providers', methods=['GET'])
def get_providers():
    """Desteklenen LLM sağlayıcılarını getir"""
    return jsonify({"providers": SUPPORTED_PROVIDERS})

@llm_bp.route('/status', methods=['GET'])
def check_status():
    """LLM sağlayıcısının durumunu kontrol et"""
    provider_type = request.args.get('provider', 'openai')
    
    if provider_type == "openai":
        # OpenAI API anahtarını kontrol et
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            return jsonify({"status": "ready", "message": "OpenAI API anahtarı mevcut"})
        else:
            return jsonify({"status": "not_configured", "message": "OpenAI API anahtarı bulunamadı"})
    
    elif provider_type in ["ollama", "lmstudio"]:
        # Yerel LLM durumunu kontrol et
        status_data = check_local_llm_status(provider_type)
        return jsonify({
            "status": "ready" if status_data["running"] else "not_running",
            "message": status_data["message"],
            "available_models": status_data["available_models"]
        })
    
    elif provider_type == "webscraper":
        # Web scraper durumunu kontrol et (basit kontrol)
        try:
            # Chrome sürücüsünün yüklü olup olmadığını kontrol et
            from selenium.webdriver.chrome.options import Options
            
            return jsonify({
                "status": "ready", 
                "message": "Web scraper kullanıma hazır"
            })
        except ImportError:
            return jsonify({
                "status": "not_configured", 
                "message": "Selenium veya webdriver yüklü değil"
            })
    
    else:
        return jsonify({
            "status": "unknown", 
            "message": f"Bilinmeyen sağlayıcı türü: {provider_type}"
        })

@llm_bp.route('/setup', methods=['POST'])
def setup_provider():
    """LLM sağlayıcısını yapılandır"""
    data = request.json
    
    if not data or 'provider' not in data:
        return jsonify({"error": "Sağlayıcı türü gerekli"}), 400
    
    provider_type = data.get('provider')
    
    try:
        # Mevcut sağlayıcıyı temizle
        if provider_type in llm_providers:
            del llm_providers[provider_type]
        
        # Sağlayıcıya özel yapılandırma
        if provider_type == "openai":
            api_key = data.get('api_key')
            if not api_key:
                return jsonify({"error": "API anahtarı gerekli"}), 400
            
            # API anahtarını geçici olarak kaydet (gerçek uygulamada .env veya güvenli depolama kullanılmalı)
            os.environ["OPENAI_API_KEY"] = api_key
            
            # Sağlayıcıyı test et
            provider = LLMFactory.create_provider(provider_type, api_key=api_key)
            # Basit bir test
            models = provider.get_available_models()
            
            return jsonify({
                "status": "configured",
                "message": "OpenAI API yapılandırıldı",
                "models": models
            })
        
        elif provider_type in ["ollama", "lmstudio"]:
            base_url = data.get('base_url')
            
            # Bağlantıyı test et
            status_data = check_local_llm_status(provider_type)
            
            if status_data["running"]:
                # Sağlayıcıyı yükle
                provider = LLMFactory.create_provider(provider_type, base_url=base_url)
                llm_providers[provider_type] = provider
                
                return jsonify({
                    "status": "configured",
                    "message": f"{provider_type.capitalize()} başarıyla yapılandırıldı",
                    "available_models": status_data["available_models"]
                })
            else:
                return jsonify({
                    "status": "not_running",
                    "message": status_data["message"]
                }), 400
        
        elif provider_type == "webscraper":
            service_type = data.get('service_type', 'chatgpt')
            
            # Web scraper'ı başlatmaya çalış
            try:
                provider = LLMFactory.create_provider(provider_type, service_type=service_type)
                llm_providers[provider_type] = provider
                
                return jsonify({
                    "status": "configured",
                    "message": "Web scraper başarıyla yapılandırıldı"
                })
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": f"Web scraper başlatılamadı: {str(e)}"
                }), 400
        
        else:
            return jsonify({
                "status": "error",
                "message": f"Bilinmeyen sağlayıcı türü: {provider_type}"
            }), 400
    
    except Exception as e:
        logger.error(f"Sağlayıcı yapılandırma hatası: {str(e)}")
        return jsonify({"error": str(e)}), 500