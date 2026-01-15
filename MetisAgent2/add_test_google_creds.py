#!/usr/bin/env python3
"""
Test Google credentials ekle
"""

import os
import sys

# Add the current directory to the path
sys.path.insert(0, '.')

from tools.settings_manager import settings_manager

def add_test_google_credentials():
    """Test için Google credentials ekler"""
    
    user_id = "ahmetb@minor.com.tr"
    
    print(f"🔧 Adding test Google credentials for user: {user_id}")
    
    # Test credentials (gerçek değil)
    test_credentials = {
        'email': 'test.user@gmail.com',
        'password': 'test_app_password_1234',
        'recovery_email': 'recovery@email.com',
        'phone_number': '+90 555 123 4567'
    }
    
    try:
        # Google credentials'ı kaydet
        success = settings_manager.save_api_key(
            user_id, 
            'google_credentials', 
            test_credentials['password'],  # Şifre
            additional_info={
                'email': test_credentials['email'],
                'recovery_email': test_credentials['recovery_email'],
                'phone_number': test_credentials['phone_number'],
                'type': 'google_account_credentials'
            }
        )
        
        if success:
            print("✅ Test Google credentials added successfully")
            
            # Verify
            retrieved_creds = settings_manager.get_google_credentials(user_id)
            if retrieved_creds:
                print(f"   Email: {retrieved_creds['email']}")
                print(f"   Password: ...{retrieved_creds['password'][-4:]}")
                print(f"   Recovery Email: {retrieved_creds['recovery_email']}")
                print(f"   Phone: {retrieved_creds['phone_number']}")
            else:
                print("❌ Could not retrieve saved credentials")
        else:
            print("❌ Failed to save test credentials")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    add_test_google_credentials()