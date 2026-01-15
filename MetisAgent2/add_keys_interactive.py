"""
İnteraktif API key ekleme scripti
"""

import sys
import os
import chromadb
from chromadb.config import Settings as ChromaSettings
import json
from datetime import datetime
import base64
from cryptography.fernet import Fernet
import getpass

def get_encryption_key(db_path):
    """Şifreleme anahtarını al veya oluştur"""
    key_file = os.path.join(db_path, "encryption.key")
    
    if os.path.exists(key_file):
        with open(key_file, 'rb') as f:
            return f.read()
    else:
        # Yeni anahtar oluştur
        key = Fernet.generate_key()
        os.makedirs(os.path.dirname(key_file), exist_ok=True)
        with open(key_file, 'wb') as f:
            f.write(key)
        print(f"✅ Yeni şifreleme anahtarı oluşturuldu: {key_file}")
        return key

def encrypt_data(data, key):
    """Veriyi şifreler"""
    fernet = Fernet(key)
    encrypted = fernet.encrypt(data.encode())
    return base64.b64encode(encrypted).decode()

def add_api_key_to_db(collection, user_id, service, api_key, additional_info, encryption_key):
    """API key'i veritabanına ekler"""
    
    # API key'i şifrele
    encrypted_key = encrypt_data(api_key, encryption_key)
    
    # Ek bilgileri de şifrele
    if additional_info:
        additional_encrypted = encrypt_data(json.dumps(additional_info), encryption_key)
    else:
        additional_encrypted = None
    
    # Metadata
    metadata = {
        "user_id": user_id,
        "service": service,
        "type": "api_key",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    # ChromaDB'ye kaydet
    document_id = f"api_key_{user_id}_{service}"
    
    api_data = {
        "encrypted_key": encrypted_key,
        "additional_info": additional_encrypted
    }
    
    try:
        existing = collection.get(ids=[document_id])
        if existing['ids']:
            # Güncelle
            collection.update(
                ids=[document_id],
                documents=[json.dumps(api_data)],
                metadatas=[metadata]
            )
            print(f"🔄 {service} API key güncellendi")
        else:
            # Yeni kayıt
            collection.add(
                ids=[document_id],
                documents=[json.dumps(api_data)],
                metadatas=[metadata]
            )
            print(f"✅ {service} API key eklendi")
    except:
        # Yeni kayıt
        collection.add(
            ids=[document_id],
            documents=[json.dumps(api_data)],
            metadatas=[metadata]
        )
        print(f"✅ {service} API key eklendi")

def main():
    """Ana fonksiyon"""
    
    user_email = "ahmetb@minor.com.tr"
    db_path = "metis_data/chroma_db"
    
    print("=== API Key Ekleme Aracı ===")
    print(f"Kullanıcı: {user_email}")
    print()
    
    try:
        # ChromaDB bağlantısı
        client = chromadb.PersistentClient(
            path=db_path,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Settings collection'ı al
        collection = client.get_or_create_collection(
            name="user_settings",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Şifreleme anahtarını al
        encryption_key = get_encryption_key(db_path)
        
        # API keylerini tanımla
        services = {
            "openai": {
                "name": "OpenAI",
                "description": "OpenAI API Key (sk-...)",
                "additional_info": {
                    "models": ["gpt-4o", "gpt-4o-mini", "gpt-4"],
                    "default_model": "gpt-4o-mini",
                    "image_generation": True
                }
            },
            "anthropic": {
                "name": "Anthropic",
                "description": "Anthropic API Key (sk-ant-...)",
                "additional_info": {
                    "models": ["claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
                    "default_model": "claude-3-sonnet-20240229"
                }
            },
            "huggingface": {
                "name": "HuggingFace",
                "description": "HuggingFace Token (hf_...)",
                "additional_info": {
                    "organization": "huggingface",
                    "access_level": "read",
                    "models": ["stable-diffusion", "llama2"]
                }
            },
            "google": {
                "name": "Google",
                "description": "Google API Key",
                "additional_info": {
                    "services": ["gemini-pro", "palm-2", "imagen"],
                    "default_model": "gemini-pro"
                }
            },
            "facebook": {
                "name": "Facebook/Meta",
                "description": "Facebook/Meta API Token",
                "additional_info": {
                    "platform": "meta",
                    "access_level": "user"
                }
            }
        }
        
        # Her servis için API key iste
        added_count = 0
        for service_id, service_info in services.items():
            print(f"📝 {service_info['name']} API Key")
            api_key = getpass.getpass(f"   {service_info['description']} (Enter ile geç): ")
            
            if api_key.strip():
                add_api_key_to_db(
                    collection, 
                    user_email, 
                    service_id, 
                    api_key.strip(), 
                    service_info['additional_info'], 
                    encryption_key
                )
                added_count += 1
            else:
                print(f"   ⏭️  Atlandı")
            print()
        
        print(f"🎉 Toplam {added_count} API key eklendi/güncellendi!")
        
        # Son durumu göster
        print("\n📋 Mevcut API keyler:")
        try:
            all_results = collection.get()
            api_keys = []
            
            for i, metadata in enumerate(all_results['metadatas']):
                if (metadata.get('user_id') == user_email and 
                    metadata.get('type') == 'api_key'):
                    service = metadata.get('service', 'Unknown')
                    created_at = metadata.get('created_at', 'Unknown')[:10]
                    api_keys.append(f"  - {service}: ✅ (Eklendi: {created_at})")
            
            if api_keys:
                for key_info in api_keys:
                    print(key_info)
            else:
                print("  Henüz API key yok")
                
        except Exception as e:
            print(f"❌ API key listesi alınamadı: {e}")
            
    except Exception as e:
        print(f"❌ Hata: {e}")

if __name__ == "__main__":
    main()