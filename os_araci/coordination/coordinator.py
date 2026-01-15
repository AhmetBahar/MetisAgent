# os_araci/coordination/coordinator.py - tam hali

import logging
import json
import asyncio
import traceback
from os_araci.a2a_protocol.registry import A2ARegistry
from os_araci.a2a_protocol.message import A2AMessage
from os_araci.mcp_core.registry import MCPRegistry
from os_araci.websocket.event_emitter import EventEmitter

logger = logging.getLogger(__name__)

class MCPCoordinator:
    def __init__(self, registry=None, event_emitter=None):
        self.registry = registry or MCPRegistry()
        self.context_values = {}  # Task çıktılarını saklamak için
        self.event_emitter = event_emitter  # WebSocket event emitter

    
    async def run_tasks_with_llm_feedback(self, tasks):
        """
        LLM geri bildirimi ile görevleri çalıştır
        """
        logger.info(f"Starting task execution with LLM feedback - {len(tasks)} tasks")
        completed_tasks = []
        remaining_tasks = tasks.copy()
        
        while remaining_tasks:
            # Bir sonraki çalıştırılabilir görevi seç
            next_task = self._select_next_executable_task(remaining_tasks, completed_tasks)
            
            if not next_task:
                logger.warning("No executable task found")
                break
            
            logger.info(f"Running task: {next_task.get('name', 'Unnamed task')} (ID: {next_task.get('id', 'no-id')})")
            
            # Görevi çalıştır
            result = await self._execute_task(next_task)
            
            # Değerlendirme sonucuna göre alternatif komut var mı kontrol et
            evaluation = result.get("evaluation", {})
            if evaluation.get("retryRecommended") and evaluation.get("alternativeCommand"):
                alternative_cmd = evaluation.get("alternativeCommand")
                task_id = next_task.get("id")
                
                logger.info(f"Task {task_id} failed. Trying alternative command: {alternative_cmd}")
                
                # Yeni bir alternatif görev oluştur
                retry_task = next_task.copy()
                retry_task["id"] = f"{task_id}-retry"
                retry_task["name"] = f"{next_task.get('name')} (Retry)"
                retry_task["description"] = f"Alternatif komut ile {next_task.get('description', '')}"
                
                # Komut tipine göre alternatif komutu ayarla
                if next_task.get("tool") == "command_executor":
                    retry_task["params"] = retry_task.get("params", {}).copy()
                    retry_task["params"]["command"] = alternative_cmd
                elif next_task.get("type") == "command":
                    retry_task["command"] = alternative_cmd
                
                logger.info(f"Created retry task: {retry_task.get('name')} with command: {alternative_cmd}")
                
                # Alternatif görevi çalıştır
                retry_result = await self._execute_task(retry_task)
                
                # Alternatif görev başarılı olduysa, bu sonucu kullan
                if retry_result.get("evaluation", {}).get("success", False):
                    logger.info(f"Retry task successful: {retry_task.get('id')}")
                    result = retry_result
                    next_task = retry_task  # Tamamlanan görevlere alternatif görevi ekle
                else:
                    logger.warning(f"Retry task failed: {retry_task.get('id')}")
                    # Alternatif görevin sonucunu log'a ekle ama original görevle devam et
                    self.context_values[f"task_{task_id}_retry_result"] = retry_result
            
            # Sonucu kaydet
            task_result = {
                "task": next_task,
                "result": result,
                "status": result.get("status", "unknown")
            }
            
            completed_tasks.append(task_result)
            logger.info(f"Task completed: {next_task.get('name')} with status: {task_result['status']}")
            
            # Görevi kaldır
            remaining_tasks = [task for task in remaining_tasks if task.get("id") != next_task.get("id")]
            
            # Eğer daha fazla görev varsa, LLM'den geri bildirim al
            if remaining_tasks:
                llm_feedback = await self._get_llm_feedback_on_tasks(completed_tasks, remaining_tasks)
                
                # LLM geri bildirimine göre görevleri güncelle
                updated_tasks = self._update_remaining_tasks(remaining_tasks, llm_feedback)
                
                # Görev listesi değişti mi kontrol et
                if len(updated_tasks) != len(remaining_tasks):
                    logger.info(f"Task list updated by LLM: {len(remaining_tasks)} -> {len(updated_tasks)} tasks")
                
                remaining_tasks = updated_tasks
            
            # Context'i güncelle
            self._update_context_for_completed_tasks(completed_tasks)
        
        logger.info(f"All tasks completed with LLM feedback: {len(completed_tasks)} tasks")
        return completed_tasks

    def _update_context_for_completed_tasks(self, completed_tasks):
        """
        Tamamlanan görevlere göre context'i günceller ve task output placeholder'ları için hazırlar
        """
        for task_result in completed_tasks:
            task = task_result.get("task", {})
            result = task_result.get("result", {})
            task_id = task.get("id")
            
            if task_id:
                # Çıktıyı belirle
                output_text = ""
                if isinstance(result, dict):
                    # Önce direkt output field'e bak
                    output_text = result.get("output", "")
                    
                    # Output yoksa result içinde ayrı bir sonuç objesi olabilir
                    if not output_text and "result" in result and isinstance(result["result"], dict):
                        output_text = result["result"].get("output", "")
                    
                    # Hala bulunamadıysa message field'e bak
                    if not output_text:
                        output_text = result.get("message", str(result))
                else:
                    output_text = str(result)
                
                # Context'e kaydet - hem ID hem de indeks formatında
                self.context_values[f"task_{task_id}_output"] = output_text
                
                # Retry task ID'leri için de orijinal task ID'sine referans ekle
                if "-retry" in task_id:
                    original_id = task_id.split("-retry")[0]
                    self.context_values[f"task_{original_id}_output"] = output_text
                    
                logger.debug(f"Updated context: task_{task_id}_output = {output_text[:100]}...")

    async def _get_alternative_command(self, failed_task, result):
        """Başarısız bir komut için LLM'den alternatif komut ister"""
        llm_tool = self.registry.get_tool("llm_tool")
        if not llm_tool:
            return None
        
        command = failed_task.get("command") or (failed_task.get("params", {}).get("command", ""))
        error_msg = result.get("message", "Unknown error")
        
        prompt = f"""
        Aşağıdaki komut başarısız oldu:
        
        KOMUT: {command}
        HATA: {error_msg}
        
        Lütfen bu komutu düzeltmek için alternatif bir komut öner. Sadece komutu döndür, açıklama yapma.
        """
        
        try:
            response = llm_tool.generate_text(
                prompt=prompt,
                provider="openai",
                model="gpt-4o-mini",
                temperature=0.2
            )
            
            if isinstance(response, dict) and "text" in response:
                return response["text"].strip()
            return response.strip()
        except Exception as e:
            logger.error(f"Alternative command generation failed: {str(e)}")
            return None

    async def _get_llm_feedback_on_tasks(self, completed_tasks, remaining_tasks):
        """
        Son tamamlanan görev ve sonuçlarına göre LLM'den geri bildirim al
        """
        # Son tamamlanan görev
        last_completed_task = completed_tasks[-1] if completed_tasks else None
        
        logger.info(f"Getting LLM feedback after task: {last_completed_task['task'].get('name') if last_completed_task else 'None'}")
        
        # LLM'e gönderilecek context (JSON serializable olması için basitleştirelim)
        context = {
            "completedTasks": [
                {
                    "task": {
                        "id": item["task"].get("id"),
                        "name": item["task"].get("name"),
                        "description": item["task"].get("description", ""),
                        "type": item["task"].get("type", "command"),
                        "command": item["task"].get("command", ""),
                        "tool": item["task"].get("tool", ""),
                        "action": item["task"].get("action", ""),
                        "params": item["task"].get("params", {})
                    },
                    "status": item["status"],
                    "result": item["result"] if isinstance(item["result"], dict) else {"output": str(item["result"])}
                }
                for item in completed_tasks
            ],
            "lastTaskResult": (
                {
                    "status": last_completed_task["status"],
                    "result": last_completed_task["result"] if isinstance(last_completed_task["result"], dict) else {"output": str(last_completed_task["result"])}
                }
                if last_completed_task else None
            ),
            "remainingTasks": remaining_tasks
        }
        
        # System prompt oluştur
        system_prompt = """
        Bir otomasyon görev yöneticisi olarak çalışıyorsun. Tamamlanmış görevleri ve sonuçlarını, 
        ayrıca kalan görevleri değerlendirerek en iyi sonraki adımlara karar ver.
        
        Son çalıştırılan görevin sonucuna dayanarak:
        1. Kalan görevlerin hala geçerli olup olmadığını değerlendir
        2. Gerekirse görevlerin parametrelerini güncelle
        3. Gerekirse yeni görevler ekle
        4. Gerekirse artık ihtiyaç duyulmayan görevleri kaldır
        
        Yanıtını aşağıdaki JSON formatında ver:
        {
          "continuePlan": true veya false,
          "addTasks": [ yeni görevler ],
          "modifyTasks": [ değiştirilmiş görevler ],
          "removeTasks": [ kaldırılacak görev ID'leri ],
          "reasoning": "Kararlarının detaylı açıklaması"
        }
        """
        
        # LLM Tool'u al
        llm_tool = self.registry.get_tool("llm_tool")
        if not llm_tool:
            logger.error("LLM Tool not found")
            return {
                "continuePlan": True,
                "addTasks": [],
                "modifyTasks": [],
                "removeTasks": [],
                "reasoning": "LLM Tool not found, continuing with original plan."
            }
            
        # LLM'den yanıt al
        try:
            # JSON serileştirme içinde güvenlik kontrolleri
            prompt = json.dumps(context, default=str)
            
            logger.info("Calling LLM for feedback")
            response_data = llm_tool.generate_text(
                prompt=prompt,
                provider="openai",  # Default provider
                system_prompt=system_prompt,
                temperature=0.2
            )
            
            response = response_data.get("text", "")
            logger.info(f"LLM feedback received: {response[:100]}...")  # İlk 100 karakter
            
            # Yanıtı JSON olarak ayrıştır
            try:
                # JSON string'i çıkar
                if "```json" in response:
                    json_str = response.split("```json")[1].split("```")[0].strip()
                elif "```" in response:
                    json_str = response.split("```")[1].split("```")[0].strip()
                else:
                    json_str = response.strip()
                    
                feedback = json.loads(json_str)
                logger.info(f"Parsed LLM feedback: {feedback.keys()}")
                return feedback
            except json.JSONDecodeError:
                logger.error(f"LLM response could not be parsed as JSON: {response}")
                # Bir hata olursa devam et (mevcut plan değişmeden)
                return {
                    "continuePlan": True,
                    "addTasks": [],
                    "modifyTasks": [],
                    "removeTasks": [],
                    "reasoning": "LLM response could not be parsed, continuing with original plan."
                }
        except Exception as e:
            logger.error(f"Error getting LLM feedback: {str(e)}")
            logger.error(traceback.format_exc())
            # Bir hata olursa devam et (mevcut plan değişmeden)
            return {
                "continuePlan": True,
                "addTasks": [],
                "modifyTasks": [],
                "removeTasks": [],
                "reasoning": f"Error getting LLM feedback: {str(e)}"
            }

    def _update_remaining_tasks(self, remaining_tasks, llm_feedback):
        """
        LLM geri bildirimine göre kalan görevleri güncelle
        """
        # Eğer devam etmememiz gerekiyorsa boş liste döndür
        if not llm_feedback.get("continuePlan", True):
            logger.info("LLM suggested to stop execution")
            return []
        
        updated_tasks = remaining_tasks.copy()
        
        # Yeni görevleri ekle
        if "addTasks" in llm_feedback and llm_feedback["addTasks"]:
            logger.info(f"Adding {len(llm_feedback['addTasks'])} new tasks from LLM")
            # Her yeni görev için benzersiz ID ekle
            for new_task in llm_feedback["addTasks"]:
                if "id" not in new_task:
                    new_task["id"] = f"task-{id(new_task)}"
            updated_tasks.extend(llm_feedback["addTasks"])
        
        # Mevcut görevleri güncelle
        if "modifyTasks" in llm_feedback and llm_feedback["modifyTasks"]:
            logger.info(f"Modifying {len(llm_feedback['modifyTasks'])} tasks based on LLM feedback")
            for i, task in enumerate(updated_tasks):
                for mod_task in llm_feedback["modifyTasks"]:
                    if task.get("id") == mod_task.get("id"):
                        # Değişiklikleri uygula, ancak ID'yi koru
                        mod_task_copy = mod_task.copy()
                        task_id = task.get("id")
                        updated_tasks[i] = mod_task_copy
                        updated_tasks[i]["id"] = task_id
                        logger.info(f"Modified task {task_id}: {task.get('name')} -> {mod_task_copy.get('name')}")
        
        # Görevleri kaldır
        if "removeTasks" in llm_feedback and llm_feedback["removeTasks"]:
            removed_ids = llm_feedback["removeTasks"]
            logger.info(f"Removing {len(removed_ids)} tasks based on LLM feedback: {removed_ids}")
            updated_tasks = [
                task for task in updated_tasks 
                if task.get("id") not in removed_ids
            ]
        
        return updated_tasks

    def _select_next_executable_task(self, remaining_tasks, completed_tasks):
        """
        Kalan görevler arasından, tüm bağımlılıkları tamamlanmış bir sonraki görevi seç
        """
        completed_task_ids = [task["task"].get("id") for task in completed_tasks]
        
        for task in remaining_tasks:
            dependencies = task.get("dependencies", [])
            
            # Bağımlılık kontrolü - boş liste veya tümü tamamlanmış mı?
            if not dependencies or all(dep in completed_task_ids for dep in dependencies):
                logger.info(f"Selected next task: {task.get('name')} (ID: {task.get('id')})")
                return task
        
        logger.warning("No executable tasks found - dependency chain may be broken")
        return None
        
    async def _execute_task(self, task, llm_settings=None):
        """
        Bir görevi çalıştırır ve placeholder'ları günceller
        """
        logger.info(f"Executing task: {task.get('name')} (ID: {task.get('id')})")
        
        if self.event_emitter:
            # Async event emitter için wrapper
            def emit_event(event_type, data):
                if self.event_emitter:
                    self.event_emitter.emit(event_type, data)
            
            emit_event('task_started', {
                'task_id': task.get('id'),
                'task_name': task.get('name'),
                'task_type': task.get('type')
            })

        try:
            # Önce parametrelerdeki placeholder'ları değiştir
            processed_task = self._process_task_with_context(task)
            
            # Task türünü belirle
            task_type = processed_task.get("type", "command")
            
            # Görev çalıştırma sonucu
            result = None
            
            # Komut çalıştırma tipindeki görevler için
            if task_type == "command" and processed_task.get("command"):
                command_tool = self.registry.get_tool("command_executor")
                if not command_tool:
                    logger.error("Command executor tool not found")
                    return {"status": "error", "message": "Command executor tool not found"}
                
                logger.info(f"Executing command: {processed_task.get('command')}")
                result = command_tool.execute_command(command=processed_task.get("command"))
                logger.info(f"Command result: {result.get('status')}")
                
            # Tool-action-params tipindeki görevler için
            elif processed_task.get("tool") and processed_task.get("action"):
                tool_name = processed_task.get("tool")
                action_name = processed_task.get("action")
                params = processed_task.get("params", {})
                
                # Noktalı format kontrolü
                if "." in tool_name:
                    parts = tool_name.split(".")
                    tool_name = parts[0]
                    action_name = parts[1]
                
                # Özel durum: command_executor aracı
                if tool_name == "command_executor":
                    command_tool = self.registry.get_tool("command_executor")
                    if not command_tool:
                        logger.error("Command executor tool not found")
                        return {"status": "error", "message": "Command executor tool not found"}
                    
                    logger.info(f"Executing command via tool: {params.get('command')}")
                    result = command_tool.execute_command(**params)
                    logger.info(f"Command result: {result.get('status')}")
                    
                else:
                    # Aracı al
                    tool = self.registry.get_tool(tool_name)
                    if not tool:
                        logger.error(f"Tool not found: {tool_name}")
                        return {"status": "error", "message": f"Tool {tool_name} not found"}
                    
                    # Aksiyonu çalıştır
                    try:
                        result = tool.execute_action(action_name, **params)
                    except Exception as action_error:
                        logger.error(f"Error executing {tool_name}.{action_name}: {str(action_error)}")
                        return {"status": "error", "message": str(action_error)}
                    
                    logger.info(f"Result from {tool_name}.{action_name}: {result.get('status') if isinstance(result, dict) else 'unknown'}")
            
            else:
                logger.error(f"Invalid task format: {processed_task}")
                return {"status": "error", "message": "Invalid task format: missing command or tool/action"}
            
            # Çıktıyı context'e kaydet
            updated_context = self._save_to_context(task, result)
            
            # LLM ile değerlendirme yap
            evaluation = await self._evaluate_task_result(task, result, llm_settings)
            
            if self.event_emitter:
                emit_event('task_completed', {
                    'task_id': task.get('id'),
                    'status': result.get('status'),
                    'result': result
                })
            # Sonuç ve değerlendirmeyi döndür
            return {
                "status": "success",
                "result": result,
                "evaluation": evaluation,
                "context": updated_context
            }
                    
        except Exception as e:
            error_details = traceback.format_exc()
            logger.error(f"Task execution error: {str(e)}\n{error_details}")
            
            # Hata durumunu kaydet
            self.context_values[f"task_{task.get('id')}_error"] = str(e)
            self.context_values[f"task_{task.get('id')}_success"] = False
            
            if self.event_emitter:
                emit_event('task_error', {
                    'task_id': task.get('id'),
                    'status': result.get('status'),
                    'result': result
                })
            
            return {
                "status": "error", 
                "message": str(e),
                "traceback": error_details,
                "context": self.context_values
            }    
        
    def _process_task_with_context(self, task):
        """Görev parametrelerindeki placeholder'ları değiştirir"""
        import re
        
        # Deep copy ile yeni bir task oluştur
        from copy import deepcopy
        processed_task = deepcopy(task)
        
        # Parametreleri işle
        if processed_task.get("params"):
            for key, value in processed_task["params"].items():
                if isinstance(value, str):
                    # <task-2_output> formatındaki placeholder'ları ara
                    matches = re.findall(r'<task-(\d+)_output>', value)
                    for task_index in matches:
                        placeholder = f"<task-{task_index}_output>"
                        context_key = f"task-{task_index}_output"
                        
                        # Context'te varsa değiştir
                        if context_key in self.context_values:
                            processed_task["params"][key] = value.replace(
                                placeholder, 
                                str(self.context_values[context_key])
                            )
                            logger.info(f"Replaced placeholder {placeholder} with context value")
                    
                    # <task_ID_output> formatındaki placeholder'ları ara
                    matches = re.findall(r'<task_([^>]+)_output>', value)
                    for task_id in matches:
                        placeholder = f"<task_{task_id}_output>"
                        context_key = f"task_{task_id}_output"
                        
                        # Context'te varsa değiştir
                        if context_key in self.context_values:
                            processed_task["params"][key] = value.replace(
                                placeholder, 
                                str(self.context_values[context_key])
                            )
                            logger.info(f"Replaced placeholder {placeholder} with context value")
        
        return processed_task

    def _save_to_context(self, task, result):
        """Task sonuçlarını context'e kaydeder ve placeholder'ları günceller"""
        task_id = task.get("id")
        
        if task_id:
            # Çıktıyı belirle - output, message veya tüm result
            output_text = ""
            if isinstance(result, dict):
                output_text = result.get("output", result.get("message", str(result)))
            else:
                output_text = str(result)
            
            # Context'e kaydet - hem ID hem de indeks formatında
            self.context_values[f"task_{task_id}_output"] = output_text
            
            # Diğer context bilgilerini ekle (başarı durumu, özet vb.)
            if isinstance(result, dict):
                # Başarı durumu
                self.context_values[f"task_{task_id}_success"] = result.get("success", 
                    result.get("status", "") == "success")
                
                # Hata mesajı
                if "error" in result:
                    self.context_values[f"task_{task_id}_error"] = result.get("error")
            
            # Indeks formatında da ekle (eski kod uyumluluğu için)
            try:
                task_index = int(task_id.split('-')[-1])
                self.context_values[f"task-{task_index}_output"] = output_text
                logger.info(f"Saved task output to context: task-{task_index}_output = {output_text[:50]}...")
            except (ValueError, IndexError, AttributeError):
                # ID formatı farklıysa veya parse edilemezse bu adımı atla
                pass
            
            logger.debug(f"Güncel context içeriği: {self.context_values}")
            return self.context_values
        
    async def _evaluate_task_result(self, task, result, llm_settings=None):
        """LLM kullanarak görev sonucunu değerlendirir"""
        task_id = task.get("id")
        output_text = ""
        
        if isinstance(result, dict):
            output_text = result.get("output", result.get("message", str(result)))
        else:
            output_text = str(result)
        
        # LLM Tool'u al
        llm_tool = self.registry.get_tool("llm_tool")
        if not llm_tool:
            logger.warning("LLM Tool not found for task evaluation")
            return {
                "success": result.get("success", True),
                "error": None,
                "summary": "No evaluation available",
                "shouldContinue": True
            }
        
        # Kodu çalıştırma hatası olması durumunda alternatif komut önerme ekle
        is_command_execution = task.get("tool") == "command_executor" or task.get("type") == "command"
        command_str = task.get("command", "") or (task.get("params", {}).get("command", ""))
        has_error = "error" in result or output_text.lower().find("error") >= 0 or result.get("status") == "error"
        
        evaluation_prompt = f"""
        Aşağıdaki komut çıktısını analiz et ve JSON formatında bir değerlendirme yap.
        
        GÖREV: {task.get('name')}
        AÇIKLAMA: {task.get('description', 'Belirtilmemiş')}
        KOMUT: {command_str}
        ÇIKTI:
        {output_text}
        
        Analiz sonucunu aşağıdaki JSON formatında dön:
        {{
        "success": boolean,  // Komut başarılı mı? (true/false)
        "error": string,     // Hata varsa açıklaması (yoksa null)
        "summary": string,   // Çıktının kısa özeti (1-2 cümle)
        "shouldContinue": boolean,  // Sonraki adımlara devam edilmeli mi?
        "recommendation": string,   // Sonraki adımlar için öneri
        "alternativeCommand": string  // Eğer komut hatalıysa alternatif komut (yoksa null)
        }}
        
        Özellikle hatayı iyi analiz et. Örneğin:
        - Eğer 'python' komutu hata veriyorsa, 'python3' komutunu öner
        - Eğer dosya bulunamadıysa, doğru yolu kontrol et
        - Eğer izin hatası varsa, gerekli izinlerin verilmesini öner
        
        Başarısız bir görev için alternatif komutu MUTLAKA doldur, diğer durumlarda null olabilir.
        
        Sadece geçerli JSON döndür.
        """
        
        try:
            # LLM değerlendirmesi alın
            provider = "openai"
            model = "gpt-4o-mini"  
            temperature = 0.7
            
            if llm_settings:
                provider = llm_settings.get("provider", provider)
                model = llm_settings.get("model", model)
                temperature = llm_settings.get("temperature", temperature)

            evaluation_response = llm_tool.generate_text(
                prompt=evaluation_prompt,
                provider=provider,
                model=model,
                system_prompt="Sen bir sistem çıktısı değerlendirme asistanısın. JSON formatında yanıt ver.",
                temperature=temperature
            )
            
            # Yanıtı JSON olarak parse et
            if isinstance(evaluation_response, dict) and "text" in evaluation_response:
                response_text = evaluation_response.get("text", "")
            else:
                response_text = evaluation_response
            
            try:
                # JSON yanıtını temizle ve parse et
                clean_json = response_text.replace("```json", "").replace("```", "").strip()
                evaluation_json = json.loads(clean_json)
                
                # Alternatif komut kontrolü ekle
                # Eğer başarısız ve alternatif komut önerilmişse, yeni bir görev oluştur
                if is_command_execution and not evaluation_json.get("success", True) and evaluation_json.get("alternativeCommand"):
                    alternative_cmd = evaluation_json.get("alternativeCommand")
                    logger.info(f"Task {task_id} failed. Trying alternative command: {alternative_cmd}")
                    
                    # Alternatif komutu context'e kaydet
                    self.context_values[f"task_{task_id}_alternative_command"] = alternative_cmd
                    evaluation_json["retryRecommended"] = True
                else:
                    evaluation_json["retryRecommended"] = False
                
                # Context'e kaydet
                self.context_values[f"task_{task_id}_evaluation"] = evaluation_json
                self.context_values[f"task_{task_id}_success"] = evaluation_json.get("success", True)
                self.context_values[f"task_{task_id}_error"] = evaluation_json.get("error")
                self.context_values[f"task_{task_id}_summary"] = evaluation_json.get("summary", "")
                self.context_values[f"task_{task_id}_should_continue"] = evaluation_json.get("shouldContinue", True)
                
                # Sonucu logla
                logger.info(f"Task evaluation: {evaluation_json.get('summary')}")
                return evaluation_json
                
            except json.JSONDecodeError:
                logger.error(f"Failed to parse LLM evaluation response: {response_text}")
                return {
                    "success": True,
                    "error": None,
                    "summary": "Evaluation response could not be parsed",
                    "shouldContinue": True,
                    "retryRecommended": False
                }
                
        except Exception as e:
            logger.error(f"Error during task evaluation: {str(e)}")
            return {
                "success": True,
                "error": str(e),
                "summary": "Error occurred during evaluation",
                "shouldContinue": True,
                "retryRecommended": False
            }
        
    async def send_task_to_persona(self, task, persona_id):
        """Görevi bir persona ajanına gönder"""
        a2a_registry = A2ARegistry()
        
        # Görev içeriğini hazırla
        task_content = {
            "task": task,
            "context": self.context_values.copy()
        }
        
        # Mesajı oluştur ve gönder
        message_id = await a2a_registry.send_message(
            A2AMessage(
                sender="coordinator",
                receiver=persona_id,
                message_type="task.request",
                content=task_content
            )
        )
        
        if not message_id:
            logger.error(f"Görev personaya gönderilemedi: {persona_id}")
            return {
                "status": "error",
                "message": f"Failed to send task to persona: {persona_id}"
            }
        
        logger.info(f"Görev personaya gönderildi: {persona_id}, mesaj ID: {message_id}")
        
        # Yanıt bekle (gelecekte implement edilecek)
        # Bu şimdilik basit bir örnek implementasyon
        future = asyncio.Future()
        
        # Yanıt dinleyicisi
        async def task_response_handler(message):
            if (message.message_type == "task.response" and 
                message.correlation_id == message_id and
                message.sender == persona_id):
                
                # Context'i güncelle (eğer varsa)
                if "context_updates" in message.content:
                    self.context_values.update(message.content["context_updates"])
                
                # Future'ı tamamla
                if not future.done():
                    future.set_result(message.content)
        
        # Dinleyiciyi kaydet
        a2a_registry.register_listener("task.response", task_response_handler)
        
        try:
            # Yanıtı bekle (timeout ile)
            result = await asyncio.wait_for(future, timeout=120.0)
            return result
        except asyncio.TimeoutError:
            logger.error(f"Görev yanıtı zaman aşımına uğradı: {persona_id}")
            return {
                "status": "error",
                "message": "Task response timed out"
            }
        finally:
            # Dinleyiciyi kaldır
            a2a_registry.unregister_listener("task.response", task_response_handler)
    
    def select_persona_for_task(self, task):
        """Görev için en uygun personayı seç"""
        # Bu şimdilik basit bir örnek implementasyon
        # Gerçek implementasyonda görev tipi, yetenekler vb. analiz edilir
        
        # Görevin tipini ve gerekli yetenekleri analiz et
        task_type = task.get("type", "")
        required_capabilities = []
        
        if "command" in task:
            task_type = "command"
            if "file" in task["command"].lower():
                required_capabilities.append("file_management")
            if "network" in task["command"].lower():
                required_capabilities.append("network_management")
        
        # Tüm personaları listele
        a2a_registry = A2ARegistry()
        all_personas = []
        
        for persona_id in a2a_registry.list_personas():
            persona = a2a_registry.get_persona(persona_id)
            if persona:
                all_personas.append(persona)
        
        # En uygun personayı bul
        best_persona = None
        best_match_score = -1
        
        for persona in all_personas:
            # Basit bir puanlama algoritması
            score = 0
            
            # Yeteneklere göre puan ver
            for capability in required_capabilities:
                if capability in persona.capabilities:
                    score += 2
            
            # Önceliğe göre puan ver
            score += persona.priority / 2
            
            # En iyi puanı alan personayı seç
            if score > best_match_score:
                best_match_score = score
                best_persona = persona
        
        if best_persona:
            return best_persona.persona_id
        
        # Hiçbir uygun persona bulunamadı, varsayılan persona'yı döndür
        return "default_executor"