"""
Verify Migration - Check what credentials were actually migrated
"""

import sys
import asyncio
import sqlite3

sys.path.append('/home/ahmet/MetisAgent/MetisAgent3')
from core.storage import SQLiteUserStorage


async def main():
    storage = SQLiteUserStorage()
    
    print("🔍 VERIFYING METISAGENT3 MIGRATION")
    print("="*50)
    
    # Check users
    users = await storage.list_users(limit=20)
    print(f"📊 Total Users: {len(users)}")
    
    for user in users:
        print(f"\n👤 User: {user['email']} ({user['user_id']})")
        
        # Get user attributes
        attributes = await storage.get_user_attributes(user['user_id'])
        print(f"   📋 Attributes: {len(attributes)}")
        
        # Check for credentials
        oauth_count = 0
        api_key_count = 0
        password_count = 0
        
        for attr_name, attr_value in attributes.items():
            if attr_name.startswith('oauth_'):
                oauth_count += 1
                print(f"   🔑 OAuth: {attr_name}")
            elif attr_name.startswith('api_key_'):
                api_key_count += 1
                print(f"   🗝️  API Key: {attr_name}")
            elif 'password' in attr_name:
                password_count += 1
                print(f"   🔒 Password: {attr_name}")
        
        print(f"   📊 Credentials: OAuth({oauth_count}), API Keys({api_key_count}), Passwords({password_count})")
    
    # Check OAuth tokens table
    print(f"\n🔍 OAuth Tokens Table:")
    try:
        with storage.db.transaction() as conn:
            cursor = conn.execute("SELECT user_id, provider FROM oauth_tokens")
            oauth_tokens = cursor.fetchall()
            print(f"   📊 OAuth tokens in table: {len(oauth_tokens)}")
            for token in oauth_tokens:
                print(f"   🔑 {token['user_id']} → {token['provider']}")
    except Exception as e:
        print(f"   ❌ Error checking OAuth tokens: {e}")
    
    # Check encrypted attributes
    print(f"\n🔍 Encrypted Attributes:")
    try:
        with storage.db.transaction() as conn:
            cursor = conn.execute("""
                SELECT user_id, attribute_name 
                FROM user_attributes 
                WHERE is_encrypted = 1
            """)
            encrypted_attrs = cursor.fetchall()
            print(f"   📊 Encrypted attributes: {len(encrypted_attrs)}")
            for attr in encrypted_attrs:
                print(f"   🔐 {attr['user_id']} → {attr['attribute_name']}")
    except Exception as e:
        print(f"   ❌ Error checking encrypted attributes: {e}")
    
    print("\n" + "="*50)
    print("✅ Migration verification completed!")


if __name__ == "__main__":
    asyncio.run(main())