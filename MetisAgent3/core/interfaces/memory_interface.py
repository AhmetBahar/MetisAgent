"""
Memory System Interfaces - Abstract Base Classes

CLAUDE.md COMPLIANT:
- Pure abstract memory contracts
- Graph-based knowledge storage
- Conversation context management
- No implementation dependencies
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncIterator
from datetime import datetime

from ..contracts import (
    MemoryEntry,
    MemoryQuery,
    MemorySearchResult,
    GraphEntity,
    GraphRelationship,
    GraphQuery,
    GraphSearchResult,
    ConversationMemory,
    MemoryInsight,
    ExecutionContext
)


class IMemoryService(ABC):
    """Abstract interface for memory management"""
    
    @abstractmethod
    async def store_memory(self, entry: MemoryEntry) -> str:
        """Store memory entry"""
        pass
    
    @abstractmethod
    async def retrieve_memory(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve memory entry by ID"""
        pass
    
    @abstractmethod
    async def search_memories(self, query: MemoryQuery) -> MemorySearchResult:
        """Search memories with query"""
        pass
    
    @abstractmethod
    async def update_memory(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update memory entry"""
        pass
    
    @abstractmethod
    async def delete_memory(self, entry_id: str) -> bool:
        """Delete memory entry"""
        pass
    
    @abstractmethod
    async def cleanup_expired_memories(self) -> int:
        """Clean up expired memory entries"""
        pass


class IGraphService(ABC):
    """Abstract interface for knowledge graph operations"""
    
    @abstractmethod
    async def create_entity(self, entity: GraphEntity) -> str:
        """Create knowledge graph entity"""
        pass
    
    @abstractmethod
    async def get_entity(self, entity_id: str) -> Optional[GraphEntity]:
        """Get entity by ID"""
        pass
    
    @abstractmethod
    async def update_entity(self, entity_id: str, updates: Dict[str, Any]) -> bool:
        """Update entity properties"""
        pass
    
    @abstractmethod
    async def delete_entity(self, entity_id: str) -> bool:
        """Delete entity and its relationships"""
        pass
    
    @abstractmethod
    async def create_relationship(self, relationship: GraphRelationship) -> str:
        """Create relationship between entities"""
        pass
    
    @abstractmethod
    async def get_relationships(self, entity_id: str) -> List[GraphRelationship]:
        """Get all relationships for an entity"""
        pass
    
    @abstractmethod
    async def delete_relationship(self, relationship_id: str) -> bool:
        """Delete specific relationship"""
        pass
    
    @abstractmethod
    async def search_graph(self, query: GraphQuery) -> GraphSearchResult:
        """Search knowledge graph"""
        pass
    
    @abstractmethod
    async def traverse_graph(self, start_entity_id: str, max_depth: int = 3) -> Dict[str, Any]:
        """Traverse graph from starting entity"""
        pass


class IConversationService(ABC):
    """Abstract interface for conversation memory"""
    
    @abstractmethod
    async def create_conversation(self, user_id: str, title: Optional[str] = None) -> str:
        """Create new conversation context"""
        pass
    
    @abstractmethod
    async def get_conversation(self, conversation_id: str) -> Optional[ConversationMemory]:
        """Get conversation by ID"""
        pass
    
    @abstractmethod
    async def add_message(self, conversation_id: str, message: Dict[str, Any]) -> bool:
        """Add message to conversation"""
        pass
    
    @abstractmethod
    async def update_conversation_summary(self, conversation_id: str, summary: str) -> bool:
        """Update conversation summary"""
        pass
    
    @abstractmethod
    async def get_conversation_history(self, user_id: str, limit: int = 10) -> List[ConversationMemory]:
        """Get user's conversation history"""
        pass
    
    @abstractmethod
    async def search_conversations(self, user_id: str, search_text: str) -> List[ConversationMemory]:
        """Search conversations by content"""
        pass
    
    @abstractmethod
    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete conversation and its memory"""
        pass


class IMemoryInsights(ABC):
    """Abstract interface for memory analytics and insights"""
    
    @abstractmethod
    async def generate_insights(self, user_id: str, context: ExecutionContext) -> List[MemoryInsight]:
        """Generate insights from user's memory"""
        pass
    
    @abstractmethod
    async def find_patterns(self, user_id: str, pattern_type: str) -> List[Dict[str, Any]]:
        """Find patterns in user behavior/memory"""
        pass
    
    @abstractmethod
    async def suggest_actions(self, user_id: str) -> List[str]:
        """Suggest actions based on memory analysis"""
        pass
    
    @abstractmethod
    async def analyze_topics(self, user_id: str) -> Dict[str, float]:
        """Analyze topic frequency in user's memory"""
        pass
    
    @abstractmethod
    async def identify_expertise(self, user_id: str) -> List[str]:
        """Identify user's areas of expertise"""
        pass


class IMemoryCompression(ABC):
    """Abstract interface for memory compression and optimization"""
    
    @abstractmethod
    async def compress_old_memories(self, cutoff_date: datetime) -> int:
        """Compress old memories to save space"""
        pass
    
    @abstractmethod
    async def summarize_conversations(self, conversation_ids: List[str]) -> Dict[str, str]:
        """Summarize conversations for compression"""
        pass
    
    @abstractmethod
    async def merge_similar_memories(self, user_id: str, similarity_threshold: float = 0.8) -> int:
        """Merge similar memory entries"""
        pass
    
    @abstractmethod
    async def archive_inactive_memories(self, inactive_days: int = 90) -> int:
        """Archive memories not accessed recently"""
        pass


class IMemorySync(ABC):
    """Abstract interface for memory synchronization"""
    
    @abstractmethod
    async def sync_to_external_store(self, user_id: str, store_config: Dict[str, Any]) -> bool:
        """Sync user memory to external storage"""
        pass
    
    @abstractmethod
    async def import_from_external_store(self, user_id: str, store_config: Dict[str, Any]) -> int:
        """Import memory from external storage"""
        pass
    
    @abstractmethod
    async def backup_user_memory(self, user_id: str) -> str:
        """Create backup of user's memory"""
        pass
    
    @abstractmethod
    async def restore_user_memory(self, user_id: str, backup_id: str) -> bool:
        """Restore user memory from backup"""
        pass