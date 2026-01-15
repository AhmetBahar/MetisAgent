"""
Session Manager - Multi-tenant user session management
"""

import uuid
import logging
from typing import Dict, Optional, Set
from datetime import datetime, timedelta
import json
import threading

logger = logging.getLogger(__name__)

class UserSession:
    """Individual user session"""
    
    def __init__(self, user_id: str, session_id: str = None):
        self.user_id = user_id
        self.session_id = session_id or str(uuid.uuid4())
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.conversation_id = f"{user_id}_{self.session_id}"
        self.metadata = {}
        
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()
        
    def is_expired(self, timeout_minutes: int = 60) -> bool:
        """Check if session is expired"""
        expiry_time = self.last_activity + timedelta(minutes=timeout_minutes)
        return datetime.utcnow() > expiry_time
    
    def to_dict(self) -> Dict:
        """Convert session to dictionary"""
        return {
            'user_id': self.user_id,
            'session_id': self.session_id,
            'conversation_id': self.conversation_id,
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'metadata': self.metadata
        }

class SessionManager:
    """Manages user sessions for multi-tenant support"""
    
    def __init__(self):
        self.sessions: Dict[str, UserSession] = {}  # session_id -> UserSession
        self.user_sessions: Dict[str, Set[str]] = {}  # user_id -> set of session_ids
        self.lock = threading.Lock()
        
    def create_session(self, user_id: str, session_id: str = None) -> UserSession:
        """Create a new user session"""
        with self.lock:
            if not user_id:
                user_id = f"anonymous_{str(uuid.uuid4())[:8]}"
            
            session = UserSession(user_id, session_id)
            
            # Store session
            self.sessions[session.session_id] = session
            
            # Track user sessions
            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = set()
            self.user_sessions[user_id].add(session.session_id)
            
            logger.info(f"Created session {session.session_id} for user {user_id}")
            return session
    
    def get_session(self, session_id: str) -> Optional[UserSession]:
        """Get session by session ID"""
        with self.lock:
            session = self.sessions.get(session_id)
            if session and not session.is_expired():
                session.update_activity()
                return session
            elif session and session.is_expired():
                self.remove_session(session_id)
            return None
    
    def get_or_create_session(self, user_id: str, session_id: str = None) -> UserSession:
        """Get existing session or create new one"""
        if session_id:
            session = self.get_session(session_id)
            if session and session.user_id == user_id:
                return session
        
        # Create new session
        return self.create_session(user_id, session_id)
    
    def remove_session(self, session_id: str) -> bool:
        """Remove a session"""
        with self.lock:
            session = self.sessions.get(session_id)
            if session:
                # Remove from user sessions
                user_id = session.user_id
                if user_id in self.user_sessions:
                    self.user_sessions[user_id].discard(session_id)
                    if not self.user_sessions[user_id]:
                        del self.user_sessions[user_id]
                
                # Remove session
                del self.sessions[session_id]
                logger.info(f"Removed session {session_id} for user {user_id}")
                return True
            return False
    
    def get_user_sessions(self, user_id: str) -> list[UserSession]:
        """Get all active sessions for a user"""
        with self.lock:
            session_ids = self.user_sessions.get(user_id, set())
            sessions = []
            for session_id in list(session_ids):  # Create copy to avoid modification during iteration
                session = self.sessions.get(session_id)
                if session and not session.is_expired():
                    session.update_activity()
                    sessions.append(session)
                elif session and session.is_expired():
                    self.remove_session(session_id)
            return sessions
    
    def cleanup_expired_sessions(self, timeout_minutes: int = 60):
        """Clean up expired sessions"""
        with self.lock:
            expired_sessions = []
            for session_id, session in self.sessions.items():
                if session.is_expired(timeout_minutes):
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                self.remove_session(session_id)
            
            if expired_sessions:
                logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
    
    def get_stats(self) -> Dict:
        """Get session statistics"""
        with self.lock:
            # Clean up expired sessions first
            self.cleanup_expired_sessions()
            
            return {
                'total_sessions': len(self.sessions),
                'total_users': len(self.user_sessions),
                'sessions_by_user': {
                    user_id: len(session_ids) 
                    for user_id, session_ids in self.user_sessions.items()
                }
            }
    
    def generate_user_id(self) -> str:
        """Generate a unique user ID"""
        return f"user_{str(uuid.uuid4())[:8]}"

# Global session manager instance
session_manager = SessionManager()