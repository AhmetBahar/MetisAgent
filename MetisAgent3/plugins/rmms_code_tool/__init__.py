"""
RMMS Code Tool Plugin - Code Editor with AI Agent

This plugin enables MetisAgent to create and manage user codes in RMMS:
- Create and edit Python/C# codes
- Save codes to database
- Execute code validation
- Manage code templates

Supported Languages:
- Python: For data processing, calculations, and automation scripts
- C#: For .NET integration and system-level operations

CLAUDE.md COMPLIANT:
- Proper architectural design
- No quick fixes
- Database operations via API
"""

from .rmms_code_tool import RMMSCodeTool

__all__ = ["RMMSCodeTool"]
