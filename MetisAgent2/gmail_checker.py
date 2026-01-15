#!/usr/bin/env python3
"""
Gmail Checker - Google hesap bilgileri ile Gmail'e giriş yapıp okunmamış mail sayısını öğrenir
"""

import time
from tools.selenium_browser import SeleniumBrowser
from tools.settings_manager import settings_manager

def check_gmail_unread_count():
    """Gmail'e giriş yapıp okunmamış mail sayısını kontrol et"""
    print("📧 Gmail Okunmamış Mail Kontrolü")
    print("=" * 40)
    
    # Google credentials'ı al
    print("\n1️⃣ Google hesap bilgileri alınıyor...")
    try:
        credentials = settings_manager.get_google_credentials("ahmetb@minor.com.tr")
        if not credentials:
            print("❌ Google hesap bilgileri bulunamadı")
            print("   Lütfen önce Settings sayfasından Google hesap bilgilerinizi kaydedin")
            return None
        
        email = credentials.get('email')
        password = credentials.get('password')
        
        if not email or not password:
            print("❌ Email veya şifre bilgisi eksik")
            return None
        
        print(f"✅ Google hesap bilgileri bulundu: {email}")
        
    except Exception as e:
        print(f"❌ Google credentials hatası: {e}")
        return None
    
    # Selenium browser başlat
    tool = SeleniumBrowser()
    
    try:
        # 2. Browser başlat
        print("\n2️⃣ Browser başlatılıyor...")
        result = tool._start_browser("chrome", headless=False, window_size="1920,1080")
        if not result.success:
            print(f"❌ Browser başlatılamadı: {result.error}")
            return None
        print("✅ Browser başarıyla başlatıldı")
        
        # 3. Gmail giriş sayfasına git
        print("\n3️⃣ Gmail giriş sayfasına gidiliyor...")
        result = tool._navigate("https://accounts.google.com/signin")
        if not result.success:
            print(f"❌ Gmail giriş sayfasına gidilemedi: {result.error}")
            return None
        print("✅ Gmail giriş sayfası açıldı")
        
        # 4. Email alanını bul ve doldur
        print("\n4️⃣ Email adresi giriliyor...")
        
        # Email input'u için farklı selector'ları dene
        email_selectors = [
            'input[type="email"]',
            'input[name="identifier"]',
            '#identifierId',
            'input[aria-label="Email or phone"]',
            'input[autocomplete="username"]'
        ]
        
        email_entered = False
        for selector in email_selectors:
            result = tool._find_element(selector, timeout=5)
            if result.success:
                print(f"✅ Email alanı bulundu: {selector}")
                result = tool._type_text(selector, email)
                if result.success:
                    print("✅ Email adresi girildi")
                    email_entered = True
                    break
                else:
                    print(f"❌ Email yazılamadı: {result.error}")
        
        if not email_entered:
            print("❌ Email alanı bulunamadı")
            return None
        
        # 5. İleri butonuna bas
        print("\n5️⃣ İleri butonuna basılıyor...")
        next_selectors = [
            'button[type="submit"]',
            '#identifierNext',
            'button:contains("Next")',
            'button[jsname="LgbsSe"]',
            'div[role="button"]:contains("Next")'
        ]
        
        next_clicked = False
        for selector in next_selectors:
            result = tool._find_element(selector, timeout=5)
            if result.success:
                print(f"✅ İleri butonu bulundu: {selector}")
                result = tool._click(selector)
                if result.success:
                    print("✅ İleri butonuna basıldı")
                    next_clicked = True
                    break
        
        if not next_clicked:
            print("❌ İleri butonu bulunamadı")
            return None
        
        # 6. Şifre sayfasının yüklenmesini bekle
        print("\n6️⃣ Şifre sayfası bekleniyor...")
        
        # URL değişimini bekle
        result = tool._smart_wait("url_contains", timeout=10, url="challenge")
        if not result.success:
            # Alternatif: password kelimesini içeren URL'yi bekle
            result = tool._smart_wait("url_contains", timeout=10, url="signin")
        
        time.sleep(3)
        
        # 7. Şifre alanını bul ve doldur
        print("\n7️⃣ Şifre giriliyor...")
        
        password_selectors = [
            'input[type="password"]',
            'input[name="password"]',
            '#password',
            'input[aria-label="Enter your password"]',
            'input[autocomplete="current-password"]',
            'input[jsname="YPqjbf"]',
            'div[jscontroller="pxq3x"] input[type="password"]'
        ]
        
        password_entered = False
        
        # Şifre alanının görünmesini bekle
        for selector in password_selectors:
            result = tool._find_element(selector, timeout=10)
            if result.success:
                print(f"✅ Şifre alanı bulundu: {selector}")
                
                # Şifre alanının görünür olmasını bekle
                result = tool._smart_wait("element_count", timeout=5, selector=selector, text="1")
                
                result = tool._type_text(selector, password)
                if result.success:
                    print("✅ Şifre girildi")
                    password_entered = True
                    break
                else:
                    print(f"❌ Şifre yazılamadı: {result.error}")
        
        if not password_entered:
            print("❌ Şifre alanı bulunamadı")
            print("   Mevcut sayfa URL'si kontrol ediliyor...")
            result = tool._get_current_url()
            if result.success:
                print(f"   Mevcut URL: {result.data['url']}")
            
            # Sayfa screenshot'ı al debug için
            result = tool._screenshot("debug_password_page.png")
            if result.success:
                print(f"   Debug screenshot: {result.data['filename']}")
            
            return None
        
        # 8. Giriş butonuna bas
        print("\n8️⃣ Giriş butonuna basılıyor...")
        login_selectors = [
            'button[type="submit"]',
            '#passwordNext',
            'button:contains("Next")',
            'div[role="button"]:contains("Next")'
        ]
        
        login_clicked = False
        for selector in login_selectors:
            result = tool._find_element(selector, timeout=5)
            if result.success:
                print(f"✅ Giriş butonu bulundu: {selector}")
                result = tool._click(selector)
                if result.success:
                    print("✅ Giriş butonuna basıldı")
                    login_clicked = True
                    break
        
        if not login_clicked:
            print("❌ Giriş butonu bulunamadı")
            return None
        
        # 9. Giriş işleminin tamamlanmasını bekle
        print("\n9️⃣ Giriş işlemi tamamlanıyor...")
        time.sleep(5)
        
        # 10. Gmail'e yönlendir
        print("\n🔟 Gmail'e yönlendiriliyor...")
        result = tool._navigate("https://mail.google.com/")
        if not result.success:
            print(f"❌ Gmail'e yönlendirilemiyor: {result.error}")
            return None
        
        # 11. Gmail'in yüklenmesini bekle
        print("\n1️⃣1️⃣ Gmail yükleniyor...")
        result = tool._smart_wait("page_load", timeout=15)
        if not result.success:
            print(f"❌ Gmail yüklenemedi: {result.error}")
            return None
        
        # 12. Okunmamış mail sayısını bul
        print("\n1️⃣2️⃣ Okunmamış mail sayısı kontrol ediliyor...")
        
        # Farklı Gmail UI versiyonları için selector'lar
        unread_selectors = [
            'span[class*="unread"]',
            '.zA.zE',  # Okunmamış mail satırları
            'tr.zA.zE',  # Okunmamış mail satırları (table)
            '[data-thread-id][class*="unread"]',
            '.yW span'  # Inbox label
        ]
        
        unread_count = 0
        
        # Önce inbox label'daki sayıyı kontrol et
        result = tool._find_element('.aim .nU > .TK .to', timeout=10)
        if result.success:
            inbox_text = result.data.get('text', '')
            if 'Inbox' in inbox_text and '(' in inbox_text:
                # Inbox (15) formatından sayıyı çıkar
                try:
                    unread_count = int(inbox_text.split('(')[1].split(')')[0])
                    print(f"✅ Okunmamış mail sayısı (Inbox label): {unread_count}")
                except:
                    pass
        
        # Eğer inbox label'dan alınamazsa, okunmamış mail satırlarını say
        if unread_count == 0:
            result = tool._find_elements('.zA.zE', timeout=10)
            if result.success:
                unread_count = result.data.get('count', 0)
                print(f"✅ Okunmamış mail sayısı (satır sayısı): {unread_count}")
        
        # 13. Screenshot al
        print("\n1️⃣3️⃣ Screenshot alınıyor...")
        result = tool._screenshot("gmail_unread_count.png")
        if result.success:
            print(f"✅ Screenshot kaydedildi: {result.data['filename']}")
        
        # 14. Sonuç
        print(f"\n🎉 Gmail kontrolü tamamlandı!")
        print(f"📧 Email: {email}")
        print(f"📬 Okunmamış mail sayısı: {unread_count}")
        
        return {
            'email': email,
            'unread_count': unread_count,
            'success': True
        }
        
    except Exception as e:
        print(f"❌ Gmail kontrolü hatası: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        # 15. Browser kapat
        print("\n1️⃣5️⃣ Browser kapatılıyor...")
        result = tool._close_browser()
        if result.success:
            print("✅ Browser kapatıldı")
        else:
            print(f"❌ Browser kapatılamadı: {result.error}")

if __name__ == "__main__":
    result = check_gmail_unread_count()
    if result:
        print(f"\n📊 SONUÇ:")
        print(f"   Email: {result['email']}")
        print(f"   Okunmamış Mail: {result['unread_count']}")
    else:
        print("\n❌ Gmail kontrolü başarısız oldu")