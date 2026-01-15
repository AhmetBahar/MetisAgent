from os_araci.mcp_core import MCPTool
import os
import json

class InMemoryEditor(MCPTool):
    def __init__(self):
        super().__init__("in_memory_editor", "Bellek içi metin editörü")
        self.files = {}
        
        # Aksiyonları kaydet
        self.register_action(
            "create_file", 
            self.create_file,
            ["filename"], 
            "Creates an in-memory file"
        )
        self.register_action(
            "write_file", 
            self.write_file,
            ["filename", "content"], 
            "Writes content to an in-memory file"
        )
        self.register_action(
            "go_to_line", 
            self.go_to_line,
            ["filename", "line_number"], 
            "Returns content of a specific line"
        )
        self.register_action(
            "find", 
            self.find,
            ["filename", "search_text"], 
            "Finds a string in an in-memory file"
        )
        self.register_action(
            "find_and_replace", 
            self.find_and_replace,
            ["filename", "search_text", "replace_text"], 
            "Replaces all occurrences of a string in an in-memory file"
        )
        self.register_action(
            "select_lines", 
            self.select_lines,
            ["filename", "start_line", "end_line"], 
            "Returns a range of lines from an in-memory file"
        )
        self.register_action(
            "list_files", 
            self.list_files,
            [], 
            "Lists all in-memory files"
        )
        self.register_action(
            "save_to_disk", 
            self.save_to_disk,
            ["filename", "disk_path"], 
            "Saves an in-memory file to disk"
        )
        self.register_action(
            "load_from_disk", 
            self.load_from_disk,
            ["filename", "disk_path"], 
            "Loads a file from disk into memory"
        )
        self.register_action(
            "initialize_change_templates", 
            self.initialize_change_templates,
            [], 
            "Initializes the change templates system"
        )
        self.register_action(
            "save_change_template", 
            self.save_change_template,
            ["template_name", "change_template"], 
            "Saves a code change template"
        )
        self.register_action(
            "get_change_template", 
            self.get_change_template,
            ["template_name"], 
            "Retrieves a saved code change template"
        )
        self.register_action(
            "list_change_templates", 
            self.list_change_templates,
            [], 
            "Lists all available code change templates"
        )
        self.register_action(
            "delete_change_template", 
            self.delete_change_template,
            ["template_name"], 
            "Deletes a code change template"
        )
        self.register_action(
            "apply_llm_change", 
            self.apply_llm_change,
            ["filename", "change_template"], 
            "Applies a code change from a template"
        )
        
    def create_file(self, filename):
        if filename in self.files:
            return {"status": "error", "message": f"File {filename} already exists"}
        self.files[filename] = []
        return {"status": "success", "message": f"File {filename} created"}
        
    def write_file(self, filename, content):
        if filename not in self.files:
            return {"status": "error", "message": f"File {filename} does not exist"}
        self.files[filename] = content.splitlines()
        return {"status": "success", "message": f"Content written to {filename}"}
        
    def go_to_line(self, filename, line_number):
        if filename not in self.files:
            return {"status": "error", "message": f"File {filename} does not exist"}
            
        content = self.files[filename]
        line_number = int(line_number) - 1
        
        if line_number < 0 or line_number >= len(content):
            return {"status": "error", "message": "Line number out of range"}
            
        return {
            "status": "success", 
            "line_content": content[line_number]
        }
        
    def find(self, filename, search_text):
        if filename not in self.files:
            return {"status": "error", "message": f"File {filename} does not exist"}
            
        content = self.files[filename]
        matches = [i + 1 for i, line in enumerate(content) if search_text in line]
            
        return {
            "status": "success", 
            "matches": matches
        }
        
    def find_and_replace(self, filename, search_text, replace_text=""):
        if filename not in self.files:
            return {"status": "error", "message": f"File {filename} does not exist"}
            
        content = self.files[filename]
        updated_content = [line.replace(search_text, replace_text) for line in content]
        self.files[filename] = updated_content
            
        return {
            "status": "success", 
            "message": f"Replaced all occurrences of '{search_text}' with '{replace_text}'"
        }
        
    def select_lines(self, filename, start_line, end_line):
        if filename not in self.files:
            return {"status": "error", "message": f"File {filename} does not exist"}
            
        content = self.files[filename]
        start_line = int(start_line) - 1
        end_line = int(end_line)
        
        if start_line < 0 or end_line > len(content):
            return {"status": "error", "message": "Line range out of bounds"}
            
        selected_lines = content[start_line:end_line]
            
        return {
            "status": "success", 
            "selected_lines": selected_lines
        }
        
    def list_files(self):
        return {
            "status": "success",
            "files": list(self.files.keys())
        }
    
    def save_to_disk(self, filename, disk_path):
        """Bellek içi dosyayı diske kaydeder"""
        if filename not in self.files:
            return {"status": "error", "message": f"File {filename} does not exist in memory"}
        
        try:
            content = '\n'.join(self.files[filename])
            with open(disk_path, 'w') as f:
                f.write(content)
            return {
                "status": "success", 
                "message": f"File {filename} saved to disk at {disk_path}"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def load_from_disk(self, filename, disk_path):
        """Disk üzerindeki dosyayı belleğe yükler"""
        if not os.path.exists(disk_path):
            return {"status": "error", "message": f"File {disk_path} does not exist on disk"}
        
        try:
            with open(disk_path, 'r') as f:
                content = f.read()
            
            # Eğer dosya bellekte yoksa, yeni oluştur
            if filename not in self.files:
                self.files[filename] = []
            
            # Dosya içeriğini satırlara ayırıp belleğe kaydet
            self.files[filename] = content.splitlines()
            
            return {
                "status": "success", 
                "message": f"File {disk_path} loaded into memory as {filename}"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
        
    def initialize_change_templates(self):
        """
        Değişiklik şablonları için sistem başlatma
        """
        template_filename = ".change_templates.json"
        
        # Eğer şablon dosyası zaten bellekte yoksa oluştur
        if template_filename not in self.files:
            self.files[template_filename] = ['{}']
        else:
            # Dosya var, içeriğini JSON olarak ayrıştırmaya çalış
            try:
                content = '\n'.join(self.files[template_filename])
                json.loads(content)  # Geçerli JSON mu kontrol et
            except json.JSONDecodeError:
                # Geçerli JSON değilse, yeni boş bir JSON oluştur
                self.files[template_filename] = ['{}']
        
        return {
            "status": "success",
            "message": f"Change templates system initialized"
        }

    def save_change_template(self, template_name, change_template):
        """
        Değişiklik şablonunu kaydeder
        """
        template_filename = ".change_templates.json"
        
        # Şablon sistemi başlatıldı mı kontrol et
        if template_filename not in self.files:
            self.initialize_change_templates()
        
        # Mevcut şablonları oku
        content = '\n'.join(self.files[template_filename])
        try:
            templates = json.loads(content)
        except json.JSONDecodeError:
            templates = {}
        
        # Yeni şablonu ekle veya güncelle
        templates[template_name] = change_template
        
        # Güncellenmiş şablonları geri yaz
        self.files[template_filename] = [json.dumps(templates, indent=2)]
        
        # Disk kalıcılığı için opsiyonel olarak diske kaydet
        # self.save_to_disk(template_filename, "path/to/templates.json")
        
        return {
            "status": "success",
            "message": f"Change template '{template_name}' saved"
        }

    def get_change_template(self, template_name):
        """
        Kaydedilmiş şablonu getirir
        """
        template_filename = ".change_templates.json"
        
        # Şablon sistemi başlatıldı mı kontrol et
        if template_filename not in self.files:
            return {
                "status": "error",
                "message": "Change templates system not initialized"
            }
        
        # Mevcut şablonları oku
        content = '\n'.join(self.files[template_filename])
        try:
            templates = json.loads(content)
        except json.JSONDecodeError:
            return {
                "status": "error",
                "message": "Invalid template storage format"
            }
        
        # İstenen şablonu getir
        if template_name not in templates:
            return {
                "status": "error",
                "message": f"Change template '{template_name}' not found"
            }
        
        return {
            "status": "success",
            "template": templates[template_name]
        }

    def list_change_templates(self):
        """
        Tüm şablonları listeler
        """
        template_filename = ".change_templates.json"
        
        # Şablon sistemi başlatıldı mı kontrol et
        if template_filename not in self.files:
            self.initialize_change_templates()
            return {
                "status": "success",
                "templates": []
            }
        
        # Mevcut şablonları oku
        content = '\n'.join(self.files[template_filename])
        try:
            templates = json.loads(content)
        except json.JSONDecodeError:
            return {
                "status": "error",
                "message": "Invalid template storage format"
            }
        
        return {
            "status": "success",
            "templates": list(templates.keys())
        }

    def delete_change_template(self, template_name):
        """
        Bir şablonu siler
        """
        template_filename = ".change_templates.json"
        
        # Şablon sistemi başlatıldı mı kontrol et
        if template_filename not in self.files:
            return {
                "status": "error",
                "message": "Change templates system not initialized"
            }
        
        # Mevcut şablonları oku
        content = '\n'.join(self.files[template_filename])
        try:
            templates = json.loads(content)
        except json.JSONDecodeError:
            return {
                "status": "error",
                "message": "Invalid template storage format"
            }
        
        # Şablonu sil (eğer varsa)
        if template_name in templates:
            del templates[template_name]
            
            # Güncellenmiş şablonları geri yaz
            self.files[template_filename] = [json.dumps(templates, indent=2)]
            
            # Disk kalıcılığı için opsiyonel olarak diske kaydet
            # self.save_to_disk(template_filename, "path/to/templates.json")
            
            return {
                "status": "success",
                "message": f"Change template '{template_name}' deleted"
            }
        else:
            return {
                "status": "error",
                "message": f"Change template '{template_name}' not found"
            }

    def apply_llm_change(self, filename, change_template):
        """
        LLM tarafından gönderilen bir değişiklik şablonunu uygular.
        
        change_template format:
        {
            "type": "replace|insert|delete",
            "start_line": <int>,
            "end_line": <int>,
            "content": "yeni içerik",
            "description": "değişiklik açıklaması" (isteğe bağlı)
        }
        """
        if filename not in self.files:
            return {"status": "error", "message": f"File {filename} does not exist"}
        
        change_type = change_template.get("type")
        start_line = int(change_template.get("start_line", 1))
        end_line = int(change_template.get("end_line", start_line))
        content = change_template.get("content", "")
        
        if change_type == "replace":
            # Belirli satır aralığını yeni içerikle değiştir
            before_lines = self.files[filename][:start_line-1] 
            after_lines = self.files[filename][end_line:]
            new_content_lines = content.splitlines()
            self.files[filename] = before_lines + new_content_lines + after_lines
            return {
                "status": "success",
                "message": f"Replaced lines {start_line}-{end_line} with new content"
            }
            
        elif change_type == "insert":
            # Belirli bir satırdan önce yeni içerik ekle
            before_lines = self.files[filename][:start_line-1] 
            after_lines = self.files[filename][start_line-1:]
            new_content_lines = content.splitlines()
            self.files[filename] = before_lines + new_content_lines + after_lines
            return {
                "status": "success",
                "message": f"Inserted content before line {start_line}"
            }
            
        elif change_type == "delete":
            # Belirli satır aralığını sil
            before_lines = self.files[filename][:start_line-1] 
            after_lines = self.files[filename][end_line:]
            self.files[filename] = before_lines + after_lines
            return {
                "status": "success",
                "message": f"Deleted lines {start_line}-{end_line}"
            }
        
        else:
            return {
                "status": "error",
                "message": f"Unknown change type: {change_type}"
            }
    
def register_tool(registry):
    """Registry'e araç kaydeder"""
    registry.register_tool(InMemoryEditor())