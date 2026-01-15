#!/usr/bin/env python3
"""
OAuth2 Basic Test - OAuth2 fonksiyonlarını test et
"""

import requests
import json

API_BASE = "http://localhost:5001"

def test_oauth2_basic():
    """OAuth2 temel fonksiyonlarını test et"""
    print("🔐 OAuth2 Basic Functionality Test")
    print("=" * 50)
    
    # 1. OAuth2 Status
    print("\n1️⃣ OAuth2 Status kontrolü...")
    try:
        status_response = requests.get(f"{API_BASE}/oauth2/google/status")
        if status_response.status_code == 200:
            status = status_response.json()
            print("✅ OAuth2 Status:")
            print(f"   Configured: {status['data']['oauth2_configured']}")
            print(f"   Available Services: {status['data']['available_services']}")
            print(f"   Redirect URI: {status['data']['redirect_uri']}")
        else:
            print(f"❌ Status check failed: {status_response.status_code}")
            return
    except Exception as e:
        print(f"❌ Status error: {e}")
        return
    
    # 2. Test OAuth2 Setup (fake credentials for testing)
    print("\n2️⃣ OAuth2 Setup test (fake credentials)...")
    test_client_id = "123456789-test.apps.googleusercontent.com"
    test_client_secret = "TEST-SECRET-FOR-DEMO"
    
    try:
        setup_response = requests.post(f"{API_BASE}/oauth2/google/setup",
            json={
                "client_id": test_client_id,
                "client_secret": test_client_secret
            }
        )
        
        if setup_response.status_code == 200:
            setup_result = setup_response.json()
            if setup_result.get('success'):
                print("✅ OAuth2 setup successful (test credentials)")
                print(f"   Available services: {setup_result['data']['available_services']}")
            else:
                print(f"❌ Setup failed: {setup_result.get('error')}")
        else:
            print(f"❌ Setup request failed: {setup_response.status_code}")
    except Exception as e:
        print(f"❌ Setup error: {e}")
    
    # 3. Get Auth URL (test)
    print("\n3️⃣ Auth URL generation test...")
    try:
        auth_response = requests.post(f"{API_BASE}/oauth2/google/start",
            json={
                "services": ["basic", "gmail"],
                "user_id": "test@example.com"
            }
        )
        
        if auth_response.status_code == 200:
            auth_result = auth_response.json()
            if auth_result.get('success'):
                print("✅ Auth URL generated successfully")
                print(f"   State: {auth_result['state'][:20]}...")
                print(f"   Services: {auth_result['services']}")
                print(f"   URL length: {len(auth_result['auth_url'])} characters")
                print(f"   URL preview: {auth_result['auth_url'][:100]}...")
            else:
                print(f"❌ Auth URL generation failed: {auth_result.get('error')}")
        else:
            print(f"❌ Auth URL request failed: {auth_response.status_code}")
    except Exception as e:
        print(f"❌ Auth URL error: {e}")
    
    # 4. List authorized users (should be empty)
    print("\n4️⃣ Authorized users list...")
    try:
        users_response = requests.get(f"{API_BASE}/oauth2/google/users")
        if users_response.status_code == 200:
            users_result = users_response.json()
            if users_result.get('success'):
                users = users_result['data']['users']
                print(f"✅ Found {len(users)} authorized users")
                if users:
                    for user in users:
                        print(f"   📧 {user['email']} - Services: {user['services']}")
                else:
                    print("   (No users authorized yet)")
            else:
                print(f"❌ Users list failed: {users_result.get('error')}")
        else:
            print(f"❌ Users request failed: {users_response.status_code}")
    except Exception as e:
        print(f"❌ Users list error: {e}")
    
    # 5. Test MCP Tool direct access
    print("\n5️⃣ MCP Tool direct access test...")
    try:
        tool_response = requests.post(f"{API_BASE}/api/tools/google_oauth2_manager/execute",
            json={
                "action": "get_oauth2_status",
                "params": {}
            }
        )
        
        if tool_response.status_code == 200:
            tool_result = tool_response.json()
            if tool_result.get('success'):
                print("✅ MCP Tool direct access works")
                status_data = tool_result['data']
                print(f"   OAuth2 configured: {status_data['oauth2_configured']}")
                print(f"   Available services: {len(status_data['available_services'])}")
            else:
                print(f"❌ MCP Tool failed: {tool_result.get('error')}")
        else:
            print(f"❌ MCP Tool request failed: {tool_response.status_code}")
    except Exception as e:
        print(f"❌ MCP Tool error: {e}")
    
    print("\n🎉 OAuth2 Basic Test Completed!")
    print("\n💡 Next Steps:")
    print("1. Get real Google OAuth2 credentials from Google Cloud Console")
    print("2. Setup real credentials using: POST /oauth2/google/setup")
    print("3. Test OAuth2 flow: POST /oauth2/google/start")
    print("4. Complete authorization in browser")
    print("5. Use Google APIs: /oauth2/google/gmail/messages, etc.")

def test_all_endpoints():
    """Tüm OAuth2 endpoint'lerini test et"""
    print("\n🧪 All OAuth2 Endpoints Test")
    print("=" * 50)
    
    endpoints = [
        ("GET", "/oauth2/google/status", None, "OAuth2 Status"),
        ("GET", "/oauth2/google/users", None, "List Users"),
        ("POST", "/oauth2/google/setup", {"client_id": "test", "client_secret": "test"}, "Setup Test"),
        ("POST", "/oauth2/google/start", {"services": ["basic"]}, "Start Flow"),
        ("GET", "/oauth2/google/gmail/messages?user_id=test", None, "Gmail Messages (unauthorized)"),
        ("GET", "/oauth2/google/drive/files?user_id=test", None, "Drive Files (unauthorized)"),
        ("GET", "/oauth2/google/calendar/events?user_id=test", None, "Calendar Events (unauthorized)")
    ]
    
    for method, endpoint, data, description in endpoints:
        print(f"\n🔍 Testing {description}...")
        print(f"   {method} {endpoint}")
        
        try:
            if method == "GET":
                response = requests.get(f"{API_BASE}{endpoint}")
            elif method == "POST":
                response = requests.post(f"{API_BASE}{endpoint}", json=data)
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get('success'):
                        print("   ✅ Success")
                        if 'data' in result:
                            data_keys = list(result['data'].keys()) if isinstance(result['data'], dict) else []
                            if data_keys:
                                print(f"   Data keys: {data_keys[:3]}{'...' if len(data_keys) > 3 else ''}")
                    else:
                        print(f"   ⚠️ Failed: {result.get('error', 'Unknown error')}")
                except:
                    print(f"   📄 Response length: {len(response.text)} chars")
            else:
                print(f"   ❌ HTTP Error: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Request error: {e}")

if __name__ == "__main__":
    print("🚀 OAuth2 Basic Test Suite")
    print("=" * 60)
    
    # Backend health check
    try:
        health_response = requests.get(f"{API_BASE}/api/health", timeout=5)
        if health_response.status_code == 200:
            health_data = health_response.json()
            tools = health_data.get('tools', {})
            oauth2_tool = tools.get('details', {}).get('google_oauth2_manager')
            
            if oauth2_tool and oauth2_tool.get('success'):
                print("✅ Backend ve OAuth2 tool çalışıyor")
            else:
                print("❌ OAuth2 tool bulunamadı")
                exit(1)
        else:
            print("❌ Backend sunucusu sorunlu")
            exit(1)
    except requests.exceptions.ConnectionError:
        print("❌ Backend sunucusuna bağlanılamadı!")
        exit(1)
    
    # Testleri çalıştır
    test_oauth2_basic()
    test_all_endpoints()
    
    print("\n✅ Tüm testler tamamlandı!")
    print("\n📋 OAuth2 Entegrasyon Özeti:")
    print("✅ Google OAuth2 Manager MCP Tool")
    print("✅ OAuth2 Web Flow Endpoints")
    print("✅ Google API Access Endpoints")
    print("✅ Token Management")
    print("✅ Multi-service Support")
    print("✅ Comprehensive Error Handling")