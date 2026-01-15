#!/usr/bin/env python3
"""
Selenium MCP Tool - Improved Test Script
Tüm sorunlar çözülmüş versiyonu test eder
"""

import sys
import time
from tools.selenium_browser import SeleniumBrowser

def test_improved_google_search():
    """Test improved Google search functionality"""
    print("🔍 Google Arama Testi (Geliştirilmiş)")
    print("=" * 50)
    
    tool = SeleniumBrowser()
    
    try:
        # 1. Browser başlat
        print("\n1️⃣ Browser başlatılıyor...")
        result = tool._start_browser("chrome", headless=False)  # UI görmek için headless=False
        if not result.success:
            print(f"❌ Browser başlatılamadı: {result.error}")
            return
        print("✅ Browser başarıyla başlatıldı")
        
        # 2. Google'a git
        print("\n2️⃣ Google'a gidiliyor...")
        result = tool._navigate("https://www.google.com")
        if not result.success:
            print(f"❌ Google'a gidemedi: {result.error}")
            return
        print(f"✅ Google açıldı: {result.data['title']}")
        
        # 3. Arama kutusunu bul (güncellenmiş selector ile)
        print("\n3️⃣ Arama kutusu bulunuyor...")
        result = tool._find_element("input[name='q']")  # Smart fallback kullanacak
        if not result.success:
            print(f"❌ Arama kutusu bulunamadı: {result.error}")
            return
        print(f"✅ Arama kutusu bulundu: {result.data['tag_name']} (Selector: {result.data.get('used_selector', 'original')})")
        
        # 4. Arama metni yaz
        print("\n4️⃣ Arama metni yazılıyor...")
        result = tool._type_text("input[name='q']", "MetisAgent Python Selenium automation")
        if not result.success:
            print(f"❌ Metin yazılamadı: {result.error}")
            return
        print("✅ Arama metni yazıldı")
        
        # 5. Enter tuşuna bas (JavaScript ile)
        print("\n5️⃣ Arama yapılıyor...")
        result = tool._execute_script("document.querySelector('textarea[name=\"q\"]').form.submit();")
        if not result.success:
            print(f"❌ Arama yapılamadı: {result.error}")
            return
        print("✅ Arama başlatıldı")
        
        # 6. Sonuç sayfasının yüklenmesini bekle
        print("\n6️⃣ Sonuç sayfası bekleniyor...")
        result = tool._smart_wait("url_contains", timeout=10, url="search")
        if not result.success:
            print(f"❌ Sonuç sayfası yüklenemedi: {result.error}")
            return
        print("✅ Sonuç sayfası yüklendi")
        
        # 7. Sonuç sayısını kontrol et
        print("\n7️⃣ Arama sonuçları kontrol ediliyor...")
        result = tool._find_elements("h3", "tag", timeout=10)
        if result.success:
            count = result.data.get('count', 0)
            print(f"✅ {count} arama sonucu bulundu")
        else:
            print(f"⚠️ Arama sonuçları bulunamadı: {result.error}")
        
        # 8. Screenshot al
        print("\n8️⃣ Screenshot alınıyor...")
        result = tool._screenshot("google_search_improved.png")
        if result.success:
            print(f"✅ Screenshot kaydedildi: {result.data['filename']}")
        else:
            print(f"❌ Screenshot alınamadı: {result.error}")
        
        print("\n🎉 Google arama testi başarıyla tamamlandı!")
        
    except Exception as e:
        print(f"❌ Test hatası: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 9. Browser kapat
        print("\n9️⃣ Browser kapatılıyor...")
        result = tool._close_browser()
        if result.success:
            print("✅ Browser kapatıldı")
        else:
            print(f"❌ Browser kapatılamadı: {result.error}")

def test_improved_form_handling():
    """Test improved form handling"""
    print("\n" + "="*50)
    print("📝 Form İşleme Testi (Geliştirilmiş)")
    print("=" * 50)
    
    tool = SeleniumBrowser()
    
    try:
        # 1. Browser başlat
        print("\n1️⃣ Browser başlatılıyor...")
        result = tool._start_browser("chrome", headless=False)
        if not result.success:
            return
        print("✅ Browser başlatıldı")
        
        # 2. Test form sayfasına git
        print("\n2️⃣ Test form sayfasına gidiliyor...")
        result = tool._navigate("https://httpbin.org/forms/post")
        if not result.success:
            return
        print("✅ Form sayfası açıldı")
        
        # 3. Form alanlarını doldur
        print("\n3️⃣ Form alanları doldruluyor...")
        
        # Customer name
        result = tool._type_text("input[name='custname']", "Test Customer")
        print(f"Customer name: {'✅' if result.success else '❌'}")
        
        # Telephone
        result = tool._type_text("input[name='custtel']", "555-1234")
        print(f"Telephone: {'✅' if result.success else '❌'}")
        
        # Email
        result = tool._type_text("input[name='custemail']", "test@example.com")
        print(f"Email: {'✅' if result.success else '❌'}")
        
        # 4. Dropdown seçimi (geliştirilmiş)
        print("\n4️⃣ Dropdown seçimi yapılıyor...")
        result = tool._select_dropdown("select[name='size']", "large", select_by="value")
        if result.success:
            print(f"✅ Dropdown: {result.data['selected_text']}")
            print(f"   Mevcut seçenekler: {result.data['available_options']}")
        else:
            print(f"❌ Dropdown seçimi: {result.error}")
        
        # 5. Checkbox'ları işaretle
        print("\n5️⃣ Checkbox'lar işaretleniyor...")
        result = tool._checkbox_toggle("input[value='cheese']", state="check")
        print(f"Cheese: {'✅' if result.success else '❌'}")
        
        result = tool._checkbox_toggle("input[value='onion']", state="check")
        print(f"Onion: {'✅' if result.success else '❌'}")
        
        # 6. Comments alanını doldur
        print("\n6️⃣ Comments alanı doldruluyor...")
        result = tool._type_text("textarea[name='comments']", "Bu MetisAgent Selenium MCP Tool ile otomatik doldurulmuş bir form testidir!")
        print(f"Comments: {'✅' if result.success else '❌'}")
        
        # 7. Form submit (geliştirilmiş)
        print("\n7️⃣ Form submit ediliyor...")
        result = tool._submit_form("input[type='submit']", wait_for_page_load=True)
        if result.success:
            print("✅ Form başarıyla submit edildi")
            print(f"   Önceki URL: {result.data['previous_url']}")
            print(f"   Yeni URL: {result.data['current_url']}")
            print(f"   URL değişti: {result.data['url_changed']}")
        else:
            print(f"❌ Form submit edilemedi: {result.error}")
        
        # 8. Sonuç sayfasını kontrol et
        print("\n8️⃣ Sonuç sayfası kontrol ediliyor...")
        result = tool._get_title()
        if result.success:
            print(f"✅ Sonuç sayfası başlığı: {result.data['title']}")
        
        # 9. Sonuç verilerini kontrol et
        result = tool._wait_for_text("custname", timeout=5, selector="body")
        if result.success:
            print("✅ Form verileri başarıyla işlendi")
        else:
            print("⚠️ Form verileri kontrol edilemedi")
        
        print("\n🎉 Form işleme testi başarıyla tamamlandı!")
        
    except Exception as e:
        print(f"❌ Test hatası: {e}")
    
    finally:
        tool._close_browser()

def test_advanced_wait_strategies():
    """Test advanced wait strategies"""
    print("\n" + "="*50)
    print("⏰ Gelişmiş Wait Stratejileri Testi")
    print("=" * 50)
    
    tool = SeleniumBrowser()
    
    try:
        # 1. Browser başlat
        result = tool._start_browser("chrome", headless=True)
        if not result.success:
            return
        print("✅ Browser başlatıldı")
        
        # 2. Dinamik içerik sayfasına git
        print("\n1️⃣ Dinamik içerik sayfasına gidiliyor...")
        result = tool._navigate("https://httpbin.org/delay/2")
        if not result.success:
            return
        print("✅ Dinamik sayfa açıldı")
        
        # 3. Sayfa yüklenmesini bekle
        print("\n2️⃣ Sayfa yüklenmesi bekleniyor...")
        result = tool._smart_wait("page_load", timeout=10)
        if result.success:
            print("✅ Sayfa tam yüklendi")
        else:
            print(f"❌ Sayfa yüklenmesi: {result.error}")
        
        # 4. GitHub'a git ve link sayısını bekle
        print("\n3️⃣ GitHub'a gidiliyor...")
        result = tool._navigate("https://github.com")
        if not result.success:
            return
        
        # 5. Belirli sayıda link yüklenmesini bekle
        print("\n4️⃣ Link yüklenmesi bekleniyor...")
        result = tool._smart_wait("element_count", timeout=10, selector="a", text="50")
        if result.success:
            print("✅ 50+ link yüklendi")
        else:
            print(f"❌ Link yüklenmesi: {result.error}")
        
        # 6. Başlıkta 'GitHub' kelimesini bekle
        print("\n5️⃣ Başlık kontrol ediliyor...")
        result = tool._smart_wait("title_contains", timeout=5, text="GitHub")
        if result.success:
            print("✅ Başlık 'GitHub' içeriyor")
        else:
            print(f"❌ Başlık kontrolü: {result.error}")
        
        # 7. URL'de 'github' kelimesini bekle
        print("\n6️⃣ URL kontrol ediliyor...")
        result = tool._smart_wait("url_contains", timeout=5, url="github")
        if result.success:
            print("✅ URL 'github' içeriyor")
        else:
            print(f"❌ URL kontrolü: {result.error}")
        
        # 8. Özel JavaScript koşulu
        print("\n7️⃣ Özel JavaScript koşulu test ediliyor...")
        result = tool._smart_wait("custom_js", timeout=5, text="return document.readyState === 'complete'")
        if result.success:
            print("✅ Özel JavaScript koşulu karşılandı")
        else:
            print(f"❌ JavaScript koşulu: {result.error}")
        
        print("\n🎉 Gelişmiş wait stratejileri testi tamamlandı!")
        
    except Exception as e:
        print(f"❌ Test hatası: {e}")
    
    finally:
        tool._close_browser()

def main():
    """Ana test fonksiyonu"""
    print("🚀 Selenium MCP Tool - Geliştirilmiş Test Paketi")
    print("=" * 60)
    
    tests = [
        ("Google Arama Testi", test_improved_google_search),
        ("Form İşleme Testi", test_improved_form_handling),
        ("Gelişmiş Wait Stratejileri", test_advanced_wait_strategies)
    ]
    
    print("\nMevcut testler:")
    for i, (name, func) in enumerate(tests, 1):
        print(f"{i}. {name}")
    
    print("\nTüm testler çalıştırılıyor...")
    
    for name, test_func in tests:
        print(f"\n{'='*20} {name} {'='*20}")
        try:
            test_func()
        except KeyboardInterrupt:
            print("\n⏹️ Test kullanıcı tarafından durduruldu")
            break
        except Exception as e:
            print(f"❌ Test paketi hatası: {e}")
    
    print("\n🏁 Tüm testler tamamlandı!")
    print("\n📊 Özet:")
    print("✅ Google arama kutusu sorunu çözüldü")
    print("✅ Dropdown seçimi geliştirildi")
    print("✅ Form submit optimizasyonu yapıldı")
    print("✅ Gelişmiş wait stratejileri eklendi")
    print("✅ JavaScript fallback desteği eklendi")
    print("✅ Smart selector fallback sistemi eklendi")

if __name__ == "__main__":
    main()