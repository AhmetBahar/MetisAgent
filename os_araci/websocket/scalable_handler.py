import asyncio
import json
import uuid
import logging
import weakref
from typing import Dict, Any
from functools import wraps
import time

from ..core.event_loop_manager import event_loop_manager, run_async

logger = logging.getLogger(__name__)

# Rate limiting decorator
def rate_limit(calls=10, period=60):
    def decorator(func):
        calls_made = {}
        
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            now = time.time()
            calls_in_period = calls_made.get(self.ws_id, [])
            calls_in_period = [c for c in calls_in_period if c > now - period]
            
            if len(calls_in_period) >= calls:
                raise Exception("Rate limit exceeded")
            
            calls_in_period.append(now)
            calls_made[self.ws_id] = calls_in_period
            
            return await func(self, *args, **kwargs)
        
        return wrapper
    return decorator

class ConnectionHandler:
    def __init__(self, ws_id: str, ws_handler, coordinator_a2a):
        self.ws_id = ws_id
        self.ws_handler = ws_handler
        self.coordinator_a2a = coordinator_a2a
        self.tasks = weakref.WeakSet()
        self.persona_lock = asyncio.Lock()
    
    @rate_limit(calls=30, period=60)
    async def handle_message(self, data: Dict[str, Any]):
        """Her mesajı işle"""
        command = data.get('command')
        
        if command == 'send_message':
            await self.handle_persona_message(data)
        elif command == 'execute_task':
            await self.handle_task_execution(data)
        elif command == 'get_personas':
            await self.handle_get_personas()
        else:
            logger.warning(f"Bilinmeyen komut: {command}")
            self.ws_handler.send_to_client(self.ws_id, 'error', {
                'message': f'Bilinmeyen komut: {command}'
            })
    
    async def handle_persona_message(self, data: Dict[str, Any]):
        """Persona mesajlarını işle"""
        message = data.get('message')
        persona_id = data.get('persona_id', 'assistant')
        
        if not message:
            self.ws_handler.send_to_client(self.ws_id, 'error', {
                'message': 'Mesaj içeriği boş'
            })
            return
        
        try:
            # Persona lock ile race condition önle
            async with self.persona_lock:
                if self.coordinator_a2a:
                    # Persona durumunu kontrol et
                    persona_status = await self.coordinator_a2a.get_persona_status(persona_id)
                    
                    if not persona_status.get('is_online'):
                        logger.info(f"Persona aktif değil, başlatılıyor: {persona_id}")
                        await self.coordinator_a2a.start_persona(persona_id)
                        await asyncio.sleep(2)
                    
                    # Mesajı gönder
                    response = await self.coordinator_a2a.send_message_to_persona(
                        persona_id=persona_id,
                        message=message,
                        user_id=self.ws_id
                    )
                    
                    self.ws_handler.send_to_client(self.ws_id, 'message_response', {
                        'persona_id': persona_id,
                        'message': message,
                        'response': response.get('response', ''),
                        'timestamp': time.time()
                    })
                else:
                    self.ws_handler.send_to_client(self.ws_id, 'error', {
                        'message': 'Persona sistemi kullanılamıyor'
                    })
                    
        except Exception as e:
            logger.error(f"Mesaj gönderme hatası: {str(e)}", exc_info=True)
            self.ws_handler.send_to_client(self.ws_id, 'message_response', {
                'persona_id': persona_id,
                'message': message,
                'response': f'Hata: {str(e)}',
                'timestamp': time.time()
            })
    
    async def handle_task_execution(self, data: Dict[str, Any]):
        """Task çalıştırma"""
        # CPU-bound işlemler için thread pool kullan
        task = data.get('task')
        if not task:
            self.ws_handler.send_to_client(self.ws_id, 'error', {
                'message': 'Task boş'
            })
            return
        
        try:
            # Task'ı thread pool'da çalıştır
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                event_loop_manager.thread_pool,
                lambda: self.coordinator_a2a.execute_task(task)
            )
            
            self.ws_handler.send_to_client(self.ws_id, 'task_result', result)
        except Exception as e:
            logger.error(f"Task çalıştırma hatası: {str(e)}")
            self.ws_handler.send_to_client(self.ws_id, 'error', {
                'message': f'Task hatası: {str(e)}'
            })
    
    async def handle_get_personas(self):
        """Persona listesini getir"""
        if self.coordinator_a2a:
            personas = await self.coordinator_a2a.get_personas()
            self.ws_handler.send_to_client(self.ws_id, 'personas_list', {
                'personas': personas
            })

class ScalableWebSocketHandler:
    def __init__(self, ws_handler, coordinator_a2a):
        self.ws_handler = ws_handler
        self.coordinator_a2a = coordinator_a2a
        self.connections: Dict[str, ConnectionHandler] = {}
    
    async def handle_connection(self, ws, ws_id: str):
        """WebSocket bağlantısını yönet"""
        handler = ConnectionHandler(ws_id, self.ws_handler, self.coordinator_a2a)
        self.connections[ws_id] = handler
        
        try:
            # Welcome message
            welcome_message = {
                'type': 'connected',
                'data': {
                    'ws_id': ws_id,
                    'message': 'Agent WebSocket bağlantısı kuruldu'
                }
            }
            ws.send(json.dumps(welcome_message))
            
            # Initial state
            if self.coordinator_a2a:
                personas = await self.coordinator_a2a.get_personas()
                initial_state = {
                    'type': 'initial_state',
                    'data': {'personas': personas}
                }
                ws.send(json.dumps(initial_state))
            
            # Message loop
            while True:
                message = ws.receive()
                if message is None:
                    break
                
                try:
                    data = json.loads(message)
                    
                    # Her mesaj için ayrı task
                    task = asyncio.create_task(handler.handle_message(data))
                    handler.tasks.add(task)
                    
                except json.JSONDecodeError:
                    error_msg = {
                        'type': 'error',
                        'data': {'message': 'Geçersiz JSON formatı'}
                    }
                    ws.send(json.dumps(error_msg))
                except Exception as e:
                    logger.error(f"Mesaj işleme hatası: {str(e)}")
                    error_msg = {
                        'type': 'error',
                        'data': {'message': f'Mesaj hatası: {str(e)}'}
                    }
                    ws.send(json.dumps(error_msg))
                    
        finally:
            # Cleanup
            del self.connections[ws_id]
            
            # Cancel tasks
            for task in handler.tasks:
                task.cancel()
    
    def create_handler(self, ws):
        """WebSocket handler factory"""
        ws_id = str(uuid.uuid4())
        
        async def run_handler():
            await self.handle_connection(ws, ws_id)
        
        # Handler'ı event loop'ta çalıştır
        run_async(run_handler())
        
        return ws_id