#!/usr/bin/env python3
"""
Test MCP Response Parsing - Debug workflow generation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.sequential_thinking_tool import SequentialThinkingTool

def test_mcp_parsing():
    """Test MCP response parsing with detailed output"""
    print("🧪 Testing MCP Response Parsing")
    print("=" * 50)
    
    tool = SequentialThinkingTool()
    
    # Direct MCP call
    request = "Gmail'deki son maili al, gönderenin web sitesine git, ekran görüntüsü al"
    available_tools = ["gmail_helper", "selenium_browser", "simple_visual_creator", "llm_tool"]
    
    mcp_result = tool._call_mcp_server("sequentialthinking", {
        "thought": f"Breaking down workflow: {request}. Available tools: {', '.join(available_tools)}",
        "nextThoughtNeeded": True,
        "thoughtNumber": 1,
        "totalThoughts": 3
    })
    
    print(f"MCP Result Success: {mcp_result.get('success')}")
    
    if mcp_result.get('success'):
        content = mcp_result.get('content', [])
        print(f"Content items: {len(content)}")
        
        for i, item in enumerate(content):
            print(f"\nContent Item {i}:")
            print(f"  Type: {item.get('type')}")
            if item.get('type') == 'text':
                text = item.get('text', '')
                print(f"  Text: {text}")
                
                # Test conversion
                print(f"\n🔄 Testing _convert_thinking_to_workflow")
                workflow = tool._convert_thinking_to_workflow(text, request, available_tools)
                
                print(f"Generated workflow:")
                print(f"  Title: {workflow.get('title')}")
                print(f"  Steps: {len(workflow.get('steps', []))}")
                
                steps = workflow.get('steps', [])
                for j, step in enumerate(steps):
                    print(f"    Step {j+1}: {step.get('title')} ({step.get('tool_name')})")
                
                # Test step-by-step parsing
                print(f"\n🔍 Step-by-step parsing:")
                
                # 1. Extract steps
                extracted_steps = tool._extract_steps_from_thinking(text)
                print(f"  Extracted logical steps: {len(extracted_steps)}")
                for step in extracted_steps:
                    print(f"    • {step.get('title', 'No title')}")
                
                # 2. Map to tools
                if extracted_steps:
                    mapped_steps = tool._map_steps_to_tools(extracted_steps, available_tools)
                    print(f"  Mapped to tools: {len(mapped_steps)}")
                    for step in mapped_steps:
                        print(f"    • {step.get('title')} → {step.get('tool_name')}")
                
                # 3. Check why parsing might fail
                print(f"\n🔎 Parsing analysis:")
                print(f"  Text contains numbered steps: {'1.' in text or '2.' in text}")
                print(f"  Text contains action verbs: {any(word in text.lower() for word in ['get', 'visit', 'take', 'extract'])}")
                print(f"  Text length: {len(text)} chars")
    else:
        print(f"❌ MCP Error: {mcp_result.get('error')}")

if __name__ == "__main__":
    test_mcp_parsing()