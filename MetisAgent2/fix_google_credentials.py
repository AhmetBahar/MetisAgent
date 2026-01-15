#!/usr/bin/env python3
"""
Fix Google credentials for the correct user ID
"""

import os
import sys

# Add the current directory to the path
sys.path.insert(0, '.')

from tools.settings_manager import settings_manager

def fix_google_credentials():
    """Fix Google credentials by adding them to the correct user ID"""
    
    # The user that logs in with ahmetb@minor.com.tr has UUID: 2f525c55-8b7c-40f1-8ec6-a4e6ffad0aef
    # But the system is looking for Google credentials using the UUID, not the email
    
    user_uuid = "2f525c55-8b7c-40f1-8ec6-a4e6ffad0aef"
    user_email = "ahmetb@minor.com.tr"
    gmail_account = "ahmetbahar.minor@gmail.com"
    gmail_password = "bahaT4121"  # This was shown in the previous output
    
    print(f"🔧 Fixing Google credentials for user...")
    print(f"   User UUID: {user_uuid}")
    print(f"   User Email: {user_email}")
    print(f"   Gmail Account: {gmail_account}")
    
    try:
        # First, get the existing Google credentials from the email-based key
        existing_creds = settings_manager.get_google_credentials(user_email)
        
        if existing_creds:
            print(f"\n✅ Found existing Google credentials:")
            print(f"   Email: {existing_creds.get('email', 'Not set')}")
            print(f"   Password: {'*' * len(existing_creds.get('password', '')) if existing_creds.get('password') else 'Not set'}")
            print(f"   Recovery Email: {existing_creds.get('recovery_email', 'Not set')}")
            print(f"   Phone: {existing_creds.get('phone_number', 'Not set')}")
            
            # Now add the same credentials using the UUID as the key
            print(f"\n🔧 Adding Google credentials using UUID as key...")
            
            success = settings_manager.save_api_key(
                user_uuid,  # Use UUID instead of email
                'google_credentials',
                existing_creds['password'],
                additional_info={
                    'email': existing_creds['email'],
                    'recovery_email': existing_creds.get('recovery_email', ''),
                    'phone_number': existing_creds.get('phone_number', ''),
                    'type': 'google_account_credentials'
                }
            )
            
            if success:
                print("✅ Google credentials successfully saved with UUID key")
                
                # Verify the credentials can be retrieved with UUID
                verified_creds = settings_manager.get_google_credentials(user_uuid)
                if verified_creds:
                    print(f"✅ Verification successful:")
                    print(f"   Email: {verified_creds.get('email', 'Not set')}")
                    print(f"   Password: {'*' * len(verified_creds.get('password', '')) if verified_creds.get('password') else 'Not set'}")
                    print(f"   Recovery Email: {verified_creds.get('recovery_email', 'Not set')}")
                    print(f"   Phone: {verified_creds.get('phone_number', 'Not set')}")
                else:
                    print("❌ Could not verify saved credentials")
            else:
                print("❌ Failed to save Google credentials with UUID key")
        else:
            print("❌ No existing Google credentials found to copy")
            
            # Let's try to add the gmail account credentials directly
            print(f"\n🔧 Adding Gmail credentials directly...")
            
            success = settings_manager.save_api_key(
                user_uuid,
                'google_credentials',
                gmail_password,
                additional_info={
                    'email': gmail_account,
                    'recovery_email': '',
                    'phone_number': '',
                    'type': 'google_account_credentials'
                }
            )
            
            if success:
                print("✅ Gmail credentials successfully saved with UUID key")
                
                # Verify
                verified_creds = settings_manager.get_google_credentials(user_uuid)
                if verified_creds:
                    print(f"✅ Verification successful:")
                    print(f"   Email: {verified_creds.get('email', 'Not set')}")
                    print(f"   Password: {'*' * len(verified_creds.get('password', '')) if verified_creds.get('password') else 'Not set'}")
                else:
                    print("❌ Could not verify saved credentials")
            else:
                print("❌ Failed to save Gmail credentials")
        
        # Also check if we should create credentials for the Gmail account directly
        print(f"\n🔧 Checking if we need to add credentials for Gmail account...")
        
        # Check if there's already a user with Gmail account
        gmail_user_creds = settings_manager.get_google_credentials(gmail_account)
        
        if not gmail_user_creds:
            print(f"🔧 Adding Google credentials for Gmail account...")
            
            success = settings_manager.save_api_key(
                gmail_account,
                'google_credentials',
                gmail_password,
                additional_info={
                    'email': gmail_account,
                    'recovery_email': '',
                    'phone_number': '',
                    'type': 'google_account_credentials'
                }
            )
            
            if success:
                print("✅ Google credentials saved for Gmail account")
            else:
                print("❌ Failed to save Google credentials for Gmail account")
        else:
            print("✅ Google credentials already exist for Gmail account")
        
        print(f"\n✅ Google credentials fix completed!")
        print(f"   Now the system should find Google credentials for user ID: {user_uuid}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_google_credentials()