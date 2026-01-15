#!/usr/bin/env python3
"""
Test Command Executor Plugin Registration

Tests the registration and loading of command executor as a plugin in MetisAgent3
"""

import os
import sys
import asyncio
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.managers.tool_manager import ToolManager
from core.contracts.tool_contracts import ToolType
from core.services.conversation_service import ConversationService
from tools.command_executor_tool import create_command_executor_tool_metadata


async def test_command_executor_plugin_registration():
    """Test command executor tool registration and loading"""
    print("🚀 Testing Command Executor Plugin Registration")
    print("=" * 50)
    
    # Initialize services
    print("\n1. 🔧 Initializing Services...")
    
    conv_service = ConversationService()
    
    # Initialize tool manager (without graph memory for now)
    tool_manager = ToolManager()
    
    print("   ✅ Services initialized")
    
    # Test 2: Register Command Executor Tool
    print("\n2. 📝 Registering Command Executor Tool...")
    try:
        # Get tool metadata and configuration
        metadata, config, tool_class = create_command_executor_tool_metadata()
        
        # Load the tool
        success = await tool_manager.load_tool(metadata, config)
        
        if success:
            print(f"   ✅ Tool registered successfully: {metadata.name}")
        else:
            print(f"   ❌ Tool registration failed: {metadata.name}")
        
    except Exception as e:
        print(f"   ❌ Registration error: {e}")
    
    # Test 3: List Registered Tools  
    print("\n3. 📋 Listing Registered Tools...")
    try:
        tools = await tool_manager.list_tools()
        print(f"   Total registered tools: {len(tools)}")
        
        for tool_name in tools:
            # Get tool from registry
            if tool_name in tool_manager.registry.tools:
                tool_meta = tool_manager.registry.tools[tool_name]
                print(f"   • {tool_name}: {tool_meta.tool_type.value} - {tool_meta.description[:60]}...")
                
    except Exception as e:
        print(f"   ❌ Error listing tools: {e}")
    
    # Test 4: Get Command Executor Tool Info
    print("\n4. 🔍 Command Executor Tool Details...")
    try:
        cmd_metadata = tool_manager.registry.get_tool_metadata("command_executor")
        cmd_config = tool_manager.registry.get_tool_config("command_executor")
        
        if cmd_metadata:
            print(f"   Name: {cmd_metadata.name}")
            print(f"   Type: {cmd_metadata.tool_type.value}")
            print(f"   Version: {cmd_metadata.version}")
            print(f"   Capabilities: {len(cmd_metadata.capabilities)}")
            print(f"   Author: {cmd_metadata.author}")
            print(f"   Tags: {', '.join(cmd_metadata.tags)}")
            
        if cmd_config:
            print(f"   Plugin Type: {cmd_config.config.get('plugin_type')}")
            print(f"   Module Path: {cmd_config.config.get('module_path')}")
            print(f"   Class Name: {cmd_config.config.get('class_name')}")
            print(f"   Enabled: {cmd_config.enabled}")
            
    except Exception as e:
        print(f"   ❌ Error getting tool details: {e}")
    
    # Test 5: Load Command Executor Tool Instance
    print("\n5. 🚀 Loading Command Executor Tool Instance...")
    try:
        # Get tool instance from loaded tools
        tool_instance = tool_manager.tools.get("command_executor")
        
        if tool_instance:
            print(f"   ✅ Tool instance loaded: {type(tool_instance).__name__}")
            
            # Test a capability  
            from core.contracts.base_types import ExecutionContext
            context = ExecutionContext(user_id="test_user", session_id="test_session")
            
            # Test platform info
            result = await tool_instance.execute("get_platform_info", {}, context)
            if result.success:
                print(f"   ✅ Platform info test passed: {result.data.get('system')}")
            else:
                print(f"   ❌ Platform info test failed: {result.error}")
                
            # Test command validation
            result = await tool_instance.execute("validate_command", {"command": "ls -la"}, context)
            if result.success:
                is_safe = result.data.get("is_safe", False)
                print(f"   ✅ Command validation test passed: 'ls -la' is {'safe' if is_safe else 'unsafe'}")
            else:
                print(f"   ❌ Command validation test failed: {result.error}")
                
        else:
            print(f"   ❌ Failed to load tool instance")
        
    except Exception as e:
        print(f"   ❌ Error loading tool instance: {e}")
    
    # Test 6: Tool Manager Health Check
    print("\n6. 💊 Tool Manager Health Check...")
    try:
        health_report = await tool_manager.get_health_report()
        print(f"   System Status: {health_report.get('system_status', 'unknown')}")
        print(f"   System Uptime: {health_report.get('summary', {}).get('system_uptime', 'unknown')}")
        print(f"   Total tools: {health_report.get('total_tools', 0)}")
        print(f"   Healthy tools: {health_report.get('healthy_tools', 0)}")
        print(f"   Failed tools: {health_report.get('failed_tools', 0)}")
        print(f"   Running tools: {health_report.get('running_tools', 0)}")
        
        if "tools" in health_report:
            for tool_name, status in health_report["tools"].items():
                is_healthy = status.get("health", False)
                state = status.get("state", "unknown")
                health_icon = "✅" if is_healthy else "❌"
                print(f"   {health_icon} {tool_name}: {state} - {'healthy' if is_healthy else 'unhealthy'}")
                
                # Show circuit breaker status
                cb_status = status.get("circuit_breaker", {})
                can_execute = cb_status.get("can_execute", False)
                failure_count = cb_status.get("failure_count", 0)
                print(f"      Circuit Breaker: {'OPEN' if can_execute else 'CLOSED'} (failures: {failure_count})")
                
    except Exception as e:
        print(f"   ❌ Error getting health report: {e}")
    
    # Test 7: Registry Info
    print("\n7. 📊 Tool Registry Information...")
    try:
        registry_info = await tool_manager.get_registry_info()
        print(f"   Registry Version: {registry_info.get('version', 'Unknown')}")
        print(f"   Last Updated: {registry_info.get('last_updated', 'Unknown')[:19]}")  # Show date part only
        print(f"   Registry Tools: {registry_info.get('total_tools', 0)}")
        print(f"   Healthy Tools: {registry_info.get('healthy_tools', 0)}")
        print(f"   Failed Tools: {registry_info.get('failed_tools', 0)}")
        
        # Show tool type distribution
        tool_types = registry_info.get("tool_types", {})
        print(f"   Tool Types: {', '.join([f'{t}({c})' for t, c in tool_types.items() if c > 0])}")
        
        # Show individual tool info
        tools_info = registry_info.get("tools", {})
        for tool_name, info in tools_info.items():
            tool_type = info.get("type", "unknown")
            status = info.get("status", "unknown")
            health = "healthy" if info.get("health", False) else "unhealthy"
            capabilities = len(info.get("capabilities", []))
            version = info.get("version", "Unknown")
            author = info.get("author", "Unknown")
            print(f"     • {tool_name} v{version}: {tool_type} - {status} - {health} - {capabilities} caps - by {author}")
            
    except Exception as e:
        print(f"   ❌ Error getting registry info: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Command Executor Plugin Registration Test Complete!")


if __name__ == "__main__":
    asyncio.run(test_command_executor_plugin_registration())