"""
Memory Contracts - Memory System Data Models

CLAUDE.md COMPLIANT:
- Structured memory storage contracts
- Immutable memory entries
- Strong typing for graph operations
- Clear relationship definitions
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from uuid import uuid4

from .base_types import AgentResult


class MemoryType(str, Enum):
    """Types of memory storage"""
    CONVERSATION = "conversation"
    USER_PROFILE = "user_profile"
    TOOL_USAGE = "tool_usage"
    WORKFLOW_HISTORY = "workflow_history"
    KNOWLEDGE_BASE = "knowledge_base"
    PREFERENCES = "preferences"


class EntityType(str, Enum):
    """Graph entity types"""
    USER = "user"
    CONVERSATION = "conversation"
    TOOL = "tool"
    WORKFLOW = "workflow"
    DOCUMENT = "document"
    CONCEPT = "concept"


class RelationType(str, Enum):
    """Graph relationship types"""
    OWNS = "owns"
    USES = "uses"
    CONTAINS = "contains"
    REFERENCES = "references"
    DEPENDS_ON = "depends_on"
    SIMILAR_TO = "similar_to"
    FOLLOWS = "follows"


class MemoryEntry(BaseModel):
    """Individual memory storage entry"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    memory_type: MemoryType
    user_id: str
    content: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)
    
    def is_expired(self) -> bool:
        """Check if memory entry is expired"""
        if self.expires_at:
            return datetime.now() > self.expires_at
        return False

    class Config:
        frozen = True


class GraphEntity(BaseModel):
    """Knowledge graph entity"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    entity_type: EntityType
    properties: Dict[str, Any] = Field(default_factory=dict)
    observations: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    user_id: Optional[str] = None

    class Config:
        frozen = True


class GraphRelationship(BaseModel):
    """Knowledge graph relationship"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    from_entity_id: str
    to_entity_id: str
    relation_type: RelationType
    properties: Dict[str, Any] = Field(default_factory=dict)
    weight: float = 1.0
    created_at: datetime = Field(default_factory=datetime.now)
    user_id: Optional[str] = None

    class Config:
        frozen = True


class ConversationMemory(BaseModel):
    """Conversation-specific memory"""
    conversation_id: str
    user_id: str
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    context_summary: Optional[str] = None
    key_topics: List[str] = Field(default_factory=list)
    mentioned_entities: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        frozen = False


class MemoryQuery(BaseModel):
    """Query for memory retrieval"""
    user_id: str
    memory_types: Optional[List[MemoryType]] = None
    search_text: Optional[str] = None
    tags: Optional[List[str]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    limit: int = 10
    offset: int = 0

    class Config:
        frozen = True


class MemorySearchResult(BaseModel):
    """Result of memory search"""
    entries: List[MemoryEntry]
    total_count: int
    query: MemoryQuery
    search_time_ms: float

    class Config:
        frozen = True


class GraphQuery(BaseModel):
    """Query for graph operations"""
    user_id: Optional[str] = None
    entity_types: Optional[List[EntityType]] = None
    relation_types: Optional[List[RelationType]] = None
    search_text: Optional[str] = None
    max_depth: int = 2
    limit: int = 50

    class Config:
        frozen = True


class GraphSearchResult(BaseModel):
    """Result of graph search"""
    entities: List[GraphEntity]
    relationships: List[GraphRelationship]
    total_entities: int
    total_relationships: int
    query: GraphQuery
    search_time_ms: float

    class Config:
        frozen = True


class MemoryInsight(BaseModel):
    """Generated insight from memory analysis"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    insight_type: str
    title: str
    description: str
    confidence: float
    supporting_entries: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = True