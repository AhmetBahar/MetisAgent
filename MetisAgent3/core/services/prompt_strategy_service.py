"""
3-Part Prompt Strategy Service

Implements a structured prompt composition system:
1. Policy Prompt - Company-wide rules, constraints, and permissions
2. Domain Prompt - Domain/module-specific context and rules
3. Task Prompt - The current user request and conversation context

This separation allows:
- Consistent policy enforcement across all interactions
- Domain experts to define their own context
- Clear task focus without policy/domain confusion
"""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class PromptSection(str, Enum):
    """Prompt section types"""
    POLICY = "policy"
    DOMAIN = "domain"
    TASK = "task"
    TOOLS = "tools"
    CONTEXT = "context"


@dataclass
class PolicyPrompt:
    """
    Company-wide policy rules and constraints.

    Applied to ALL interactions regardless of domain or task.
    """
    company_id: str
    company_name: str
    rules: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    forbidden_actions: List[str] = field(default_factory=list)
    data_handling: str = ""
    compliance_requirements: List[str] = field(default_factory=list)
    custom_instructions: str = ""

    def to_prompt(self) -> str:
        """Generate policy prompt text"""
        lines = [
            "## Policy Guidelines",
            f"Company: {self.company_name}",
            ""
        ]

        if self.rules:
            lines.append("### Rules")
            for rule in self.rules:
                lines.append(f"- {rule}")
            lines.append("")

        if self.constraints:
            lines.append("### Constraints")
            for constraint in self.constraints:
                lines.append(f"- {constraint}")
            lines.append("")

        if self.permissions:
            lines.append("### Allowed Actions")
            for perm in self.permissions:
                lines.append(f"- {perm}")
            lines.append("")

        if self.forbidden_actions:
            lines.append("### Forbidden Actions")
            for action in self.forbidden_actions:
                lines.append(f"- {action}")
            lines.append("")

        if self.data_handling:
            lines.append("### Data Handling")
            lines.append(self.data_handling)
            lines.append("")

        if self.compliance_requirements:
            lines.append("### Compliance Requirements")
            for req in self.compliance_requirements:
                lines.append(f"- {req}")
            lines.append("")

        if self.custom_instructions:
            lines.append("### Additional Instructions")
            lines.append(self.custom_instructions)
            lines.append("")

        return "\n".join(lines)


@dataclass
class DomainPrompt:
    """
    Domain/module-specific context and rules.

    Applies to a specific functional area (SCADA, Maintenance, etc.)
    """
    domain_name: str
    description: str = ""
    context: str = ""
    terminology: Dict[str, str] = field(default_factory=dict)
    available_tools: List[str] = field(default_factory=list)
    tool_descriptions: Dict[str, str] = field(default_factory=dict)
    domain_rules: List[str] = field(default_factory=list)
    examples: List[Dict[str, str]] = field(default_factory=list)

    def to_prompt(self) -> str:
        """Generate domain prompt text"""
        lines = [
            f"## Domain: {self.domain_name}",
            ""
        ]

        if self.description:
            lines.append(self.description)
            lines.append("")

        if self.context:
            lines.append("### Context")
            lines.append(self.context)
            lines.append("")

        if self.terminology:
            lines.append("### Terminology")
            for term, definition in self.terminology.items():
                lines.append(f"- **{term}**: {definition}")
            lines.append("")

        if self.available_tools:
            lines.append("### Available Tools")
            for tool in self.available_tools:
                desc = self.tool_descriptions.get(tool, "")
                lines.append(f"- `{tool}`: {desc}")
            lines.append("")

        if self.domain_rules:
            lines.append("### Domain-Specific Rules")
            for rule in self.domain_rules:
                lines.append(f"- {rule}")
            lines.append("")

        if self.examples:
            lines.append("### Examples")
            for i, example in enumerate(self.examples, 1):
                lines.append(f"**Example {i}:**")
                lines.append(f"User: {example.get('input', '')}")
                lines.append(f"Assistant: {example.get('output', '')}")
                lines.append("")

        return "\n".join(lines)


@dataclass
class TaskPrompt:
    """
    Current task context and user request.
    """
    user_message: str
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    extracted_entities: Dict[str, Any] = field(default_factory=dict)
    intent: Optional[str] = None
    priority: str = "medium"
    additional_context: str = ""

    def to_prompt(self) -> str:
        """Generate task prompt text"""
        lines = ["## Current Task", ""]

        if self.intent:
            lines.append(f"**Intent:** {self.intent}")

        if self.extracted_entities:
            lines.append("**Entities:**")
            for entity, value in self.extracted_entities.items():
                lines.append(f"  - {entity}: {value}")
            lines.append("")

        if self.conversation_history:
            lines.append("**Recent Conversation:**")
            for msg in self.conversation_history[-5:]:  # Last 5 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")
                lines.append(f"  {role}: {content[:200]}...")
            lines.append("")

        if self.additional_context:
            lines.append("**Additional Context:**")
            lines.append(self.additional_context)
            lines.append("")

        lines.append("**User Request:**")
        lines.append(self.user_message)

        return "\n".join(lines)


class PromptStrategyService:
    """
    Service for composing 3-part prompts.

    Combines Policy, Domain, and Task prompts into a coherent system prompt.
    """

    def __init__(self):
        self._policy_templates: Dict[str, PolicyPrompt] = {}
        self._domain_templates: Dict[str, DomainPrompt] = {}
        self._initialize_default_domains()

    def _initialize_default_domains(self):
        """Initialize default domain templates"""

        # SCADA Domain
        self._domain_templates["scada"] = DomainPrompt(
            domain_name="SCADA/HMI",
            description="Real-time monitoring and control of industrial processes.",
            context="You are assisting with SCADA operations including tag monitoring, "
                   "setpoint changes, and alarm management.",
            terminology={
                "Tag": "A named data point representing a sensor or actuator value",
                "Setpoint": "Target value for a process variable",
                "PLC": "Programmable Logic Controller - industrial computer",
                "HMI": "Human-Machine Interface - operator display"
            },
            domain_rules=[
                "Always verify tag exists before reading or writing",
                "Warn user before changing setpoints on critical tags",
                "Log all write operations for audit",
                "Check alarm limits before modifying tag values"
            ]
        )

        # Maintenance Domain
        self._domain_templates["maintenance"] = DomainPrompt(
            domain_name="Maintenance (TPM)",
            description="Total Productive Maintenance operations.",
            context="You are assisting with maintenance planning, execution, and tracking.",
            terminology={
                "TPM": "Total Productive Maintenance",
                "MTBF": "Mean Time Between Failures",
                "MTTR": "Mean Time To Repair",
                "PM": "Preventive Maintenance",
                "CM": "Corrective Maintenance"
            },
            domain_rules=[
                "Prioritize safety-critical equipment maintenance",
                "Check spare parts availability before scheduling",
                "Consider skill requirements for technician assignment",
                "Track actual vs estimated maintenance time"
            ]
        )

        # Work Order Domain
        self._domain_templates["workorder"] = DomainPrompt(
            domain_name="Work Order Management",
            description="Managing work orders and task assignments.",
            context="You are assisting with work order creation, assignment, and tracking.",
            domain_rules=[
                "Validate equipment ID before creating work orders",
                "Check technician availability before assignment",
                "Set appropriate priority based on impact",
                "Track work order status transitions"
            ]
        )

        # Data Science Domain
        self._domain_templates["datascience"] = DomainPrompt(
            domain_name="Data Science & Analytics",
            description="Machine learning, forecasting, and data analysis.",
            context="You are assisting with data analysis, ML model execution, and insights.",
            terminology={
                "Forecast": "Prediction of future values based on historical data",
                "Anomaly": "Unusual pattern that deviates from expected behavior",
                "Time Series": "Sequence of data points indexed by time"
            },
            domain_rules=[
                "Validate data quality before running analysis",
                "Explain model outputs in business terms",
                "Provide confidence intervals for predictions",
                "Warn about data gaps or quality issues"
            ]
        )

        # MES Domain
        self._domain_templates["mes"] = DomainPrompt(
            domain_name="Manufacturing Execution",
            description="Production tracking and manufacturing operations.",
            context="You are assisting with production management and MES operations.",
            terminology={
                "BOM": "Bill of Materials",
                "WIP": "Work In Progress",
                "Routing": "Sequence of operations for manufacturing",
                "Batch": "A group of products manufactured together"
            },
            domain_rules=[
                "Validate BOM before starting production",
                "Track material consumption accurately",
                "Record quality checks at each operation",
                "Maintain traceability of all materials"
            ]
        )

    def compose_prompt(
        self,
        policy: PolicyPrompt,
        domain: Optional[DomainPrompt],
        task: TaskPrompt,
        tools_context: Optional[str] = None
    ) -> str:
        """
        Compose a complete system prompt from the three parts.

        Args:
            policy: Policy prompt with company rules
            domain: Domain-specific prompt (optional)
            task: Current task prompt
            tools_context: Optional tool context from classifier

        Returns:
            Complete system prompt string
        """
        sections = []

        # 1. Policy Section
        sections.append(policy.to_prompt())

        # 2. Domain Section (if applicable)
        if domain:
            sections.append(domain.to_prompt())

        # 3. Tools Context (if provided)
        if tools_context:
            sections.append("## Available Tools\n")
            sections.append(tools_context)
            sections.append("")

        # 4. Task Section
        sections.append(task.to_prompt())

        return "\n\n".join(sections)

    def get_domain_template(self, domain_name: str) -> Optional[DomainPrompt]:
        """Get a domain template by name"""
        return self._domain_templates.get(domain_name.lower())

    def register_domain_template(self, domain_name: str, template: DomainPrompt):
        """Register a custom domain template"""
        self._domain_templates[domain_name.lower()] = template
        logger.info(f"Registered domain template: {domain_name}")

    def create_policy_prompt(
        self,
        company_id: str,
        company_name: str,
        user_role: str,
        permissions: List[str]
    ) -> PolicyPrompt:
        """
        Create a policy prompt based on company and user context.

        Args:
            company_id: Company identifier
            company_name: Company display name
            user_role: User's role
            permissions: User's permissions

        Returns:
            Configured PolicyPrompt
        """
        # Default rules that apply to all
        default_rules = [
            "Be concise and accurate in responses",
            "Verify data before making changes",
            "Log all significant operations",
            "Respect user permissions and role restrictions"
        ]

        # Role-based constraints
        constraints = []
        if user_role == "operator":
            constraints = [
                "Cannot modify system configuration",
                "Can only control assigned equipment",
                "Must escalate critical issues to supervisor"
            ]
        elif user_role == "supervisor":
            constraints = [
                "Can approve operator actions",
                "Can modify non-critical settings",
                "Must document all configuration changes"
            ]
        elif user_role == "admin":
            constraints = [
                "Full system access",
                "Must maintain audit trail",
                "Responsible for data integrity"
            ]

        return PolicyPrompt(
            company_id=company_id,
            company_name=company_name,
            rules=default_rules,
            constraints=constraints,
            permissions=permissions,
            data_handling="Handle all data according to company security policy. "
                         "Do not expose sensitive information in responses."
        )

    def create_task_prompt(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        intent: Optional[str] = None,
        entities: Optional[Dict[str, Any]] = None
    ) -> TaskPrompt:
        """
        Create a task prompt from user input.

        Args:
            user_message: Current user message
            conversation_history: Previous conversation messages
            intent: Classified intent (optional)
            entities: Extracted entities (optional)

        Returns:
            Configured TaskPrompt
        """
        return TaskPrompt(
            user_message=user_message,
            conversation_history=conversation_history or [],
            intent=intent,
            extracted_entities=entities or {}
        )

    def list_domains(self) -> List[str]:
        """List available domain templates"""
        return list(self._domain_templates.keys())

    def get_prompt_statistics(self) -> Dict[str, Any]:
        """Get service statistics"""
        return {
            "registered_domains": len(self._domain_templates),
            "domain_names": list(self._domain_templates.keys()),
            "policy_templates": len(self._policy_templates)
        }
