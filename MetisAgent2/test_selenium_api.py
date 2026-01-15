#!/usr/bin/env python3
"""
Selenium MCP Tool API Test Script
MetisAgent API üzerinden Selenium tool'u test eder
"""

import requests
import json
import time

def test_selenium_via_api():
    """MetisAgent API üzerinden Selenium tool'u test et"""
    print("🌐 Selenium MCP Tool - API Test")
    print("=" * 40)
    
    base_url = "http://localhost:5001"
    
    # 1. Login yap
    print("\n1️⃣ Logging in...")
    login_data = {
        "username": "ahmetb@minor.com.tr",
        "password": "123456"
    }
    
    response = requests.post(f"{base_url}/api/auth/login", json=login_data)
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return
    
    session_token = response.json()["session_token"]
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {session_token}"
    }
    print("✅ Login successful")
    
    # 2. Mevcut tool'ları listele
    print("\n2️⃣ Listing available tools...")
    response = requests.get(f"{base_url}/api/mcp/tools", headers=headers)
    if response.status_code == 200:
        tools = response.json().get("tools", [])
        print(f"Available tools: {tools}")
        
        if "selenium_browser" in tools:
            print("✅ Selenium browser tool found!")
        else:
            print("❌ Selenium browser tool not found")
            return
    else:
        print(f"❌ Failed to list tools: {response.status_code}")
        return
    
    # 3. Browser başlat
    print("\n3️⃣ Starting browser...")
    selenium_data = {
        "tool": "selenium_browser",
        "action": "start_browser",
        "params": {
            "browser": "chrome",
            "headless": True,
            "window_size": "1920,1080"
        }
    }
    
    response = requests.post(f"{base_url}/api/mcp/execute", json=selenium_data, headers=headers)
    print(f"Response status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Browser start result: {result}")
    else:
        print(f"❌ Failed to start browser: {response.text}")
        return
    
    # 4. Website'e git
    print("\n4️⃣ Navigating to website...")
    selenium_data = {
        "tool": "selenium_browser",
        "action": "navigate",
        "params": {
            "url": "https://httpbin.org/html"
        }
    }
    
    response = requests.post(f"{base_url}/api/mcp/execute", json=selenium_data, headers=headers)
    if response.status_code == 200:
        result = response.json()
        print(f"Navigation result: {result}")
    else:
        print(f"❌ Navigation failed: {response.text}")
    
    # 5. Sayfa başlığını al
    print("\n5️⃣ Getting page title...")
    selenium_data = {
        "tool": "selenium_browser",
        "action": "get_title",
        "params": {}
    }
    
    response = requests.post(f"{base_url}/api/mcp/execute", json=selenium_data, headers=headers)
    if response.status_code == 200:
        result = response.json()
        print(f"Page title: {result}")
    else:
        print(f"❌ Failed to get title: {response.text}")
    
    # 6. Element bul
    print("\n6️⃣ Finding elements...")
    selenium_data = {
        "tool": "selenium_browser",
        "action": "find_elements",
        "params": {
            "selector": "h1",
            "by": "tag"
        }
    }
    
    response = requests.post(f"{base_url}/api/mcp/execute", json=selenium_data, headers=headers)
    if response.status_code == 200:
        result = response.json()
        print(f"Found elements: {result}")
    else:
        print(f"❌ Failed to find elements: {response.text}")
    
    # 7. Screenshot al
    print("\n7️⃣ Taking screenshot...")
    selenium_data = {
        "tool": "selenium_browser",
        "action": "screenshot",
        "params": {
            "filename": "api_test_screenshot.png"
        }
    }
    
    response = requests.post(f"{base_url}/api/mcp/execute", json=selenium_data, headers=headers)
    if response.status_code == 200:
        result = response.json()
        print(f"Screenshot result: {result}")
    else:
        print(f"❌ Screenshot failed: {response.text}")
    
    # 8. Browser kapat
    print("\n8️⃣ Closing browser...")
    selenium_data = {
        "tool": "selenium_browser",
        "action": "close_browser",
        "params": {}
    }
    
    response = requests.post(f"{base_url}/api/mcp/execute", json=selenium_data, headers=headers)
    if response.status_code == 200:
        result = response.json()
        print(f"Browser close result: {result}")
    else:
        print(f"❌ Failed to close browser: {response.text}")
    
    print("\n✅ API test completed!")

if __name__ == "__main__":
    test_selenium_via_api()