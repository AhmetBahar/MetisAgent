#!/usr/bin/env python3
"""
Frontend Prompt Test - Arayüzden test edilebilecek promptlar
"""

import requests
import json

API_BASE = "http://localhost:5001/api"

def test_prompt(prompt, description):
    """Single prompt test"""
    print(f"\n🧪 Testing: {description}")
    print(f"📝 Prompt: {prompt}")
    print("-" * 60)
    
    try:
        response = requests.post(f"{API_BASE}/chat",
            json={
                "message": prompt,
                "user_id": "test_user",
                "provider": "openai",
                "model": "gpt-4o-mini"
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ Response received:")
                
                # LLM response
                llm_response = result.get('data', {}).get('response', '')
                print(f"💬 LLM: {llm_response[:200]}...")
                
                # Tool calls
                tool_results = result.get('data', {}).get('tool_results', [])
                if tool_results:
                    print(f"🔧 Tools executed: {len(tool_results)}")
                    for i, tool_result in enumerate(tool_results):
                        tool_name = tool_result.get('tool_name', 'unknown')
                        action = tool_result.get('action', 'unknown')
                        success = tool_result.get('success', False)
                        print(f"   {i+1}. {tool_name}.{action}: {'✅' if success else '❌'}")
                        if not success:
                            print(f"      Error: {tool_result.get('error', 'Unknown error')}")
                else:
                    print("⚠️ No tools executed")
                    
            else:
                print(f"❌ Request failed: {result.get('error')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Test error: {e}")

def main():
    """Test çeşitli promptlar"""
    print("🚀 Frontend Prompt Test Suite")
    print("=" * 60)
    print("Backend'de tool coordination ve enhanced prompts test ediliyor")
    
    # Backend health check
    try:
        health_response = requests.get(f"{API_BASE}/health", timeout=5)
        if health_response.status_code == 200:
            print("✅ Backend çalışıyor")
        else:
            print("❌ Backend sorunlu")
            return
    except:
        print("❌ Backend'e bağlanılamadı")
        return
    
    # Test prompts
    test_cases = [
        # Selenium Tests
        ("headless modda minor.com.tr web sitesinin başlığını oku", "Selenium - Web Title"),
        ("browser aç ve google.com'a git", "Selenium - Basic Navigation"),
        ("web site screenshot al", "Selenium - Screenshot"),
        ("gemini web sitesini aç", "Selenium - Gemini Navigation"),
        
        # OAuth2 Tests  
        ("oauth2 durumunu kontrol et", "OAuth2 - Status Check"),
        ("google api authentication", "OAuth2 - Authentication"),
        ("gmail messages listele", "OAuth2 - Gmail API"),
        
        # Command Tests
        ("ls komutunu çalıştır", "Command - Basic"),
        ("pwd komutu", "Command - PWD"),
        
        # Mixed/General Tests
        ("web automation ile google arama yap", "Mixed - Web + Search"),
        ("sistem bilgilerini göster", "General - System Info")
    ]
    
    for prompt, description in test_cases:
        test_prompt(prompt, description)
        print("\n" + "="*60)
    
    print("\n🎯 RECOMMENDATION FOR FRONTEND TESTING:")
    print("\n🌐 Selenium Web Automation Prompts:")
    print('- "headless modda minor.com.tr web sitesinin başlığını oku"')
    print('- "selenium ile google.com\'a git ve arama yap"')
    print('- "gemini web sitesini aç ve screenshot al"')
    print('- "browser automation ile form doldur"')
    
    print("\n🔐 OAuth2 Google API Prompts:")
    print('- "oauth2 durumunu kontrol et"')
    print('- "google api ile gmail mesajlarımı listele"')
    print('- "google drive dosyalarımı göster"')
    print('- "gmail api ile email gönder"')
    
    print("\n🔧 System Command Prompts:")
    print('- "ls komutu ile dosyaları listele"')
    print('- "pwd komutu çalıştır"')
    print('- "sistem bilgilerini göster"')
    
    print("\n💡 Enhanced Prompt Features:")
    print("✅ Tool pattern recognition")
    print("✅ Automatic tool suggestion")
    print("✅ JSON response formatting")
    print("✅ Action parameter guidance")
    print("✅ Turkish language support")

if __name__ == "__main__":
    main()