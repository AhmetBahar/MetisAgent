#!/usr/bin/env python3
"""
Test Iterative Sequential Thinking - Multi-cycle workflow generation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.sequential_thinking_tool import SequentialThinkingTool
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_iterative_thinking():
    """Test the new iterative sequential thinking approach"""
    print("🔄 Testing Iterative Sequential Thinking")
    print("=" * 60)
    
    tool = SequentialThinkingTool()
    
    if not tool.mcp_server_path:
        print("❌ MCP server not found")
        return
    
    print(f"✅ MCP Server: {tool.mcp_server_path}")
    
    # Test case: Complex Gmail workflow
    test_request = "Gmail'deki son maili al, gönderenin web sitesine git, ekran görüntüsü al ve görsel oluştur"
    available_tools = ["gmail_helper", "selenium_browser", "simple_visual_creator", "llm_tool"]
    
    print(f"\n🧪 Test Request: {test_request}")
    print(f"Available Tools: {', '.join(available_tools)}")
    
    try:
        # Test complete thinking cycle
        print(f"\n🔄 Running Complete Thinking Cycle...")
        full_thinking = tool._run_complete_thinking_cycle(test_request, available_tools, totalThoughts=3)
        
        if full_thinking:
            print(f"✅ Complete thinking generated: {len(full_thinking)} characters")
            print(f"📝 Preview:\n{full_thinking[:500]}...\n")
            
            # Test workflow conversion
            print(f"🔧 Converting to workflow...")
            workflow = tool._convert_thinking_to_workflow(full_thinking, test_request, available_tools)
            
            print(f"Generated Workflow:")
            print(f"  Title: {workflow.get('title')}")
            print(f"  Complexity: {workflow.get('complexity')}")
            print(f"  Duration: {workflow.get('estimated_duration')} seconds")
            print(f"  Steps: {len(workflow.get('steps', []))}")
            
            steps = workflow.get('steps', [])
            for i, step in enumerate(steps, 1):
                deps = step.get('dependencies', [])
                deps_str = f" (deps: {', '.join(deps)})" if deps else ""
                print(f"    {i}. {step.get('title')} ({step.get('tool_name')}){deps_str}")
            
            # Test via plan_workflow action
            print(f"\n🎯 Testing via plan_workflow action...")
            result = tool.execute_action(
                "plan_workflow",
                user_request=test_request,
                available_tools=available_tools,
                user_id="test_user"
            )
            
            if result.success:
                workflow_data = result.data.get("workflow_plan", {})
                method = result.data.get("planning_method", "unknown")
                steps_count = len(workflow_data.get("steps", []))
                
                print(f"✅ Action Success: {steps_count} steps via {method}")
                
                if steps_count > 1:
                    print(f"🎉 MULTI-STEP WORKFLOW GENERATED!")
                else:
                    print(f"⚠️ Still generating single step workflow")
                    
            else:
                print(f"❌ Action Failed: {result.error}")
        else:
            print(f"❌ Complete thinking cycle failed")
            
    except Exception as e:
        print(f"❌ Test Exception: {str(e)}")

def test_direct_mcp_phases():
    """Test direct MCP phases to understand the output"""
    print(f"\n🔍 Direct MCP Phase Testing")
    print("-" * 40)
    
    tool = SequentialThinkingTool()
    
    phases = [
        "Phase 1: Breaking down Gmail workflow - identify main steps",
        "Phase 2: Sequencing the workflow - determine order and dependencies",
        "Phase 3: Tool mapping and validation - ensure proper implementation"
    ]
    
    for i, phase_desc in enumerate(phases, 1):
        print(f"\n📋 Testing Phase {i}: {phase_desc}")
        
        result = tool._call_mcp_server("sequentialthinking", {
            "thought": phase_desc,
            "nextThoughtNeeded": i < len(phases),
            "thoughtNumber": i,
            "totalThoughts": len(phases)
        })
        
        if result.get('success'):
            content = result.get('content', [])
            for item in content:
                if item.get('type') == 'text':
                    text = item.get('text', '')
                    print(f"  Response: {text[:200]}...")
                    
                    # Check if this contains actual thinking content
                    if len(text) > 50 and any(word in text.lower() for word in ['step', 'workflow', 'gmail', 'website']):
                        print(f"  ✅ Contains meaningful content")
                    else:
                        print(f"  ⚠️ Minimal content - might just be metadata")
        else:
            print(f"  ❌ Phase failed: {result.get('error')}")

if __name__ == "__main__":
    test_iterative_thinking()
    test_direct_mcp_phases()