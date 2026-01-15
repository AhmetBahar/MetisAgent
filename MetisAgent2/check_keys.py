"""
Basit API key kontrol scripti
"""

import os
import sys
import chromadb
from chromadb.config import Settings as ChromaSettings

def check_user_keys():
    """Kullanıcının mevcut API keylerini kontrol eder"""
    
    user_email = "ahmet@minor.com.tr"
    db_path = "metis_data/chroma_db"
    
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
        
        print(f"🔍 {user_email} kullanıcısının API keyleri kontrol ediliyor...")
        
        # Tüm kayıtları getir
        try:
            results = collection.get(
                where={"$and": [{"user_id": user_email}, {"type": "api_key"}]}
            )
        except:
            # Fallback: tüm kayıtları getir ve filtrele
            all_results = collection.get()
            results = {"ids": [], "metadatas": [], "documents": []}
            
            for i, metadata in enumerate(all_results['metadatas']):
                if (metadata.get('user_id') == user_email and 
                    metadata.get('type') == 'api_key'):
                    results['ids'].append(all_results['ids'][i])
                    results['metadatas'].append(metadata)
                    results['documents'].append(all_results['documents'][i])
        
        if results['ids']:
            print(f"📋 Bulunan API keyler ({len(results['ids'])} adet):")
            for i, doc_id in enumerate(results['ids']):
                metadata = results['metadatas'][i]
                service = metadata.get('service', 'Unknown')
                created_at = metadata.get('created_at', 'Unknown')[:10]
                print(f"  - {service}: ✅ (Eklendi: {created_at})")
        else:
            print("📭 Henüz API key bulunmuyor")
            
        # Kullanıcı ayarlarını da kontrol et
        try:
            user_settings_results = collection.get(
                where={"$and": [{"user_id": user_email}, {"type": "user_settings"}]}
            )
        except:
            # Fallback: tüm kayıtları getir ve filtrele
            all_results = collection.get()
            user_settings_results = {"ids": [], "metadatas": [], "documents": []}
            
            for i, metadata in enumerate(all_results['metadatas']):
                if (metadata.get('user_id') == user_email and 
                    metadata.get('type') == 'user_settings'):
                    user_settings_results['ids'].append(all_results['ids'][i])
                    user_settings_results['metadatas'].append(metadata)
                    user_settings_results['documents'].append(all_results['documents'][i])
        
        if user_settings_results['ids']:
            print(f"\n⚙️  Kullanıcı ayarları mevcut")
        else:
            print(f"\n⚙️  Kullanıcı ayarları henüz oluşturulmamış")
            
    except Exception as e:
        print(f"❌ Hata: {e}")

if __name__ == "__main__":
    check_user_keys()