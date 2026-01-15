"""
Task and execution related routes extracted from app_old.py
Handles task execution, coordination, and command execution endpoints
"""

from flask import Blueprint, request, jsonify
import subprocess
import platform
import logging
import os
from os_araci.core.event_loop_manager import run_async

# Create blueprint
task_bp = Blueprint('task', __name__)

# Logger setup
logger = logging.getLogger(__name__)

# Global variables (should be injected/configured)
coordinator = None
registry = None

def init_task_routes(coordinator_instance, registry_instance):
    """Initialize task routes with required dependencies"""
    global coordinator, registry
    coordinator = coordinator_instance
    registry = registry_instance

# ===============================
# TASK EXECUTION ENDPOINTS
# ===============================

@task_bp.route('/api/task/execute', methods=['POST'])
def execute_task():
    """Tek bir görevi çalıştır"""
    try:
        data = request.get_json()
        task = data.get('task')
        
        if not task:
            return jsonify({'error': 'Task required'}), 400
        
        result = coordinator.execute_task(task)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Görev çalıştırma hatası: {str(e)}")
        return jsonify({'error': str(e)}), 500

@task_bp.route('/api/task/execute_with_context', methods=['POST'])
def execute_task_with_context():
    """Placeholder güncelleme ve LLM değerlendirmesi ile görev çalıştırır"""
    try:
        data = request.get_json()
        task = data.get('task')
        clear_context = data.get('clear_context', False)
        llm_settings = data.get('llm_settings', {}) 

        if not task:
            return jsonify({'error': 'Task required'}), 400
        
        if clear_context:
            coordinator.context_values = {}
        
        result = run_async(coordinator._execute_task(task, llm_settings))
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Görev çalıştırma hatası: {str(e)}")
        return jsonify({'error': str(e)}), 500

@task_bp.route('/api/tasks/execute', methods=['POST'])
def execute_tasks():
    """Birden fazla görevi çalıştır"""
    try:
        data = request.get_json()
        tasks = data.get('tasks', [])
        mode = data.get('mode', 'sequential')
        
        if not tasks:
            return jsonify({'error': 'Tasks required'}), 400
        
        if data.get('clear_context', False):
            coordinator.clear_context()
        
        results = coordinator.execute_tasks(tasks, mode)
        return jsonify({'results': results})
    except Exception as e:
        logger.error(f"Görevleri çalıştırma hatası: {str(e)}")
        return jsonify({'error': str(e)}), 500

@task_bp.route('/api/tasks/execute_sequential', methods=['POST'])
def execute_tasks_sequential():
    """Görevleri sırayla çalıştırır, context'i güncelleyerek ilerler"""
    try:
        data = request.get_json()
        tasks = data.get('tasks', [])
        fail_strategy = data.get('fail_strategy', 'continue')
        
        if not tasks:
            return jsonify({'error': 'Tasks required'}), 400
        
        if data.get('clear_context', True):
            coordinator.context_values = {}
        
        results = []
        
        for task in tasks:
            result = run_async(coordinator._execute_task(task))
            results.append(result)
            
            if result.get('status') == 'error' or (
                result.get('evaluation', {}).get('success') == False and 
                result.get('evaluation', {}).get('shouldContinue') == False):
                
                if fail_strategy == 'stop':
                    break
        
        return jsonify({
            'status': 'success',
            'results': results,
            'context': coordinator.context_values
        })
    except Exception as e:
        logger.error(f"Görevleri çalıştırma hatası: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ===============================
# COORDINATOR ENDPOINTS
# ===============================

@task_bp.route('/api/coordinator/run_tasks_with_feedback', methods=['POST'])
def run_tasks_with_feedback_endpoint():
    """LLM geri bildirimi ile görevleri çalıştır API'si"""
    data = request.json
    tasks = data.get('tasks', [])
    
    try:
        result = run_async(coordinator.run_tasks_with_llm_feedback(tasks))
        
        standardized_result = []
        for task_result in result:
            if isinstance(task_result, dict) and 'task' in task_result and 'result' in task_result:
                if 'status' not in task_result:
                    if isinstance(task_result['result'], dict):
                        status = task_result['result'].get('status', 'unknown')
                    else:
                        status = 'unknown'
                    task_result['status'] = status
                
                standardized_result.append(task_result)
        
        return jsonify({
            "status": "success",
            "result": standardized_result
        })
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error running tasks with LLM feedback: {str(e)}\n{error_details}")
        return jsonify({
            "error": str(e), 
            "details": error_details,
            "status": "error"
        }), 500

# ===============================
# COMMAND EXECUTION ENDPOINTS
# ===============================

@task_bp.route('/api/command/execute', methods=['POST'])
def execute_command():
    """Güvenli bir şekilde sistem komutu çalıştır"""
    try:
        data = request.get_json()
        command = data.get('command', '')
        working_dir = data.get('workingDir')
        timeout = data.get('timeout', 30)
        
        if not command:
            return jsonify({'error': 'Empty command'}), 400
        
        current_os = platform.system()
        
        dangerous_commands = []
        
        if current_os == 'Windows':
            dangerous_commands = [
                'rmdir /s /q C:', 'del /f /s /q C:', 'format C:', 
                'rd /s /q C:', '> C:', 'del /f /s /q', 
                'format', 'shutdown', 'rd /s /q', 'reg delete',
                'wmic process call create', 'net user', 'taskkill /f',
                'rundll32', 'wmic process delete', 'vssadmin delete shadows'
            ]
        else:
            dangerous_commands = [
                'rm -rf /', 'rm -rf /*', 'rm -rf ~', 'rm -rf .', 
                'dd if=/dev/zero', 'mkfs', ':(){:|:&};:', '> /dev/sda',
                'chmod -R 777 /', 'mv /* /dev/null', 'wget -O- | sh',
                'curl | sh', '$(curl', '$(wget', 'eval', 'sudo rm'
            ]
        
        for dangerous in dangerous_commands:
            if dangerous in command:
                logger.warning(f"Tehlikeli komut engellendi: {command}")
                return jsonify({'error': 'Dangerous command detected'}), 403
        
        if command.startswith(('file_', 'dir_', 'get_', 'execute_', 'schedule_')):
            return handle_metis_tool_command(command)
        
        logger.info(f"Komut çalıştırılıyor: {command}")
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=working_dir,
            text=True
        )
        
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            
            if process.returncode != 0:
                logger.warning(f"Komut hata kodu ile tamamlandı: {process.returncode}")
                return jsonify({
                    'success': False,
                    'output': stderr or stdout,
                    'returnCode': process.returncode
                }), 200
            
            logger.info(f"Komut başarıyla tamamlandı (kod: {process.returncode})")
            return jsonify({
                'success': True,
                'output': stdout,
                'returnCode': process.returncode
            }), 200
            
        except subprocess.TimeoutExpired:
            process.kill()
            logger.warning(f"Komut zaman aşımına uğradı ({timeout} saniye)")
            return jsonify({
                'success': False,
                'output': f'Command timed out after {timeout} seconds',
                'returnCode': -1
            }), 200
            
    except Exception as e:
        logger.error(f"Komut çalıştırma hatası: {str(e)}")
        return jsonify({
            'success': False,
            'output': f'Error executing command: {str(e)}',
            'returnCode': -1
        }), 500

def handle_metis_tool_command(command):
    """Metis Agent'a özel komutları işleyen yardımcı fonksiyon"""
    try:
        cmd_parts = command.split('(')
        cmd_name = cmd_parts[0]
        params = cmd_parts[1].rstrip(')').replace('"', '').split(',')
        
        logger.info(f"Metis özel komutu çalıştırılıyor: {cmd_name} - Parametreler: {params}")
        
        if cmd_name == 'file_list':
            path = params[0].strip()
            file_tool = None
            for tool_id, metadata in registry.get_all_metadata().items():
                if metadata.name == 'file_manager':
                    file_tool = registry.get_tool_by_id(tool_id)
                    break
                    
            if file_tool:
                result = file_tool.execute_action('list_files', path=path)
            else:
                result = '\n'.join(os.listdir(path))
        
        elif cmd_name == 'file_read':
            path = params[0].strip()
            file_tool = None
            for tool_id, metadata in registry.get_all_metadata().items():
                if metadata.name == 'file_manager':
                    file_tool = registry.get_tool_by_id(tool_id)
                    break
                    
            if file_tool:
                result = file_tool.execute_action('read_file', path=path)
            else:
                with open(path, 'r') as f:
                    result = f.read()
        
        elif cmd_name == 'file_write':
            path = params[0].strip()
            content = params[1].strip()
            file_tool = None
            for tool_id, metadata in registry.get_all_metadata().items():
                if metadata.name == 'file_manager':
                    file_tool = registry.get_tool_by_id(tool_id)
                    break
                    
            if file_tool:
                result = file_tool.execute_action('write_file', path=path, content=content)
            else:
                with open(path, 'w') as f:
                    f.write(content)
                result = f"Content written to {path}"
        
        else:
            logger.warning(f"Bilinmeyen Metis Agent komutu: {cmd_name}")
            return jsonify({
                'success': False,
                'output': f'Unknown Metis Agent command: {cmd_name}',
                'returnCode': -1
            }), 400
        
        logger.info(f"Metis özel komutu başarıyla çalıştırıldı: {cmd_name}")
        return jsonify({
            'success': True,
            'output': result,
            'returnCode': 0
        }), 200
        
    except Exception as e:
        logger.error(f"Metis özel komut hatası: {str(e)}")
        return jsonify({
            'success': False,
            'output': f'Error executing Metis Agent command: {str(e)}',
            'returnCode': -1
        }), 500

# ===============================
# CONTEXT MANAGEMENT ENDPOINTS
# ===============================

@task_bp.route('/api/context/get', methods=['GET'])
def get_context():
    """Mevcut context değerlerini döndürür"""
    return jsonify({
        'context': coordinator.context_values
    })

@task_bp.route('/api/context/update', methods=['POST'])
def update_context():
    """Context değerlerini günceller"""
    try:
        data = request.get_json()
        context_updates = data.get('context', {})
        
        coordinator.context_values.update(context_updates)
        
        return jsonify({
            'status': 'success',
            'context': coordinator.context_values
        })
    except Exception as e:
        logger.error(f"Context güncelleme hatası: {str(e)}")
        return jsonify({'error': str(e)}), 500