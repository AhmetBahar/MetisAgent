#!/usr/bin/env python3
"""
Gmail API Checker - Google API kullanarak güvenilir Gmail erişimi
"""

import requests
import json
import base64
from email.mime.text import MIMEText
from tools.settings_manager import settings_manager

API_BASE = "http://localhost:5001/api"

def check_gmail_via_api():
    """Gmail API kullanarak okunmamış email sayısını kontrol et"""
    print("📧 Gmail API ile Email Kontrolü")
    print("=" * 50)
    
    try:
        # Google credentials al
        print("\n1️⃣ Google hesap bilgileri alınıyor...")
        credentials = settings_manager.get_google_credentials("ahmetb@minor.com.tr")
        if not credentials:
            print("❌ Google hesap bilgileri bulunamadı")
            return None
            
        email = credentials.get('email')
        password = credentials.get('password')
        print(f"✅ Google hesap: {email}")
        
        # Gmail API için OAuth2 token gerekli
        print("\n2️⃣ Gmail API erişimi için OAuth2 setup...")
        print("💡 Gmail API kullanımı için aşağıdaki adımları takip edin:")
        print("   1. https://console.cloud.google.com/ → APIs & Services")
        print("   2. Gmail API'yi aktif edin")
        print("   3. Credentials → Create Credentials → Service Account")
        print("   4. JSON key dosyasını indirin")
        print("   5. GOOGLE_APPLICATION_CREDENTIALS env var olarak ayarlayın")
        
        # Alternatif: IMAP kullanımı
        print("\n3️⃣ Alternatif: IMAP ile email erişimi...")
        return check_gmail_via_imap(email, password)
        
    except Exception as e:
        print(f"❌ Gmail API hatası: {e}")
        return None

def check_gmail_via_imap(email, password):
    """IMAP protokolü ile Gmail erişimi"""
    try:
        import imaplib
        import ssl
        
        print("   IMAP bağlantısı kuruluyor...")
        
        # Gmail IMAP ayarları
        imap_server = "imap.gmail.com"
        imap_port = 993
        
        # SSL context oluştur
        context = ssl.create_default_context()
        
        # IMAP bağlantısı
        with imaplib.IMAP4_SSL(imap_server, imap_port, ssl_context=context) as server:
            print("   Gmail IMAP'a bağlanılıyor...")
            
            # Giriş yap
            server.login(email, password)
            print("✅ IMAP girişi başarılı")
            
            # INBOX seç
            server.select('INBOX')
            
            # Okunmamış emailları ara
            status, unread_data = server.search(None, 'UNSEEN')
            
            if status == 'OK':
                unread_emails = unread_data[0].split()
                unread_count = len(unread_emails)
                print(f"✅ Okunmamış email sayısı: {unread_count}")
                
                # İlk birkaç email başlığını göster
                if unread_count > 0:
                    print("\n📬 Son okunmamış emaillar:")
                    for i, email_id in enumerate(unread_emails[-3:]):  # Son 3 email
                        try:
                            status, msg_data = server.fetch(email_id, '(RFC822.HEADER)')
                            if status == 'OK':
                                import email
                                msg = email.message_from_bytes(msg_data[0][1])
                                subject = msg.get('Subject', 'Konu yok')
                                sender = msg.get('From', 'Gönderen bilinmiyor')
                                print(f"   {i+1}. {subject} - {sender}")
                        except Exception as e:
                            print(f"   {i+1}. Email okunamadı: {e}")
                
                return {
                    'success': True,
                    'unread_count': unread_count,
                    'email': email,
                    'method': 'IMAP',
                    'server': imap_server
                }
            else:
                print(f"❌ Email arama hatası: {status}")
                return None
                
    except imaplib.IMAP4.error as e:
        print(f"❌ IMAP hatası: {e}")
        print("💡 Muhtemel çözümler:")
        print("   1. 2-Factor Authentication aktifse App Password kullanın")
        print("   2. 'Less secure app access' ayarını aktif edin")
        print("   3. Gmail hesap ayarlarından IMAP'ı aktif edin")
        return None
        
    except ImportError:
        print("❌ imaplib modülü bulunamadı")
        return None
        
    except Exception as e:
        print(f"❌ IMAP bağlantı hatası: {e}")
        return None

def check_gmail_backend_automation():
    """Backend automation ile Gmail kontrolü (headless)"""
    print("\n" + "=" * 50)
    print("🤖 Backend Automation ile Gmail")
    print("=" * 50)
    
    try:
        # Backend health check
        health_response = requests.get(f"{API_BASE}/health", timeout=5)
        if health_response.status_code != 200:
            print("❌ Backend sunucusu sorunlu")
            return None
            
        print("✅ Backend sunucusu çalışıyor")
        
        # Selenium browser ile Gmail (headless)
        print("\n1️⃣ Headless browser ile Gmail erişimi...")
        
        # Browser başlat
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
        
        if start_response.status_code != 200 or not start_response.json().get('success'):
            print("❌ Browser başlatılamadı")
            return None
            
        print("✅ Headless browser başlatıldı")
        
        # Gmail'e git
        navigate_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
            json={
                "action": "navigate", 
                "params": {"url": "https://mail.google.com/"}
            }
        )
        
        if navigate_response.status_code == 200 and navigate_response.json().get('success'):
            print("✅ Gmail sayfasına gidildi")
            
            # URL kontrol et
            url_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
                json={"action": "get_current_url", "params": {}}
            )
            
            if url_response.status_code == 200:
                url_result = url_response.json()
                current_url = url_result.get('data', {}).get('url', '')
                
                if 'accounts.google.com' in current_url:
                    print("⚠️ Gmail authentication gerekli")
                    print("💡 Otomatik giriş için stored credentials veya OAuth kullanılabilir")
                elif 'mail.google.com' in current_url:
                    print("✅ Gmail'e erişim sağlandı")
                    # Unread email count logic here
                
                # Screenshot al
                screenshot_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
                    json={
                        "action": "screenshot",
                        "params": {"filename": "gmail_headless_backend.png"}
                    }
                )
                
                if screenshot_response.status_code == 200:
                    print("✅ Screenshot alındı: gmail_headless_backend.png")
                    
        # Browser kapat
        close_response = requests.post(f"{API_BASE}/tools/selenium_browser/execute",
            json={"action": "close_browser", "params": {}}
        )
        
        if close_response.status_code == 200:
            print("✅ Browser kapatıldı")
            
        return {
            'success': True,
            'method': 'Backend Selenium Headless',
            'auth_required': 'accounts.google.com' in current_url if 'current_url' in locals() else True
        }
        
    except requests.exceptions.ConnectionError:
        print("❌ Backend sunucusuna bağlanılamadı")
        return None
        
    except Exception as e:
        print(f"❌ Backend automation hatası: {e}")
        return None

def create_gmail_automation_api():
    """Gmail automation için MCP tool oluştur"""
    print("\n" + "=" * 50)
    print("⚙️ Gmail Automation MCP Tool")
    print("=" * 50)
    
    gmail_tool_code = '''
def _check_gmail_unread(self, method="imap", email=None, password=None):
    """Gmail okunmamış email sayısını kontrol et"""
    try:
        if method == "imap":
            return self._check_gmail_imap(email, password)
        elif method == "selenium":
            return self._check_gmail_selenium()
        else:
            return MCPToolResult(success=False, error="Invalid method")
            
    except Exception as e:
        return MCPToolResult(success=False, error=str(e))

def _check_gmail_imap(self, email, password):
    """IMAP ile Gmail kontrolü"""
    import imaplib
    import ssl
    
    try:
        context = ssl.create_default_context()
        with imaplib.IMAP4_SSL("imap.gmail.com", 993, ssl_context=context) as server:
            server.login(email, password)
            server.select('INBOX')
            status, unread_data = server.search(None, 'UNSEEN')
            
            if status == 'OK':
                unread_count = len(unread_data[0].split())
                return MCPToolResult(
                    success=True,
                    data={
                        'unread_count': unread_count,
                        'method': 'IMAP',
                        'email': email
                    }
                )
                
    except Exception as e:
        return MCPToolResult(success=False, error=str(e))
'''
    
    print("💡 Gmail MCP Tool kodu hazırlandı")
    print("   Bu kod tools/gmail_manager.py olarak kaydedilebilir")
    print("   Ve backend API'de /api/tools/gmail_manager/execute kullanılabilir")
    
    return gmail_tool_code

if __name__ == "__main__":
    print("🚀 Gmail API ve Automation Test Paketi")
    print("=" * 60)
    
    # 1. Gmail API erişimi dene
    api_result = check_gmail_via_api()
    
    print("\n" + "=" * 60)
    
    # 2. Backend automation dene
    backend_result = check_gmail_backend_automation()
    
    print("\n" + "=" * 60)
    
    # 3. MCP Tool kodu oluştur
    tool_code = create_gmail_automation_api()
    
    print("\n📊 TEST SONUÇLARI:")
    print("=" * 30)
    
    if api_result:
        print(f"📧 IMAP: {'✅ Başarılı' if api_result.get('success') else '❌ Başarısız'}")
        if api_result.get('success'):
            print(f"   Okunmamış: {api_result.get('unread_count', 0)}")
            print(f"   Email: {api_result.get('email')}")
    else:
        print("📧 IMAP: ❌ Bağlantı kurulamadı")
    
    if backend_result:
        print(f"🤖 Backend: {'✅ Başarılı' if backend_result.get('success') else '❌ Başarısız'}")
        print(f"   Method: {backend_result.get('method')}")
        if backend_result.get('auth_required'):
            print("   ⚠️ Authentication gerekli")
    else:
        print("🤖 Backend: ❌ Test başarısız")
    
    print("\n💡 ÖNERİLER:")
    print("1. IMAP erişimi için App Password kullanın")
    print("2. Gmail API için OAuth2 setup yapın") 
    print("3. Backend automation için stored credentials kullanın")
    print("4. Production'da Gmail API tercih edin")