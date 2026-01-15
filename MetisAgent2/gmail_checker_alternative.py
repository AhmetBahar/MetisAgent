#!/usr/bin/env python3
"""
Gmail Checker Alternative - Google OAuth ile Gmail API kullanarak okunmamış mail sayısını öğrenir
"""

import time
from tools.selenium_browser import SeleniumBrowser
from tools.settings_manager import settings_manager

def check_gmail_unread_alternative():
    """Gmail'e alternatif yöntemlerle bağlanıp okunmamış mail sayısını kontrol et"""
    print("📧 Gmail Okunmamış Mail Kontrolü (Alternatif)")
    print("=" * 50)
    
    # Google credentials'ı al
    print("\n1️⃣ Google hesap bilgileri alınıyor...")
    try:
        credentials = settings_manager.get_google_credentials("ahmetb@minor.com.tr")
        if not credentials:
            print("❌ Google hesap bilgileri bulunamadı")
            return None
        
        email = credentials.get('email')
        password = credentials.get('password')
        
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
        
        # 3. Direkt Gmail'e git (giriş yapmış kullanıcı olup olmadığını kontrol et)
        print("\n3️⃣ Gmail'e gidiliyor...")
        result = tool._navigate("https://mail.google.com/")
        if not result.success:
            print(f"❌ Gmail'e gidilemedi: {result.error}")
            return None
        print("✅ Gmail'e gidildi")
        
        # 4. Sayfa yüklenmesini bekle
        print("\n4️⃣ Sayfa yükleniyor...")
        result = tool._smart_wait("page_load", timeout=10)
        time.sleep(5)
        
        # 5. Giriş yapmış mı kontrol et
        print("\n5️⃣ Giriş durumu kontrol ediliyor...")
        result = tool._get_current_url()
        current_url = result.data.get('url', '') if result.success else ''
        
        if 'accounts.google.com' in current_url or 'signin' in current_url:
            print("⚠️ Giriş yapmış kullanıcı bulunamadı, manuel giriş gerekli")
            
            # Manuel giriş işlemi
            print("\n6️⃣ Manuel giriş işlemi başlatılıyor...")
            print("   Lütfen browser penceresinde manuel olarak giriş yapın...")
            print("   60 saniye bekleniyor...")
            
            # Kullanıcının manuel giriş yapmasını bekle
            for i in range(60):
                time.sleep(1)
                result = tool._get_current_url()
                if result.success:
                    current_url = result.data.get('url', '')
                    if 'mail.google.com' in current_url:
                        print(f"✅ Giriş başarılı! ({i+1} saniye)")
                        break
                    elif i % 10 == 0:
                        print(f"   Bekleniyor... ({i+1}/60)")
            else:
                print("❌ Giriş işlemi timeout oldu")
                return None
        else:
            print("✅ Zaten giriş yapmış")
        
        # 6. Gmail'in tam yüklenmesini bekle
        print("\n7️⃣ Gmail tam yükleniyor...")
        result = tool._smart_wait("page_load", timeout=20)
        time.sleep(5)
        
        # 7. Farklı Gmail UI versiyonlarını dene
        print("\n8️⃣ Gmail UI versiyonu tespit ediliyor...")
        
        # Yeni Gmail UI
        result = tool._find_element('[data-tooltip="Inbox"]', timeout=5)
        if result.success:
            print("✅ Yeni Gmail UI tespit edildi")
            return check_new_gmail_ui(tool, email)
        
        # Klasik Gmail UI
        result = tool._find_element('.aim', timeout=5)
        if result.success:
            print("✅ Klasik Gmail UI tespit edildi")
            return check_classic_gmail_ui(tool, email)
        
        # Genel approach
        print("⚠️ Genel Gmail UI yaklaşımı deneniyor...")
        return check_general_gmail_ui(tool, email)
        
    except Exception as e:
        print(f"❌ Gmail kontrolü hatası: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        # Browser kapat
        print("\n🔚 Browser kapatılıyor...")
        result = tool._close_browser()
        if result.success:
            print("✅ Browser kapatıldı")

def check_new_gmail_ui(tool, email):
    """Yeni Gmail UI'da okunmamış mail sayısını kontrol et"""
    print("\n📬 Yeni Gmail UI'da okunmamış mail kontrolü...")
    
    try:
        # Inbox link'ini bul
        result = tool._find_element('[data-tooltip="Inbox"]', timeout=10)
        if result.success:
            inbox_text = result.data.get('text', '')
            print(f"Inbox text: {inbox_text}")
            
            # Sayı varsa çıkar
            import re
            numbers = re.findall(r'\d+', inbox_text)
            if numbers:
                unread_count = int(numbers[0])
                print(f"✅ Okunmamış mail sayısı: {unread_count}")
            else:
                unread_count = 0
                print("✅ Okunmamış mail yok")
            
            # Screenshot al
            result = tool._screenshot("gmail_new_ui.png")
            if result.success:
                print(f"✅ Screenshot: {result.data['filename']}")
            
            return {
                'email': email,
                'unread_count': unread_count,
                'ui_type': 'new',
                'success': True
            }
    
    except Exception as e:
        print(f"❌ Yeni UI kontrolü hatası: {e}")
        return None

def check_classic_gmail_ui(tool, email):
    """Klasik Gmail UI'da okunmamış mail sayısını kontrol et"""
    print("\n📬 Klasik Gmail UI'da okunmamış mail kontrolü...")
    
    try:
        # Inbox label'ını bul
        result = tool._find_element('.aim .nU > .TK .to', timeout=10)
        if result.success:
            inbox_text = result.data.get('text', '')
            print(f"Inbox text: {inbox_text}")
            
            # Inbox (15) formatından sayıyı çıkar
            if '(' in inbox_text and ')' in inbox_text:
                try:
                    unread_count = int(inbox_text.split('(')[1].split(')')[0])
                    print(f"✅ Okunmamış mail sayısı: {unread_count}")
                except:
                    unread_count = 0
                    print("✅ Okunmamış mail yok")
            else:
                unread_count = 0
                print("✅ Okunmamış mail yok")
            
            # Screenshot al
            result = tool._screenshot("gmail_classic_ui.png")
            if result.success:
                print(f"✅ Screenshot: {result.data['filename']}")
            
            return {
                'email': email,
                'unread_count': unread_count,
                'ui_type': 'classic',
                'success': True
            }
    
    except Exception as e:
        print(f"❌ Klasik UI kontrolü hatası: {e}")
        return None

def check_general_gmail_ui(tool, email):
    """Genel Gmail UI yaklaşımı ile okunmamış mail sayısını kontrol et"""
    print("\n📬 Genel Gmail UI yaklaşımı...")
    
    try:
        # Farklı selector'ları dene
        selectors_to_try = [
            # Inbox labels
            'span:contains("Inbox")',
            'a[href*="inbox"]',
            '.aim .nU .n0',
            
            # Unread indicators
            '.zE',  # Unread mail rows
            '.yW',  # Unread count
            '[data-thread-id].zE',  # Unread threads
            
            # Navigation
            'nav[role="navigation"]',
            '.TK .to',
            '.wT .n0'
        ]
        
        unread_count = 0
        
        # Önce okunmamış mail satırlarını say
        result = tool._find_elements('.zE', timeout=10)
        if result.success:
            unread_count = result.data.get('count', 0)
            print(f"✅ Okunmamış mail satırları: {unread_count}")
        
        # Sayfa başlığından kontrol et
        result = tool._get_title()
        if result.success:
            title = result.data.get('title', '')
            if 'Inbox' in title and '(' in title:
                import re
                numbers = re.findall(r'\((\d+)\)', title)
                if numbers:
                    title_count = int(numbers[0])
                    print(f"✅ Başlıktan okunmamış sayı: {title_count}")
                    unread_count = max(unread_count, title_count)
        
        # Screenshot al
        result = tool._screenshot("gmail_general_ui.png")
        if result.success:
            print(f"✅ Screenshot: {result.data['filename']}")
        
        return {
            'email': email,
            'unread_count': unread_count,
            'ui_type': 'general',
            'success': True
        }
    
    except Exception as e:
        print(f"❌ Genel UI kontrolü hatası: {e}")
        return None

if __name__ == "__main__":
    print("🔄 Gmail Alternatif Kontrol Yöntemi")
    print("=" * 50)
    print("NOT: Bu yöntem mevcut browser session'ından faydalanır")
    print("Eğer önceden Gmail'e giriş yapmışsanız direkt çalışacak")
    print("Yoksa manuel giriş yapmanız gerekebilir\n")
    
    result = check_gmail_unread_alternative()
    if result:
        print(f"\n📊 SONUÇ:")
        print(f"   Email: {result['email']}")
        print(f"   Okunmamış Mail: {result['unread_count']}")
        print(f"   UI Tipi: {result['ui_type']}")
        print(f"   Durum: {'✅ Başarılı' if result['success'] else '❌ Başarısız'}")
    else:
        print("\n❌ Gmail kontrolü başarısız oldu")
        print("💡 Öneriler:")
        print("   1. Browser'da manuel olarak mail.google.com'a girin")
        print("   2. Hesabınızda 2FA aktifse app password kullanın")
        print("   3. 'Less secure app access' ayarını kontrol edin")
        print("   4. Gmail API kullanımını düşünün")