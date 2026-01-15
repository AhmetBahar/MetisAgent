"""
Command Executor MCP Tool - Platform-independent command execution with security features
"""

import subprocess
import platform
import shlex
import logging
import re
import zipfile
import tempfile
from typing import List, Optional
import sys
import os
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.mcp_core import MCPTool, MCPToolResult

logger = logging.getLogger(__name__)

class CommandExecutor(MCPTool):
    """Secure command executor with platform independence"""
    
    # Dangerous commands that should be blocked
    DANGEROUS_COMMANDS = [
        r'\brm\s+-rf\s*/',  # rm -rf /
        r'\brm\s+-rf\s*\*',  # rm -rf *
        r'\bformat\s+c:',  # Windows format command
        r'\bdel\s+/s\s+/q\s+\*',  # Windows recursive delete
        r'\bsudo\s+rm',  # sudo rm commands
        r'\bchmod\s+777',  # Dangerous permissions
        r'\b(shutdown|reboot|halt)\b',  # System control
        r'\b(mkfs|fdisk|parted)\b',  # Disk operations
        r'\b(iptables|ufw)\s+.*flush',  # Firewall flush
        r'\bdd\s+if=.*of=/dev/',  # Direct disk writes
    ]
    
    # Commands that require special handling
    RESTRICTED_COMMANDS = [
        r'\bsudo\b',
        r'\bsu\b',
        r'\brunas\b',
        r'\bpasswd\b',
        r'\buseradd\b',
        r'\buserdel\b',
    ]
    
    def __init__(self):
        super().__init__(
            name="command_executor",
            description="Execute system commands safely across platforms",
            version="2.0.0"
        )
        
        # Register capabilities
        self.add_capability("system_command_execution")
        self.add_capability("cross_platform_support")
        self.add_capability("security_filtering")
        
        # Register actions
        self.register_action(
            "execute",
            self._execute_command,
            required_params=["command"],
            optional_params=["timeout", "working_directory", "allow_dangerous"]
        )
        
        self.register_action(
            "validate",
            self._validate_command,
            required_params=["command"]
        )
        
        self.register_action(
            "get_platform_info",
            self._get_platform_info,
            required_params=[],
            optional_params=[]
        )
        
        self.register_action(
            "extract_zip",
            self._extract_zip,
            required_params=["zip_path"],
            optional_params=["extract_to", "password"]
        )
        
        self.register_action(
            "create_zip",
            self._create_zip,
            required_params=["zip_path", "source_path"],
            optional_params=["compression_level", "password"]
        )
        
        self.register_action(
            "list_zip_contents",
            self._list_zip_contents,
            required_params=["zip_path"],
            optional_params=["password"]
        )
        
        # Initialize graph memory for context-aware command resolution
        self.graph_memory = None
        self._initialize_memory_integration()
    
    def _initialize_memory_integration(self):
        """Initialize graph memory connection for context-aware commands"""
        try:
            from app.mcp_core import registry
            self.graph_memory = registry.get_tool("graph_memory")
            if not self.graph_memory:
                logger.warning("Graph memory tool not available - context-aware commands disabled")
        except Exception as e:
            logger.error(f"Failed to initialize memory integration: {e}")
    
    def _resolve_contextual_command(self, command: str, user_id: str = "system") -> str:
        """Pure LLM-driven command analysis and resolution"""
        try:
            # Get tools needed for LLM analysis
            from app.mcp_core import registry
            llm_tool = registry.get_tool("llm_tool")
            
            if not llm_tool or not self.graph_memory:
                logger.warning("LLM or Graph Memory not available for command resolution")
                return command
            
            # Step 1: LLM analyzes if command needs context resolution
            import json
            analysis_prompt = f"""
            Analyze this command to determine if it needs context resolution:
            "{command}"
            
            Determine:
            1. Is this a natural language command that references previous operations?
            2. What type of context might be needed (files, images, previous commands)?
            3. Should this be resolved to a shell command?
            
            Return JSON only:
            {{
                "needs_resolution": true/false,
                "context_type": "image/file/command/none",
                "reasoning": "brief explanation"
            }}
            """
            
            analysis_result = llm_tool._chat(
                message=analysis_prompt,
                provider="openai",
                user_id=user_id,
                conversation_name="command_analysis"
            )
            
            if not analysis_result.success:
                logger.error(f"Command analysis failed: {analysis_result.error}")
                return command
            
            # Parse analysis
            try:
                # Log analysis data without large content (avoid base64 spam)
                analysis_data_summary = {k: v for k, v in analysis_result.data.items() if k not in ['base64_image', 'image_data']}
                logger.debug(f"Command analysis raw data: {analysis_data_summary}")
                analysis_content = analysis_result.data.get("content") or analysis_result.data.get("response") or "{}"
                # Only log first 200 chars to avoid base64 spam
                content_preview = analysis_content[:200] + "..." if len(analysis_content) > 200 else analysis_content
                logger.debug(f"Command analysis content: {content_preview}")
                analysis_data = json.loads(analysis_content)
                logger.info(f"Command analysis parsed: {analysis_data}")
            except Exception as e:
                logger.error(f"Analysis JSON parse failed: {e}, content: {analysis_content}")
                return command
            
            # If no resolution needed, return original
            if not analysis_data.get("needs_resolution", False):
                return command
                
            # Step 2: Get relevant context based on LLM analysis
            context_type = analysis_data.get("context_type", "none")
            context_data = None
            
            if context_type == "image":
                context_result = self.graph_memory._get_latest_operation(
                    user_id=user_id,
                    tool_name="simple_visual_creator", 
                    action_type="generate"
                )
                if context_result.success:
                    context_data = context_result.data
            elif context_type == "file":
                context_result = self.graph_memory._get_latest_operation(
                    user_id=user_id,
                    tool_name="command_executor",
                    action_type="execute"
                )
                if context_result.success:
                    context_data = context_result.data
            elif context_type == "command":
                # Get any recent operation
                context_result = self.graph_memory._get_latest_operation(user_id=user_id)
                if context_result.success:
                    context_data = context_result.data
            
            # Extract file path from context if available
            actual_file_path = None
            if context_data:
                # Look for file path in observations
                entity = context_data.get("entity", {})
                observations = entity.get("observations", [])
                for obs in observations:
                    if obs.startswith("File Path: "):
                        actual_file_path = obs.split("File Path: ")[1]
                        break
                    elif obs.startswith("Filename: ") and not actual_file_path:
                        # Fallback: try to construct path from filename
                        filename = obs.split("Filename: ")[1]
                        if filename:
                            actual_file_path = f"/home/{user_id}/generated_images/{filename}"
            
            # Step 3: LLM converts to shell command with context
            context_info = ""
            if actual_file_path:
                context_info = f"IMPORTANT: Use this ACTUAL file path: {actual_file_path}"
            
            resolution_prompt = f"""
            Convert this natural language command to a proper shell command:
            "{command}"

            {context_info}
            
            Available Context: {json.dumps(context_data, indent=2) if context_data else "No context available"}
            
            Requirements:
            1. Use the ACTUAL file path provided above if available
            2. Generate valid shell commands for the user's intent
            3. Return ONLY the shell command, no explanations or formatting
            4. Create target directory if it doesn't exist
            
            Shell command:
            """
            
            resolution_result = llm_tool._chat(
                message=resolution_prompt,
                provider="openai",
                user_id=user_id,
                conversation_name="command_resolution"
            )
            
            if resolution_result.success:
                resolved_command = (resolution_result.data.get("content") or resolution_result.data.get("response") or "").strip()
                logger.info(f"Command resolved: '{command}' → '{resolved_command}'")
                return resolved_command
            else:
                logger.error(f"Command resolution failed: {resolution_result.error}")
                return command
                
        except Exception as e:
            logger.error(f"Error in LLM command resolution: {e}")
            return command
    
    def _validate_command(self, command: str, **kwargs) -> MCPToolResult:
        """Validate if a command is safe to execute"""
        try:
            validation_result = self._is_command_safe(command)
            return MCPToolResult(
                success=True,
                data={
                    "is_safe": validation_result["is_safe"],
                    "reason": validation_result.get("reason"),
                    "severity": validation_result.get("severity", "info")
                }
            )
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))
    
    def _execute_command(self, command: str, timeout: int = 30, 
                        working_directory: Optional[str] = None, 
                        allow_dangerous: bool = False, user_id: str = "system", **kwargs) -> MCPToolResult:
        """Execute a system command with security checks and context-aware resolution"""
        try:
            # Step 1: Resolve contextual commands
            original_command = command
            command = self._resolve_contextual_command(command, user_id)
            
            if command != original_command:
                logger.info(f"Command resolution: '{original_command}' → '{command}'")
            
            # Validate command safety
            if not allow_dangerous:
                validation = self._is_command_safe(command)
                if not validation["is_safe"]:
                    return MCPToolResult(
                        success=False,
                        error=f"Command blocked for security: {validation['reason']}",
                        metadata={"severity": validation.get("severity", "high")}
                    )
            
            # Get platform-specific execution method
            system = platform.system()
            
            if system == "Windows":
                cmd = command
                shell = True
            else:
                # Use bash -c for consistent behavior on Unix-like systems
                cmd = ["bash", "-c", command]
                shell = False
            
            # Execute command
            logger.info(f"Executing command: {command}")
            
            result = subprocess.run(
                cmd,
                shell=shell,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=working_directory
            )
            
            # Prepare response
            response_data = {
                "command": command,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "platform": system,
                "working_directory": working_directory,
                "execution_time": timeout  # This would be actual time in real implementation
            }
            
            if result.returncode == 0:
                return MCPToolResult(
                    success=True,
                    data=response_data,
                    metadata={"status": "completed_successfully"}
                )
            else:
                return MCPToolResult(
                    success=False,
                    error=f"Command failed with return code {result.returncode}",
                    data=response_data,
                    metadata={"status": "completed_with_error"}
                )
                
        except subprocess.TimeoutExpired:
            return MCPToolResult(
                success=False,
                error=f"Command timed out after {timeout} seconds"
            )
        except FileNotFoundError as e:
            return MCPToolResult(
                success=False,
                error=f"Command not found: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error executing command '{command}': {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _get_platform_info(self, **kwargs) -> MCPToolResult:
        """Get platform information"""
        try:
            info = {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version()
            }
            return MCPToolResult(success=True, data=info)
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))
    
    def _is_command_safe(self, command: str) -> dict:
        """Check if a command is safe to execute"""
        command_lower = command.lower().strip()
        
        # Check for dangerous commands
        for pattern in self.DANGEROUS_COMMANDS:
            if re.search(pattern, command_lower, re.IGNORECASE):
                return {
                    "is_safe": False,
                    "reason": "Command contains dangerous operations",
                    "severity": "critical",
                    "pattern_matched": pattern
                }
        
        # Check for restricted commands that need special handling
        for pattern in self.RESTRICTED_COMMANDS:
            if re.search(pattern, command_lower, re.IGNORECASE):
                return {
                    "is_safe": False,
                    "reason": "Command requires elevated privileges",
                    "severity": "high",
                    "pattern_matched": pattern
                }
        
        # Additional safety checks
        if len(command) > 1000:
            return {
                "is_safe": False,
                "reason": "Command too long (potential buffer overflow)",
                "severity": "medium"
            }
        
        # Check for command injection patterns
        injection_patterns = [
            r';.*rm\s',
            r'&&.*rm\s',
            r'\|.*rm\s',
            r'`.*`',
            r'\$\(.*\)',
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return {
                    "is_safe": False,
                    "reason": "Potential command injection detected",
                    "severity": "high",
                    "pattern_matched": pattern
                }
        
        return {"is_safe": True, "reason": "Command passed security checks"}
    
    def _extract_zip(self, zip_path: str, extract_to: Optional[str] = None, 
                     password: Optional[str] = None, **kwargs) -> MCPToolResult:
        """Extract ZIP file to specified directory"""
        try:
            zip_path = Path(zip_path)
            
            # Validate ZIP file exists and is readable
            if not zip_path.exists():
                return MCPToolResult(
                    success=False,
                    error=f"ZIP file not found: {zip_path}"
                )
            
            if not zip_path.is_file():
                return MCPToolResult(
                    success=False,
                    error=f"Path is not a file: {zip_path}"
                )
            
            # Set extraction directory
            if extract_to:
                extract_dir = Path(extract_to)
            else:
                extract_dir = zip_path.parent / zip_path.stem
            
            # Create extraction directory if it doesn't exist
            extract_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract ZIP file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Check if password protected
                if zip_ref.testzip() is not None and password is None:
                    return MCPToolResult(
                        success=False,
                        error="ZIP file appears corrupted or password protected"
                    )
                
                # Set password if provided
                pwd = password.encode('utf-8') if password else None
                
                # List contents for security check
                file_list = zip_ref.namelist()
                
                # Security check for directory traversal
                for filename in file_list:
                    if '..' in filename or filename.startswith('/'):
                        return MCPToolResult(
                            success=False,
                            error=f"Security violation: unsafe path in ZIP - {filename}"
                        )
                
                # Extract all files
                extracted_files = []
                for filename in file_list:
                    try:
                        zip_ref.extract(filename, extract_dir, pwd=pwd)
                        extracted_files.append(str(extract_dir / filename))
                    except Exception as e:
                        logger.warning(f"Failed to extract {filename}: {str(e)}")
                
                return MCPToolResult(
                    success=True,
                    data={
                        "zip_path": str(zip_path),
                        "extract_to": str(extract_dir),
                        "extracted_files": extracted_files,
                        "total_files": len(extracted_files),
                        "file_list": file_list
                    }
                )
                
        except zipfile.BadZipFile:
            return MCPToolResult(
                success=False,
                error="Invalid or corrupted ZIP file"
            )
        except PermissionError:
            return MCPToolResult(
                success=False,
                error="Permission denied - check file/directory permissions"
            )
        except Exception as e:
            logger.error(f"Error extracting ZIP file {zip_path}: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _create_zip(self, zip_path: str, source_path: str, 
                   compression_level: int = 6, password: Optional[str] = None, 
                   **kwargs) -> MCPToolResult:
        """Create ZIP file from source directory or file"""
        try:
            zip_path = Path(zip_path)
            source_path = Path(source_path)
            
            # Validate source exists
            if not source_path.exists():
                return MCPToolResult(
                    success=False,
                    error=f"Source path not found: {source_path}"
                )
            
            # Create parent directory for ZIP file if needed
            zip_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Determine compression method
            compression = zipfile.ZIP_DEFLATED
            if compression_level < 0 or compression_level > 9:
                compression_level = 6
            
            added_files = []
            
            with zipfile.ZipFile(zip_path, 'w', compression=compression, 
                               compresslevel=compression_level) as zip_ref:
                
                if source_path.is_file():
                    # Add single file
                    arcname = source_path.name
                    if password:
                        # Note: Python's zipfile doesn't support password protection for writing
                        logger.warning("Password protection not supported for ZIP creation")
                    zip_ref.write(source_path, arcname)
                    added_files.append(arcname)
                    
                elif source_path.is_dir():
                    # Add directory recursively
                    for file_path in source_path.rglob('*'):
                        if file_path.is_file():
                            # Create relative path for archive
                            arcname = file_path.relative_to(source_path)
                            zip_ref.write(file_path, arcname)
                            added_files.append(str(arcname))
                
                return MCPToolResult(
                    success=True,
                    data={
                        "zip_path": str(zip_path),
                        "source_path": str(source_path),
                        "added_files": added_files,
                        "total_files": len(added_files),
                        "compression_level": compression_level,
                        "zip_size_bytes": zip_path.stat().st_size
                    }
                )
                
        except PermissionError:
            return MCPToolResult(
                success=False,
                error="Permission denied - check file/directory permissions"
            )
        except Exception as e:
            logger.error(f"Error creating ZIP file {zip_path}: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _list_zip_contents(self, zip_path: str, password: Optional[str] = None, 
                          **kwargs) -> MCPToolResult:
        """List contents of ZIP file"""
        try:
            zip_path = Path(zip_path)
            
            # Validate ZIP file exists
            if not zip_path.exists():
                return MCPToolResult(
                    success=False,
                    error=f"ZIP file not found: {zip_path}"
                )
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Set password if provided
                pwd = password.encode('utf-8') if password else None
                
                # Get file information
                file_info = []
                total_size = 0
                compressed_size = 0
                
                for info in zip_ref.infolist():
                    file_data = {
                        "filename": info.filename,
                        "file_size": info.file_size,
                        "compressed_size": info.compress_size,
                        "date_time": info.date_time,
                        "is_dir": info.is_dir(),
                        "compression_type": info.compress_type
                    }
                    file_info.append(file_data)
                    total_size += info.file_size
                    compressed_size += info.compress_size
                
                compression_ratio = (1 - compressed_size / total_size) * 100 if total_size > 0 else 0
                
                return MCPToolResult(
                    success=True,
                    data={
                        "zip_path": str(zip_path),
                        "file_count": len(file_info),
                        "total_size_bytes": total_size,
                        "compressed_size_bytes": compressed_size,
                        "compression_ratio_percent": round(compression_ratio, 2),
                        "files": file_info
                    }
                )
                
        except zipfile.BadZipFile:
            return MCPToolResult(
                success=False,
                error="Invalid or corrupted ZIP file"
            )
        except Exception as e:
            logger.error(f"Error listing ZIP contents {zip_path}: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def health_check(self) -> MCPToolResult:
        """Check if command executor is working properly"""
        try:
            # Test basic command execution
            test_command = "echo 'health_check'" if platform.system() != "Windows" else "echo health_check"
            result = self._execute_command(test_command, timeout=5, allow_dangerous=False)
            
            if result.success and "health_check" in result.data.get("stdout", ""):
                return MCPToolResult(
                    success=True,
                    data={
                        "status": "healthy",
                        "platform": platform.system(),
                        "test_passed": True
                    }
                )
            else:
                return MCPToolResult(
                    success=False,
                    error="Health check command failed"
                )
                
        except Exception as e:
            return MCPToolResult(
                success=False,
                error=f"Health check failed: {str(e)}"
            )

def register_tool(registry):
    """Register the command executor tool with the registry"""
    tool = CommandExecutor()
    return registry.register_tool(tool)