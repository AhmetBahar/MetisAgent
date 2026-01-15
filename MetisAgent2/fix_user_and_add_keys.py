#!/usr/bin/env python3
"""
Fix user account and add API keys
"""

import os
import sys

# Add the current directory to the path so we can import app modules
sys.path.insert(0, '.')

from tools.settings_manager import SettingsManager

def fix_user_and_add_keys():
    """Fix user account and add API keys"""
    
    # User's correct email
    correct_email = "ahmet@minor.com.tr"
    current_email = "ahmetb@minor.com.tr"  # What exists in legacy system
    
    # Initialize settings manager
    settings_manager = SettingsManager()
    
    print("🔧 Fixing user account and adding API keys...")
    
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
    
    # Social media credentials (these would be stored securely)
    social_credentials = {
        'google': {
            'email': correct_email,
            'additional_info': {'account_type': 'personal'}
        },
        'facebook': {
            'email': correct_email,
            'additional_info': {'account_type': 'personal'}
        }
    }
    
    # Use the correct email for settings manager
    user_id = correct_email
    
    print(f"👤 Adding API keys for user: {user_id}")
    
    # Add API keys
    for service, api_key in api_keys.items():
        try:
            result = settings_manager.save_api_key(user_id, service, api_key)
            if result:
                print(f"✅ {service} API key added successfully")
            else:
                print(f"❌ Failed to add {service} API key")
        except Exception as e:
            print(f"❌ Error adding {service} API key: {e}")
    
    # Add social media credentials (as settings, not API keys)
    for platform, creds in social_credentials.items():
        try:
            settings_manager.save_user_setting(
                user_id, 
                f"{platform}_credentials", 
                creds, 
                additional_info={'type': 'social_media_account'}
            )
            print(f"✅ {platform} credentials added successfully")
        except Exception as e:
            print(f"❌ Error adding {platform} credentials: {e}")
    
    # Add general user settings
    general_settings = {
        'language': 'tr',
        'theme': 'dark',
        'preferred_llm': 'openai',
        'default_image_model': 'dall-e-3'
    }
    
    try:
        settings_manager.save_user_setting(
            user_id,
            'general_settings',
            general_settings,
            additional_info={'type': 'user_preferences'}
        )
        print("✅ General settings added successfully")
    except Exception as e:
        print(f"❌ Error adding general settings: {e}")
    
    print(f"\n🔍 Verifying added keys for {user_id}:")
    
    # Verify API keys
    for service in api_keys.keys():
        try:
            api_key_data = settings_manager.get_api_key(user_id, service)
            if api_key_data:
                print(f"✅ {service}: API key verified (ends with ...{api_key_data['api_key'][-8:]})")
            else:
                print(f"❌ {service}: API key not found")
        except Exception as e:
            print(f"❌ Error verifying {service}: {e}")
    
    print(f"\n✅ Setup complete for user: {user_id}")
    print("🔄 You should now be able to log in with Google OAuth using ahmet@minor.com.tr")

if __name__ == "__main__":
    fix_user_and_add_keys()