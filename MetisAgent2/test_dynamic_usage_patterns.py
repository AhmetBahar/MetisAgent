"""
Dinamik Tool Usage Pattern Sistemi Test
"""

import sys
import os
import json

# Path ayarları
sys.path.append('/home/ahmet/MetisAgent/MetisAgent2/app')
sys.path.append('/home/ahmet/MetisAgent/MetisAgent2/tools')
sys.path.append('/home/ahmet/MetisAgent')

# Test imports
from mcp_core import MCPTool
from tool_usage_patterns import usage_pattern_manager, ToolUsagePattern
from tools.instagram_tool import InstagramTool

def test_instagram_pattern_generation():
    """Instagram tool için pattern generation testi"""
    print("🧪 Instagram Tool Pattern Generation Test")
    print("=" * 50)
    
    try:
        # Instagram tool instance oluştur
        instagram_tool = InstagramTool()
        print(f"✅ Instagram tool created: {instagram_tool.name}")
        print(f"   Actions: {list(instagram_tool.actions.keys())}")
        
        # Usage pattern oluştur
        pattern = usage_pattern_manager.generate_pattern_from_tool(instagram_tool)
        print(f"✅ Usage pattern generated")
        print(f"   Tool: {pattern.tool_name}")
        print(f"   Category: {pattern.category}")
        print(f"   Actions analyzed: {len(pattern.actions)}")
        print(f"   Workflows created: {len(pattern.common_workflows)}")
        print(f"   Language mappings: {len(pattern.language_mappings)}")
        
        # Workflow örneklerini göster
        print("\n📋 Generated Workflows:")
        for i, workflow in enumerate(pattern.common_workflows):
            print(f"   {i+1}. {workflow.title}")
            print(f"      Description: {workflow.description}")
            print(f"      Complexity: {workflow.complexity}")
            print(f"      User Examples: {workflow.user_request_examples[:2]}")
            print()
        
        # Language mappings göster
        print("🌍 Language Mappings:")
        for lang_mapping in pattern.language_mappings:
            if lang_mapping.language == "tr":
                print(f"   Turkish phrases: {list(lang_mapping.phrases.keys())[:3]}...")
                print(f"   Parameter names: {lang_mapping.parameter_names}")
        
        # Pattern kaydet
        success = usage_pattern_manager.save_pattern(pattern)
        print(f"\n💾 Pattern save result: {'✅ Success' if success else '❌ Failed'}")
        
        return pattern
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return None

def test_pattern_retrieval():
    """Pattern retrieval testi"""
    print("\n🔍 Pattern Retrieval Test")
    print("=" * 30)
    
    try:
        # Instagram pattern'ı getir
        pattern = usage_pattern_manager.get_pattern("instagram_tool")
        
        if pattern:
            print("✅ Pattern retrieved successfully")
            print(f"   Tool: {pattern.tool_name}")
            print(f"   Created: {pattern.created_at}")
            print(f"   Auto-generated: {pattern.auto_generated}")
        else:
            print("❌ Pattern not found")
            
        return pattern
        
    except Exception as e:
        print(f"❌ Retrieval test failed: {e}")
        return None

def test_intent_matching():
    """Intent matching testi"""
    print("\n🎯 Intent Matching Test")
    print("=" * 25)
    
    test_queries = [
        "Instagram'a giriş yap",
        "instagram_tool /home/ahmet/MetisAgent/tools/ klasöründe bulunuyor",
        "Fotoğraf paylaş Instagram'da",
        "Login to Instagram account",
        "Upload photo with caption"
    ]
    
    # Mock workflow orchestrator intent matching
    try:
        from app.workflow_orchestrator import WorkflowOrchestrator
        orchestrator = WorkflowOrchestrator()
        
        for query in test_queries:
            print(f"\n🔸 Query: '{query}'")
            
            # Mock usage examples
            mock_examples = [
                {
                    'tool_name': 'instagram_tool',
                    'workflow': type('MockWorkflow', (), {
                        'title': 'Instagram Login',
                        'user_request_examples': ['Instagram\'a giriş yap', 'Login to Instagram'],
                        'complexity': 'simple'
                    })()
                },
                {
                    'tool_name': 'tool_manager', 
                    'workflow': type('MockWorkflow', (), {
                        'title': 'Install Tool',
                        'user_request_examples': ['araç yükle', 'install tool from folder'],
                        'complexity': 'simple'
                    })()
                }
            ]
            
            relevant = orchestrator._filter_relevant_examples(query, mock_examples)
            print(f"   Relevant examples: {len(relevant)}")
            for example in relevant:
                print(f"   - {example['workflow'].title} ({example['tool_name']})")
                
    except Exception as e:
        print(f"❌ Intent matching test failed: {e}")

def test_turkish_language_support():
    """Türkçe dil desteği testi"""
    print("\n🇹🇷 Turkish Language Support Test")
    print("=" * 35)
    
    turkish_queries = [
        "instagram_tool'unu yükle",
        "Instagram'a giriş yap",
        "fotoğraf paylaş",
        "kullanıcı bilgilerini getir",
        "takipçi listesi al"
    ]
    
    pattern = usage_pattern_manager.get_pattern("instagram_tool")
    if not pattern:
        pattern = test_instagram_pattern_generation()
    
    if pattern:
        # Turkish language mapping kontrolü
        turkish_mapping = None
        for lang_mapping in pattern.language_mappings:
            if lang_mapping.language == "tr":
                turkish_mapping = lang_mapping
                break
        
        if turkish_mapping:
            print("✅ Turkish language mapping found")
            print(f"   Phrases: {len(turkish_mapping.phrases)}")
            print(f"   Parameter names: {len(turkish_mapping.parameter_names)}")
            
            for query in turkish_queries:
                matched_intent = None
                for phrase, intent in turkish_mapping.phrases.items():
                    if phrase.lower() in query.lower():
                        matched_intent = intent
                        break
                
                print(f"   '{query}' → {matched_intent or 'No match'}")
        else:
            print("❌ Turkish language mapping not found")

def main():
    """Ana test fonksiyonu"""
    print("🚀 Dinamik Tool Usage Pattern Sistemi Test Başlatılıyor...")
    print("=" * 60)
    
    # 1. Pattern generation testi
    pattern = test_instagram_pattern_generation()
    
    # 2. Pattern retrieval testi
    if pattern:
        test_pattern_retrieval()
    
    # 3. Intent matching testi
    test_intent_matching()
    
    # 4. Turkish language support testi
    test_turkish_language_support()
    
    print("\n🎉 Test tamamlandı!")
    print("=" * 60)
    
    return pattern is not None

if __name__ == "__main__":
    success = main()
    if success:
        print("✅ Tüm testler başarılı!")
    else:
        print("❌ Bazı testler başarısız!")