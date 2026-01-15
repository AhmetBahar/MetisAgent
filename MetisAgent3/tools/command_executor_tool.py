"""
Command Executor Tool - MCP-Compatible Plugin for MetisAgent3

CLAUDE.md COMPLIANT:
- Secure command execution with isolation
- Platform-independent operation (Windows/Linux/macOS)
- MCP-compatible with JSON I/O
- Security filtering and validation
- Context-aware command resolution
- Plugin architecture implementation
"""

import subprocess
import platform
import shlex
import logging
import re
import zipfile
import tempfile
import json
from typing import Dict, Any, List, Optional, Tuple
import socket
import time
from pathlib import Path
import os
from datetime import datetime

from core.contracts.tool_contracts import BaseTool, ToolMetadata, ToolConfiguration, AgentResult, ExecutionContext, CapabilityType, ToolCapability, ToolType, HealthStatus

logger = logging.getLogger(__name__)


class CommandExecutorTool(BaseTool):
    """Secure command executor with platform independence and MCP compatibility"""
    
    # Dangerous commands that should be blocked
    DANGEROUS_COMMANDS = [
        r'\brm\s+-rf\s*/',  # rm -rf /
        r'\brm\s+-rf\s*\*',  # rm -rf *  
        r'\brm\s+-rf\s+\/',  # rm -rf / (with explicit /)
        r'\bformat\s+[cC]:',  # Windows format command
        r'\bdel\s+/[sS]\s+/[qQ]\s+\*',  # Windows recursive delete
        r'\bsudo\s+rm.*-rf',  # sudo rm commands with -rf
        r'\bchmod\s+777',  # Dangerous permissions
        r'\b(shutdown|reboot|halt)\b',  # System control
        r'\b(mkfs|fdisk|parted)\b',  # Disk operations
        r'\b(iptables|ufw)\s+.*flush',  # Firewall flush
        r'\bdd\s+if=.*of=/dev/',  # Direct disk writes
        r'\brm\s+-[rf]+.*\*',  # rm with wildcards
        r'\b(del|erase)\s+[cC]:\\.*\*',  # Windows delete with wildcards on C:
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
    
    def __init__(self, metadata: Optional[ToolMetadata] = None, config: Optional[ToolConfiguration] = None, conversation_service=None):
        # Create default metadata and config for this tool if not provided
        if metadata is None or config is None:
            default_metadata, default_config, _ = create_command_executor_tool_metadata()
            metadata = metadata or default_metadata
            config = config or default_config
        
        super().__init__(metadata, config)
        self.conversation_service = conversation_service
        self.platform_info = self._get_platform_info()
        logger.info(f"Command Executor initialized on {self.platform_info['system']}")
    
    async def execute(self, capability: str, input_data: Dict[str, Any], context: ExecutionContext) -> AgentResult:
        """Execute command executor capabilities"""
        try:
            if capability == "execute_command":
                return await self._execute_command(input_data, context)
            elif capability == "measure_ping":
                return await self._measure_ping(input_data)
            elif capability == "resolve_dns":
                return await self._resolve_dns(input_data)
            elif capability == "http_check":
                return await self._http_check(input_data)
            elif capability == "port_check":
                return await self._port_check(input_data)
            elif capability == "validate_command":
                return await self._validate_command(input_data)
            elif capability == "get_platform_info":
                return await self._get_platform_info_result()
            elif capability == "extract_zip":
                return await self._extract_zip(input_data)
            elif capability == "create_zip":
                return await self._create_zip(input_data)
            elif capability == "list_zip_contents":
                return await self._list_zip_contents(input_data)
            else:
                return AgentResult(
                    success=False,
                    error=f"Unknown capability: {capability}"
                )
                
        except Exception as e:
            logger.error(f"Command executor error: {e}")
            return AgentResult(success=False, error=str(e))

    async def _measure_ping(self, input_data: Dict[str, Any]) -> AgentResult:
        """Measure average ping in ms to a target using N attempts.
        Falls back to TCP connect latency (port 443) if ICMP ping is unavailable.
        """
        try:
            target = input_data.get("target") or input_data.get("host") or "google.com"
            count = int(input_data.get("count", 10))
            timeout = int(input_data.get("timeout", 20))

            sysname = platform.system()
            if sysname == "Windows":
                cmd = ["ping", "-n", str(count), target]
            else:
                # -c count, -n numeric, -q quiet summary
                cmd = ["ping", "-c", str(count), "-n", "-q", target]

            logger.info(f"Measuring ping: target={target} count={count} system={sysname}")
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
            except FileNotFoundError:
                result = None  # ICMP ping not available

            stdout = result.stdout if result else ""
            stderr = result.stderr if result else ""

            avg_ms = None
            if result and sysname == "Windows":
                # Example: Average = 23ms
                m = re.search(r"Average\s*=\s*(\d+)ms", stdout)
                if m:
                    avg_ms = float(m.group(1))
            elif result:
                # Example: rtt min/avg/max/mdev = 14.345/18.123/25.678/2.345 ms
                m = re.search(r"=\s*([0-9.]+)/([0-9.]+)/([0-9.]+)/([0-9.]+)\s*ms", stdout)
                if m:
                    avg_ms = float(m.group(2))

            data = {
                "target": target,
                "count": count,
                "return_code": result.returncode if result else None,
                "stdout": stdout,
                "stderr": stderr,
                "average_ms": avg_ms
            }

            if avg_ms is not None and result and result.returncode == 0:
                data["method"] = "icmp"
                return AgentResult(success=True, data=data)

            # Fallback: TCP connect to 443 measured N times
            logger.info("ICMP ping unavailable or failed, falling back to TCP connect timing (443)")
            try:
                # Resolve target once
                infos = socket.getaddrinfo(target, 443, proto=socket.IPPROTO_TCP)
                addr = None
                for info in infos:
                    sockaddr = info[4]
                    if sockaddr and sockaddr[0]:
                        addr = (sockaddr[0], 443)
                        break
                if not addr:
                    return AgentResult(success=False, error="DNS resolution failed", data=data)

                times: List[float] = []
                for _ in range(max(1, count)):
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(timeout)
                    t0 = time.time()
                    err = s.connect_ex(addr)
                    t1 = time.time()
                    s.close()
                    if err == 0:
                        times.append((t1 - t0) * 1000.0)
                tcp_avg = sum(times) / len(times) if times else None
                data.update({
                    "average_ms": tcp_avg,
                    "method": "tcp_connect",
                    "samples": len(times),
                    "resolved_ip": addr[0]
                })
                if tcp_avg is not None:
                    return AgentResult(success=True, data=data, metadata={"fallback": True})
                return AgentResult(success=False, error="Unable to measure TCP connect latency", data=data)
            except Exception as e:
                data["fallback_error"] = str(e)
                return AgentResult(success=False, error="Unable to measure ping (icmp/tcp)", data=data)
        except Exception as e:
            logger.error(f"measure_ping error: {e}")
            return AgentResult(success=False, error=str(e))

    def _cmd_exists(self, cmd: str) -> bool:
        from shutil import which
        return which(cmd) is not None

    async def _resolve_dns(self, input_data: Dict[str, Any]) -> AgentResult:
        """Resolve DNS records for a target using dig/nslookup or Python fallback."""
        try:
            target = input_data.get("target") or input_data.get("host") or "google.com"
            rtype = (input_data.get("type") or input_data.get("rtype") or "A").upper()
            timeout = int(input_data.get("timeout", 10))
            records: List[str] = []
            server = None
            query_ms = None
            stdout = ""
            stderr = ""

            if self._cmd_exists("dig"):
                # Get records
                cmd = ["bash", "-c", f"dig {shlex.quote(target)} {shlex.quote(rtype)} +short"]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
                stdout = res.stdout
                stderr = res.stderr
                records = [line.strip() for line in res.stdout.splitlines() if line.strip()]
                # Stats
                cmd2 = ["bash", "-c", f"dig {shlex.quote(target)} {shlex.quote(rtype)} +stats +time={timeout}"]
                res2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=timeout)
                for line in (res2.stdout or "").splitlines():
                    if "SERVER:" in line:
                        # SERVER: 192.168.1.1#53(192.168.1.1)
                        server = line.split("SERVER:", 1)[1].strip()
                    if "Query time:" in line and "msec" in line:
                        try:
                            query_ms = float(line.split("Query time:", 1)[1].split("msec")[0].strip())
                        except Exception:
                            pass
            elif self._cmd_exists("nslookup"):
                cmd = ["nslookup", "-type=" + rtype, target]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
                stdout = res.stdout
                stderr = res.stderr
                # Parse simplistic: pick lines with 'Address:' after 'Name:' block
                in_answer = False
                for line in stdout.splitlines():
                    if line.lower().startswith("server:"):
                        server = line.split(":", 1)[1].strip()
                    if line.lower().startswith("address:") and not in_answer:
                        # First address may be server addr; continue
                        continue
                    if line.lower().startswith("name:"):
                        in_answer = True
                        continue
                    if in_answer and line.lower().startswith("address:"):
                        records.append(line.split(":", 1)[1].strip())
                # No easy query time from nslookup
            else:
                # Python fallback
                t0 = time.time()
                infos = socket.getaddrinfo(target, None, proto=socket.IPPROTO_TCP)
                t1 = time.time()
                addrs = set()
                for info in infos:
                    sockaddr = info[4]
                    if sockaddr and sockaddr[0]:
                        addrs.add(sockaddr[0])
                records = list(addrs)
                query_ms = (t1 - t0) * 1000.0

            data = {
                "target": target,
                "type": rtype,
                "records": records,
                "server": server,
                "query_ms": query_ms,
                "stdout": stdout,
                "stderr": stderr
            }
            if records:
                return AgentResult(success=True, data=data)
            else:
                return AgentResult(success=False, error="No DNS records found", data=data)
        except Exception as e:
            logger.error(f"resolve_dns error: {e}")
            return AgentResult(success=False, error=str(e))

    async def _http_check(self, input_data: Dict[str, Any]) -> AgentResult:
        """Perform an HTTP(S) request and report status and timings."""
        try:
            url = input_data.get("url")
            if not url:
                return AgentResult(success=False, error="url is required")
            method = (input_data.get("method") or "GET").upper()
            headers = input_data.get("headers") or {}
            body = input_data.get("body")
            timeout = float(input_data.get("timeout", 15))
            insecure = bool(input_data.get("insecure", False))

            stdout = ""
            stderr = ""
            status = None
            remote_ip = None
            t_connect = None
            t_total = None
            t_starttransfer = None

            if self._cmd_exists("curl"):
                # Build curl command
                curl = ["curl", "-sS", "-o", "/dev/null", "-X", method]
                if insecure:
                    curl.append("-k")
                for k, v in headers.items():
                    curl.extend(["-H", f"{k}: {v}"])
                if body is not None:
                    curl.extend(["--data", body if isinstance(body, str) else json.dumps(body)])
                # Output: code connect starttransfer total remote_ip
                curl.extend(["-w", "%{http_code} %{time_connect} %{time_starttransfer} %{time_total} %{remote_ip}"])
                curl.append(url)
                res = subprocess.run(curl, capture_output=True, text=True, timeout=timeout)
                stdout = (res.stdout or "").strip()
                stderr = res.stderr or ""
                parts = stdout.split()
                if len(parts) >= 5:
                    try:
                        status = int(parts[0])
                    except Exception:
                        status = None
                    try:
                        t_connect = float(parts[1]) * 1000.0
                        t_starttransfer = float(parts[2]) * 1000.0
                        t_total = float(parts[3]) * 1000.0
                    except Exception:
                        pass
                    remote_ip = parts[4]
            else:
                # Python fallback via requests
                try:
                    import requests
                    t0 = time.time()
                    resp = requests.request(method, url, headers=headers, data=body, timeout=timeout, verify=not insecure)
                    t1 = time.time()
                    status = resp.status_code
                    t_total = (t1 - t0) * 1000.0
                    stdout = resp.text[:2000]
                except Exception as e:
                    stderr = str(e)

            data = {
                "url": url,
                "status": status,
                "time_connect_ms": t_connect,
                "time_starttransfer_ms": t_starttransfer,
                "time_total_ms": t_total,
                "remote_ip": remote_ip,
                "stdout": stdout,
                "stderr": stderr
            }
            if status is not None and (200 <= status < 600):
                return AgentResult(success=True, data=data)
            return AgentResult(success=False, error="HTTP request failed", data=data)
        except Exception as e:
            logger.error(f"http_check error: {e}")
            return AgentResult(success=False, error=str(e))

    async def _port_check(self, input_data: Dict[str, Any]) -> AgentResult:
        """Check TCP port reachability and measure connect latency."""
        try:
            host = input_data.get("host") or input_data.get("target")
            port = int(input_data.get("port", 0))
            timeout = float(input_data.get("timeout", 5))
            if not host or not port:
                return AgentResult(success=False, error="host and port are required")

            t0 = time.time()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            try:
                err = s.connect_ex((host, port))
            finally:
                t1 = time.time()
                s.close()
            connect_ms = (t1 - t0) * 1000.0

            data = {"host": host, "port": port, "reachable": err == 0, "connect_ms": connect_ms}
            if err == 0:
                return AgentResult(success=True, data=data)
            else:
                return AgentResult(success=False, error=f"connect_ex error {err}", data=data)
        except Exception as e:
            logger.error(f"port_check error: {e}")
            return AgentResult(success=False, error=str(e))
    
    async def _execute_command(self, input_data: Dict[str, Any], context: ExecutionContext) -> AgentResult:
        """Execute a system command with security checks"""
        try:
            # Extract parameters
            command = input_data.get("command", "")
            timeout = input_data.get("timeout", 30)
            working_directory = input_data.get("working_directory")
            allow_dangerous = input_data.get("allow_dangerous", False)
            
            if not command:
                return AgentResult(success=False, error="Command parameter is required")
            
            # Validate command safety
            if not allow_dangerous:
                validation = self._is_command_safe(command)
                if not validation["is_safe"]:
                    return AgentResult(
                        success=False,
                        error=f"Command blocked for security: {validation['reason']}",
                        metadata={"security_violation": True, "severity": validation.get("severity", "high")}
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
            logger.info(f"Executing command on {system}: {command}")
            start_time = datetime.now()
            
            result = subprocess.run(
                cmd,
                shell=shell,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=working_directory
            )
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            # Prepare response
            response_data = {
                "command": command,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "platform": system,
                "working_directory": working_directory or os.getcwd(),
                "execution_time_seconds": execution_time,
                "success": result.returncode == 0
            }
            
            if result.returncode == 0:
                return AgentResult(
                    success=True,
                    data=response_data,
                    metadata={"status": "completed_successfully"}
                )
            else:
                return AgentResult(
                    success=False,
                    error=f"Command failed with return code {result.returncode}",
                    data=response_data,
                    metadata={"status": "completed_with_error"}
                )
                
        except subprocess.TimeoutExpired:
            return AgentResult(
                success=False,
                error=f"Command timed out after {timeout} seconds",
                metadata={"timeout": True}
            )
        except FileNotFoundError as e:
            return AgentResult(
                success=False,
                error=f"Command not found: {str(e)}",
                metadata={"command_not_found": True}
            )
        except Exception as e:
            logger.error(f"Error executing command '{command}': {str(e)}")
            return AgentResult(success=False, error=str(e))
    
    async def _validate_command(self, input_data: Dict[str, Any]) -> AgentResult:
        """Validate if a command is safe to execute"""
        try:
            command = input_data.get("command", "")
            if not command:
                return AgentResult(success=False, error="Command parameter is required")
            
            validation_result = self._is_command_safe(command)
            return AgentResult(
                success=True,
                data={
                    "command": command,
                    "is_safe": validation_result["is_safe"],
                    "reason": validation_result.get("reason", ""),
                    "severity": validation_result.get("severity", "info"),
                    "matched_pattern": validation_result.get("pattern_matched"),
                    "validation_timestamp": datetime.now().isoformat()
                }
            )
        except Exception as e:
            return AgentResult(success=False, error=str(e))
    
    async def _get_platform_info_result(self) -> AgentResult:
        """Get platform information as AgentResult"""
        try:
            return AgentResult(success=True, data=self.platform_info)
        except Exception as e:
            return AgentResult(success=False, error=str(e))
    
    def _get_platform_info(self) -> Dict[str, str]:
        """Get platform information"""
        try:
            return {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "platform_info": platform.platform()
            }
        except Exception as e:
            logger.error(f"Error getting platform info: {e}")
            return {"system": "unknown", "error": str(e)}
    
    def _is_command_safe(self, command: str) -> Dict[str, Any]:
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
            r';.*rm\\s',
            r'&&.*rm\\s',
            r'\\|.*rm\\s',
            r'`.*`',
            r'\\$\\(.*\\)',
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
    
    async def _extract_zip(self, input_data: Dict[str, Any]) -> AgentResult:
        """Extract ZIP file to specified directory"""
        try:
            zip_path = Path(input_data.get("zip_path", ""))
            extract_to = input_data.get("extract_to")
            password = input_data.get("password")
            
            if not zip_path:
                return AgentResult(success=False, error="zip_path parameter is required")
            
            # Validate ZIP file exists and is readable
            if not zip_path.exists():
                return AgentResult(success=False, error=f"ZIP file not found: {zip_path}")
            
            if not zip_path.is_file():
                return AgentResult(success=False, error=f"Path is not a file: {zip_path}")
            
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
                    return AgentResult(
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
                        return AgentResult(
                            success=False,
                            error=f"Security violation: unsafe path in ZIP - {filename}",
                            metadata={"security_violation": True}
                        )
                
                # Extract all files
                extracted_files = []
                for filename in file_list:
                    try:
                        zip_ref.extract(filename, extract_dir, pwd=pwd)
                        extracted_files.append(str(extract_dir / filename))
                    except Exception as e:
                        logger.warning(f"Failed to extract {filename}: {str(e)}")
                
                return AgentResult(
                    success=True,
                    data={
                        "zip_path": str(zip_path),
                        "extract_to": str(extract_dir),
                        "extracted_files": extracted_files,
                        "total_files": len(extracted_files),
                        "file_list": file_list,
                        "extraction_timestamp": datetime.now().isoformat()
                    }
                )
                
        except zipfile.BadZipFile:
            return AgentResult(success=False, error="Invalid or corrupted ZIP file")
        except PermissionError:
            return AgentResult(
                success=False,
                error="Permission denied - check file/directory permissions"
            )
        except Exception as e:
            logger.error(f"Error extracting ZIP file: {str(e)}")
            return AgentResult(success=False, error=str(e))
    
    async def _create_zip(self, input_data: Dict[str, Any]) -> AgentResult:
        """Create ZIP file from source directory or file"""
        try:
            zip_path = Path(input_data.get("zip_path", ""))
            source_path = Path(input_data.get("source_path", ""))
            compression_level = input_data.get("compression_level", 6)
            password = input_data.get("password")
            
            if not zip_path or not source_path:
                return AgentResult(
                    success=False, 
                    error="zip_path and source_path parameters are required"
                )
            
            # Validate source exists
            if not source_path.exists():
                return AgentResult(success=False, error=f"Source path not found: {source_path}")
            
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
                
                return AgentResult(
                    success=True,
                    data={
                        "zip_path": str(zip_path),
                        "source_path": str(source_path),
                        "added_files": added_files,
                        "total_files": len(added_files),
                        "compression_level": compression_level,
                        "zip_size_bytes": zip_path.stat().st_size,
                        "creation_timestamp": datetime.now().isoformat()
                    }
                )
                
        except PermissionError:
            return AgentResult(
                success=False,
                error="Permission denied - check file/directory permissions"
            )
        except Exception as e:
            logger.error(f"Error creating ZIP file: {str(e)}")
            return AgentResult(success=False, error=str(e))
    
    async def _list_zip_contents(self, input_data: Dict[str, Any]) -> AgentResult:
        """List contents of ZIP file"""
        try:
            zip_path = Path(input_data.get("zip_path", ""))
            password = input_data.get("password")
            
            if not zip_path:
                return AgentResult(success=False, error="zip_path parameter is required")
            
            # Validate ZIP file exists
            if not zip_path.exists():
                return AgentResult(success=False, error=f"ZIP file not found: {zip_path}")
            
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
                        "date_time": list(info.date_time),  # Convert tuple to list for JSON
                        "is_dir": info.is_dir(),
                        "compression_type": info.compress_type
                    }
                    file_info.append(file_data)
                    total_size += info.file_size
                    compressed_size += info.compress_size
                
                compression_ratio = (1 - compressed_size / total_size) * 100 if total_size > 0 else 0
                
                return AgentResult(
                    success=True,
                    data={
                        "zip_path": str(zip_path),
                        "file_count": len(file_info),
                        "total_size_bytes": total_size,
                        "compressed_size_bytes": compressed_size,
                        "compression_ratio_percent": round(compression_ratio, 2),
                        "files": file_info,
                        "analysis_timestamp": datetime.now().isoformat()
                    }
                )
                
        except zipfile.BadZipFile:
            return AgentResult(success=False, error="Invalid or corrupted ZIP file")
        except Exception as e:
            logger.error(f"Error listing ZIP contents: {str(e)}")
            return AgentResult(success=False, error=str(e))
    
    async def health_check(self) -> HealthStatus:
        """Check if command executor is working properly"""
        try:
            # Test basic command execution
            test_command = "echo 'health_check'" if platform.system() != "Windows" else "echo health_check"
            
            result = await self._execute_command(
                {"command": test_command, "timeout": 5, "allow_dangerous": False},
                ExecutionContext(user_id="system", session_id="health_check")
            )
            
            if result.success and "health_check" in result.data.get("stdout", ""):
                return HealthStatus(
                    healthy=True,
                    component=self.metadata.name,
                    message=f"Command executor healthy on {self.platform_info['system']}",
                    details={
                        "platform": self.platform_info,
                        "test_command": test_command,
                        "test_passed": True
                    }
                )
            else:
                return HealthStatus(
                    healthy=False,
                    component=self.metadata.name,
                    message="Health check command failed",
                    details={"error": result.error if not result.success else "Unknown error"}
                )
                
        except Exception as e:
            return HealthStatus(
                healthy=False,
                component=self.metadata.name,
                message=f"Health check failed: {str(e)}"
            )
    
    async def validate_input(self, capability: str, input_data: Dict[str, Any]) -> List[str]:
        """Validate input for command executor capabilities"""
        errors = []
        
        try:
            if capability == "execute_command":
                if not input_data.get("command"):
                    errors.append("command parameter is required")
                
                timeout = input_data.get("timeout", 30)
                if not isinstance(timeout, (int, float)) or timeout <= 0:
                    errors.append("timeout must be a positive number")
                
                working_dir = input_data.get("working_directory")
                if working_dir and not os.path.exists(working_dir):
                    errors.append(f"working_directory does not exist: {working_dir}")
                    
            elif capability == "validate_command":
                if not input_data.get("command"):
                    errors.append("command parameter is required")
                    
            elif capability in ["extract_zip", "list_zip_contents"]:
                if not input_data.get("zip_path"):
                    errors.append("zip_path parameter is required")
                    
            elif capability == "create_zip":
                if not input_data.get("zip_path"):
                    errors.append("zip_path parameter is required")
                if not input_data.get("source_path"):
                    errors.append("source_path parameter is required")
                    
                compression = input_data.get("compression_level", 6)
                if not isinstance(compression, int) or compression < 0 or compression > 9:
                    errors.append("compression_level must be an integer between 0 and 9")
                    
        except Exception as e:
            errors.append(f"Input validation error: {e}")
        
        return errors


# Factory function for creating CommandExecutorTool metadata
def create_command_executor_tool_metadata() -> Tuple[ToolMetadata, ToolConfiguration, type]:
    """Create command executor tool with metadata and configuration"""
    
    metadata = ToolMetadata(
        name="command_executor",
        description="Secure cross-platform command execution with safety checks",
        version="3.0.0",
        tool_type=ToolType.PLUGIN,
        capabilities=[
            ToolCapability(
                name="execute_command",
                description="Execute system commands safely with security validation",
                capability_type=CapabilityType.EXECUTE,
                input_schema={
                    "command": {
                        "type": "string",
                        "description": "The command to execute",
                        "required": True
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Command timeout in seconds",
                        "default": 30,
                        "minimum": 1,
                        "maximum": 300
                    },
                    "working_directory": {
                        "type": "string",
                        "description": "Working directory for command execution",
                        "required": False
                    },
                    "allow_dangerous": {
                        "type": "boolean",
                        "description": "Allow potentially dangerous commands (use with caution)",
                        "default": False
                    }
                },
                output_schema={
                    "command": {"type": "string"},
                    "return_code": {"type": "integer"},
                    "stdout": {"type": "string"},
                    "stderr": {"type": "string"},
                    "platform": {"type": "string"},
                    "execution_time_seconds": {"type": "number"},
                    "success": {"type": "boolean"}
                },
                examples=[
                    {
                        "input": {"command": "ls -la", "timeout": 10},
                        "output": {"return_code": 0, "stdout": "file listings...", "success": True}
                    },
                    {
                        "input": {"command": "echo 'Hello World'"},
                        "output": {"return_code": 0, "stdout": "Hello World\\n", "success": True}
                    }
                ]
            ),
            ToolCapability(
                name="validate_command",
                description="Validate command safety without executing",
                capability_type=CapabilityType.ANALYZE,
                input_schema={
                    "command": {
                        "type": "string",
                        "description": "The command to validate",
                        "required": True
                    }
                },
                output_schema={
                    "is_safe": {"type": "boolean"},
                    "reason": {"type": "string"},
                    "severity": {"type": "string"}
                },
                examples=[
                    {
                        "input": {"command": "ls -la"},
                        "output": {"is_safe": True, "reason": "Command passed security checks", "severity": "info"}
                    }
                ]
            ),
            ToolCapability(
                name="get_platform_info",
                description="Get information about the current platform",
                capability_type=CapabilityType.READ,
                input_schema={},
                output_schema={
                    "system": {"type": "string"},
                    "release": {"type": "string"},
                    "version": {"type": "string"},
                    "machine": {"type": "string"}
                },
                examples=[]
            ),
            ToolCapability(
                name="extract_zip",
                description="Extract ZIP file contents to a directory",
                capability_type=CapabilityType.EXECUTE,
                input_schema={
                    "zip_path": {
                        "type": "string",
                        "description": "Path to the ZIP file",
                        "required": True
                    },
                    "extract_to": {
                        "type": "string",
                        "description": "Directory to extract to (optional)"
                    },
                    "password": {
                        "type": "string",
                        "description": "Password for encrypted ZIP (optional)"
                    }
                },
                output_schema={
                    "extracted_files": {"type": "array"},
                    "total_files": {"type": "integer"}
                },
                examples=[]
            ),
            ToolCapability(
                name="create_zip",
                description="Create ZIP file from source directory or file",
                capability_type=CapabilityType.WRITE,
                input_schema={
                    "zip_path": {
                        "type": "string",
                        "description": "Path for the new ZIP file",
                        "required": True
                    },
                    "source_path": {
                        "type": "string",
                        "description": "Source file or directory to compress",
                        "required": True
                    },
                    "compression_level": {
                        "type": "integer",
                        "description": "Compression level (0-9)",
                        "default": 6,
                        "minimum": 0,
                        "maximum": 9
                    }
                },
                output_schema={
                    "zip_size_bytes": {"type": "integer"},
                    "total_files": {"type": "integer"}
                },
                examples=[]
            ),
            ToolCapability(
                name="list_zip_contents",
                description="List contents of a ZIP file without extracting",
                capability_type=CapabilityType.READ,
                input_schema={
                    "zip_path": {
                        "type": "string",
                        "description": "Path to the ZIP file",
                        "required": True
                    },
                    "password": {
                        "type": "string",
                        "description": "Password for encrypted ZIP (optional)"
                    }
                },
                output_schema={
                    "file_count": {"type": "integer"},
                    "files": {"type": "array"},
                    "compression_ratio_percent": {"type": "number"}
                },
                examples=[]
            )
        ],
        dependencies=[],
        tags={"system", "commands", "security", "cross-platform", "zip"},
        author="MetisAgent3",
        license="MIT"
    )
    
    config = ToolConfiguration(
        tool_name="command_executor",
        enabled=True,
        config={
            "plugin_type": "python_module",
            "module_path": "tools.command_executor_tool",
            "class_name": "CommandExecutorTool"
        },
        environment_variables={},
        resource_limits={
            "max_memory_mb": 100,
            "max_execution_time_seconds": 300
        }
    )
    
    return metadata, config, CommandExecutorTool
