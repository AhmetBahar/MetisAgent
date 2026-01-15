"""
Persona Service - SQLite-Based Persona Management

Provides persistent persona management with:
- Create/Read/Update/Delete personas
- Persona status tracking
- Task execution history
- Persona configuration management
"""

import sqlite3
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
import uuid

logger = logging.getLogger(__name__)


@dataclass
class Persona:
    """Persona definition"""
    id: str
    name: str
    description: str
    avatar: str
    status: str  # active, inactive, busy
    capabilities: List[str]
    config: Dict[str, Any]
    user_id: str
    created_at: datetime
    updated_at: datetime
    last_active_at: Optional[datetime] = None
    task_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "avatar": self.avatar,
            "status": self.status,
            "capabilities": self.capabilities,
            "config": self.config,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None,
            "task_count": self.task_count
        }


@dataclass
class PersonaTask:
    """Task executed by a persona"""
    id: str
    persona_id: str
    user_id: str
    task_type: str
    task_data: Dict[str, Any]
    status: str  # pending, running, completed, failed
    result: Optional[Dict[str, Any]]
    created_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "persona_id": self.persona_id,
            "user_id": self.user_id,
            "task_type": self.task_type,
            "task_data": self.task_data,
            "status": self.status,
            "result": self.result,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error
        }


class PersonaService:
    """SQLite-based persona management service"""

    def __init__(self, db_path: str = "metis_agent3.db"):
        self.db_path = Path(db_path)
        self._init_database()
        self._ensure_default_personas()
        logger.info(f"Persona service initialized: {self.db_path}")

    def _init_database(self):
        """Initialize persona database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create personas table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS personas (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                avatar TEXT DEFAULT '🤖',
                status TEXT DEFAULT 'inactive',
                capabilities TEXT,  -- JSON array
                config TEXT,        -- JSON object
                user_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active_at TIMESTAMP,
                task_count INTEGER DEFAULT 0
            )
        """)

        # Create persona tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS persona_tasks (
                id TEXT PRIMARY KEY,
                persona_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                task_type TEXT,
                task_data TEXT,     -- JSON object
                status TEXT DEFAULT 'pending',
                result TEXT,        -- JSON object
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                error TEXT,
                FOREIGN KEY (persona_id) REFERENCES personas(id)
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_personas_user_id ON personas(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_personas_status ON personas(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_persona_tasks_persona_id ON persona_tasks(persona_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_persona_tasks_user_id ON persona_tasks(user_id)")

        conn.commit()
        conn.close()

    def _ensure_default_personas(self):
        """Create default system personas if they don't exist"""
        default_personas = [
            {
                "id": "assistant",
                "name": "AI Assistant",
                "description": "General purpose AI assistant for various tasks",
                "avatar": "🤖",
                "capabilities": ["chat", "code", "analysis", "planning"],
                "config": {"temperature": 0.7, "max_tokens": 4096, "model": "claude-3-opus"},
                "user_id": "system"
            },
            {
                "id": "social-media",
                "name": "Social Media Manager",
                "description": "AI assistant for social media content and management",
                "avatar": "📱",
                "capabilities": ["content_creation", "scheduling", "analytics"],
                "config": {"platforms": ["twitter", "linkedin", "instagram"], "auto_post": False},
                "user_id": "system"
            },
            {
                "id": "developer",
                "name": "Developer Assistant",
                "description": "AI assistant for software development tasks",
                "avatar": "👨‍💻",
                "capabilities": ["code_review", "debugging", "documentation"],
                "config": {"languages": ["python", "javascript", "csharp"], "auto_test": True},
                "user_id": "system"
            }
        ]

        for persona_data in default_personas:
            existing = self.get_persona(persona_data["id"])
            if not existing:
                self.create_persona(
                    persona_id=persona_data["id"],
                    name=persona_data["name"],
                    description=persona_data["description"],
                    avatar=persona_data["avatar"],
                    capabilities=persona_data["capabilities"],
                    config=persona_data["config"],
                    user_id=persona_data["user_id"]
                )

    def create_persona(
        self,
        name: str,
        user_id: str,
        persona_id: Optional[str] = None,
        description: str = "",
        avatar: str = "🤖",
        capabilities: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Persona:
        """Create a new persona"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            pid = persona_id or str(uuid.uuid4())[:8]
            now = datetime.now()

            cursor.execute("""
                INSERT INTO personas (id, name, description, avatar, status, capabilities, config, user_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'inactive', ?, ?, ?, ?, ?)
            """, (
                pid,
                name,
                description,
                avatar,
                json.dumps(capabilities or []),
                json.dumps(config or {}),
                user_id,
                now,
                now
            ))

            conn.commit()

            persona = Persona(
                id=pid,
                name=name,
                description=description,
                avatar=avatar,
                status="inactive",
                capabilities=capabilities or [],
                config=config or {},
                user_id=user_id,
                created_at=now,
                updated_at=now,
                last_active_at=None,
                task_count=0
            )

            logger.info(f"Created persona: {pid} ({name})")
            return persona

        finally:
            conn.close()

    def get_persona(self, persona_id: str) -> Optional[Persona]:
        """Get a persona by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, name, description, avatar, status, capabilities, config,
                       user_id, created_at, updated_at, last_active_at, task_count
                FROM personas WHERE id = ?
            """, (persona_id,))

            row = cursor.fetchone()
            if row:
                return Persona(
                    id=row[0],
                    name=row[1],
                    description=row[2] or "",
                    avatar=row[3] or "🤖",
                    status=row[4] or "inactive",
                    capabilities=json.loads(row[5]) if row[5] else [],
                    config=json.loads(row[6]) if row[6] else {},
                    user_id=row[7],
                    created_at=datetime.fromisoformat(row[8]) if row[8] else datetime.now(),
                    updated_at=datetime.fromisoformat(row[9]) if row[9] else datetime.now(),
                    last_active_at=datetime.fromisoformat(row[10]) if row[10] else None,
                    task_count=row[11] or 0
                )
            return None

        finally:
            conn.close()

    def get_all_personas(self, user_id: Optional[str] = None) -> List[Persona]:
        """Get all personas, optionally filtered by user_id"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            if user_id:
                # Get user's personas + system personas
                cursor.execute("""
                    SELECT id, name, description, avatar, status, capabilities, config,
                           user_id, created_at, updated_at, last_active_at, task_count
                    FROM personas
                    WHERE user_id = ? OR user_id = 'system'
                    ORDER BY created_at DESC
                """, (user_id,))
            else:
                cursor.execute("""
                    SELECT id, name, description, avatar, status, capabilities, config,
                           user_id, created_at, updated_at, last_active_at, task_count
                    FROM personas ORDER BY created_at DESC
                """)

            personas = []
            for row in cursor.fetchall():
                personas.append(Persona(
                    id=row[0],
                    name=row[1],
                    description=row[2] or "",
                    avatar=row[3] or "🤖",
                    status=row[4] or "inactive",
                    capabilities=json.loads(row[5]) if row[5] else [],
                    config=json.loads(row[6]) if row[6] else {},
                    user_id=row[7],
                    created_at=datetime.fromisoformat(row[8]) if row[8] else datetime.now(),
                    updated_at=datetime.fromisoformat(row[9]) if row[9] else datetime.now(),
                    last_active_at=datetime.fromisoformat(row[10]) if row[10] else None,
                    task_count=row[11] or 0
                ))

            return personas

        finally:
            conn.close()

    def update_persona(
        self,
        persona_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        avatar: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Optional[Persona]:
        """Update persona fields"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Build update query dynamically
            updates = []
            params = []

            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            if avatar is not None:
                updates.append("avatar = ?")
                params.append(avatar)
            if capabilities is not None:
                updates.append("capabilities = ?")
                params.append(json.dumps(capabilities))
            if config is not None:
                updates.append("config = ?")
                params.append(json.dumps(config))

            if not updates:
                return self.get_persona(persona_id)

            updates.append("updated_at = ?")
            params.append(datetime.now())
            params.append(persona_id)

            query = f"UPDATE personas SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()

            logger.info(f"Updated persona: {persona_id}")
            return self.get_persona(persona_id)

        finally:
            conn.close()

    def delete_persona(self, persona_id: str) -> bool:
        """Delete a persona"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Don't allow deleting system personas
            cursor.execute("SELECT user_id FROM personas WHERE id = ?", (persona_id,))
            row = cursor.fetchone()
            if row and row[0] == "system":
                logger.warning(f"Cannot delete system persona: {persona_id}")
                return False

            cursor.execute("DELETE FROM persona_tasks WHERE persona_id = ?", (persona_id,))
            cursor.execute("DELETE FROM personas WHERE id = ?", (persona_id,))
            conn.commit()

            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"Deleted persona: {persona_id}")
            return deleted

        finally:
            conn.close()

    def set_persona_status(self, persona_id: str, status: str) -> Optional[Persona]:
        """Set persona status (active, inactive, busy)"""
        if status not in ["active", "inactive", "busy"]:
            logger.error(f"Invalid status: {status}")
            return None

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            now = datetime.now()
            cursor.execute("""
                UPDATE personas
                SET status = ?, updated_at = ?, last_active_at = ?
                WHERE id = ?
            """, (status, now, now if status == "active" else None, persona_id))
            conn.commit()

            logger.info(f"Set persona {persona_id} status to {status}")
            return self.get_persona(persona_id)

        finally:
            conn.close()

    def get_persona_status(self, persona_id: str) -> Optional[Dict[str, Any]]:
        """Get persona status info"""
        persona = self.get_persona(persona_id)
        if not persona:
            return None

        return {
            "id": persona.id,
            "status": persona.status,
            "last_active_at": persona.last_active_at.isoformat() if persona.last_active_at else None,
            "task_count": persona.task_count
        }

    def create_task(
        self,
        persona_id: str,
        user_id: str,
        task_type: str,
        task_data: Dict[str, Any]
    ) -> PersonaTask:
        """Create a new task for a persona"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            task_id = str(uuid.uuid4())[:12]
            now = datetime.now()

            cursor.execute("""
                INSERT INTO persona_tasks (id, persona_id, user_id, task_type, task_data, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'pending', ?)
            """, (task_id, persona_id, user_id, task_type, json.dumps(task_data), now))

            # Update persona task count and last active
            cursor.execute("""
                UPDATE personas
                SET task_count = task_count + 1, last_active_at = ?, updated_at = ?
                WHERE id = ?
            """, (now, now, persona_id))

            conn.commit()

            task = PersonaTask(
                id=task_id,
                persona_id=persona_id,
                user_id=user_id,
                task_type=task_type,
                task_data=task_data,
                status="pending",
                result=None,
                created_at=now,
                completed_at=None,
                error=None
            )

            logger.info(f"Created task {task_id} for persona {persona_id}")
            return task

        finally:
            conn.close()

    def update_task(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> Optional[PersonaTask]:
        """Update task status and result"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            now = datetime.now()
            completed_at = now if status in ["completed", "failed"] else None

            cursor.execute("""
                UPDATE persona_tasks
                SET status = ?, result = ?, error = ?, completed_at = ?
                WHERE id = ?
            """, (status, json.dumps(result) if result else None, error, completed_at, task_id))

            conn.commit()

            # Fetch and return the updated task
            cursor.execute("""
                SELECT id, persona_id, user_id, task_type, task_data, status, result, created_at, completed_at, error
                FROM persona_tasks WHERE id = ?
            """, (task_id,))

            row = cursor.fetchone()
            if row:
                return PersonaTask(
                    id=row[0],
                    persona_id=row[1],
                    user_id=row[2],
                    task_type=row[3],
                    task_data=json.loads(row[4]) if row[4] else {},
                    status=row[5],
                    result=json.loads(row[6]) if row[6] else None,
                    created_at=datetime.fromisoformat(row[7]) if row[7] else datetime.now(),
                    completed_at=datetime.fromisoformat(row[8]) if row[8] else None,
                    error=row[9]
                )
            return None

        finally:
            conn.close()

    def get_persona_tasks(
        self,
        persona_id: str,
        limit: int = 50,
        status: Optional[str] = None
    ) -> List[PersonaTask]:
        """Get tasks for a persona"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            if status:
                cursor.execute("""
                    SELECT id, persona_id, user_id, task_type, task_data, status, result, created_at, completed_at, error
                    FROM persona_tasks
                    WHERE persona_id = ? AND status = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (persona_id, status, limit))
            else:
                cursor.execute("""
                    SELECT id, persona_id, user_id, task_type, task_data, status, result, created_at, completed_at, error
                    FROM persona_tasks
                    WHERE persona_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (persona_id, limit))

            tasks = []
            for row in cursor.fetchall():
                tasks.append(PersonaTask(
                    id=row[0],
                    persona_id=row[1],
                    user_id=row[2],
                    task_type=row[3],
                    task_data=json.loads(row[4]) if row[4] else {},
                    status=row[5],
                    result=json.loads(row[6]) if row[6] else None,
                    created_at=datetime.fromisoformat(row[7]) if row[7] else datetime.now(),
                    completed_at=datetime.fromisoformat(row[8]) if row[8] else None,
                    error=row[9]
                ))

            return tasks

        finally:
            conn.close()
