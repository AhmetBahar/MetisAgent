# os_araci/websocket/handler.py
import logging
import json
import uuid
import time
from typing import Set, Dict, Any
from flask_sock import Sock

logger = logging.getLogger(__name__)

class WebSocketHandler:
    def __init__(self, sock: Sock):
        self.sock = sock
        self.clients: Dict[str, Any] = {}  # ws_id -> ws connection
        self.client_sessions: Dict[str, Dict] = {}  # ws_id -> session info
        
    def add_client(self, ws_id: str, ws):
        """WebSocket client ekle"""
        self.clients[ws_id] = ws
        self.client_sessions[ws_id] = {
            'id': ws_id,
            'connected_at': time.time(),
            'subscriptions': set()  # Hangi event'lere abone
        }
        logger.info(f"WebSocket client bağlandı: {ws_id}")
    
    def remove_client(self, ws_id: str):
        """WebSocket client kaldır"""
        if ws_id in self.clients:
            del self.clients[ws_id]
            del self.client_sessions[ws_id]
            logger.info(f"WebSocket client ayrıldı: {ws_id}")
    
    def broadcast(self, event_type: str, data: Dict[str, Any], target_clients: Set[str] = None):
        """Tüm veya belirli client'lara mesaj yayınla"""
        message = {
            'type': event_type,
            'data': data,
            'timestamp': time.time()
        }
        
        targets = target_clients if target_clients else self.clients.keys()
        
        for client_id in targets:
            if client_id in self.clients:
                try:
                    ws = self.clients[client_id]
                    ws.send(json.dumps(message))
                except Exception as e:
                    logger.error(f"WebSocket mesaj gönderme hatası {client_id}: {str(e)}")
                    self.remove_client(client_id)
    
    def send_to_client(self, client_id: str, event_type: str, data: Dict[str, Any]):
        """Belirli bir client'a mesaj gönder"""
        if client_id in self.clients:
            self.broadcast(event_type, data, {client_id})