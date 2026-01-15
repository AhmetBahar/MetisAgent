from os_araci.mcp_core.tool import MCPTool
import shutil
import os

class ArchiveManagerTool(MCPTool):
# ArchiveManagerTool sınıfının __init__ metodunda:
    def __init__(self):
        super().__init__(
            name="archive_manager",
            description="Dosya arşivleme ve sıkıştırma işlemleri",
            version="1.0.0"
        )
        # Register methods as actions
        self.register_action("compress", self.compress)
        self.register_action("extract", self.extract)
        self.register_action("list_archive_contents", self.list_archive_contents)
        
    def compress(self, source=None, destination="archive.zip", **kwargs):
        """
        Belirtilen dosya veya klasörü sıkıştırır (ZIP formatında).
        """
        if not source:
            return {'error': 'Source path is required'}, 400

        try:
            shutil.make_archive(destination.replace('.zip', ''), 'zip', source)
            return {'message': f'Compressed {source} into {destination}'}
        except Exception as e:
            return {'error': str(e)}, 400
            
    def extract(self, archive_path=None, extract_to='.', **kwargs):
        """
        Belirtilen ZIP dosyasını çıkarır.
        """
        if not archive_path:
            return {'error': 'Archive path is required'}, 400

        try:
            shutil.unpack_archive(archive_path, extract_to)
            return {'message': f'Extracted {archive_path} to {extract_to}'}
        except Exception as e:
            return {'error': str(e)}, 400
            
    def list_archive_contents(self, archive_path=None, **kwargs):
        """
        Bir ZIP dosyasının içeriğini listeler.
        """
        if not archive_path:
            return {'error': 'Archive path is required'}, 400

        try:
            with shutil.ZipFile(archive_path, 'r') as archive:
                file_list = archive.namelist()
            return {'files': file_list}
        except Exception as e:
            return {'error': str(e)}, 400

# Register the tool with the registry when imported
def register_tool(registry):
    registry.register_local_tool(ArchiveManagerTool())