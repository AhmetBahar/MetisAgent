from os_araci.mcp_core.tool import MCPTool
from os_araci.utils.command_executor import execute_command
import os

class NetworkManagerTool(MCPTool):
    def __init__(self):
        super().__init__(name="network_manager",description="Network yönetim işlemleri",version="1.0.0")
        # Register methods as operations
        self.register_action("ping", self.ping)
        self.register_action("get_connections", self.get_connections)
        self.register_action("port_scan", self.port_scan)
        self.register_action("get_ip", self.get_ip)
        self.register_action("change_ip", self.change_ip)
        
    def ping(self, host="google.com", **kwargs):
        try:
            command = f'ping -c 4 {host}' if os.name != 'nt' else f'ping {host}'
            result = execute_command(command)
            return {'output': result}
        except Exception as e:
            return {'error': str(e)}, 400
            
    def get_connections(self, **kwargs):
        try:
            command = 'netstat -tuln' if os.name != 'nt' else 'netstat -an'
            result = execute_command(command)
            return {'connections': result.splitlines()}
        except Exception as e:
            return {'error': str(e)}, 400
            
    def port_scan(self, ip=None, ports=None, **kwargs):
        if not ip or not ports:
            return {'error': 'IP address and ports are required'}, 400

        try:
            open_ports = []
            for port in ports:
                command = f'nc -zv {ip} {port}' if os.name != 'nt' else f'telnet {ip} {port}'
                result = execute_command(command)
                if 'open' in result or 'succeeded' in result:
                    open_ports.append(port)
            return {'open_ports': open_ports}
        except Exception as e:
            return {'error': str(e)}, 400
            
    def get_ip(self, **kwargs):
        """
        Sistemin mevcut IP adresini döndürür.
        """
        try:
            if os.name == 'nt':  # Windows
                command = "ipconfig"
            else:  # Linux/Unix
                command = "hostname -I"
            result = execute_command(command)
            return {'ip': result.strip()}
        except Exception as e:
            return {'error': str(e)}, 400
            
    def change_ip(self, interface=None, ip=None, **kwargs):
        """
        Belirtilen ağ arayüzünde IP adresini değiştirir.
        """
        if not interface or not ip:
            return {'error': 'Interface and new IP address are required'}, 400

        try:
            if os.name == 'nt':  # Windows
                command = f'netsh interface ip set address name="{interface}" static {ip} 255.255.255.0'
            else:  # Linux/Unix
                command = f'sudo ip addr add {ip}/24 dev {interface}'
            result = execute_command(command)
            return {'message': f'IP address of {interface} changed to {ip}', 'details': result}
        except Exception as e:
            return {'error': str(e)}, 400

# Register the tool with the registry when imported
def register_tool(registry):
    tool = NetworkManagerTool(registry)
    return registry.register_local_tool(tool)