#!/usr/bin/env python3
"""
Kullanıcı şifresini direkt veritabanında sıfırla
"""

import os
import sys
import chromadb
from chromadb.config import Settings as ChromaSettings
import hashlib
import secrets
import json

def reset_password_in_db():
    """Veritabanında şifreyi direkt sıfırla"""
    
    username = "ahmetb@minor.com.tr"
    new_password = "123456"
    
    print(f"🔧 Resetting password for: {username}")
    print(f"New password will be: {new_password}")
    
    # Şifre hash'i oluştur
    salt = secrets.token_hex(16)
    hash_obj = hashlib.pbkdf2_hmac(
        'sha256', 
        new_password.encode('utf-8'), 
        salt.encode('utf-8'), 
        100000
    )
    new_password_hash = f"{salt}${hash_obj.hex()}"
    
    print(f"New hash: {new_password_hash}")
    
    try:
        # ChromaDB bağlantısı
        db_path = "metis_data/chroma_db"
        client = chromadb.PersistentClient(
            path=db_path,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Users collection'ı al
        users_collection = client.get_collection("users")
        
        # Kullanıcıyı bul
        all_users = users_collection.get()
        user_found = False
        
        for i, (user_id, metadata) in enumerate(zip(all_users['ids'], all_users['metadatas'])):
            if metadata.get('username') == username:
                user_found = True
                
                print(f"✅ Found user: {user_id}")
                print(f"Old hash: {metadata.get('password_hash')}")
                
                # Metadata'yı güncelle
                updated_metadata = metadata.copy()
                updated_metadata['password_hash'] = new_password_hash
                updated_metadata['updated_at'] = '2025-07-07T14:40:00'
                
                # Kullanıcıyı sil ve yeniden ekle (ChromaDB update yöntemi)
                users_collection.delete(ids=[user_id])
                
                users_collection.add(
                    ids=[user_id],
                    documents=[username],
                    metadatas=[updated_metadata]
                )
                
                print(f"✅ Password updated successfully!")
                break
        
        if not user_found:
            print(f"❌ User not found: {username}")
            return False
        
        # Test the new password
        print(f"\n🔍 Testing new password...")
        
        # Import auth manager and test
        sys.path.insert(0, '.')
        from app.auth_manager import auth_manager
        
        result = auth_manager.authenticate_user(username, new_password)
        
        if result['status'] == 'success':
            print(f"✅ Login successful with new password!")
            print(f"   Session token: {result['session_token'][:20]}...")
            return True
        else:
            print(f"❌ Login failed: {result.get('message')}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    reset_password_in_db()