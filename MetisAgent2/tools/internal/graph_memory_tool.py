"""
Graph Memory Tool - Entity-relation based memory system for MetisAgent2
Integrates official MCP Memory Server with fallback to local implementation
"""

import json
import os
import uuid
import subprocess
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.mcp_core import MCPTool, MCPToolResult

logger = logging.getLogger(__name__)

class GraphMemoryTool(MCPTool):
    """Graph-based memory management with entities and relations"""
    
    def __init__(self):
        super().__init__(
            name="graph_memory",
            description="Advanced graph-based memory with MCP server integration",
            version="3.0.0"
        )
        
        # Register capabilities
        self.add_capability("graph_memory")
        self.add_capability("entity_management")
        self.add_capability("relation_mapping")
        self.add_capability("semantic_search")
        self.add_capability("mcp_integration")
        
        # Register actions
        self.register_action(
            "create_entities",
            self._create_entities,
            required_params=["entities"],
            optional_params=["user_id"]
        )
        
        self.register_action(
            "create_relations", 
            self._create_relations,
            required_params=["relations"],
            optional_params=["user_id"]
        )
        
        self.register_action(
            "add_observations",
            self._add_observations,
            required_params=["observations"],
            optional_params=["user_id"]
        )
        
        self.register_action(
            "search_nodes",
            self._search_nodes,
            required_params=["query"],
            optional_params=["user_id"]
        )
        
        self.register_action(
            "read_graph",
            self._read_graph,
            required_params=[],
            optional_params=["user_id"]
        )
        
        self.register_action(
            "open_nodes",
            self._open_nodes,
            required_params=["names"],
            optional_params=["user_id"]
        )
        
        self.register_action(
            "delete_entities",
            self._delete_entities,
            required_params=["entityNames"],
            optional_params=["user_id"]
        )
        
        self.register_action(
            "delete_relations",
            self._delete_relations,
            required_params=["relations"],
            optional_params=["user_id"]
        )
        
        self.register_action(
            "delete_observations",
            self._delete_observations,
            required_params=["deletions"],
            optional_params=["user_id"]
        )
        
        # Tool capability management actions
        self.register_action(
            "store_tool_capability",
            self._store_tool_capability,
            required_params=["tool_name", "tool_info"],
            optional_params=["user_id"]
        )
        
        self.register_action(
            "get_user_tools",
            self._get_user_tools,
            required_params=[],
            optional_params=["user_id"]
        )
        
        self.register_action(
            "log_tool_operation",
            self._log_tool_operation,
            required_params=["tool_name", "action_name", "result"],
            optional_params=["user_id", "parameters"]
        )
        
        self.register_action(
            "generate_tool_prompt",
            self._generate_tool_prompt,
            required_params=[],
            optional_params=["user_id"]
        )
        
        # Context-aware operation retrieval actions
        self.register_action(
            "get_latest_operation",
            self._get_latest_operation,
            required_params=[],
            optional_params=["user_id", "tool_name", "action_type"]
        )
        
        self.register_action(
            "get_context_operation",
            self._get_context_operation,
            required_params=["context_query"],
            optional_params=["user_id"]
        )
        
        # Storage setup
        self.base_storage_path = os.path.join(os.getcwd(), "graph_memory_storage")
        os.makedirs(self.base_storage_path, exist_ok=True)
        
        # MCP Memory server integration
        self.mcp_memory_server_path = self._find_mcp_memory_server()
        self.mcp_available = bool(self.mcp_memory_server_path)
        self.mcp_process = None
        self.mcp_request_id = 0
        
    def __del__(self):
        """Cleanup MCP process on destruction"""
        self._stop_mcp_process()
    
    def _get_user_graph_path(self, user_id: str = "default") -> str:
        """Get user-specific graph storage path"""
        user_dir = os.path.join(self.base_storage_path, user_id)
        os.makedirs(user_dir, exist_ok=True)
        return os.path.join(user_dir, "graph.json")
    
    def _load_graph(self, user_id: str = "default") -> Dict:
        """Load user graph from storage"""
        try:
            graph_path = self._get_user_graph_path(user_id)
            if os.path.exists(graph_path):
                with open(graph_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"entities": [], "relations": []}
        except Exception as e:
            logger.error(f"Error loading graph for user {user_id}: {str(e)}")
            return {"entities": [], "relations": []}
    
    def _save_graph(self, graph: Dict, user_id: str = "default"):
        """Save user graph to storage"""
        try:
            graph_path = self._get_user_graph_path(user_id)
            with open(graph_path, 'w', encoding='utf-8') as f:
                json.dump(graph, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving graph for user {user_id}: {str(e)}")
    
    def _find_mcp_memory_server(self) -> Optional[str]:
        """Find MCP Memory server executable path"""
        possible_paths = [
            "./node_modules/@modelcontextprotocol/server-memory/dist/index.js",
            "./node_modules/.bin/mcp-server-memory",
            "../node_modules/@modelcontextprotocol/server-memory/dist/index.js",
            "/home/ahmet/MetisAgent/node_modules/@modelcontextprotocol/server-memory/dist/index.js"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Found MCP Memory server at: {path}")
                return path
        
        # Fallback: try to find via npm
        try:
            result = subprocess.run(
                ["npm", "list", "@modelcontextprotocol/server-memory", "--depth=0"],
                capture_output=True, text=True, cwd="."
            )
            if result.returncode == 0:
                # Extract path from npm output
                for line in result.stdout.split('\n'):
                    if 'server-memory' in line:
                        logger.info("MCP Memory server found via npm")
                        return "./node_modules/@modelcontextprotocol/server-memory/index.js"
        except Exception as e:
            logger.error(f"Error finding MCP Memory server via npm: {e}")
        
        logger.warning("MCP Memory server not found, using local JSON storage")
        return None
    
    def _start_mcp_process(self):
        """Start persistent MCP Memory server process"""
        try:
            if not self.mcp_memory_server_path:
                return False
                
            if self.mcp_process is None or self.mcp_process.poll() is not None:
                cmd = ["node", self.mcp_memory_server_path]
                self.mcp_process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                logger.info("MCP Memory server process started")
                return True
            return True
        except Exception as e:
            logger.error(f"Error starting MCP Memory server process: {e}")
            return False
    
    def _stop_mcp_process(self):
        """Stop MCP Memory server process"""
        try:
            if self.mcp_process and self.mcp_process.poll() is None:
                self.mcp_process.terminate()
                self.mcp_process.wait(timeout=5)
                logger.info("MCP Memory server process stopped")
        except Exception as e:
            logger.error(f"Error stopping MCP Memory server process: {e}")
            
    def _call_mcp_memory_server(self, method: str, params: Dict) -> Dict:
        """Call MCP Memory server for graph operations via stdio JSON-RPC"""
        try:
            if not self.mcp_memory_server_path:
                return {"success": False, "error": "MCP Memory server not available"}
            
            # Start MCP process if needed
            if not self._start_mcp_process():
                return {"success": False, "error": "Could not start MCP Memory server process"}
            
            # Prepare JSON-RPC request
            self.mcp_request_id += 1
            mcp_request = {
                "jsonrpc": "2.0",
                "id": self.mcp_request_id,
                "method": "tools/call",
                "params": {
                    "name": method,
                    "arguments": params
                }
            }
            
            try:
                # Send request via stdin
                request_line = json.dumps(mcp_request) + '\n'
                self.mcp_process.stdin.write(request_line)
                self.mcp_process.stdin.flush()
                
                # Read response from stdout
                response_line = self.mcp_process.stdout.readline()
                if not response_line:
                    return {"success": False, "error": "No response from MCP server"}
                
                response = json.loads(response_line.strip())
                
                if "result" in response:
                    logger.info(f"MCP Memory server success: {method}")
                    return {"success": True, "data": response["result"]}
                elif "error" in response:
                    logger.error(f"MCP Memory server error: {response['error']}")
                    return {"success": False, "error": response["error"]}
                else:
                    logger.warning(f"MCP Memory server unexpected response: {response}")
                    return {"success": False, "error": "Unexpected MCP response format"}
                    
            except json.JSONDecodeError as e:
                logger.error(f"MCP Memory server JSON decode error: {e}")
                # Restart process and retry once
                self._stop_mcp_process()
                return {"success": False, "error": f"JSON decode error: {e}"}
            except Exception as e:
                logger.error(f"MCP Memory server communication error: {e}")
                return {"success": False, "error": f"Communication error: {e}"}
            
        except Exception as e:
            logger.error(f"Error calling MCP Memory server: {e}")
            return {"success": False, "error": str(e)}
    
    def _create_entities(self, entities: List[Dict], user_id: str = "default", **kwargs) -> MCPToolResult:
        """Create multiple new entities in the knowledge graph"""
        try:
            # Try MCP Memory server first
            if self.mcp_available:
                mcp_result = self._call_mcp_memory_server("create_entities", {"entities": entities})
                if mcp_result.get("success"):
                    return MCPToolResult(
                        success=True,
                        data=mcp_result.get("data", entities)
                    )
                else:
                    logger.warning(f"MCP Memory server failed, falling back to local storage: {mcp_result.get('error')}")
            
            # Fallback to local JSON storage
            graph = self._load_graph(user_id)
            created_entities = []
            
            for entity_data in entities:
                # Validate required fields
                if not all(key in entity_data for key in ["name", "entityType", "observations"]):
                    continue
                
                # Check if entity already exists
                existing = next((e for e in graph["entities"] if e["name"] == entity_data["name"]), None)
                if existing:
                    # Add new observations to existing entity
                    existing["observations"].extend(entity_data["observations"])
                    existing["last_updated"] = datetime.now().isoformat()
                    created_entities.append(existing)
                else:
                    # Create new entity
                    entity = {
                        "type": "entity",
                        "name": entity_data["name"],
                        "entityType": entity_data["entityType"],
                        "observations": entity_data["observations"],
                        "created": datetime.now().isoformat(),
                        "last_updated": datetime.now().isoformat(),
                        "user_id": user_id
                    }
                    graph["entities"].append(entity)
                    created_entities.append(entity)
            
            self._save_graph(graph, user_id)
            
            return MCPToolResult(
                success=True,
                data=created_entities
            )
            
        except Exception as e:
            logger.error(f"Error creating entities: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _create_relations(self, relations: List[Dict], user_id: str = "default", **kwargs) -> MCPToolResult:
        """Create multiple new relations between entities"""
        try:
            # Try MCP Memory server first
            if self.mcp_available:
                mcp_result = self._call_mcp_memory_server("create_relations", {"relations": relations})
                if mcp_result.get("success"):
                    return MCPToolResult(
                        success=True,
                        data=mcp_result.get("data", relations)
                    )
                else:
                    logger.warning(f"MCP Memory server failed, falling back to local storage: {mcp_result.get('error')}")
            
            # Fallback to local JSON storage
            graph = self._load_graph(user_id)
            created_relations = []
            
            for relation_data in relations:
                # Validate required fields
                if not all(key in relation_data for key in ["from", "to", "relationType"]):
                    continue
                
                # Check if relation already exists
                existing = next((r for r in graph["relations"] 
                               if r["from"] == relation_data["from"] 
                               and r["to"] == relation_data["to"]
                               and r["relationType"] == relation_data["relationType"]), None)
                
                if not existing:
                    relation = {
                        "from": relation_data["from"],
                        "to": relation_data["to"], 
                        "relationType": relation_data["relationType"],
                        "created": datetime.now().isoformat(),
                        "user_id": user_id
                    }
                    graph["relations"].append(relation)
                    created_relations.append(relation)
            
            self._save_graph(graph, user_id)
            
            return MCPToolResult(
                success=True,
                data=created_relations
            )
            
        except Exception as e:
            logger.error(f"Error creating relations: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _add_observations(self, observations: List[Dict], user_id: str = "default", **kwargs) -> MCPToolResult:
        """Add new observations to existing entities"""
        try:
            graph = self._load_graph(user_id)
            updated_entities = []
            
            for obs_data in observations:
                if not all(key in obs_data for key in ["entityName", "contents"]):
                    continue
                
                # Find entity
                entity = next((e for e in graph["entities"] if e["name"] == obs_data["entityName"]), None)
                if entity:
                    entity["observations"].extend(obs_data["contents"])
                    entity["last_updated"] = datetime.now().isoformat()
                    updated_entities.append(entity)
            
            self._save_graph(graph, user_id)
            
            return MCPToolResult(
                success=True,
                data=updated_entities
            )
            
        except Exception as e:
            logger.error(f"Error adding observations: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _search_nodes(self, query: str, user_id: str = "default", **kwargs) -> MCPToolResult:
        """Search for nodes based on query"""
        try:
            # Try MCP Memory server first
            if self.mcp_available:
                mcp_result = self._call_mcp_memory_server("search_nodes", {"query": query})
                if mcp_result.get("success"):
                    return MCPToolResult(
                        success=True,
                        data=mcp_result.get("data", {})
                    )
                else:
                    logger.warning(f"MCP Memory server failed, falling back to local storage: {mcp_result.get('error')}")
            
            # Fallback to local JSON storage
            graph = self._load_graph(user_id)
            matching_entities = []
            matching_relations = []
            
            query_lower = query.lower()
            
            # Search in entities
            for entity in graph["entities"]:
                if (query_lower in entity["name"].lower() or 
                    query_lower in entity["entityType"].lower() or
                    any(query_lower in obs.lower() for obs in entity["observations"])):
                    matching_entities.append(entity)
            
            # Search in relations
            for relation in graph["relations"]:
                if (query_lower in relation["from"].lower() or
                    query_lower in relation["to"].lower() or
                    query_lower in relation["relationType"].lower()):
                    matching_relations.append(relation)
            
            return MCPToolResult(
                success=True,
                data={
                    "entities": matching_entities,
                    "relations": matching_relations
                }
            )
            
        except Exception as e:
            logger.error(f"Error searching nodes: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _read_graph(self, user_id: str = "default", **kwargs) -> MCPToolResult:
        """Read the entire knowledge graph"""
        try:
            graph = self._load_graph(user_id)
            
            return MCPToolResult(
                success=True,
                data=graph
            )
            
        except Exception as e:
            logger.error(f"Error reading graph: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _open_nodes(self, names: List[str], user_id: str = "default", **kwargs) -> MCPToolResult:
        """Open specific nodes by their names"""
        try:
            graph = self._load_graph(user_id)
            found_entities = []
            
            for name in names:
                entity = next((e for e in graph["entities"] if e["name"] == name), None)
                if entity:
                    found_entities.append(entity)
            
            return MCPToolResult(
                success=True,
                data=found_entities
            )
            
        except Exception as e:
            logger.error(f"Error opening nodes: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _delete_entities(self, entityNames: List[str], user_id: str = "default", **kwargs) -> MCPToolResult:
        """Delete multiple entities and their associated relations"""
        try:
            graph = self._load_graph(user_id)
            
            # Remove entities
            original_count = len(graph["entities"])
            graph["entities"] = [e for e in graph["entities"] if e["name"] not in entityNames]
            deleted_entities = original_count - len(graph["entities"])
            
            # Remove related relations
            original_rel_count = len(graph["relations"])
            graph["relations"] = [r for r in graph["relations"] 
                                if r["from"] not in entityNames and r["to"] not in entityNames]
            deleted_relations = original_rel_count - len(graph["relations"])
            
            self._save_graph(graph, user_id)
            
            return MCPToolResult(
                success=True,
                data={
                    "deleted_entities": deleted_entities,
                    "deleted_relations": deleted_relations
                }
            )
            
        except Exception as e:
            logger.error(f"Error deleting entities: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _delete_relations(self, relations: List[Dict], user_id: str = "default", **kwargs) -> MCPToolResult:
        """Delete multiple relations from the knowledge graph"""
        try:
            graph = self._load_graph(user_id)
            original_count = len(graph["relations"])
            
            for rel_to_delete in relations:
                graph["relations"] = [r for r in graph["relations"]
                                    if not (r["from"] == rel_to_delete["from"] and
                                           r["to"] == rel_to_delete["to"] and
                                           r["relationType"] == rel_to_delete["relationType"])]
            
            deleted_count = original_count - len(graph["relations"])
            self._save_graph(graph, user_id)
            
            return MCPToolResult(
                success=True,
                data={"deleted_relations": deleted_count}
            )
            
        except Exception as e:
            logger.error(f"Error deleting relations: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _delete_observations(self, deletions: List[Dict], user_id: str = "default", **kwargs) -> MCPToolResult:
        """Delete specific observations from entities"""
        try:
            graph = self._load_graph(user_id)
            updated_entities = []
            
            for deletion in deletions:
                if not all(key in deletion for key in ["entityName", "observations"]):
                    continue
                
                entity = next((e for e in graph["entities"] if e["name"] == deletion["entityName"]), None)
                if entity:
                    for obs_to_delete in deletion["observations"]:
                        if obs_to_delete in entity["observations"]:
                            entity["observations"].remove(obs_to_delete)
                    entity["last_updated"] = datetime.now().isoformat()
                    updated_entities.append(entity)
            
            self._save_graph(graph, user_id)
            
            return MCPToolResult(
                success=True,
                data=updated_entities
            )
            
        except Exception as e:
            logger.error(f"Error deleting observations: {str(e)}")
            return MCPToolResult(success=False, error=str(e))
    
    def _store_tool_capability(self, tool_name: str, tool_info: Dict, user_id: str = "system") -> MCPToolResult:
        """Store tool capability information in user-isolated graph memory"""
        try:
            # Create tool entity with capabilities
            tool_entity = {
                "name": f"tool_{tool_name}",
                "entityType": "tool",
                "observations": [
                    f"Tool name: {tool_name}",
                    f"Description: {tool_info.get('description', 'No description')}",
                    f"Actions: {', '.join(tool_info.get('actions', {}).keys())}",
                    f"Version: {tool_info.get('version', 'unknown')}",
                    f"Capabilities: {', '.join(tool_info.get('capabilities', []))}",
                    f"Use cases: {tool_info.get('use_cases', 'General purpose')}",
                    f"Priority: {tool_info.get('priority', 'normal')}",
                    f"Conflicts with: {', '.join(tool_info.get('conflicts_with', []))}",
                    f"Stored at: {datetime.now().isoformat()}"
                ]
            }
            
            # Create user-tool relation
            user_relation = {
                "from": f"user_{user_id}",
                "to": f"tool_{tool_name}",
                "relationType": "has_access_to"
            }
            
            # Store in graph memory
            result = self._create_entities([tool_entity], user_id)
            if result.success:
                self._create_relations([user_relation], user_id)
            
            return MCPToolResult(
                success=True,
                data={
                    "tool_name": tool_name,
                    "user_id": user_id,
                    "stored_at": datetime.now().isoformat()
                }
            )
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))
    
    def _get_user_tools(self, user_id: str = "system") -> MCPToolResult:
        """Get all tools available to a specific user"""
        try:
            # Search for tool entities directly instead of through relations
            graph = self._load_graph(user_id)
            
            tools = []
            for entity in graph.get("entities", []):
                if entity.get("entityType") == "tool":
                    tools.append({
                        "name": entity.get("name", "").replace("tool_", ""),
                        "observations": entity.get("observations", [])
                    })
            
            return MCPToolResult(
                success=True,
                data={
                    "user_id": user_id,
                    "tools": tools,
                    "tool_count": len(tools)
                }
            )
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))
    
    def _log_tool_operation(self, tool_name: str, action_name: str, result: Dict, 
                           user_id: str = "system", parameters: Dict = None) -> MCPToolResult:
        """Log tool operation for user-isolated tracking"""
        try:
            # Create operation entity
            operation_id = str(uuid.uuid4())[:8]
            observations = [
                f"Tool: {tool_name}",
                f"Action: {action_name}",
                f"User: {user_id}",
                f"Success: {result.get('success', False)}",
                f"Parameters: {json.dumps(parameters or {})}",
                f"Timestamp: {datetime.now().isoformat()}"
            ]
            
            # Add result data to observations for context-aware retrieval
            if result.get("file_path"):
                observations.append(f"File Path: {result.get('file_path')}")
                logger.info(f"Added file path to observations: {result.get('file_path')}")
            if result.get("local_filename"):
                observations.append(f"Filename: {result.get('local_filename')}")
            if result.get("prompt"):
                observations.append(f"Prompt: {result.get('prompt')}")
            if result.get("provider"):
                observations.append(f"Provider: {result.get('provider')}")
            if result.get("command"):
                observations.append(f"Command: {result.get('command')}")
            if result.get("output"):
                observations.append(f"Output: {result.get('output')[:100]}...")  # First 100 chars
            
            # Debug logging
            logger.debug(f"Tool operation result keys: {list(result.keys())}")
            logger.info(f"Final observations count: {len(observations)}")
            
            operation_entity = {
                "name": f"operation_{operation_id}",
                "entityType": "tool_operation",
                "observations": observations
            }
            
            # Create relations
            relations = [
                {
                    "from": f"user_{user_id}",
                    "to": f"operation_{operation_id}",
                    "relationType": "performed"
                },
                {
                    "from": f"tool_{tool_name}",
                    "to": f"operation_{operation_id}",
                    "relationType": "executed_in"
                }
            ]
            
            # Store in graph memory
            self._create_entities([operation_entity], user_id)
            self._create_relations(relations, user_id)
            
            return MCPToolResult(success=True, data={"operation_id": operation_id})
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))
    
    def _get_latest_operation(self, user_id: str = "system", tool_name: str = None, 
                             action_type: str = None) -> MCPToolResult:
        """Get the latest operation for a user, optionally filtered by tool/action"""
        try:
            # Load user graph
            graph = self._load_graph(user_id)
            
            # Find operation entities
            operations = []
            for entity in graph.get("entities", []):
                if entity.get("entityType") == "tool_operation":
                    # Parse operation details from observations
                    operation_data = {"entity": entity}
                    for obs in entity.get("observations", []):
                        if obs.startswith("Tool: "):
                            operation_data["tool"] = obs.split("Tool: ")[1]
                        elif obs.startswith("Action: "):
                            operation_data["action"] = obs.split("Action: ")[1]
                        elif obs.startswith("Timestamp: "):
                            operation_data["timestamp"] = obs.split("Timestamp: ")[1]
                        elif obs.startswith("Success: "):
                            operation_data["success"] = obs.split("Success: ")[1] == "True"
                    
                    # Apply filters
                    if tool_name and operation_data.get("tool") != tool_name:
                        continue
                    if action_type and action_type not in operation_data.get("action", ""):
                        continue
                    
                    operations.append(operation_data)
            
            # Sort by timestamp (latest first)
            operations.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            if operations:
                return MCPToolResult(success=True, data=operations[0])
            else:
                return MCPToolResult(success=False, error="No matching operations found")
                
        except Exception as e:
            return MCPToolResult(success=False, error=f"Error retrieving latest operation: {str(e)}")
    
    def _get_context_operation(self, context_query: str, user_id: str = "system") -> MCPToolResult:
        """Get operation based on context query like 'son ürettiğin imaj', 'önceki email'"""
        try:
            # Parse context query
            query_lower = context_query.lower()
            
            # Temporal keywords
            if any(word in query_lower for word in ["son", "latest", "last", "en son"]):
                temporal_filter = "latest"
            elif any(word in query_lower for word in ["önceki", "previous", "before"]):
                temporal_filter = "previous"
            elif any(word in query_lower for word in ["ilk", "first", "en başta"]):
                temporal_filter = "first"
            else:
                temporal_filter = "latest"  # default
            
            # Tool/action keywords
            tool_filter = None
            action_filter = None
            
            if any(word in query_lower for word in ["imaj", "görsel", "resim", "image", "visual"]):
                tool_filter = "simple_visual_creator"
                action_filter = "generate"
            elif any(word in query_lower for word in ["email", "mail", "gmail"]):
                tool_filter = "gmail_helper"
            elif any(word in query_lower for word in ["komut", "command", "terminal"]):
                tool_filter = "command_executor"
            
            # Get filtered operations
            operations_result = self._get_latest_operation(user_id, tool_filter, action_filter)
            
            if operations_result.success:
                operation_data = operations_result.data
                
                # Extract useful info for context
                context_info = {
                    "operation_type": f"{operation_data.get('tool')} - {operation_data.get('action')}",
                    "timestamp": operation_data.get("timestamp"),
                    "success": operation_data.get("success"),
                    "entity_name": operation_data.get("entity", {}).get("name"),
                    "query_matched": context_query
                }
                
                # Try to extract file paths, results from observations
                for obs in operation_data.get("entity", {}).get("observations", []):
                    if "saved_path" in obs or "file_path" in obs or ".jpg" in obs or ".png" in obs:
                        context_info["file_info"] = obs
                
                return MCPToolResult(success=True, data=context_info)
            else:
                return operations_result
                
        except Exception as e:
            return MCPToolResult(success=False, error=f"Error processing context query: {str(e)}")
    
    def _generate_tool_prompt(self, user_id: str = "system") -> MCPToolResult:
        """Generate dynamic tool prompt for LLM based on user's available tools"""
        try:
            # Get user's tools
            tools_result = self._get_user_tools(user_id)
            if not tools_result.success:
                return tools_result
            
            tools = tools_result.data.get("tools", [])
            
            # Build dynamic prompt
            tool_lines = []
            for tool in tools:
                tool_name = tool.get("name", "unknown")
                observations = tool.get("observations", [])
                
                # Extract info from observations
                description = "No description"
                actions = "No actions"
                for obs in observations:
                    if obs.startswith("Description:"):
                        description = obs.replace("Description: ", "")
                    elif obs.startswith("Actions:"):
                        actions = obs.replace("Actions: ", "")
                
                tool_lines.append(f"- {tool_name}: {description} ({actions})")
            
            prompt_template = f"""
AVAILABLE TOOLS FOR USER {user_id}:
{chr(10).join(tool_lines)}

ANALYZE THE REQUEST AND CREATE LOGICAL STEPS USING THESE EXACT TOOLS AND ACTIONS.
"""
            
            return MCPToolResult(
                success=True,
                data={
                    "user_id": user_id,
                    "tool_count": len(tools),
                    "prompt_template": prompt_template
                }
            )
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))

    def health_check(self) -> MCPToolResult:
        """Check graph memory health"""
        try:
            storage_type = "MCP Memory Server + JSON Fallback" if self.mcp_available else "JSON Graph Only"
            
            return MCPToolResult(
                success=True,
                data={
                    "status": "healthy",
                    "storage_type": storage_type,
                    "mcp_memory_available": self.mcp_available,
                    "mcp_server_path": self.mcp_memory_server_path,
                    "base_storage_path": self.base_storage_path
                }
            )
        except Exception as e:
            return MCPToolResult(success=False, error=str(e))

def register_tool(registry):
    """Register the Graph Memory tool with the registry"""
    tool = GraphMemoryTool()
    return registry.register_tool(tool)