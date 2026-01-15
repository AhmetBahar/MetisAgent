# personas/persona_factory.py
import os
import json
import logging
import importlib
from typing import Dict, Any, List, Optional, Type
from os_araci.personas.persona_agent import PersonaAgent

logger = logging.getLogger(__name__)

class PersonaFactory:
    """Persona oluşturma ve yönetme fabrikası"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PersonaFactory, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            logger.info("PersonaFactory başlatılıyor...")
            
            # Persona şablonları ve sınıfları
            self._persona_templates = {}  # template_id -> template
            self._persona_classes = {}    # class_name -> class
            
            # Şablonları ve sınıfları yükle
            self._initialized = True
    
    def register_persona_class(self, class_name: str, persona_class: Type[PersonaAgent]) -> bool:
        """Persona sınıfını kaydet"""
        if class_name in self._persona_classes:
            logger.warning(f"Persona sınıfı zaten kayıtlı: {class_name}")
            return False
        
        # PersonaAgent'tan türediğini kontrol et
        if not issubclass(persona_class, PersonaAgent):
            logger.error(f"Geçersiz persona sınıfı, PersonaAgent'tan türemeli: {class_name}")
            return False
        
        self._persona_classes[class_name] = persona_class
        logger.info(f"Persona sınıfı kaydedildi: {class_name}")
        return True
    
    def register_template(self, template_id: str, template: Dict[str, Any]) -> bool:
        """Persona şablonunu kaydet"""
        if template_id in self._persona_templates:
            logger.warning(f"Persona şablonu zaten kayıtlı: {template_id}")
            return False
        
        # Şablonu doğrula
        required_fields = ["persona_id", "name", "class_name"]
        for field in required_fields:
            if field not in template:
                logger.error(f"Geçersiz persona şablonu, {field} alanı eksik: {template_id}")
                return False
        
        # Class_name'in kayıtlı olduğunu kontrol et
        class_name = template["class_name"]
        if class_name not in self._persona_classes:
            logger.error(f"Persona şablonu için sınıf bulunamadı: {class_name}")
            return False
        
        self._persona_templates[template_id] = template
        logger.info(f"Persona şablonu kaydedildi: {template_id}")
        return True
    
    def create_persona(self, template_id: str, **kwargs) -> Optional[PersonaAgent]:
        """Şablona göre persona oluştur"""
        if template_id not in self._persona_templates:
            logger.error(f"Persona şablonu bulunamadı: {template_id}")
            return None
        
        template = self._persona_templates[template_id]
        class_name = template["class_name"]
        
        if class_name not in self._persona_classes:
            logger.error(f"Persona sınıfı bulunamadı: {class_name}")
            return None
        
        try:
            # Şablon değerlerini al
            persona_args = template.copy()
            
            # class_name'i kaldır (constructor parametresi değil)
            persona_args.pop("class_name", None)
            
            # Kullanıcı tarafından verilen değerleri ekle/güncelle
            persona_args.update(kwargs)
            
            # Persona sınıfını al ve örneğini oluştur
            persona_class = self._persona_classes[class_name]
            persona = persona_class(**persona_args)
            
            logger.info(f"Persona oluşturuldu: {persona.persona_id} ({class_name})")
            return persona
            
        except Exception as e:
            logger.error(f"Persona oluşturma hatası: {str(e)}")
            return None
    
    def load_templates_from_directory(self, directory: str) -> int:
        """Belirtilen dizindeki tüm şablon dosyalarını yükle"""
        if not os.path.exists(directory) or not os.path.isdir(directory):
            logger.error(f"Dizin bulunamadı: {directory}")
            return 0
        
        count = 0
        for filename in os.listdir(directory):
            if filename.endswith(".json"):
                file_path = os.path.join(directory, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        template = json.load(f)
                    
                    # Şablon ID'si
                    template_id = os.path.splitext(filename)[0]
                    
                    # Şablonu kaydet
                    if self.register_template(template_id, template):
                        count += 1
                
                except Exception as e:
                    logger.error(f"Şablon dosyası yüklenirken hata: {file_path}, {str(e)}")
        
        logger.info(f"{count} adet persona şablonu yüklendi: {directory}")
        return count
    
    def discover_persona_classes(self, package_name: str = 'personas') -> int:
        """Belirtilen paketteki tüm persona sınıflarını keşfet ve kaydet"""
        count = 0
        try:
            # Paketi içe aktar
            package = importlib.import_module(package_name)
            
            # Paket içindeki tüm modülleri tara
            import pkgutil
            import inspect
            
            for _, name, is_pkg in pkgutil.iter_modules(package.__path__, package.__name__ + '.'):
                try:
                    # Modülü yükle
                    module = importlib.import_module(name)
                    
                    # Modül içindeki sınıfları bul
                    for item_name, item in inspect.getmembers(module, inspect.isclass):
                        # PersonaAgent türevi mi kontrol et
                        if (issubclass(item, PersonaAgent) and 
                            item is not PersonaAgent and
                            item.__module__ == module.__name__):
                            
                            # Sınıfı kaydet
                            if self.register_persona_class(item_name, item):
                                count += 1
                
                except Exception as e:
                    logger.error(f"Modül yüklenirken hata: {name}, {str(e)}")
            
            logger.info(f"{count} adet persona sınıfı keşfedildi: {package_name}")
            return count
            
        except ImportError as e:
            logger.error(f"Paket yüklenemedi: {package_name}, {str(e)}")
            return 0
    
    def list_available_templates(self) -> List[Dict[str, Any]]:
        """Kullanılabilir tüm şablonları listele"""
        templates = []
        
        for template_id, template in self._persona_templates.items():
            templates.append({
                "template_id": template_id,
                "name": template.get("name", ""),
                "description": template.get("description", ""),
                "class_name": template.get("class_name", ""),
                "capabilities": template.get("capabilities", [])
            })
        
        return templates
    
    def list_available_classes(self) -> List[str]:
        """Kullanılabilir tüm persona sınıflarını listele"""
        return list(self._persona_classes.keys())
    
    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Belirli bir şablonu getir"""
        return self._persona_templates.get(template_id)
    # persona_factory.py'ye ekle/güncelle

    def auto_discover_and_register(self, package_name: str = 'os_araci.personas') -> int:
        """Otomatik olarak persona sınıflarını keşfet ve kaydet"""
        count = 0
        try:
            # Paketi import et
            package = importlib.import_module(package_name)
            
            # __init__.py'deki register_all_personas fonksiyonunu çağır
            if hasattr(package, 'register_all_personas'):
                count = package.register_all_personas(self)
                logger.info(f"{count} persona sınıfı otomatik kaydedildi")
            else:
                # Eski yöntemle devam et
                count = self.discover_persona_classes(package_name)
                
            return count
            
        except ImportError as e:
            logger.error(f"Persona paketi yüklenemedi: {package_name}, {str(e)}")
            return 0