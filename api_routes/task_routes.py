"""
Task execution routes - task execution, commands, coordination
"""
from flask import request, jsonify
import logging
import platform

logger = logging.getLogger(__name__)

# Tehlikeli komutlar listesi (Windows ve Linux)
DANGEROUS_COMMANDS = {
    'windows': ['del', 'rmdir', 'format', 'shutdown', 'restart', 'reboot', 'taskkill', 'net user', 'reg delete'],
    'linux': ['rm', 'rmdir', 'dd', 'shutdown', 'reboot', 'halt', 'killall', 'pkill', 'chmod 777']
}

def is_command_safe(command):
    """Komutun güvenli olup olmadığını kontrol et"""
    command_lower = command.lower().strip()
    system = 'windows' if platform.system().lower() == 'windows' else 'linux'
    
    dangerous_list = DANGEROUS_COMMANDS.get(system, [])
    
    for dangerous_cmd in dangerous_list:
        if dangerous_cmd in command_lower:
            return False
    return True

def register_task_routes(app, coordinator=None, registry=None):
    """Register task execution routes"""
    
    @app.route('/api/task/execute', methods=['POST'])
    def execute_task():
        """Görev çalıştır API endpoint'i"""
        try:
            data = request.get_json()
            
            task_name = data.get('task')
            parameters = data.get('parameters', {})
            
            if not task_name:
                return jsonify({"status": "error", "message": "Task name required"}), 400
            
            if coordinator:
                result = coordinator.execute_task(task_name, parameters)
            elif registry:
                result = registry.execute_tool(task_name, parameters)
            else:
                return jsonify({"status": "error", "message": "No executor available"}), 500
            
            return jsonify(result)
        except Exception as e:
            logger.error(f"Görev çalıştırılırken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/task/execute_with_context', methods=['POST'])
    def execute_task_with_context():
        """Görev çalıştır (context ile) API endpoint'i"""
        try:
            data = request.get_json()
            
            task_name = data.get('task')
            parameters = data.get('parameters', {})
            context = data.get('context', {})
            
            if not task_name:
                return jsonify({"status": "error", "message": "Task name required"}), 400
            
            if coordinator:
                result = coordinator.execute_task_with_context(task_name, parameters, context)
            else:
                result = {"status": "error", "message": "Coordinator not available"}
                
            return jsonify(result)
        except Exception as e:
            logger.error(f"Context ile görev çalıştırılırken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/tasks/execute', methods=['POST'])
    def execute_multiple_tasks():
        """Çoklu görev çalıştır API endpoint'i"""
        try:
            data = request.get_json()
            tasks = data.get('tasks', [])
            
            if not tasks:
                return jsonify({"status": "error", "message": "Tasks list required"}), 400
            
            results = []
            for task in tasks:
                task_name = task.get('task')
                parameters = task.get('parameters', {})
                
                if coordinator:
                    result = coordinator.execute_task(task_name, parameters)
                elif registry:
                    result = registry.execute_tool(task_name, parameters)
                else:
                    result = {"status": "error", "message": "No executor available"}
                
                results.append(result)
            
            return jsonify({"status": "success", "results": results})
        except Exception as e:
            logger.error(f"Çoklu görev çalıştırılırken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/tasks/execute_sequential', methods=['POST'])
    def execute_tasks_sequential():
        """Sıralı görev çalıştır API endpoint'i"""
        try:
            data = request.get_json()
            tasks = data.get('tasks', [])
            context = data.get('context', {})
            
            if not tasks:
                return jsonify({"status": "error", "message": "Tasks list required"}), 400
            
            if coordinator:
                result = coordinator.execute_tasks_sequential(tasks, context)
            else:
                result = {"status": "error", "message": "Coordinator not available"}
                
            return jsonify(result)
        except Exception as e:
            logger.error(f"Sıralı görev çalıştırılırken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/coordinator/run_tasks_with_feedback', methods=['POST'])
    def run_tasks_with_feedback():
        """Görevleri feedback ile çalıştır"""
        try:
            data = request.get_json()
            tasks = data.get('tasks', [])
            
            if not tasks:
                return jsonify({"status": "error", "message": "Tasks required"}), 400
            
            if coordinator:
                result = coordinator.run_tasks_with_feedback(tasks)
            else:
                result = {"status": "error", "message": "Coordinator not available"}
                
            return jsonify(result)
        except Exception as e:
            logger.error(f"Feedback ile görev çalıştırılırken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/command/execute', methods=['POST'])
    def execute_command():
        """Güvenli komut çalıştır API endpoint'i"""
        try:
            data = request.get_json()
            command = data.get('command', '')
            
            if not command:
                return jsonify({"status": "error", "message": "Command required"}), 400
            
            # Güvenlik kontrolü
            if not is_command_safe(command):
                logger.warning(f"Tehlikeli komut engellendi: {command}")
                return jsonify({
                    "status": "error", 
                    "message": "Dangerous command blocked for security"
                }), 403
            
            # Command executor aracını kullan
            if registry:
                result = registry.execute_tool("command_executor", {"command": command})
            else:
                result = {"status": "error", "message": "Registry not available"}
            
            return jsonify(result)
        except Exception as e:
            logger.error(f"Komut çalıştırılırken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/context/get', methods=['GET'])
    def get_context():
        """Mevcut context değerlerini getir"""
        try:
            if coordinator and hasattr(coordinator, 'get_context'):
                context = coordinator.get_context()
                return jsonify({"status": "success", "context": context})
            else:
                return jsonify({"status": "success", "context": {}})
        except Exception as e:
            logger.error(f"Context getirilirken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/context/update', methods=['POST'])
    def update_context():
        """Context değerlerini güncelle"""
        try:
            data = request.get_json()
            updates = data.get('updates', {})
            
            if coordinator and hasattr(coordinator, 'update_context'):
                result = coordinator.update_context(updates)
                return jsonify({"status": "success", "result": result})
            else:
                return jsonify({"status": "success", "message": "Context updated"})
        except Exception as e:
            logger.error(f"Context güncellenirken hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    logger.info("Task routes registered")