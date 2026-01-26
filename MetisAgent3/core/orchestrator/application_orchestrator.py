"""
Application Orchestrator - Main System Controller with Workflow Template Management

CLAUDE.md COMPLIANT:
- Axis/RMMS style workflow management system
- Successful workflow template persistence
- Workflow execution tracking and replay
- Component coordination and lifecycle management
- Production-ready error handling and monitoring
"""

import asyncio
import json
import logging
from uuid import uuid4
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path

from ..contracts.base_types import AgentResult, ExecutionContext, ExecutionStatus, Priority
from ..contracts.reasoning_contracts import ReasoningResult, ReasoningStep
from ..managers.reasoning_manager import ReasoningEngine, LLMService
from ..managers.user_manager import UserManager
from ..managers.tool_manager import ToolManager
from ..managers.memory_manager import GraphMemoryService
from ..services.conversation_service import ConversationService
from ..services.conversation_memory_service import ConversationMemoryService
from ..services.settings_service import SettingsService
from ..storage.sqlite_storage import SQLiteUserStorage
from ..classifier import ToolClassifier, ToolClassifierFactory

logger = logging.getLogger(__name__)


class WorkflowStatus(str, Enum):
    """Workflow execution status"""
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class WorkflowTemplateType(str, Enum):
    """Types of workflow templates"""
    MANUAL = "manual"           # Manually created
    AUTO_GENERATED = "auto"     # Generated from successful runs
    IMPORTED = "imported"       # Imported from other systems
    SHARED = "shared"          # Shared between users


@dataclass
class WorkflowStep:
    """Individual workflow step definition"""
    id: str
    name: str
    tool_name: str
    capability: str
    input_data: Dict[str, Any]
    expected_outputs: List[str]
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300
    depends_on: List[str] = None
    condition: Optional[str] = None  # Conditional execution logic
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.depends_on is None:
            self.depends_on = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class WorkflowTemplate:
    """Reusable workflow template - Axis/RMMS style"""
    id: str
    name: str
    description: str
    version: str
    template_type: WorkflowTemplateType
    created_by: str
    steps: List[WorkflowStep]
    success_rate: float = 0.0
    total_executions: int = 0
    successful_executions: int = 0
    average_duration: float = 0.0
    tags: List[str] = None
    input_schema: Dict[str, Any] = None
    output_schema: Dict[str, Any] = None
    created_at: datetime = None
    updated_at: datetime = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.input_schema is None:
            self.input_schema = {}
        if self.output_schema is None:
            self.output_schema = {}
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class WorkflowExecution:
    """Workflow execution instance"""
    id: str
    template_id: str
    user_id: str
    status: WorkflowStatus
    input_data: Dict[str, Any]
    output_data: Dict[str, Any] = None
    current_step: int = 0
    step_results: Dict[str, Any] = None
    error_message: Optional[str] = None
    started_at: datetime = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    execution_context: Dict[str, Any] = None

    def __post_init__(self):
        if self.output_data is None:
            self.output_data = {}
        if self.step_results is None:
            self.step_results = {}
        if self.started_at is None:
            self.started_at = datetime.utcnow()
        if self.execution_context is None:
            self.execution_context = {}


class WorkflowTemplateManager:
    """Manages workflow templates - Axis/RMMS style persistence"""
    
    def __init__(self, storage: SQLiteUserStorage):
        self.storage = storage
        self._init_template_storage()
    
    def _init_template_storage(self):
        """Initialize workflow template storage tables"""
        # This would extend the existing SQLite schema
        # For now, we'll use the EAV model in user_attributes
        logger.info("Workflow template storage initialized")
    
    async def save_template(self, template: WorkflowTemplate) -> bool:
        """Save workflow template to persistent storage"""
        try:
            template_key = f"workflow_template_{template.id}"
            template_data = asdict(template)
            
            # Convert datetime objects to ISO strings for JSON serialization
            if template_data.get('created_at'):
                template_data['created_at'] = template.created_at.isoformat()
            if template_data.get('updated_at'):
                template_data['updated_at'] = template.updated_at.isoformat()
            
            await self.storage.set_user_attribute(
                user_id=template.created_by,
                attribute_name=template_key,
                attribute_value=json.dumps(template_data),
                encrypt=False
            )
            
            logger.info(f"Saved workflow template: {template.name} (ID: {template.id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save workflow template {template.id}: {e}")
            return False
    
    async def load_template(self, template_id: str, user_id: str) -> Optional[WorkflowTemplate]:
        """Load workflow template from storage (user or system)"""
        try:
            template_key = f"workflow_template_{template_id}"
            
            # Try user's templates first
            template_data = await self.storage.get_user_attribute(user_id, template_key)
            
            # If not found in user templates, try system templates
            if not template_data and user_id != "system":
                template_data = await self.storage.get_user_attribute("system", template_key)
            
            if not template_data:
                return None
            
            return self._parse_template_data(template_key, template_data, None)
            
        except Exception as e:
            logger.error(f"Failed to load workflow template {template_id}: {e}")
            return None
    
    async def list_templates(self, user_id: str, template_type: Optional[WorkflowTemplateType] = None) -> List[WorkflowTemplate]:
        """List user's workflow templates including system templates"""
        try:
            templates = []
            
            # Get user's own templates
            user_attributes = await self.storage.get_user_attributes(user_id)
            for key, value in user_attributes.items():
                if key.startswith("workflow_template_"):
                    template = self._parse_template_data(key, value, template_type)
                    if template:
                        templates.append(template)
            
            # Get system templates (available to all users)
            if user_id != "system":
                system_attributes = await self.storage.get_user_attributes("system")
                for key, value in system_attributes.items():
                    if key.startswith("workflow_template_"):
                        template = self._parse_template_data(key, value, template_type)
                        if template:
                            templates.append(template)
            
            # Sort by success rate and total executions
            templates.sort(key=lambda t: (t.success_rate, t.total_executions), reverse=True)
            return templates
            
        except Exception as e:
            logger.error(f"Failed to list templates for user {user_id}: {e}")
            return []
    
    def _parse_template_data(self, key: str, value: Any, template_type: Optional[WorkflowTemplateType]) -> Optional[WorkflowTemplate]:
        """Parse template data from storage"""
        try:
            if isinstance(value, str):
                template_dict = json.loads(value)
            else:
                template_dict = value
            
            # Filter by type if specified
            if template_type and template_dict.get('template_type') != template_type.value:
                return None
            
            # Convert datetime strings back
            if template_dict.get('created_at'):
                template_dict['created_at'] = datetime.fromisoformat(template_dict['created_at'])
            if template_dict.get('updated_at'):
                template_dict['updated_at'] = datetime.fromisoformat(template_dict['updated_at'])
            
            # Convert template_type string to enum
            if 'template_type' in template_dict:
                template_dict['template_type'] = WorkflowTemplateType(template_dict['template_type'])
            
            # Convert steps
            steps = []
            for step_data in template_dict.get('steps', []):
                steps.append(WorkflowStep(**step_data))
            template_dict['steps'] = steps
            
            return WorkflowTemplate(**template_dict)
            
        except Exception as e:
            logger.warning(f"Failed to parse template {key}: {e}")
            return None
    
    async def update_template_stats(self, template_id: str, user_id: str, success: bool, duration: float):
        """Update template statistics after execution"""
        try:
            template = await self.load_template(template_id, user_id)
            if not template:
                return False
            
            template.total_executions += 1
            if success:
                template.successful_executions += 1
            
            template.success_rate = template.successful_executions / template.total_executions
            
            # Update average duration (exponential moving average)
            if template.average_duration == 0:
                template.average_duration = duration
            else:
                alpha = 0.2  # Weight for new value
                template.average_duration = alpha * duration + (1 - alpha) * template.average_duration
            
            template.updated_at = datetime.utcnow()
            
            return await self.save_template(template)
            
        except Exception as e:
            logger.error(f"Failed to update template stats {template_id}: {e}")
            return False


class ApplicationOrchestrator:
    """Main application orchestrator with Axis/RMMS style workflow management"""
    
    def __init__(self,
                 storage: Optional[SQLiteUserStorage] = None,
                 settings_service: Optional[SettingsService] = None,
                 tool_manager: Optional['ToolManager'] = None,
                 application_id: Optional[str] = None):
        """
        Initialize Application Orchestrator.

        Args:
            storage: SQLite storage instance
            settings_service: Settings service instance
            tool_manager: Tool manager instance
            application_id: Application filter - "axis", "rmms", or None for all tools
        """
        # Application filter for multi-app deployment
        self.application_id = application_id

        # Core services
        self.storage = storage or SQLiteUserStorage()
        self.settings_service = settings_service or SettingsService(self.storage)
        
        # Managers
        self.user_manager = UserManager(self.storage)

        # Initialize graph memory service first (needed by tool manager)
        self.graph_memory_service = GraphMemoryService()

        # Tool manager with graph memory for capability sync
        self.tool_manager = tool_manager or ToolManager(graph_memory_service=self.graph_memory_service)

        # Initialize reasoning components with storage injection
        self.llm_service = LLMService(storage=self.storage)
        
        # Initialize ReasoningEngine with shared LLM service (has storage access)
        self.reasoning_manager = ReasoningEngine(self.llm_service, self.graph_memory_service)
        
        self.conversation_service = ConversationService()
        self.conversation_memory_service = ConversationMemoryService()

        # Workflow management
        self.template_manager = WorkflowTemplateManager(self.storage)
        self.active_executions: Dict[str, WorkflowExecution] = {}

        # Workflow history tracking for UI
        self.workflow_history: List[Dict[str, Any]] = []
        self.max_history_size = 50  # Keep last 50 workflows

        # Tool Classifier for 3-stage tool selection (MCP Server Plan)
        self.tool_classifier = ToolClassifierFactory.create_default()

        # System state
        self.is_initialized = False
        self.component_health: Dict[str, bool] = {}

        logger.info(f"Application Orchestrator initialized (application_id: {self.application_id or 'all'})")
    
    async def _load_system_tools(self):
        """Load tools based on type: internal (all users) vs plugin (settings-based)"""
        try:
            # 1. Load INTERNAL tools - auto-load for ALL users
            await self._load_internal_tools()
            
            # 2. Load PLUGIN tools - based on settings
            await self._load_plugin_tools()
                    
        except Exception as e:
            logger.error(f"System tools loading failed: {e}")
    
    async def _load_internal_tools(self):
        """Load internal tools that are available for ALL users"""
        try:
            from ..config.system_tools import get_internal_tools
            internal_tools = get_internal_tools()
            
            logger.info(f"Loading {len(internal_tools)} internal tools...")
            
            for metadata, config in internal_tools:
                try:
                    success = await self.tool_manager.load_tool(metadata, config)
                    if success:
                        logger.info(f"✅ Loaded internal tool: {metadata.name}")
                    else:
                        logger.error(f"❌ Failed to load internal tool: {metadata.name}")
                except Exception as e:
                    logger.error(f"❌ Error loading internal tool {metadata.name}: {e}")
                    
        except Exception as e:
            logger.error(f"Internal tools loading failed: {e}")
    
    async def _load_plugin_tools(self):
        """Load plugin tools based on global/user settings"""
        try:
            from ..config.system_tools import get_plugin_tools
            plugin_tools = get_plugin_tools()
            
            logger.info(f"Checking {len(plugin_tools)} plugin tools for loading...")
            
            for metadata, config in plugin_tools:
                try:
                    # Check if plugin is enabled in global settings
                    enabled = await self._check_plugin_enabled(metadata.name)
                    
                    if enabled:
                        success = await self.tool_manager.load_tool(metadata, config)
                        if success:
                            logger.info(f"✅ Loaded plugin tool: {metadata.name}")
                        else:
                            logger.error(f"❌ Failed to load plugin tool: {metadata.name}")
                    else:
                        logger.info(f"⏭️ Plugin tool {metadata.name} disabled in settings")
                        
                except Exception as e:
                    logger.error(f"❌ Error loading plugin tool {metadata.name}: {e}")
                    
        except Exception as e:
            logger.error(f"Plugin tools loading failed: {e}")
    
    async def _check_plugin_enabled(self, tool_name: str) -> bool:
        """Check if plugin is enabled in settings"""
        try:
            # Check global setting first
            plugin_setting_key = f"plugin_{tool_name}_enabled"
            global_enabled = await self.settings_service.get_user_setting("system", plugin_setting_key)
            
            # Default to True if no setting found (backward compatibility)
            return global_enabled if global_enabled is not None else True
            
        except Exception as e:
            logger.warning(f"Could not check plugin setting for {tool_name}: {e}")
            # Default to enabled for backward compatibility
            return True
    
    async def _discover_and_load_tools(self):
        """Discover and load additional tools from configured paths"""
        try:
            from ..config.system_tools import get_plugin_discovery_paths
            discovery_paths = get_plugin_discovery_paths()
            
            for path in discovery_paths:
                try:
                    discovered_tools = await self.tool_manager.discover_tools(path)
                    logger.info(f"Discovered {len(discovered_tools)} tools in {path}")
                    
                    # Auto-load discovered tools would go here
                    # For now, just log discovery
                    
                except Exception as e:
                    logger.warning(f"Tool discovery failed for {path}: {e}")
                    
        except Exception as e:
            logger.error(f"Tool discovery failed: {e}")
    
    async def _sync_tools_to_memory(self):
        """Sync all loaded tools to graph memory service per blueprint specification"""
        try:
            # Get all loaded tools from tool manager
            tool_list = await self.tool_manager.list_tools()
            logger.info(f"Syncing {len(tool_list)} tools to graph memory...")
            
            for tool_name in tool_list:
                try:
                    # Get tool metadata
                    metadata = self.tool_manager.registry.get_tool_metadata(tool_name)
                    config = self.tool_manager.registry.get_tool_config(tool_name)
                    
                    if metadata and config:
                        # Sync to graph memory for system user
                        success = await self.graph_memory_service.sync_tool_capabilities(
                            metadata=metadata,
                            config=config,
                            user_id="system"
                        )
                        
                        if success:
                            logger.info(f"✅ Synced tool {tool_name} to graph memory")
                        else:
                            logger.warning(f"⚠️ Failed to sync tool {tool_name}")
                            
                except Exception as e:
                    logger.error(f"Failed to sync tool {tool_name}: {e}")
                    
        except Exception as e:
            logger.error(f"Tool sync to memory failed: {e}")

    async def _index_tools_in_classifier(self):
        """Index all loaded tools in the classifier for 3-stage selection"""
        try:
            # Get all tool metadata from registry
            tools_metadata = {}
            for tool_name in self.tool_manager.registry.tools:
                metadata = self.tool_manager.registry.get_tool_metadata(tool_name)
                if metadata:
                    tools_metadata[tool_name] = metadata

            if tools_metadata:
                self.tool_classifier.index_tools(tools_metadata)
                stats = self.tool_classifier.get_statistics()
                logger.info(f"✅ Classifier indexed: {stats['total_tools']} tools, "
                           f"{stats['total_capabilities']} capabilities")
            else:
                logger.warning("⚠️ No tools to index in classifier")

        except Exception as e:
            logger.error(f"Tool classifier indexing failed: {e}")

    async def reindex_classifier(self):
        """Re-index the classifier after new tools are loaded (public method)"""
        logger.info("🔄 Re-indexing classifier with updated tools...")
        await self._index_tools_in_classifier()

    def classify_tools_for_query(self, query: str, include_high_risk: bool = False) -> Dict[str, Any]:
        """
        Classify query and return tool shortlist.

        Args:
            query: User query text
            include_high_risk: Whether to include high-risk tools

        Returns:
            Classification result with shortlisted tools
        """
        try:
            result = self.tool_classifier.classify(query, include_high_risk=include_high_risk)
            return result.to_dict()
        except Exception as e:
            logger.error(f"Tool classification failed: {e}")
            return {
                "query": query,
                "tool_names": [],
                "error": str(e)
            }

    def get_classifier_statistics(self) -> Dict[str, Any]:
        """Get tool classifier statistics"""
        return self.tool_classifier.get_statistics()

    async def initialize(self) -> bool:
        """Initialize all system components"""
        try:
            logger.info("Initializing MetisAgent3 Application Orchestrator...")
            
            # Initialize core components
            components = {
                "storage": self._init_storage(),
                "user_manager": self._init_user_manager(),
                "tool_manager": self._init_tool_manager(),
                "reasoning_manager": self._init_reasoning_manager(),
                "conversation_service": self._init_conversation_service()
            }
            
            # Initialize components concurrently
            results = await asyncio.gather(*components.values(), return_exceptions=True)
            
            for component_name, result in zip(components.keys(), results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to initialize {component_name}: {result}")
                    self.component_health[component_name] = False
                else:
                    self.component_health[component_name] = result
            
            # Check overall health
            healthy_components = sum(self.component_health.values())
            total_components = len(self.component_health)
            
            self.is_initialized = healthy_components >= (total_components * 0.8)  # 80% threshold
            
            if self.is_initialized:
                logger.info(f"✅ System initialized successfully ({healthy_components}/{total_components} components healthy)")
                await self._load_default_templates()
            else:
                logger.error(f"❌ System initialization failed ({healthy_components}/{total_components} components healthy)")
            
            return self.is_initialized
            
        except Exception as e:
            logger.error(f"System initialization failed: {e}")
            self.is_initialized = False
            return False
    
    async def _init_storage(self) -> bool:
        """Initialize storage layer"""
        try:
            # Storage is already initialized in __init__
            return True
        except Exception as e:
            logger.error(f"Storage initialization failed: {e}")
            return False
    
    async def _init_user_manager(self) -> bool:
        """Initialize user management"""
        try:
            # User manager is already initialized
            return True
        except Exception as e:
            logger.error(f"User manager initialization failed: {e}")
            return False
    
    async def _init_tool_manager(self) -> bool:
        """Initialize tool management with blueprint-compliant auto-loading"""
        try:
            logger.info("🔧 Starting tool manager initialization...")
            
            # Auto-load system tools per blueprint specification
            logger.info("📦 Loading system tools...")
            await self._load_system_tools()
            
            # Discovery additional tools from configured paths
            logger.info("🔍 Discovering additional tools...")
            await self._discover_and_load_tools()
            
            # Sync all loaded tools to graph memory
            logger.info("💾 Syncing tools to graph memory...")
            await self._sync_tools_to_memory()

            # Index tools in classifier for 3-stage selection
            logger.info("🔍 Indexing tools in classifier...")
            await self._index_tools_in_classifier()

            # Log final tool count
            tool_count = len(await self.tool_manager.list_tools())
            logger.info(f"✅ Tool manager initialized with {tool_count} tools")

            return True
        except Exception as e:
            logger.error(f"❌ Tool manager initialization failed: {e}")
            return False
    
    async def _init_reasoning_manager(self) -> bool:
        """Initialize reasoning engine"""
        try:
            # Reasoning manager is already initialized
            return True
        except Exception as e:
            logger.error(f"Reasoning manager initialization failed: {e}")
            return False
    
    async def _init_conversation_service(self) -> bool:
        """Initialize conversation service"""
        try:
            # Conversation service is already initialized
            return True
        except Exception as e:
            logger.error(f"Conversation service initialization failed: {e}")
            return False
    
    async def process_user_request(self, 
                                   user_request: str, 
                                   context: ExecutionContext,
                                   llm_provider: str = None,
                                   llm_model: str = "claude-3-5-sonnet-20241022",
                                   system_prompt: Optional[str] = None,
                                   workflow_callback: Optional[callable] = None) -> AgentResult:
        """
        Process user request through intelligent reasoning and tool orchestration system
        
        CLAUDE.md COMPLIANT:
        - Uses ReasoningEngine for intelligent tool selection
        - LLM decides which tools to use (no keyword-based detection)
        - Sequential Thinking pattern implementation
        """
        try:
            logger.info(f"Processing user request: {user_request[:100]}...")
            
            # Create workflow tracking entry
            workflow_id = str(uuid4())
            workflow_start = datetime.now()
            workflow_entry = {
                "workflow_id": workflow_id,
                "user_request": user_request,
                "user_id": context.user_id,
                "status": "running",
                "start_time": workflow_start.isoformat(),
                "end_time": None,
                "duration_ms": None,
                "llm_provider": llm_provider,
                "llm_model": llm_model,
                "steps": [],
                "final_result": None,
                "error": None
            }
            
            # Add to history immediately as "running" so frontend can see it
            self._add_to_workflow_history(workflow_entry)
            
            # Send workflow started event via callback
            if workflow_callback:
                workflow_callback('workflow_started', {
                    'workflow': {
                        'workflow_id': workflow_id,
                        'title': user_request,
                        'description': user_request,
                        'status': 'running',
                        'progress_percentage': 0,
                        'completed_steps': 0,
                        'total_steps': 0,
                        'steps': [],
                        'created_at': workflow_start.isoformat(),
                        'updated_at': workflow_start.isoformat()
                    }
                })
            
            # Ensure reasoning manager is available
            if not hasattr(self, 'reasoning_manager') or not self.reasoning_manager:
                logger.warning("ReasoningEngine not available, falling back to direct LLM")
                return await self._fallback_llm_processing(user_request, context, llm_provider, llm_model, system_prompt)
            
            # Send initial progress update (5%)
            if workflow_callback:
                workflow_callback('workflow_update', {
                    'workflow': {
                        'workflow_id': workflow_id,
                        'title': user_request,
                        'description': user_request, 
                        'progress_percentage': 5,
                        'completed_steps': 0,
                        'total_steps': 0,
                        'status': 'analyzing',
                        'steps': [],
                        'created_at': workflow_start.isoformat(),
                        'updated_at': datetime.now().isoformat()
                    }
                })

            # ============================================================
            # UNIFIED PLANNING - Single LLM call for everything
            # ============================================================
            logger.info("🎯 Starting UNIFIED PLANNING (single LLM call)...")

            try:
                # Get user tools from graph memory
                user_tools = await self.graph_memory_service.get_user_tools(context.user_id)

                # Per-request application_id filtering
                app_id = getattr(context, 'application_id', None)
                if app_id:
                    user_tools = [
                        t for t in user_tools
                        if t.get("application_id") is None or t.get("application_id") == app_id
                    ]
                    logger.info(f"📦 {len(user_tools)} tools after application filter (app: {app_id})")
                else:
                    logger.info(f"📦 Retrieved {len(user_tools)} tools for user {context.user_id}")

                # Get lightweight conversation memory context (replaces full history)
                memory_context = await self.conversation_memory_service.get_context_for_llm(
                    context.conversation_id or "default",
                    context.user_id
                )
                if memory_context:
                    logger.info(f"📝 Using conversation memory context ({len(memory_context)} chars)")

                # Single LLM call for classification + workflow generation
                plan_result = await self.reasoning_manager.llm.unified_plan_request(
                    user_request=user_request,
                    user_tools=user_tools,
                    context=context,
                    provider=llm_provider,
                    conversation_memory_context=memory_context
                )

                mode = plan_result.get("mode", "CHAT")

                # Handle CHAT mode (direct answer - no tools needed)
                if mode == "CHAT":
                    logger.info(f"💬 CHAT MODE: {plan_result.get('reasoning', 'Direct response')}")

                    duration = plan_result.get("duration_ms", 0)
                    response_text = plan_result.get("response", "")

                    # If no response in plan_result, generate one
                    if not response_text:
                        chat_response = await self._fallback_llm_processing(
                            user_request, context, llm_provider, llm_model, system_prompt
                        )
                        if chat_response.success:
                            response_text = chat_response.data.get("response", "")

                    if workflow_callback:
                        workflow_callback('workflow_completed', {
                            'workflow': {
                                'workflow_id': workflow_id,
                                'status': 'completed',
                                'mode': 'CHAT',
                                'duration_ms': duration,
                                'steps_completed': 0,
                                'total_steps': 0
                            }
                        })

                    # Update conversation memory with this exchange
                    await self._update_conversation_memory(
                        context, user_request, response_text, None, ["chat"]
                    )

                    return AgentResult(
                        success=True,
                        data={
                            "type": "chat_response",
                            "response": response_text,
                            "mode": "CHAT",
                            "duration_ms": duration,
                            "workflow_id": workflow_id
                        },
                        metadata={"mode": "CHAT", "unified_planning": True}
                    )

                # Handle TOOL mode - execute workflow
                workflow_steps = plan_result.get("workflow", [])

                if not workflow_steps:
                    logger.warning("TOOL mode but no workflow steps, falling back to LLM")
                    return await self._fallback_llm_processing(
                        user_request, context, llm_provider, llm_model, system_prompt
                    )

                logger.info(f"🛠️ TOOL MODE: {len(workflow_steps)} steps to execute")

                # Convert workflow dict to ReasoningStep objects
                reasoning_steps = []
                for step_data in workflow_steps:
                    step = ReasoningStep(
                        step_id=step_data.get("step_id", f"step_{len(reasoning_steps)+1}"),
                        name=step_data.get("name", "Unnamed Step"),
                        description=step_data.get("description", ""),
                        tool_name=step_data.get("tool_name", ""),
                        capability=step_data.get("capability", ""),
                        input_parameters=step_data.get("input_parameters", {}),
                        reasoning=step_data.get("reasoning", "LLM determined this step"),
                        confidence=step_data.get("confidence", 0.8)
                    )
                    reasoning_steps.append(step)

                # Create reasoning result for workflow execution
                reasoning_result = ReasoningResult(
                    success=True,
                    steps=reasoning_steps,
                    confidence=plan_result.get("confidence", 0.8),
                    reasoning_time=plan_result.get("duration_ms", 0) / 1000,
                    metadata={"mode": "UNIFIED", "reasoning": plan_result.get("reasoning", "")}
                )

                # Send workflow ready progress update
                if workflow_callback:
                    workflow_callback('workflow_update', {
                        'workflow': {
                            'workflow_id': workflow_id,
                            'title': user_request,
                            'description': user_request,
                            'progress_percentage': 30,
                            'completed_steps': 0,
                            'total_steps': len(reasoning_steps),
                            'status': 'ready_to_execute',
                            'steps': [],
                            'created_at': workflow_start.isoformat(),
                            'updated_at': datetime.now().isoformat()
                        }
                    })

            except Exception as e:
                logger.error(f"Unified planning failed: {e}, falling back to LLM")
                return await self._fallback_llm_processing(
                    user_request, context, llm_provider, llm_model, system_prompt
                )

            # ============================================================
            # Execute Workflow Steps (unchanged from original)
            # ============================================================
            logger.info(f"🛠️ Executing {len(reasoning_result.steps)} workflow steps...")
            
            # Send workflow update with steps
            if workflow_callback:
                workflow_steps = []
                for i, step in enumerate(reasoning_result.steps):
                    workflow_steps.append({
                        'id': step.step_id,
                        'title': step.name,
                        'description': step.description,
                        'status': 'pending',
                        'tool_name': step.tool_name,
                        'capability': step.capability
                    })
                
                workflow_callback('workflow_update', {
                    'workflow': {
                        'workflow_id': workflow_id,
                        'title': user_request,
                        'description': user_request,
                        'status': 'running',
                        'progress_percentage': 40,
                        'completed_steps': 0,
                        'total_steps': len(reasoning_result.steps),
                        'steps': workflow_steps,
                        'created_at': workflow_start.isoformat(),
                        'updated_at': datetime.now().isoformat()
                    }
                })
            
            # Execute workflow steps sequentially
            step_results = {}
            final_output = None
            
            for step_index, step in enumerate(reasoning_result.steps):
                logger.info(f"▶️ Executing Step {step_index + 1}: {step.name} (Tool: {step.tool_name})")
                
                # Track step start
                step_start = datetime.now()
                step_entry = {
                    "step_id": step.step_id,
                    "step_number": step_index + 1,
                    "name": step.name,
                    "description": step.description,
                    "tool_name": step.tool_name,
                    "capability": step.capability,
                    "input_parameters": step.input_parameters,
                    "status": "running",
                    "start_time": step_start.isoformat(),
                    "end_time": None,
                    "duration_ms": None,
                    "result": None,
                    "error": None
                }
                
                try:
                    # Send step started event
                    if workflow_callback:
                        workflow_callback('workflow_step_update', {
                            'workflow_id': workflow_id,
                            'step': {
                                'id': step.step_id,
                                'title': step.name,
                                'description': step.description,
                                'status': 'running',
                                'tool_name': step.tool_name,
                                'capability': step.capability,
                                'start_time': step_start.isoformat()
                            },
                            'timestamp': step_start.isoformat()
                        })
                    
                    # Get tool instance or handle manual steps
                    if step.tool_name.lower() in ['none', 'manual', 'analysis']:
                        # Handle manual analysis steps
                        step_entry["status"] = "completed"
                        step_entry["result"] = f"Manual analysis: {step.description}"
                        step_entry["end_time"] = datetime.now().isoformat()
                        step_entry["duration_ms"] = (datetime.now() - step_start).total_seconds() * 1000
                        workflow_entry["steps"].append(step_entry)
                        
                        logger.info(f"✅ Manual step completed: {step.name}")
                        
                        # Send step completed event
                        if workflow_callback:
                            completed_steps = step_index + 1
                            total_steps = len(reasoning_result.steps)
                            # Step execution progress: 40% to 100% (60% range)
                            step_progress = (completed_steps / total_steps) * 60
                            progress = 40 + step_progress
                            
                            workflow_callback('workflow_step_update', {
                                'workflow_id': workflow_id,
                                'step': {
                                    'id': step.step_id,
                                    'title': step.name,
                                    'description': step.description,
                                    'status': 'completed',
                                    'tool_name': 'manual_analysis',
                                    'capability': step.capability,
                                    'result': step.description,
                                    'end_time': datetime.now().isoformat()
                                },
                                'timestamp': datetime.now().isoformat()
                            })
                        
                        continue  # Skip to next step
                    
                    tool = await self.tool_manager.get_tool(step.tool_name)
                    if not tool:
                        step_entry["status"] = "failed"
                        step_entry["error"] = f"Tool '{step.tool_name}' not found"
                        step_entry["end_time"] = datetime.now().isoformat()
                        step_entry["duration_ms"] = (datetime.now() - step_start).total_seconds() * 1000
                        workflow_entry["steps"].append(step_entry)
                        logger.error(f"❌ Tool '{step.tool_name}' not found")
                        
                        # Send step failed event
                        if workflow_callback:
                            workflow_callback('workflow_step_update', {
                                'workflow_id': workflow_id,
                                'step': {
                                    'id': step.step_id,
                                    'title': step.name,
                                    'status': 'failed',
                                    'error': f"Tool '{step.tool_name}' not found"
                                },
                                'timestamp': datetime.now().isoformat()
                            })
                        continue
                    
                    # Normalize step input for tool compatibility
                    normalized_input = self._normalize_step_input(step, step.input_parameters, llm_provider, step_results)
                    
                    # Execute tool capability with SEQUENTIAL REASONED EXECUTION
                    tool_result = await self._execute_step_with_reasoning_inline(
                        step=step,
                        step_input=normalized_input,
                        tool=tool,
                        execution_context=context,
                        workflow_context={"step_results": step_results, "workflow_id": workflow_id},
                        llm_provider=llm_provider,
                        llm_model=llm_model
                    )
                    step_end = datetime.now()
                    step_entry["end_time"] = step_end.isoformat()
                    step_entry["duration_ms"] = (step_end - step_start).total_seconds() * 1000
                    
                    if tool_result.success:
                        step_results[step.step_id] = tool_result.data
                        final_output = tool_result.data
                        step_entry["status"] = "completed"
                        step_entry["result"] = tool_result.data
                        workflow_entry["steps"].append(step_entry)
                        logger.info(f"✅ Step {step_index + 1} completed successfully")
                        
                        # Send step completed event
                        if workflow_callback:
                            completed_steps = step_index + 1
                            total_steps = len(reasoning_result.steps)
                            # Step execution progress: 40% to 100% (60% range)
                            step_progress = (completed_steps / total_steps) * 60
                            progress = 40 + step_progress
                            
                            workflow_callback('workflow_step_update', {
                                'workflow_id': workflow_id,
                                'step': {
                                    'id': step.step_id,
                                    'title': step.name,
                                    'description': step.description,
                                    'status': 'completed',
                                    'tool_name': step.tool_name,
                                    'capability': step.capability,
                                    'result': tool_result.data
                                },
                                'timestamp': step_end.isoformat()
                            })
                            
                            # Send workflow progress update
                            workflow_callback('workflow_update', {
                                'workflow': {
                                    'workflow_id': workflow_id,
                                    'title': user_request,
                                    'description': user_request, 
                                    'progress_percentage': progress,
                                    'completed_steps': completed_steps,
                                    'total_steps': total_steps,
                                    'status': 'running',
                                    'steps': workflow_steps,
                                    'created_at': workflow_start.isoformat(),
                                    'updated_at': datetime.now().isoformat()
                                }
                            })
                    else:
                        step_results[step.step_id] = {"error": tool_result.error}
                        step_entry["status"] = "failed"
                        step_entry["error"] = tool_result.error
                        workflow_entry["steps"].append(step_entry)
                        logger.error(f"❌ Step {step_index + 1} failed: {tool_result.error}")
                        
                        # Send step failed event
                        if workflow_callback:
                            workflow_callback('workflow_step_update', {
                                'workflow_id': workflow_id,
                                'step': {
                                    'id': step.step_id,
                                    'title': step.name,
                                    'status': 'failed',
                                    'error': tool_result.error
                                },
                                'timestamp': step_end.isoformat()
                            })
                
                except Exception as step_error:
                    step_entry["status"] = "failed"
                    step_entry["error"] = str(step_error)
                    step_entry["end_time"] = datetime.now().isoformat()
                    step_entry["duration_ms"] = (datetime.now() - step_start).total_seconds() * 1000
                    workflow_entry["steps"].append(step_entry)
                    logger.error(f"❌ Step {step_index + 1} execution error: {step_error}")
                    step_results[step.step_id] = {"error": str(step_error)}
            
            # Step 3: Generate Final Response with LLM Formatting
            # Always use LLM to generate user-friendly response from tool results
            if final_output and isinstance(final_output, dict):
                # Check if it's already user-friendly text
                if "output" in final_output and isinstance(final_output["output"], str) and len(final_output) == 1:
                    response_text = final_output["output"]
                else:
                    # IMPORTANT: Truncate final_output to prevent context_length_exceeded
                    # Tool outputs (like RMMS SCADA) can be 300K+ characters
                    truncated_output = self._truncate_step_results_for_summary({"result": final_output}, max_total_chars=8000)

                    # Use LLM to format raw tool output into user-friendly response
                    format_prompt = f"""User requested: {user_request}

I executed these steps and got results:
{truncated_output}

Please provide a clear, concise, user-friendly response that:
1. Answers the user's question directly
2. Presents the key information in an easily readable format
3. Hides technical details like return codes, working directory, etc.
4. Focuses on what the user actually wanted to know
5. IMPORTANT: Respond in the SAME LANGUAGE as the user's request above

Be natural and conversational."""

                    response_text = await self.llm_service.generate_text(
                        prompt=format_prompt,
                        max_tokens=500,
                        context=context,
                        provider=llm_provider,
                        model=llm_model
                    )
            else:
                # Fallback: Generate LLM summary of what was done
                summary_prompt = f"""User requested: {user_request}

I executed these steps:
{chr(10).join([f"- {step.name}: {step.description}" for step in reasoning_result.steps])}

Results: {self._truncate_step_results_for_summary(step_results)}

Please provide a concise, user-friendly response summarizing what was done and the results.
IMPORTANT: Respond in the SAME LANGUAGE as the user's request above."""

                response_text = await self.llm_service.generate_text(
                    prompt=summary_prompt,
                    max_tokens=1000,
                    context=context,
                    provider=llm_provider,
                    model=llm_model
                )
            
            # Complete workflow tracking
            workflow_end = datetime.now()
            workflow_entry["status"] = "completed"
            workflow_entry["end_time"] = workflow_end.isoformat()
            workflow_entry["duration_ms"] = (workflow_end - workflow_start).total_seconds() * 1000
            workflow_entry["final_result"] = response_text
            
            # Add to history and maintain size limit
            self._add_to_workflow_history(workflow_entry)
            
            # Send workflow completed event
            if workflow_callback:
                workflow_callback('workflow_completed', {
                    'workflow_id': workflow_id,
                    'status': 'completed',
                    'final_result': response_text,
                    'duration_ms': (workflow_end - workflow_start).total_seconds() * 1000,
                    'timestamp': workflow_end.isoformat()
                })

            # Update conversation memory with tool execution results
            # Extract entities from step_results for memory
            extracted_entities = await self.conversation_memory_service.extract_entities_from_response(
                response_text, step_results
            )
            tool_names = [step.tool_name for step in reasoning_result.steps]
            await self._update_conversation_memory(
                context, user_request, response_text, extracted_entities, tool_names
            )

            return AgentResult(
                success=True,
                data={
                    "response": response_text,
                    "conversation_id": context.conversation_id,
                    "provider": llm_provider,
                    "model": llm_model,
                    "workflow_steps": len(reasoning_result.steps),
                    "step_results": step_results
                },
                metadata={
                    "processing_method": "intelligent_orchestration",
                    "user_id": context.user_id,
                    "timestamp": datetime.now().isoformat(),
                    "reasoning_trace_id": reasoning_result.reasoning_trace.trace_id if reasoning_result.reasoning_trace else None
                }
            )

        except Exception as e:
            logger.error(f"Intelligent orchestration failed: {e}")
            logger.info("🔄 Falling back to direct LLM processing...")
            return await self._fallback_llm_processing(user_request, context, llm_provider, llm_model, system_prompt)
    
    async def _fallback_llm_processing(self, 
                                     user_request: str, 
                                     context: ExecutionContext,
                                     llm_provider: str,
                                     llm_model: str,
                                     system_prompt: Optional[str] = None) -> AgentResult:
        """Fallback to direct LLM processing when intelligent orchestration fails"""
        try:
            # Ensure LLM service is available
            if not hasattr(self, 'llm_service') or not self.llm_service:
                self.llm_service = LLMService(storage=self.storage)
            
            # Prepare messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_request})
            
            # Generate response using LLM with provider/model parameters
            user_content = messages[-1]["content"] if messages else user_request
            response_text = await self.llm_service.generate_text(
                prompt=user_content,
                max_tokens=2000,
                context=context,
                provider=llm_provider,
                model=llm_model
            )
            
            return AgentResult(
                success=True,
                data={
                    "response": response_text,
                    "conversation_id": context.conversation_id,
                    "provider": llm_provider,
                    "model": llm_model,
                    "message_count": len(messages)
                },
                metadata={
                    "processing_method": "fallback_llm",
                    "user_id": context.user_id,
                    "timestamp": datetime.now().isoformat()
                }
            )
                
        except Exception as e:
            logger.error(f"Fallback LLM processing failed: {e}")
            return AgentResult(
                success=False,
                error=f"All processing methods failed: {str(e)}",
                metadata={"user_request": user_request[:100]}
            )

    async def _update_conversation_memory(
        self,
        context: ExecutionContext,
        user_request: str,
        assistant_response: str,
        extracted_entities: Optional[Dict[str, Any]] = None,
        topics: Optional[List[str]] = None
    ):
        """Update conversation memory after an exchange"""
        try:
            conversation_id = context.conversation_id or "default"
            user_id = context.user_id

            # Don't use LLM for summary to avoid recursion and extra cost
            # Just do simple memory update
            await self.conversation_memory_service.update_memory(
                conversation_id=conversation_id,
                user_id=user_id,
                user_message=user_request,
                assistant_response=assistant_response,
                extracted_entities=extracted_entities,
                topics=topics,
                llm_service=None  # Skip LLM summarization for now - use simple update
            )

        except Exception as e:
            # Don't fail the main request if memory update fails
            logger.warning(f"Failed to update conversation memory: {e}")

    async def _load_default_templates(self):
        """Load default workflow templates"""
        try:
            # Create some default workflow templates
            default_templates = [
                self._create_llm_chat_template(),
                self._create_email_analysis_template(),
                self._create_visual_generation_template()
            ]
            
            for template in default_templates:
                # Save as system template
                await self.template_manager.save_template(template)
            
            logger.info(f"Loaded {len(default_templates)} default workflow templates")
            
        except Exception as e:
            logger.error(f"Failed to load default templates: {e}")
    
    def _create_llm_chat_template(self) -> WorkflowTemplate:
        """Create default LLM chat workflow template"""
        steps = [
            WorkflowStep(
                id="step_1",
                name="LLM Chat Response",
                tool_name="llm_tool",
                capability="generate_response",
                input_data={
                    "messages": "{{user_messages}}",
                    "provider": "{{provider|anthropic}}",
                    "model": "{{model|claude-3-5-sonnet-20241022}}",
                    "max_tokens": "{{max_tokens|2000}}"
                },
                expected_outputs=["response", "conversation_id"],
                metadata={"category": "llm", "priority": "high"}
            )
        ]
        
        return WorkflowTemplate(
            id="default_llm_chat",
            name="LLM Chat Workflow",
            description="Standard LLM chat interaction workflow",
            version="1.0.0",
            template_type=WorkflowTemplateType.MANUAL,
            created_by="system",
            steps=steps,
            tags=["llm", "chat", "default"],
            input_schema={
                "user_messages": {"type": "array", "required": True},
                "provider": {"type": "string", "default": "anthropic"},
                "model": {"type": "string", "default": "claude-3-5-sonnet-20241022"},
                "max_tokens": {"type": "integer", "default": 2000}
            },
            output_schema={
                "response": {"type": "string"},
                "conversation_id": {"type": "string"}
            }
        )
    
    def _create_email_analysis_template(self) -> WorkflowTemplate:
        """Create email analysis workflow template (for future Gmail tool)"""
        steps = [
            WorkflowStep(
                id="step_1",
                name="Fetch Emails",
                tool_name="gmail_tool",
                capability="list_emails",
                input_data={"limit": "{{limit|10}}", "query": "{{query}}"},
                expected_outputs=["emails"]
            ),
            WorkflowStep(
                id="step_2",
                name="Analyze Email Content",
                tool_name="llm_tool",
                capability="generate_response",
                input_data={
                    "messages": [{"role": "user", "content": "Email analizi: {{step_1.emails}}"}],
                    "provider": "anthropic"
                },
                expected_outputs=["analysis"],
                depends_on=["step_1"]
            )
        ]
        
        return WorkflowTemplate(
            id="email_analysis",
            name="Email Analysis Workflow",
            description="Fetch and analyze email content",
            version="1.0.0",
            template_type=WorkflowTemplateType.MANUAL,
            created_by="system",
            steps=steps,
            tags=["email", "analysis", "gmail"],
            input_schema={
                "limit": {"type": "integer", "default": 10},
                "query": {"type": "string", "required": False}
            }
        )
    
    def _create_visual_generation_template(self) -> WorkflowTemplate:
        """Create visual generation workflow template (for future Visual Creator tool)"""
        steps = [
            WorkflowStep(
                id="step_1",
                name="Generate Image",
                tool_name="visual_creator_tool",
                capability="generate_image",
                input_data={
                    "prompt": "{{image_prompt}}",
                    "provider": "{{provider|dalle}}",
                    "size": "{{size|1024x1024}}"
                },
                expected_outputs=["image_url", "image_path"]
            ),
            WorkflowStep(
                id="step_2",
                name="Create Description",
                tool_name="llm_tool",
                capability="generate_response",
                input_data={
                    "messages": [{"role": "user", "content": "Bu görseli açıkla: {{step_1.image_url}}"}]
                },
                expected_outputs=["description"],
                depends_on=["step_1"]
            )
        ]
        
        return WorkflowTemplate(
            id="visual_generation",
            name="Visual Generation Workflow",
            description="Generate image and create description",
            version="1.0.0",
            template_type=WorkflowTemplateType.MANUAL,
            created_by="system",
            steps=steps,
            tags=["visual", "image", "generation"],
            input_schema={
                "image_prompt": {"type": "string", "required": True},
                "provider": {"type": "string", "default": "dalle"},
                "size": {"type": "string", "default": "1024x1024"}
            }
        )
    
    async def execute_workflow(self, 
                             template_id: str,
                             user_id: str,
                             input_data: Dict[str, Any],
                             execution_context: Optional[ExecutionContext] = None) -> AgentResult[WorkflowExecution]:
        """Execute a workflow from template - Axis/RMMS style execution"""
        execution = None
        
        try:
            # Load workflow template
            template = await self.template_manager.load_template(template_id, user_id)
            if not template:
                return AgentResult(success=False, error=f"Workflow template {template_id} not found")
            
            # Create execution instance
            execution = WorkflowExecution(
                id=str(uuid.uuid4()),
                template_id=template_id,
                user_id=user_id,
                status=WorkflowStatus.RUNNING,
                input_data=input_data,
                execution_context=execution_context.__dict__ if execution_context else {}
            )
            
            # Register active execution
            self.active_executions[execution.id] = execution
            
            logger.info(f"Starting workflow execution: {template.name} (ID: {execution.id})")
            
            try:
                # Execute workflow steps
                await self._execute_workflow_steps(template, execution, execution_context)
                
                # Mark as completed
                execution.status = WorkflowStatus.COMPLETED
                execution.completed_at = datetime.utcnow()
                execution.duration_seconds = (execution.completed_at - execution.started_at).total_seconds()
                
                # Update template statistics
                await self.template_manager.update_template_stats(
                    template_id, user_id, success=True, duration=execution.duration_seconds
                )
                
                logger.info(f"✅ Workflow execution completed: {execution.id} ({execution.duration_seconds:.2f}s)")
                
                # Auto-save successful workflow as template if it's not already a template
                if template.template_type == WorkflowTemplateType.MANUAL:
                    await self._auto_save_successful_workflow(template, execution, user_id)
                
                return AgentResult(success=True, data=execution)
                
            except Exception as step_error:
                execution.status = WorkflowStatus.FAILED
                execution.error_message = str(step_error)
                execution.completed_at = datetime.utcnow()
                execution.duration_seconds = (execution.completed_at - execution.started_at).total_seconds()
                
                # Update template statistics
                await self.template_manager.update_template_stats(
                    template_id, user_id, success=False, duration=execution.duration_seconds
                )
                
                logger.error(f"❌ Workflow execution failed: {execution.id} - {step_error}")
                return AgentResult(success=False, error=str(step_error), data=execution)
                
        except Exception as e:
            logger.error(f"Workflow execution setup failed: {e}")
            return AgentResult(success=False, error=str(e))
        
        finally:
            # Clean up active execution
            if execution and execution.id in self.active_executions:
                del self.active_executions[execution.id]
    
    async def _execute_workflow_steps(self, 
                                    template: WorkflowTemplate, 
                                    execution: WorkflowExecution,
                                    execution_context: Optional[ExecutionContext]):
        """Execute individual workflow steps with dependency management"""
        completed_steps = set()
        
        for step_index, step in enumerate(template.steps):
            # Check dependencies
            if step.depends_on:
                missing_deps = set(step.depends_on) - completed_steps
                if missing_deps:
                    raise ValueError(f"Step {step.name} has unmet dependencies: {missing_deps}")
            
            # Execute step
            execution.current_step = step_index
            logger.info(f"Executing step {step_index + 1}/{len(template.steps)}: {step.name}")
            
            # Prepare step input data with variable substitution
            step_input = self._substitute_variables(step.input_data, execution)
            
            # Get tool and execute capability
            tool = await self.tool_manager.get_tool(step.tool_name)
            if not tool:
                raise ValueError(f"Tool {step.tool_name} not found")
            
            # Execute with SEQUENTIAL REASONED EXECUTION (CRITICAL ENHANCEMENT)
            step_result = await self._execute_step_with_reasoning(
                step=step,
                step_input=step_input,
                tool=tool,
                execution_context=execution_context,
                execution=execution
            )
            
            # Store step result and handle failures
            if step_result and step_result.success:
                execution.step_results[step.id] = step_result.data
                completed_steps.add(step.id)
                logger.info(f"✅ Step {step.name} completed successfully")
            else:
                # Step failed even after LLM reasoning attempts
                execution.step_results[step.id] = None
                logger.error(f"🔥 Step {step.name} FINAL FAILURE - stopping workflow execution")
                
                # Add failure info to execution
                if not hasattr(execution, 'failed_steps'):
                    execution.failed_steps = []
                execution.failed_steps.append({
                    "step_name": step.name,
                    "step_id": step.id,
                    "error": step_result.error if step_result else "Unknown error",
                    "metadata": step_result.metadata if step_result else {}
                })
                
                # For critical failures, stop execution
                # (Could be made configurable per step in future)
                break
        
        # Compile final output
        execution.output_data = self._compile_workflow_output(template, execution)
    
    async def _execute_step_with_reasoning(self, step, step_input: Dict[str, Any], tool, 
                                          execution_context: Optional[ExecutionContext],
                                          execution) -> Any:
        """Execute step with LLM reasoning for failure recovery (SEQUENTIAL REASONED EXECUTION)"""
        
        max_reasoning_attempts = 3
        attempt = 0
        last_error = None
        current_step_input = step_input.copy()
        
        while attempt < max_reasoning_attempts:
            try:
                # Try executing the step
                logger.info(f"▶️ Executing Step {attempt + 1}: {step.name} (Tool: {step.tool_name})")
                
                step_result = await asyncio.wait_for(
                    tool.execute(step.capability, current_step_input, execution_context),
                    timeout=step.timeout_seconds
                )
                
                if step_result.success:
                    logger.info(f"✅ Step {step.name} completed successfully")
                    return step_result
                
                # STEP FAILED - Apply LLM reasoning for remedy
                last_error = step_result.error
                logger.error(f"❌ Step {step.name} failed: {step_result.error}")
                
                if attempt < max_reasoning_attempts - 1:  # Don't reason on last attempt
                    logger.info(f"🧠 Applying LLM reasoning to fix Step {step.name} (Attempt {attempt + 1}/{max_reasoning_attempts})")
                    
                    remedy_result = await self._apply_llm_remedy_to_step(
                        step=step,
                        step_input=current_step_input,
                        failure_error=step_result.error,
                        failure_data=step_result.data,
                        execution=execution,
                        attempt_number=attempt + 1
                    )
                    
                    if remedy_result and remedy_result.get("success"):
                        # LLM provided a remedy - update step input and retry
                        remedy_info = remedy_result.get("remedy_info", {})
                        current_step_input = remedy_info.get("updated_input", current_step_input)
                        
                        # Update step timeout if recommended
                        if "updated_timeout" in remedy_info:
                            step.timeout_seconds = remedy_info["updated_timeout"]
                        
                        logger.info(f"🧠 LLM Remedy Applied: {remedy_info.get('remedy_description', 'Generic fix')}")
                        
                        # Log confidence level
                        confidence = remedy_info.get('confidence', 0.0)
                        logger.info(f"🎯 Remedy Confidence: {confidence:.2f}")
                    else:
                        logger.warning(f"🚨 LLM Remedy Failed for step {step.name}")
                
                attempt += 1
                
            except asyncio.TimeoutError:
                last_error = f"Step timed out after {step.timeout_seconds} seconds"
                logger.warning(f"⏰ Step {step.name} attempt {attempt + 1} timed out")
                attempt += 1
            except Exception as e:
                last_error = str(e)
                logger.error(f"💥 Step {step.name} attempt {attempt + 1} crashed: {str(e)}")
                attempt += 1
        
        # All attempts failed - create final error result
        final_error = f"Step failed after {max_reasoning_attempts} reasoning attempts. Last error: {last_error}"
        logger.error(f"🔥 FINAL FAILURE: {step.name} - {final_error}")
        
        # Return failed result but don't raise exception (let workflow continue or decide)
        from ..contracts.base_types import AgentResult
        return AgentResult(
            success=False,
            error=final_error,
            metadata={
                "max_attempts_reached": True, 
                "reasoning_attempts": max_reasoning_attempts,
                "step_name": step.name,
                "tool_name": step.tool_name
            }
        )
    
    async def _apply_llm_remedy_to_step(self, step, step_input: Dict[str, Any], 
                                       failure_error: str, failure_data: Any,
                                       execution, attempt_number: int) -> Optional[Dict[str, Any]]:
        """Use LLM to analyze step failure and provide remedy (CORE INNOVATION)"""
        
        try:
            # Build context for LLM reasoning
            previous_results = {
                step_id: {"data": result_data, "success": True} 
                for step_id, result_data in execution.step_results.items()
                if result_data is not None
            }
            
            remedy_prompt = f"""
STEP FAILURE ANALYSIS & REMEDY

**Failed Step Details:**
- Step Name: {step.name}
- Tool: {step.tool_name}
- Capability: {step.capability}
- Input Data: {step_input}
- Error: {failure_error}
- Failure Data: {failure_data}
- Timeout: {step.timeout_seconds}s

**Previous Successful Steps:**
{self._format_previous_results_for_remedy(previous_results)}

**Attempt Number:** {attempt_number}/3

**TASK:** Analyze this specific step failure and provide a precise remedy.

**COMMON FAILURE PATTERNS TO CHECK:**
1. **File/Directory Path Issues**: 
   - Wrong capitalization (e.g., "Rmms" vs "RMMS")
   - Wrong path format
   - Missing directories
   
2. **Command Parameter Issues**:
   - Missing required parameters
   - Wrong parameter format
   - Invalid parameter values
   
3. **Timeout Issues**:
   - Command taking too long (du commands can be slow)
   - Insufficient timeout for large directories
   
4. **Permission/Access Issues**:
   - Insufficient permissions
   - Protected directories

**FOR THIS SPECIFIC CASE:**
The error suggests a "file not found" issue. The most likely cause is:
- Directory name case mismatch (user said "Rmms" but actual directory is "RMMS")
- Need to correct the path or use alternative approach

**REQUIRED REMEDY OUTPUT:**
1. **Root Cause**: Specific reason for failure
2. **Fix Strategy**: Exact changes needed
3. **Updated Input**: Modified input data (JSON format)
4. **Updated Timeout**: Recommended timeout if needed
5. **Confidence**: Success probability (0.0-1.0)

Respond ONLY with valid JSON in this exact format:
{{
    "root_cause": "string describing exact cause",
    "remedy_strategy": "string describing fix approach", 
    "updated_input": {{"command": "corrected command", "timeout": "number if needed"}},
    "updated_timeout": 60,
    "confidence_level": 0.85
}}
"""

            # Use LLM service to get remedy (BLUEPRINT COMPLIANT)
            remedy_text = await self.llm_service.generate_text(
                prompt=remedy_prompt,
                max_tokens=500,
                context=execution_context,
                provider=llm_provider,
                model=llm_model
            )
            
            if remedy_response and remedy_response.success:
                # Try to parse JSON response
                import json
                try:
                    remedy_json = json.loads(remedy_response.data.get("response", "{}"))
                    
                    # Validate confidence level
                    confidence = remedy_json.get("confidence_level", 0.0)
                    if confidence > 0.6:  # Only apply high-confidence remedies
                        return {
                            "success": True,
                            "remedy_info": {
                                "remedy_description": remedy_json.get("remedy_strategy", "LLM-generated fix"),
                                "updated_input": remedy_json.get("updated_input", step_input),
                                "updated_timeout": remedy_json.get("updated_timeout"),
                                "confidence": confidence,
                                "root_cause": remedy_json.get("root_cause", "Unknown")
                            }
                        }
                    else:
                        logger.warning(f"🚨 LLM remedy confidence too low: {confidence}")
                        return {"success": False, "reason": f"Low confidence: {confidence}"}
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"🚨 Failed to parse LLM remedy JSON: {e}")
                    return {"success": False, "reason": "Invalid JSON response"}
            else:
                logger.warning(f"🚨 LLM reasoning failed: {remedy_response.error if remedy_response else 'No response'}")
                return {"success": False, "reason": "LLM reasoning failed"}
                
        except Exception as e:
            logger.error(f"💥 LLM remedy generation crashed: {str(e)}")
            return {"success": False, "reason": f"Exception: {str(e)}"}
    
    def _format_previous_results_for_remedy(self, results: Dict[str, Any]) -> str:
        """Format previous results for LLM context"""
        if not results:
            return "No previous successful steps."

        formatted = []
        for step_id, result_info in results.items():
            formatted.append(f"✅ Step {step_id}: SUCCESS")
            if result_info.get("data"):
                data_str = str(result_info["data"])[:150]
                formatted.append(f"   Output: {data_str}{'...' if len(str(result_info['data'])) > 150 else ''}")

        return "\n".join(formatted)

    def _truncate_step_results_for_summary(self, step_results: Dict[str, Any], max_total_chars: int = 5000) -> str:
        """Truncate step results to avoid context length overflow in summary prompts

        IMPROVED: Better preserves important data fields for LLM understanding
        """
        if not step_results:
            return "{}"

        def truncate_value(value, max_chars: int = 500, depth: int = 0) -> Any:
            """Recursively truncate a value while preserving important information"""
            if value is None:
                return None
            if isinstance(value, (int, float, bool)):
                return value  # Keep numbers and bools as-is
            if isinstance(value, str):
                return value[:max_chars] + "..." if len(value) > max_chars else value
            if isinstance(value, list):
                # For lists, show count and sample items
                count = len(value)
                if count == 0:
                    return []
                if count > 5:
                    # Show count + first 3 items
                    truncated_items = [truncate_value(item, 200, depth + 1) for item in value[:3]]
                    return {"_list_count": count, "_sample_items": truncated_items}
                return [truncate_value(item, 200, depth + 1) for item in value]
            if isinstance(value, dict):
                if depth > 2:
                    # Too deep, just show keys
                    return {"_keys": list(value.keys())[:10]}

                # Extended essential keys - more comprehensive
                essential_keys = [
                    # Identifiers
                    'id', 'pageId', 'companyId', 'userId', 'menuId', 'buttonId',
                    'tagId', 'deviceId', 'sensorId', 'pointId', 'objectId',
                    # Names and titles
                    'name', 'pageName', 'title', 'label', 'description', 'tag', 'address',
                    # Status and type
                    'type', 'status', 'state', 'enabled', 'visible', 'active',
                    # Counts (very important!)
                    'count', 'total', 'length', 'size', 'quantity', 'number',
                    'totalComponents', 'componentCounts', 'tagBindingCount',  # SCADA analyze_page fields
                    # Data arrays (show counts)
                    'items', 'data', 'results', 'list', 'records', 'pages', 'gauges',
                    # SCADA specific
                    'buttonMenus', 'buttons', 'menus', 'components', 'elements', 'tagBindings',
                    'value', 'values', 'output', 'response', 'message', 'unit', 'min', 'max',
                    # Metadata
                    'success', 'error', 'code'
                ]

                result = {}
                # First, add all essential keys if present
                for key in essential_keys:
                    if key in value:
                        result[key] = truncate_value(value[key], 150, depth + 1)

                # If no essential keys found, take first 5 key-value pairs
                if not result:
                    for i, (k, v) in enumerate(value.items()):
                        if i >= 5:
                            break
                        result[k] = truncate_value(v, 150, depth + 1)

                # Always include count/length if it's a meaningful structure
                if len(value) > len(result):
                    result["_total_fields"] = len(value)

                return result
            return str(value)[:max_chars] if len(str(value)) > max_chars else value

        truncated = {}
        for step_id, result_data in step_results.items():
            truncated[step_id] = truncate_value(result_data, 1500, 0)

        result_str = json.dumps(truncated, indent=2, ensure_ascii=False)

        # Final safety truncation
        if len(result_str) > max_total_chars:
            return result_str[:max_total_chars] + "\n... [truncated for context limits]"

        return result_str
    
    def _normalize_step_input(self, step, step_input: Dict[str, Any], llm_provider: str = None, step_results: Dict[str, Any] = None) -> Dict[str, Any]:
        """Normalize step input parameters for tool compatibility"""
        normalized = step_input.copy()

        # Debug logging
        logger.debug(f"🔧 Normalizing input for {step.tool_name}.{step.capability}: {step_input}")

        # ============================================================
        # STEP 0: Resolve placeholders from previous step results
        # ============================================================
        if step_results:
            step_context = f"{step.name} {step.description}".lower() if hasattr(step, 'name') else ""
            normalized = self._resolve_step_placeholders(normalized, step_results, step_context)
            logger.debug(f"🔗 After placeholder resolution: {normalized}")
        
        if step.tool_name == "llm_tool" and step.capability in ["chat", "generate_response"]:
            # LLM tool expects 'message' field, but LLM might generate 'query', 'prompt', etc.
            
            if 'message' not in normalized:
                # Look for alternative message fields and map to 'message'
                for alt_field in ['query', 'prompt', 'text', 'content', 'input']:
                    if alt_field in normalized:
                        normalized['message'] = normalized[alt_field]
                        break
                else:
                    # If no alternative found, create a generic message
                    normalized['message'] = f"Process this request: {step.description}"
            
            # Inject user's selected LLM provider
            if 'provider' not in normalized:
                if llm_provider:
                    normalized['provider'] = llm_provider
                    logger.debug(f"Injected user's LLM provider: {llm_provider}")
                else:
                    raise ValueError("LLM provider must be specified by user. No default provider available.")
            
            # Inject previous step results as context for LLM
            if step_results and len(step_results) > 0:
                context_info = []
                for step_id, result_data in step_results.items():
                    if result_data and isinstance(result_data, dict):
                        # Format step results for LLM context  
                        if 'output' in result_data:  # Command executor results
                            # For command results, extract key information properly
                            if isinstance(result_data, dict) and 'stdout' in result_data:
                                stdout_content = result_data['stdout'][:1000]  # Increased to 1000 chars
                                context_info.append(f"Previous step {step_id} output: {stdout_content}")
                            else:
                                context_info.append(f"Previous step {step_id} output: {str(result_data)[:1000]}")
                        elif 'response' in result_data:  # LLM tool results  
                            context_info.append(f"Previous step {step_id} response: {result_data['response']}")
                        else:
                            # Generic result data - increased limit
                            context_info.append(f"Previous step {step_id} result: {str(result_data)[:800]}")
                
                if context_info:
                    # Enhance message with context
                    original_message = normalized['message']
                    enhanced_message = f"""Based on the following previous step results:

{chr(10).join(context_info)}

{original_message}"""
                    normalized['message'] = enhanced_message
                    logger.info(f"🔗 Enhanced LLM message with {len(context_info)} previous step results")
        
        elif step.tool_name == "command_executor" and step.capability == "execute_command":
            # Command executor expects 'command' field
            
            if 'command' not in normalized:
                # Look for alternative command fields
                for alt_field in ['cmd', 'shell_command', 'exec', 'run']:
                    if alt_field in normalized:
                        normalized['command'] = normalized[alt_field]
                        break
                else:
                    # If no alternative found, create from description
                    normalized['command'] = f"echo 'Command from step: {step.description}'"
                    logger.warning(f"No command found in step input, using fallback: {normalized['command']}")
                
        return normalized

    def _resolve_step_placeholders(self, params: Dict[str, Any], step_results: Dict[str, Any], step_context: str = "") -> Dict[str, Any]:
        """Resolve placeholder values from previous step results.

        Handles patterns like:
        - "NEW_PAGE_ID" -> looks for pageId in previous steps
        - "$step_1.pageId" -> explicit reference to step_1's pageId
        - "PREVIOUS_RESULT" -> uses last step's main result

        step_context: lowercase step name+description for name-based list filtering
        """
        if not step_results:
            return params

        resolved = {}

        # Get the last step result for convenience
        last_step_id = list(step_results.keys())[-1] if step_results else None
        last_result = step_results.get(last_step_id, {}) if last_step_id else {}

        # Common ID fields to look for in step results
        id_fields = ['pageId', 'page_id', 'id', 'companyId', 'company_id', 'userId', 'user_id', 'widgetId', 'widget_id']

        def find_value_in_results(key_to_find: str) -> Any:
            """Search for a value in all step results"""
            # First try exact match in last result
            if isinstance(last_result, dict):
                if key_to_find in last_result:
                    return last_result[key_to_find]
                # Check nested 'data' field
                if 'data' in last_result and isinstance(last_result['data'], dict):
                    if key_to_find in last_result['data']:
                        return last_result['data'][key_to_find]

            # Search all step results
            for step_id, result in step_results.items():
                if isinstance(result, dict):
                    if key_to_find in result:
                        return result[key_to_find]
                    if 'data' in result and isinstance(result['data'], dict):
                        if key_to_find in result['data']:
                            return result['data'][key_to_find]
            return None

        def resolve_value(value: Any, param_name: str) -> Any:
            """Resolve a single value"""
            if not isinstance(value, str):
                return value

            # Pattern 0: {result_from_step_N} format (LLM generated)
            import re
            result_from_match = re.match(r'\{?result_from_step_(\d+)\}?', value)
            if result_from_match:
                step_num = result_from_match.group(1)
                step_key = f"step_{step_num}"
                if step_key in step_results:
                    result = step_results[step_key]
                    # Return the whole result or extract relevant ID
                    if isinstance(result, dict):
                        # Try to find relevant ID based on param_name
                        if param_name in ['widget_id', 'widgetId']:
                            for field in ['widget_id', 'widgetId', 'id', 'component_id']:
                                if field in result:
                                    logger.info(f"🔗 Resolved {value} -> {result[field]}")
                                    return result[field]
                                if 'data' in result and isinstance(result['data'], dict) and field in result['data']:
                                    logger.info(f"🔗 Resolved {value} -> {result['data'][field]}")
                                    return result['data'][field]
                        # Return first ID-like field found
                        for field in id_fields:
                            if field in result:
                                logger.info(f"🔗 Resolved {value} -> {result[field]}")
                                return result[field]
                    logger.info(f"🔗 Resolved {value} -> {result}")
                    return result
                else:
                    logger.warning(f"⚠️ Step {step_key} not found in results for placeholder {value}")

            # Pattern 1: Explicit reference like "$step_1.pageId"
            if value.startswith('$step_'):
                match = re.match(r'\$step_(\d+)\.(\w+)', value)
                if match:
                    step_num = match.group(1)
                    field_name = match.group(2)
                    step_key = f"step_{step_num}"
                    if step_key in step_results:
                        result = step_results[step_key]
                        if isinstance(result, dict):
                            # Direct field match
                            if field_name in result:
                                logger.info(f"🔗 Resolved {value} -> {result[field_name]}")
                                return result[field_name]
                            # Check 'data' sub-dict
                            if 'data' in result and isinstance(result['data'], dict):
                                if field_name in result['data']:
                                    logger.info(f"🔗 Resolved {value} -> {result['data'][field_name]}")
                                    return result['data'][field_name]

                            # ID aliasing: page_id -> id, pageId, etc.
                            id_alias_map = {
                                'page_id': ['id', 'pageId'],
                                'company_id': ['id', 'companyId'],
                                'widget_id': ['id', 'widgetId'],
                                'workflow_id': ['id', 'workflowId'],
                                'code_id': ['id', 'codeId'],
                                'datasource_id': ['id', 'datasourceId'],
                                'task_id': ['id', 'taskId'],
                                'node_id': ['id', 'nodeId'],
                            }
                            aliases = id_alias_map.get(field_name, [field_name])

                            # Try aliases at top level
                            for alias in aliases:
                                if alias in result:
                                    logger.info(f"🔗 Resolved {value} -> {result[alias]} (alias {field_name}->{alias})")
                                    return result[alias]

                            # Search inside list values within result
                            # Build name context from params AND step_context
                            name_context = None
                            for pk, pv in params.items():
                                if pk in ['name', 'page_name', 'pageName', 'search', 'filter_name'] and isinstance(pv, str) and not pv.startswith('$'):
                                    name_context = pv.lower()
                                    break
                            # If no name in params, extract from step_context (step name/description)
                            if not name_context and step_context:
                                name_context = step_context

                            # Fuzzy matching helper: normalize string for comparison
                            def normalize_for_match(s: str) -> str:
                                """Remove separators and normalize for fuzzy matching"""
                                import re
                                # Remove common separators: space, hyphen, underscore, dot
                                normalized = re.sub(r'[\s\-_\.]+', '', s.lower())
                                return normalized

                            def fuzzy_match(item_name: str, context: str) -> bool:
                                """Check if item_name fuzzy-matches any word in context"""
                                if not item_name or not context:
                                    return False
                                # Normalize both
                                norm_item = normalize_for_match(item_name)
                                norm_context = normalize_for_match(context)
                                # Direct substring match after normalization
                                if norm_item in norm_context or norm_context in norm_item:
                                    return True
                                # Token-based: check if normalized item matches any word in context
                                # Minimum 5 chars to avoid false matches from common short words like 'for', 'the', 'and'
                                context_words = [normalize_for_match(w) for w in context.split() if len(w) >= 5]
                                for word in context_words:
                                    # Word must be substantial (5+ chars) to be used for matching
                                    if word and norm_item and len(word) >= 5 and (word in norm_item or norm_item in word):
                                        return True
                                    # Also check edit distance for very close matches (1-2 chars diff)
                                    if word and norm_item and len(word) >= 5 and len(norm_item) >= 5:
                                        if abs(len(word) - len(norm_item)) <= 2:
                                            # Simple similarity: count matching chars
                                            matches = sum(1 for a, b in zip(word, norm_item) if a == b)
                                            if matches >= min(len(word), len(norm_item)) * 0.7:
                                                return True
                                return False

                            for result_key, result_val in result.items():
                                if isinstance(result_val, list) and result_val:
                                    logger.debug(f"🔍 Resolver: key={result_key}, items={len(result_val)}, name_context='{name_context}'")
                                    # Single item: use it directly
                                    if len(result_val) == 1 and isinstance(result_val[0], dict):
                                        for alias in aliases:
                                            if alias in result_val[0]:
                                                logger.info(f"🔗 Resolved {value} -> {result_val[0][alias]} (single list item)")
                                                return result_val[0][alias]

                                    # Multiple items: try fuzzy name-based filtering
                                    if name_context and len(result_val) > 1:
                                        for item in result_val:
                                            if isinstance(item, dict):
                                                item_name = item.get('pageName') or item.get('name') or item.get('title') or ''
                                                if fuzzy_match(item_name, name_context):
                                                    for alias in aliases:
                                                        if alias in item:
                                                            logger.info(f"🔗 Resolved {value} -> {item[alias]} (fuzzy match: {item_name})")
                                                            return item[alias]

                                    # Fallback: use first item with matching alias
                                    for item in result_val:
                                        if isinstance(item, dict):
                                            for alias in aliases:
                                                if alias in item:
                                                    logger.info(f"🔗 Resolved {value} -> {item[alias]} (first list item fallback)")
                                                    return item[alias]

                            logger.warning(f"⚠️ Could not resolve {value} from step_results[{step_key}]")

            # Pattern 2: Generic placeholders like "NEW_PAGE_ID", "PREVIOUS_RESULT"
            placeholder_patterns = [
                'NEW_PAGE_ID', 'PAGE_ID', 'CREATED_PAGE_ID',
                'NEW_ID', 'PREVIOUS_RESULT', 'RESULT_ID'
            ]

            if value.upper() in placeholder_patterns or '_ID' in value.upper():
                # Try to find appropriate value based on parameter name
                if param_name in ['page_id', 'pageId']:
                    found = find_value_in_results('pageId') or find_value_in_results('page_id') or find_value_in_results('id')
                    if found:
                        logger.info(f"🔗 Resolved placeholder {value} for {param_name} -> {found}")
                        return found
                elif param_name in ['company_id', 'companyId']:
                    found = find_value_in_results('companyId') or find_value_in_results('company_id')
                    if found:
                        logger.info(f"🔗 Resolved placeholder {value} for {param_name} -> {found}")
                        return found
                else:
                    # Generic: try all ID fields
                    for field in id_fields:
                        found = find_value_in_results(field)
                        if found:
                            logger.info(f"🔗 Resolved placeholder {value} -> {found} (from {field})")
                            return found

            return value

        # Resolve all parameters
        for key, value in params.items():
            if isinstance(value, dict):
                # Recursively resolve nested dicts
                resolved[key] = self._resolve_step_placeholders(value, step_results)
            elif isinstance(value, list):
                # Resolve items in lists
                resolved[key] = [resolve_value(item, key) if isinstance(item, str) else item for item in value]
            else:
                resolved[key] = resolve_value(value, key)

        return resolved

    async def _execute_step_with_reasoning_inline(self, step, step_input: Dict[str, Any], tool,
                                                 execution_context: Optional[ExecutionContext],
                                                 workflow_context: Dict[str, Any],
                                                 llm_provider: str = None,
                                                 llm_model: str = None) -> Any:
        """Execute step with LLM reasoning for failure recovery (INLINE VERSION for process_user_request)"""
        
        max_reasoning_attempts = 3
        attempt = 0
        last_error = None
        current_step_input = step_input.copy() if step_input else {}
        
        while attempt < max_reasoning_attempts:
            try:
                # Try executing the step
                logger.info(f"▶️ Executing Step {attempt + 1}: {step.name} (Tool: {step.tool_name})")
                
                step_result = await asyncio.wait_for(
                    tool.execute(step.capability, current_step_input, execution_context),
                    timeout=getattr(step, 'timeout_seconds', 30)
                )
                
                if step_result.success:
                    logger.info(f"✅ Step {step.name} completed successfully")
                    return step_result
                
                # STEP FAILED - Apply LLM reasoning for remedy
                last_error = step_result.error
                logger.error(f"❌ Step {step.name} failed: {step_result.error}")
                
                if attempt < max_reasoning_attempts - 1:  # Don't reason on last attempt
                    logger.info(f"🧠 Applying LLM reasoning to fix Step {step.name} (Attempt {attempt + 1}/{max_reasoning_attempts})")
                    
                    remedy_result = await self._apply_llm_remedy_to_step_inline(
                        step=step,
                        step_input=current_step_input,
                        failure_error=step_result.error,
                        failure_data=step_result.data,
                        workflow_context=workflow_context,
                        attempt_number=attempt + 1,
                        execution_context=execution_context,
                        llm_provider=llm_provider,
                        llm_model=llm_model
                    )
                    
                    if remedy_result and remedy_result.get("success"):
                        # LLM provided a remedy - update step input and retry
                        remedy_info = remedy_result.get("remedy_info", {})
                        current_step_input = remedy_info.get("updated_input", current_step_input)
                        
                        logger.info(f"🧠 LLM Remedy Applied: {remedy_info.get('remedy_description', 'Generic fix')}")
                        
                        # Log confidence level
                        confidence = remedy_info.get('confidence', 0.0)
                        logger.info(f"🎯 Remedy Confidence: {confidence:.2f}")
                    else:
                        logger.warning(f"🚨 LLM Remedy Failed for step {step.name}")
                
                attempt += 1
                
            except asyncio.TimeoutError:
                last_error = f"Step timed out after {getattr(step, 'timeout_seconds', 30)} seconds"
                logger.warning(f"⏰ Step {step.name} attempt {attempt + 1} timed out")
                attempt += 1
            except Exception as e:
                last_error = str(e)
                logger.error(f"💥 Step {step.name} attempt {attempt + 1} crashed: {str(e)}")
                attempt += 1
        
        # All attempts failed - create final error result
        final_error = f"Step failed after {max_reasoning_attempts} reasoning attempts. Last error: {last_error}"
        logger.error(f"🔥 FINAL FAILURE: {step.name} - {final_error}")
        
        # Return failed result with the same structure as successful result
        from ..contracts.base_types import AgentResult
        return AgentResult(
            success=False,
            error=final_error,
            metadata={
                "max_attempts_reached": True, 
                "reasoning_attempts": max_reasoning_attempts,
                "step_name": step.name,
                "tool_name": step.tool_name
            }
        )
    
    async def _apply_llm_remedy_to_step_inline(self, step, step_input: Dict[str, Any], 
                                              failure_error: str, failure_data: Any,
                                              workflow_context: Dict[str, Any], 
                                              attempt_number: int,
                                              execution_context: Optional[ExecutionContext],
                                              llm_provider: str = None,
                                              llm_model: str = None) -> Optional[Dict[str, Any]]:
        """Use LLM to analyze step failure and provide remedy (INLINE VERSION)"""
        
        try:
            # Build context for LLM reasoning
            previous_results = workflow_context.get("step_results", {})

            # Get tool's capability schema for constraint
            capability_schema_str = "Unknown schema"
            try:
                metadata = self.tool_manager.registry.get_tool_metadata(step.tool_name)
                if metadata:
                    for cap in metadata.capabilities:
                        if cap.name == step.capability:
                            capability_schema_str = json.dumps(cap.input_schema, indent=2, ensure_ascii=False)
                            break
            except Exception:
                pass

            remedy_prompt = f"""
STEP FAILURE ANALYSIS & REMEDY

**Failed Step Details:**
- Tool: {step.tool_name}
- Capability: {step.capability}
- Input Data: {json.dumps(step_input, ensure_ascii=False)}
- Error: {failure_error}
- Response Data: {str(failure_data)[:300] if failure_data else 'None'}

**Capability Input Schema (ONLY these parameters are valid):**
{capability_schema_str}

**Previous Successful Steps:**
{self._format_previous_results_for_remedy_inline(previous_results)}

**Attempt Number:** {attempt_number}/3

**TASK:** Analyze this failure and provide corrected input parameters.

**RULES:**
- The "updated_input" MUST only contain keys defined in the Capability Input Schema above
- Do NOT invent parameters that don't exist in the schema (e.g. no "command" unless schema defines it)
- Fix the actual error: wrong values, missing required fields, type mismatches
- If the error indicates the capability/tool doesn't support this operation, set confidence_level to 0.0

**RESPOND WITH ONLY THIS JSON (no other text):**
{{
    "root_cause": "<brief description of why it failed>",
    "remedy_strategy": "<what you're fixing>",
    "updated_input": {{<corrected parameters matching the schema>}},
    "confidence_level": <0.0 to 1.0>
}}
"""

            # Use LLM service to get remedy (BLUEPRINT COMPLIANT)
            remedy_text = await self.llm_service.generate_text(
                prompt=remedy_prompt,
                max_tokens=500,
                context=execution_context,
                provider=llm_provider,
                model=llm_model
            )
            
            # DEBUG: Log LLM response
            logger.info(f"🔍 LLM Remedy Response: '{remedy_text}' (type: {type(remedy_text)}, len: {len(remedy_text) if remedy_text else 'None'})")
            
            if remedy_text:
                # Try to parse JSON response (strip markdown code blocks if present)
                try:
                    # Clean up markdown code blocks
                    clean_text = remedy_text.strip()
                    if clean_text.startswith('```json'):
                        clean_text = clean_text[7:]  # Remove ```json
                    if clean_text.startswith('```'):
                        clean_text = clean_text[3:]   # Remove ```
                    if clean_text.endswith('```'):
                        clean_text = clean_text[:-3]  # Remove trailing ```
                    clean_text = clean_text.strip()
                    
                    remedy_json = json.loads(clean_text)

                    # Validate updated_input keys against capability schema
                    updated_input = remedy_json.get("updated_input", {})
                    if updated_input and capability_schema_str != "Unknown schema":
                        try:
                            cap_schema = json.loads(capability_schema_str)
                            valid_keys = set(cap_schema.get("properties", {}).keys())
                            if valid_keys:
                                invalid_keys = set(updated_input.keys()) - valid_keys
                                if invalid_keys:
                                    logger.warning(f"🚨 Remedy contains invalid keys {invalid_keys}, filtering to schema keys {valid_keys}")
                                    remedy_json["updated_input"] = {k: v for k, v in updated_input.items() if k in valid_keys}
                                    if not remedy_json["updated_input"]:
                                        return {"success": False, "reason": f"All remedy keys invalid: {invalid_keys}"}
                        except (json.JSONDecodeError, Exception):
                            pass

                    # Validate confidence level
                    confidence = remedy_json.get("confidence_level", 0.0)
                    if confidence > 0.6:  # Only apply high-confidence remedies
                        return {
                            "success": True,
                            "remedy_info": {
                                "remedy_description": remedy_json.get("remedy_strategy", "LLM-generated fix"),
                                "updated_input": remedy_json.get("updated_input", step_input),
                                "confidence": confidence,
                                "root_cause": remedy_json.get("root_cause", "Unknown")
                            }
                        }
                    else:
                        logger.warning(f"🚨 LLM remedy confidence too low: {confidence}")
                        return {"success": False, "reason": f"Low confidence: {confidence}"}
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"🚨 Failed to parse LLM remedy JSON: {e}")
                    return {"success": False, "reason": "Invalid JSON response"}
            else:
                logger.warning(f"🚨 LLM reasoning failed: No response from LLM")
                return {"success": False, "reason": "LLM reasoning failed"}
                
        except Exception as e:
            logger.error(f"💥 LLM remedy generation crashed: {str(e)}")
            return {"success": False, "reason": f"Exception: {str(e)}"}
    
    def _format_previous_results_for_remedy_inline(self, results: Dict[str, Any]) -> str:
        """Format previous results for LLM context (INLINE VERSION)"""
        if not results:
            return "No previous successful steps."
        
        formatted = []
        for step_id, result_data in results.items():
            if result_data and not isinstance(result_data, dict) or not result_data.get("error"):
                formatted.append(f"✅ Step {step_id}: SUCCESS")
                if result_data:
                    data_str = str(result_data)[:150]
                    formatted.append(f"   Output: {data_str}{'...' if len(str(result_data)) > 150 else ''}")
        
        return "\n".join(formatted) if formatted else "No previous successful steps."
    
    def _substitute_variables(self, data: Any, execution: WorkflowExecution) -> Any:
        """Substitute variables in step input data"""
        if isinstance(data, dict):
            return {k: self._substitute_variables(v, execution) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._substitute_variables(item, execution) for item in data]
        elif isinstance(data, str):
            # Simple variable substitution
            # {{variable}} -> from input_data
            # {{step_id.field}} -> from step results
            # {{variable|default}} -> with default value
            
            # This is a simplified implementation - could use Jinja2 for more advanced templating
            import re
            
            def replace_var(match):
                var_expr = match.group(1)
                
                # Handle default values
                if '|' in var_expr:
                    var_name, default_value = var_expr.split('|', 1)
                else:
                    var_name, default_value = var_expr, None
                
                # Handle step references
                if '.' in var_name:
                    step_id, field = var_name.split('.', 1)
                    step_result = execution.step_results.get(step_id, {})
                    value = step_result.get(field) if isinstance(step_result, dict) else None
                else:
                    # Direct input data reference
                    value = execution.input_data.get(var_name)
                
                if value is None:
                    return default_value if default_value is not None else f"{{{{{var_expr}}}}}"
                
                return str(value)
            
            return re.sub(r'\{\{([^}]+)\}\}', replace_var, data)
        else:
            return data
    
    def _compile_workflow_output(self, template: WorkflowTemplate, execution: WorkflowExecution) -> Dict[str, Any]:
        """Compile final workflow output from step results"""
        output = {}
        
        # Include all step results
        output["step_results"] = execution.step_results
        
        # Include specific outputs based on template output schema
        for output_key, schema in template.output_schema.items():
            # Try to find the output value from step results
            for step_id, step_result in execution.step_results.items():
                if isinstance(step_result, dict) and output_key in step_result:
                    output[output_key] = step_result[output_key]
                    break
        
        return output
    
    async def _auto_save_successful_workflow(self, 
                                           original_template: WorkflowTemplate,
                                           execution: WorkflowExecution,
                                           user_id: str):
        """Auto-save successful workflow execution as a new template"""
        try:
            # Create new auto-generated template
            auto_template = WorkflowTemplate(
                id=f"auto_{execution.id}",
                name=f"Auto: {original_template.name} - {datetime.utcnow().strftime('%Y%m%d_%H%M')}",
                description=f"Auto-generated from successful execution of {original_template.name}",
                version="1.0.0",
                template_type=WorkflowTemplateType.AUTO_GENERATED,
                created_by=user_id,
                steps=original_template.steps,
                success_rate=1.0,  # First execution was successful
                total_executions=1,
                successful_executions=1,
                average_duration=execution.duration_seconds,
                tags=original_template.tags + ["auto-generated"],
                input_schema=original_template.input_schema,
                output_schema=original_template.output_schema,
                metadata={
                    "parent_template_id": original_template.id,
                    "execution_id": execution.id,
                    "input_data": execution.input_data,
                    "output_data": execution.output_data
                }
            )
            
            await self.template_manager.save_template(auto_template)
            logger.info(f"Auto-saved successful workflow as template: {auto_template.id}")
            
        except Exception as e:
            logger.error(f"Failed to auto-save workflow template: {e}")
    
    async def list_workflow_templates(self, 
                                    user_id: str,
                                    template_type: Optional[WorkflowTemplateType] = None) -> List[WorkflowTemplate]:
        """List available workflow templates"""
        return await self.template_manager.list_templates(user_id, template_type)
    
    async def get_workflow_template(self, template_id: str, user_id: str) -> Optional[WorkflowTemplate]:
        """Get specific workflow template"""
        return await self.template_manager.load_template(template_id, user_id)
    
    async def create_workflow_template_from_conversation(self, 
                                                       conversation_id: str,
                                                       user_id: str,
                                                       template_name: str) -> AgentResult[WorkflowTemplate]:
        """Create workflow template from successful conversation pattern"""
        try:
            # This would analyze a conversation and extract workflow steps
            # For now, return a placeholder implementation
            
            # Get conversation messages
            messages = await self.conversation_service.get_messages(conversation_id, user_id)
            
            if not messages:
                return AgentResult(success=False, error="Conversation not found or empty")
            
            # Analyze conversation pattern (simplified)
            steps = []
            for i, message in enumerate(messages):
                if message.role == "user":
                    step = WorkflowStep(
                        id=f"step_{i+1}",
                        name=f"User Input {i+1}",
                        tool_name="llm_tool",
                        capability="generate_response",
                        input_data={"messages": [{"role": "user", "content": message.content}]},
                        expected_outputs=["response"]
                    )
                    steps.append(step)
            
            # Create template
            template = WorkflowTemplate(
                id=str(uuid.uuid4()),
                name=template_name,
                description=f"Generated from conversation {conversation_id}",
                version="1.0.0",
                template_type=WorkflowTemplateType.AUTO_GENERATED,
                created_by=user_id,
                steps=steps,
                tags=["conversation-generated"]
            )
            
            # Save template
            success = await self.template_manager.save_template(template)
            
            if success:
                return AgentResult(success=True, data=template)
            else:
                return AgentResult(success=False, error="Failed to save template")
                
        except Exception as e:
            logger.error(f"Failed to create template from conversation: {e}")
            return AgentResult(success=False, error=str(e))
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get system health status"""
        return {
            "is_initialized": self.is_initialized,
            "component_health": self.component_health,
            "active_executions": len(self.active_executions),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def shutdown(self):
        """Gracefully shutdown the orchestrator"""
        try:
            logger.info("Shutting down Application Orchestrator...")
            
            # Cancel active executions
            for execution_id, execution in self.active_executions.items():
                execution.status = WorkflowStatus.CANCELLED
                logger.info(f"Cancelled active execution: {execution_id}")
            
            self.active_executions.clear()
            self.is_initialized = False
            
            logger.info("Application Orchestrator shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def _add_to_workflow_history(self, workflow_entry: Dict[str, Any]):
        """Add workflow to history with size limit management"""
        try:
            self.workflow_history.append(workflow_entry)
            
            # Maintain size limit (keep most recent)
            if len(self.workflow_history) > self.max_history_size:
                self.workflow_history = self.workflow_history[-self.max_history_size:]
                
            logger.info(f"📋 Added workflow {workflow_entry['workflow_id'][:8]}... to history ({len(self.workflow_history)}/{self.max_history_size})")
            
        except Exception as e:
            logger.error(f"Failed to add workflow to history: {e}")
    
    def get_workflow_history(self, user_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Get workflow history, optionally filtered by user"""
        try:
            if user_id:
                # Filter by user_id
                user_workflows = [wf for wf in self.workflow_history if wf.get("user_id") == user_id]
                return user_workflows[-limit:] if limit else user_workflows
            else:
                # Return all workflows (for admin view)
                return self.workflow_history[-limit:] if limit else self.workflow_history
        except Exception as e:
            logger.error(f"Failed to get workflow history: {e}")
            return []


# Singleton instance
_orchestrator_instance: Optional[ApplicationOrchestrator] = None

def get_orchestrator() -> ApplicationOrchestrator:
    """Get singleton orchestrator instance"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = ApplicationOrchestrator()
    return _orchestrator_instance


async def initialize_application() -> bool:
    """Initialize the application orchestrator"""
    orchestrator = get_orchestrator()
    return await orchestrator.initialize()