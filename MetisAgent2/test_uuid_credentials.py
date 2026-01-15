#!/usr/bin/env python3
"""
Test Google credentials using UUID directly
"""

import os
import sys

# Add the current directory to the path
sys.path.insert(0, '.')

from tools.settings_manager import settings_manager

def test_uuid_credentials():
    """Test Google credentials using UUID directly"""
    
    user_uuid = "2f525c55-8b7c-40f1-8ec6-a4e6ffad0aef"
    
    print(f"🔍 Testing Google credentials for UUID: {user_uuid}")
    
    try:
        # Check Google credentials using UUID
        google_creds = settings_manager.get_google_credentials(user_uuid)
        
        if google_creds:
            print(f"✅ Found Google credentials using UUID:")
            print(f"   Email: {google_creds.get('email', 'Not set')}")
            print(f"   Password: {'*' * len(google_creds.get('password', '')) if google_creds.get('password') else 'Not set'}")
            print(f"   Recovery Email: {google_creds.get('recovery_email', 'Not set')}")
            print(f"   Phone: {google_creds.get('phone_number', 'Not set')}")
        else:
            print("❌ No Google credentials found using UUID")
        
        # Check if has Google credentials
        has_google = settings_manager.has_google_credentials(user_uuid)
        print(f"\n🔍 Has Google credentials (UUID): {has_google}")
        
        # Test with tools
        print(f"\n🔍 Testing with GoogleTools...")
        
        # Import GoogleTools
        from tools.google_tools import GoogleTools
        
        google_tools = GoogleTools()
        credentials = google_tools.get_credentials_for_user(user_uuid)
        
        if credentials:
            print(f"✅ GoogleTools found credentials:")
            print(f"   Type: {credentials.get('type')}")
            if credentials.get('type') == 'manual':
                print(f"   Email: {credentials.get('email')}")
                print(f"   Password: {'*' * len(credentials.get('password', '')) if credentials.get('password') else 'Not set'}")
            elif credentials.get('type') == 'oauth':
                print(f"   Access Token: {'*' * 10 if credentials.get('access_token') else 'Not set'}")
                print(f"   Refresh Token: {'*' * 10 if credentials.get('refresh_token') else 'Not set'}")
        else:
            print("❌ GoogleTools could not find credentials")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_uuid_credentials()