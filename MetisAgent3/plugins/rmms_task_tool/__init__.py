"""
RMMS Task Tool Plugin - Task Management with AI Agent

This plugin enables MetisAgent to manage tasks in RMMS:
- Create and manage tasks
- Assign tasks to users
- Track task progress and status
- Add comments and notes
- Set priorities and due dates

Task States:
- pending: Task created but not started
- in_progress: Task being worked on
- completed: Task finished
- cancelled: Task cancelled

CLAUDE.md COMPLIANT:
- Proper architectural design
- No quick fixes
- Database operations via API
"""

from .rmms_task_tool import RMMSTaskTool

__all__ = ["RMMSTaskTool"]
