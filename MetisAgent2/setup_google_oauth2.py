#!/usr/bin/env python3
"""
Google OAuth2 Setup ve Test Script
Google Cloud Console'da OAuth2 credentials oluşturma ve test etme
"""

import requests
import json
import webbrowser
import time

API_BASE = "http://localhost:5001"

def setup_oauth2_credentials():
    """OAuth2 credentials setup"""
    print("🔐 Google OAuth2 Credentials Setup")
    print("=" * 50)
    
    print("\n📋 Google Cloud Console Setup Steps:")
    print("1. https://console.cloud.google.com/ → APIs & Services")
    print("2. Credentials → Create Credentials → OAuth 2.0 Client IDs")
    print("3. Application type: Web application")
    print("4. Authorized redirect URIs: http://localhost:5001/oauth2/google/callback")
    print("5. Download JSON or copy Client ID and Client Secret")
    
    print("\n🔧 Required APIs to enable:")
    print("- Gmail API (for email access)")
    print("- Google Drive API (for file access)")
    print("- Calendar API (for calendar access)")
    print("- People API (for contacts)")
    print("- Photos Library API (for photos)")
    
    print("\n" + "=" * 50)
    
    # Kullanıcıdan credentials al
    client_id = input("Enter Google OAuth2 Client ID: ").strip()
    if not client_id:
        print("❌ Client ID required!")
        return None
    
    client_secret = input("Enter Google OAuth2 Client Secret: ").strip()
    if not client_secret:
        print("❌ Client Secret required!")
        return None
    
    redirect_uri = input("Enter Redirect URI (or press Enter for default): ").strip()
    if not redirect_uri:
        redirect_uri = "http://localhost:5001/oauth2/google/callback"
    
    print(f"\n✅ Credentials entered:")
    print(f"   Client ID: {client_id[:20]}...")
    print(f"   Client Secret: {client_secret[:10]}...")
    print(f"   Redirect URI: {redirect_uri}")
    
    # Backend'e credentials gönder
    try:
        setup_response = requests.post(f"{API_BASE}/oauth2/google/setup",
            json={
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri
            }
        )
        
        if setup_response.status_code == 200:
            setup_result = setup_response.json()
            if setup_result.get('success'):
                print("\n✅ OAuth2 credentials configured successfully!")
                print(f"Available services: {', '.join(setup_result.get('data', {}).get('available_services', []))}")
                return True
            else:
                print(f"\n❌ Setup failed: {setup_result.get('error')}")
                return None
        else:
            print(f"\n❌ Setup request failed: {setup_response.status_code}")
            print(setup_response.text)
            return None
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Backend sunucusuna bağlanılamadı!")
        print("💡 Önce backend'i başlatın: python app.py")
        return None
    except Exception as e:
        print(f"\n❌ Setup hatası: {e}")
        return None

def test_oauth2_flow():
    """OAuth2 flow'u test et"""
    print("\n🧪 OAuth2 Flow Test")
    print("=" * 50)
    
    # OAuth2 durumunu kontrol et
    try:
        status_response = requests.get(f"{API_BASE}/oauth2/google/status")
        if status_response.status_code == 200:
            status_result = status_response.json()
            if status_result.get('success'):
                status_data = status_result.get('data', {})
                print(f"✅ OAuth2 Status:")
                print(f"   Configured: {status_data.get('oauth2_configured')}")
                print(f"   Available Services: {', '.join(status_data.get('available_services', []))}")
                print(f"   Authorized Users: {status_data.get('authorized_users')}")
            else:
                print("❌ OAuth2 not configured")
                return None
        else:
            print("❌ Status check failed")
            return None
    except Exception as e:
        print(f"❌ Status check error: {e}")
        return None
    
    # Hangi servisleri test etmek istediğini sor
    print(f"\n📋 Available Google Services:")
    available_services = ['basic', 'gmail', 'drive', 'calendar', 'youtube', 'photos', 'contacts']
    for i, service in enumerate(available_services, 1):
        print(f"   {i}. {service}")
    
    selected_services = []
    service_input = input("\nEnter service numbers (comma-separated, e.g., 1,2,3): ").strip()
    
    if service_input:
        try:
            service_indices = [int(x.strip()) - 1 for x in service_input.split(',')]
            selected_services = [available_services[i] for i in service_indices if 0 <= i < len(available_services)]
        except:
            print("⚠️ Invalid input, using basic service")
            selected_services = ['basic']
    else:
        selected_services = ['basic']
    
    print(f"✅ Selected services: {', '.join(selected_services)}")
    
    # User ID al
    user_id = input("\nEnter user ID (email recommended): ").strip()
    if not user_id:
        user_id = "test_user"
    
    # OAuth2 flow başlat
    print(f"\n🚀 Starting OAuth2 flow for {user_id}...")
    
    try:
        auth_response = requests.post(f"{API_BASE}/oauth2/google/start",
            json={
                "services": selected_services,
                "user_id": user_id
            }
        )
        
        if auth_response.status_code == 200:
            auth_result = auth_response.json()
            if auth_result.get('success'):
                auth_url = auth_result.get('auth_url')
                state = auth_result.get('state')
                
                print(f"✅ Authorization URL generated")
                print(f"   State: {state}")
                print(f"   Expires in: {auth_result.get('expires_in')} seconds")
                
                print(f"\n🌐 Opening browser for authorization...")
                print(f"URL: {auth_url}")
                
                # Browser'da aç
                webbrowser.open(auth_url)
                
                print(f"\n⏳ Waiting for authorization...")
                print(f"   Complete the authorization in your browser")
                print(f"   This script will check for completion...")
                
                # Authorization completion'ı bekle
                max_wait = 300  # 5 dakika
                check_interval = 5  # 5 saniye
                
                for i in range(0, max_wait, check_interval):
                    time.sleep(check_interval)
                    
                    # Authorized users listesini kontrol et
                    users_response = requests.get(f"{API_BASE}/oauth2/google/users")
                    if users_response.status_code == 200:
                        users_result = users_response.json()
                        if users_result.get('success'):
                            users = users_result.get('data', {}).get('users', [])
                            user_found = any(user.get('user_id') == user_id for user in users)
                            
                            if user_found:
                                print(f"\n🎉 Authorization completed for {user_id}!")
                                
                                # User info göster
                                user_data = next(user for user in users if user.get('user_id') == user_id)
                                print(f"✅ User Info:")
                                print(f"   Email: {user_data.get('email')}")
                                print(f"   Name: {user_data.get('name')}")
                                print(f"   Services: {', '.join(user_data.get('services', []))}")
                                print(f"   Token Expires: {user_data.get('token_expires_at')}")
                                
                                return user_id
                    
                    if i % 30 == 0:  # Her 30 saniyede status göster
                        print(f"   Still waiting... ({i}/{max_wait} seconds)")
                
                print(f"\n⏰ Authorization timeout after {max_wait} seconds")
                return None
                
            else:
                print(f"❌ Auth URL generation failed: {auth_result.get('error')}")
                return None
        else:
            print(f"❌ Auth request failed: {auth_response.status_code}")
            print(auth_response.text)
            return None
            
    except Exception as e:
        print(f"❌ OAuth2 flow error: {e}")
        return None

def test_google_apis(user_id):
    """Google API'lerini test et"""
    print(f"\n🧪 Google APIs Test for {user_id}")
    print("=" * 50)
    
    tests = [
        ("Gmail Messages", f"/oauth2/google/gmail/messages?user_id={user_id}&max_results=5"),
        ("Drive Files", f"/oauth2/google/drive/files?user_id={user_id}&max_results=5"),
        ("Calendar Events", f"/oauth2/google/calendar/events?user_id={user_id}")
    ]
    
    for test_name, endpoint in tests:
        print(f"\n🔍 Testing {test_name}...")
        
        try:
            response = requests.get(f"{API_BASE}{endpoint}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    data = result.get('data', {})
                    
                    if 'messages' in data:
                        messages = data['messages'].get('messages', [])
                        print(f"   ✅ Found {len(messages)} messages")
                        
                    elif 'files' in data:
                        files = data['files'].get('files', [])
                        print(f"   ✅ Found {len(files)} files")
                        if files:
                            print(f"   📁 Example: {files[0].get('name', 'Unnamed')}")
                            
                    elif 'events' in data:
                        events = data['events'].get('items', [])
                        print(f"   ✅ Found {len(events)} events")
                        if events:
                            print(f"   📅 Example: {events[0].get('summary', 'No title')}")
                    
                    else:
                        print(f"   ✅ Success: {data}")
                        
                else:
                    print(f"   ❌ API Error: {result.get('error')}")
                    
            else:
                print(f"   ❌ Request failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Test error: {e}")

def main():
    """Ana test fonksiyonu"""
    print("🚀 Google OAuth2 Setup ve Test")
    print("=" * 60)
    print("MetisAgent için Google OAuth2 entegrasyonu")
    
    # Backend health check
    try:
        health_response = requests.get(f"{API_BASE}/api/health", timeout=5)
        if health_response.status_code == 200:
            print(f"✅ Backend sunucusu çalışıyor: {API_BASE}")
        else:
            print(f"⚠️ Backend sunucusu sorunlu: {health_response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ Backend sunucusuna bağlanılamadı!")
        print("💡 Önce sunucuyu başlatın: python app.py")
        return
    
    # Menu
    while True:
        print(f"\n📋 OAuth2 Setup Menu:")
        print("1. Setup OAuth2 Credentials")
        print("2. Test OAuth2 Flow")
        print("3. List Authorized Users")
        print("4. Test Google APIs")
        print("5. OAuth2 Status")
        print("0. Exit")
        
        choice = input("\nSelect option (0-5): ").strip()
        
        if choice == "1":
            setup_oauth2_credentials()
            
        elif choice == "2":
            user_id = test_oauth2_flow()
            if user_id:
                print(f"\n💡 You can now test APIs with user_id: {user_id}")
                
        elif choice == "3":
            try:
                users_response = requests.get(f"{API_BASE}/oauth2/google/users")
                if users_response.status_code == 200:
                    users_result = users_response.json()
                    if users_result.get('success'):
                        users = users_result.get('data', {}).get('users', [])
                        print(f"\n👥 Authorized Users ({len(users)}):")
                        for user in users:
                            print(f"   📧 {user.get('email')} ({user.get('user_id')})")
                            print(f"      Services: {', '.join(user.get('services', []))}")
                            print(f"      Expires: {user.get('token_expires_at')}")
                    else:
                        print("❌ Failed to get users")
                else:
                    print("❌ Request failed")
            except Exception as e:
                print(f"❌ Error: {e}")
                
        elif choice == "4":
            user_id = input("Enter user_id to test: ").strip()
            if user_id:
                test_google_apis(user_id)
            else:
                print("❌ User ID required")
                
        elif choice == "5":
            try:
                status_response = requests.get(f"{API_BASE}/oauth2/google/status")
                if status_response.status_code == 200:
                    status_result = status_response.json()
                    if status_result.get('success'):
                        status_data = status_result.get('data', {})
                        print(f"\n📊 OAuth2 Status:")
                        for key, value in status_data.items():
                            print(f"   {key}: {value}")
                    else:
                        print("❌ Status check failed")
                else:
                    print("❌ Request failed")
            except Exception as e:
                print(f"❌ Error: {e}")
                
        elif choice == "0":
            print("👋 Goodbye!")
            break
            
        else:
            print("❌ Invalid option")

if __name__ == "__main__":
    main()