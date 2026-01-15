"""
Tüm kullanıcıları ve auth sistemini kontrol et
"""

import os
import chromadb
from chromadb.config import Settings as ChromaSettings

def check_all_users():
    """Tüm kullanıcıları listeler"""
    
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
        
        print("📋 ChromaDB'deki tüm kayıtlar:")
        
        # Tüm kayıtları getir
        all_results = collection.get()
        
        if not all_results['ids']:
            print("📭 ChromaDB boş")
            return
        
        users = set()
        api_keys = {}
        settings = {}
        
        for i, metadata in enumerate(all_results['metadatas']):
            user_id = metadata.get('user_id', 'Unknown')
            record_type = metadata.get('type', 'Unknown')
            service = metadata.get('service', '')
            
            users.add(user_id)
            
            if record_type == 'api_key':
                if user_id not in api_keys:
                    api_keys[user_id] = []
                api_keys[user_id].append(service)
            elif record_type == 'user_settings':
                settings[user_id] = True
        
        print(f"\n👥 Bulunan kullanıcılar ({len(users)} adet):")
        for user in sorted(users):
            print(f"\n🔹 {user}")
            
            # API keyleri
            if user in api_keys:
                print(f"   🔑 API Keys: {', '.join(api_keys[user])}")
            else:
                print(f"   🔑 API Keys: Yok")
            
            # Settings
            if user in settings:
                print(f"   ⚙️  Settings: Mevcut")
            else:
                print(f"   ⚙️  Settings: Yok")
        
        # Detayları göster
        print(f"\n📄 Detaylı kayıtlar:")
        for i, doc_id in enumerate(all_results['ids']):
            metadata = all_results['metadatas'][i]
            print(f"  {i+1}. {doc_id}")
            print(f"     User: {metadata.get('user_id', 'Unknown')}")
            print(f"     Type: {metadata.get('type', 'Unknown')}")
            if metadata.get('service'):
                print(f"     Service: {metadata.get('service')}")
            print(f"     Created: {metadata.get('created_at', 'Unknown')[:19]}")
            print()
            
    except Exception as e:
        print(f"❌ Hata: {e}")

if __name__ == "__main__":
    check_all_users()