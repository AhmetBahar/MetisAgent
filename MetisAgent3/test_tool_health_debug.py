#!/usr/bin/env python3
"""
Debug Tool Health Status

Direct health check testing to identify why command executor is showing unhealthy
"""

import os
import sys
import asyncio
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.managers.tool_manager import ToolManager
from tools.command_executor_tool import create_command_executor_tool_metadata


async def debug_tool_health():
    """Debug tool health status"""
    print("🔍 Debugging Tool Health Status")
    print("=" * 50)
    
    # Initialize tool manager
    tool_manager = ToolManager()
    
    # Load command executor tool
    metadata, config, tool_class = create_command_executor_tool_metadata()
    success = await tool_manager.load_tool(metadata, config)
    
    if not success:
        print("❌ Failed to load tool")
        return
    
    print("✅ Tool loaded successfully")
    
    # Get tool instance directly
    tool_instance = tool_manager.tools.get("command_executor")
    if not tool_instance:
        print("❌ Tool instance not found")
        return
    
    print(f"✅ Tool instance found: {type(tool_instance).__name__}")
    
    # Test direct health check
    print("\n🔍 Direct Health Check Test:")
    try:
        health_result = await tool_instance.health_check()
        print(f"   Health Status Type: {type(health_result)}")
        print(f"   Healthy: {health_result.healthy}")
        print(f"   Component: {health_result.component}")
        print(f"   Message: {health_result.message}")
        
        if hasattr(health_result, 'details') and health_result.details:
            print(f"   Details: {health_result.details}")
            
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
        import traceback
        traceback.print_exc()
    
    # Check stored health status
    print("\n🔍 Stored Health Status:")
    stored_health = tool_manager.health_status.get("command_executor")
    if stored_health:
        print(f"   Stored Healthy: {stored_health.healthy}")
        print(f"   Stored Message: {stored_health.message}")
    else:
        print("   ❌ No stored health status found")
    
    # Check tool state
    print("\n🔍 Tool State:")
    tool_state = tool_manager.tool_states.get("command_executor")
    if tool_state:
        print(f"   Tool State: {tool_state.value}")
    else:
        print("   ❌ No tool state found")
    
    # Test the underlying tool's health check directly (if it's NativeTool)
    if hasattr(tool_instance, 'tool_instance') and tool_instance.tool_instance:
        print("\n🔍 Underlying Tool Health Check:")
        try:
            underlying_health = await tool_instance.tool_instance.health_check()
            print(f"   Underlying Healthy: {underlying_health.healthy}")
            print(f"   Underlying Message: {underlying_health.message}")
        except Exception as e:
            print(f"   ❌ Underlying health check error: {e}")
    
    print("\n" + "=" * 50)
    print("🔍 Debug Complete!")


if __name__ == "__main__":
    asyncio.run(debug_tool_health())