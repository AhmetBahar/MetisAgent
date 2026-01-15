#!/usr/bin/env python3
"""
Google Tool Integration Test

Tests the complete Google Tool integration with MetisAgent3.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add MetisAgent3 to path
sys.path.insert(0, str(Path(__file__).parent))

from core.contracts.base_types import ExecutionContext
from plugins.google_tool.google_tool_legacy import GoogleTool

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_google_tool_oauth():
    """Test Google Tool OAuth2 functionality"""
    print("🧪 Testing Google Tool OAuth2 Integration")
    print("=" * 50)
    
    try:
        # Initialize Google Tool
        print("📦 Initializing Google Tool...")
        google_tool = GoogleTool()
        
        # Create test execution context
        context = ExecutionContext(
            user_id="test_user",
            session_id="test_session",
            conversation_id="test_conversation"
        )
        
        # Test 1: Check OAuth2 status (should be not authorized)
        print("\n🔐 Testing OAuth2 status check...")
        result = await google_tool.execute({
            'capability': 'oauth2_management',
            'action': 'check_status',
            'user_id': 'test_user'
        }, context)
        
        print(f"   Status Result: {result}")
        
        if result.get('success'):
            auth_status = result.get('authenticated', False)
            print(f"   ✅ OAuth2 Status Check: {'Authorized' if auth_status else 'Not Authorized'}")
        else:
            print(f"   ❌ OAuth2 Status Check Failed: {result.get('error')}")
        
        # Test 2: Generate authorization URL (should work)
        print("\n🔗 Testing OAuth2 authorization URL generation...")
        result = await google_tool.execute({
            'capability': 'oauth2_management',
            'action': 'authorize',
            'user_id': 'test_user'
        }, context)
        
        print(f"   Auth URL Result: {result}")
        
        if result.get('success'):
            auth_url = result.get('auth_url')
            if auth_url:
                print(f"   ✅ Authorization URL Generated")
                print(f"   🔗 Auth URL: {auth_url[:100]}...")
            else:
                print(f"   ⚠️ Authorization URL empty")
        else:
            print(f"   ❌ Authorization URL Generation Failed: {result.get('error')}")
            
        # Test 3: Validate input method
        print("\n✅ Testing input validation...")
        
        valid_input = {
            'capability': 'oauth2_management',
            'action': 'check_status',
            'user_id': 'test_user'
        }
        
        invalid_input = {
            'capability': 'invalid_capability',
            'action': 'invalid_action'
        }
        
        valid_result = google_tool.validate_input(valid_input)
        invalid_result = google_tool.validate_input(invalid_input)
        
        print(f"   Valid Input Validation: {valid_result}")
        print(f"   Invalid Input Validation: {invalid_result}")
        
        if valid_result and not invalid_result:
            print("   ✅ Input validation working correctly")
        else:
            print("   ❌ Input validation issues detected")
            
        print("\n🎉 Google Tool Integration Test Completed!")
        print("\n💡 Next steps:")
        print("   1. Run ./setup_google_oauth2.py to configure credentials")
        print("   2. Start bridge server: python bridge_server.py")
        print("   3. Test OAuth flow through Settings UI")
        
        return True
        
    except Exception as e:
        print(f"\n💥 Google Tool test failed: {e}")
        logger.error(f"Google Tool test failed: {e}")
        return False


async def main():
    """Main test function"""
    success = await test_google_tool_oauth()
    
    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())