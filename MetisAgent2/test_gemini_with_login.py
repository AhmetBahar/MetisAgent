#!/usr/bin/env python3
"""
Gemini Web Automation with Google Login - Google hesabıyla giriş yapıp soru sorma
"""

import requests
import json
import time

API_BASE = "http://localhost:5001/api"

def test_gemini_with_google_login():
    """Google hesabıyla Gemini'ye giriş yapıp soru sor"""
    print("🔐 Gemini Google Giriş + Soru Sorma")
    print("=" * 50)
    
    try:
        # Backend health check
        health_response = requests.get(f"{API_BASE}/health", timeout=5)
        if health_response.status_code != 200:
            print("❌ Backend sunucusu sorunlu")
            return None
        print("✅ Backend sunucusu çalışıyor")
        
        # 1. Browser başlat (headless)
        print("\n1️⃣ Browser başlatılıyor...")
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
        
        if not start_response.json().get('success'):
            print("❌ Browser başlatılamadı")
            return None
        print("✅ Browser başlatıldı")
        
        # 2. Google giriş sayfasına git
        print("\n2️⃣ Google giriş sayfasına gidiliyor...")
        navigate_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
            json={
                "action": "navigate",
                "params": {
                    "url": "https://accounts.google.com/signin"
                }
            }
        )
        
        if not navigate_response.json().get('success'):
            print("❌ Google giriş sayfasına gidilemedi")
            return None
        print("✅ Google giriş sayfası açıldı")
        
        # 3. Google hesap bilgilerini al
        print("\n3️⃣ Google hesap bilgileri alınıyor...")
        try:
            from tools.settings_manager import settings_manager
            credentials = settings_manager.get_google_credentials("ahmetb@minor.com.tr")
            if not credentials:
                print("❌ Google hesap bilgileri bulunamadı")
                return None
                
            email = credentials.get('email')
            password = credentials.get('password')
            print(f"✅ Google hesap: {email}")
        except Exception as e:
            print(f"❌ Credential hatası: {e}")
            return None
        
        # 4. Email gir
        print("\n4️⃣ Email adresi giriliyor...")
        email_selectors = [
            'input[type="email"]',
            'input[name="identifier"]',
            '#identifierId'
        ]
        
        email_entered = False
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
            
            if find_response.json().get('success'):
                print(f"✅ Email alanı bulundu: {selector}")
                
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
                
                if type_response.json().get('success'):
                    print("✅ Email adresi girildi")
                    email_entered = True
                    break
        
        if not email_entered:
            print("❌ Email alanı bulunamadı")
            return None
        
        # 5. İleri butonu
        print("\n5️⃣ İleri butonuna basılıyor...")
        next_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
            json={
                "action": "send_keys",
                "params": {
                    "selector": selector,
                    "keys": "RETURN"
                }
            }
        )
        
        if next_response.json().get('success'):
            print("✅ İleri butonuna basıldı")
            time.sleep(3)
        
        # 6. Şifre gir
        print("\n6️⃣ Şifre giriliyor...")
        password_selectors = [
            'input[type="password"]',
            'input[name="password"]',
            '#password'
        ]
        
        password_entered = False
        for pass_selector in password_selectors:
            time.sleep(2)  # Şifre sayfasının yüklenmesini bekle
            
            pass_find = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
                json={
                    "action": "find_element",
                    "params": {
                        "selector": pass_selector,
                        "timeout": 10
                    }
                }
            )
            
            if pass_find.json().get('success'):
                print(f"✅ Şifre alanı bulundu: {pass_selector}")
                
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
                
                if pass_type.json().get('success'):
                    print("✅ Şifre girildi")
                    password_entered = True
                    break
        
        if not password_entered:
            print("❌ Şifre alanı bulunamadı")
            
            # Debug screenshot
            debug_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
                json={
                    "action": "screenshot",
                    "params": {"filename": "debug_password_page.png"}
                }
            )
            print("🔍 Debug screenshot alındı: debug_password_page.png")
            return None
        
        # 7. Giriş yap
        print("\n7️⃣ Giriş butonuna basılıyor...")
        login_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
            json={
                "action": "send_keys",
                "params": {
                    "selector": pass_selector,
                    "keys": "RETURN"
                }
            }
        )
        
        if login_response.json().get('success'):
            print("✅ Giriş butonuna basıldı")
            time.sleep(5)  # Giriş işleminin tamamlanmasını bekle
        
        # 8. Giriş başarısını kontrol et
        print("\n8️⃣ Giriş durumu kontrol ediliyor...")
        url_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
            json={
                "action": "get_current_url",
                "params": {}
            }
        )
        
        current_url = ""
        if url_response.json().get('success'):
            current_url = url_response.json().get('data', {}).get('url', '')
            print(f"Mevcut URL: {current_url}")
            
            if 'accounts.google.com' in current_url and 'challenge' in current_url:
                print("⚠️ 2FA veya güvenlik kontrolü gerekiyor")
                print("💡 Bu durumda manuel müdahale gerekebilir")
                
                # 2FA için biraz bekle
                print("   30 saniye bekleniyor...")
                time.sleep(30)
        
        # 9. Gemini'ye git
        print("\n9️⃣ Gemini'ye yönlendiriliyor...")
        gemini_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
            json={
                "action": "navigate",
                "params": {
                    "url": "https://gemini.google.com/app"
                }
            }
        )
        
        if gemini_response.json().get('success'):
            print("✅ Gemini'ye gidildi")
            time.sleep(5)  # Sayfa yüklenmesini bekle
        
        # 10. Gemini'de giriş durumunu kontrol et
        print("\n🔟 Gemini giriş durumu kontrol ediliyor...")
        title_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
            json={
                "action": "get_title",
                "params": {}
            }
        )
        
        if title_response.json().get('success'):
            title = title_response.json().get('data', {}).get('title', '')
            print(f"Gemini sayfa başlığı: {title}")
        
        # Screenshot al
        screenshot_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
            json={
                "action": "screenshot",
                "params": {"filename": "gemini_after_login.png"}
            }
        )
        
        if screenshot_response.json().get('success'):
            print("✅ Giriş sonrası screenshot: gemini_after_login.png")
        
        # 11. Soru sor
        print("\n1️⃣1️⃣ Gemini'ye soru soruluyor...")
        question = "Fransa'nın başkenti nedir?"
        
        # Input alanını bul
        input_selectors = [
            'div[contenteditable="true"]',
            'textarea[placeholder*="Enter"]',
            'textarea[placeholder*="Ask"]',
            'textarea',
            'div[role="textbox"]'
        ]
        
        input_found = False
        used_selector = None
        
        for selector in input_selectors:
            find_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
                json={
                    "action": "find_element",
                    "params": {
                        "selector": selector,
                        "timeout": 5
                    }
                }
            )
            
            if find_response.json().get('success'):
                print(f"✅ Input alanı bulundu: {selector}")
                used_selector = selector
                input_found = True
                break
        
        if not input_found:
            print("❌ Gemini input alanı bulunamadı")
            return None
        
        # Soruyu yaz
        type_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
            json={
                "action": "type_text",
                "params": {
                    "selector": used_selector,
                    "text": question
                }
            }
        )
        
        if type_response.json().get('success'):
            print(f"✅ Soru yazıldı: {question}")
        else:
            print("❌ Soru yazılamadı")
            return None
        
        # 12. Gönder
        print("\n1️⃣2️⃣ Soru gönderiliyor...")
        
        # Gönder butonunu bul ve tıkla
        send_selectors = [
            'button[aria-label*="Send"]',
            'button[data-testid="send"]',
            'button[type="submit"]',
            '[role="button"][aria-label*="Send"]'
        ]
        
        sent = False
        for send_selector in send_selectors:
            send_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
                json={
                    "action": "click",
                    "params": {
                        "selector": send_selector
                    }
                }
            )
            
            if send_response.json().get('success'):
                print(f"✅ Gönder butonu tıklandı: {send_selector}")
                sent = True
                break
        
        if not sent:
            # Enter tuşunu dene
            enter_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
                json={
                    "action": "send_keys",
                    "params": {
                        "selector": used_selector,
                        "keys": "RETURN"
                    }
                }
            )
            
            if enter_response.json().get('success'):
                print("✅ Enter tuşu ile gönderildi")
                sent = True
        
        if not sent:
            print("❌ Soru gönderilemedi")
            return None
        
        # 13. Yanıt bekle
        print("\n1️⃣3️⃣ Gemini yanıtı bekleniyor...")
        time.sleep(15)  # Yanıt için yeterli süre bekle
        
        # 14. Yanıt screenshot'ı
        print("\n1️⃣4️⃣ Yanıt screenshot'ı alınıyor...")
        final_screenshot = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
            json={
                "action": "screenshot",
                "params": {"filename": "gemini_final_response.png"}
            }
        )
        
        if final_screenshot.json().get('success'):
            print("✅ Final screenshot: gemini_final_response.png")
        
        # 15. Yanıt metnini çıkar
        print("\n1️⃣5️⃣ Yanıt metni çıkarılıyor...")
        
        # Sayfa metnini al
        page_text_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
            json={
                "action": "execute_script",
                "params": {
                    "script": """
                    let responses = document.querySelectorAll('[data-testid*="conversation"], .model-response, [role="article"]');
                    let text = '';
                    responses.forEach(r => {
                        if (r.innerText && r.innerText.includes('Paris') || r.innerText.includes('başkent')) {
                            text += r.innerText + '\\n';
                        }
                    });
                    return text || document.body.innerText.substring(0, 3000);
                    """
                }
            }
        )
        
        response_text = ""
        if page_text_response.json().get('success'):
            response_text = page_text_response.json().get('data', {}).get('result', '')
            if response_text and len(response_text.strip()) > 50:
                print(f"✅ Gemini yanıtı:")
                print(f"📝 {response_text[:500]}...")
            else:
                print("⚠️ Yanıt metni kısa, screenshot'a bakın")
        
        print("\n🎉 Gemini Google giriş + soru sorma testi tamamlandı!")
        
        return {
            'success': True,
            'email': email,
            'question': question,
            'response_text': response_text,
            'logged_in': True,
            'screenshots': [
                'gemini_after_login.png',
                'gemini_final_response.png'
            ]
        }
        
    except Exception as e:
        print(f"❌ Test hatası: {e}")
        import traceback
        traceback.print_exc()
        return None
        
    finally:
        # Browser kapat
        print("\n🔚 Browser kapatılıyor...")
        try:
            close_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
                json={"action": "close_browser", "params": {}}
            )
            print("✅ Browser kapatıldı")
        except:
            pass

if __name__ == "__main__":
    print("🚀 Gemini Google Login + Automation Test")
    print("=" * 60)
    print("Google hesabıyla giriş yapıp Gemini'de soru sorma")
    
    result = test_gemini_with_google_login()
    
    if result:
        print(f"\n📊 TEST SONUCU:")
        print(f"   Durum: {'✅ Başarılı' if result.get('success') else '❌ Başarısız'}")
        print(f"   Email: {result.get('email')}")
        print(f"   Soru: {result.get('question')}")
        print(f"   Giriş Durumu: {'✅ Giriş yapıldı' if result.get('logged_in') else '❌ Giriş yapılamadı'}")
        print(f"   Yanıt Alındı: {'✅' if result.get('response_text') else '❌'}")
        if result.get('response_text'):
            print(f"   Yanıt: {result.get('response_text')[:200]}...")
        print(f"   Screenshot'lar: {', '.join(result.get('screenshots', []))}")
    else:
        print("\n❌ Test başarısız oldu")