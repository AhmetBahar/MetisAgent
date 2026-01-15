"""
RMMS SCADA Tool Plugin - SCADA Page Design with AI Agent

This plugin enables MetisAgent to design and manage SCADA pages for RMMS:
- Create and configure SCADA pages
- Add and position widgets
- Set widget properties and tag bindings
- Manage page layouts and configurations

CLAUDE.md COMPLIANT:
- Proper architectural design
- No quick fixes
- Database operations via API
"""

from .rmms_scada_tool import RMMSScadaTool

__all__ = ["RMMSScadaTool"]
