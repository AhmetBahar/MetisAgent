"""
Google Tool Plugin - Complete Google Workspace Integration

CLAUDE.md COMPLIANT:
- OAuth2 authentication with encrypted token storage
- Gmail, Calendar, and Drive operations
- User-isolated credentials management
- Fault-tolerant error handling
- No quick fixes - proper architectural design
"""

from .google_tool import GoogleTool

__all__ = ["GoogleTool"]