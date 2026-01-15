# os_araci/tools/__init__.py

from os_araci.mcp_core.registry import MCPRegistry

# Create registry instance
registry = MCPRegistry()

def register_all_tools():
    """
    Tüm MCP araçlarını kayıt eder ve registry nesnesini döndürür.
    """
    # Import tool modules - sadece çalışanlar
    from . import system_info
    from . import network_manager
    from . import scheduler
    
    # Register tools - sadece çalışanları kaydet
    try:
        system_info.register_tool(registry)
        network_manager.register_tool(registry)  
        scheduler.register_tool(registry)
        
        # Memory Manager'ı ayrı kaydet
        try:
            from . import memory_manager
            print("📥 Memory Manager import edildi")
            result = memory_manager.register_tool(registry)
            print(f"✅ Memory Manager başarıyla kaydedildi: {result}")
        except Exception as mem_error:
            print(f"⚠️ Memory Manager kayıt hatası: {mem_error}")
            import traceback
            traceback.print_exc()
            
        print("✅ Temel araçlar başarıyla kaydedildi")
    except Exception as e:
        print(f"❌ Araç kayıt hatası: {e}")
        # Hata durumunda fallback registry döndür
        from os_araci.mcp_core.registry import MCPRegistry
        fallback_registry = MCPRegistry()
        return fallback_registry
    
    return registry