#!/usr/bin/env python3
"""
Google OAuth2 Client oluşturma yardımcı scripti
"""

from tools.settings_manager import get_settings_manager

def create_oauth_client():
    print("Google OAuth2 Client oluşturma adımları:")
    print("="*50)
    
    print("\n1. Google Cloud Console'a gidin:")
    print("   https://console.cloud.google.com/")
    
    print("\n2. Proje seçin veya yeni proje oluşturun")
    
    print("\n3. Gmail API'yi etkinleştirin:")
    print("   APIs & Services > Enable APIs and Services > Gmail API")
    
    print("\n4. OAuth consent screen ayarlayın:")
    print("   - External seçin")
    print("   - App name: MetisAgent2")
    print("   - User support email: ahmetbahar.minor@gmail.com")
    print("   - Developer contact: ahmetbahar.minor@gmail.com")
    print("   - Test users: ahmetbahar.minor@gmail.com")
    
    print("\n5. OAuth Client ID oluşturun:")
    print("   APIs & Services > Credentials > + CREATE CREDENTIALS > OAuth client ID")
    print("   - Application type: Web application")
    print("   - Name: MetisAgent2-OAuth")
    print("   - Authorized redirect URIs:")
    print("     http://localhost:5001/oauth2/google/callback")
    print("     http://127.0.0.1:5001/oauth2/google/callback")
    
    print("\n6. Client ID ve Secret'i kopyalayın ve buraya girin:")
    
    client_id = input("\nClient ID: ").strip()
    client_secret = input("Client Secret: ").strip()
    
    if client_id and client_secret:
        # Settings manager'a kaydet
        sm = get_settings_manager()
        credentials = {
            'client_id': client_id,
            'client_secret': client_secret
        }
        
        success = sm.set_user_setting('system', 'google_oauth_client', credentials, encrypt=True)
        
        if success:
            print(f"\n✅ Credentials başarıyla kaydedildi!")
            print(f"Client ID: {client_id[:20]}...")
            print("Backend'i yeniden başlatın ve OAuth2 flow'u test edin.")
        else:
            print("❌ Credentials kaydetme hatası!")
    else:
        print("❌ Client ID ve Secret gerekli!")

if __name__ == "__main__":
    create_oauth_client()