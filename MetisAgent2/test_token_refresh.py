#!/usr/bin/env python3
"""
Test script to definitively determine OAuth2 refresh token validity
This will test if we can refresh the expired access token without re-authorization
"""

import json
import requests
import sys
from datetime import datetime
from typing import Dict

def load_token_data() -> Dict:
    """Load token data from JSON file"""
    try:
        with open('oauth_tokens/ahmetbahar.minor@gmail.com_google.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ ERROR loading token file: {e}")
        return None

def load_oauth_config() -> Dict:
    """Load OAuth config from config"""
    try:
        sys.path.append('/home/ahmet/MetisAgent/MetisAgent2')
        from config import config
        return config.google_oauth
    except Exception as e:
        print(f"❌ ERROR loading OAuth config: {e}")
        return None

def test_refresh_token(token_data: Dict, oauth_config: Dict) -> Dict:
    """Test if refresh token works"""
    try:
        refresh_token = token_data.get('refresh_token')
        if not refresh_token:
            return {'success': False, 'error': 'No refresh token found'}

        # Prepare refresh request
        refresh_data = {
            'client_id': oauth_config['client_id'],
            'client_secret': oauth_config['client_secret'],
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token'
        }

        print("🔄 Testing refresh token...")
        print(f"   Client ID: {oauth_config['client_id'][:20]}...")
        print(f"   Refresh Token: {refresh_token[:30]}...")

        # Make refresh request
        response = requests.post(
            'https://oauth2.googleapis.com/token',
            data=refresh_data,
            timeout=10
        )

        print(f"   Response Status: {response.status_code}")
        
        if response.status_code == 200:
            refresh_response = response.json()
            new_access_token = refresh_response.get('access_token')
            expires_in = refresh_response.get('expires_in', 3600)
            
            print(f"✅ SUCCESS: New access token received")
            print(f"   New Token: {new_access_token[:30]}...")
            print(f"   Expires in: {expires_in} seconds")
            
            return {
                'success': True,
                'new_access_token': new_access_token,
                'expires_in': expires_in,
                'refresh_response': refresh_response
            }
        else:
            error_text = response.text
            print(f"❌ FAILED: HTTP {response.status_code}")
            print(f"   Error: {error_text}")
            
            return {
                'success': False,
                'http_status': response.status_code,
                'error': error_text
            }

    except Exception as e:
        print(f"❌ EXCEPTION during refresh: {e}")
        return {'success': False, 'error': str(e)}

def main():
    """Main test function"""
    print("=" * 60)
    print("🔍 OAUTH2 REFRESH TOKEN VALIDATION TEST")
    print("=" * 60)
    
    # Load token data
    print("\n1. Loading token data...")
    token_data = load_token_data()
    if not token_data:
        print("❌ CRITICAL: Cannot load token data")
        return
    
    # Analyze current state
    print(f"✅ Token data loaded")
    expires_at = token_data.get('expires_at', 'Unknown')
    refresh_token = token_data.get('refresh_token', 'None')
    access_token = token_data.get('access_token', 'None')
    
    print(f"   Access Token: {access_token[:30]}...")
    print(f"   Refresh Token: {refresh_token[:30] if refresh_token != 'None' else 'None'}...")
    print(f"   Expires At: {expires_at}")
    
    # Check expiration
    current_time = datetime.now().isoformat()
    print(f"   Current Time: {current_time}")
    
    if expires_at < current_time:
        print("⚠️  Access token is EXPIRED")
    else:
        print("✅ Access token is still valid")
    
    # Load OAuth config
    print("\n2. Loading OAuth configuration...")
    oauth_config = load_oauth_config()
    if not oauth_config:
        print("❌ CRITICAL: Cannot load OAuth config")
        return
    
    print(f"✅ OAuth config loaded")
    print(f"   Client ID: {oauth_config['client_id'][:20]}...")
    
    # Test refresh token
    print("\n3. Testing refresh token functionality...")
    result = test_refresh_token(token_data, oauth_config)
    
    # Final verdict
    print("\n" + "=" * 60)
    print("🎯 DEFINITIVE ANSWER")
    print("=" * 60)
    
    if result['success']:
        print("✅ REFRESH TOKEN IS VALID")
        print("✅ NO RE-AUTHORIZATION NEEDED")
        print("✅ System can automatically refresh expired tokens")
        print("\nConclusion: The refresh token works perfectly.")
        print("The system can handle expired access tokens automatically.")
    else:
        print("❌ REFRESH TOKEN IS INVALID/EXPIRED")
        print("❌ RE-AUTHORIZATION IS REQUIRED")
        print("❌ User must go through OAuth2 flow again")
        print(f"\nError Details: {result.get('error', 'Unknown error')}")
        print("\nConclusion: The refresh token has expired or become invalid.")
        print("The user needs to re-authorize the application.")

if __name__ == "__main__":
    main()