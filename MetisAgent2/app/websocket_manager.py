"""
WebSocket Manager for real-time workflow updates
"""

import logging
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask import request
from typing import Dict, Set, Any
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Manages WebSocket connections and real-time workflow updates"""
    
    def __init__(self):
        self.socketio = None
        self.connected_users: Dict[str, Set[str]] = {}  # user_id -> set of session_ids
        self.user_sessions: Dict[str, str] = {}  # session_id -> user_id
        
    def init_app(self, app):
        """Initialize SocketIO with Flask app"""
        self.socketio = SocketIO(
            app, 
            cors_allowed_origins="*",
            logger=False,
            engineio_logger=False,
            async_mode='threading',
            ping_timeout=120,  # 2 minutes ping timeout
            ping_interval=25,  # Ping every 25 seconds
            max_http_buffer_size=10*1024*1024  # 10MB buffer for large base64 images
        )
        
        # Register event handlers
        self.socketio.on_event('connect', self._handle_connect)
        self.socketio.on_event('disconnect', self._handle_disconnect)
        self.socketio.on_event('join_workflow_room', self._handle_join_workflow_room)
        self.socketio.on_event('leave_workflow_room', self._handle_leave_workflow_room)
        self.socketio.on_event('clear_todos', self._handle_clear_todos)
        self.socketio.on_event('get_todos', self._handle_get_todos)
        self.socketio.on_event('update_todo_status', self._handle_update_todo_status)
        
        logger.info("WebSocket Manager initialized")
        return self.socketio
    
    def _handle_connect(self):
        """Handle client connection"""
        session_id = request.sid
        logger.info(f"WebSocket client connected: {session_id}")
        
        # Send connection confirmation
        emit('connection_status', {
            'connected': True,
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        })
    
    def _handle_disconnect(self):
        """Handle client disconnection"""
        session_id = request.sid
        
        # Clean up user session mapping
        if session_id in self.user_sessions:
            user_id = self.user_sessions[session_id]
            if user_id in self.connected_users:
                self.connected_users[user_id].discard(session_id)
                if not self.connected_users[user_id]:
                    del self.connected_users[user_id]
            del self.user_sessions[session_id]
        
        logger.info(f"WebSocket client disconnected: {session_id}")
    
    def _handle_join_workflow_room(self, data):
        """Handle joining workflow-specific room"""
        session_id = request.sid
        user_id = data.get('user_id', 'anonymous')
        
        # Map session to user
        self.user_sessions[session_id] = user_id
        if user_id not in self.connected_users:
            self.connected_users[user_id] = set()
        self.connected_users[user_id].add(session_id)
        
        # Join user-specific room
        room_name = f"user_{user_id}"
        join_room(room_name)
        
        logger.info(f"User {user_id} joined workflow room: {room_name}")
        
        # Send confirmation
        emit('room_joined', {
            'room': room_name,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        })
    
    def _handle_leave_workflow_room(self, data):
        """Handle leaving workflow-specific room"""
        session_id = request.sid
        user_id = data.get('user_id', 'anonymous')
        room_name = f"user_{user_id}"
        
        leave_room(room_name)
        logger.info(f"User {user_id} left workflow room: {room_name}")
        
        emit('room_left', {
            'room': room_name,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        })
    
    def broadcast_workflow_update(self, user_id: str, workflow_data: Dict[str, Any]):
        """Broadcast workflow update to specific user"""
        if not self.socketio:
            return
        
        room_name = f"user_{user_id}"
        
        try:
            self.socketio.emit('workflow_update', {
                'type': 'workflow_update',
                'workflow': workflow_data,
                'timestamp': datetime.now().isoformat()
            }, room=room_name)
            
            logger.info(f"Workflow update broadcasted to user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast workflow update: {e}")
    
    def broadcast_workflow_step_update(self, user_id: str, workflow_id: str, step_data: Dict[str, Any]):
        """Broadcast individual step update"""
        if not self.socketio:
            return
        
        room_name = f"user_{user_id}"
        
        try:
            self.socketio.emit('workflow_step_update', {
                'type': 'step_update',
                'workflow_id': workflow_id,
                'step': step_data,
                'timestamp': datetime.now().isoformat()
            }, room=room_name)
            
            logger.info(f"Step update broadcasted to user {user_id} for workflow {workflow_id}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast step update: {e}")
    
    def broadcast_todo_update(self, user_id: str, event_type: str, todo_data: Dict[str, Any], workflow_id: str = None):
        """Broadcast todo updates to specific user"""
        if not self.socketio:
            return
        
        room_name = f"user_{user_id}"
        
        try:
            self.socketio.emit('todo_update', {
                'type': 'todo_update',
                'event': event_type,
                'data': todo_data,
                'workflow_id': workflow_id,
                'timestamp': datetime.now().isoformat()
            }, room=room_name)
            
            logger.info(f"Todo update ({event_type}) broadcasted to user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast todo update: {e}")
    
    def broadcast_to_user(self, user_id: str, data: Dict[str, Any]):
        """Generic method to broadcast any data to specific user"""
        if not self.socketio:
            return
        
        room_name = f"user_{user_id}"
        
        try:
            self.socketio.emit('message', data, room=room_name)
            logger.debug(f"Message broadcasted to user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast message to user: {e}")
    
    def broadcast_workflow_started(self, user_id: str, workflow_data: Dict[str, Any]):
        """Notify when workflow starts"""
        if not self.socketio:
            return
        
        room_name = f"user_{user_id}"
        
        try:
            self.socketio.emit('workflow_started', {
                'type': 'workflow_started',
                'workflow': workflow_data,
                'timestamp': datetime.now().isoformat()
            }, room=room_name)
            
            logger.info(f"Workflow started event sent to user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast workflow started: {e}")
    
    def broadcast_workflow_completed(self, user_id: str, workflow_id: str, status: str):
        """Notify when workflow completes"""
        if not self.socketio:
            return
        
        room_name = f"user_{user_id}"
        
        try:
            self.socketio.emit('workflow_completed', {
                'type': 'workflow_completed',
                'workflow_id': workflow_id,
                'status': status,
                'timestamp': datetime.now().isoformat()
            }, room=room_name)
            
            logger.info(f"Workflow completed event sent to user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast workflow completed: {e}")
    
    def get_connected_users(self) -> Dict[str, int]:
        """Get statistics of connected users"""
        return {
            user_id: len(sessions) 
            for user_id, sessions in self.connected_users.items()
        }
    
    def _handle_clear_todos(self, data):
        """Handle todo clearing request from frontend"""
        try:
            session_id = request.sid
            user_id = data.get('user_id', 'anonymous')
            
            logger.info(f"Todo clear request from session {session_id} for user {user_id}")
            
            # Broadcast todos cleared event to all user sessions
            room_name = f"user_{user_id}"
            
            self.socketio.emit('todos_cleared', {
                'type': 'todos_cleared',
                'user_id': user_id,
                'timestamp': data.get('timestamp', datetime.now().isoformat()),
                'cleared_by': session_id
            }, room=room_name)
            
            logger.info(f"Todo clear event broadcasted to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error handling clear todos: {e}")
    
    def _handle_get_todos(self, data):
        """Handle get todos request"""
        try:
            session_id = request.sid
            user_id = self.user_sessions.get(session_id)
            
            if not user_id:
                emit('error', {'message': 'User not authenticated'})
                return
            
            # Get todos from internal todo manager
            from tools.internal.todo_manager import get_todo_tool
            todo_tool = get_todo_tool()
            
            workflow_id = data.get('workflow_id')
            result = todo_tool.todo_get_all(user_id, workflow_id)
            
            emit('todos_loaded', {
                'todos': result.get('todos', []),
                'total': result.get('total', 0),
                'workflow_id': workflow_id
            })
            
            logger.info(f"Sent {result.get('total', 0)} todos to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error handling get todos: {e}")
            emit('error', {'message': f'Error getting todos: {str(e)}'})
    
    def _handle_update_todo_status(self, data):
        """Handle update todo status request"""
        try:
            session_id = request.sid
            user_id = self.user_sessions.get(session_id)
            
            if not user_id:
                emit('error', {'message': 'User not authenticated'})
                return
            
            todo_id = data.get('todo_id')
            status = data.get('status')
            workflow_id = data.get('workflow_id')
            
            if not todo_id or not status:
                emit('error', {'message': 'Missing todo_id or status'})
                return
            
            # Update todo status using internal todo manager
            from tools.internal.todo_manager import get_todo_tool
            todo_tool = get_todo_tool()
            
            result = todo_tool.todo_update_status(user_id, todo_id, status, workflow_id)
            
            if result.get('success'):
                emit('todo_status_updated', {
                    'todo_id': todo_id,
                    'status': status,
                    'todo': result.get('todo')
                })
                logger.info(f"Updated todo {todo_id} status to {status} for user {user_id}")
            else:
                emit('error', {'message': result.get('error', 'Unknown error')})
            
        except Exception as e:
            logger.error(f"Error handling update todo status: {e}")
            emit('error', {'message': f'Error updating todo: {str(e)}'})

# Global WebSocket manager instance
websocket_manager = WebSocketManager()

def get_websocket_manager() -> WebSocketManager:
    """Get the global WebSocket manager instance"""
    return websocket_manager