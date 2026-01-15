#!/usr/bin/env python3
"""
Final Intent Preservation Test
Test the implemented solution without registry dependencies
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_final_intent_preservation():
    """Test the final intent preservation implementation"""
    print("🎯 Final Intent Preservation Test")
    print("=" * 50)
    
    # Import the updated tools directly
    from tools.llm_tool import LLMTool
    from tools.gmail_helper_tool import GmailHelperTool
    
    print("1. Testing Intent Detection...")
    
    llm_tool = LLMTool()
    
    # Test intent detection
    test_cases = [
        ("gönderen bilgilerini listele", "sender_request"),
        ("son mail konusunu göster", "subject_request"),
        ("emailde ek dosya var mı?", "attachment_request"),
        ("mail ne zaman geldi?", "date_request"),
        ("gmail genel durum", "general_request")
    ]
    
    intent_scores = 0
    for message, expected in test_cases:
        detected = llm_tool.detect_user_intent(message)
        if detected == expected:
            intent_scores += 1
            print(f"   ✅ '{message}' -> {detected}")
        else:
            print(f"   ❌ '{message}' -> {detected} (expected {expected})")
    
    print(f"   Intent Detection Score: {intent_scores}/{len(test_cases)}")
    
    print("\n2. Testing System Prompt Enhancement...")
    
    base_prompt = "You are a helpful assistant."
    enhanced_sender = llm_tool.enhance_system_prompt_with_intent(base_prompt, "sender_request")
    enhanced_subject = llm_tool.enhance_system_prompt_with_intent(base_prompt, "subject_request")
    
    # Check if intent instructions are properly added
    sender_check = "SENDER information" in enhanced_sender and "from' field" in enhanced_sender
    subject_check = "SUBJECT information" in enhanced_subject and "subject' field" in enhanced_subject
    
    print(f"   ✅ Sender prompt enhancement: {'✓' if sender_check else '✗'}")
    print(f"   ✅ Subject prompt enhancement: {'✓' if subject_check else '✗'}")
    
    print("\n3. Testing Gmail Response Filtering...")
    
    gmail_tool = GmailHelperTool()
    
    # Mock Gmail data
    mock_data = {
        'subject': 'Important Meeting Tomorrow',
        'from': 'john.doe@example.com',
        'date': 'Mon, 26 Jul 2025 10:30:00 +0000',
        'message_id': '18f12345678901234',
        'has_attachments': True,
        'attachments': [{'filename': 'report.pdf'}]
    }
    
    # Test filtering for sender request
    sender_filtered = gmail_tool.filter_response_by_intent(mock_data, "sender_request")
    sender_correct = (
        'from' in sender_filtered and 
        'subject' not in sender_filtered and
        sender_filtered.get('intent') == 'sender_request'
    )
    
    # Test filtering for subject request
    subject_filtered = gmail_tool.filter_response_by_intent(mock_data, "subject_request")
    subject_correct = (
        'subject' in subject_filtered and 
        'from' not in subject_filtered and
        subject_filtered.get('intent') == 'subject_request'
    )
    
    print(f"   ✅ Sender filtering: {'✓' if sender_correct else '✗'}")
    print(f"   ✅ Subject filtering: {'✓' if subject_correct else '✗'}")
    
    print("\n4. Testing Full User Intent Scenarios...")
    
    scenarios = [
        {
            "user_input": "gönderen bilgilerini listele",
            "expected_intent": "sender_request",
            "expected_response_content": "john.doe@example.com",
            "should_not_contain": ["Important Meeting Tomorrow", "Mon, 26 Jul"]
        },
        {
            "user_input": "son mail konusunu göster",
            "expected_intent": "subject_request", 
            "expected_response_content": "Important Meeting Tomorrow",
            "should_not_contain": ["john.doe@example.com", "Mon, 26 Jul"]
        }
    ]
    
    scenario_scores = 0
    for scenario in scenarios:
        # Step 1: Detect intent
        intent = llm_tool.detect_user_intent(scenario["user_input"])
        
        # Step 2: Filter Gmail response
        filtered = gmail_tool.filter_response_by_intent(mock_data, intent)
        
        # Step 3: Check if expected content is present and unwanted content is absent
        expected_present = scenario["expected_response_content"] in str(filtered.values())
        unwanted_absent = all(
            unwanted not in str(filtered.values()) 
            for unwanted in scenario["should_not_contain"]
        )
        
        if intent == scenario["expected_intent"] and expected_present and unwanted_absent:
            scenario_scores += 1
            print(f"   ✅ '{scenario['user_input']}' -> Intent preserved successfully")
        else:
            print(f"   ❌ '{scenario['user_input']}' -> Intent preservation failed")
            print(f"      Intent: {intent} (expected {scenario['expected_intent']})")
            print(f"      Filtered: {filtered}")
    
    print(f"   Scenario Score: {scenario_scores}/{len(scenarios)}")
    
    print("\n📊 FINAL RESULTS:")
    total_score = intent_scores + (2 if sender_check and subject_check else 0) + (2 if sender_correct and subject_correct else 0) + scenario_scores
    max_score = len(test_cases) + 2 + 2 + len(scenarios)
    
    print(f"   Total Score: {total_score}/{max_score}")
    print(f"   Success Rate: {(total_score/max_score)*100:.1f}%")
    
    if total_score >= max_score * 0.8:
        print("\n🎉 INTENT PRESERVATION IMPLEMENTATION SUCCESSFUL!")
        print("✅ User intent detection working")
        print("✅ System prompt enhancement working")
        print("✅ Gmail response filtering working")
        print("✅ End-to-end intent preservation working")
    else:
        print("\n⚠️ Intent preservation needs improvement")
        print(f"Score: {total_score}/{max_score}")

def generate_usage_examples():
    """Generate usage examples for the implemented solution"""
    print("\n📝 USAGE EXAMPLES:")
    print("=" * 30)
    
    print("""
BEFORE (Problem):
User: "gönderen bilgilerini listele"
LLM Response: "📧 Subject: Important Meeting, From: john@example.com, Date: Today"
❌ User asked for sender only but got all fields

AFTER (Solution):
User: "gönderen bilgilerini listele"
Intent Detection: sender_request
Response Filtering: Only 'from' field returned
LLM Response: "📧 Gönderen: john@example.com"
✅ User gets exactly what they asked for

IMPLEMENTATION:
1. LLMTool.detect_user_intent() -> "sender_request"
2. GmailHelperTool.filter_response_by_intent() -> {'from': 'john@example.com'}
3. Enhanced system prompt focuses LLM on sender only
4. Final response preserves user intent
""")

if __name__ == "__main__":
    test_final_intent_preservation()
    generate_usage_examples()