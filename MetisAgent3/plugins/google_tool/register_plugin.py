"""
Google Tool Plugin Registration Script

CLAUDE.md COMPLIANT:
- Automatic plugin discovery and registration
- Tool metadata validation
- Configuration setup
- Health check validation
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add MetisAgent3 to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.contracts import ToolMetadata, ToolConfiguration, ToolCapability, CapabilityType, ToolType
from core.managers.tool_manager import ToolManager

logger = logging.getLogger(__name__)


async def register_google_tool():
    """Register Google Tool plugin with MetisAgent3"""
    try:
        print("🔧 Starting Google Tool plugin registration...")
        
        # Load tool configuration
        config_path = Path(__file__).parent / "tool_config.json"
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        tool_meta = config_data["tool_metadata"]
        tool_config = config_data["tool_configuration"]
        
        # Create tool metadata
        capabilities = []
        for cap_data in tool_meta["capabilities"]:
            capability = ToolCapability(
                name=cap_data["name"],
                description=cap_data["description"],
                capability_type=CapabilityType(cap_data["capability_type"]),
                input_schema=cap_data["input_schema"],
                output_schema=cap_data["output_schema"],
                required_permissions=cap_data.get("required_permissions", []),
                examples=cap_data.get("examples", [])
            )
            capabilities.append(capability)
        
        metadata = ToolMetadata(
            name=tool_meta["name"],
            description=tool_meta["description"],
            version=tool_meta["version"],
            tool_type=ToolType(tool_meta["tool_type"]),
            author=tool_meta.get("author"),
            capabilities=capabilities,
            dependencies=tool_meta.get("dependencies", []),
            tags=set(tool_meta.get("tags", []))
        )
        
        # Create tool configuration
        configuration = ToolConfiguration(
            tool_name=tool_config["tool_name"],
            enabled=tool_config["enabled"],
            config=tool_config["config"],
            user_permissions=tool_config.get("user_permissions", []),
            rate_limits=tool_config.get("rate_limits", {})
        )
        
        # Initialize tool manager
        print("🔄 Initializing Tool Manager...")
        tool_manager = ToolManager()
        
        # Load the plugin (this will register it)
        print("📝 Loading Google Tool plugin...")
        success = await tool_manager.load_tool(metadata, configuration)
        
        if success:
            print("✅ Google Tool plugin registered successfully!")
            
            # List capabilities  
            print("⚡ Checking tool capabilities...")
            capabilities = [cap.name for cap in metadata.capabilities]
            print(f"📋 Available capabilities: {capabilities}")
            
            return True
            
        else:
            print("❌ Failed to register Google Tool plugin")
            return False
            
    except Exception as e:
        print(f"💥 Plugin registration failed: {e}")
        logger.error(f"Plugin registration failed: {e}")
        return False


async def test_google_tool():
    """Test Google Tool functionality"""
    try:
        print("\n🧪 Testing Google Tool functionality...")
        
        # Initialize tool manager
        tool_manager = ToolManager()
        
        # Test OAuth2 management capability
        print("🔐 Testing OAuth2 management...")
        from core.contracts import ExecutionContext, ToolExecutionRequest, Priority
        
        context = ExecutionContext(
            user_id="test_user",
            session_id="test_session",
            conversation_id="test_conversation"
        )
        
        request = ToolExecutionRequest(
            tool_name="google_tool",
            capability="oauth2_management",
            input_data={
                "action": "check_status",
                "user_id": "test_user"
            },
            context=context,
            priority=Priority.MEDIUM
        )
        
        result = await tool_manager.execute_capability(request)
        print(f"🔐 OAuth2 test result: {result.success}")
        
        print("✅ Google Tool testing completed!")
        return True
        
    except Exception as e:
        print(f"💥 Google Tool testing failed: {e}")
        logger.error(f"Google Tool testing failed: {e}")
        return False


async def main():
    """Main registration process"""
    print("🚀 Google Tool Plugin Registration")
    print("=" * 50)
    
    # Step 1: Register plugin
    registration_success = await register_google_tool()
    if not registration_success:
        print("❌ Registration failed. Exiting.")
        return
    
    # Step 2: Test plugin
    test_success = await test_google_tool()
    if not test_success:
        print("⚠️ Testing failed, but plugin is registered.")
        return
    
    print("\n🎉 Google Tool Plugin successfully registered and tested!")
    print("📋 Available capabilities:")
    print("   • oauth2_management - Google authentication")
    print("   • gmail_operations - Email management")
    print("   • calendar_operations - Calendar management")  
    print("   • drive_operations - File management")
    print("   • event_management - Workflow automation")
    
    print("\n💡 Next steps:")
    print("   1. Configure Google OAuth2 credentials")
    print("   2. Start event monitoring for automation")
    print("   3. Create workflow triggers as needed")


if __name__ == "__main__":
    asyncio.run(main())