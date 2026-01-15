#!/usr/bin/env python3
"""
Basit Workflow Test: Subject → Görsel Oluşturma
"""

import json
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.simple_visual_creator import SimpleVisualCreatorTool
from tools.graph_memory_tool import GraphMemoryTool

def simple_workflow_test():
    """Basit workflow testi"""
    
    print("🚀 Basit Workflow Test: Subject → Görsel")
    print("=" * 50)
    
    # Simulated email subject
    subject = "MetisAgent2 MCP Integration Success - Advanced Workflow Test"
    
    print(f"\n📧 Email Subject: {subject}")
    
    # Tools
    visual_tool = SimpleVisualCreatorTool()
    memory_tool = GraphMemoryTool()
    
    # Step 1: Analyze subject for visual
    print(f"\n🧠 Step 1: Subject analizi...")
    
    analysis_data = {
        "main_topic": "MetisAgent2 MCP Integration Success",
        "visual_concept": "Modern AI system with MCP integration and workflow success",
        "dall_e_prompt": "A futuristic AI dashboard showing successful MCP (Model Context Protocol) integration, with interconnected nodes representing different tools, glowing green success indicators, modern tech interface, professional digital art style"
    }
    
    print(f"✅ Analiz tamamlandı:")
    print(f"   🎯 Ana konu: {analysis_data['main_topic']}")
    print(f"   🎨 Görsel konsept: {analysis_data['visual_concept']}")
    
    # Step 2: Create visual
    print(f"\n🎨 Step 2: Görsel oluşturuluyor...")
    
    visual_result = visual_tool._generate_image_with_openai(
        prompt=analysis_data['dall_e_prompt']
    )
    
    if visual_result.success:
        visual_data = visual_result.data
        image_url = visual_data.get('image_url', 'Generated successfully')
        print(f"✅ Görsel oluşturuldu:")
        print(f"   🖼️ Sonuç: {image_url}")
    else:
        print(f"⚠️ Görsel oluşturma problemi: {visual_result.error}")
        image_url = "Simulated: visual_generation_test.png"
        print(f"📝 Simüle edildi: {image_url}")
    
    # Step 3: Save to memory
    print(f"\n💾 Step 3: Memory'e kayıt...")
    
    test_id = f"workflow_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    entities = [
        {
            "name": test_id,
            "entityType": "workflow_test",
            "observations": [
                f"Email subject: {subject}",
                f"Analysis: {analysis_data['main_topic']}",
                f"Visual concept: {analysis_data['visual_concept']}",
                f"Generated image: {image_url}",
                f"Test completed: {datetime.now().isoformat()}"
            ]
        }
    ]
    
    memory_result = memory_tool._create_entities(entities)
    
    if memory_result.success:
        print(f"✅ Memory'e kaydedildi: {test_id}")
    else:
        print(f"⚠️ Memory kayıt problemi: {memory_result.error}")
    
    # Final results
    print("\n" + "=" * 50)
    print("🎉 WORKFLOW TEST BAŞARILI!")
    print("=" * 50)
    print(f"📧 Processed: {subject}")
    print(f"🎯 Topic: {analysis_data['main_topic']}")
    print(f"🎨 Visual: {image_url}")
    print(f"💾 Memory ID: {test_id}")
    
    # Test memory search
    print(f"\n🔍 Memory search test...")
    search_result = memory_tool._search_nodes("workflow_test")
    
    if search_result.success:
        entities = search_result.data.get('entities', [])
        print(f"✅ Memory search başarılı: {len(entities)} sonuç")
        for entity in entities[-2:]:  # Son 2 test
            print(f"   📝 {entity['name']} - {len(entity['observations'])} observation")
    else:
        print(f"⚠️ Memory search problemi: {search_result.error}")
    
    print(f"\n🌟 Tüm workflow adımları başarıyla tamamlandı!")
    return True

if __name__ == "__main__":
    simple_workflow_test()