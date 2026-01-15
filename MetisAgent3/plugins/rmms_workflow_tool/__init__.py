"""
RMMS Workflow Tool Plugin - Workflow Design with AI Agent

This plugin enables MetisAgent to design and manage workflows for RMMS:
- Create and configure workflows
- Add workflow nodes (triggers, conditions, actions)
- Define node connections and flow
- Manage workflow execution parameters

CLAUDE.md COMPLIANT:
- Proper architectural design
- No quick fixes
- Database operations via API
"""

from .rmms_workflow_tool import RMMSWorkflowTool

__all__ = ["RMMSWorkflowTool"]
