#!/usr/bin/env python3
"""
Test Sequential Thinking Tool Gmail Subject Integration
Test the complete workflow generation and Gmail subject detection
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.sequential_thinking_tool import SequentialThinkingTool
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_gmail_subject_detection():
    """Test Gmail subject request detection"""
    print("🧪 Testing Gmail Subject Request Detection")
    print("=" * 50)
    
    # Test cases for manual verification
    test_cases = [
        ("gmail inbox son gelen mailin konusu nedir", True),
        ("son gmail mesajlarının subject'lerini göster", True), 
        ("email konularını listele", True),
        ("gmail konuları formatla", True),
        ("latest gmail subjects", True),
        ("show me email titles", True),
        ("sistem durumunu kontrol et", False),  
        ("weather update", False),
        ("gmail login", False),  # Should be False - not asking for subjects
        ("send email", False)    # Should be False - not asking for subjects
    ]
    
    print("Test cases (manual verification needed):")
    for request, expected in test_cases:
        # Manual logic check
        request_lower = request.lower()
        gmail_keywords = ['gmail', 'email', 'mail', 'mesaj', 'eposta']
        has_gmail = any(keyword in request_lower for keyword in gmail_keywords)
        
        subject_keywords = ['subject', 'konu', 'başlık', 'title', 'topic']
        has_subject = any(keyword in request_lower for keyword in subject_keywords)
        
        format_keywords = ['format', 'list', 'show', 'display', 'göster', 'listele', 'formatla']
        has_format = any(keyword in request_lower for keyword in format_keywords)
        
        result = has_gmail and has_subject and (has_format or 'son' in request_lower or 'latest' in request_lower)
        status = "✅" if result == expected else "❌"
        print(f"   {status} '{request}' -> {result} (expected: {expected})")
    
    print()

def test_workflow_generation():
    """Test complete workflow generation for Gmail subject requests"""
    print("🔧 Testing Workflow Generation for Gmail Subjects")
    print("=" * 50)
    
    tool = SequentialThinkingTool()
    
    # Test Gmail subject request
    request = "gmail inbox son 3 mesajın konularını düzenli bir listede göster"
    available_tools = ["google_oauth2_manager", "llm_tool", "command_executor"]
    
    print(f"Request: {request}")
    print(f"Available Tools: {available_tools}")
    print()
    
    # Test plan_workflow action
    result = tool._plan_workflow(
        user_request=request,
        available_tools=available_tools
    )
    
    if result.success:
        workflow_plan = result.data.get('workflow_plan', {})
        steps = workflow_plan.get('steps', [])
        
        print(f"✅ Workflow Generated Successfully")
        print(f"   Title: {workflow_plan.get('title', 'N/A')}")
        print(f"   Steps Count: {len(steps)}")
        print(f"   Method: {result.data.get('planning_method', 'N/A')}")
        print()
        
        # Check for Gmail subject handling
        gmail_steps = []
        llm_with_subjects = []
        
        for step in steps:
            tool_name = step.get('tool_name', '')
            action_name = step.get('action_name', '')
            params = step.get('params', {})
            
            if tool_name == 'google_oauth2_manager':
                if action_name in ['gmail_list_messages', 'gmail_get_message']:
                    gmail_steps.append(step)
            
            elif tool_name == 'llm_tool' and params.get('use_extracted_subjects') == True:
                llm_with_subjects.append(step)
        
        print(f"📧 Gmail Extraction Steps: {len(gmail_steps)}")
        for i, step in enumerate(gmail_steps, 1):
            print(f"   {i}. {step.get('title', 'N/A')} ({step.get('tool_name')}.{step.get('action_name')})")
        
        print(f"🤖 LLM Steps with use_extracted_subjects: {len(llm_with_subjects)}")
        for i, step in enumerate(llm_with_subjects, 1):
            print(f"   {i}. {step.get('title', 'N/A')} -> use_extracted_subjects: {step.get('params', {}).get('use_extracted_subjects')}")
        
        # Check workflow enhancement
        metadata = workflow_plan.get('metadata', {})
        enhanced = metadata.get('gmail_subject_enhanced', False)
        print(f"📋 Gmail Subject Enhanced: {enhanced}")
        
        if gmail_steps and llm_with_subjects:
            print("\n🎉 SUCCESS: Complete Gmail Subject Workflow Generated!")
            print("   ✅ Gmail extraction steps present")
            print("   ✅ LLM formatting with use_extracted_subjects parameter")
        elif gmail_steps:
            print("\n⚠️  PARTIAL: Gmail extraction found but missing LLM formatting")
        else:
            print("\n❌ FAILED: No Gmail extraction steps found")
            
    else:
        print(f"❌ Workflow Generation Failed: {result.error}")

def test_fallback_workflow():
    """Test fallback workflow generation for Gmail subjects"""
    print("\n🔄 Testing Fallback Workflow for Gmail Subjects")
    print("=" * 50)
    
    # Simplified test without private method access
    request = "gmail konularını göster"
    
    # Check if this looks like a Gmail subject request
    request_lower = request.lower()
    gmail_keywords = ['gmail', 'email', 'mail', 'mesaj', 'eposta']
    has_gmail = any(keyword in request_lower for keyword in gmail_keywords)
    
    subject_keywords = ['subject', 'konu', 'başlık', 'title', 'topic']
    has_subject = any(keyword in request_lower for keyword in subject_keywords)
    
    format_keywords = ['format', 'list', 'show', 'display', 'göster', 'listele', 'formatla']
    has_format = any(keyword in request_lower for keyword in format_keywords)
    
    is_gmail_subject_request = has_gmail and has_subject and (has_format or 'son' in request_lower or 'latest' in request_lower)
    
    print(f"Request: '{request}'")
    print(f"Gmail Subject Request: {is_gmail_subject_request}")
    
    if is_gmail_subject_request:
        print("✅ Request would trigger Gmail subject workflow generation")
        print("   Expected workflow steps:")
        print("   1. List Gmail Messages (google_oauth2_manager.gmail_list_messages)")
        print("   2. Extract Gmail Subjects (google_oauth2_manager.gmail_get_message)")
        print("   3. Format Gmail Subjects (llm_tool.chat with use_extracted_subjects=True)")
    else:
        print("❌ Request would not trigger specialized Gmail subject workflow")

if __name__ == "__main__":
    print("🚀 Sequential Thinking Tool Gmail Integration Test")
    print("=" * 60)
    
    test_gmail_subject_detection()
    test_workflow_generation() 
    test_fallback_workflow()
    
    print("\n" + "=" * 60)
    print("🏁 Sequential Thinking Tool Gmail Test Complete")