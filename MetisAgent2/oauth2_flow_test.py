#!/usr/bin/env python3
"""
OAuth2 Flow Test - Google OAuth2 authentication için test scripti
"""

from tools.google_oauth2_manager import GoogleOAuth2Manager
import webbrowser

def main():
    print("🔐 MetisAgent2 Google OAuth2 Flow Test")
    print("=" * 50)
    
    oauth_manager = GoogleOAuth2Manager()
    
    # 1. Auth URL al
    print("\n1️⃣ OAuth2 authorization URL oluşturuluyor...")
    result = oauth_manager._get_auth_url(['gmail', 'gemini'], user_id='test_user')
    
    if not result.success:
        print(f"❌ Auth URL alınamadı: {result.error}")
        return
    
    auth_url = result.data.get('auth_url')
    state = result.data.get('state')
    
    print(f"✅ Auth URL oluşturuldu")
    print(f"State: {state}")
    print()
    
    # 2. Kullanıcıya URL'yi göster
    print("🌐 OAuth2 Authorization")
    print("-" * 30)
    print("Aşağıdaki URL'yi tarayıcıda açın ve Google hesabınızla giriş yapın:")
    print()
    print(auth_url)
    print()
    
    # Otomatik tarayıcı açma
    try:
        webbrowser.open(auth_url)
        print("✅ Tarayıcı otomatik açıldı")
    except:
        print("⚠️ Tarayıcı otomatik açılamadı, manuel açın")
    
    print()
    print("📋 Authorization sonrası:")
    print("1. Google hesabınızla giriş yapın")
    print("2. MetisAgent2'ye izin verin")
    print("3. Callback URL'den authorization code'u kopyalayın")
    print("4. Bu kod ile token exchange yapabilirsiniz")
    print()
    
    # 3. Authorization code bekleme
    print("🔑 Authorization code girin:")
    auth_code = input("Code: ").strip()
    
    if not auth_code:
        print("❌ Authorization code boş, çıkılıyor...")
        return
    
    # 4. Token exchange
    print("\n4️⃣ Authorization code ile token exchange...")
    exchange_result = oauth_manager._exchange_code(auth_code, state=state, user_id='test_user')
    
    if not exchange_result.success:
        print(f"❌ Token exchange başarısız: {exchange_result.error}")
        return
    
    print("✅ OAuth2 token exchange başarılı!")
    
    token_data = exchange_result.data
    print(f"User: {token_data.get('email', 'Unknown')}")
    print(f"Services: {', '.join(token_data.get('services', []))}")
    print(f"Expires: {token_data.get('expires_at', 'Unknown')}")
    
    # 5. OAuth2 status kontrol
    print("\n5️⃣ OAuth2 status kontrolü...")
    status_result = oauth_manager._get_oauth2_status()
    
    if status_result.success:
        users = status_result.data.get('users', [])
        print(f"✅ Toplam authorized kullanıcı: {len(users)}")
        
        for user in users:
            print(f"  - {user.get('user_id')}: {user.get('email', 'No email')}")
            print(f"    Valid: {user.get('token_valid', False)}")
            print(f"    Services: {', '.join(user.get('services', []))}")
    
    print("\n🎉 OAuth2 flow başarıyla tamamlandı!")
    print("Artık Playwright ile otomatik Google login yapabilirsiniz.")

if __name__ == "__main__":
    main()