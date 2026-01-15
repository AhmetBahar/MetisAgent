#!/usr/bin/env python3
"""
Backend Gmail Test - MetisAgent API üzerinden headless Gmail kontrolü
"""

import requests
import json
import time

API_BASE = "http://localhost:5001/api"

def test_backend_gmail_check():
    """Backend API üzerinden Gmail kontrolü yap"""
    print("🌐 Backend Gmail Kontrolü")
    print("=" * 50)
    
    try:
        # 1. Browser başlat (headless)
        print("\n1️⃣ Browser başlatılıyor (headless)...")
        start_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute", 
            json={
                "action": "start_browser",
                "params": {
                    "browser": "chrome",
                    "headless": True,
                    "window_size": "1920,1080"
                }
            }
        )
        
        if start_response.status_code != 200:
            print(f"❌ Browser başlatılamadı: {start_response.text}")
            return None
            
        start_result = start_response.json()
        if not start_result.get('success'):
            print(f"❌ Browser başlatma hatası: {start_result.get('error')}")
            return None
            
        print("✅ Browser başarıyla başlatıldı (headless mode)")
        
        # 2. Gmail'e git
        print("\n2️⃣ Gmail'e gidiliyor...")
        navigate_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
            json={
                "action": "navigate",
                "params": {
                    "url": "https://mail.google.com/"
                }
            }
        )
        
        if navigate_response.status_code != 200:
            print(f"❌ Gmail'e gidilemedi: {navigate_response.text}")
            return None
            
        navigate_result = navigate_response.json()
        if not navigate_result.get('success'):
            print(f"❌ Gmail navigation hatası: {navigate_result.get('error')}")
            return None
            
        print("✅ Gmail'e gidildi")
        
        # 3. Sayfa yüklenmesini bekle
        print("\n3️⃣ Sayfa yükleniyor...")
        wait_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
            json={
                "action": "smart_wait",
                "params": {
                    "condition": "page_load",
                    "timeout": 10
                }
            }
        )
        
        if wait_response.status_code == 200:
            print("✅ Sayfa yüklendi")
        else:
            print("⚠️ Sayfa yükleme kontrolü yapılamadı, devam ediliyor...")
        
        # 4. Mevcut URL'yi kontrol et
        print("\n4️⃣ Mevcut URL kontrol ediliyor...")
        url_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
            json={
                "action": "get_current_url",
                "params": {}
            }
        )
        
        if url_response.status_code == 200:
            url_result = url_response.json()
            if url_result.get('success'):
                current_url = url_result.get('data', {}).get('url', '')
                print(f"✅ Mevcut URL: {current_url}")
                
                if 'accounts.google.com' in current_url or 'signin' in current_url:
                    print("⚠️ Gmail giriş sayfasında - authentication gerekli")
                    print("💡 Bu durumda manuel giriş gerekebilir veya API anahtarı kullanılabilir")
                    
                    # Gmail API öneri mesajı
                    print("\n📝 ÖNERİ: Daha güvenilir erişim için Gmail API kullanımı:")
                    print("   1. Google Cloud Console'da Gmail API'yi aktif edin")
                    print("   2. Service Account oluşturun")
                    print("   3. JSON key dosyasını indirin")
                    print("   4. gmail_api_checker.py scriptini çalıştırın")
                    
                elif 'mail.google.com' in current_url:
                    print("✅ Gmail ana sayfasında - giriş yapmış")
                    
                    # Okunmamış mail kontrolü dene
                    return check_unread_emails_headless()
                else:
                    print(f"⚠️ Beklenmeyen sayfa: {current_url}")
        
        # 5. Screenshot al (debug için)
        print("\n5️⃣ Screenshot alınıyor...")
        screenshot_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
            json={
                "action": "screenshot",
                "params": {
                    "filename": "backend_gmail_check.png"
                }
            }
        )
        
        if screenshot_response.status_code == 200:
            screenshot_result = screenshot_response.json()
            if screenshot_result.get('success'):
                filename = screenshot_result.get('data', {}).get('filename')
                print(f"✅ Screenshot kaydedildi: {filename}")
            else:
                print(f"❌ Screenshot hatası: {screenshot_result.get('error')}")
        
        return {
            'success': True,
            'message': 'Gmail sayfasına erişildi',
            'current_url': current_url,
            'auth_required': 'accounts.google.com' in current_url
        }
        
    except requests.exceptions.ConnectionError:
        print("❌ Backend sunucusuna bağlanılamadı!")
        print("💡 Sunucuyu başlatmak için: python app.py")
        return None
        
    except Exception as e:
        print(f"❌ Test hatası: {e}")
        return None
        
    finally:
        # Browser'ı kapat
        print("\n🔚 Browser kapatılıyor...")
        try:
            close_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
                json={
                    "action": "close_browser",
                    "params": {}
                }
            )
            
            if close_response.status_code == 200:
                print("✅ Browser kapatıldı")
            else:
                print("⚠️ Browser kapatma hatası")
                
        except Exception as e:
            print(f"⚠️ Browser kapatma hatası: {e}")

def check_unread_emails_headless():
    """Headless modda okunmamış email sayısını kontrol et"""
    print("\n📬 Okunmamış email kontrolü...")
    
    try:
        # Farklı Gmail UI selector'larını dene
        selectors_to_try = [
            ('[data-tooltip="Inbox"]', 'Yeni Gmail UI'),
            ('.aim .nU > .TK .to', 'Klasik Gmail UI'),
            ('.zE', 'Okunmamış mail satırları')
        ]
        
        for selector, description in selectors_to_try:
            print(f"   {description} test ediliyor...")
            
            find_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
                json={
                    "action": "find_element",
                    "params": {
                        "selector": selector,
                        "timeout": 5
                    }
                }
            )
            
            if find_response.status_code == 200:
                find_result = find_response.json()
                if find_result.get('success'):
                    print(f"   ✅ {description} bulundu")
                    
                    # Element text'ini al
                    text = find_result.get('data', {}).get('text', '')
                    print(f"   Text: {text}")
                    
                    # Sayı çıkarma işlemi
                    import re
                    numbers = re.findall(r'\d+', text)
                    if numbers:
                        unread_count = int(numbers[0])
                        print(f"✅ Okunmamış email sayısı: {unread_count}")
                        return unread_count
                    else:
                        print("   Sayı bulunamadı, 0 kabul ediliyor")
                        return 0
                        
        # Hiçbir selector çalışmazsa, title'dan kontrol et
        print("   Sayfa başlığından kontrol ediliyor...")
        title_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
            json={
                "action": "get_title",
                "params": {}
            }
        )
        
        if title_response.status_code == 200:
            title_result = title_response.json()
            if title_result.get('success'):
                title = title_result.get('data', {}).get('title', '')
                print(f"   Sayfa başlığı: {title}")
                
                if 'Inbox' in title and '(' in title:
                    import re
                    numbers = re.findall(r'\((\d+)\)', title)
                    if numbers:
                        unread_count = int(numbers[0])
                        print(f"✅ Başlıktan okunmamış sayısı: {unread_count}")
                        return unread_count
        
        print("⚠️ Okunmamış email sayısı belirlenemedi, 0 kabul ediliyor")
        return 0
        
    except Exception as e:
        print(f"❌ Email kontrol hatası: {e}")
        return None

def test_web_automation_general():
    """Genel web automation test - backend API ile"""
    print("\n" + "=" * 50)
    print("🤖 Genel Web Automation Testi (Backend)")
    print("=" * 50)
    
    try:
        # Google search testi
        print("\n1️⃣ Google arama testi...")
        
        # Browser başlat
        start_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
            json={
                "action": "start_browser",
                "params": {
                    "browser": "chrome",
                    "headless": True
                }
            }
        )
        
        if start_response.status_code != 200 or not start_response.json().get('success'):
            print("❌ Browser başlatılamadı")
            return
            
        print("✅ Browser başlatıldı")
        
        # Google'a git
        navigate_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
            json={
                "action": "navigate",
                "params": {
                    "url": "https://www.google.com"
                }
            }
        )
        
        if navigate_response.status_code == 200 and navigate_response.json().get('success'):
            print("✅ Google'a gidildi")
        else:
            print("❌ Google'a gidilemedi")
            return
        
        # Arama kutusunu bul
        find_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
            json={
                "action": "find_element",
                "params": {
                    "selector": "input[name='q']"
                }
            }
        )
        
        if find_response.status_code == 200 and find_response.json().get('success'):
            print("✅ Arama kutusu bulundu")
            
            # Arama yap
            type_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
                json={
                    "action": "type_text",
                    "params": {
                        "selector": "input[name='q']",
                        "text": "MetisAgent web automation"
                    }
                }
            )
            
            if type_response.status_code == 200 and type_response.json().get('success'):
                print("✅ Arama metni yazıldı")
                
                # Enter tuşu
                key_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
                    json={
                        "action": "send_keys",
                        "params": {
                            "selector": "input[name='q']",
                            "keys": "RETURN"
                        }
                    }
                )
                
                if key_response.status_code == 200:
                    print("✅ Arama yapıldı")
                    
                    # Sonuçları bekle
                    time.sleep(3)
                    
                    # Screenshot al
                    screenshot_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
                        json={
                            "action": "screenshot",
                            "params": {
                                "filename": "backend_google_search.png"
                            }
                        }
                    )
                    
                    if screenshot_response.status_code == 200:
                        print("✅ Screenshot alındı: backend_google_search.png")
                    
                else:
                    print("❌ Arama yapılamadı")
            else:
                print("❌ Arama metni yazılamadı")
        else:
            print("❌ Arama kutusu bulunamadı")
        
    except Exception as e:
        print(f"❌ Web automation test hatası: {e}")
        
    finally:
        # Browser kapat
        try:
            requests.post(f"{API_BASE}/tools/selenium_browser/execute",
                json={"action": "close_browser", "params": {}})
            print("✅ Browser kapatıldı")
        except:
            pass

if __name__ == "__main__":
    print("🚀 MetisAgent Backend Web Automation Test")
    print("=" * 60)
    print("Bu test backend API üzerinden headless web automation yapar")
    print("Backend sunucusunun çalışıyor olması gerekir (python app.py)")
    
    # Backend server kontrolü
    try:
        health_response = requests.get(f"{API_BASE}/health", timeout=5)
        if health_response.status_code == 200:
            print(f"✅ Backend sunucusu çalışıyor: {API_BASE}")
        else:
            print(f"⚠️ Backend sunucusu sorunlu: {health_response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ Backend sunucusuna bağlanılamadı!")
        print("💡 Önce sunucuyu başlatın: python app.py")
        exit(1)
    
    print("\nTestler başlatılıyor...\n")
    
    # Gmail kontrolü
    gmail_result = test_backend_gmail_check()
    
    print("\n" + "=" * 60)
    
    # Genel web automation
    test_web_automation_general()
    
    print("\n🏁 Backend web automation testleri tamamlandı!")
    
    if gmail_result:
        print("\n📊 Gmail Test Sonucu:")
        print(f"   Durum: {'✅ Başarılı' if gmail_result.get('success') else '❌ Başarısız'}")
        print(f"   Mesaj: {gmail_result.get('message')}")
        if gmail_result.get('auth_required'):
            print("   ⚠️ Authentication gerekli")
            print("   💡 Gmail API kullanımı önerilir")