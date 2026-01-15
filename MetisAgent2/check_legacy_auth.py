#!/usr/bin/env python3
"""
Check legacy authentication system for user accounts
"""

import os
import sys
import chromadb
from chromadb.config import Settings as ChromaSettings

def check_legacy_auth():
    """Check legacy auth system for user accounts"""
    
    db_path = "metis_data/chroma_db"
    
    try:
        # ChromaDB client
        client = chromadb.PersistentClient(
            path=db_path,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        print("🔍 Legacy Authentication System Check:")
        print(f"Database path: {db_path}")
        print()
        
        # List all collections
        collections = client.list_collections()
        print(f"📋 Available collections ({len(collections)} total):")
        for collection in collections:
            print(f"  - {collection.name}")
        print()
        
        # Check users collection
        if any(c.name == "users" for c in collections):
            users_collection = client.get_collection("users")
            all_users = users_collection.get()
            
            print(f"👥 Users collection ({len(all_users['ids'])} users):")
            
            target_user = None
            for i, (user_id, metadata) in enumerate(zip(all_users['ids'], all_users['metadatas'])):
                username = metadata.get('username', 'Unknown')
                email = metadata.get('email', 'Unknown') 
                status = metadata.get('status', 'Unknown')
                created = metadata.get('created_at', 'Unknown')[:19] if metadata.get('created_at') else 'Unknown'
                
                print(f"  {i+1}. {username} ({email}) - {status}")
                print(f"     ID: {user_id}")
                print(f"     Created: {created}")
                
                if email == "ahmet@minor.com.tr" or username == "ahmet@minor.com.tr":
                    target_user = (user_id, metadata)
                    
                print()
            
            if target_user:
                user_id, metadata = target_user
                print(f"✅ Target user found!")
                print(f"   User ID: {user_id}")
                print(f"   Username: {metadata.get('username')}")
                print(f"   Email: {metadata.get('email')}")
                print(f"   Status: {metadata.get('status')}")
                print(f"   Permissions: {metadata.get('permissions')}")
                return user_id
            else:
                print(f"❌ ahmet@minor.com.tr not found in users collection")
        else:
            print("❌ No 'users' collection found")
        
        # Check api_keys collection
        if any(c.name == "api_keys" for c in collections):
            api_keys_collection = client.get_collection("api_keys")
            all_keys = api_keys_collection.get()
            
            print(f"🔑 API Keys collection ({len(all_keys['ids'])} keys):")
            for i, (key_id, metadata) in enumerate(zip(all_keys['ids'], all_keys['metadatas'])):
                user_id = metadata.get('user_id', 'Unknown')
                created = metadata.get('created_at', 'Unknown')[:19] if metadata.get('created_at') else 'Unknown'
                status = metadata.get('status', 'Unknown')
                
                print(f"  {i+1}. Key for user: {user_id}")
                print(f"     Status: {status}")
                print(f"     Created: {created}")
                print()
        else:
            print("❌ No 'api_keys' collection found")
            
        # Check sessions collection
        if any(c.name == "sessions" for c in collections):
            sessions_collection = client.get_collection("sessions")
            all_sessions = sessions_collection.get()
            
            print(f"🔐 Sessions collection ({len(all_sessions['ids'])} sessions):")
            for i, (session_id, metadata) in enumerate(zip(all_sessions['ids'], all_sessions['metadatas'])):
                user_id = metadata.get('user_id', 'Unknown')
                created = metadata.get('created_at', 'Unknown')[:19] if metadata.get('created_at') else 'Unknown'
                status = metadata.get('status', 'Unknown')
                
                print(f"  {i+1}. Session for user: {user_id}")
                print(f"     Status: {status}")
                print(f"     Created: {created}")
                print()
        else:
            print("❌ No 'sessions' collection found")
            
        return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    check_legacy_auth()