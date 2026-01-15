#!/usr/bin/env python3
"""
Debug token storage and user mappings
"""

import sys
import os

# Add MetisAgent2 to path
sys.path.append('/home/ahmet/MetisAgent/MetisAgent2')

def debug_token_storage():
    """Debug actual token storage"""
    
    print("🔍 Token Storage Debug")
    print("=" * 50)
    
    try:
        from tools.settings_manager import get_settings_manager
        from tools.user_storage import get_user_storage
        
        # Check settings manager
        print("\n📋 Settings Manager Check:")
        settings_manager = get_settings_manager()
        users = settings_manager.get_all_users()
        print(f"   Total users in settings: {len(users)}")
        
        for user_id in users:
            print(f"\n👤 User: {user_id}")
            
            # Check OAuth2 credentials
            oauth_creds = settings_manager.get_oauth2_credentials(user_id, 'google')
            if oauth_creds:
                print(f"   ✅ OAuth2 credentials found")
                print(f"      Access token: {str(oauth_creds.get('access_token', 'N/A'))[:20]}...")
                print(f"      Expires at: {oauth_creds.get('expires_at', 'N/A')}")
                print(f"      Scope: {oauth_creds.get('scope', 'N/A')}")
            else:
                print(f"   ❌ No OAuth2 credentials")
            
            # Check user mapping
            user_mapping = settings_manager.get_user_mapping(user_id, 'google')
            if user_mapping:
                print(f"   ✅ Google mapping: {user_mapping}")
            else:
                print(f"   ❌ No Google mapping")
        
        # Check user storage
        print(f"\n📋 User Storage Check:")
        user_storage = get_user_storage()
        storage_users = user_storage.list_users()
        print(f"   Total users in user_storage: {len(storage_users)}")
        
        for user_id in storage_users:
            print(f"\n👤 User Storage: {user_id}")
            
            # Check OAuth token
            oauth_token = user_storage.get_oauth_token(user_id, 'google')
            if oauth_token:
                print(f"   ✅ OAuth token found")
                print(f"      Access token: {str(oauth_token.get('access_token', 'N/A'))[:20]}...")
            else:
                print(f"   ❌ No OAuth token")
            
            # Check user mapping
            google_mapping = user_storage.get_user_mapping(user_id, 'google')
            if google_mapping:
                print(f"   ✅ Google mapping: {google_mapping}")
            else:
                print(f"   ❌ No Google mapping")
        
        # Test specific users from CLAUDE.md
        print(f"\n🎯 CLAUDE.md Users Check:")
        test_users = [
            "ahmetb@minor.com.tr",
            "ahmetbahar.minor@gmail.com", 
            "f75ba26d-0eb6-4f88-81de-96057fd6ed12"
        ]
        
        for user_id in test_users:
            print(f"\n🔍 Testing: {user_id}")
            
            # Settings manager
            oauth_creds = settings_manager.get_oauth2_credentials(user_id, 'google')
            user_map = settings_manager.get_user_mapping(user_id, 'google')
            print(f"   Settings OAuth: {'✅' if oauth_creds else '❌'}")
            print(f"   Settings Mapping: {'✅' if user_map else '❌'} ({user_map})")
            
            # User storage  
            oauth_token = user_storage.get_oauth_token(user_id, 'google')
            storage_map = user_storage.get_user_mapping(user_id, 'google')
            print(f"   Storage OAuth: {'✅' if oauth_token else '❌'}")
            print(f"   Storage Mapping: {'✅' if storage_map else '❌'} ({storage_map})")
        
    except Exception as e:
        print(f"❌ Debug error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_token_storage()