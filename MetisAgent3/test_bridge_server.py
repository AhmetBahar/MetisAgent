#!/usr/bin/env python3
"""
Test Bridge Server - Comprehensive Bridge Server Testing

Tests the bridge server initialization, API endpoints and MetisAgent3 integration
"""

import requests
import json
import time
from datetime import datetime

def test_bridge_server():
    """Test bridge server endpoints"""
    print("🧪 Testing MetisAgent3 Bridge Server")
    print("=" * 50)
    
    base_url = "http://localhost:5001"
    
    # Test 1: Health Check
    print("\n1. 🏥 Testing Health Check...")
    try:
        response = requests.get(f"{base_url}/api/health", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            health_data = response.json()
            print(f"   ✅ Bridge Status: {health_data.get('data', {}).get('status', 'unknown')}")
            print(f"   ✅ Backend: {health_data.get('data', {}).get('metis_agent3_backend', 'unknown')}")
            
            services = health_data.get('data', {}).get('services', {})
            for service, status in services.items():
                icon = "✅" if status else "❌"
                print(f"   {icon} {service}: {'Ready' if status else 'Not Ready'}")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
    
    # Test 2: Providers
    print("\n2. 🤖 Testing LLM Providers...")
    try:
        response = requests.get(f"{base_url}/api/providers", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            providers_data = response.json()
            providers = providers_data.get('data', [])
            print(f"   ✅ Found {len(providers)} providers")
            for provider in providers:
                name = provider.get('name', 'Unknown')
                available = provider.get('available', False)
                models = provider.get('models', [])
                icon = "✅" if available else "❌"
                print(f"   {icon} {name}: {'Available' if available else 'Not Available'} ({len(models)} models)")
        else:
            print(f"   ❌ Providers failed: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Providers error: {e}")
    
    # Test 3: Tools
    print("\n3. 🔧 Testing Tools Endpoint...")
    try:
        response = requests.get(f"{base_url}/api/tools", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            tools_data = response.json()
            if tools_data.get('success'):
                tools = tools_data.get('data', {}).get('tools', [])
                print(f"   ✅ Found {len(tools)} tools")
                for tool in tools:
                    name = tool.get('name', 'Unknown')
                    tool_type = tool.get('type', 'unknown')
                    capabilities = tool.get('capabilities', [])
                    print(f"      • {name} ({tool_type}): {len(capabilities)} capabilities")
            else:
                print(f"   ❌ Tools response unsuccessful: {tools_data.get('error')}")
        else:
            print(f"   ❌ Tools failed: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Tools error: {e}")
    
    # Test 4: Simple Chat Test
    print("\n4. 💬 Testing Chat Endpoint...")
    try:
        chat_payload = {
            "message": "Hello, this is a test message",
            "provider": "openai",
            "model": "gpt-4",
            "conversation_id": "test_conversation"
        }
        
        response = requests.post(
            f"{base_url}/api/chat", 
            json=chat_payload,
            timeout=30
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            chat_data = response.json()
            if chat_data.get('success'):
                response_text = chat_data.get('data', {}).get('response', '')
                print(f"   ✅ Chat successful")
                print(f"   Response: {response_text[:100]}{'...' if len(response_text) > 100 else ''}")
            else:
                print(f"   ❌ Chat unsuccessful: {chat_data.get('error')}")
        else:
            print(f"   ❌ Chat failed: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Chat error: {e}")
    
    # Test 5: Tool Execution
    print("\n5. ⚡ Testing Tool Execution...")
    try:
        # Test command executor if available
        tool_payload = {
            "action": "get_platform_info",
            "params": {}
        }
        
        response = requests.post(
            f"{base_url}/api/tools/command_executor/execute",
            json=tool_payload,
            timeout=15
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            tool_data = response.json()
            if tool_data.get('success'):
                platform_info = tool_data.get('data', {})
                system = platform_info.get('system', 'Unknown')
                print(f"   ✅ Tool execution successful")
                print(f"   Platform: {system}")
            else:
                print(f"   ❌ Tool execution unsuccessful: {tool_data.get('error')}")
        else:
            print(f"   ❌ Tool execution failed: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Tool execution error: {e}")
    
    print("\n" + "=" * 50)
    print(f"✅ Bridge Server Testing Complete!")
    print(f"🕒 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    print("⏰ Waiting 3 seconds for bridge server to be ready...")
    time.sleep(3)
    test_bridge_server()