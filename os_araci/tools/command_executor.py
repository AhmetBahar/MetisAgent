from os_araci.mcp_core import MCPTool
import subprocess
import platform
import json

class CommandExecutor(MCPTool):
    def __init__(self):
        super().__init__(
            name="command_executor",
            description="Komut çalıştırma aracı",
            version="1.0.0"
        )
        self.registry = None
    
    def initialize(self):
        # MCP Registry'ye erişim alın
        from os_araci.mcp_core.registry import MCPRegistry
        self.registry = MCPRegistry()
        
        # Aksiyonları kaydet
        self.register_action("execute_command", self.execute_command, ["command"], "Executes a command on the system")
        self.register_action("execute_and_save_to_editor", self.execute_and_save_to_editor, ["command", "editor_filename"], "Executes a command and saves the output to in-memory editor")
        self.register_action("test_and_apply_template", self.test_and_apply_template, ["command", "editor_filename", "template_name"], "Runs a test command and applies result to a file using a template")
        
        return True
    
    def execute_command(self, command):
        """
        İşletim sistemine uygun şekilde komut çalıştırır.
        
        Args:
            command (str): Çalıştırılacak komut.
        
        Returns:
            dict: İşlem sonucu ve çıktı.
        """
        system = platform.system()
        try:
            if system == "Windows":
                # Windows için komut çalıştırma
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
            else:
                # Linux/Unix için komut çalıştırma
                result = subprocess.run(f"bash -c '{command}'", shell=True, capture_output=True, text=True)
            
            # Başarılıysa stdout döndür, değilse stderr
            output = result.stdout if result.returncode == 0 else result.stderr
            return {
                "status": "success", 
                "return_code": result.returncode,
                "output": output
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def set_registry(self, registry):
        """Registry referansını ayarlar"""
        self._registry = registry
    
    def execute_and_save_to_editor(self, command, editor_filename):
        """
        Komutu çalıştırır ve çıktıyı in-memory editörüne kaydeder.
        
        Args:
            command (str): Çalıştırılacak komut.
            editor_filename (str): Çıktının kaydedileceği in-memory dosyası.
        
        Returns:
            dict: İşlem sonucu.
        """
        # Önce komutu çalıştır
        result = self.execute_command(command)
        
        if result["status"] == "error":
            return result
        
        # Registry kontrolü
        if not self._registry:
            return {"status": "error", "message": "Registry not set for this tool"}
        
        # In-memory editör aracına ulaş
        editor_tool = self._registry.get_tool("in_memory_editor")
        if not editor_tool:
            return {"status": "error", "message": "In-memory editor tool not found"}
        
        # Dosya varsa içeriği yaz, yoksa önce oluştur
        file_check = editor_tool.list_files()
        if editor_filename not in file_check.get("files", []):
            create_result = editor_tool.create_file(editor_filename)
            if create_result["status"] == "error":
                return create_result
        
        # Çıktıyı dosyaya yaz
        write_result = editor_tool.write_file(editor_filename, result["output"])
        
        return {
            "status": "success",
            "message": f"Command executed and output saved to {editor_filename}",
            "command_result": result,
            "write_result": write_result
        }
    
    def test_and_apply_template(self, command, editor_filename, template_name):
        """
        Test komutunu çalıştırır ve sonucu bir şablon kullanarak dosyaya uygular.
        
        Args:
            command (str): Çalıştırılacak test komutu.
            editor_filename (str): Değişikliğin uygulanacağı in-memory dosyası.
            template_name (str): Kullanılacak değişiklik şablonu.
        
        Returns:
            dict: İşlem sonucu.
        """
        # Önce komutu çalıştır
        result = self.execute_command(command)
        
        if result["status"] == "error":
            return result
        
        # Registry kontrolü
        if not self._registry:
            return {"status": "error", "message": "Registry not set for this tool"}
        
        # In-memory editör aracına ulaş
        editor_tool = self._registry.get_tool("in_memory_editor")
        if not editor_tool:
            return {"status": "error", "message": "In-memory editor tool not found"}
        
        # Şablonu al
        template_result = editor_tool.get_change_template(template_name)
        if template_result["status"] == "error":
            return template_result
        
        # Şablonu doldur - test çıktısını şablondaki ilgili alana yerleştir
        template = template_result["template"]
        
        # Şablonu güncelle (örneğin test sonucunu içerikle değiştir)
        if "content_placeholder" in template:
            template["content"] = template["content"].replace(
                template["content_placeholder"], 
                result["output"]
            )
        else:
            # Direkt olarak çıktıyı içerik olarak koy
            template["content"] = result["output"]
        
        # Değişikliği uygula
        apply_result = editor_tool.apply_llm_change(editor_filename, template)
        
        return {
            "status": "success",
            "message": f"Test executed and changes applied to {editor_filename}",
            "command_result": result,
            "apply_result": apply_result
        }

def register_tool(registry):
    """Registry'e araç kaydeder"""
    tool = CommandExecutor()
    tool.set_registry(registry)  # Registry referansını aracımıza set et
    registry.register_tool(tool)