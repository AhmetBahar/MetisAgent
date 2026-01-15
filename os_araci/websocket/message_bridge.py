# os_araci/websocket/message_bridge.py
import logging
from typing import Dict, Any
import time
from os_araci.a2a_protocol.message import A2AMessage

logger = logging.getLogger(__name__)

class MessageBridge:
    """A2A mesajlarını WebSocket formatına dönüştürür"""
    
    def __init__(self, ws_handler):
        self.ws_handler = ws_handler
    
    def a2a_to_websocket(self, message: A2AMessage) -> Dict[str, Any]:
        """A2A mesajını WebSocket formatına çevir"""
        return {
            'type': 'a2a_message',
            'data': {
                'message_id': message.message_id,
                'sender': message.sender,
                'receiver': message.receiver,
                'message_type': message.message_type,
                'content': message.content,
                'timestamp': message.created_at
            }
        }
    
    def task_update_to_websocket(self, task_id: str, status: str, details: Dict[str, Any]) -> Dict[str, Any]:
        """Task güncellemesini WebSocket formatına çevir"""
        return {
            'type': 'task_update',
            'data': {
                'task_id': task_id,
                'status': status,
                'details': details,
                'timestamp': time.time()
            }
        }
    
    def persona_status_to_websocket(self, persona_id: str, status: str, details: Dict[str, Any]) -> Dict[str, Any]:
        """Persona durumunu WebSocket formatına çevir"""
        return {
            'type': 'persona_status',
            'data': {
                'persona_id': persona_id,
                'status': status,
                'details': details,
                'timestamp': time.time()
            }
        }