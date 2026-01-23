"""
Computer Security Service - Security Modes for Computer Tools

Implements three security modes for computer tools (file, browser, code execution):
- off: Computer tools completely disabled
- restricted: Limited operations with whitelist/blacklist rules
- dev: Full access (development mode only)

Security Layers:
1. Mode check - is the mode enabled?
2. Path validation - is the path allowed?
3. Operation validation - is the operation allowed?
4. Confirmation check - does this require user confirmation?
"""

import os
import re
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from pathlib import Path

from ..contracts.tool_envelope import RiskLevel, ConfirmationPolicy

logger = logging.getLogger(__name__)


class ComputerMode(str, Enum):
    """Security mode for computer tools"""
    OFF = "off"            # Computer tools disabled
    RESTRICTED = "restricted"  # Limited with whitelist/blacklist
    DEV = "dev"           # Full access (development only)


class OperationResult(str, Enum):
    """Result of security check"""
    ALLOWED = "allowed"
    DENIED = "denied"
    REQUIRES_CONFIRMATION = "requires_confirmation"


@dataclass
class SecurityCheckResult:
    """Result of a security check"""
    allowed: bool
    result: OperationResult
    reason: Optional[str] = None
    requires_confirmation: bool = False
    confirmation_message: Optional[str] = None
    risk_level: RiskLevel = RiskLevel.LOW


@dataclass
class RestrictedModeConfig:
    """Configuration for restricted mode"""
    # Path whitelists (allowed paths)
    allowed_paths: Set[str] = field(default_factory=lambda: {
        "/tmp",
        "/home/*/projects",
        "/var/log"
    })

    # Path blacklists (always denied)
    denied_paths: Set[str] = field(default_factory=lambda: {
        "/etc/passwd",
        "/etc/shadow",
        "~/.ssh",
        "~/.aws",
        "~/.config/gcloud",
        "*.pem",
        "*.key",
        "*credentials*",
        "*secrets*"
    })

    # Allowed file extensions
    allowed_extensions: Set[str] = field(default_factory=lambda: {
        ".txt", ".json", ".csv", ".log", ".md",
        ".py", ".js", ".ts", ".html", ".css",
        ".yaml", ".yml", ".xml", ".toml"
    })

    # Denied extensions (always blocked)
    denied_extensions: Set[str] = field(default_factory=lambda: {
        ".exe", ".dll", ".so", ".dylib",
        ".sh", ".bash", ".bat", ".cmd", ".ps1",
        ".pem", ".key", ".crt"
    })

    # Allowed URL patterns (for browser tools)
    allowed_url_patterns: List[str] = field(default_factory=lambda: [
        r"^https://docs\.",
        r"^https://api\.",
        r"^https://github\.com/",
        r"^https://stackoverflow\.com/"
    ])

    # Denied URL patterns
    denied_url_patterns: List[str] = field(default_factory=lambda: [
        r"^file://",
        r"^javascript:",
        r"localhost",
        r"127\.0\.0\.1",
        r"192\.168\.",
        r"10\.\d+\.\d+\.\d+"
    ])

    # Max file size for read/write (bytes)
    max_file_size: int = 10 * 1024 * 1024  # 10MB

    # Operations requiring confirmation
    confirmation_operations: Set[str] = field(default_factory=lambda: {
        "delete_file",
        "delete_directory",
        "execute_code",
        "execute_shell",
        "write_file",
        "move_file"
    })


class ComputerSecurityService:
    """
    Service for enforcing security modes on computer tools.

    Usage:
        security = ComputerSecurityService(mode=ComputerMode.RESTRICTED)
        result = security.check_file_operation("read", "/tmp/test.txt")
        if result.allowed:
            # proceed with operation
    """

    def __init__(
        self,
        mode: ComputerMode = ComputerMode.OFF,
        config: Optional[RestrictedModeConfig] = None
    ):
        self.mode = mode
        self.config = config or RestrictedModeConfig()
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for URL matching"""
        self._allowed_url_patterns = [
            re.compile(p) for p in self.config.allowed_url_patterns
        ]
        self._denied_url_patterns = [
            re.compile(p) for p in self.config.denied_url_patterns
        ]

    def set_mode(self, mode: ComputerMode):
        """Set security mode"""
        logger.info(f"Computer security mode changed: {self.mode} -> {mode}")
        self.mode = mode

    def check_file_operation(
        self,
        operation: str,
        file_path: str,
        file_size: Optional[int] = None
    ) -> SecurityCheckResult:
        """
        Check if a file operation is allowed.

        Args:
            operation: Operation type (read, write, delete, move, etc.)
            file_path: Path to the file
            file_size: Size of file in bytes (for write operations)

        Returns:
            SecurityCheckResult
        """
        # Mode: OFF - all file operations denied
        if self.mode == ComputerMode.OFF:
            return SecurityCheckResult(
                allowed=False,
                result=OperationResult.DENIED,
                reason="Computer tools are disabled (mode: off)"
            )

        # Mode: DEV - all operations allowed
        if self.mode == ComputerMode.DEV:
            return SecurityCheckResult(
                allowed=True,
                result=OperationResult.ALLOWED,
                reason="Development mode - all operations allowed",
                risk_level=RiskLevel.HIGH
            )

        # Mode: RESTRICTED - apply rules
        return self._check_restricted_file_operation(operation, file_path, file_size)

    def _check_restricted_file_operation(
        self,
        operation: str,
        file_path: str,
        file_size: Optional[int]
    ) -> SecurityCheckResult:
        """Check file operation in restricted mode"""
        path = Path(file_path).resolve()
        path_str = str(path)

        # Check denied paths first (blacklist)
        for denied in self.config.denied_paths:
            if self._path_matches(path_str, denied):
                return SecurityCheckResult(
                    allowed=False,
                    result=OperationResult.DENIED,
                    reason=f"Path is in denied list: {denied}"
                )

        # Check denied extensions
        if path.suffix.lower() in self.config.denied_extensions:
            return SecurityCheckResult(
                allowed=False,
                result=OperationResult.DENIED,
                reason=f"File extension not allowed: {path.suffix}"
            )

        # Check allowed paths (whitelist)
        path_allowed = False
        for allowed in self.config.allowed_paths:
            if self._path_matches(path_str, allowed):
                path_allowed = True
                break

        if not path_allowed:
            return SecurityCheckResult(
                allowed=False,
                result=OperationResult.DENIED,
                reason="Path not in allowed list"
            )

        # Check file size for write operations
        if operation in ("write", "write_file") and file_size:
            if file_size > self.config.max_file_size:
                return SecurityCheckResult(
                    allowed=False,
                    result=OperationResult.DENIED,
                    reason=f"File size exceeds limit: {file_size} > {self.config.max_file_size}"
                )

        # Check if operation requires confirmation
        if operation in self.config.confirmation_operations:
            return SecurityCheckResult(
                allowed=True,
                result=OperationResult.REQUIRES_CONFIRMATION,
                requires_confirmation=True,
                confirmation_message=f"Confirm {operation} on {file_path}?",
                risk_level=RiskLevel.MEDIUM
            )

        # Operation allowed
        return SecurityCheckResult(
            allowed=True,
            result=OperationResult.ALLOWED,
            risk_level=RiskLevel.LOW
        )

    def _path_matches(self, path: str, pattern: str) -> bool:
        """Check if path matches a pattern (supports * wildcards)"""
        # Expand ~ to home directory
        pattern = os.path.expanduser(pattern)

        # Convert glob-style to regex
        regex_pattern = pattern.replace("*", ".*")
        try:
            return bool(re.match(regex_pattern, path))
        except re.error:
            return pattern in path

    def check_browser_operation(
        self,
        operation: str,
        url: str
    ) -> SecurityCheckResult:
        """
        Check if a browser operation is allowed.

        Args:
            operation: Operation type (navigate, fetch, etc.)
            url: Target URL

        Returns:
            SecurityCheckResult
        """
        # Mode: OFF - all browser operations denied
        if self.mode == ComputerMode.OFF:
            return SecurityCheckResult(
                allowed=False,
                result=OperationResult.DENIED,
                reason="Computer tools are disabled (mode: off)"
            )

        # Mode: DEV - all operations allowed
        if self.mode == ComputerMode.DEV:
            return SecurityCheckResult(
                allowed=True,
                result=OperationResult.ALLOWED,
                reason="Development mode - all operations allowed",
                risk_level=RiskLevel.HIGH
            )

        # Mode: RESTRICTED - check URL patterns
        return self._check_restricted_browser_operation(operation, url)

    def _check_restricted_browser_operation(
        self,
        operation: str,
        url: str
    ) -> SecurityCheckResult:
        """Check browser operation in restricted mode"""
        # Check denied patterns first
        for pattern in self._denied_url_patterns:
            if pattern.search(url):
                return SecurityCheckResult(
                    allowed=False,
                    result=OperationResult.DENIED,
                    reason=f"URL matches denied pattern: {pattern.pattern}"
                )

        # Check allowed patterns
        url_allowed = False
        for pattern in self._allowed_url_patterns:
            if pattern.search(url):
                url_allowed = True
                break

        if not url_allowed:
            return SecurityCheckResult(
                allowed=False,
                result=OperationResult.DENIED,
                reason="URL not in allowed list"
            )

        return SecurityCheckResult(
            allowed=True,
            result=OperationResult.ALLOWED,
            risk_level=RiskLevel.LOW
        )

    def check_code_execution(
        self,
        language: str,
        code: str,
        sandbox: bool = False
    ) -> SecurityCheckResult:
        """
        Check if code execution is allowed.

        Args:
            language: Programming language
            code: Code to execute
            sandbox: Whether execution is sandboxed

        Returns:
            SecurityCheckResult
        """
        # Mode: OFF - all code execution denied
        if self.mode == ComputerMode.OFF:
            return SecurityCheckResult(
                allowed=False,
                result=OperationResult.DENIED,
                reason="Computer tools are disabled (mode: off)"
            )

        # Mode: DEV - all execution allowed
        if self.mode == ComputerMode.DEV:
            return SecurityCheckResult(
                allowed=True,
                result=OperationResult.ALLOWED,
                reason="Development mode - all operations allowed",
                risk_level=RiskLevel.CRITICAL
            )

        # Mode: RESTRICTED - only sandboxed execution allowed
        if not sandbox:
            return SecurityCheckResult(
                allowed=False,
                result=OperationResult.DENIED,
                reason="Code execution requires sandbox in restricted mode"
            )

        # Check for dangerous patterns in code
        dangerous_patterns = [
            r"os\.system",
            r"subprocess",
            r"eval\s*\(",
            r"exec\s*\(",
            r"__import__",
            r"open\s*\([^)]*['\"]w['\"]",
            r"rm\s+-rf",
            r"chmod\s+777"
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                return SecurityCheckResult(
                    allowed=True,
                    result=OperationResult.REQUIRES_CONFIRMATION,
                    requires_confirmation=True,
                    confirmation_message=f"Code contains potentially dangerous pattern: {pattern}",
                    risk_level=RiskLevel.HIGH
                )

        return SecurityCheckResult(
            allowed=True,
            result=OperationResult.ALLOWED,
            requires_confirmation=True,  # Always confirm code execution
            confirmation_message=f"Confirm execution of {language} code?",
            risk_level=RiskLevel.MEDIUM
        )

    def get_status(self) -> Dict[str, Any]:
        """Get current security status"""
        return {
            "mode": self.mode.value,
            "allowed_paths_count": len(self.config.allowed_paths),
            "denied_paths_count": len(self.config.denied_paths),
            "allowed_extensions": list(self.config.allowed_extensions),
            "denied_extensions": list(self.config.denied_extensions),
            "max_file_size": self.config.max_file_size,
            "confirmation_operations": list(self.config.confirmation_operations)
        }


def create_security_service_for_environment(env: str) -> ComputerSecurityService:
    """
    Factory function to create security service based on environment.

    Args:
        env: Environment name (production, staging, development, test)

    Returns:
        Configured ComputerSecurityService
    """
    if env == "production":
        return ComputerSecurityService(mode=ComputerMode.OFF)
    elif env == "staging":
        return ComputerSecurityService(mode=ComputerMode.RESTRICTED)
    elif env == "development":
        return ComputerSecurityService(mode=ComputerMode.DEV)
    elif env == "test":
        return ComputerSecurityService(mode=ComputerMode.RESTRICTED)
    else:
        # Default to most restrictive
        return ComputerSecurityService(mode=ComputerMode.OFF)
