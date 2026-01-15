#!/usr/bin/env python3
"""
Test Dynamic Synthesis - User request specific workflow generation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.sequential_thinking_tool import SequentialThinkingTool

def test_dynamic_synthesis():
    """Test dynamic synthesis with various user requests"""
    print("🎯 Testing Dynamic Synthesis")
    print("=" * 50)
    
    tool = SequentialThinkingTool()
    available_tools = ["gmail_helper", "simple_visual_creator", "command_executor", "llm_tool"]
    
    test_requests = [
        "bana deniz kenarında güneşlenen insanlar görseli üret ve hangisini seçeceğimi sor. Birinci görseli seçersem, ahmet.bahar@metisbot adresine bu görseli gmail ile gönder. İkinciyi seçersem görüntüyü /home/ahmet/images klasörüne kayıt et, klasör yoksa oluştur.",
        "Gmail'deki son maili al, gönderenin web sitesine git ve ekran görüntüsü al",
        "Yeni bir Instagram aracı yükle ve test et",
        "Bana bir gökkuşağı görseli oluştur"
    ]
    
    for i, request in enumerate(test_requests, 1):
        print(f"\n🧪 Test {i}: {request[:60]}...")
        
        try:
            # Test plan_workflow action
            result = tool.execute_action(
                "plan_workflow",
                user_request=request,
                available_tools=available_tools,
                user_id="test_user"
            )
            
            if result.success:
                workflow_plan = result.data.get("workflow_plan", {})
                method = result.data.get("planning_method", "unknown")
                steps = workflow_plan.get("steps", [])
                
                print(f"✅ Success: {len(steps)} steps via {method}")
                print(f"   Title: {workflow_plan.get('title', 'N/A')}")
                print(f"   Complexity: {workflow_plan.get('complexity', 'N/A')}")
                
                for j, step in enumerate(steps, 1):
                    tool_name = step.get('tool_name', 'unknown')
                    title = step.get('title', 'No title')[:50]
                    deps = step.get('dependencies', [])
                    deps_str = f" (deps: {len(deps)})" if deps else ""
                    print(f"   {j}. {title} ({tool_name}){deps_str}")
                    
                # Check if workflow matches request type
                request_lower = request.lower()
                if 'görsel' in request_lower and 'gmail' in request_lower:
                    expected_tools = ['simple_visual_creator', 'gmail_helper']
                    actual_tools = [step.get('tool_name') for step in steps]
                    match = all(tool in actual_tools for tool in expected_tools)
                    print(f"   Request-Workflow Match: {'✅' if match else '❌'}")
                
            else:
                print(f"❌ Failed: {result.error}")
                
        except Exception as e:
            print(f"❌ Exception: {str(e)}")

def test_synthesis_methods():
    """Test individual synthesis methods"""
    print(f"\n🔧 Testing Individual Synthesis Methods")
    print("-" * 40)
    
    tool = SequentialThinkingTool()
    available_tools = ["gmail_helper", "simple_visual_creator", "command_executor", "llm_tool"]
    
    # Test visual with email
    request = "bana görsel üret ve gmail ile gönder"
    synthesis = tool._generate_dynamic_synthesis(request, available_tools)
    
    print(f"Visual + Email Synthesis:")
    print(f"  Length: {len(synthesis)} chars")
    print(f"  Contains visual generation: {'simple_visual_creator' in synthesis}")
    print(f"  Contains email sending: {'gmail_helper' in synthesis}")
    print(f"  Preview: {synthesis[:200]}...")

if __name__ == "__main__":
    test_dynamic_synthesis()
    test_synthesis_methods()