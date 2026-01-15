#!/usr/bin/env python3
"""
Google OAuth Debug Test
"""

import os
import sys
import requests

# Add the current directory to the path
sys.path.insert(0, '.')

def test_google_oauth_endpoints():
    """Google OAuth endpoint'lerini test et"""
    
    base_url = "http://localhost:5001"
    
    print("🔍 Testing Google OAuth System...")
    
    # 1. Environment variables kontrol
    print("\n1. Environment Variables:")
    oauth_vars = ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'GOOGLE_REDIRECT_URI']
    for var in oauth_vars:
        value = os.getenv(var, 'Not set')
        if value == 'Not set' or 'your-google' in value:
            print(f"   ❌ {var}: {value}")
        else:
            print(f"   ✅ {var}: {value[:20]}...")
    
    # 2. Backend importları test et
    print("\n2. Backend Google Auth Import Test:")
    try:
        from tools.google_auth import google_auth
        print("   ✅ google_auth imported successfully")
        
        # Google auth yapılandırmasını kontrol et
        if hasattr(google_auth, 'client_id'):
            if google_auth.client_id and 'your-google' not in google_auth.client_id:
                print(f"   ✅ Google Client ID configured: {google_auth.client_id[:20]}...")
            else:
                print("   ❌ Google Client ID not properly configured")
        else:
            print("   ⚠️  Google auth object structure unknown")
            
    except Exception as e:
        print(f"   ❌ Import error: {e}")
    
    # 3. Settings manager test
    print("\n3. Settings Manager Test:")
    try:
        from tools.settings_manager import settings_manager
        print("   ✅ settings_manager imported successfully")
    except Exception as e:
        print(f"   ❌ Settings manager error: {e}")
    
    # 4. API endpoint'leri test et
    print("\n4. API Endpoints Test:")
    
    endpoints_to_test = [
        "/api/settings/auth/status",
        "/api/settings/auth/google/login", 
        "/api/auth/login"
    ]
    
    for endpoint in endpoints_to_test:
        try:
            url = f"{base_url}{endpoint}"
            response = requests.get(url, timeout=3)
            print(f"   {endpoint}: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"      Response: {data}")
                except:
                    print(f"      Response: {response.text[:100]}...")
            elif response.status_code == 404:
                print("      ❌ Endpoint not found")
            elif response.status_code == 500:
                print("      ❌ Server error")
                
        except requests.exceptions.ConnectionError:
            print(f"   {endpoint}: ❌ Connection refused - Backend not running")
        except Exception as e:
            print(f"   {endpoint}: ❌ Error - {e}")
    
    print("\n✅ Google OAuth debug test complete")

if __name__ == "__main__":
    test_google_oauth_endpoints()