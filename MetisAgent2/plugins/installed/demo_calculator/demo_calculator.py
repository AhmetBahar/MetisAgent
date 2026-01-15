"""
Demo_Calculator Plugin for MetisAgent2
"""

import logging
import sys
import os
from typing import Dict, Any, List
from datetime import datetime

# Add parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.mcp_core import MCPTool, MCPToolResult

logger = logging.getLogger(__name__)

class Demo_CalculatorTool(MCPTool):
    """Demo_Calculator tool implementation"""
    
    def __init__(self):
        """Initialize demo_calculator tool"""
        super().__init__(
            name="demo_calculator",
            description="Demo_Calculator operations and functionality",
            version="1.0.0"
        )
        
        # Register capabilities
        self.add_capability("demo_calculator_operations")
        
        # Register actions
        self.register_action(
            "hello",
            self._hello,
            required_params=["name"],
            optional_params=["message"]
        )
    
    def _hello(self, name: str, message: str = "Hello") -> MCPToolResult:
        """Simple hello action"""
        try:
            response = f"{message} {name}! This is the {self.name} plugin."
            
            return MCPToolResult(
                success=True,
                data={"response": response, "timestamp": datetime.now().isoformat()},
                metadata={"action": "hello", "plugin": self.name}
            )
            
        except Exception as e:
            logger.error(f"Error in hello action: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
                metadata={"action": "hello", "plugin": self.name}
            )

def register_tool(registry):
    """Register demo_calculator tool with the registry"""
    try:
        tool = Demo_CalculatorTool()
        registry.register_tool(tool)
        logger.info("Demo_Calculator plugin registered successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to register demo_calculator plugin: {e}")
        return False

def unregister_tool(registry):
    """Unregister demo_calculator tool from the registry"""
    try:
        registry.unregister_tool("demo_calculator")
        logger.info("Demo_Calculator plugin unregistered successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to unregister demo_calculator plugin: {e}")
        return False
