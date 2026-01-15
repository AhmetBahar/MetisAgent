#!/usr/bin/env python3
"""
Selenium MCP Tool Test Script
"""

import sys
import time
from tools.selenium_browser import SeleniumBrowser

def test_basic_browser_automation():
    """Test basic browser automation"""
    print("🧪 Selenium MCP Tool Test")
    print("=" * 40)
    
    # Tool'u başlat
    tool = SeleniumBrowser()
    print(f"✅ Tool initialized: {tool.name}")
    
    try:
        # 1. Browser başlat
        print("\n1️⃣ Starting browser...")
        result = tool._start_browser("chrome", headless=True)
        print(f"Result: {result.success}")
        if result.error:
            print(f"Error: {result.error}")
            return
        
        # 2. Google'a git
        print("\n2️⃣ Navigating to Google...")
        result = tool._navigate("https://www.google.com")
        print(f"Result: {result.success}")
        print(f"Current URL: {result.data.get('current_url', 'N/A')}")
        print(f"Page Title: {result.data.get('title', 'N/A')}")
        
        # 3. Sayfa başlığını al
        print("\n3️⃣ Getting page title...")
        result = tool._get_title()
        print(f"Title: {result.data.get('title', 'N/A')}")
        
        # 4. Arama kutusunu bul
        print("\n4️⃣ Finding search box...")
        result = tool._find_element("input[name='q']", "css")
        print(f"Search box found: {result.success}")
        
        # 5. Arama yap
        if result.success:
            print("\n5️⃣ Typing search query...")
            result = tool._type_text("input[name='q']", "MetisAgent selenium test", "css")
            print(f"Text typed: {result.success}")
            
            # Enter tuşuna bas
            print("\n6️⃣ Pressing Enter...")
            result = tool._execute_script("document.querySelector('input[name=\"q\"]').form.submit();")
            print(f"Form submitted: {result.success}")
            
            # Sonuçları bekle
            time.sleep(3)
            
            # Yeni URL'yi al
            print("\n7️⃣ Getting search results URL...")
            result = tool._get_current_url()
            print(f"Results URL: {result.data.get('url', 'N/A')}")
        
        # 8. Screenshot al
        print("\n8️⃣ Taking screenshot...")
        result = tool._screenshot("test_screenshot.png")
        print(f"Screenshot saved: {result.success}")
        if result.success:
            print(f"Filename: {result.data.get('filename')}")
        
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 9. Browser'ı kapat
        print("\n9️⃣ Closing browser...")
        result = tool._close_browser()
        print(f"Browser closed: {result.success}")

def test_form_interactions():
    """Test form interactions"""
    print("\n" + "="*40)
    print("🧪 Form Interaction Test")
    print("=" * 40)
    
    tool = SeleniumBrowser()
    
    try:
        # Browser başlat
        result = tool._start_browser("chrome", headless=False)  # headless=False UI görmek için
        if not result.success:
            print(f"❌ Browser start failed: {result.error}")
            return
        
        # Test formu olan siteye git
        print("\n1️⃣ Going to test form page...")
        result = tool._navigate("https://httpbin.org/forms/post")
        print(f"Navigation: {result.success}")
        
        # Form elementlerini bul ve doldur
        print("\n2️⃣ Filling form fields...")
        
        # Customer name
        result = tool._type_text("input[name='custname']", "Test User")
        print(f"Customer name: {result.success}")
        
        # Telephone
        result = tool._type_text("input[name='custtel']", "1234567890")
        print(f"Telephone: {result.success}")
        
        # Email
        result = tool._type_text("input[name='custemail']", "test@example.com")
        print(f"Email: {result.success}")
        
        # Size dropdown
        result = tool._select_dropdown("select[name='size']", "large", select_by="value")
        print(f"Size selection: {result.success}")
        
        # Pizza topping checkboxes
        result = tool._checkbox_toggle("input[value='cheese']", state="check")
        print(f"Cheese checkbox: {result.success}")
        
        result = tool._checkbox_toggle("input[value='onion']", state="check")
        print(f"Onion checkbox: {result.success}")
        
        # Comments
        result = tool._type_text("textarea[name='comments']", "This is a test comment from Selenium MCP Tool!")
        print(f"Comments: {result.success}")
        
        print("\n3️⃣ Form filled successfully!")
        print("Form will be submitted in 5 seconds...")
        time.sleep(5)
        
        # Form submit
        result = tool._click("input[type='submit']")
        print(f"Form submitted: {result.success}")
        
        # Sonuç sayfasını bekle
        time.sleep(3)
        
        # Sonuç sayfasından bilgi al
        result = tool._get_title()
        print(f"Result page title: {result.data.get('title', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Form test failed: {e}")
    
    finally:
        # Browser kapat
        tool._close_browser()

def test_element_interactions():
    """Test various element interactions"""
    print("\n" + "="*40)
    print("🧪 Element Interaction Test")
    print("=" * 40)
    
    tool = SeleniumBrowser()
    
    try:
        # Browser başlat
        result = tool._start_browser("chrome", headless=True)
        if not result.success:
            return
        
        # GitHub'a git
        print("\n1️⃣ Going to GitHub...")
        result = tool._navigate("https://github.com")
        print(f"GitHub loaded: {result.success}")
        
        # Sayfa başlığını kontrol et
        result = tool._get_title()
        print(f"Page title: {result.data.get('title', 'N/A')}")
        
        # Arama butonunu bul
        print("\n2️⃣ Finding search elements...")
        result = tool._find_elements("a", "tag")
        print(f"Found {result.data.get('count', 0)} links on page")
        
        # Navigation linklerini test et
        result = tool._find_element("a[href='/features']", "css")
        if result.success:
            print("✅ Features link found")
            
            # Link'e tıkla
            click_result = tool._click("a[href='/features']", "css")
            print(f"Features link clicked: {click_result.success}")
            
            # Yeni sayfa yüklensin
            time.sleep(2)
            
            # Yeni sayfa başlığını al
            result = tool._get_title()
            print(f"New page title: {result.data.get('title', 'N/A')}")
        
        # Geri git
        print("\n3️⃣ Going back...")
        result = tool._back()
        print(f"Back navigation: {result.success}")
        
        # JavaScript ile scroll test
        print("\n4️⃣ Testing JavaScript execution...")
        result = tool._execute_script("window.scrollTo(0, document.body.scrollHeight);")
        print(f"Scroll to bottom: {result.success}")
        
        # Sayfa kaynağının bir kısmını al
        print("\n5️⃣ Getting page source...")
        result = tool._get_page_source()
        if result.success:
            source_length = result.data.get('length', 0)
            print(f"Page source length: {source_length} characters")
        
    except Exception as e:
        print(f"❌ Element test failed: {e}")
    
    finally:
        tool._close_browser()

if __name__ == "__main__":
    print("🚀 Selenium MCP Tool - Test Suite")
    print("=" * 50)
    
    # Hangi testleri çalıştırmak istediğinizi seçin
    tests = [
        ("Basic Browser Automation", test_basic_browser_automation),
        ("Form Interactions", test_form_interactions),
        ("Element Interactions", test_element_interactions)
    ]
    
    print("\nAvailable tests:")
    for i, (name, func) in enumerate(tests, 1):
        print(f"{i}. {name}")
    
    print("\nRunning all tests...")
    
    for name, test_func in tests:
        print(f"\n{'='*20} {name} {'='*20}")
        try:
            test_func()
        except KeyboardInterrupt:
            print("\n⏹️ Test interrupted by user")
            break
        except Exception as e:
            print(f"❌ Test suite error: {e}")
    
    print("\n🏁 Test suite completed!")