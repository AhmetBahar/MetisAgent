#!/usr/bin/env python3
"""
Test Command Executor Tool Migration - MCP Compatible Testing

Tests the migrated command executor tool with all capabilities:
1. Basic command execution
2. Security validation 
3. Platform info retrieval
4. ZIP operations
5. Error handling and edge cases
"""

import os
import sys
import asyncio
import tempfile
import zipfile
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tools.command_executor_tool import CommandExecutorTool
from core.contracts.tool_contracts import ToolCapability, CapabilityType
from core.contracts.base_types import ExecutionContext
from core.services.conversation_service import ConversationService


async def test_command_executor():
    """Test all command executor capabilities"""
    print("🚀 Testing Command Executor Tool Migration")
    print("=" * 50)
    
    # Initialize conversation service (mock for testing)
    conv_service = ConversationService()
    
    # Initialize command executor tool  
    tool = CommandExecutorTool(conversation_service=conv_service)
    
    # Create execution context for all tests
    context = ExecutionContext(user_id="test_user", session_id="test_session")
    
    # Test 1: Get Tool Information
    print("\n1. 🔍 Tool Information:")
    print(f"   Name: {tool.metadata.name}")
    print(f"   Description: {tool.metadata.description}")
    print(f"   Version: {tool.metadata.version}")
    print(f"   Capabilities: {len(tool.metadata.capabilities)}")
    
    # Test 2: List All Capabilities
    print("\n2. 📋 Available Capabilities:")
    for cap in tool.metadata.capabilities:
        print(f"   • {cap.name}: {cap.description}")
    
    # Test 3: Platform Information
    print("\n3. 🖥️  Platform Information:")
    try:
        platform_result = await tool.execute("get_platform_info", {}, context)
        if platform_result.success:
            data = platform_result.data
            print(f"   Platform: {data.get('system')}")
            print(f"   Architecture: {data.get('machine')}")
            print(f"   Python Version: {data.get('python_version')}")
        else:
            print(f"   ❌ Error: {platform_result.error}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 4: Command Validation (Safe Commands)
    print("\n4. ✅ Command Validation (Safe):")
    safe_commands = [
        "ls -la",
        "echo 'Hello World'",
        "python --version",
        "pwd"
    ]
    
    for cmd in safe_commands:
        try:
            validation_result = await tool.execute("validate_command", {"command": cmd}, context)
            if validation_result.success:
                is_safe = validation_result.data.get("is_safe", False)
                status = "✅ SAFE" if is_safe else "❌ UNSAFE"
                print(f"   {cmd:20} -> {status}")
            else:
                print(f"   {cmd:20} -> ❌ Error: {validation_result.error}")
        except Exception as e:
            print(f"   {cmd:20} -> ❌ Error: {e}")
    
    # Test 5: Command Validation (Dangerous Commands)  
    print("\n5. 🚨 Command Validation (Dangerous):")
    dangerous_commands = [
        "rm -rf /",
        "format c:",
        "shutdown -h now",
        "del C:\\Windows\\System32"
    ]
    
    for cmd in dangerous_commands:
        try:
            validation_result = await tool.execute("validate_command", {"command": cmd}, context)
            if validation_result.success:
                is_safe = validation_result.data.get("is_safe", False)
                status = "✅ SAFE" if is_safe else "❌ UNSAFE"
                print(f"   {cmd:20} -> {status}")
            else:
                print(f"   {cmd:20} -> ❌ Error: {validation_result.error}")
        except Exception as e:
            print(f"   {cmd:20} -> ❌ Error: {e}")
    
    # Test 6: Simple Command Execution
    print("\n6. 🚀 Command Execution:")
    simple_commands = [
        "echo 'MetisAgent3 Test'",
        "python --version",
        "pwd"
    ]
    
    for cmd in simple_commands:
        try:
            exec_result = await tool.execute("execute_command", {"command": cmd}, context)
            if exec_result.success:
                data = exec_result.data
                print(f"   Command: {cmd}")
                print(f"   Return Code: {data.get('return_code')}")
                print(f"   Output: {data.get('stdout', '')[:100]}...")
                print(f"   Error: {data.get('stderr', 'None')}")
                print()
            else:
                print(f"   ❌ Error executing '{cmd}': {exec_result.error}")
                print()
        except Exception as e:
            print(f"   ❌ Error executing '{cmd}': {e}")
    
    # Test 7: ZIP Operations  
    print("\n7. 📦 ZIP Operations Test:")
    
    # Create temporary test files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test files
        test_file1 = temp_path / "test1.txt"
        test_file2 = temp_path / "test2.txt"
        test_file1.write_text("This is test file 1")
        test_file2.write_text("This is test file 2")
        
        zip_path = temp_path / "test.zip"
        
        # Test create_zip
        try:
            create_result = await tool.execute("create_zip", {
                "zip_path": str(zip_path),
                "source_path": str(temp_path)
            }, context)
            if create_result.success:
                print(f"   Create ZIP: ✅ Success - {create_result.data.get('total_files', 0)} files added")
            else:
                print(f"   Create ZIP: ❌ Failed - {create_result.error}")
        except Exception as e:
            print(f"   ❌ Create ZIP Error: {e}")
        
        # Test list_zip_contents
        if zip_path.exists():
            try:
                list_result = await tool.execute("list_zip_contents", {
                    "zip_path": str(zip_path)
                }, context)
                if list_result.success:
                    files = list_result.data.get("files", [])
                    file_names = [f["filename"] for f in files]
                    print(f"   ZIP Contents: {file_names}")
                else:
                    print(f"   ❌ List ZIP Error: {list_result.error}")
            except Exception as e:
                print(f"   ❌ List ZIP Error: {e}")
        
        # Test extract_zip
        extract_dir = temp_path / "extracted"
        extract_dir.mkdir()
        try:
            extract_result = await tool.execute("extract_zip", {
                "zip_path": str(zip_path),
                "extract_to": str(extract_dir)
            }, context)
            if extract_result.success:
                extracted_files = extract_result.data.get("extracted_files", [])
                print(f"   Extract ZIP: ✅ Success - {len(extracted_files)} files extracted")
                
                # Verify extraction
                if extract_dir.exists():
                    actual_files = list(extract_dir.glob("*"))
                    print(f"   Extracted Files: {[f.name for f in actual_files]}")
            else:
                print(f"   Extract ZIP: ❌ Failed - {extract_result.error}")
        except Exception as e:
            print(f"   ❌ Extract ZIP Error: {e}")
    
    # Test 8: Error Handling
    print("\n8. 🛠️  Error Handling:")
    
    # Test invalid capability
    try:
        invalid_result = await tool.execute("invalid_capability", {}, context)
        if invalid_result.success:
            print("   ❌ Should have failed for invalid capability")
        else:
            print(f"   ✅ Invalid capability correctly handled: {invalid_result.error}")
    except Exception as e:
        print(f"   ✅ Invalid capability correctly handled: {type(e).__name__}")
    
    # Test missing required parameters
    try:
        missing_result = await tool.execute("execute_command", {}, context)
        if missing_result.success:
            print("   ❌ Should have failed for missing parameters")
        else:
            print(f"   ✅ Missing parameters correctly handled: {missing_result.error}")
    except Exception as e:
        print(f"   ✅ Missing parameters correctly handled: {type(e).__name__}")
    
    print("\n" + "=" * 50)
    print("✅ Command Executor Tool Migration Test Complete!")


if __name__ == "__main__":
    asyncio.run(test_command_executor())