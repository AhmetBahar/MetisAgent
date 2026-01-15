# os_araci/plugins/workflow_plugin.py
import os
import json
import time
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union
from os_araci.personas.persona_agent import PersonaAgent
from os_araci.a2a_protocol.message import A2AMessage

logger = logging.getLogger(__name__)

class WorkflowPlugin(PersonaAgent):
    """İş akışı temelli plugin temel sınıfı"""
    
    def __init__(self, 
                persona_id: str, 
                name: str,
                description: str,
                workflow_steps: List[Dict[str, Any]] = None,
                workflow_transitions: List[Dict[str, Any]] = None,
                default_language: str = "tr",
                **kwargs):
        
        # Ana sınıfın başlatıcısını çağır
        capabilities = ["workflow_execution", "task_management", "task_execution"]
        
        super().__init__(
            persona_id=persona_id,
            name=name,
            description=description,
            capabilities=capabilities,
            **kwargs
        )
        
        # İş akışı özellikleri
        self.workflow_steps = workflow_steps or []
        self.workflow_transitions = workflow_transitions or []
        self.default_language = default_language
        
        # Çalışma izleme
        self.workflow_instances = {}  # instance_id -> workflow_instance
        self.history = []  # Geçmiş çalışma örnekleri
        
    async def _initialize(self) -> bool:
        """İş akışı eklentisini başlat"""
        try:
            # Çalışma dizinini kontrol et/oluştur
            working_dir = self.settings.get("working_dir", f"./plugins/data/{self.persona_id}")
            if not os.path.exists(working_dir):
                os.makedirs(working_dir)
                logger.info(f"Çalışma dizini oluşturuldu: {working_dir}")
            
            # Geçmiş verileri yükle (varsa)
            history_file = os.path.join(working_dir, "workflow_history.json")
            if os.path.exists(history_file):
                try:
                    with open(history_file, 'r', encoding='utf-8') as f:
                        self.history = json.load(f)
                    logger.info(f"{len(self.history)} adet çalışma geçmişi yüklendi")
                except Exception as e:
                    logger.warning(f"Çalışma geçmişi yüklenirken hata: {str(e)}")
            
            # Aktif workflow örneklerini yükle
            instances_file = os.path.join(working_dir, "active_instances.json")
            if os.path.exists(instances_file):
                try:
                    with open(instances_file, 'r', encoding='utf-8') as f:
                        self.workflow_instances = json.load(f)
                    logger.info(f"{len(self.workflow_instances)} adet aktif çalışma örneği yüklendi")
                except Exception as e:
                    logger.warning(f"Aktif çalışma örnekleri yüklenirken hata: {str(e)}")
            
            # Genişletilmiş MCP Registry bağlantısı
            from os_araci.mcp_core.registry import MCPRegistry
            self.mcp_registry = MCPRegistry()
            
            # LLM aracını bul
            self._find_llm_tool()
            
            # Coordinator bağlantısı
            self._find_coordinator()
            
            logger.info(f"İş akışı eklentisi başlatıldı: {self.persona_id}")
            return True
        except Exception as e:
            logger.error(f"İş akışı eklentisi başlatma hatası: {str(e)}")
            return False
    
    def _find_llm_tool(self):
        """LLM tool'u bul ve kaydet"""
        try:
            # LLM tool'u bul
            for tool_id, metadata in self.mcp_registry.get_all_metadata().items():
                if metadata.name == 'llm_tool':
                    self.llm_tool = self.mcp_registry.get_tool_by_id(tool_id)
                    logger.info(f"LLM tool bulundu: {tool_id}")
                    return
            
            logger.warning("LLM tool bulunamadı")
            self.llm_tool = None
        except Exception as e:
            logger.error(f"LLM tool arama hatası: {str(e)}")
            self.llm_tool = None

    def _find_coordinator(self):
        """MCPCoordinator'ı bul"""
        try:
            # Coordinator'ı al
            from os_araci.coordination.coordinator import MCPCoordinator
            self.coordinator = MCPCoordinator(self.mcp_registry)
            return self.coordinator
        except Exception as e:
            logger.error(f"Coordinator arama hatası: {str(e)}")
            self.coordinator = None
    
    async def _shutdown(self) -> bool:
        """İş akışı eklentisi kapanırken çağrılır"""
        try:
            # Çalışma dizinini al
            working_dir = self.settings.get("working_dir", f"./plugins/data/{self.persona_id}")
            
            # Geçmiş verileri kaydet
            history_file = os.path.join(working_dir, "workflow_history.json")
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
            
            # Aktif çalışma örneklerini kaydet
            instances_file = os.path.join(working_dir, "active_instances.json")
            with open(instances_file, 'w', encoding='utf-8') as f:
                json.dump(self.workflow_instances, f, ensure_ascii=False, indent=2)
            
            logger.info(f"İş akışı eklentisi verileri kaydedildi: {self.persona_id}")
            return True
        except Exception as e:
            logger.error(f"İş akışı eklentisi verileri kaydedilirken hata: {str(e)}")
            return False
    
    async def handle_task_request(self, message: A2AMessage) -> None:
        """Görev isteklerini işle"""
        # Durum kontrolü
        if self.status == "disabled":
            reply = message.create_reply(
                content={"status": "error", "message": f"Plugin {self.name} is disabled"},
                message_type="task.response"
            )
            await self._registry.send_message(reply)
            return
        
        task = message.content.get("task", {})
        context = message.content.get("context", {})
        action = task.get("action", "")
        
        try:
            # Görev aksiyonuna göre işle
            if action == "start_workflow":
                result = await self._action_start_workflow(task, context)
            elif action == "complete_step":
                result = await self._action_complete_step(task, context)
            elif action == "get_workflow_status":
                result = await self._action_get_workflow_status(task, context)
            elif action == "cancel_workflow":
                result = await self._action_cancel_workflow(task, context)
            else:
                # Desteklenmeyen aksiyon
                raise ValueError(f"Unsupported workflow action: {action}")
            
            # Başarılı yanıt
            reply = message.create_reply(
                content={
                    "status": "success",
                    "task_id": task.get("id", ""),
                    "result": result,
                    "context_updates": context
                },
                message_type="task.response"
            )
            await self._registry.send_message(reply)
            
        except Exception as e:
            # Hatalı yanıt
            reply = message.create_reply(
                content={
                    "status": "error",
                    "task_id": task.get("id", ""),
                    "error": str(e)
                },
                message_type="task.response"
            )
            await self._registry.send_message(reply)
            logger.error(f"İş akışı görevi başarısız: {task.get('id', '')}, hata: {str(e)}")
    
    # ----- WORKFLOW ACTIONS -----
    
    async def _action_start_workflow(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Yeni bir iş akışı başlat"""
        # Görev parametrelerini al
        params = task.get("params", {})
        workflow_name = params.get("workflow_name", self.name)
        initial_data = params.get("initial_data", {})
        
        # Yeni bir workflow örneği oluştur
        instance_id = f"wf_{int(time.time())}_{workflow_name.replace(' ', '_')}"
        
        # İlk adımı bul
        if not self.workflow_steps:
            raise ValueError("No workflow steps defined")
        
        first_step = self.workflow_steps[0]
        
        # Workflow örneğini oluştur
        workflow_instance = {
            "instance_id": instance_id,
            "workflow_name": workflow_name,
            "current_step": first_step["step_id"],
            "status": "active",
            "created_at": time.time(),
            "last_updated": time.time(),
            "data": initial_data,
            "completed_steps": [],
            "step_history": [
                {
                    "step_id": first_step["step_id"],
                    "status": "active",
                    "started_at": time.time()
                }
            ]
        }
        
        # Workflow örneklerini güncelle
        self.workflow_instances[instance_id] = workflow_instance
        
        # Context güncellemesi
        context["current_workflow_id"] = instance_id
        
        return {
            "instance_id": instance_id,
            "workflow_name": workflow_name,
            "current_step": {
                "step_id": first_step["step_id"],
                "name": first_step["name"],
                "description": first_step["description"],
                "required_inputs": first_step.get("required_inputs", []),
                "responsible_roles": first_step.get("responsible_roles", [])
            },
            "message": f"İş akışı başlatıldı: {workflow_name}"
        }
    
    async def _action_complete_step(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Bir adımı tamamla ve sonraki adıma geç"""
        # Görev parametrelerini al
        params = task.get("params", {})
        instance_id = params.get("instance_id") or context.get("current_workflow_id")
        step_id = params.get("step_id")
        step_data = params.get("step_data", {})
        
        if not instance_id:
            raise ValueError("Workflow instance ID required")
        
        if not step_id:
            raise ValueError("Step ID required")
        
        # Workflow örneğini kontrol et
        if instance_id not in self.workflow_instances:
            raise ValueError(f"Workflow instance not found: {instance_id}")
        
        workflow = self.workflow_instances[instance_id]
        
        # Mevcut adımı kontrol et
        if workflow["current_step"] != step_id:
            raise ValueError(f"Current step is {workflow['current_step']}, not {step_id}")
        
        # Adım verisini doğrula
        current_step_info = None
        for step in self.workflow_steps:
            if step["step_id"] == step_id:
                current_step_info = step
                break
                
        if not current_step_info:
            raise ValueError(f"Step definition not found: {step_id}")
        
        # Gerekli girdileri kontrol et
        required_inputs = current_step_info.get("required_inputs", [])
        missing_inputs = []
        
        for input_name in required_inputs:
            if input_name not in step_data:
                missing_inputs.append(input_name)
        
        if missing_inputs:
            raise ValueError(f"Missing required inputs: {', '.join(missing_inputs)}")
        
        # Adım verisini kaydet
        if "data" not in workflow:
            workflow["data"] = {}
            
        workflow["data"][step_id] = step_data
        
        # Adım geçmişini güncelle
        for step_record in workflow["step_history"]:
            if step_record["step_id"] == step_id and step_record["status"] == "active":
                step_record["status"] = "completed"
                step_record["completed_at"] = time.time()
                step_record["data"] = step_data
                break
        
        # Tamamlanan adımlara ekle
        if "completed_steps" not in workflow:
            workflow["completed_steps"] = []
            
        workflow["completed_steps"].append(step_id)
        
        # Sonraki adımı belirle
        next_step_id = None
        
        # Geçiş kurallarını kontrol et
        if self.workflow_transitions:
            for transition in self.workflow_transitions:
                if transition["from_step"] == step_id:
                    # Koşul varsa değerlendir
                    if "condition" in transition:
                        # TODO: Koşul değerlendirme mekanizması eklenebilir
                        condition_met = True  # Basit olması için true kabul edelim
                        if condition_met:
                            next_step_id = transition["to_step"]
                            break
                    else:
                        # Koşulsuz geçiş
                        next_step_id = transition["to_step"]
                        break
        
        # Geçiş kuralı yoksa, sıradaki adıma geç
        if next_step_id is None:
            current_index = -1
            for i, step in enumerate(self.workflow_steps):
                if step["step_id"] == step_id:
                    current_index = i
                    break
            
            if current_index >= 0 and current_index < len(self.workflow_steps) - 1:
                next_step_id = self.workflow_steps[current_index + 1]["step_id"]
        
        response = {
            "instance_id": instance_id,
            "step_id": step_id,
            "status": "completed",
            "message": f"Adım tamamlandı: {step_id}"
        }
        
        # Sonraki adım var mı?
        if next_step_id:
            # Sonraki adım bilgilerini al
            next_step_info = None
            for step in self.workflow_steps:
                if step["step_id"] == next_step_id:
                    next_step_info = step
                    break
            
            if next_step_info:
                # Workflow örneğini güncelle
                workflow["current_step"] = next_step_id
                workflow["last_updated"] = time.time()
                
                # Adım geçmişine ekle
                workflow["step_history"].append({
                    "step_id": next_step_id,
                    "status": "active",
                    "started_at": time.time()
                })
                
                # Yanıta sonraki adım bilgilerini ekle
                response["next_step"] = {
                    "step_id": next_step_id,
                    "name": next_step_info["name"],
                    "description": next_step_info["description"],
                    "required_inputs": next_step_info.get("required_inputs", []),
                    "responsible_roles": next_step_info.get("responsible_roles", [])
                }
            else:
                logger.warning(f"Next step not found: {next_step_id}")
        else:
            # İş akışı tamamlandı
            workflow["status"] = "completed"
            workflow["completed_at"] = time.time()
            
            # Geçmişe ekle
            self.history.append(workflow.copy())
            
            # Aktif örneklerden kaldır
            # NOT: Hemen kaldırmak yerine bir süre tutup, sonra arşivleyebiliriz
            # del self.workflow_instances[instance_id]
            
            response["workflow_completed"] = True
            response["message"] = f"İş akışı tamamlandı: {workflow['workflow_name']}"
        
        return response
    
    async def _action_get_workflow_status(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """İş akışı durumunu al"""
        # Görev parametrelerini al
        params = task.get("params", {})
        instance_id = params.get("instance_id") or context.get("current_workflow_id")
        
        if not instance_id:
            raise ValueError("Workflow instance ID required")
        
        # Workflow örneğini kontrol et
        if instance_id not in self.workflow_instances:
            raise ValueError(f"Workflow instance not found: {instance_id}")
        
        workflow = self.workflow_instances[instance_id]
        
        # Mevcut adım bilgilerini al
        current_step_info = None
        for step in self.workflow_steps:
            if step["step_id"] == workflow["current_step"]:
                current_step_info = step
                break
        
        # İlerleme durumunu hesapla
        progress = 0
        if self.workflow_steps:
            completed_steps = len(workflow.get("completed_steps", []))
            total_steps = len(self.workflow_steps)
            progress = (completed_steps / total_steps) * 100
        
        return {
            "instance_id": instance_id,
            "workflow_name": workflow["workflow_name"],
            "status": workflow["status"],
            "created_at": workflow["created_at"],
            "last_updated": workflow["last_updated"],
            "current_step": {
                "step_id": workflow["current_step"],
                "name": current_step_info["name"] if current_step_info else "",
                "description": current_step_info["description"] if current_step_info else ""
            },
            "completed_steps": workflow.get("completed_steps", []),
            "progress": progress,
            "step_history": workflow.get("step_history", [])
        }
    
    async def _action_cancel_workflow(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """İş akışını iptal et"""
        # Görev parametrelerini al
        params = task.get("params", {})
        instance_id = params.get("instance_id") or context.get("current_workflow_id")
        reason = params.get("reason", "Kullanıcı tarafından iptal edildi")
        
        if not instance_id:
            raise ValueError("Workflow instance ID required")
        
        # Workflow örneğini kontrol et
        if instance_id not in self.workflow_instances:
            raise ValueError(f"Workflow instance not found: {instance_id}")
        
        workflow = self.workflow_instances[instance_id]
        
        # İş akışını iptal et
        workflow["status"] = "cancelled"
        workflow["cancelled_at"] = time.time()
        workflow["cancel_reason"] = reason
        
        # Geçmişe ekle
        self.history.append(workflow.copy())
        
        # Aktif örneklerden kaldır
        # del self.workflow_instances[instance_id]
        
        return {
            "instance_id": instance_id,
            "status": "cancelled",
            "message": f"İş akışı iptal edildi: {reason}"
        }
    
    # ----- UTILITY METHODS -----
    
    def get_workflow_definition(self) -> Dict[str, Any]:
        """İş akışı tanımını döndür"""
        return {
            "name": self.name,
            "description": self.description,
            "steps": self.workflow_steps,
            "transitions": self.workflow_transitions
        }
    
    def get_workflow_statistics(self) -> Dict[str, Any]:
        """İş akışı istatistiklerini döndür"""
        total_instances = len(self.history) + len(self.workflow_instances)
        active_instances = len(self.workflow_instances)
        completed_instances = len([wf for wf in self.history if wf.get("status") == "completed"])
        cancelled_instances = len([wf for wf in self.history if wf.get("status") == "cancelled"])
        
        return {
            "total_instances": total_instances,
            "active_instances": active_instances,
            "completed_instances": completed_instances,
            "cancelled_instances": cancelled_instances
        }