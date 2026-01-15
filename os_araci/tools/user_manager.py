from os_araci.mcp_core.tool import MCPTool
from os_araci.utils.command_executor import execute_command
import os
import json

class UserManagerTool(MCPTool):
    def __init__(self):
        super().__init__(name="user_manager",description="Kullanıcıların yönetim işlemleri", version="1.0.0")
        # Register methods as actions (not operations)
        self.register_action("list_users", self.list_users)
        self.register_action("create_user", self.create_user)
        self.register_action("delete_user", self.delete_user)
        self.register_action("change_password", self.change_password)
        self.register_action("authorize_user", self.authorize_user)
        
    def list_users(self, **kwargs):
        try:
            if os.name == 'nt':  # Windows
                command = "net user"
            else:  # Linux/Unix
                command = "cut -d: -f1 /etc/passwd"
            result = execute_command(command)
            users = result.splitlines()
            return {'users': users}
        except Exception as e:
            return {'error': str(e)}, 400
            
    def create_user(self, username=None, password=None, **kwargs):
        if not username:
            return {'error': 'Username is required'}, 400

        try:
            if os.name == 'nt':  # Windows
                if not password:
                    return {'error': 'Password is required for Windows'}, 400
                command = f'net user {username} {password} /add'
            else:  # Linux/Unix
                command = f'sudo adduser --disabled-password --gecos "" {username}'
            result = execute_command(command)
            return {'message': f'User {username} created successfully', 'details': result}
        except Exception as e:
            return {'error': str(e)}, 400
            
    def delete_user(self, username=None, **kwargs):
        if not username:
            return {'error': 'Username is required'}, 400

        try:
            if os.name == 'nt':  # Windows
                command = f'net user {username} /delete'
            else:  # Linux/Unix
                command = f'sudo deluser {username}'
            result = execute_command(command)
            return {'message': f'User {username} deleted successfully', 'details': result}
        except Exception as e:
            return {'error': str(e)}, 400
            
    def change_password(self, username=None, new_password=None, **kwargs):
        if not username or not new_password:
            return {'error': 'Username and new password are required'}, 400

        try:
            if os.name == 'nt':  # Windows
                command = f'net user {username} {new_password}'
            else:  # Linux/Unix
                command = f'echo "{username}:{new_password}" | sudo chpasswd'
            result = execute_command(command)
            return {'message': f'Password for {username} changed successfully', 'details': result}
        except Exception as e:
            return {'error': str(e)}, 400
            
    def authorize_user(self, username=None, group=None, **kwargs):
        if not username or not group:
            return {'error': 'Username and group are required'}, 400

        try:
            if os.name == 'nt':  # Windows
                command = f'net localgroup {group} {username} /add'
            else:  # Linux/Unix
                command = f'sudo usermod -aG {group} {username}'
            result = execute_command(command)
            return {'message': f'User {username} added to group {group} successfully', 'details': result}
        except Exception as e:
            return {'error': str(e)}, 400

# Register the tool with the registry when imported
def register_tool(registry):
    tool = UserManagerTool(registry)
    return registry.register_local_tool(tool)