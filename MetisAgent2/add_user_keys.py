"""
Manuel API key ekleme scripti
"""

import json
import os
from datetime import datetime
import base64
from cryptography.fernet import Fernet

def get_encryption_key():
    """Şifreleme anahtarını al veya oluştur"""
    key_file = "metis_data/chroma_db/encryption.key"
    
    if os.path.exists(key_file):
        with open(key_file, 'rb') as f:
            return f.read()
    else:
        # Yeni anahtar oluştur
        key = Fernet.generate_key()
        os.makedirs(os.path.dirname(key_file), exist_ok=True)
        with open(key_file, 'wb') as f:
            f.write(key)
        return key

def encrypt_data(data, key):
    """Veriyi şifreler"""
    fernet = Fernet(key)
    encrypted = fernet.encrypt(data.encode())
    return base64.b64encode(encrypted).decode()

def add_api_keys_manually():
    """Manuel olarak API keylerini ekler"""
    
    user_email = "ahmetb@minor.com.tr"
    
    print("=== API Key Ekleme Aracı ===")
    print(f"Kullanıcı: {user_email}")
    print("\nLütfen API keylerini girin (boş bırakmak için Enter'a basın):\n")
    
    # API key bilgilerini al
    api_keys = {}
    
    services = {
        "openai": "OpenAI API Key (sk-...)",
        "anthropic": "Anthropic API Key (sk-ant-...)",
        "huggingface": "HuggingFace Token (hf_...)",
        "google": "Google API Key",
        "facebook": "Facebook/Meta API Token"
    }
    
    for service, description in services.items():
        key = input(f"{description}: ").strip()
        if key:
            api_keys[service] = key
    
    if not api_keys:
        print("Hiç API key girilmedi!")
        return
    
    # Şifreleme anahtarını al
    encryption_key = get_encryption_key()
    
    # Her API key için JSON dosyası oluştur
    for service, api_key in api_keys.items():
        try:
            # API key verisini şifrele
            encrypted_key = encrypt_data(api_key, encryption_key)
            
            # Ek bilgiler
            additional_info = {}
            if service == "openai":
                additional_info = {
                    "models": ["gpt-4o", "gpt-4o-mini", "gpt-4"],
                    "default_model": "gpt-4o-mini",
                    "image_generation": True
                }
            elif service == "anthropic":
                additional_info = {
                    "models": ["claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
                    "default_model": "claude-3-sonnet-20240229"
                }
            elif service == "huggingface":
                additional_info = {
                    "organization": "huggingface",
                    "access_level": "read",
                    "models": ["stable-diffusion", "llama2"]
                }
            elif service == "google":
                additional_info = {
                    "services": ["gemini-pro", "palm-2", "imagen"],
                    "default_model": "gemini-pro"
                }
            elif service == "facebook":
                additional_info = {
                    "platform": "meta",
                    "access_level": "user"
                }
            
            encrypted_additional = encrypt_data(json.dumps(additional_info), encryption_key) if additional_info else None
            
            # Metadata
            metadata = {
                "user_id": user_email,
                "service": service,
                "type": "api_key",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # API data
            api_data = {
                "encrypted_key": encrypted_key,
                "additional_info": encrypted_additional
            }
            
            # Dosya adı
            document_id = f"api_key_{user_email}_{service}"
            
            # JSON dosyasını kaydet
            output_dir = "metis_data/manual_keys"
            os.makedirs(output_dir, exist_ok=True)
            
            # Metadata dosyası
            with open(f"{output_dir}/{document_id}_metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Data dosyası  
            with open(f"{output_dir}/{document_id}_data.json", 'w') as f:
                json.dump(api_data, f, indent=2)
            
            print(f"✅ {service} API key kaydedildi")
            
        except Exception as e:
            print(f"❌ {service} API key kaydedilemedi: {e}")
    
    print(f"\n📁 Dosyalar şuraya kaydedildi: {output_dir}/")
    print("Bu dosyaları ChromaDB'ye manuel olarak import edebilirsiniz.")

if __name__ == "__main__":
    add_api_keys_manually()