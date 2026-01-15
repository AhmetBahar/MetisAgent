# personas/task_executor_persona.py
import asyncio
import logging
import time
import json
from typing import Dict, Any, List, Optional, Union, Callable
from os_araci.personas.persona_agent import PersonaAgent
from os_araci.a2a_protocol.message import A2AMessage
from os_araci.mcp_core.registry import MCPRegistry, ToolSourceType

logger = logging.getLogger(__name__)

class TaskExecutorPersona(PersonaAgent):
    """Görev çalıştırmak için özelleştirilmiş bir persona"""
    
    def __init__(self, 
                persona_id: str, 
                name: str,
                description: str,
                tool_categories: List[str] = None,
                tool_capabilities: List[str] = None,
                max_concurrent_tasks: int = 5,
                **kwargs):
        
        # Ana sınıfın başlatıcısını çağır
        super().__init__(
            persona_id=persona_id,
            name=name,
            description=description,
            capabilities=["task_execution"] + (tool_capabilities or []),
            **kwargs
        )
        
        # Görev yürütücü özellikleri
        self.tool_categories = tool_categories or ["general"]
        self.tool_capabilities = tool_capabilities or []
        self.max_concurrent_tasks = max_concurrent_tasks
        
        # MCP Registry
        self.mcp_registry = MCPRegistry()
        
        # Görev çalıştırma izleyicisi
        self.task_history = []  # Son çalıştırılan görevlerin geçmişi
        self.max_history = 100  # Maksimum geçmiş uzunluğu
    
    async def _initialize(self) -> bool:
        """TaskExecutor başlatma"""
        # MCP Registry'nin başlatıldığından emin ol
        if not self.mcp_registry._initialized:
            logger.error(f"MCP Registry başlatılmamış, {self.persona_id} başlatılamıyor")
            return False
        
        # Kullanılabilir araçları kontrol et
        tools = self.mcp_registry.get_all_tools()
        if not tools:
            logger.warning(f"Hiç araç bulunamadı, {self.persona_id} sınırlı çalışabilir")
        
        return True
    
    async def handle_task_request(self, message: A2AMessage) -> None:
        """Görev isteklerini işle ve çalıştır"""
        # Durum kontrolü
        if self.status == "disabled":
            reply = message.create_reply(
                content={"status": "error", "message": f"Persona {self.name} is disabled"},
                message_type="task.response"
            )
            await self._registry.send_message(reply)
            return
        
        # Eş zamanlı görev sayısı kontrolü
        if len(self._current_tasks) >= self.max_concurrent_tasks:
            reply = message.create_reply(
                content={
                    "status": "error", 
                    "message": f"Too many concurrent tasks ({len(self._current_tasks)}/{self.max_concurrent_tasks})"
                },
                message_type="task.response"
            )
            await self._registry.send_message(reply)
            return
        
        # Görev bilgilerini al
        task = message.content.get("task", {})
        context = message.content.get("context", {})
        task_id = task.get("id") or message.message_id
        
        if not task:
            reply = message.create_reply(
                content={"status": "error", "message": "No task specified in request"},
                message_type="task.response"
            )
            await self._registry.send_message(reply)
            return
        
        # Görev ismi ve açıklaması
        task_name = task.get("name", "Unnamed Task")
        task_description = task.get("description", "")
        
        logger.info(f"Görev talebi alındı: {task_id} - {task_name}")
        
        # Görevi asenkron olarak çalıştır ve takip et
        task_coro = self._execute_task(task, context, message)
        task_obj = asyncio.create_task(task_coro)
        self._current_tasks[task_id] = task_obj
        
        # Durum güncelleme
        if len(self._current_tasks) == 1:  # İlk görev başladıysa durum idle -> busy
            await self.update_status("busy")
        
        # Görev bittiğinde temizlik yap
        task_obj.add_done_callback(lambda _: self._task_completed(task_id))
    
    async def _execute_task(self, task: Dict[str, Any], context: Dict[str, Any], original_message: A2AMessage) -> None:
        """Görevi çalıştır ve sonucu yanıtla"""
        start_time = time.time()
        task_id = task.get("id") or original_message.message_id
        task_name = task.get("name", "Unnamed Task")
        
        try:
            # Görevi çalıştırmak için hazırla
            command = task.get("command", "")
            tool_name = task.get("tool", "")
            action_name = task.get("action", "")
            params = task.get("params", {})
            
            # Metrikler
            self.task_metrics["total_tasks"] += 1
            self.task_metrics["last_task_time"] = start_time
            
            result = None
            
            # Görev tipine göre çalıştır
            if tool_name and action_name:
                # MCP aracı aksiyonu
                result = await self._run_tool_action(tool_name, action_name, params, context)
            elif command:
                # Komut çalıştırma
                result = await self._run_command(command, context)
            else:
                # Desteklenmeyen görev tipi
                raise ValueError(f"Unsupported task type, missing tool+action or command")
            
            # Başarılı yanıt
            execution_time = time.time() - start_time
            
            # Metrikleri güncelle
            self.task_metrics["successful_tasks"] += 1
            self._update_avg_response_time(execution_time)
            
            # Görev geçmişine ekle
            self._add_to_history({
                "task_id": task_id,
                "task_name": task_name,
                "start_time": start_time,
                "execution_time": execution_time,
                "status": "success"
            })
            
            # Yanıt mesajı
            reply = original_message.create_reply(
                content={
                    "status": "success",
                    "task_id": task_id,
                    "result": result,
                    "execution_time": execution_time,
                    "context_updates": context  # Context güncellemelerini ilet
                },
                message_type="task.response"
            )
            await self._registry.send_message(reply)
            logger.info(f"Görev başarıyla tamamlandı: {task_id} - {task_name} ({execution_time:.2f}s)")
            
        except Exception as e:
            # Hatalı yanıt
            execution_time = time.time() - start_time
            
            # Metrikleri güncelle
            self.task_metrics["failed_tasks"] += 1
            self._update_avg_response_time(execution_time)
            
            # Görev geçmişine ekle
            self._add_to_history({
                "task_id": task_id,
                "task_name": task_name,
                "start_time": start_time,
                "execution_time": execution_time,
                "status": "error",
                "error": str(e)
            })
            
            # Yanıt mesajı
            reply = original_message.create_reply(
                content={
                    "status": "error",
                    "task_id": task_id,
                    "error": str(e),
                    "execution_time": execution_time
                },
                message_type="task.response"
            )
            await self._registry.send_message(reply)
            logger.error(f"Görev başarısız: {task_id} - {task_name}, hata: {str(e)}")
    
    async def _run_tool_action(self, tool_name: str, action_name: str, params: Dict[str, Any], context: Dict[str, Any]) -> Any:
        """MCP aracı aksiyonunu çalıştır"""
        # Aracı bul
        tool = None
        tool_id = None
        
        # Önce tool_id doğrudan verilmiş mi kontrol et
        if "." in tool_name:  # tool_id formatı: source_type.name.version
            tool = self.mcp_registry.get_tool_by_id(tool_name)
            tool_id = tool_name
        else:
            # İsimle ara, en son sürümü al
            tool_id = self.mcp_registry.get_latest_version(tool_name)
            if tool_id:
                tool = self.mcp_registry.get_tool_by_id(tool_id)
        
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")
        
        # Aksiyonu çağır
        logger.info(f"MCP aracı çağrılıyor: {tool_id}.{action_name}")
        result = self.mcp_registry.call_handler(tool_id, action_name, **params)
        
        # Context'i güncelle (aksiyon sonucunda context değişkenleri var mı?)
        if isinstance(result, dict) and "context_updates" in result:
            context.update(result["context_updates"])
        
        return result
    
    async def _run_command(self, command: str, context: Dict[str, Any]) -> Any:
        """Sistem komutu çalıştır"""
        # Güvenlik kontrolü ve komut yürütme
        logger.info(f"Komut çalıştırılıyor: {command}")
        
        # command_executor aracını bul
        command_tool = None
        for tool_id, metadata in self.mcp_registry.get_all_metadata().items():
            if metadata.name == 'command_executor':
                command_tool = self.mcp_registry.get_tool_by_id(tool_id)
                break
        
        if not command_tool:
            raise ValueError("Command executor tool not found")
        
        # Komutu çalıştır
        result = command_tool.execute_action('execute_command', command=command)
        
        return result
    
    def _task_completed(self, task_id: str) -> None:
        """Görev tamamlandığında temizlik yap"""
        # Görev listesinden kaldır
        if task_id in self._current_tasks:
            del self._current_tasks[task_id]
        
        # Eğer aktif görev kalmadıysa durumu güncelle
        if not self._current_tasks and self.status == "busy":
            # sync içinden async çağrı
            asyncio.create_task(self.update_status("idle"))
    
    def _update_avg_response_time(self, execution_time: float) -> None:
        """Ortalama yanıt süresini güncelle"""
        # İlk görev ise doğrudan ata
        if self.task_metrics["total_tasks"] == 1:
            self.task_metrics["average_response_time"] = execution_time
            return
        
        # Hareketli ortalama ile güncelle
        total_tasks = self.task_metrics["total_tasks"]
        current_avg = self.task_metrics["average_response_time"]
        
        # Yeni ortalama = eski ortalama * (n-1)/n + yeni değer/n
        new_avg = current_avg * (total_tasks - 1) / total_tasks + execution_time / total_tasks
        self.task_metrics["average_response_time"] = new_avg
    
    def _add_to_history(self, task_info: Dict[str, Any]) -> None:
        """Görev geçmişine ekle, maksimum uzunluğu koru"""
        self.task_history.append(task_info)
        
        # Geçmiş uzunluğunu kontrol et
        if len(self.task_history) > self.max_history:
            # En eski kaydı sil
            self.task_history.pop(0)
    
    async def get_task_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Son çalıştırılan görevlerin geçmişini getir"""
        # En son X kaydı döndür
        return self.task_history[-limit:]