"""
Memory Manager Implementation - Graph-Based Memory with Tool Capability Management

CLAUDE.md COMPLIANT:
- MCP memory server integration with fallback
- User-isolated tool capability storage
- Dynamic tool prompt generation
- Professional tool metadata management
"""

import asyncio
import json
import subprocess
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
from pathlib import Path
import logging

from ..contracts import (
    MemoryEntry,
    MemoryQuery,
    MemorySearchResult,
    GraphEntity,
    GraphRelationship,
    ConversationMemory,
    MemoryInsight,
    ToolMetadata,
    ToolConfiguration,
    AgentResult,
    ExecutionContext,
    EntityType,
    RelationType
)
from ..interfaces import (
    IMemoryService,
    IGraphService,
    IConversationService
)

logger = logging.getLogger(__name__)


class MCPMemoryClient:
    """MCP Memory server client with JSON-RPC over stdio"""
    
    def __init__(self, server_command: List[str]):
        self.server_command = server_command
        self.process = None
        self.is_connected = False
    
    async def connect(self):
        """Connect to MCP memory server"""
        try:
            self.process = await asyncio.create_subprocess_exec(
                *self.server_command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Test connection with ping
            test_result = await self._call_method("ping", {})
            self.is_connected = test_result is not None
            
            if self.is_connected:
                logger.info("Connected to MCP memory server")
            else:
                logger.error("Failed to connect to MCP memory server")
                
        except Exception as e:
            logger.error(f"MCP memory server connection failed: {e}")
            self.is_connected = False
    
    async def disconnect(self):
        """Disconnect from MCP memory server"""
        if self.process and self.process.returncode is None:
            self.process.terminate()
            await self.process.wait()
            self.is_connected = False
    
    async def _call_method(self, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make JSON-RPC call to MCP server"""
        if not self.is_connected or not self.process:
            return None
        
        try:
            request = {
                "jsonrpc": "2.0",
                "id": str(datetime.now().timestamp()),
                "method": method,
                "params": params
            }
            
            # Send request
            self.process.stdin.write(json.dumps(request).encode() + b'\n')
            await self.process.stdin.drain()
            
            # Read response
            response_line = await asyncio.wait_for(
                self.process.stdout.readline(),
                timeout=10.0
            )
            
            if not response_line:
                return None
            
            response = json.loads(response_line.decode())
            
            if "error" in response:
                logger.error(f"MCP method {method} error: {response['error']}")
                return None
            
            return response.get("result")
            
        except Exception as e:
            logger.error(f"MCP method call failed: {e}")
            return None
    
    async def create_entities(self, entities: List[Dict[str, Any]]) -> bool:
        """Create entities in graph memory"""
        result = await self._call_method("create_entities", {"entities": entities})
        return result is not None
    
    async def create_relations(self, relations: List[Dict[str, Any]]) -> bool:
        """Create relationships in graph memory"""
        result = await self._call_method("create_relations", {"relations": relations})
        return result is not None
    
    async def search_nodes(self, query: str) -> Optional[Dict[str, Any]]:
        """Search nodes in graph memory"""
        return await self._call_method("search_nodes", {"query": query})
    
    async def open_nodes(self, names: List[str]) -> Optional[Dict[str, Any]]:
        """Open specific nodes by names"""
        return await self._call_method("open_nodes", {"names": names})


class GraphMemoryService(IMemoryService, IGraphService, IConversationService):
    """Professional graph-based memory with tool capability management"""
    
    def __init__(self, mcp_server_command: Optional[List[str]] = None):
        self.mcp_client = None
        self.local_storage: Dict[str, Any] = {}
        self.tool_capabilities: Dict[str, Dict[str, Any]] = {}
        self.user_tool_access: Dict[str, Set[str]] = {}
        
        # Performance caches
        self._tool_prompt_cache: Dict[str, str] = {}
        self._user_tools_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_ttl_seconds = 300  # 5 minutes cache TTL
        
        # Initialize MCP client if server command provided
        if mcp_server_command:
            self.mcp_client = MCPMemoryClient(mcp_server_command)
        
        # Load local storage
        self._load_local_storage()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid"""
        if cache_key not in self._cache_timestamps:
            return False
        
        cache_time = self._cache_timestamps[cache_key]
        now = datetime.now()
        return (now - cache_time).total_seconds() < self._cache_ttl_seconds
    
    def _invalidate_user_cache(self, user_id: str):
        """Invalidate all cache entries for a user"""
        cache_keys_to_remove = []
        for key in self._cache_timestamps:
            if key.startswith(f"user_{user_id}_"):
                cache_keys_to_remove.append(key)
        
        for key in cache_keys_to_remove:
            self._tool_prompt_cache.pop(key, None)
            self._user_tools_cache.pop(key, None)
            self._cache_timestamps.pop(key, None)
    
    async def initialize(self):
        """Initialize the memory service"""
        if self.mcp_client:
            await self.mcp_client.connect()
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.mcp_client:
            await self.mcp_client.disconnect()
        self._save_local_storage()
    
    # Tool Capability Management Methods
    async def sync_tool_capabilities(self, metadata: ToolMetadata, config: ToolConfiguration, user_id: str = "system") -> bool:
        """Sync tool capabilities to graph memory"""
        try:
            tool_info = {
                "name": metadata.name,
                "description": metadata.description,
                "version": metadata.version,
                "tool_type": metadata.tool_type.value,
                "capabilities": [
                    {
                        "name": cap.name,
                        "description": cap.description,
                        "capability_type": cap.capability_type.value,
                        "input_schema": cap.input_schema,
                        "output_schema": cap.output_schema,
                        "examples": cap.examples
                    } for cap in metadata.capabilities
                ],
                "dependencies": metadata.dependencies,
                "tags": list(metadata.tags),
                "application_id": getattr(metadata, 'application_id', None),
                "usage_patterns": getattr(metadata, 'usage_patterns', []),
                "last_updated": datetime.now().isoformat()
            }
            
            # Store in local cache
            self.tool_capabilities[metadata.name] = tool_info

            # DEBUG: Log SCADA capabilities being synced
            if metadata.name == 'rmms_scada_tool':
                cap_names = [cap.name for cap in metadata.capabilities]
                logger.info(f"🔍 DEBUG SCADA sync capabilities: {cap_names}")

            # Try to store in MCP memory
            if self.mcp_client and self.mcp_client.is_connected:
                entity = {
                    "name": f"tool_{metadata.name}",
                    "entityType": "tool",
                    "observations": [
                        f"Tool Name: {metadata.name}",
                        f"Description: {metadata.description}",
                        f"Type: {metadata.tool_type.value}",
                        f"Capabilities: {', '.join([cap.name for cap in metadata.capabilities])}",
                        f"Version: {metadata.version}"
                    ]
                }
                
                await self.mcp_client.create_entities([entity])
                
                # Create user-tool relationship
                if user_id != "system":
                    await self._create_user_tool_relation(user_id, metadata.name)
            
            # Update user tool access
            if user_id not in self.user_tool_access:
                self.user_tool_access[user_id] = set()
            self.user_tool_access[user_id].add(metadata.name)
            
            # Invalidate cache since tools changed
            self._invalidate_user_cache(user_id)
            
            logger.info(f"Synced tool {metadata.name} capabilities to memory")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync tool capabilities: {e}")
            return False
    
    async def get_user_tools(self, user_id: str) -> List[Dict[str, Any]]:
        """Get tools available to specific user with caching"""
        cache_key = f"user_{user_id}_tools"

        # Check cache first
        if self._is_cache_valid(cache_key) and cache_key in self._user_tools_cache:
            logger.info(f"🚀 Cache HIT for user tools: {user_id}")
            return self._user_tools_cache[cache_key]

        try:
            # Start with system tools as base for all users
            system_tools = self.user_tool_access.get("system", set())
            user_specific_tools = self.user_tool_access.get(user_id, set())

            # Merge system tools with user-specific tools
            user_tools = system_tools.union(user_specific_tools)

            tools = []
            for tool_name in user_tools:
                tool_info = self.tool_capabilities.get(tool_name)
                if tool_info:
                    tools.append(tool_info)
                    # DEBUG: Log SCADA capabilities from cache
                    if tool_name == 'rmms_scada_tool':
                        caps = tool_info.get('capabilities', [])
                        cap_names = [c.get('name', 'unknown') for c in caps]
                        logger.info(f"🔍 DEBUG SCADA from cache: {cap_names}")

            # Cache the result
            self._user_tools_cache[cache_key] = tools
            self._cache_timestamps[cache_key] = datetime.now()
            logger.info(f"💾 Cached user tools for: {user_id} ({len(tools)} tools)")

            return tools
            
        except Exception as e:
            logger.error(f"Failed to get user tools: {e}")
            return []
    
    async def generate_tool_prompt(self, user_id: str) -> str:
        """Generate dynamic tool prompt for LLM with platform-specific examples (CACHED)"""
        cache_key = f"user_{user_id}_prompt"
        
        # Check cache first - tool prompts rarely change
        if self._is_cache_valid(cache_key) and cache_key in self._tool_prompt_cache:
            logger.info(f"🚀 Cache HIT for tool prompt: {user_id}")
            return self._tool_prompt_cache[cache_key]
        
        try:
            user_tools = await self.get_user_tools(user_id)
            if not user_tools:
                return "No tools available for this user."
            
            prompt_parts = [
                "AVAILABLE TOOLS AND CAPABILITIES:",
                "You have access to the following tools and their capabilities:",
                ""
            ]
            
            for tool in user_tools:
                prompt_parts.extend([
                    f"## {tool['name'].upper()} ({tool['tool_type']})",
                    f"Description: {tool['description']}",
                    f"Version: {tool['version']}",
                    ""
                ])
                
                if tool['capabilities']:
                    prompt_parts.append("Capabilities:")
                    for cap in tool['capabilities']:
                        prompt_parts.append(f"- **{cap['name']}**: {cap['description']}")
                        if cap.get('examples'):
                            prompt_parts.append(f"  Examples: {cap['examples']}")
                    prompt_parts.append("")
                
                if tool['dependencies']:
                    prompt_parts.append(f"Dependencies: {', '.join(tool['dependencies'])}")
                    prompt_parts.append("")
                
                # Add platform-specific command examples for command_executor
                if tool['name'] == 'command_executor':
                    prompt_parts.extend([
                        "### PLATFORM-SPECIFIC COMMAND EXAMPLES:",
                        "",
                        "**Linux/WSL DNS Commands:**",
                        "- `cat /etc/resolv.conf` - Show current DNS servers",
                        "- `systemd-resolve --status` - Show detailed DNS status (Ubuntu/Debian)",
                        "- `dig google.com` - Test DNS resolution",
                        "- `nslookup google.com` - Test DNS lookup",
                        "- `host google.com` - Simple DNS lookup",
                        "",
                        "**Network Information:**",
                        "- `ip addr show` - Show network interfaces",
                        "- `ip route show` - Show routing table", 
                        "- `netstat -tuln` - Show listening ports",
                        "- `ss -tuln` - Show socket statistics",
                        "",
                        "**System Information:**",
                        "- `uname -a` - Show system information",
                        "- `lsb_release -a` - Show Linux distribution info",
                        "- `cat /proc/version` - Show kernel version",
                        "- `df -h` - Show disk usage",
                        "- `free -h` - Show memory usage",
                        "",
                        "**File Operations:**",
                        "- `ls -la /path` - List directory contents",
                        "- `cat /path/file` - Show file contents",
                        "- `grep 'pattern' /path/file` - Search in files",
                        "- `find /path -name 'pattern'` - Find files",
                        "",
                        "**Process Management:**",
                        "- `ps aux` - Show running processes",
                        "- `top -n 1 -b` - Show system performance",
                        "- `systemctl status service` - Show service status",
                        "",
                    ])
            
            prompt_parts.extend([
                "USAGE INSTRUCTIONS:",
                "- Use tools by specifying the tool name and capability",
                "- For command_executor, always provide specific commands with parameters",
                "- Choose platform-appropriate commands (Linux/WSL commands shown above)",
                "- Validate commands before execution when possible",
                "- Chain multiple commands for complex information gathering",
                "- Consider security implications of commands",
                "- Provide meaningful error handling",
                "",
                "COMMAND SELECTION GUIDELINES:",
                "- For DNS info: Use `cat /etc/resolv.conf` for basic info, `dig` or `nslookup` for testing",
                "- For network info: Use `ip` commands over deprecated `ifconfig`",
                "- For system info: Combine multiple commands for comprehensive details",
                "- For file operations: Use appropriate flags for human-readable output",
                "",
                "WORKFLOW ORDERING PRINCIPLES:",
                "- Place the PRIMARY ACTION (the actual information gathering) as the LAST STEP",
                "- Use validation/preparation steps BEFORE the main action",
                "- The final step's output becomes the user's response",
                "- Example: Step 1=Validate, Step 2=Execute and show DNS info",
                ""
            ])
            
            final_prompt = "\n".join(prompt_parts)
            
            # Cache the generated prompt
            self._tool_prompt_cache[cache_key] = final_prompt
            self._cache_timestamps[cache_key] = datetime.now()
            logger.info(f"💾 Cached tool prompt for: {user_id} ({len(final_prompt)} chars)")
            
            return final_prompt
            
        except Exception as e:
            logger.error(f"Failed to generate tool prompt: {e}")
            return "Error generating tool prompt."
    
    async def add_tool_for_user(self, user_id: str, tool_name: str) -> bool:
        """Grant tool access to specific user"""
        try:
            if user_id not in self.user_tool_access:
                self.user_tool_access[user_id] = set()
            
            self.user_tool_access[user_id].add(tool_name)
            
            # Create relationship in MCP memory
            if self.mcp_client and self.mcp_client.is_connected:
                await self._create_user_tool_relation(user_id, tool_name)
            
            # Invalidate cache since user tools changed
            self._invalidate_user_cache(user_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add tool for user: {e}")
            return False
    
    async def remove_tool_for_user(self, user_id: str, tool_name: str) -> bool:
        """Remove tool access from specific user"""
        try:
            if user_id in self.user_tool_access:
                self.user_tool_access[user_id].discard(tool_name)
            return True
        except Exception as e:
            logger.error(f"Failed to remove tool for user: {e}")
            return False
    
    async def log_tool_operation(self, user_id: str, tool_name: str, capability: str, 
                                result: AgentResult, execution_time_ms: float) -> bool:
        """Log tool operation for analytics"""
        try:
            operation_log = {
                "user_id": user_id,
                "tool_name": tool_name,
                "capability": capability,
                "success": result.success,
                "execution_time_ms": execution_time_ms,
                "timestamp": datetime.now().isoformat(),
                "error": result.error if not result.success else None
            }
            
            # Store in local cache
            if "tool_operations" not in self.local_storage:
                self.local_storage["tool_operations"] = []
            self.local_storage["tool_operations"].append(operation_log)
            
            # Try to store in MCP memory as observation
            if self.mcp_client and self.mcp_client.is_connected:
                observation = f"Tool operation: {tool_name}.{capability} by {user_id} - {'Success' if result.success else 'Failed'} ({execution_time_ms}ms)"
                # Would add as observation to user entity
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to log tool operation: {e}")
            return False
    
    # Memory Service Interface Implementation
    async def store_memory(self, entry: MemoryEntry) -> str:
        """Store memory entry"""
        try:
            entry_id = entry.id
            
            # Store locally
            if "memories" not in self.local_storage:
                self.local_storage["memories"] = {}
            self.local_storage["memories"][entry_id] = entry.dict()
            
            # Try to store in MCP memory
            if self.mcp_client and self.mcp_client.is_connected:
                entity = {
                    "name": f"memory_{entry_id}",
                    "entityType": entry.memory_type.value,
                    "observations": [
                        f"Content: {json.dumps(entry.content)}",
                        f"Tags: {', '.join(entry.tags)}",
                        f"Created: {entry.created_at.isoformat()}"
                    ]
                }
                await self.mcp_client.create_entities([entity])
            
            return entry_id
            
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            return ""
    
    async def retrieve_memory(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve memory entry by ID"""
        try:
            memories = self.local_storage.get("memories", {})
            entry_data = memories.get(entry_id)
            
            if entry_data:
                return MemoryEntry(**entry_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve memory: {e}")
            return None
    
    async def search_memories(self, query: MemoryQuery) -> MemorySearchResult:
        """Search memories with query"""
        try:
            memories = self.local_storage.get("memories", {})
            matching_entries = []
            
            for entry_data in memories.values():
                entry = MemoryEntry(**entry_data)
                
                # Filter by user_id
                if entry.user_id != query.user_id:
                    continue
                
                # Filter by memory types
                if query.memory_types and entry.memory_type not in query.memory_types:
                    continue
                
                # Simple text search
                if query.search_text:
                    content_str = json.dumps(entry.content).lower()
                    if query.search_text.lower() not in content_str:
                        continue
                
                matching_entries.append(entry)
            
            # Apply limit and offset
            start = query.offset
            end = start + query.limit
            limited_entries = matching_entries[start:end]
            
            return MemorySearchResult(
                entries=limited_entries,
                total_count=len(matching_entries),
                query=query,
                search_time_ms=0.0  # Would measure actual search time
            )
            
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return MemorySearchResult(entries=[], total_count=0, query=query, search_time_ms=0.0)
    
    async def update_memory(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update memory entry"""
        try:
            memories = self.local_storage.get("memories", {})
            if entry_id in memories:
                memories[entry_id].update(updates)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update memory: {e}")
            return False
    
    async def delete_memory(self, entry_id: str) -> bool:
        """Delete memory entry"""
        try:
            memories = self.local_storage.get("memories", {})
            if entry_id in memories:
                del memories[entry_id]
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete memory: {e}")
            return False
    
    async def cleanup_expired_memories(self) -> int:
        """Clean up expired memory entries"""
        try:
            memories = self.local_storage.get("memories", {})
            expired_count = 0
            current_time = datetime.now()
            
            to_delete = []
            for entry_id, entry_data in memories.items():
                entry = MemoryEntry(**entry_data)
                if entry.expires_at and current_time > entry.expires_at:
                    to_delete.append(entry_id)
            
            for entry_id in to_delete:
                del memories[entry_id]
                expired_count += 1
            
            return expired_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired memories: {e}")
            return 0
    
    # Graph Service Interface Implementation
    async def create_entity(self, entity: GraphEntity) -> str:
        """Create knowledge graph entity"""
        # Implementation would go here
        return entity.id
    
    async def get_entity(self, entity_id: str) -> Optional[GraphEntity]:
        """Get entity by ID"""
        # Implementation would go here
        return None
    
    async def update_entity(self, entity_id: str, updates: Dict[str, Any]) -> bool:
        """Update entity properties"""
        # Implementation would go here
        return True
    
    async def delete_entity(self, entity_id: str) -> bool:
        """Delete entity and its relationships"""
        # Implementation would go here
        return True
    
    async def create_relationship(self, relationship: GraphRelationship) -> str:
        """Create relationship between entities"""
        # Implementation would go here
        return relationship.id
    
    async def get_relationships(self, entity_id: str) -> List[GraphRelationship]:
        """Get all relationships for an entity"""
        # Implementation would go here
        return []
    
    async def delete_relationship(self, relationship_id: str) -> bool:
        """Delete specific relationship"""
        # Implementation would go here
        return True
    
    # Conversation Service Interface Implementation
    async def create_conversation(self, user_id: str, title: Optional[str] = None) -> str:
        """Create new conversation context"""
        if not hasattr(self, '_conversation_service'):
            from ..services.conversation_service import ConversationService
            self._conversation_service = ConversationService()
        
        return await self._conversation_service.create_conversation(
            user_id=user_id,
            title=title or "New Conversation"
        )
    
    async def get_conversation(self, conversation_id: str) -> Optional[ConversationMemory]:
        """Get conversation by ID"""
        if not hasattr(self, '_conversation_service'):
            from ..services.conversation_service import ConversationService
            self._conversation_service = ConversationService()
        
        # This would need user_id - for now return None
        # Real implementation would need to track conversation ownership
        return None
    
    async def add_message(self, conversation_id: str, message: Dict[str, Any]) -> bool:
        """Add message to conversation"""
        if not hasattr(self, '_conversation_service'):
            from ..services.conversation_service import ConversationService
            self._conversation_service = ConversationService()
        
        try:
            await self._conversation_service.add_message(
                conversation_id=conversation_id,
                user_id=message.get('user_id', 'unknown'),
                role=message.get('role', 'user'),
                content=message.get('content', ''),
                metadata=message.get('metadata'),
                token_count=message.get('token_count')
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add message via conversation service: {e}")
            return False
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete conversation"""
        if not hasattr(self, '_conversation_service'):
            from ..services.conversation_service import ConversationService
            self._conversation_service = ConversationService()
        
        # This would need user_id - for now return False
        # Real implementation would need to track conversation ownership
        logger.warning("delete_conversation needs user_id - integration incomplete")
        return False
    
    async def get_conversation_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get conversation history"""
        if not hasattr(self, '_conversation_service'):
            from ..services.conversation_service import ConversationService
            self._conversation_service = ConversationService()
        
        if not user_id:
            logger.warning("get_conversation_history needs user_id")
            return []

        try:
            # Get recent conversations for user
            conversations = await self._conversation_service.get_conversations(
                user_id=user_id,
                limit=limit
            )
            
            result = []
            for conv in conversations:
                # Get recent messages for each conversation
                try:
                    messages = await self._conversation_service.get_messages(
                        conversation_id=conv.id,
                        user_id=user_id,
                        limit=5  # Get last 5 messages per conversation
                    )

                    # Format as conversation history entry
                    if messages:
                        result.append({
                            'id': conv.id,
                            'title': conv.title or f"Conversation {conv.id[:8]}",
                            'created_at': conv.created_at.isoformat(),
                            'updated_at': conv.updated_at.isoformat(),
                            'messages': [
                                {
                                    'role': msg.role,
                                    'content': msg.content,
                                    'created_at': msg.created_at.isoformat()
                                }
                                for msg in messages[-3:]  # Last 3 messages only
                            ]
                        })
                except Exception as msg_error:
                    logger.warning(f"Failed to get messages for conversation {conv.id}: {msg_error}")

            return result
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []
    
    async def search_conversations(self, query: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search conversations"""
        if not hasattr(self, '_conversation_service'):
            from ..services.conversation_service import ConversationService
            self._conversation_service = ConversationService()
        
        if not user_id:
            logger.warning("search_conversations needs user_id")
            return []
        
        try:
            search_results = await self._conversation_service.search_conversations(
                user_id=user_id,
                query=query,
                limit=20,
                include_context=True
            )
            
            return [
                {
                    'conversation_id': result.conversation_id,
                    'message_id': result.message_id,
                    'role': result.role,
                    'content_snippet': result.content_snippet,
                    'relevance_score': result.relevance_score,
                    'created_at': result.created_at.isoformat(),
                    'context_before': result.context_before,
                    'context_after': result.context_after
                }
                for result in search_results
            ]
        except Exception as e:
            logger.error(f"Failed to search conversations: {e}")
            return []
    
    async def update_conversation_summary(self, conversation_id: str, summary: str, user_id: Optional[str] = None) -> bool:
        """Update conversation summary"""
        if not hasattr(self, '_conversation_service'):
            from ..services.conversation_service import ConversationService
            self._conversation_service = ConversationService()
        
        if not user_id:
            logger.warning("update_conversation_summary needs user_id")
            return False
        
        try:
            return await self._conversation_service.update_conversation_summary(
                conversation_id=conversation_id,
                user_id=user_id,
                summary=summary
            )
        except Exception as e:
            logger.error(f"Failed to update conversation summary: {e}")
            return False
    
    async def search_nodes(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search nodes in graph memory - adapter for ReasoningEngine"""
        try:
            # Simple implementation - search through local storage
            memories = self.local_storage.get("memories", {})
            results = []
            
            for entry_id, entry_data in memories.items():
                content_str = str(entry_data.get("content", "")).lower()
                if query.lower() in content_str:
                    results.append({
                        "id": entry_id,
                        "content": content_str[:200],
                        "relevance": 0.8
                    })
                    if len(results) >= limit:
                        break
                        
            return results
        except Exception as e:
            logger.error(f"Search nodes failed: {e}")
            return []
    
    async def search_graph(self, query: str, entity_type: Optional[str] = None) -> List[GraphEntity]:
        """Search graph entities"""
        # Stub implementation - would search through stored entities
        return []
    
    async def traverse_graph(self, start_entity_id: str, max_depth: int = 3) -> List[GraphEntity]:
        """Traverse graph from starting entity"""
        # Stub implementation - would traverse relationships
        return []
    
    # Helper Methods
    async def _create_user_tool_relation(self, user_id: str, tool_name: str):
        """Create user-tool relationship in MCP memory"""
        if self.mcp_client and self.mcp_client.is_connected:
            relation = {
                "from": f"user_{user_id}",
                "to": f"tool_{tool_name}",
                "relationType": "has_access"
            }
            await self.mcp_client.create_relations([relation])
    
    def _load_local_storage(self):
        """Load local storage from disk"""
        try:
            storage_path = Path("graph_memory_storage.json")
            if storage_path.exists():
                with open(storage_path, 'r') as f:
                    data = json.load(f)
                    self.local_storage = data.get("local_storage", {})
                    self.tool_capabilities = data.get("tool_capabilities", {})
                    self.user_tool_access = {
                        k: set(v) for k, v in data.get("user_tool_access", {}).items()
                    }
        except Exception as e:
            logger.error(f"Failed to load local storage: {e}")
    
    def _save_local_storage(self):
        """Save local storage to disk"""
        try:
            storage_path = Path("graph_memory_storage.json")
            data = {
                "local_storage": self.local_storage,
                "tool_capabilities": self.tool_capabilities,
                "user_tool_access": {
                    k: list(v) for k, v in self.user_tool_access.items()
                }
            }
            with open(storage_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save local storage: {e}")