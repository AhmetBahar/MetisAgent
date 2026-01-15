#!/usr/bin/env python3
"""
Test Command Executor Tool Capabilities - Comprehensive Testing

Tests all capabilities of the command executor tool including:
- Command execution with different platforms
- Security validation 
- ZIP operations
- Platform info retrieval
- Error handling
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

from core.managers.tool_manager import ToolManager
from core.contracts.base_types import ExecutionContext
from tools.command_executor_tool import create_command_executor_tool_metadata


async def test_command_executor_capabilities():
    """Test all command executor capabilities comprehensively"""
    print("🧪 Testing Command Executor Capabilities")
    print("=" * 50)
    
    # Initialize tool manager and load command executor
    tool_manager = ToolManager()
    metadata, config, tool_class = create_command_executor_tool_metadata()
    success = await tool_manager.load_tool(metadata, config)
    
    if not success:
        print("❌ Failed to load command executor tool")
        return
    
    tool_instance = tool_manager.tools.get("command_executor")
    context = ExecutionContext(user_id="test_user", session_id="test_session")
    
    # Test 1: Platform Information
    print("\n1. 🖥️  Testing Platform Information...")
    try:
        result = await tool_instance.execute("get_platform_info", {}, context)
        if result.success:
            platform_data = result.data
            print(f"   ✅ System: {platform_data.get('system')}")
            print(f"   ✅ Release: {platform_data.get('release')}")
            print(f"   ✅ Machine: {platform_data.get('machine')}")
            print(f"   ✅ Python Version: {platform_data.get('python_version')}")
        else:
            print(f"   ❌ Failed: {result.error}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    # Test 2: Command Validation - Safe Commands
    print("\n2. 🛡️  Testing Command Validation (Safe Commands)...")
    safe_commands = [
        "ls -la",
        "echo 'Hello World'",
        "pwd",
        "whoami",
        "date",
        "python --version"
    ]
    
    for cmd in safe_commands:
        try:
            result = await tool_instance.execute("validate_command", {"command": cmd}, context)
            if result.success:
                is_safe = result.data.get("is_safe", False)
                reason = result.data.get("reason", "Unknown")
                icon = "✅" if is_safe else "❌"
                print(f"   {icon} '{cmd}': {'SAFE' if is_safe else 'UNSAFE'} - {reason}")
            else:
                print(f"   ❌ Validation failed for '{cmd}': {result.error}")
        except Exception as e:
            print(f"   ❌ Exception for '{cmd}': {e}")
    
    # Test 3: Command Validation - Dangerous Commands
    print("\n3. ⚠️  Testing Command Validation (Dangerous Commands)...")
    dangerous_commands = [
        "rm -rf /",
        "rm -rf *",
        "format C:",
        "sudo rm -rf /home",
        "chmod 777 /etc/passwd",
        "shutdown -h now",
        "dd if=/dev/zero of=/dev/sda"
    ]
    
    for cmd in dangerous_commands:
        try:
            result = await tool_instance.execute("validate_command", {"command": cmd}, context)
            if result.success:
                is_safe = result.data.get("is_safe", True)  # Should be False
                reason = result.data.get("reason", "Unknown")
                severity = result.data.get("severity", "unknown")
                icon = "✅" if not is_safe else "❌"  # Should NOT be safe
                print(f"   {icon} '{cmd}': {'BLOCKED' if not is_safe else 'ALLOWED'} - {severity.upper()} - {reason}")
            else:
                print(f"   ❌ Validation failed for '{cmd}': {result.error}")
        except Exception as e:
            print(f"   ❌ Exception for '{cmd}': {e}")
    
    # Test 4: Safe Command Execution
    print("\n4. 🚀 Testing Safe Command Execution...")
    safe_exec_commands = [
        {"command": "echo 'Test Command'", "description": "Simple echo"},
        {"command": "pwd", "description": "Get current directory"},
        {"command": "python3 --version", "description": "Python version check"},
        {"command": "ls /tmp", "description": "List tmp directory"}
    ]
    
    for cmd_info in safe_exec_commands:
        cmd = cmd_info["command"]
        desc = cmd_info["description"]
        try:
            result = await tool_instance.execute("execute_command", {
                "command": cmd,
                "timeout": 10,
                "allow_dangerous": False
            }, context)
            
            if result.success:
                exec_data = result.data
                return_code = exec_data.get("return_code", -1)
                stdout = exec_data.get("stdout", "").strip()
                execution_time = exec_data.get("execution_time_seconds", 0)
                print(f"   ✅ {desc}: RC={return_code}, Time={execution_time:.3f}s")
                if stdout:
                    print(f"      Output: {stdout[:100]}{'...' if len(stdout) > 100 else ''}")
            else:
                print(f"   ❌ {desc} failed: {result.error}")
                
        except Exception as e:
            print(f"   ❌ Exception for '{cmd}': {e}")
    
    # Test 5: ZIP File Operations
    print("\n5. 📦 Testing ZIP Operations...")
    
    # Create a temporary directory with test files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test files
        test_files = ["file1.txt", "file2.txt", "subdir/file3.txt"]
        for file_path in test_files:
            full_path = temp_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(f"Content of {file_path}\nGenerated for testing.")
        
        zip_path = temp_path / "test.zip"
        
        # Test ZIP creation
        try:
            result = await tool_instance.execute("create_zip", {
                "zip_path": str(zip_path),
                "source_path": str(temp_path / "file1.txt"),
                "compression_level": 6
            }, context)
            
            if result.success:
                zip_data = result.data
                zip_size = zip_data.get("zip_size_bytes", 0)
                total_files = zip_data.get("total_files", 0)
                print(f"   ✅ ZIP Creation: {total_files} files, {zip_size} bytes")
            else:
                print(f"   ❌ ZIP Creation failed: {result.error}")
        except Exception as e:
            print(f"   ❌ ZIP Creation exception: {e}")
        
        # Test ZIP contents listing
        if zip_path.exists():
            try:
                result = await tool_instance.execute("list_zip_contents", {
                    "zip_path": str(zip_path)
                }, context)
                
                if result.success:
                    zip_info = result.data
                    file_count = zip_info.get("file_count", 0)
                    total_size = zip_info.get("total_size_bytes", 0)
                    compression_ratio = zip_info.get("compression_ratio_percent", 0)
                    print(f"   ✅ ZIP Contents: {file_count} files, {total_size} bytes, {compression_ratio:.1f}% compression")
                    
                    files = zip_info.get("files", [])
                    for file_info in files[:3]:  # Show first 3 files
                        filename = file_info.get("filename", "unknown")
                        file_size = file_info.get("file_size", 0)
                        print(f"      • {filename}: {file_size} bytes")
                        
                else:
                    print(f"   ❌ ZIP Contents failed: {result.error}")
            except Exception as e:
                print(f"   ❌ ZIP Contents exception: {e}")
            
            # Test ZIP extraction
            extract_dir = temp_path / "extracted"
            try:
                result = await tool_instance.execute("extract_zip", {
                    "zip_path": str(zip_path),
                    "extract_to": str(extract_dir)
                }, context)
                
                if result.success:
                    extract_data = result.data
                    extracted_files = extract_data.get("extracted_files", [])
                    total_extracted = extract_data.get("total_files", 0)
                    print(f"   ✅ ZIP Extraction: {total_extracted} files extracted")
                    
                    # Verify extraction
                    for extracted_file in extracted_files:
                        if Path(extracted_file).exists():
                            print(f"      • Verified: {Path(extracted_file).name}")
                        else:
                            print(f"      • Missing: {Path(extracted_file).name}")
                            
                else:
                    print(f"   ❌ ZIP Extraction failed: {result.error}")
            except Exception as e:
                print(f"   ❌ ZIP Extraction exception: {e}")
    
    # Test 6: Error Handling and Edge Cases
    print("\n6. 🔧 Testing Error Handling...")
    
    error_test_cases = [
        {
            "capability": "execute_command",
            "input": {"command": ""},  # Empty command
            "description": "Empty command"
        },
        {
            "capability": "execute_command", 
            "input": {"command": "nonexistentcommand12345"},  # Non-existent command
            "description": "Non-existent command"
        },
        {
            "capability": "validate_command",
            "input": {"command": ""},  # Empty command validation
            "description": "Empty command validation"
        },
        {
            "capability": "extract_zip",
            "input": {"zip_path": "/nonexistent/path.zip"},  # Non-existent ZIP
            "description": "Non-existent ZIP file"
        },
        {
            "capability": "create_zip",
            "input": {"zip_path": "/tmp/test.zip", "source_path": "/nonexistent"},  # Non-existent source
            "description": "Non-existent source path"
        }
    ]
    
    for test_case in error_test_cases:
        try:
            result = await tool_instance.execute(
                test_case["capability"], 
                test_case["input"], 
                context
            )
            
            if not result.success:
                print(f"   ✅ {test_case['description']}: Error handled properly - {result.error}")
            else:
                print(f"   ⚠️  {test_case['description']}: Expected error but got success")
                
        except Exception as e:
            print(f"   ✅ {test_case['description']}: Exception handled - {type(e).__name__}")
    
    # Test 7: Performance and Timeout
    print("\n7. ⏱️  Testing Performance and Timeout...")
    
    # Test timeout functionality
    try:
        result = await tool_instance.execute("execute_command", {
            "command": "sleep 2",  # 2 second sleep
            "timeout": 1,          # 1 second timeout
            "allow_dangerous": False
        }, context)
        
        if not result.success and "timeout" in result.error.lower():
            print("   ✅ Timeout handling: Command properly timed out")
        else:
            print("   ⚠️  Timeout handling: Expected timeout but command succeeded/failed differently")
            
    except Exception as e:
        print(f"   ⚠️  Timeout test exception: {e}")
    
    # Test working directory
    try:
        result = await tool_instance.execute("execute_command", {
            "command": "pwd",
            "working_directory": "/tmp",
            "timeout": 5
        }, context)
        
        if result.success:
            stdout = result.data.get("stdout", "").strip()
            if "/tmp" in stdout:
                print("   ✅ Working directory: Command executed in specified directory")
            else:
                print(f"   ⚠️  Working directory: Expected /tmp, got {stdout}")
        else:
            print(f"   ❌ Working directory test failed: {result.error}")
            
    except Exception as e:
        print(f"   ❌ Working directory test exception: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Command Executor Capabilities Testing Complete!")


if __name__ == "__main__":
    asyncio.run(test_command_executor_capabilities())