#!/usr/bin/env python3
"""
Gemini Web Automation - Backend API kullanarak Gemini web sitesinde soru sorma
"""

import requests
import json
import time

API_BASE = "http://localhost:5001/api"

def test_gemini_web_automation():
    """Backend API üzerinden Gemini web sitesine erişim ve soru sorma"""
    print("🤖 Gemini Web Automation Test")
    print("=" * 50)
    
    try:
        # Backend health check
        print("\n🔍 Backend sunucu kontrolü...")
        health_response = requests.get(f"{API_BASE}/health", timeout=5)
        if health_response.status_code != 200:
            print("❌ Backend sunucusu sorunlu")
            return None
        print("✅ Backend sunucusu çalışıyor")
        
        # 1. Browser başlat (headless)
        print("\n1️⃣ Browser başlatılıyor (headless mode)...")
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
        print("✅ Browser başarıyla başlatıldı")
        
        # 2. Gemini web sitesine git
        print("\n2️⃣ Gemini web sitesine gidiliyor...")
        navigate_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
            json={
                "action": "navigate",
                "params": {
                    "url": "https://gemini.google.com/"
                }
            }
        )
        
        if navigate_response.status_code != 200:
            print(f"❌ Gemini sitesine gidilemedi: {navigate_response.text}")
            return None
            
        navigate_result = navigate_response.json()
        if not navigate_result.get('success'):
            print(f"❌ Gemini navigation hatası: {navigate_result.get('error')}")
            return None
        print("✅ Gemini web sitesine gidildi")
        
        # 3. Sayfa yüklenmesini bekle
        print("\n3️⃣ Sayfa yükleniyor...")
        time.sleep(5)  # Gemini sayfasının yüklenmesi için bekle
        
        # Sayfa title kontrol et
        title_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
            json={
                "action": "get_title",
                "params": {}
            }
        )
        
        if title_response.status_code == 200:
            title_result = title_response.json()
            if title_result.get('success'):
                page_title = title_result.get('data', {}).get('title', '')
                print(f"✅ Sayfa başlığı: {page_title}")
        
        # 4. Screenshot al (Gemini ana sayfası)
        print("\n4️⃣ Gemini ana sayfa screenshot'ı alınıyor...")
        screenshot_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
            json={
                "action": "screenshot",
                "params": {
                    "filename": "gemini_homepage.png"
                }
            }
        )
        
        if screenshot_response.status_code == 200:
            screenshot_result = screenshot_response.json()
            if screenshot_result.get('success'):
                print(f"✅ Screenshot kaydedildi: gemini_homepage.png")
        
        # 5. Mevcut URL'yi kontrol et
        print("\n5️⃣ Mevcut URL kontrol ediliyor...")
        url_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
            json={
                "action": "get_current_url",
                "params": {}
            }
        )
        
        current_url = ""
        if url_response.status_code == 200:
            url_result = url_response.json()
            if url_result.get('success'):
                current_url = url_result.get('data', {}).get('url', '')
                print(f"✅ Mevcut URL: {current_url}")
        
        # 6. Login gerekli mi kontrol et
        if 'accounts.google.com' in current_url or 'signin' in current_url:
            print("\n⚠️ Google hesabıyla giriş gerekli")
            login_result = perform_google_login()
            if not login_result:
                print("❌ Giriş işlemi başarısız")
                return None
        else:
            print("✅ Giriş gerektirmiyor veya zaten giriş yapılmış")
        
        # 7. Gemini chat input alanını bul
        print("\n6️⃣ Gemini chat input alanı aranıyor...")
        
        # Gemini'de kullanılabilecek selector'lar
        input_selectors = [
            'textarea[placeholder*="Enter a prompt"]',
            'textarea[placeholder*="Type a message"]',
            'textarea[placeholder*="Ask me anything"]',
            'textarea[data-testid="chat-input"]',
            'div[contenteditable="true"]',
            'textarea',
            'input[type="text"]'
        ]
        
        input_found = False
        used_selector = None
        
        for selector in input_selectors:
            print(f"   {selector} deneniyor...")
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
                    print(f"   ✅ Input alanı bulundu: {selector}")
                    input_found = True
                    used_selector = selector
                    break
                else:
                    print(f"   ❌ {selector} bulunamadı")
        
        if not input_found:
            print("❌ Gemini input alanı bulunamadı")
            
            # Debug için sayfa source'unu kontrol et
            print("\n🔍 Debug: Sayfa elementleri kontrol ediliyor...")
            source_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
                json={
                    "action": "execute_script",
                    "params": {
                        "script": "return document.querySelector('body').innerHTML.substring(0, 1000);"
                    }
                }
            )
            
            if source_response.status_code == 200:
                source_result = source_response.json()
                if source_result.get('success'):
                    page_content = source_result.get('data', {}).get('result', '')
                    print(f"Sayfa içeriği (ilk 1000 karakter): {page_content}")
            
            return None
        
        # 8. Soruyu yaz
        print(f"\n7️⃣ Soru yazılıyor: 'Fransa'nın başkenti nedir?'")
        question = "Fransa'nın başkenti nedir?"
        
        type_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
            json={
                "action": "type_text",
                "params": {
                    "selector": used_selector,
                    "text": question
                }
            }
        )
        
        if type_response.status_code == 200:
            type_result = type_response.json()
            if type_result.get('success'):
                print("✅ Soru başarıyla yazıldı")
            else:
                print(f"❌ Soru yazılamadı: {type_result.get('error')}")
                return None
        else:
            print("❌ Soru yazma isteği başarısız")
            return None
        
        # 9. Enter tuşuna bas veya gönder butonuna tıkla
        print("\n8️⃣ Soru gönderiliyor...")
        
        # Önce Enter tuşunu dene
        send_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
            json={
                "action": "send_keys",
                "params": {
                    "selector": used_selector,
                    "keys": "RETURN"
                }
            }
        )
        
        if send_response.status_code == 200:
            send_result = send_response.json()
            if send_result.get('success'):
                print("✅ Soru gönderildi (Enter tuşu)")
            else:
                print("⚠️ Enter tuşu çalışmadı, gönder butonu aranıyor...")
                
                # Gönder butonu selector'ları
                send_button_selectors = [
                    'button[aria-label*="Send"]',
                    'button[data-testid="send-button"]',
                    'button:contains("Send")',
                    'button[type="submit"]',
                    '[role="button"][aria-label*="Send"]'
                ]
                
                button_clicked = False
                for button_selector in send_button_selectors:
                    button_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
                        json={
                            "action": "click",
                            "params": {
                                "selector": button_selector
                            }
                        }
                    )
                    
                    if button_response.status_code == 200 and button_response.json().get('success'):
                        print(f"✅ Gönder butonu tıklandı: {button_selector}")
                        button_clicked = True
                        break
                
                if not button_clicked:
                    print("❌ Gönder butonu bulunamadı")
                    return None
        
        # 10. Yanıt bekle
        print("\n9️⃣ Gemini yanıtı bekleniyor...")
        time.sleep(10)  # Gemini'nin yanıt vermesi için bekle
        
        # 11. Yanıt screenshot'ı al
        print("\n🔟 Yanıt screenshot'ı alınıyor...")
        response_screenshot = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
            json={
                "action": "screenshot",
                "params": {
                    "filename": "gemini_response.png"
                }
            }
        )
        
        if response_screenshot.status_code == 200:
            response_screenshot_result = response_screenshot.json()
            if response_screenshot_result.get('success'):
                print(f"✅ Yanıt screenshot'ı kaydedildi: gemini_response.png")
        
        # 12. Yanıt metnini almaya çalış
        print("\n1️⃣1️⃣ Gemini yanıtı çıkarılmaya çalışılıyor...")
        
        # Gemini yanıt element selector'ları
        response_selectors = [
            '[data-testid="conversation-turn-3"]',
            '[data-testid*="response"]',
            '.model-response',
            '.response-text',
            '[role="article"]',
            'div[class*="response"]'
        ]
        
        response_found = False
        for response_selector in response_selectors:
            response_element = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
                json={
                    "action": "find_element",
                    "params": {
                        "selector": response_selector,
                        "timeout": 5
                    }
                }
            )
            
            if response_element.status_code == 200:
                response_result = response_element.json()
                if response_result.get('success'):
                    response_text = response_result.get('data', {}).get('text', '')
                    if response_text and len(response_text.strip()) > 10:
                        print(f"✅ Gemini yanıtı bulundu:")
                        print(f"📝 {response_text}")
                        response_found = True
                        break
        
        if not response_found:
            print("⚠️ Yanıt metni otomatik çıkarılamadı, screenshot'a bakın")
            
            # Genel sayfa text'ini al
            page_text_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
                json={
                    "action": "execute_script",
                    "params": {
                        "script": "return document.body.innerText.substring(0, 2000);"
                    }
                }
            )
            
            if page_text_response.status_code == 200:
                page_text_result = page_text_response.json()
                if page_text_result.get('success'):
                    page_text = page_text_result.get('data', {}).get('result', '')
                    print(f"📄 Sayfa içeriği (ilk 2000 karakter):")
                    print(page_text)
        
        print("\n🎉 Gemini web automation testi tamamlandı!")
        
        return {
            'success': True,
            'question': question,
            'response_found': response_found,
            'screenshots': ['gemini_homepage.png', 'gemini_response.png']
        }
        
    except requests.exceptions.ConnectionError:
        print("❌ Backend sunucusuna bağlanılamadı!")
        print("💡 Sunucuyu başlatmak için: python app.py")
        return None
        
    except Exception as e:
        print(f"❌ Test hatası: {e}")
        import traceback
        traceback.print_exc()
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

def perform_google_login():
    """Google hesabıyla giriş yapmayı dene"""
    print("\n🔐 Google hesabıyla giriş yapılıyor...")
    
    try:
        from tools.settings_manager import settings_manager
        
        # Google credentials al
        credentials = settings_manager.get_google_credentials("ahmetb@minor.com.tr")
        if not credentials:
            print("❌ Google hesap bilgileri bulunamadı")
            return False
            
        email = credentials.get('email')
        password = credentials.get('password')
        print(f"✅ Google hesap bilgileri bulundu: {email}")
        
        # Email alanını bul ve doldur
        email_selectors = [
            'input[type="email"]',
            'input[name="identifier"]',
            '#identifierId'
        ]
        
        for selector in email_selectors:
            find_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
                json={
                    "action": "find_element",
                    "params": {
                        "selector": selector,
                        "timeout": 5
                    }
                }
            )
            
            if find_response.status_code == 200 and find_response.json().get('success'):
                # Email yaz
                type_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
                    json={
                        "action": "type_text",
                        "params": {
                            "selector": selector,
                            "text": email
                        }
                    }
                )
                
                if type_response.status_code == 200 and type_response.json().get('success'):
                    print("✅ Email adresi girildi")
                    
                    # İleri butonuna bas
                    next_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
                        json={
                            "action": "send_keys",
                            "params": {
                                "selector": selector,
                                "keys": "RETURN"
                            }
                        }
                    )
                    
                    if next_response.status_code == 200:
                        print("✅ İleri butonuna basıldı")
                        time.sleep(3)
                        
                        # Şifre sayfasına geçmesini bekle ve şifre gir
                        password_selectors = [
                            'input[type="password"]',
                            'input[name="password"]'
                        ]
                        
                        for pass_selector in password_selectors:
                            pass_find = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
                                json={
                                    "action": "find_element",
                                    "params": {
                                        "selector": pass_selector,
                                        "timeout": 10
                                    }
                                }
                            )
                            
                            if pass_find.status_code == 200 and pass_find.json().get('success'):
                                # Şifre yaz
                                pass_type = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
                                    json={
                                        "action": "type_text",
                                        "params": {
                                            "selector": pass_selector,
                                            "text": password
                                        }
                                    }
                                )
                                
                                if pass_type.status_code == 200 and pass_type.json().get('success'):
                                    print("✅ Şifre girildi")
                                    
                                    # Giriş yap
                                    login_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
                                        json={
                                            "action": "send_keys",
                                            "params": {
                                                "selector": pass_selector,
                                                "keys": "RETURN"
                                            }
                                        }
                                    )
                                    
                                    if login_response.status_code == 200:
                                        print("✅ Giriş butonuna basıldı")
                                        time.sleep(5)  # Giriş işleminin tamamlanmasını bekle
                                        return True
                                break
                        break
        
        print("❌ Giriş işlemi tamamlanamadı")
        return False
        
    except Exception as e:
        print(f"❌ Giriş hatası: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Gemini Web Automation Test")
    print("=" * 60)
    print("Backend API kullanarak Gemini web sitesinde soru sorma testi")
    print("Backend sunucusunun çalışıyor olması gerekir")
    
    result = test_gemini_web_automation()
    
    if result:
        print(f"\n📊 TEST SONUCU:")
        print(f"   Durum: {'✅ Başarılı' if result.get('success') else '❌ Başarısız'}")
        print(f"   Soru: {result.get('question')}")
        print(f"   Yanıt Bulundu: {'✅' if result.get('response_found') else '❌'}")
        print(f"   Screenshot'lar: {', '.join(result.get('screenshots', []))}")
    else:
        print("\n❌ Gemini automation testi başarısız")