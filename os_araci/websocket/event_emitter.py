# websocket/event_emitter.py
import logging
from typing import Dict, Any, Callable, List

logger = logging.getLogger(__name__)

class EventEmitter:
    """Event yayınlama ve dinleme mekanizması"""
    
    def __init__(self, ws_handler=None):
        self.ws_handler = ws_handler
        self.listeners: Dict[str, List[Callable]] = {}
    
    def on(self, event: str, callback: Callable):
        """Event dinleyicisi ekle"""
        if event not in self.listeners:
            self.listeners[event] = []
        self.listeners[event].append(callback)
    
    def off(self, event: str, callback: Callable):
        """Event dinleyicisi kaldır"""
        if event in self.listeners:
            self.listeners[event].remove(callback)
    
    def emit(self, event: str, data: Dict[str, Any]):
        """Event yayınla (senkron)"""
        # WebSocket üzerinden yayınla
        if self.ws_handler:
            self.ws_handler.broadcast(event, data)
        
        # Lokal dinleyicilere bildir
        if event in self.listeners:
            for callback in self.listeners[event]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Event callback hatası: {event}, {str(e)}")