from os_araci.mcp_core.tool import MCPTool
import platform
import os
import psutil

class SystemInfoTool(MCPTool):
    def __init__(self):
        super().__init__(name="system_info", description="İşletim sistemi hakkında bilgiler ve yönetim işlemleri", version="1.0.0")
        # Register methods as operations
        self.register_action("get_system_info", self.get_system_info)
        self.register_action("get_system_resources", self.get_system_resources)
        self.register_action("get_active_users", self.get_active_users)
        
    def get_system_info(self, **kwargs):
        """
        İşletim sistemiyle ilgili temel bilgileri döndürür.
        """
        try:
            system_data = {
                'os': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'architecture': platform.architecture(),
                'hostname': platform.node(),
                'python_version': platform.python_version(),
            }
            return system_data
        except Exception as e:
            return {'error': str(e)}, 400

    def get_system_resources(self, **kwargs):
        """
        Sistem kaynaklarının (CPU, RAM, Disk) durumunu döndürür.
        """
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk_usage = psutil.disk_usage('/')

            resource_data = {
                'cpu_usage': f"{cpu_usage}%",
                'memory': {
                    'total': f"{memory.total / (1024 ** 3):.2f} GB",
                    'used': f"{memory.used / (1024 ** 3):.2f} GB",
                    'free': f"{memory.free / (1024 ** 3):.2f} GB",
                    'percent': f"{memory.percent}%",
                },
                'disk': {
                    'total': f"{disk_usage.total / (1024 ** 3):.2f} GB",
                    'used': f"{disk_usage.used / (1024 ** 3):.2f} GB",
                    'free': f"{disk_usage.free / (1024 ** 3):.2f} GB",
                    'percent': f"{disk_usage.percent}%",
                }
            }
            return resource_data
        except Exception as e:
            return {'error': str(e)}, 400

    def get_active_users(self, **kwargs):
        """
        Sistemde aktif olan kullanıcıları döndürür.
        """
        try:
            users = psutil.users()
            user_list = [{'name': user.name, 'terminal': user.terminal, 'started': user.started} for user in users]
            return {'active_users': user_list}
        except Exception as e:
            return {'error': str(e)}, 400

# Register the tool with the registry when imported
def register_tool(registry):
    tool = SystemInfoTool(registry)
    return registry.register_local_tool(tool)