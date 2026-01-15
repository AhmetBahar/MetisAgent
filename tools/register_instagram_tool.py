"""
Instagram Tool Registration - MCP Registry için kayıt scripti
"""

import sys
import os

# Path ayarları
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append('/home/ahmet/MetisAgent/MetisAgent2/app')

from instagram_tool import InstagramTool

def register_tool(registry):
    """Instagram tool'unu registry'e kaydet"""
    try:
        tool = InstagramTool()
        registry.register_tool(tool)
        print(f"Instagram tool başarıyla kaydedildi: {tool.name}")
        return True
    except Exception as e:
        print(f"Instagram tool kayıt hatası: {e}")
        return False

if __name__ == "__main__":
    # Test için
    tool = InstagramTool()
    print(f"Instagram Tool: {tool.name}")
    print(f"Actions: {list(tool.actions.keys())}")