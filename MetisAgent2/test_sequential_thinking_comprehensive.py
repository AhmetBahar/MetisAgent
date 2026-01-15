#!/usr/bin/env python3
"""
Comprehensive Sequential Thinking Tool Test
Tests multi-step plan generation capabilities
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.sequential_thinking_tool import SequentialThinkingTool
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_sequential_thinking_workflow():
    """Test sequential thinking multi-step workflow planning"""
    print("🧠 Testing Sequential Thinking Tool - Multi-Step Plan Generation")
    print("=" * 70)
    
    # Initialize the tool
    tool = SequentialThinkingTool()
    
    # Test cases for multi-step planning
    test_cases = [
        {
            "name": "Gmail + Website Analysis",
            "request": "Son gelen gmail'in gönderensinin websitesini ziyaret et ve ekran görüntüsü al",
            "available_tools": ["gmail_helper", "selenium_browser", "llm_tool"],
            "expected_steps": 4
        },
        {
            "name": "Complex Multi-Tool Workflow", 
            "request": "Gmail'deki son maili al, gönderenin web sitesine git, görsel oluştur",
            "available_tools": ["gmail_helper", "playwright_browser", "simple_visual_creator", "llm_tool"],
            "expected_steps": 5
        },
        {
            "name": "Tool Installation Flow",
            "request": "Yeni bir sosyal medya aracı yükle ve test et",
            "available_tools": ["tool_manager", "command_executor"],
            "expected_steps": 3
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 Test Case {i}: {test_case['name']}")
        print(f"Request: {test_case['request']}")
        print(f"Available Tools: {', '.join(test_case['available_tools'])}")
        
        try:
            # Test plan_workflow action
            result = tool.execute_action(
                "plan_workflow",
                user_request=test_case['request'],
                available_tools=test_case['available_tools'],
                user_id="test_user"
            )
            
            if result.success:
                workflow_plan = result.data.get("workflow_plan", {})
                steps = workflow_plan.get("steps", [])
                
                print(f"✅ Success: Generated {len(steps)} steps")
                print(f"   Title: {workflow_plan.get('title', 'N/A')}")
                print(f"   Complexity: {workflow_plan.get('complexity', 'N/A')}")
                print(f"   Duration: {workflow_plan.get('estimated_duration', 0)} seconds")
                print(f"   Method: {result.data.get('planning_method', 'unknown')}")
                
                # Show step details
                for j, step in enumerate(steps[:3], 1):  # Show first 3 steps
                    print(f"   Step {j}: {step.get('title', 'Unknown')} ({step.get('tool_name', 'unknown')})")
                
                if len(steps) > 3:
                    print(f"   ... and {len(steps) - 3} more steps")
                
                results.append({
                    "test": test_case['name'],
                    "success": True,
                    "steps_generated": len(steps),
                    "expected_steps": test_case['expected_steps'],
                    "method": result.data.get('planning_method', 'unknown'),
                    "has_dependencies": any(step.get('dependencies', []) for step in steps),
                    "tools_used": list(set(step.get('tool_name') for step in steps))
                })
                
            else:
                print(f"❌ Failed: {result.error}")
                results.append({
                    "test": test_case['name'],
                    "success": False,
                    "error": result.error
                })
                
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
            results.append({
                "test": test_case['name'],
                "success": False,
                "error": str(e)
            })
    
    # Test break_down_task action
    print(f"\n🔧 Testing Task Breakdown Feature")
    try:
        breakdown_result = tool.execute_action(
            "break_down_task",
            task_description="Gmail'deki son e-postanın ekini indir ve analiz et",
            complexity_level="high",
            user_id="test_user"
        )
        
        if breakdown_result.success:
            breakdown = breakdown_result.data.get("breakdown", [])
            print(f"✅ Task Breakdown: {len(breakdown)} steps generated")
            print(f"   Method: {breakdown_result.data.get('method', 'unknown')}")
            for step in breakdown:
                print(f"   • {step.get('title', 'Unknown')}")
        else:
            print(f"❌ Task Breakdown Failed: {breakdown_result.error}")
            
    except Exception as e:
        print(f"❌ Task Breakdown Exception: {str(e)}")
    
    # Summary
    print(f"\n📊 Test Summary")
    print("=" * 50)
    successful_tests = sum(1 for r in results if r["success"])
    print(f"Successful Tests: {successful_tests}/{len(results)}")
    
    for result in results:
        if result["success"]:
            steps_ok = "✅" if result["steps_generated"] >= result["expected_steps"] else "⚠️"
            deps_ok = "✅" if result["has_dependencies"] else "⚠️"
            print(f"{steps_ok} {result['test']}: {result['steps_generated']} steps, deps: {deps_ok}")
            print(f"   Method: {result['method']}, Tools: {', '.join(result['tools_used'])}")
        else:
            print(f"❌ {result['test']}: {result.get('error', 'Unknown error')}")
    
    # Health check
    print(f"\n🏥 Health Check")
    health = tool.health_check()
    if health.success:
        print(f"✅ Tool Status: {health.data.get('status')}")
        print(f"   MCP Server: {health.data.get('mcp_server')}")
        print(f"   Server Path: {health.data.get('server_path', 'None')}")
    else:
        print(f"❌ Health Check Failed: {health.error}")
    
    return results

def test_mcp_server_integration():
    """Test MCP Sequential Thinking server integration"""
    print(f"\n🔌 Testing MCP Server Integration")
    print("-" * 40)
    
    tool = SequentialThinkingTool()
    
    # Direct MCP server test
    if tool.mcp_server_path:
        print(f"✅ MCP Server Found: {tool.mcp_server_path}")
        
        # Test direct MCP call
        try:
            mcp_result = tool._call_mcp_server("sequentialthinking", {
                "thought": "Plan a workflow to analyze Gmail and create visuals",
                "nextThoughtNeeded": True,
                "thoughtNumber": 1,
                "totalThoughts": 3
            })
            
            if mcp_result.get("success"):
                print("✅ MCP Server Response: Success")
                content = mcp_result.get("content", [])
                if content:
                    text_content = next((item["text"] for item in content if item.get("type") == "text"), "")
                    if text_content:
                        print(f"   Content Preview: {text_content[:100]}...")
                    else:
                        print("   No text content found")
                else:
                    print("   No content in response")
            else:
                print(f"❌ MCP Server Failed: {mcp_result.get('error')}")
                
        except Exception as e:
            print(f"❌ MCP Server Test Exception: {str(e)}")
    else:
        print("❌ MCP Server Not Found - Using Fallback")
    
    return tool.mcp_server_path is not None

if __name__ == "__main__":
    print("🚀 Starting Sequential Thinking Tool Comprehensive Test")
    print("="*70)
    
    # Test MCP integration first
    mcp_available = test_mcp_server_integration()
    
    # Test workflow planning
    test_results = test_sequential_thinking_workflow()
    
    # Final analysis
    print(f"\n🎯 Final Analysis")
    print("="*50)
    print(f"MCP Server Available: {'✅' if mcp_available else '❌'}")
    
    successful_workflows = sum(1 for r in test_results if r.get("success", False))
    total_workflows = len(test_results)
    
    print(f"Workflow Planning: {successful_workflows}/{total_workflows} successful")
    
    if successful_workflows == total_workflows and mcp_available:
        print("🎉 All tests passed! Sequential Thinking is working correctly.")
    elif successful_workflows == total_workflows:
        print("⚠️ Workflow planning works but using fallback (MCP server issues)")
    else:
        print("❌ Some workflow planning tests failed - needs debugging")
    
    # Check why multi-step plans might not be generated
    print(f"\n🔍 Multi-Step Generation Analysis")
    print("-" * 40)
    
    multi_step_tests = [r for r in test_results if r.get("success") and r.get("steps_generated", 0) > 1]
    single_step_tests = [r for r in test_results if r.get("success") and r.get("steps_generated", 0) <= 1]
    
    print(f"Multi-step workflows: {len(multi_step_tests)}")
    print(f"Single-step workflows: {len(single_step_tests)}")
    
    if single_step_tests:
        print("⚠️ Some tests generated only single steps - this might be the issue!")
        for test in single_step_tests:
            print(f"   • {test['test']}: {test['method']} method")
    
    if not multi_step_tests:
        print("❌ NO MULTI-STEP WORKFLOWS GENERATED - This is the problem!")
        print("   Possible causes:")
        print("   1. MCP server not properly parsing complex requests")
        print("   2. Fallback logic too simple") 
        print("   3. Tool mapping logic issues")
        print("   4. Agent not calling sequential thinking tool")