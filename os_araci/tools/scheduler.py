from os_araci.mcp_core.tool import MCPTool
import os
import platform
import subprocess

class SchedulerTool(MCPTool):
    def __init__(self):
        super().__init__(name="scheduler", description="Zamanlamalı yürütme işlemleri", version="1.0.0")
        # Register methods as operations
        self.register_action("schedule_task", self.schedule_task)
        self.register_action("list_scheduled_tasks", self.list_scheduled_tasks)
        self.register_action("cancel_task", self.cancel_task)
        self.register_action("schedule_recurring_task", self.schedule_recurring_task)
        self.register_action("task_status", self.task_status)
        
    def schedule_task(self, command=None, time=None, **kwargs):
        """
        Belirtilen bir görevi zamanlar.
        """
        if not command or not time:
            return {'error': 'Command and time are required'}, 400

        try:
            if platform.system() == "Windows":
                schedule_command = f'schtasks /create /tn "ScheduledTask" /tr "{command}" /sc once /st {time}'
            else:
                schedule_command = f'(echo "{time} {command}") | at'
            result = subprocess.run(schedule_command, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return {'message': f'Task scheduled: {command} at {time}'}
            else:
                return {'error': result.stderr}, 400
        except Exception as e:
            return {'error': str(e)}, 400
            
    def list_scheduled_tasks(self, **kwargs):
        """
        Planlanan görevleri listeler.
        """
        try:
            if platform.system() == "Windows":
                list_command = "schtasks"
            else:
                list_command = "atq"
            result = subprocess.run(list_command, shell=True, capture_output=True, text=True)
            tasks = result.stdout.strip().split('\n')
            return {'tasks': tasks}
        except Exception as e:
            return {'error': str(e)}, 400
            
    def cancel_task(self, task_id=None, **kwargs):
        """
        Belirtilen bir görevi iptal eder.
        """
        if not task_id:
            return {'error': 'Task ID is required'}, 400

        try:
            if platform.system() == "Windows":
                cancel_command = f'schtasks /delete /tn "{task_id}" /f'
            else:
                cancel_command = f'at -d {task_id}'
            result = subprocess.run(cancel_command, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return {'message': f'Task {task_id} cancelled successfully'}
            else:
                return {'error': result.stderr}, 400
        except Exception as e:
            return {'error': str(e)}, 400
            
    def schedule_recurring_task(self, command=None, schedule_type=None, time=None, **kwargs):
        """
        Yinelenen bir görevi zamanlar (günlük, haftalık, aylık).
        """
        if not command or not schedule_type or not time:
            return {'error': 'Command, schedule_type, and time are required'}, 400

        try:
            if platform.system() == "Windows":
                schedule_command = f'schtasks /create /tn "RecurringTask" /tr "{command}" /sc {schedule_type} /st {time}'
            else:
                if schedule_type == "daily":
                    cron_expr = f"{time.split(':')[1]} {time.split(':')[0]} * * *"
                elif schedule_type == "weekly":
                    cron_expr = f"{time.split(':')[1]} {time.split(':')[0]} * * 1"  # Default: Monday
                elif schedule_type == "monthly":
                    cron_expr = f"{time.split(':')[1]} {time.split(':')[0]} 1 * *"  # Default: 1st day of month
                else:
                    return {'error': 'Invalid schedule_type'}, 400
                schedule_command = f'(echo "{cron_expr} {command}") | crontab -'

            result = subprocess.run(schedule_command, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return {'message': f'Recurring task scheduled: {command} as {schedule_type} at {time}'}
            else:
                return {'error': result.stderr}, 400
        except Exception as e:
            return {'error': str(e)}, 400
            
    def task_status(self, task_name=None, **kwargs):
        """
        Belirtilen bir görevin durumunu kontrol eder.
        """
        if not task_name:
            return {'error': 'Task name is required'}, 400

        try:
            if platform.system() == "Windows":
                status_command = f'schtasks /query /tn "{task_name}" /v /fo LIST'
            else:
                # Linux/Unix için uygun bir log okuma veya durum kontrol komutu eklenebilir
                status_command = f'crontab -l | grep "{task_name}"'

            result = subprocess.run(status_command, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return {'status': result.stdout.strip()}
            else:
                return {'error': result.stderr}, 400
        except Exception as e:
            return {'error': str(e)}, 400

# Register the tool with the registry when imported
def register_tool(registry):
    tool = SchedulerTool(registry)
    return registry.register_local_tool(tool)