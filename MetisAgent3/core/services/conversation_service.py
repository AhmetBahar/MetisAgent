"""
Conversation Service - SQLite-Based Conversation Persistence and Search

CLAUDE.md COMPLIANT:
- SQLite-based conversation history storage
- Full-text search in conversation content  
- User-isolated conversation management
- Context retrieval for LLM prompts
- Conversation analytics and insights
"""

import sqlite3
import json
import logging
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass
import uuid

from ..contracts.base_types import AgentResult

logger = logging.getLogger(__name__)


@dataclass
class ConversationMessage:
    """Individual message in a conversation"""
    id: str
    conversation_id: str
    user_id: str
    role: str  # user, assistant, system
    content: str
    metadata: Dict[str, Any]
    created_at: datetime
    token_count: Optional[int] = None


@dataclass
class ConversationThread:
    """Conversation thread metadata"""
    id: str
    user_id: str
    title: str
    summary: Optional[str]
    total_messages: int
    total_tokens: int
    first_message_at: datetime
    last_message_at: datetime
    metadata: Dict[str, Any]
    tags: List[str]


@dataclass
class ConversationSearchResult:
    """Search result for conversations"""
    conversation_id: str
    message_id: str
    role: str
    content_snippet: str
    relevance_score: float
    created_at: datetime
    context_before: List[str]
    context_after: List[str]


class ConversationService:
    """SQLite-based conversation persistence and search service"""
    
    def __init__(self, db_path: str = "conversations.db"):
        self.db_path = Path(db_path)
        self._init_database()
        logger.info(f"Conversation service initialized: {self.db_path}")
    
    def _init_database(self):
        """Initialize conversation database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT,
                total_messages INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                first_message_at TIMESTAMP,
                last_message_at TIMESTAMP,
                metadata TEXT,  -- JSON
                tags TEXT,      -- JSON array
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for conversations
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_last_message_at ON conversations(last_message_at)")
        
        # Create messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,  -- user, assistant, system
                content TEXT NOT NULL,
                metadata TEXT,       -- JSON
                token_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(conversation_id) REFERENCES conversations(id)
            )
        """)
        
        # Create indexes for messages
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at)")
        
        # Create full-text search index
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                content,
                content_id UNINDEXED
            )
        """)
        
        # Create conversation analytics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_analytics (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                date DATE NOT NULL,
                message_count INTEGER DEFAULT 0,
                token_count INTEGER DEFAULT 0,
                avg_response_time REAL DEFAULT 0.0,
                topics TEXT,  -- JSON array of detected topics
                sentiment_score REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(conversation_id) REFERENCES conversations(id)
            )
        """)
        
        # Create indexes for analytics
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_analytics_user_id_date ON conversation_analytics(user_id, date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_analytics_conversation_id ON conversation_analytics(conversation_id)")
        
        conn.commit()
        conn.close()
    
    async def create_conversation(
        self, 
        user_id: str, 
        title: str, 
        initial_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        conversation_id: Optional[str] = None
    ) -> str:
        """Create new conversation thread"""
        conversation_id = conversation_id or str(uuid.uuid4())
        now = datetime.utcnow()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Insert conversation (OR IGNORE to handle duplicate IDs)
            cursor.execute("""
                INSERT OR IGNORE INTO conversations
                (id, user_id, title, metadata, tags, first_message_at, last_message_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                conversation_id,
                user_id,
                title,
                json.dumps(metadata or {}),
                json.dumps(tags or []),
                now.isoformat(),
                now.isoformat()
            ))
            
            # Add initial message if provided
            if initial_message:
                await self._add_message_internal(
                    cursor, conversation_id, user_id, "user", initial_message, {}
                )
            
            conn.commit()
            logger.info(f"Created conversation {conversation_id} for user {user_id}")
            return conversation_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create conversation: {e}")
            raise
        finally:
            conn.close()
    
    async def add_message(
        self,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        token_count: Optional[int] = None
    ) -> str:
        """Add message to conversation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            message_id = await self._add_message_internal(
                cursor, conversation_id, user_id, role, content, 
                metadata or {}, token_count
            )
            
            # Update conversation stats
            await self._update_conversation_stats(cursor, conversation_id)
            
            conn.commit()
            return message_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to add message: {e}")
            raise
        finally:
            conn.close()
    
    async def _add_message_internal(
        self,
        cursor,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        metadata: Dict[str, Any],
        token_count: Optional[int] = None
    ) -> str:
        """Internal method to add message (used within transactions)"""
        message_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        # Insert message
        cursor.execute("""
            INSERT INTO messages 
            (id, conversation_id, user_id, role, content, metadata, token_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            message_id, conversation_id, user_id, role, content, 
            json.dumps(metadata), token_count, now.isoformat()
        ))
        
        # Add to full-text search index
        cursor.execute("""
            INSERT INTO messages_fts (content, content_id) VALUES (?, ?)
        """, (content, message_id))
        
        return message_id
    
    async def _update_conversation_stats(self, cursor, conversation_id: str):
        """Update conversation statistics"""
        logger.info(f"📊 Updating conversation stats for: {conversation_id}")
        
        # First check current message count
        cursor.execute("SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (conversation_id,))
        message_count = cursor.fetchone()[0]
        logger.info(f"📊 Found {message_count} messages for conversation {conversation_id}")
        
        # Update message count and timestamps
        cursor.execute("""
            UPDATE conversations SET
                total_messages = (
                    SELECT COUNT(*) FROM messages WHERE conversation_id = ?
                ),
                total_tokens = (
                    SELECT COALESCE(SUM(token_count), 0) FROM messages 
                    WHERE conversation_id = ? AND token_count IS NOT NULL
                ),
                last_message_at = (
                    SELECT MAX(created_at) FROM messages WHERE conversation_id = ?
                ),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (conversation_id, conversation_id, conversation_id, conversation_id))
    
    async def get_conversation(self, conversation_id: str, user_id: str) -> Optional[ConversationThread]:
        """Get conversation metadata"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, user_id, title, summary, total_messages, total_tokens,
                   first_message_at, last_message_at, metadata, tags
            FROM conversations 
            WHERE id = ? AND user_id = ?
        """, (conversation_id, user_id))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
            
        return ConversationThread(
            id=row[0],
            user_id=row[1], 
            title=row[2],
            summary=row[3],
            total_messages=row[4],
            total_tokens=row[5],
            first_message_at=datetime.fromisoformat(row[6]),
            last_message_at=datetime.fromisoformat(row[7]),
            metadata=json.loads(row[8]) if row[8] else {},
            tags=json.loads(row[9]) if row[9] else []
        )
    
    async def get_messages(
        self, 
        conversation_id: str, 
        user_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
        role_filter: Optional[str] = None
    ) -> List[ConversationMessage]:
        """Get messages from conversation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
            SELECT id, conversation_id, user_id, role, content, metadata, token_count, created_at
            FROM messages 
            WHERE conversation_id = ? AND user_id = ?
        """
        params = [conversation_id, user_id]
        
        if role_filter:
            query += " AND role = ?"
            params.append(role_filter)
        
        query += " ORDER BY created_at ASC"
        
        if limit:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        messages = []
        for row in rows:
            messages.append(ConversationMessage(
                id=row[0],
                conversation_id=row[1],
                user_id=row[2],
                role=row[3],
                content=row[4],
                metadata=json.loads(row[5]) if row[5] else {},
                token_count=row[6],
                created_at=datetime.fromisoformat(row[7])
            ))
        
        return messages
    
    async def search_conversations(
        self,
        user_id: str,
        query: str,
        limit: int = 20,
        include_context: bool = True,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[ConversationSearchResult]:
        """Full-text search in user's conversations"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build search query
        search_query = """
            SELECT m.id, m.conversation_id, m.role, m.content, m.created_at,
                   c.title, rank
            FROM messages_fts f
            JOIN messages m ON f.content_id = m.id
            JOIN conversations c ON m.conversation_id = c.id
            WHERE f.content MATCH ? AND m.user_id = ?
        """
        params = [query, user_id]
        
        if date_from:
            search_query += " AND m.created_at >= ?"
            params.append(date_from.isoformat())
        
        if date_to:
            search_query += " AND m.created_at <= ?"
            params.append(date_to.isoformat())
        
        search_query += " ORDER BY rank LIMIT ?"
        params.append(limit)
        
        cursor.execute(search_query, params)
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            result = ConversationSearchResult(
                conversation_id=row[1],
                message_id=row[0],
                role=row[2],
                content_snippet=self._create_snippet(row[3], query),
                relevance_score=float(row[6]),
                created_at=datetime.fromisoformat(row[4]),
                context_before=[],
                context_after=[]
            )
            
            # Add context if requested
            if include_context:
                result.context_before, result.context_after = await self._get_message_context(
                    cursor, row[0], row[1], context_size=2
                )
            
            results.append(result)
        
        conn.close()
        return results
    
    async def _get_message_context(
        self, cursor, message_id: str, conversation_id: str, context_size: int = 2
    ) -> Tuple[List[str], List[str]]:
        """Get context messages before and after target message"""
        # Get message timestamp
        cursor.execute("""
            SELECT created_at FROM messages WHERE id = ?
        """, (message_id,))
        target_time = cursor.fetchone()[0]
        
        # Get context before
        cursor.execute("""
            SELECT content FROM messages 
            WHERE conversation_id = ? AND created_at < ? 
            ORDER BY created_at DESC LIMIT ?
        """, (conversation_id, target_time, context_size))
        context_before = [row[0] for row in cursor.fetchall()]
        context_before.reverse()  # Chronological order
        
        # Get context after  
        cursor.execute("""
            SELECT content FROM messages 
            WHERE conversation_id = ? AND created_at > ? 
            ORDER BY created_at ASC LIMIT ?
        """, (conversation_id, target_time, context_size))
        context_after = [row[0] for row in cursor.fetchall()]
        
        return context_before, context_after
    
    def _create_snippet(self, content: str, query: str, snippet_length: int = 200) -> str:
        """Create content snippet highlighting search terms"""
        # Simple snippet creation - can be enhanced with better highlighting
        if len(content) <= snippet_length:
            return content
        
        # Find query position
        query_lower = query.lower()
        content_lower = content.lower()
        pos = content_lower.find(query_lower)
        
        if pos == -1:
            return content[:snippet_length] + "..."
        
        # Center snippet around query
        start = max(0, pos - snippet_length // 2)
        end = min(len(content), start + snippet_length)
        
        snippet = content[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."
        
        return snippet
    
    async def list_conversations(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "last_message_at",  # created_at, title, message_count
        sort_order: str = "DESC"
    ) -> List[ConversationThread]:
        """List user's conversations"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        valid_sort_fields = {"created_at", "last_message_at", "title", "total_messages", "total_tokens"}
        if sort_by not in valid_sort_fields:
            sort_by = "last_message_at"
        
        sort_order = "ASC" if sort_order.upper() == "ASC" else "DESC"
        
        cursor.execute(f"""
            SELECT id, user_id, title, summary, total_messages, total_tokens,
                   first_message_at, last_message_at, metadata, tags
            FROM conversations 
            WHERE user_id = ?
            ORDER BY {sort_by} {sort_order}
            LIMIT ? OFFSET ?
        """, (user_id, limit, offset))
        
        rows = cursor.fetchall()
        conn.close()
        
        conversations = []
        for row in rows:
            conversations.append(ConversationThread(
                id=row[0],
                user_id=row[1],
                title=row[2], 
                summary=row[3],
                total_messages=row[4],
                total_tokens=row[5],
                first_message_at=datetime.fromisoformat(row[6]) if row[6] else datetime.utcnow(),
                last_message_at=datetime.fromisoformat(row[7]) if row[7] else datetime.utcnow(),
                metadata=json.loads(row[8]) if row[8] else {},
                tags=json.loads(row[9]) if row[9] else []
            ))
        
        return conversations
    
    async def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        """Delete conversation and all its messages"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Delete from FTS index first
            cursor.execute("""
                DELETE FROM messages_fts WHERE content_id IN (
                    SELECT id FROM messages WHERE conversation_id = ? AND user_id = ?
                )
            """, (conversation_id, user_id))
            
            # Delete messages
            cursor.execute("""
                DELETE FROM messages WHERE conversation_id = ? AND user_id = ?
            """, (conversation_id, user_id))
            
            # Delete conversation
            cursor.execute("""
                DELETE FROM conversations WHERE id = ? AND user_id = ?
            """, (conversation_id, user_id))
            
            # Delete analytics
            cursor.execute("""
                DELETE FROM conversation_analytics WHERE conversation_id = ? AND user_id = ?
            """, (conversation_id, user_id))
            
            deleted = cursor.rowcount > 0
            conn.commit()
            
            if deleted:
                logger.info(f"Deleted conversation {conversation_id} for user {user_id}")
            
            return deleted
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to delete conversation: {e}")
            raise
        finally:
            conn.close()
    
    async def get_conversation_context_for_llm(
        self,
        conversation_id: str,
        user_id: str,
        max_tokens: int = 4000,
        include_system: bool = True
    ) -> List[Dict[str, str]]:
        """Get conversation context optimized for LLM prompt

        IMPORTANT: This method properly limits token usage by:
        1. Truncating individual large messages (max 2000 chars each)
        2. Stopping when total limit is reached
        3. NOT adding messages that would exceed the limit (even if context is empty)
        """
        messages = await self.get_messages(conversation_id, user_id)

        # Build context with token estimation (rough: 1 token ≈ 4 chars)
        context = []
        total_chars = 0
        max_chars = max_tokens * 4  # ~16000 chars for 4000 tokens
        max_single_message = 2000  # Max chars per individual message

        # Add messages in reverse order, then reverse to get chronological
        for message in reversed(messages):
            if not include_system and message.role == "system":
                continue

            # Truncate individual large messages
            content = message.content
            if len(content) > max_single_message:
                content = content[:max_single_message] + "...[truncated]"

            content_chars = len(content)

            # FIXED: Always check limit, even for first message
            if total_chars + content_chars > max_chars:
                break

            context.append({
                "role": message.role,
                "content": content
            })
            total_chars += content_chars

        context.reverse()  # Chronological order
        return context
    
    async def update_conversation_summary(
        self, 
        conversation_id: str, 
        user_id: str, 
        summary: str
    ) -> bool:
        """Update conversation summary"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE conversations 
            SET summary = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
        """, (summary, conversation_id, user_id))
        
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return updated
    
    async def add_conversation_tags(
        self,
        conversation_id: str,
        user_id: str, 
        tags: List[str]
    ) -> bool:
        """Add tags to conversation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get existing tags
        cursor.execute("SELECT tags FROM conversations WHERE id = ? AND user_id = ?", 
                      (conversation_id, user_id))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return False
        
        existing_tags = json.loads(row[0]) if row[0] else []
        updated_tags = list(set(existing_tags + tags))
        
        cursor.execute("""
            UPDATE conversations 
            SET tags = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
        """, (json.dumps(updated_tags), conversation_id, user_id))
        
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return updated


# Integration helper for LLM Tool
class LLMConversationIntegration:
    """Helper class to integrate ConversationService with LLM Tool"""
    
    def __init__(self, conversation_service: ConversationService):
        self.conversation_service = conversation_service
    
    async def start_conversation(
        self,
        user_id: str,
        title: str,
        initial_message: str,
        provider: str,
        model: str,
        conversation_id: Optional[str] = None
    ) -> str:
        """Start new conversation with metadata"""
        metadata = {
            "provider": provider,
            "model": model,
            "started_at": datetime.utcnow().isoformat()
        }
        
        conversation_id = await self.conversation_service.create_conversation(
            user_id=user_id,
            title=title,
            initial_message=initial_message,
            metadata=metadata,
            tags=["llm", provider],
            conversation_id=conversation_id
        )
        
        return conversation_id
    
    async def continue_conversation(
        self,
        conversation_id: str,
        user_id: str,
        user_message: str,
        assistant_response: str,
        provider: str,
        model: str,
        usage: Dict[str, Any]
    ) -> None:
        """Add messages to existing conversation"""
        # Add user message
        await self.conversation_service.add_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role="user",
            content=user_message,
            token_count=usage.get("prompt_tokens", 0)
        )
        
        # Add assistant response
        await self.conversation_service.add_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role="assistant", 
            content=assistant_response,
            metadata={
                "provider": provider,
                "model": model,
                "usage": usage
            },
            token_count=usage.get("completion_tokens", 0)
        )
    
    async def get_recent_context(
        self,
        user_id: str,
        query_similarity: str,
        max_conversations: int = 5,
        max_tokens: int = 2000
    ) -> str:
        """Get relevant context from recent conversations"""
        # Search recent conversations
        search_results = await self.conversation_service.search_conversations(
            user_id=user_id,
            query=query_similarity,
            limit=max_conversations,
            include_context=True,
            date_from=datetime.utcnow() - timedelta(days=30)
        )
        
        if not search_results:
            return ""
        
        context_parts = []
        total_chars = 0
        max_chars = max_tokens * 4
        
        for result in search_results:
            snippet = f"Previous conversation context:\n{result.content_snippet}"
            if result.context_before:
                snippet = f"Context: {' '.join(result.context_before[-2:])}\n{snippet}"
            
            snippet_chars = len(snippet)
            if total_chars + snippet_chars > max_chars:
                break
                
            context_parts.append(snippet)
            total_chars += snippet_chars
        
        return "\n\n---\n\n".join(context_parts)
