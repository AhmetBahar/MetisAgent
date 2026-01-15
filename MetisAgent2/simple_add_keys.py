"""
Basit API key ekleme scripti - manual input
"""

import os
import sys
import chromadb
from chromadb.config import Settings as ChromaSettings
import json
from datetime import datetime

def simple_encrypt(data):
    """Basit string encoding (gerçek uygulamada cryptography kullanın)"""
    import base64
    return base64.b64encode(data.encode()).decode()

def add_api_keys():
    """API keylerini manuel olarak ekler"""
    
    user_email = "ahmetb@minor.com.tr"
    db_path = "metis_data/chroma_db"
    
    print("=== Basit API Key Ekleme ===")
    print(f"Kullanıcı: {user_email}")
    print()
    
    # API keylerini buraya manuel girin
    api_keys = {
        # Gerçek API keylerini buraya girin
        "openai": "sk-proj-ACTUAL_OPENAI_KEY_HERE",
        "anthropic": "sk-ant-ACTUAL_ANTHROPIC_KEY_HERE", 
        "huggingface": "hf_ACTUAL_HUGGINGFACE_TOKEN_HERE",
        "google": "ACTUAL_GOOGLE_API_KEY_HERE",
        "facebook": "ACTUAL_FACEBOOK_TOKEN_HERE"
    }
    
    try:
        # ChromaDB bağlantısı
        client = chromadb.PersistentClient(
            path=db_path,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        collection = client.get_or_create_collection(
            name="user_settings",
            metadata={"hnsw:space": "cosine"}
        )
        
        added_count = 0
        
        for service, api_key in api_keys.items():
            if api_key and not api_key.startswith("ACTUAL_"):
                # API key'i encode et (basit yöntem)
                encoded_key = simple_encrypt(api_key)
                
                # Ek bilgiler
                additional_info = {}
                if service == "openai":
                    additional_info = {"models": ["gpt-4o", "gpt-4o-mini"], "default": "gpt-4o-mini"}
                elif service == "anthropic":
                    additional_info = {"models": ["claude-3-sonnet"], "default": "claude-3-sonnet"}
                
                encoded_additional = simple_encrypt(json.dumps(additional_info)) if additional_info else None
                
                # Metadata
                metadata = {
                    "user_id": user_email,
                    "service": service,
                    "type": "api_key",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
                
                # Data
                api_data = {
                    "encrypted_key": encoded_key,
                    "additional_info": encoded_additional
                }
                
                document_id = f"api_key_{user_email}_{service}"
                
                try:
                    collection.add(
                        ids=[document_id],
                        documents=[json.dumps(api_data)],
                        metadatas=[metadata]
                    )
                    print(f"✅ {service} API key eklendi")
                    added_count += 1
                except Exception as e:
                    # Update if exists
                    try:
                        collection.update(
                            ids=[document_id],
                            documents=[json.dumps(api_data)],
                            metadatas=[metadata]
                        )
                        print(f"🔄 {service} API key güncellendi")
                        added_count += 1
                    except Exception as e2:
                        print(f"❌ {service} eklenemedi: {e2}")
            else:
                print(f"⏭️  {service} atlandı (placeholder key)")
        
        print(f"\n🎉 Toplam {added_count} API key işlendi!")
        
    except Exception as e:
        print(f"❌ Hata: {e}")

if __name__ == "__main__":
    print("⚠️  DİKKAT: Bu script gerçek API keyler içermelidir!")
    print("api_keys dictionary'sindeki placeholder'ları gerçek keylerle değiştirin.\n")
    
    # Onay al
    if len(sys.argv) > 1 and sys.argv[1] == "--run":
        add_api_keys()
    else:
        print("Çalıştırmak için: python3 simple_add_keys.py --run")
        print("Önce scriptteki placeholder keylerini gerçek keylerle değiştirin!")