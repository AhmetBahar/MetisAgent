"""
Instagram Tool Test Senaryosu
"""

import sys
import os

# Path ayarları
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append('/home/ahmet/MetisAgent/MetisAgent2/app')

from instagram_tool import InstagramTool

def test_instagram_tool():
    """Instagram tool test senaryosu"""
    print("🔧 Instagram Tool Test Başlatılıyor...")
    
    # Tool instance oluştur
    tool = InstagramTool()
    print(f"✅ Tool oluşturuldu: {tool.name}")
    
    # Actions kontrolü
    actions = list(tool.actions.keys())
    print(f"📋 Mevcut actions: {actions}")
    
    expected_actions = [
        'login', 'logout', 'upload_photo', 'upload_story', 
        'get_user_info', 'get_followers', 'like_media', 'comment_media'
    ]
    
    for action in expected_actions:
        if action in actions:
            print(f"  ✅ {action}")
        else:
            print(f"  ❌ {action} - eksik!")
    
    # Mock test - login action
    print("\n🧪 Mock Login Test:")
    try:
        # Bu gerçek bir login denemesi yapmaz, sadece yapıyı test eder
        print("  Test login parametreleri kontrol ediliyor...")
        action_info = tool.actions.get('login')
        
        if action_info:
            required = action_info['required_params']
            optional = action_info['optional_params']
            print(f"  Required params: {required}")
            print(f"  Optional params: {optional}")
            
            if 'username' in required and 'password' in required:
                print("  ✅ Login action parametreleri doğru")
            else:
                print("  ❌ Login action parametreleri eksik")
        
    except Exception as e:
        print(f"  ❌ Mock login test hatası: {e}")
    
    # Tool definition test
    print("\n📋 Tool Definition Test:")
    try:
        definition = tool.get_tool_definition()
        print(f"  Tool name: {definition['name']}")
        print(f"  Description: {definition['description']}")
        print(f"  Methods count: {len(definition['methods'])}")
        print("  ✅ Tool definition başarılı")
    except Exception as e:
        print(f"  ❌ Tool definition hatası: {e}")
    
    print("\n🎉 Instagram Tool Test Tamamlandı!")
    return True

if __name__ == "__main__":
    test_instagram_tool()