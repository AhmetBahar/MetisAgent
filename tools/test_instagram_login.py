"""
Instagram Login Test - Gerçek credentials ile test
"""

import sys
import os

# Path ayarları
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append('/home/ahmet/MetisAgent/MetisAgent2/app')

from instagram_tool import InstagramTool

def test_instagram_login():
    """Instagram login test"""
    print("🔐 Instagram Login Test Başlatılıyor...")
    
    # Test credentials
    username = "ahmet__bahar"
    password = "bahaT4121"
    user_id = "ahmetb@minor.com.tr"  # MetisAgent user ID
    
    # Tool instance oluştur
    tool = InstagramTool()
    print(f"✅ Tool oluşturuldu: {tool.name}")
    
    try:
        print(f"\n🔑 Login denemesi: {username}")
        print("⏳ Instagram'a bağlanılıyor...")
        
        # Login test
        result = tool.login(username, password, user_id)
        
        if result.success:
            print("✅ Instagram login başarılı!")
            print(f"📊 Kullanıcı bilgileri:")
            user_info = result.data.get('user_info', {})
            
            for key, value in user_info.items():
                print(f"  {key}: {value}")
                
            # Session kontrolü
            if tool.logged_in_user:
                print(f"🔗 Aktif session: {tool.logged_in_user}")
                
                # Logout test
                print("\n🚪 Logout testi...")
                logout_result = tool.logout()
                
                if logout_result.success:
                    print("✅ Logout başarılı")
                else:
                    print(f"❌ Logout hatası: {logout_result.error}")
            
        else:
            print(f"❌ Instagram login başarısız: {result.error}")
            
            # Challenge/2FA kontrolü
            if "challenge" in result.error.lower():
                print("⚠️  Instagram güvenlik doğrulaması gerekiyor")
                print("📱 Telefon/email ile doğrulama yapmanız gerekebilir")
            elif "login_required" in result.error.lower():
                print("⚠️  Kullanıcı adı veya şifre hatalı olabilir")
                
    except Exception as e:
        print(f"💥 Beklenmeyen hata: {e}")
    
    print("\n🎯 Test tamamlandı!")

if __name__ == "__main__":
    test_instagram_login()