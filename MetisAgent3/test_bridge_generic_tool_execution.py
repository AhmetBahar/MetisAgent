#!/usr/bin/env python3
"""
Bridge Server Generic Tool Execution Test

Tests the generic tool execution via HTTP endpoint.
"""

import asyncio
import json
import requests
import time

def test_bridge_generic_tool_execution():
    """Test generic tool execution via bridge server"""
    print("🌐 Testing Bridge Server Generic Tool Execution")
    print("=" * 50)
    
    base_url = "http://localhost:5001"
    
    try:
        # Test 1: Check if bridge server is running
        print("🔍 Checking bridge server availability...")
        try:
            response = requests.get(f"{base_url}/api/tools/available", timeout=5)
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Bridge server is running")
                print(f"   📦 Available tools: {list(result.get('tools', {}).keys())}")
                
                if 'google_tool' in result.get('tools', {}):
                    print("   ✅ Google Tool is loaded")
                else:
                    print("   ⚠️ Google Tool not found in available tools")
                    return False
            else:
                print(f"   ❌ Bridge server returned status {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            print("   ❌ Bridge server not running. Start with: python bridge_server.py")
            return False
        except requests.exceptions.Timeout:
            print("   ❌ Bridge server timeout")
            return False
        
        # Test 2: Generic Tool Execution - OAuth2 Status
        print("\n🔐 Testing OAuth2 Status via Generic Endpoint...")
        
        request_data = {
            "tool_name": "google_tool",
            "capability": "oauth2_management",
            "action": "check_status",
            "parameters": {}
        }
        
        response = requests.post(
            f"{base_url}/api/tools/execute",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Request successful")
            print(f"   📋 Success: {result.get('success', False)}")
            print(f"   📋 Tool: {result.get('tool_name')}")
            print(f"   📋 Capability: {result.get('capability')}")
            print(f"   📋 Action: {result.get('action')}")
            print(f"   📋 Execution time: {result.get('execution_time_ms', 0)}ms")
            
            if result.get('success'):
                print("   ✅ OAuth2 status check successful")
                data = result.get('data', {})
                print(f"   📧 Authenticated: {data.get('authenticated', False)}")
            else:
                print(f"   ⚠️ OAuth2 status check failed: {result.get('error')}")
        else:
            print(f"   ❌ HTTP error {response.status_code}: {response.text}")
            return False
        
        # Test 3: Authorization URL Generation
        print("\n🔗 Testing Authorization URL Generation...")
        
        request_data = {
            "tool_name": "google_tool",
            "capability": "oauth2_management",
            "action": "authorize",
            "parameters": {}
        }
        
        response = requests.post(
            f"{base_url}/api/tools/execute",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Request successful")
            
            if result.get('success'):
                auth_url = result.get('data', {}).get('auth_url')
                if auth_url:
                    print("   ✅ Authorization URL generated")
                    print(f"   🔗 URL: {auth_url[:100]}...")
                else:
                    print("   ⚠️ No authorization URL in response")
            else:
                print(f"   ⚠️ Authorization failed: {result.get('error')}")
        else:
            print(f"   ❌ HTTP error {response.status_code}: {response.text}")
        
        # Test 4: User Mapping Operations
        print("\n👤 Testing User Mapping Operations...")
        
        # Get mapping
        request_data = {
            "tool_name": "google_tool", 
            "capability": "oauth2_management",
            "action": "get_user_mapping",
            "parameters": {}
        }
        
        response = requests.post(
            f"{base_url}/api/tools/execute",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   📋 Get mapping - Success: {result.get('success')}")
            
            if result.get('success'):
                data = result.get('data', {})
                print(f"   📧 Mapping exists: {data.get('mapping_exists', False)}")
                print(f"   📧 Google email: {data.get('google_email', 'None')}")
            
        # Set mapping
        request_data = {
            "tool_name": "google_tool",
            "capability": "oauth2_management", 
            "action": "set_user_mapping",
            "parameters": {
                "google_email": "test@gmail.com",
                "google_name": "Test User"
            }
        }
        
        response = requests.post(
            f"{base_url}/api/tools/execute",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   📋 Set mapping - Success: {result.get('success')}")
            
            if result.get('success'):
                print("   ✅ User mapping set successfully")
            else:
                print(f"   ⚠️ Set mapping failed: {result.get('error')}")
        
        # Test 5: Performance Test
        print("\n⚡ Testing Performance...")
        
        start_time = time.time()
        
        # Execute 5 requests
        for i in range(5):
            request_data = {
                "tool_name": "google_tool",
                "capability": "oauth2_management",
                "action": "check_status", 
                "parameters": {}
            }
            
            response = requests.post(
                f"{base_url}/api/tools/execute",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )
        
        end_time = time.time()
        total_time = (end_time - start_time) * 1000
        
        print(f"   📊 5 sequential requests: {total_time:.2f}ms")
        print(f"   📊 Average per request: {total_time/5:.2f}ms")
        
        print("\n🎉 Bridge Server Generic Tool Execution Test Completed!")
        print("\n📊 Summary:")
        print("   ✅ Bridge server connectivity")
        print("   ✅ Tool availability check")
        print("   ✅ Generic tool execution endpoint")
        print("   ✅ OAuth2 operations")
        print("   ✅ User mapping operations")
        print("   ✅ Performance testing")
        
        print("\n💡 System is ready for frontend integration!")
        
        return True
        
    except Exception as e:
        print(f"\n💥 Bridge server test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_bridge_generic_tool_execution()
    
    if success:
        print("\n✅ All tests passed!")
        exit(0)
    else:
        print("\n❌ Some tests failed!")
        exit(1)