"""
API Keys ekleme scripti - ahmetb@minor.com.tr kullanıcısı için
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.settings_manager import settings_manager

def add_user_api_keys():
    """Kullanıcı API keylerini ekler"""
    
    user_email = "ahmetb@minor.com.tr"
    print(f"API keys ekleniyor: {user_email}")
    
    # API keylerini buraya ekleyin (gerçek keyler yerine placeholder'lar)
    api_keys = {
        "openai": {
            "key": "sk-proj-PLACEHOLDER_OPENAI_KEY",  # Gerçek key'i buraya
            "additional_info": {
                "model_preferences": ["gpt-4o", "gpt-4o-mini"],
                "default_model": "gpt-4o-mini",
                "usage_limit": "unlimited"
            }
        },
        "anthropic": {
            "key": "sk-ant-PLACEHOLDER_ANTHROPIC_KEY",  # Gerçek key'i buraya
            "additional_info": {
                "model_preferences": ["claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
                "default_model": "claude-3-sonnet-20240229",
                "usage_limit": "unlimited"
            }
        },
        "google": {
            "key": "PLACEHOLDER_GOOGLE_API_KEY",  # Gerçek key'i buraya
            "additional_info": {
                "services": ["gemini-pro", "palm-2", "imagen"],
                "default_model": "gemini-pro",
                "region": "us-central1"
            }
        },
        "gemini": {
            "key": "PLACEHOLDER_GEMINI_API_KEY",  # Gerçek key'i buraya
            "additional_info": {
                "model_preferences": ["gemini-1.5-pro", "gemini-1.5-flash"],
                "default_model": "gemini-1.5-pro",
                "image_generation": True
            }
        },
        "huggingface": {
            "key": "hf_PLACEHOLDER_HF_TOKEN",  # Gerçek key'i buraya
            "additional_info": {
                "organization": "huggingface",
                "access_level": "read",
                "models": ["stable-diffusion", "llama2"]
            }
        }
    }
    
    # Her API key'i ekle
    for service, config in api_keys.items():
        try:
            success = settings_manager.save_api_key(
                user_email, 
                service, 
                config["key"], 
                config["additional_info"]
            )
            
            if success:
                print(f"✅ {service} API key başarıyla eklendi")
            else:
                print(f"❌ {service} API key eklenemedi")
                
        except Exception as e:
            print(f"❌ {service} API key ekleme hatası: {e}")
    
    # Eklenen API keyleri listele
    print(f"\n📋 {user_email} kullanıcısının API keyleri:")
    try:
        user_keys = settings_manager.list_user_api_keys(user_email)
        for key_info in user_keys:
            print(f"  - {key_info['service']}: ✅ (Eklendi: {key_info['created_at'][:10]})")
    except Exception as e:
        print(f"❌ API key listesi alınamadı: {e}")

def check_existing_keys():
    """Mevcut API keyleri kontrol eder"""
    user_email = "ahmetb@minor.com.tr"
    
    print(f"🔍 Mevcut API keyler kontrol ediliyor: {user_email}")
    
    try:
        user_keys = settings_manager.list_user_api_keys(user_email)
        if user_keys:
            print("📋 Bulunan API keyler:")
            for key_info in user_keys:
                print(f"  - {key_info['service']}: ✅ (Eklendi: {key_info['created_at'][:10]})")
        else:
            print("📭 Henüz API key bulunmuyor")
            
    except Exception as e:
        print(f"❌ API key kontrolü hatası: {e}")

if __name__ == "__main__":
    print("=== API Key Yönetimi ===")
    print("1. Mevcut keyleri kontrol et")
    print("2. API keyleri ekle")
    
    choice = input("\nSeçiminiz (1/2): ").strip()
    
    if choice == "1":
        check_existing_keys()
    elif choice == "2":
        print("\n⚠️  DİKKAT: Bu script placeholder keyler içeriyor!")
        print("Gerçek API keylerini add_api_keys.py dosyasına manuel olarak ekleyin.")
        
        confirm = input("Devam etmek istiyor musunuz? (y/N): ").strip().lower()
        if confirm == 'y':
            add_user_api_keys()
        else:
            print("İşlem iptal edildi.")
    else:
        print("Geçersiz seçim!")