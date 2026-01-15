# os_araci/coordination/context_manager.py
import logging

logger = logging.getLogger(__name__)

class MCPContextManager:
    def __init__(self):
        self.context = {}
        logger.info("MCPContextManager başlatıldı")
    
    def set_value(self, key, value):
        """Context'e değer ekler"""
        self.context[key] = value
        logger.debug(f"Context güncellendi: {key} = {value[:100] if isinstance(value, str) else value}")
    
    def get_value(self, key, default=None):
        """Context'ten değer alır"""
        return self.context.get(key, default)
    
    def apply_template(self, template_string):
        """Şablondaki placeholder'ları context değerleriyle değiştirir"""
        if not isinstance(template_string, str):
            return template_string
            
        original = template_string
        for key, value in self.context.items():
            placeholder = f"<{key}>"
            if placeholder in template_string:
                template_string = template_string.replace(placeholder, str(value))
                logger.debug(f"Placeholder değiştirildi: {placeholder} -> {str(value)[:50]}...")
        
        if original != template_string:
            logger.info(f"Şablon değiştirildi: {original[:50]}... -> {template_string[:50]}...")
        
        return template_string
    
    def clear(self):
        """Context'i temizler"""
        self.context = {}
        logger.info("Context temizlendi")