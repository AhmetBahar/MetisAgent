#!/usr/bin/env python3
"""
Check for actual Google OAuth credentials in the system
This will help determine if the client ID/secret are correct
"""

import sys
import json
import os
from typing import Dict

sys.path.append('/home/ahmet/MetisAgent/MetisAgent2')

def check_google_credentials():
    """Check all Google credential sources"""
    print("=" * 60)
    print("🔍 GOOGLE OAUTH CREDENTIALS AUDIT")
    print("=" * 60)
    
    # 1. Check environment config
    print("\n1. Environment Configuration:")
    try:
        from config import config
        oauth_config = config.google_oauth
        print(f"   Client ID: {oauth_config['client_id']}")
        print(f"   Client Secret: {oauth_config['client_secret']}")
        print(f"   Redirect URI: {oauth_config['redirect_uri']}")
        
        # Check if these are placeholder values
        is_placeholder_client_id = (
            not oauth_config['client_id'] or 
            oauth_config['client_id'] == 'your-google-client-id' or
            oauth_config['client_id'].startswith('your_')
        )
        is_placeholder_secret = (
            not oauth_config['client_secret'] or 
            oauth_config['client_secret'] == 'your-google-client-secret' or
            oauth_config['client_secret'].startswith('your_')
        )
        
        if is_placeholder_client_id or is_placeholder_secret:
            print("   ❌ PROBLEM: Using placeholder OAuth credentials")
        else:
            print("   ✅ OAuth credentials appear to be real")
            
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
    
    # 2. Check JSON settings for stored credentials
    print("\n2. JSON Settings Manager:")
    try:
        from tools.json_settings_manager import get_json_settings_manager
        settings_manager = get_json_settings_manager()
        
        # Get Google credentials for the user
        user_id = "ahmetb@minor.com.tr"
        google_creds = settings_manager.get_google_credentials(user_id)
        
        if google_creds:
            print(f"   ✅ Found Google credentials for {user_id}")
            print(f"   Email: {google_creds.get('email')}")
            
            oauth_token = google_creds.get('oauth_token', {})
            if oauth_token:
                print(f"   Access Token: {oauth_token.get('access_token', 'None')[:30]}...")
                print(f"   Refresh Token: {oauth_token.get('refresh_token', 'None')[:30]}...")
                print(f"   Expires At: {oauth_token.get('expires_at', 'None')}")
            else:
                print("   ❌ No OAuth token data found")
        else:
            print(f"   ❌ No Google credentials found for {user_id}")
            
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
    
    # 3. Check settings.json directly
    print("\n3. Direct Settings.json Check:")
    try:
        settings_file = "metis_json_storage/settings.json"
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                settings_data = json.load(f)
            
            print(f"   Settings file exists with {len(settings_data)} entries")
            
            # Look for any Google-related settings
            google_entries = []
            for user_key, user_settings in settings_data.items():
                if isinstance(user_settings, dict):
                    for setting_key in user_settings.keys():
                        if 'google' in setting_key.lower() or 'oauth' in setting_key.lower():
                            google_entries.append(f"{user_key} -> {setting_key}")
            
            if google_entries:
                print("   Google/OAuth settings found:")
                for entry in google_entries:
                    print(f"     - {entry}")
            else:
                print("   ❌ No Google/OAuth settings found in settings.json")
        else:
            print("   ❌ settings.json file not found")
            
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
    
    # 4. Check if actual working client credentials exist
    print("\n4. Real Client Credentials Check:")
    
    # Look for the client ID from CLAUDE.md comment
    expected_client_id = "117336478735-nq2448utl9hutq6ds2d68qmr5o71culf.apps.googleusercontent.com"
    
    try:
        from config import config
        current_client_id = config.google_oauth['client_id']
        
        if current_client_id == expected_client_id:
            print(f"   ✅ Using the correct client ID from documentation")
            print(f"   Client ID: {current_client_id}")
        else:
            print(f"   ❌ Current client ID doesn't match expected")
            print(f"   Current: {current_client_id}")
            print(f"   Expected: {expected_client_id}")
            
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
    
    return True

if __name__ == "__main__":
    check_google_credentials()