# a2a_protocol/message.py
import uuid
import time
import json
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class A2AMessage:
    """A2A protokolü için mesaj sınıfı"""
    
    def __init__(self, 
                sender: str,
                receiver: str,
                message_type: str,
                content: Dict[str, Any],
                message_id: Optional[str] = None,
                correlation_id: Optional[str] = None,
                reply_to: Optional[str] = None,
                expires_at: Optional[float] = None,
                priority: int = 5,
                headers: Optional[Dict[str, Any]] = None):
        
        self.message_id = message_id or str(uuid.uuid4())
        self.correlation_id = correlation_id
        self.sender = sender
        self.receiver = receiver
        self.message_type = message_type
        self.content = content
        self.reply_to = reply_to
        self.created_at = time.time()
        self.expires_at = expires_at
        self.priority = min(max(priority, 1), 10)  # 1-10 arası (10 en yüksek)
        self.headers = headers or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Mesajı sözlüğe dönüştür"""
        return {
            "message_id": self.message_id,
            "correlation_id": self.correlation_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "message_type": self.message_type,
            "content": self.content,
            "reply_to": self.reply_to,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "priority": self.priority,
            "headers": self.headers
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'A2AMessage':
        """Sözlükten mesaj oluştur"""
        return cls(
            message_id=data.get("message_id"),
            correlation_id=data.get("correlation_id"),
            sender=data.get("sender"),
            receiver=data.get("receiver"),
            message_type=data.get("message_type"),
            content=data.get("content", {}),
            reply_to=data.get("reply_to"),
            expires_at=data.get("expires_at"),
            priority=data.get("priority", 5),
            headers=data.get("headers", {})
        )
        
    def to_json(self) -> str:
        """Mesajı JSON formatına dönüştür"""
        return json.dumps(self.to_dict())
        
    @classmethod
    def from_json(cls, json_str: str) -> 'A2AMessage':
        """JSON formatından mesaj oluştur"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def create_reply(self, content: Dict[str, Any], message_type: Optional[str] = None) -> 'A2AMessage':
        """Bu mesaja yanıt oluştur"""
        return A2AMessage(
            sender=self.receiver,
            receiver=self.sender,
            message_type=message_type or f"reply:{self.message_type}",
            content=content,
            correlation_id=self.message_id,
            reply_to=self.message_id,
            priority=self.priority
        )
    
    def is_expired(self) -> bool:
        """Mesajın süresi dolmuş mu kontrol et"""
        if not self.expires_at:
            return False
        return time.time() > self.expires_at