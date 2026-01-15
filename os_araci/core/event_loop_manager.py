import asyncio
import threading
import concurrent.futures
from typing import Optional, Coroutine, Any
import logging
import weakref
from asyncio import Queue

logger = logging.getLogger(__name__)

class EventLoopManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._task_queue = None
        self._running_tasks = weakref.WeakSet()
        
        # Thread pools
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=20)
        self.process_pool = concurrent.futures.ProcessPoolExecutor(max_workers=4)
        
        self._initialized = True
    
    def ensure_loop(self) -> asyncio.AbstractEventLoop:
        """Event loop'u garanti et"""
        with self._lock:
            if self._loop is None or not self._loop.is_running():
                self._loop = asyncio.new_event_loop()
                self._task_queue = Queue(maxsize=1000)
                
                def run_loop():
                    asyncio.set_event_loop(self._loop)
                    self._loop.run_forever()
                
                self._thread = threading.Thread(target=run_loop, daemon=True)
                self._thread.start()
                
                # Task worker başlat
                asyncio.run_coroutine_threadsafe(
                    self._task_worker(), self._loop
                )
                
                # Loop'un başlamasını bekle
                import time
                time.sleep(0.1)
        
        return self._loop
    
    async def _task_worker(self):
        """Kuyruktan task'ları al ve çalıştır"""
        while True:
            try:
                coro = await self._task_queue.get()
                task = asyncio.create_task(coro)
                self._running_tasks.add(task)
                await task
            except Exception as e:
                logger.error(f"Task worker hatası: {e}")
    
    def run_async(self, coro: Coroutine[Any, Any, Any]) -> Any:
        """Async işlemleri güvenli çalıştır"""
        loop = self.ensure_loop()
        
        try:
            current_loop = asyncio.get_event_loop()
            if current_loop.is_running() and current_loop == loop:
                # Aynı loop'tayız
                task = asyncio.create_task(coro)
                self._running_tasks.add(task)
                return task
        except RuntimeError:
            pass
        
        # Farklı thread'deyiz
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result(timeout=90)
    
    def queue_task(self, coro: Coroutine[Any, Any, Any]):
        """Task'ı kuyruğa ekle"""
        loop = self.ensure_loop()
        asyncio.run_coroutine_threadsafe(
            self._task_queue.put(coro), loop
        )
    
    def shutdown(self):
        """Event loop'u temizle"""
        if self._loop and self._loop.is_running():
            # Bekleyen task'ları iptal et
            for task in self._running_tasks:
                task.cancel()
            
            self._loop.call_soon_threadsafe(self._loop.stop)
            
        self.thread_pool.shutdown(wait=True)
        self.process_pool.shutdown(wait=True)

# Singleton instance
event_loop_manager = EventLoopManager()
run_async = event_loop_manager.run_async
queue_task = event_loop_manager.queue_task