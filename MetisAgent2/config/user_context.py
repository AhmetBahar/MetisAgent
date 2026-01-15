#!/usr/bin/env python3
"""
User Context Management System
Dynamic user session and identity management for multi-user MetisAgent2
"""

import json
import os
import logging
import threading
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class UserContext:
    """User context for a single user session"""
    
    def __init__(self, user_id: str, session_id: str, user_data: Dict[str, Any]):
        self.user_id = user_id
        self.session_id = session_id
        self.user_data = user_data
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()
        self._lock = threading.Lock()
    
    def get(self, key: str, default=None):
        """Get user data"""
        with self._lock:
            self.last_accessed = datetime.now()
            return self.user_data.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set user data"""
        with self._lock:
            self.user_data[key] = value
            self.last_accessed = datetime.now()
    
    def get_google_account(self) -> Optional[str]:
        """Get user's mapped Google account"""
        return self.get('google_account')
    
    def get_system_email(self) -> Optional[str]:
        """Get user's system email"""
        return self.get('system_email', self.user_id)
    
    def get_display_name(self) -> str:
        """Get user's display name"""
        return self.get('display_name', self.user_id)
    
    def is_expired(self, timeout_minutes: int = 60) -> bool:
        """Check if user context is expired"""
        return (datetime.now() - self.last_accessed) > timedelta(minutes=timeout_minutes)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'user_id': self.user_id,
            'session_id': self.session_id,
            'user_data': self.user_data,
            'created_at': self.created_at.isoformat(),
            'last_accessed': self.last_accessed.isoformat()
        }

class UserContextManager:
    """Global user context management"""
    
    def __init__(self):
        self._contexts: Dict[str, UserContext] = {}
        self._session_to_user: Dict[str, str] = {}
        self._lock = threading.Lock()
        # Use SQLite storage instead of JSON file
        try:
            from ..tools.internal.user_storage import get_user_storage
        except ImportError:
            # Fallback for direct execution
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
            from tools.internal.user_storage import get_user_storage
        
        self.user_storage = get_user_storage()
        self._migrate_json_mappings_if_exists()
    
    def _migrate_json_mappings_if_exists(self):
        """Migrate existing JSON mappings to SQLite if file exists"""
        config_file = "config/user_mappings.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                
                user_mappings = json_data.get("user_mappings", {})
                migrated_count = 0
                
                for user_id, mapping_data in user_mappings.items():
                    try:
                        # Migrate to SQLite user storage
                        if 'google_account' in mapping_data:
                            self.user_storage.set_user_mapping(user_id, 'google', mapping_data['google_account'])
                        
                        if 'system_email' in mapping_data:
                            self.user_storage.set_property(user_id, 'system_email', mapping_data['system_email'])
                        
                        if 'display_name' in mapping_data:
                            self.user_storage.set_property(user_id, 'display_name', mapping_data['display_name'])
                        
                        migrated_count += 1
                        logger.info(f"Migrated user mapping: {user_id}")
                        
                    except Exception as e:
                        logger.error(f"Error migrating user mapping {user_id}: {e}")
                
                # Rename JSON file to prevent re-migration
                backup_file = f"{config_file}.migrated_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.rename(config_file, backup_file)
                logger.info(f"Migrated {migrated_count} user mappings to SQLite, JSON backed up as {backup_file}")
                
            except Exception as e:
                logger.error(f"Error migrating JSON user mappings: {e}")
    
    def _get_user_mapping_data(self, user_id: str) -> Dict[str, Any]:
        """Get user mapping data from SQLite"""
        try:
            mapping_data = {}
            
            # Get Google mapping
            google_account = self.user_storage.get_user_mapping(user_id, 'google')
            if google_account:
                mapping_data['google_account'] = google_account
            
            # Get other properties
            system_email = self.user_storage.get_property(user_id, 'system_email')
            if system_email:
                mapping_data['system_email'] = system_email
            
            display_name = self.user_storage.get_property(user_id, 'display_name')
            if display_name:
                mapping_data['display_name'] = display_name
            
            return mapping_data
            
        except Exception as e:
            logger.error(f"Error getting user mapping data for {user_id}: {e}")
            return {}
    
    def create_user_context(self, user_id: str, session_id: str, user_data: Dict[str, Any] = None) -> UserContext:
        """Create new user context"""
        if user_data is None:
            user_data = {}
        
        # Load any persistent mapping for this user from SQLite
        user_mapping = self._get_user_mapping_data(user_id)
        if user_mapping:
            user_data.update(user_mapping)
        
        with self._lock:
            context = UserContext(user_id, session_id, user_data)
            self._contexts[user_id] = context
            self._session_to_user[session_id] = user_id
            
        logger.info(f"Created user context: {user_id} (session: {session_id})")
        return context
    
    def get_user_context(self, user_id: str = None, session_id: str = None) -> Optional[UserContext]:
        """Get user context by user_id or session_id"""
        with self._lock:
            if user_id:
                return self._contexts.get(user_id)
            elif session_id:
                user_id = self._session_to_user.get(session_id)
                return self._contexts.get(user_id) if user_id else None
            return None
    
    def get_current_user_context(self) -> Optional[UserContext]:
        """Get current user context from thread local storage or active session"""
        # This would be implemented with Flask session or thread local
        # For now, return the most recently accessed context
        with self._lock:
            if not self._contexts:
                return None
            
            # Find most recently accessed context
            most_recent = max(self._contexts.values(), key=lambda ctx: ctx.last_accessed)
            return most_recent
    
    def remove_user_context(self, user_id: str):
        """Remove user context"""
        with self._lock:
            context = self._contexts.pop(user_id, None)
            if context:
                self._session_to_user.pop(context.session_id, None)
                logger.info(f"Removed user context: {user_id}")
    
    def cleanup_expired_contexts(self, timeout_minutes: int = 60):
        """Remove expired user contexts"""
        expired_users = []
        
        with self._lock:
            for user_id, context in self._contexts.items():
                if context.is_expired(timeout_minutes):
                    expired_users.append(user_id)
        
        for user_id in expired_users:
            self.remove_user_context(user_id)
        
        if expired_users:
            logger.info(f"Cleaned up {len(expired_users)} expired user contexts")
    
    def add_persistent_mapping(self, user_id: str, google_account: str, system_email: str = None, display_name: str = None):
        """Add persistent user mapping to SQLite"""
        if system_email is None:
            system_email = user_id
        if display_name is None:
            display_name = user_id
        
        try:
            # Save to SQLite user storage
            self.user_storage.set_user_mapping(user_id, 'google', google_account)
            self.user_storage.set_property(user_id, 'system_email', system_email)
            self.user_storage.set_property(user_id, 'display_name', display_name)
            self.user_storage.set_property(user_id, 'mapping_created_at', datetime.now().isoformat())
            
            logger.info(f"Added persistent mapping to SQLite: {user_id} -> {google_account}")
            
        except Exception as e:
            logger.error(f"Error adding persistent mapping: {e}")
    
    def get_all_contexts(self) -> Dict[str, Dict[str, Any]]:
        """Get all active user contexts (for debugging/admin)"""
        with self._lock:
            return {user_id: ctx.to_dict() for user_id, ctx in self._contexts.items()}
    
    def get_user_google_account(self, user_id: str = None) -> Optional[str]:
        """Get Google account for user (with fallback to SQLite mappings)"""
        # Try active context first
        context = self.get_user_context(user_id) if user_id else self.get_current_user_context()
        if context:
            google_account = context.get_google_account()
            if google_account:
                return google_account
        
        # Fallback to SQLite mappings
        if user_id:
            try:
                return self.user_storage.get_user_mapping(user_id, 'google')
            except Exception as e:
                logger.error(f"Error getting Google account mapping for {user_id}: {e}")
        
        return None
    
    def get_user_system_email(self, user_id: str = None) -> Optional[str]:
        """Get system email for user"""
        context = self.get_user_context(user_id) if user_id else self.get_current_user_context()
        if context:
            return context.get_system_email()
        
        # Fallback to SQLite storage, then user_id itself
        if user_id:
            try:
                system_email = self.user_storage.get_property(user_id, 'system_email')
                if system_email:
                    return system_email
            except Exception as e:
                logger.error(f"Error getting system email for {user_id}: {e}")
        
        return user_id

# Global user context manager
_user_context_manager = UserContextManager()

# Convenience functions for compatibility
def get_current_user_context() -> Optional[UserContext]:
    """Get current user context"""
    return _user_context_manager.get_current_user_context()

def get_user_google_account(user_id: str = None) -> Optional[str]:
    """Get Google account for user"""
    return _user_context_manager.get_user_google_account(user_id)

def get_user_system_email(user_id: str = None) -> Optional[str]:
    """Get system email for user"""
    return _user_context_manager.get_user_system_email(user_id)

def create_user_context(user_id: str, session_id: str, user_data: Dict[str, Any] = None) -> UserContext:
    """Create user context"""
    return _user_context_manager.create_user_context(user_id, session_id, user_data)

def get_context_manager() -> UserContextManager:
    """Get the global context manager"""
    return _user_context_manager

# Export main classes and functions
__all__ = [
    'UserContext', 'UserContextManager', 
    'get_current_user_context', 'get_user_google_account', 'get_user_system_email',
    'create_user_context', 'get_context_manager'
]