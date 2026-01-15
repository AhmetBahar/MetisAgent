#!/usr/bin/env python3
"""
Move API keys to correct user: ahmetb@minor.com.tr
"""

import os
import sys

# Add the current directory to the path
sys.path.insert(0, '.')

from tools.settings_manager import SettingsManager

def fix_correct_user():
    """Move API keys to the correct user"""
    
    # Correct user ID that exists in legacy system
    correct_user_id = "ahmetb@minor.com.tr"
    wrong_user_id = "ahmet@minor.com.tr"
    
    settings_manager = SettingsManager()
    
    print(f"🔧 Moving API keys from {wrong_user_id} to {correct_user_id}")
    
    # SECURITY: API keys now loaded from environment variables
    # Set these in your .env file or environment
    from config import get_api_key
    
    api_keys = {}
    for service in ['openai', 'anthropic', 'huggingface']:
        api_key = get_api_key(service)
        if api_key and api_key != f'your_{service}_api_key_here':
            api_keys[service] = api_key
        else:
            print(f"⚠️ No valid API key found for {service}. Set {service.upper()}_API_KEY in .env file")
    
    if not api_keys:
        print("❌ No API keys found. Please configure your .env file with valid API keys.")
        return
    
    print(f"👤 Adding API keys for correct user: {correct_user_id}")
    
    # Add API keys for correct user
    for service, api_key in api_keys.items():
        try:
            result = settings_manager.save_api_key(correct_user_id, service, api_key)
            if result:
                print(f"✅ {service} API key added for {correct_user_id}")
            else:
                print(f"❌ Failed to add {service} API key for {correct_user_id}")
        except Exception as e:
            print(f"❌ Error adding {service} API key: {e}")
    
    print(f"\n🔍 Verifying keys for {correct_user_id}:")
    
    # Verify API keys
    for service in api_keys.keys():
        try:
            api_key_data = settings_manager.get_api_key(correct_user_id, service)
            if api_key_data:
                print(f"✅ {service}: API key verified (ends with ...{api_key_data['api_key'][-8:]})")
            else:
                print(f"❌ {service}: API key not found")
        except Exception as e:
            print(f"❌ Error verifying {service}: {e}")
    
    print(f"\n✅ Setup complete for user: {correct_user_id}")
    print("🔄 You can now log in using the legacy system or Google OAuth")

if __name__ == "__main__":
    fix_correct_user()