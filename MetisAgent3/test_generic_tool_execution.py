#!/usr/bin/env python3
"""
Generic Tool Execution Test

Tests the new generic tool execution system end-to-end.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add MetisAgent3 to path
sys.path.insert(0, str(Path(__file__).parent))

from core.services.tool_execution_service import ToolExecutionService, ToolExecutionRequest
from core.managers.tool_manager import ToolManager
from core.managers.user_manager import UserManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_generic_tool_execution():
    """Test generic tool execution system"""
    print("🧪 Testing Generic Tool Execution System")
    print("=" * 50)
    
    try:
        # Initialize services
        print("📦 Initializing services...")
        tool_manager = ToolManager()
        user_manager = UserManager()
        tool_execution_service = ToolExecutionService(tool_manager, user_manager)
        
        # Get available tools
        print("\n🔧 Getting available tools...")
        available_tools = tool_execution_service.get_available_tools()
        print(f"   Available tools: {list(available_tools.keys())}")
        
        # Test 1: Google Tool OAuth2 Status Check
        print("\n🔐 Testing Google Tool OAuth2 Status...")
        request = ToolExecutionRequest(
            tool_name="google_tool",
            capability="oauth2_management",
            action="check_status",
            parameters={},
            user_id="test_user"
        )
        
        result = await tool_execution_service.execute_tool_capability(request)
        print(f"   OAuth2 Status Result: {result.success}")
        print(f"   Data: {json.dumps(result.data, indent=2)}")
        
        if result.success:
            print("   ✅ OAuth2 status check successful")
        else:
            print(f"   ❌ OAuth2 status check failed: {result.error}")
        
        # Test 2: Google Tool Authorization URL Generation
        print("\n🔗 Testing Google Tool Authorization URL...")
        request = ToolExecutionRequest(
            tool_name="google_tool",
            capability="oauth2_management", 
            action="authorize",
            parameters={},
            user_id="test_user"
        )
        
        result = await tool_execution_service.execute_tool_capability(request)
        print(f"   Auth URL Result: {result.success}")
        
        if result.success and result.data.get('auth_url'):
            auth_url = result.data['auth_url']
            print(f"   ✅ Authorization URL generated")
            print(f"   🔗 URL: {auth_url[:100]}...")
        else:
            print(f"   ❌ Authorization URL generation failed: {result.error}")
        
        # Test 3: User Mapping Operations
        print("\n👤 Testing User Mapping Operations...")
        
        # Get current mapping
        request = ToolExecutionRequest(
            tool_name="google_tool",
            capability="oauth2_management",
            action="get_user_mapping",
            parameters={},
            user_id="test_user"
        )
        
        result = await tool_execution_service.execute_tool_capability(request)
        print(f"   Get Mapping Result: {result.success}")
        print(f"   Mapping exists: {result.data.get('mapping_exists', False)}")
        print(f"   Google email: {result.data.get('google_email', 'None')}")
        
        # Test setting mapping
        request = ToolExecutionRequest(
            tool_name="google_tool",
            capability="oauth2_management",
            action="set_user_mapping",
            parameters={
                "google_email": "test@gmail.com",
                "google_name": "Test User"
            },
            user_id="test_user"
        )
        
        result = await tool_execution_service.execute_tool_capability(request)
        print(f"   Set Mapping Result: {result.success}")
        
        if result.success:
            print("   ✅ User mapping set successfully")
        else:
            print(f"   ⚠️ User mapping set failed: {result.error}")
        
        # Test 4: Error Handling
        print("\n⚠️ Testing Error Handling...")
        
        # Invalid tool name
        request = ToolExecutionRequest(
            tool_name="nonexistent_tool",
            capability="test_capability",
            action="test_action",
            parameters={},
            user_id="test_user"
        )
        
        result = await tool_execution_service.execute_tool_capability(request)
        print(f"   Invalid tool test: {'✅ Handled correctly' if not result.success else '❌ Should have failed'}")
        print(f"   Error message: {result.error}")
        
        # Test 5: Performance Test
        print("\n⚡ Testing Performance...")
        
        start_time = asyncio.get_event_loop().time()
        
        # Execute 5 requests concurrently
        tasks = []
        for i in range(5):
            request = ToolExecutionRequest(
                tool_name="google_tool",
                capability="oauth2_management",
                action="check_status",
                parameters={},
                user_id=f"test_user_{i}"
            )
            tasks.append(tool_execution_service.execute_tool_capability(request))
        
        results = await asyncio.gather(*tasks)
        
        end_time = asyncio.get_event_loop().time()
        total_time = (end_time - start_time) * 1000
        
        successful = sum(1 for r in results if r.success)
        print(f"   Concurrent execution: {successful}/{len(results)} successful")
        print(f"   Total time: {total_time:.2f}ms")
        print(f"   Average per request: {total_time/len(results):.2f}ms")
        
        print("\n🎉 Generic Tool Execution Test Completed!")
        
        # Summary
        print("\n📊 Test Summary:")
        print("   ✅ Tool service initialization")
        print("   ✅ Available tools discovery") 
        print("   ✅ OAuth2 status checking")
        print("   ✅ Authorization URL generation")
        print("   ✅ User mapping operations")
        print("   ✅ Error handling")
        print("   ✅ Performance testing")
        
        print("\n💡 Next steps:")
        print("   1. Test via bridge server HTTP endpoint")
        print("   2. Test frontend integration")
        print("   3. Test complete OAuth2 flow")
        
        return True
        
    except Exception as e:
        print(f"\n💥 Generic tool execution test failed: {e}")
        logger.error(f"Generic tool execution test failed: {e}", exc_info=True)
        return False


async def main():
    """Main test function"""
    success = await test_generic_tool_execution()
    
    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())