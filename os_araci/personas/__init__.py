# os_araci/personas/__init__.py
import os
import importlib
import inspect
from pathlib import Path
from .persona_agent import PersonaAgent

# Registry yardımcı fonksiyonu
def discover_personas():
    """Personas klasöründeki tüm persona sınıflarını keşfet"""
    persona_classes = {}
    
    # Bu dosyanın bulunduğu dizin
    current_dir = Path(__file__).parent
    
    # Tüm Python dosyalarını tara
    for file_path in current_dir.glob("*.py"):
        if file_path.name.startswith("_") or file_path.name == "__init__.py":
            continue
            
        # Modül adını çıkar
        module_name = file_path.stem
        
        try:
            # Modülü import et
            module = importlib.import_module(f".{module_name}", package=__package__)
            
            # Modül içindeki sınıfları tara
            for name, obj in inspect.getmembers(module):
                # PersonaAgent'tan türetilmiş sınıfları bul
                if (inspect.isclass(obj) and 
                    issubclass(obj, PersonaAgent) and 
                    obj is not PersonaAgent and
                    obj.__module__ == module.__name__):
                    
                    persona_classes[name] = obj
                    
        except ImportError as e:
            print(f"Persona modülü yüklenemedi: {module_name}, hata: {e}")
            
    return persona_classes

# Dinamik olarak persona sınıflarını yükle
_discovered_personas = discover_personas()

# Discovered persona'ları module namespace'e ekle
for name, cls in _discovered_personas.items():
    globals()[name] = cls

# __all__ listesini dinamik olarak oluştur
__all__ = ['PersonaAgent'] + list(_discovered_personas.keys())

# Registry'ye kayıt fonksiyonu
def register_all_personas(persona_factory):
    """Tüm keşfedilen persona sınıflarını factory'e kaydet"""
    for name, cls in _discovered_personas.items():
        persona_factory.register_persona_class(name, cls)
    return len(_discovered_personas)