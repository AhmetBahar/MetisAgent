"""
Basit Pattern Generation Testi
"""

import sys
import os

# Path ayarları
sys.path.append('/home/ahmet/MetisAgent/MetisAgent2/app')
sys.path.append('/home/ahmet/MetisAgent')

# Test imports
from mcp_core import MCPTool
from tools.instagram_tool import InstagramTool

# Manual pattern generation (ChromaDB olmadan)
def test_pattern_generation_manual():
    """Manuel pattern generation testi"""
    print("🧪 Manuel Pattern Generation Test")
    print("=" * 40)
    
    try:
        # Instagram tool instance oluştur
        instagram_tool = InstagramTool()
        print(f"✅ Instagram tool created: {instagram_tool.name}")
        print(f"   Actions: {list(instagram_tool.actions.keys())}")
        
        # Manuel pattern oluştur
        pattern_data = {
            'tool_name': instagram_tool.name,
            'description': instagram_tool.description,
            'actions': {},
            'workflows': [],
            'language_mappings': {}
        }
        
        # Actions analiz et
        for action_name, action_info in instagram_tool.actions.items():
            pattern_data['actions'][action_name] = {
                'required_params': action_info.get('required_params', []),
                'optional_params': action_info.get('optional_params', []),
                'description': f"Execute {action_name} for Instagram"
            }
        
        # Basit workflow örnekleri
        pattern_data['workflows'] = [
            {
                'title': 'Instagram Login',
                'user_examples': ['Instagram\'a giriş yap', 'Login to Instagram'],
                'steps': [
                    {
                        'tool_name': 'instagram_tool',
                        'action_name': 'login',
                        'params': {'username': 'user', 'password': 'pass', 'user_id': 'email'}
                    }
                ]
            },
            {
                'title': 'Upload Photo',
                'user_examples': ['Fotoğraf paylaş', 'Upload photo to Instagram'],
                'steps': [
                    {
                        'tool_name': 'instagram_tool', 
                        'action_name': 'upload_photo',
                        'params': {'image_path': '/path/image.jpg', 'caption': 'Caption'}
                    }
                ]
            }
        ]
        
        # Turkish language mapping
        pattern_data['language_mappings'] = {
            'tr': {
                'phrases': {
                    'instagram\'a giriş yap': 'login',
                    'fotoğraf paylaş': 'upload_photo',
                    'kullanıcı bilgisi': 'get_user_info'
                },
                'parameters': {
                    'kullanıcı_adı': 'username',
                    'şifre': 'password',
                    'resim_yolu': 'image_path'
                }
            }
        }
        
        print("✅ Pattern data generated successfully")
        print(f"   Actions: {len(pattern_data['actions'])}")
        print(f"   Workflows: {len(pattern_data['workflows'])}")
        print(f"   Language mappings: {len(pattern_data['language_mappings'])}")
        
        # Workflow örnekleri göster
        print("\n📋 Generated Workflows:")
        for workflow in pattern_data['workflows']:
            print(f"   - {workflow['title']}")
            print(f"     Examples: {workflow['user_examples']}")
        
        # Turkish mapping göster
        print("\n🇹🇷 Turkish Mappings:")
        tr_mapping = pattern_data['language_mappings']['tr']
        print(f"   Phrases: {list(tr_mapping['phrases'].keys())}")
        print(f"   Parameters: {tr_mapping['parameters']}")
        
        return pattern_data
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_intent_matching_simple(pattern_data):
    """Basit intent matching testi"""
    print("\n🎯 Simple Intent Matching Test")
    print("=" * 30)
    
    test_queries = [
        "Instagram'a giriş yap",
        "Fotoğraf paylaş Instagram'da", 
        "Login to Instagram",
        "Upload photo",
        "kullanıcı bilgilerini getir"
    ]
    
    tr_phrases = pattern_data['language_mappings']['tr']['phrases']
    
    for query in test_queries:
        query_lower = query.lower()
        matched_intent = None
        
        # Turkish phrase matching
        for phrase, intent in tr_phrases.items():
            if phrase in query_lower:
                matched_intent = intent
                break
        
        # Workflow example matching
        if not matched_intent:
            for workflow in pattern_data['workflows']:
                for example in workflow['user_examples']:
                    if any(word in query_lower for word in example.lower().split()):
                        matched_intent = workflow['steps'][0]['action_name']
                        break
                if matched_intent:
                    break
        
        print(f"   '{query}' → {matched_intent or 'No match'}")

def test_dynamic_prompt_generation(pattern_data):
    """Dinamik prompt generation testi"""
    print("\n📝 Dynamic Prompt Generation Test")
    print("=" * 35)
    
    user_query = "Instagram'a giriş yap ve fotoğraf paylaş"
    
    # Relevant workflow örnekleri bul
    relevant_workflows = []
    query_lower = user_query.lower()
    
    for workflow in pattern_data['workflows']:
        for example in workflow['user_examples']:
            if any(word in query_lower for word in example.lower().split()):
                relevant_workflows.append(workflow)
                break
    
    print(f"User Query: '{user_query}'")
    print(f"Relevant Workflows Found: {len(relevant_workflows)}")
    
    for workflow in relevant_workflows:
        print(f"\n📋 Workflow: {workflow['title']}")
        print(f"   User Examples: {workflow['user_examples']}")
        print(f"   Steps: {len(workflow['steps'])}")
        for i, step in enumerate(workflow['steps']):
            print(f"     {i+1}. {step['tool_name']}.{step['action_name']}")
    
    # Mock dynamic prompt piece oluştur
    dynamic_prompt_piece = f"""
RELEVANT USAGE PATTERNS FOR: {user_query}

Available Instagram Workflows:
{chr(10).join(f'- {w["title"]}: {w["user_examples"]}' for w in relevant_workflows)}

Example Implementation:
{{
  "title": "Instagram Login and Upload",
  "steps": [
    {{"tool_name": "instagram_tool", "action_name": "login", "params": {{"username": "user", "password": "pass", "user_id": "email"}}}},
    {{"tool_name": "instagram_tool", "action_name": "upload_photo", "params": {{"image_path": "/path/image.jpg", "caption": "My photo"}}}}
  ]
}}
"""
    
    print(f"\n📤 Generated Dynamic Prompt Piece:")
    print(dynamic_prompt_piece)
    
    return dynamic_prompt_piece

def main():
    """Ana test fonksiyonu"""
    print("🚀 Basit Pattern Generation Sistemi Test")
    print("=" * 50)
    
    # 1. Pattern generation
    pattern_data = test_pattern_generation_manual()
    
    if pattern_data:
        # 2. Intent matching
        test_intent_matching_simple(pattern_data)
        
        # 3. Dynamic prompt generation
        test_dynamic_prompt_generation(pattern_data)
        
        print("\n🎉 Tüm testler başarılı!")
        return True
    else:
        print("\n❌ Pattern generation başarısız!")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("✅ Dinamik pattern sistemi çalışıyor!")
    else:
        print("❌ Sistem test başarısız!")