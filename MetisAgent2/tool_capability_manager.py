"""
Tool Capability Manager - Dynamic tool loading and capability management
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from app.mcp_core import registry

logger = logging.getLogger(__name__)

class ToolCapabilityManager:
    """Manages dynamic tool capabilities and graph memory integration"""
    
    def __init__(self):
        self.graph_memory = None
        self._initialize_graph_memory()
    
    def _initialize_graph_memory(self):
        """Initialize graph memory connection"""
        try:
            # Late import to avoid circular dependencies
            from app.mcp_core import registry
            self.graph_memory = registry.get_tool("graph_memory")
            if not self.graph_memory:
                logger.error("Graph memory tool not available")
            else:
                logger.info("Graph memory tool connected successfully")
        except Exception as e:
            logger.error(f"Failed to initialize graph memory: {e}")
    
    def sync_all_tools_to_memory(self, user_id: str = "system"):
        """Sync all registered tools to graph memory for user"""
        try:
            if not self.graph_memory:
                logger.error("Graph memory not available")
                return False
            
            # Get all tools from registry with late import
            from app.mcp_core import registry
            all_tools = registry.list_tools()
            logger.info(f"Syncing {len(all_tools)} tools to graph memory for user {user_id}")
            
            success_count = 0
            for tool_info in all_tools:
                try:
                    # Debug: check tool_info type and content
                    logger.debug(f"Tool info type: {type(tool_info)}, content: {tool_info}")
                    
                    # Ensure tool_info is a dict
                    if isinstance(tool_info, str):
                        logger.warning(f"Tool info is string: {tool_info}, skipping")
                        continue
                    
                    # Store tool capability in graph memory
                    result = self.graph_memory.execute_action(
                        "store_tool_capability",
                        tool_name=tool_info.get("name", "unknown"),
                        tool_info=tool_info,
                        user_id=user_id
                    )
                    
                    if result.success:
                        success_count += 1
                        logger.info(f"Synced tool: {tool_info.get('name', 'unknown')}")
                    else:
                        logger.error(f"Failed to sync tool {tool_info.get('name', 'unknown')}: {result.error}")
                        
                except Exception as e:
                    logger.error(f"Error syncing tool {tool_info.get('name', 'unknown')}: {e}")
            
            logger.info(f"Successfully synced {success_count}/{len(all_tools)} tools to graph memory")
            return success_count == len(all_tools)
            
        except Exception as e:
            logger.error(f"Failed to sync tools to memory: {e}")
            return False
    
    def get_user_tool_prompt(self, user_id: str = "system") -> Optional[str]:
        """Get dynamic tool prompt for user from graph memory"""
        try:
            # Lazy loading: try to get graph_memory again if not available
            if not self.graph_memory:
                self._initialize_graph_memory()
                if not self.graph_memory:
                    logger.warning("Graph memory still not available for tool prompt generation")
                    return None
            
            result = self.graph_memory.execute_action(
                "generate_tool_prompt",
                user_id=user_id
            )
            
            if result.success:
                return result.data.get("prompt_template", "")
            else:
                logger.error(f"Failed to generate tool prompt: {result.error}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating tool prompt: {e}")
            return None
    
    def log_tool_operation(self, user_id: str, tool_name: str, action_name: str, 
                          result_data: Dict, parameters: Dict = None):
        """Log tool operation to graph memory"""
        try:
            if not self.graph_memory:
                return
            
            result = self.graph_memory.execute_action(
                action_name="log_tool_operation",
                tool_name=tool_name,
                action_name_param=action_name,
                result=result_data,
                user_id=user_id,
                parameters=parameters
            )
            
            if not result.success:
                logger.warning(f"Failed to log tool operation: {result.error}")
            
        except Exception as e:
            logger.error(f"Error logging tool operation: {e}")
    
    def add_tool_for_user(self, user_id: str, tool_name: str, tool_info: Dict):
        """Add a specific tool for a user"""
        try:
            if not self.graph_memory:
                return False
            
            result = self.graph_memory.execute_action(
                "store_tool_capability",
                tool_name=tool_name,
                tool_info=tool_info,
                user_id=user_id
            )
            
            if result.success:
                logger.info(f"Added tool {tool_name} for user {user_id}")
                return True
            else:
                logger.error(f"Failed to add tool {tool_name}: {result.error}")
                return False
                
        except Exception as e:
            logger.error(f"Error adding tool for user: {e}")
            return False
    
    def get_user_tools(self, user_id: str = "system") -> List[Dict]:
        """Get all tools available to a user"""
        try:
            if not self.graph_memory:
                return []
            
            result = self.graph_memory.execute_action(
                "get_user_tools",
                user_id=user_id
            )
            
            if result.success:
                return result.data.get("tools", [])
            else:
                logger.error(f"Failed to get user tools: {result.error}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting user tools: {e}")
            return []

# Global instance
tool_capability_manager = ToolCapabilityManager()

def initialize_tool_capabilities():
    """Initialize tool capabilities at system startup"""
    logger.info("Initializing tool capabilities...")
    
    # Sync all tools for system user
    success = tool_capability_manager.sync_all_tools_to_memory("system")
    
    if success:
        logger.info("✅ Tool capabilities initialized successfully")
    else:
        logger.warning("⚠️ Some tools failed to sync to graph memory")
    
    return success

def get_user_tool_prompt(user_id: str) -> Optional[str]:
    """Get dynamic tool prompt for user"""
    return tool_capability_manager.get_user_tool_prompt(user_id)

def log_user_tool_operation(user_id: str, tool_name: str, action_name: str, 
                           result_data: Dict, parameters: Dict = None):
    """Log user tool operation"""
    tool_capability_manager.log_tool_operation(
        user_id, tool_name, action_name, result_data, parameters
    )

def get_capability_manager() -> ToolCapabilityManager:
    """Get global capability manager instance"""
    return tool_capability_manager