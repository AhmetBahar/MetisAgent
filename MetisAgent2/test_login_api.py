#!/usr/bin/env python3
"""
API üzerinden login testi
"""

import requests
import json

def test_login_api():
    """API üzerinden login testi"""
    
    base_url = "http://localhost:5001"
    
    print("🔍 Testing API endpoints...")
    
    # 1. Auth status kontrolü
    print("\n1. Checking auth status...")
    try:
        response = requests.get(f"{base_url}/api/settings/auth/status", timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {data}")
        else:
            print(f"   Error: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"   Connection error: {e}")
    
    # 2. Frontend'in hangi portu kullandığını kontrol et
    print("\n2. Checking frontend config...")
    try:
        with open("../MetisAgent2-Frontend/src/services/authService.js", "r") as f:
            content = f.read()
            if "5001" in content:
                print("   ✅ Frontend configured for port 5001")
            elif "5000" in content:
                print("   ❌ Frontend configured for port 5000")
            else:
                print("   ⚠️  Port configuration unclear")
    except Exception as e:
        print(f"   Error reading frontend config: {e}")
    
    # 3. Legacy auth testi
    print("\n3. Testing legacy auth endpoint...")
    # Legacy auth sistemine erişim için farklı endpoint olabilir
    
    print("\n4. Available endpoints test...")
    endpoints_to_test = [
        "/api/settings/auth/status",
        "/api/auth/status", 
        "/api/users/login",
        "/api/login",
        "/auth/login"
    ]
    
    for endpoint in endpoints_to_test:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=2)
            print(f"   {endpoint}: {response.status_code}")
        except:
            print(f"   {endpoint}: Connection failed")

if __name__ == "__main__":
    test_login_api()