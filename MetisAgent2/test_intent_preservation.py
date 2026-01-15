#!/usr/bin/env python3
"""
Test Intent Preservation Implementation
Test the implemented user intent preservation in Gmail tools
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.llm_tool import LLMTool
from tools.gmail_helper_tool import GmailHelperTool

def test_intent_detection():
    """Test intent detection functionality"""
    print("🧪 Testing Intent Detection")
    print("=" * 40)
    
    llm_tool = LLMTool()
    
    test_messages = [
        "gönderen bilgilerini listele",
        "son mail konusunu göster", 
        "emailde ek dosya var mı?",
        "mail ne zaman geldi?",
        "gmail durumunu kontrol et"
    ]
    
    expected_intents = [
        "sender_request",
        "subject_request", 
        "attachment_request",
        "date_request",
        "general_request"
    ]
    
    for i, (message, expected) in enumerate(zip(test_messages, expected_intents), 1):
        detected = llm_tool.detect_user_intent(message)
        status = "✅" if detected == expected else "❌"
        
        print(f"{i}. '{message}'")
        print(f"   Expected: {expected}")
        print(f"   Detected: {detected} {status}")
        print()

def test_system_prompt_enhancement():
    """Test system prompt enhancement with intent"""
    print("🧪 Testing System Prompt Enhancement")
    print("=" * 40)
    
    llm_tool = LLMTool()
    
    base_prompt = "You are a helpful assistant."
    
    intents = ["sender_request", "subject_request", "attachment_request", "general_request"]
    
    for intent in intents:
        enhanced = llm_tool.enhance_system_prompt_with_intent(base_prompt, intent)
        
        print(f"Intent: {intent}")
        print(f"Enhanced prompt length: {len(enhanced)} chars")
        
        if intent == "sender_request":
            assert "SENDER information" in enhanced
            assert "from' field" in enhanced
            print("   ✅ Sender intent properly injected")
        elif intent == "subject_request":
            assert "SUBJECT information" in enhanced
            assert "subject' field" in enhanced
            print("   ✅ Subject intent properly injected")
        
        print()

def test_gmail_response_filtering():
    """Test Gmail response filtering by intent"""
    print("🧪 Testing Gmail Response Filtering")
    print("=" * 40)
    
    gmail_tool = GmailHelperTool()
    
    # Mock Gmail data
    mock_data = {
        'subject': 'Important Meeting Tomorrow',
        'from': 'john.doe@example.com',
        'date': 'Mon, 26 Jul 2025 10:30:00 +0000',
        'message_id': '18f12345678901234',
        'thread_id': '18f12345678901234',
        'has_attachments': True,
        'attachments': [{'filename': 'report.pdf'}]
    }
    
    test_intents = [
        ("sender_request", ["from", "intent", "focused_field"]),
        ("subject_request", ["subject", "intent", "focused_field"]),
        ("attachment_request", ["has_attachments", "attachments", "intent", "focused_field"]),
        ("date_request", ["date", "intent", "focused_field"])
    ]
    
    for intent, expected_fields in test_intents:
        filtered = gmail_tool.filter_response_by_intent(mock_data, intent)
        
        print(f"Intent: {intent}")
        print(f"   Fields: {list(filtered.keys())}")
        print(f"   Expected: {expected_fields}")
        
        fields_match = all(field in filtered for field in expected_fields)
        status = "✅" if fields_match else "❌"
        print(f"   Status: {status}")
        
        if intent == "sender_request":
            assert filtered.get('from') == 'john.doe@example.com'
            assert 'subject' not in filtered  # Should NOT include subject
            print("   ✅ Sender filtering works correctly")
        elif intent == "subject_request":
            assert filtered.get('subject') == 'Important Meeting Tomorrow'
            assert 'from' not in filtered  # Should NOT include sender
            print("   ✅ Subject filtering works correctly")
        
        print()

def test_full_workflow_simulation():
    """Simulate full workflow with intent preservation"""
    print("🧪 Testing Full Workflow Simulation")
    print("=" * 40)
    
    # 1. User request
    user_requests = [
        "gönderen bilgilerini listele",
        "son mail konusunu göster"
    ]
    
    llm_tool = LLMTool()
    gmail_tool = GmailHelperTool()
    
    for request in user_requests:
        print(f"User Request: '{request}'")
        
        # Step 1: Detect intent
        intent = llm_tool.detect_user_intent(request)
        print(f"   Detected Intent: {intent}")
        
        # Step 2: Mock Gmail API response
        mock_gmail_data = {
            'subject': 'Important Meeting Tomorrow',
            'from': 'john.doe@example.com',
            'date': 'Mon, 26 Jul 2025 10:30:00 +0000'
        }
        
        # Step 3: Filter response by intent
        filtered_data = gmail_tool.filter_response_by_intent(mock_gmail_data, intent)
        print(f"   Filtered Data: {filtered_data}")
        
        # Step 4: Generate intent-aware response
        if intent == "sender_request":
            expected_response = f"📧 Gönderen: {filtered_data.get('from')}"
        elif intent == "subject_request":
            expected_response = f"📝 Konu: {filtered_data.get('subject')}"
        else:
            expected_response = "General response"
        
        print(f"   Expected Response: {expected_response}")
        print()

if __name__ == "__main__":
    test_intent_detection()
    test_system_prompt_enhancement()
    test_gmail_response_filtering()
    test_full_workflow_simulation()
    print("🎉 All intent preservation tests completed!")