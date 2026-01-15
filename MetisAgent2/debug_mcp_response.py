#!/usr/bin/env python3
"""
Debug MCP Sequential Thinking Response
Analyze why MCP server response doesn't generate multi-step workflows
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.sequential_thinking_tool import SequentialThinkingTool
import json
import logging

# Setup detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_mcp_response():
    """Debug MCP server response parsing"""
    print("🔍 Debugging MCP Sequential Thinking Response")
    print("=" * 60)
    
    tool = SequentialThinkingTool()
    
    if not tool.mcp_server_path:
        print("❌ MCP server not found")
        return
    
    print(f"✅ MCP Server: {tool.mcp_server_path}")
    
    # Test with complex request
    test_requests = [
        "Gmail'deki son maili al, gönderenin web sitesine git, ekran görüntüsü al ve görsel oluştur",
        "Son gelen email'in gönderensinin websitesini ziyaret et ve screenshot al",
        "Yeni tool yükle ve test et"
    ]
    
    for i, request in enumerate(test_requests, 1):
        print(f"\n🧪 Test {i}: {request}")
        print("-" * 50)
        
        # Direct MCP call
        mcp_result = tool._call_mcp_server("sequentialthinking", {
            "thought": f"Breaking down workflow: {request}. Available tools: gmail_helper, selenium_browser, simple_visual_creator",
            "nextThoughtNeeded": True,
            "thoughtNumber": 1,
            "totalThoughts": 3
        })
        
        print(f"MCP Success: {mcp_result.get('success')}")
        
        if mcp_result.get('success'):
            content = mcp_result.get('content', [])
            print(f"Content items: {len(content)}")
            
            for j, item in enumerate(content):
                print(f"  Item {j}: type={item.get('type')}")
                if item.get('type') == 'text':
                    text = item.get('text', '')
                    print(f"    Text length: {len(text)}")
                    print(f"    Text preview: {text[:200]}...")
                    
                    # Test parsing
                    available_tools = ["gmail_helper", "selenium_browser", "simple_visual_creator", "llm_tool"]
                    workflow = tool._convert_thinking_to_workflow(text, request, available_tools)
                    
                    print(f"    Parsed workflow steps: {len(workflow.get('steps', []))}")
                    print(f"    Workflow title: {workflow.get('title', 'N/A')}")
                    
                    # Check step details
                    steps = workflow.get('steps', [])
                    for k, step in enumerate(steps[:2]):  # Show first 2 steps
                        print(f"      Step {k+1}: {step.get('title')} ({step.get('tool_name')})")
                    
                    # Test step extraction
                    extracted_steps = tool._extract_steps_from_thinking(text)
                    print(f"    Extracted logical steps: {len(extracted_steps)}")
                    
                    for k, step in enumerate(extracted_steps[:3]):
                        print(f"      Logical step {k+1}: {step.get('title', 'No title')}")
        else:
            print(f"❌ MCP Error: {mcp_result.get('error')}")
    
    # Test the parsing functions directly
    print(f"\n🔧 Testing parsing functions")
    print("-" * 30)
    
    sample_thinking_text = """
    1. First, I need to get the latest email from Gmail
    2. Then extract the sender information 
    3. Navigate to the sender's website
    4. Take a screenshot of the website
    5. Generate a visual report
    """
    
    extracted = tool._extract_steps_from_thinking(sample_thinking_text)
    print(f"Sample text extraction: {len(extracted)} steps")
    for step in extracted:
        print(f"  • {step.get('title')}")
    
    available_tools = ["gmail_helper", "selenium_browser", "simple_visual_creator"]
    mapped = tool._map_steps_to_tools(extracted, available_tools)
    print(f"Tool mapping: {len(mapped)} mapped steps")
    for step in mapped:
        print(f"  • {step.get('title')} → {step.get('tool_name')}")

def test_convert_thinking_directly():
    """Test the _convert_thinking_to_workflow function directly"""
    print(f"\n🎯 Direct _convert_thinking_to_workflow Test")
    print("-" * 50)
    
    tool = SequentialThinkingTool()
    
    # Simulate MCP server response text
    thinking_texts = [
        """
        {
          "thoughtNumber": 1,
          "totalThoughts": 3,
          "nextThoughtNeeded": true,
          "branches": [],
          "thoughtHistoryLength": 1
        }
        
        Breaking down the Gmail workflow:
        1. Connect to Gmail and get the latest email
        2. Extract sender information from the email
        3. Visit the sender's website
        4. Take a screenshot
        5. Generate visual content
        """,
        """
        Step by step analysis:
        - Get Gmail email (use gmail_helper)
        - Extract domain from sender
        - Navigate to website (use selenium_browser)  
        - Capture screenshot
        - Process with visual tool
        """,
        """
        Workflow planning:
        First, authenticate with Gmail API
        Next, retrieve most recent message
        Then, parse sender domain
        After that, open browser
        Finally, take screenshot
        """
    ]
    
    request = "Gmail'deki son maili al, gönderenin web sitesine git, ekran görüntüsü al"
    available_tools = ["gmail_helper", "selenium_browser", "simple_visual_creator", "llm_tool"]
    
    for i, thinking_text in enumerate(thinking_texts, 1):
        print(f"\nThinking Text {i}:")
        workflow = tool._convert_thinking_to_workflow(thinking_text, request, available_tools)
        
        print(f"Generated steps: {len(workflow.get('steps', []))}")
        print(f"Title: {workflow.get('title', 'N/A')}")
        
        for j, step in enumerate(workflow.get('steps', [])[:3]):
            print(f"  Step {j+1}: {step.get('title')} ({step.get('tool_name')})")

if __name__ == "__main__":
    debug_mcp_response()
    test_convert_thinking_directly()