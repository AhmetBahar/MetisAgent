#!/usr/bin/env python3
"""
Test login for ahmetb@minor.com.tr
"""

import os
import sys

# Add the current directory to the path
sys.path.insert(0, '.')

from app.auth_manager import auth_manager

def test_login():
    """Test login for existing user"""
    
    username = "ahmetb@minor.com.tr"
    
    print(f"🔍 Testing login for user: {username}")
    
    # Check if user exists
    user = auth_manager.get_user(username)
    if user:
        print(f"✅ User found in legacy system:")
        print(f"   Username: {user['username']}")
        print(f"   Email: {user['email']}")
        print(f"   User ID: {user['user_id']}")
        print(f"   Status: {user['status']}")
        print(f"   Permissions: {user['permissions']}")
        
        # Check sessions
        print(f"\n🔐 Checking active sessions...")
        from app.database import db_manager
        all_sessions = db_manager.sessions_collection.get()
        
        user_sessions = 0
        for metadata in all_sessions['metadatas']:
            if metadata.get('user_id') == user['user_id']:
                user_sessions += 1
        
        print(f"   Active sessions: {user_sessions}")
        
        # Test API key access from settings
        print(f"\n🔑 Testing API key access:")
        from tools.settings_manager import SettingsManager
        settings_manager = SettingsManager()
        
        for service in ['openai', 'anthropic', 'huggingface']:
            api_key_data = settings_manager.get_api_key(username, service)
            if api_key_data:
                print(f"   ✅ {service}: Available")
            else:
                print(f"   ❌ {service}: Not found")
                
        print(f"\n✅ User {username} is ready for authentication")
        print("🔄 You can now:")
        print("   1. Use legacy login with password")
        print("   2. Use Google OAuth (if configured)")
        print("   3. Access API keys from database")
        
    else:
        print(f"❌ User not found: {username}")

if __name__ == "__main__":
    test_login()