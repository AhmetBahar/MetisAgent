"""
Conversation Memory Service - Lightweight context tracking for LLM calls

Instead of sending full conversation history to LLM (which causes context_length_exceeded),
this service maintains a concise summary of the conversation context.

Key features:
- Maintains conversation summary (not full messages)
- Tracks key entities mentioned (company_id, page_id, etc.)
- Updates after each turn with LLM summarization
- Provides context for unified_plan_request without token overflow
"""

import json
import logging
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ConversationMemoryService:
    """Service for managing lightweight conversation memory/context"""

    def __init__(self, db_path: str = "conversation_memory.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database for conversation memory"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                context_summary TEXT DEFAULT '',
                key_entities TEXT DEFAULT '{}',
                key_topics TEXT DEFAULT '[]',
                last_user_intent TEXT DEFAULT '',
                turn_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(conversation_id, user_id)
            )
        """)

        conn.commit()
        conn.close()
        logger.info("Conversation memory service initialized")

    async def get_memory(self, conversation_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation memory for a specific conversation"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT context_summary, key_entities, key_topics, last_user_intent, turn_count
                FROM conversation_memory
                WHERE conversation_id = ? AND user_id = ?
            """, (conversation_id, user_id))

            row = cursor.fetchone()
            conn.close()

            if row:
                return {
                    "context_summary": row[0] or "",
                    "key_entities": json.loads(row[1]) if row[1] else {},
                    "key_topics": json.loads(row[2]) if row[2] else [],
                    "last_user_intent": row[3] or "",
                    "turn_count": row[4] or 0
                }
            return None

        except Exception as e:
            logger.error(f"Failed to get conversation memory: {e}")
            return None

    async def update_memory(
        self,
        conversation_id: str,
        user_id: str,
        user_message: str,
        assistant_response: str,
        extracted_entities: Optional[Dict[str, Any]] = None,
        topics: Optional[List[str]] = None,
        llm_service = None
    ) -> bool:
        """Update conversation memory after a turn"""
        try:
            # Get existing memory
            existing = await self.get_memory(conversation_id, user_id)

            if existing:
                # Update existing memory
                new_summary = await self._generate_updated_summary(
                    existing["context_summary"],
                    user_message,
                    assistant_response,
                    llm_service
                )

                # Merge entities
                merged_entities = existing["key_entities"].copy()
                if extracted_entities:
                    merged_entities.update(extracted_entities)

                # Merge topics (keep last 5)
                merged_topics = existing["key_topics"] + (topics or [])
                merged_topics = list(dict.fromkeys(merged_topics))[-5:]  # Unique, last 5

                turn_count = existing["turn_count"] + 1
            else:
                # Create new memory
                new_summary = await self._generate_initial_summary(
                    user_message,
                    assistant_response,
                    llm_service
                )
                merged_entities = extracted_entities or {}
                merged_topics = topics or []
                turn_count = 1

            # Extract user intent from message
            user_intent = self._extract_user_intent(user_message)

            # Save to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO conversation_memory
                (conversation_id, user_id, context_summary, key_entities, key_topics, last_user_intent, turn_count, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(conversation_id, user_id) DO UPDATE SET
                    context_summary = excluded.context_summary,
                    key_entities = excluded.key_entities,
                    key_topics = excluded.key_topics,
                    last_user_intent = excluded.last_user_intent,
                    turn_count = excluded.turn_count,
                    updated_at = excluded.updated_at
            """, (
                conversation_id,
                user_id,
                new_summary,
                json.dumps(merged_entities, ensure_ascii=False),
                json.dumps(merged_topics, ensure_ascii=False),
                user_intent,
                turn_count,
                datetime.now().isoformat()
            ))

            conn.commit()
            conn.close()

            logger.info(f"📝 Updated conversation memory for {conversation_id}: {turn_count} turns")
            return True

        except Exception as e:
            logger.error(f"Failed to update conversation memory: {e}")
            return False

    async def _generate_updated_summary(
        self,
        existing_summary: str,
        user_message: str,
        assistant_response: str,
        llm_service
    ) -> str:
        """Generate updated summary using LLM"""
        if not llm_service:
            # Fallback: simple concatenation
            return self._simple_summary_update(existing_summary, user_message, assistant_response)

        try:
            summary_prompt = f"""Update this conversation summary with the new exchange.

CURRENT SUMMARY:
{existing_summary if existing_summary else "No previous context."}

NEW USER MESSAGE:
{user_message[:500]}

NEW ASSISTANT RESPONSE:
{assistant_response[:500]}

Write a brief updated summary (max 200 words) that captures:
1. What the user is trying to accomplish
2. Key information discussed (IDs, names, values)
3. What was resolved vs still pending

Updated summary:"""

            # Use a lightweight model for summarization
            response = await llm_service.generate_text(
                prompt=summary_prompt,
                max_tokens=300,
                provider="openai",
                model="gpt-4o-mini"
            )

            return response.strip() if response else self._simple_summary_update(existing_summary, user_message, assistant_response)

        except Exception as e:
            logger.warning(f"LLM summary generation failed, using simple update: {e}")
            return self._simple_summary_update(existing_summary, user_message, assistant_response)

    async def _generate_initial_summary(
        self,
        user_message: str,
        assistant_response: str,
        llm_service
    ) -> str:
        """Generate initial summary for new conversation"""
        if not llm_service:
            return f"User asked: {user_message[:200]}. Response provided about: {assistant_response[:200]}"

        try:
            summary_prompt = f"""Summarize this conversation exchange briefly.

USER: {user_message[:500]}

ASSISTANT: {assistant_response[:500]}

Write a brief summary (max 100 words) capturing the key points:"""

            response = await llm_service.generate_text(
                prompt=summary_prompt,
                max_tokens=150,
                provider="openai",
                model="gpt-4o-mini"
            )

            return response.strip() if response else f"User asked about: {user_message[:100]}"

        except Exception as e:
            logger.warning(f"LLM initial summary failed: {e}")
            return f"User asked about: {user_message[:100]}"

    def _simple_summary_update(self, existing: str, user_msg: str, asst_resp: str) -> str:
        """Simple summary update without LLM"""
        user_part = user_msg[:150] if len(user_msg) > 150 else user_msg
        resp_part = asst_resp[:150] if len(asst_resp) > 150 else asst_resp

        if existing:
            # Keep last part of existing + new
            existing_trimmed = existing[-300:] if len(existing) > 300 else existing
            return f"{existing_trimmed} | Latest: User asked '{user_part}', got response about '{resp_part}'"
        return f"User asked '{user_part}', got response about '{resp_part}'"

    def _extract_user_intent(self, message: str) -> str:
        """Extract simple user intent from message"""
        message_lower = message.lower()

        if any(q in message_lower for q in ["nedir", "ne", "kaç", "hangi", "kim"]):
            return "question"
        elif any(a in message_lower for a in ["yap", "oluştur", "ekle", "sil", "güncelle"]):
            return "action"
        elif any(l in message_lower for l in ["listele", "göster", "getir"]):
            return "list"
        else:
            return "general"

    async def get_context_for_llm(self, conversation_id: str, user_id: str) -> str:
        """Get formatted context string for LLM prompt"""
        memory = await self.get_memory(conversation_id, user_id)

        if not memory or not memory["context_summary"]:
            return ""

        context_parts = []

        # Add summary
        if memory["context_summary"]:
            context_parts.append(f"CONVERSATION CONTEXT:\n{memory['context_summary']}")

        # Add key entities
        if memory["key_entities"]:
            entities_str = ", ".join([f"{k}={v}" for k, v in memory["key_entities"].items()])
            context_parts.append(f"KEY ENTITIES: {entities_str}")

        # Add topics
        if memory["key_topics"]:
            context_parts.append(f"TOPICS DISCUSSED: {', '.join(memory['key_topics'])}")

        return "\n".join(context_parts) + "\n\n" if context_parts else ""

    async def extract_entities_from_response(self, response: str, tool_results: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract key entities from response and tool results"""
        entities = {}

        # Extract from tool results if available
        if tool_results:
            for step_id, result in tool_results.items():
                if isinstance(result, dict):
                    # Look for common ID fields
                    for key in ["companyId", "company_id", "pageId", "page_id", "id", "name"]:
                        if key in result:
                            entities[key] = result[key]

                    # Handle list results (get first item's IDs)
                    for key, value in result.items():
                        if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                            # Store count and sample
                            entities[f"{key}_count"] = len(value)

        return entities

    async def clear_memory(self, conversation_id: str, user_id: str) -> bool:
        """Clear memory for a conversation"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM conversation_memory
                WHERE conversation_id = ? AND user_id = ?
            """, (conversation_id, user_id))

            conn.commit()
            conn.close()

            logger.info(f"Cleared conversation memory for {conversation_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to clear conversation memory: {e}")
            return False
