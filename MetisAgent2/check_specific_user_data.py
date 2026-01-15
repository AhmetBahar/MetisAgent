#!/usr/bin/env python3
"""
Check specific user data in ChromaDB
"""

import os
import sys

# Add the current directory to the path
sys.path.insert(0, '.')

from tools.settings_manager import settings_manager

def check_specific_user_data():
    """Check specific user data"""
    
    target_user_id = "2f525c55-8b7c-40f1-8ec6-a4e6ffad0aef"
    
    print(f"🔍 Checking data for user ID: {target_user_id}")
    
    # The user settings manager uses email as user_id, not the UUID
    # From the auth database, we know this user has email: ahmetb@minor.com.tr
    user_email = "ahmetb@minor.com.tr"
    
    print(f"📧 Using email as user_id: {user_email}")
    
    try:
        # Check Google credentials
        print(f"\n🔍 Checking Google credentials...")
        google_creds = settings_manager.get_google_credentials(user_email)
        
        if google_creds:
            print(f"✅ Found Google credentials:")
            print(f"   Email: {google_creds.get('email', 'Not set')}")
            print(f"   Password: {'*' * len(google_creds.get('password', '')) if google_creds.get('password') else 'Not set'}")
            print(f"   Recovery Email: {google_creds.get('recovery_email', 'Not set')}")
            print(f"   Phone: {google_creds.get('phone_number', 'Not set')}")
        else:
            print("❌ No Google credentials found")
        
        # Check if has Google credentials
        has_google = settings_manager.has_google_credentials(user_email)
        print(f"\n🔍 Has Google credentials: {has_google}")
        
        # List all API keys
        print(f"\n🔍 Checking all API keys...")
        api_keys = settings_manager.list_user_api_keys(user_email)
        
        if api_keys:
            print(f"✅ Found {len(api_keys)} API keys:")
            for key in api_keys:
                print(f"   - {key['service']}: ✅ (created: {key['created_at'][:19]})")
        else:
            print("❌ No API keys found")
        
        # Check user settings
        print(f"\n🔍 Checking user settings...")
        user_settings = settings_manager.get_user_settings(user_email)
        
        if user_settings:
            print(f"✅ Found user settings: {list(user_settings.keys())}")
        else:
            print("❌ No user settings found")
        
        # Check if the issue is that the system is looking for the wrong user ID
        print(f"\n🔍 Checking if system is looking for Gmail account...")
        
        # Let's check the Gmail account that was mentioned
        gmail_account = "ahmetbahar.minor@gmail.com"
        print(f"📧 Checking Gmail account: {gmail_account}")
        
        gmail_google_creds = settings_manager.get_google_credentials(gmail_account)
        if gmail_google_creds:
            print(f"✅ Found Google credentials for Gmail account:")
            print(f"   Email: {gmail_google_creds.get('email', 'Not set')}")
            print(f"   Password: {'*' * len(gmail_google_creds.get('password', '')) if gmail_google_creds.get('password') else 'Not set'}")
        else:
            print("❌ No Google credentials found for Gmail account")
        
        # Check OAuth tokens
        print(f"\n🔍 Checking OAuth tokens...")
        oauth_token = settings_manager.get_oauth_token(target_user_id, "google")
        
        if oauth_token:
            print(f"✅ Found OAuth token for user ID {target_user_id}")
            print(f"   Keys: {list(oauth_token.keys())}")
        else:
            print(f"❌ No OAuth token found for user ID {target_user_id}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_specific_user_data()