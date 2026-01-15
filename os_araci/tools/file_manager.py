import os
import shutil
from os_araci.mcp_core import MCPTool

class FileManager(MCPTool):
    def __init__(self):
        super().__init__("file_manager", "Dosya sistemi yönetim araçları")
        
        # Aksiyonları kaydet
        self.register_action(
            "list_files", 
            self.list_files,
            ["path"], 
            "Lists all files in a given directory"
        )
        self.register_action(
            "create_file", 
            self.create_file,
            ["path", "content"], 
            "Creates a file at the specified path with optional content"
        )
        self.register_action(
            "delete_file", 
            self.delete_file,
            ["path"], 
            "Deletes a file at the specified path"
        )
        self.register_action(
            "list_folders", 
            self.list_folders,
            ["path"], 
            "Lists all folders in a given directory"
        )
        self.register_action(
            "create_folder", 
            self.create_folder,
            ["path"], 
            "Creates a new folder at the specified path"
        )
        self.register_action(
            "delete_folder", 
            self.delete_folder,
            ["path"], 
            "Deletes a folder and its contents at the specified path"
        )
        self.register_action(
            "rename_folder", 
            self.rename_folder,
            ["old_path", "new_path"], 
            "Renames a folder from the old path to the new path"
        )
        self.register_action(
            "change_directory", 
            self.change_directory,
            ["path"], 
            "Changes the current working directory to the specified path"
        )
    
    def list_files(self, path):
        try:
            items = os.listdir(path)
            files = [item for item in items if os.path.isfile(os.path.join(path, item))]
            return {"status": "success", "items": files}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def create_file(self, path, content=""):
        try:
            with open(path, 'w') as f:
                f.write(content)
            return {"status": "success", "message": f"File created at {path}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def delete_file(self, path):
        try:
            os.remove(path)
            return {"status": "success", "message": f"File {path} deleted successfully"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def list_folders(self, path):
        try:
            items = os.listdir(path)
            folders = [item for item in items if os.path.isdir(os.path.join(path, item))]
            return {"status": "success", "folders": folders}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def create_folder(self, path):
        try:
            os.makedirs(path, exist_ok=True)
            return {"status": "success", "message": f"Folder created at {path}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def delete_folder(self, path):
        try:
            shutil.rmtree(path)
            return {"status": "success", "message": f"Folder {path} deleted successfully"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def rename_folder(self, old_path, new_path):
        try:
            os.rename(old_path, new_path)
            return {"status": "success", "message": f"Folder renamed from {old_path} to {new_path}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def change_directory(self, path):
        try:
            os.chdir(path)
            current_directory = os.getcwd()
            return {"status": "success", "message": f"Current directory changed to {current_directory}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

def register_tool(registry):
    """Registry'e araç kaydeder"""
    registry.register_tool(FileManager())