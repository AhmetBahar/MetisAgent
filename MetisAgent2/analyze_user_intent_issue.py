#!/usr/bin/env python3
"""
Analyze User Intent Preservation Issue in LLM Tool
Test how user intent gets lost between tool execution and LLM response formatting
"""

import json
import logging
from app.mcp_core import registry

def analyze_user_intent_issue():
    """Analyze the user intent preservation problem"""
    print("🔍 Analyzing User Intent Preservation Issue")
    print("=" * 60)
    
    # Test scenario: User asks for "gönderen bilgileri" but gets subjects
    user_requests = [
        {
            "request": "gönderen bilgilerini listele",
            "expected_focus": "sender information (from field)",
            "description": "User wants sender information, not subjects"
        },
        {
            "request": "son mail konusunu göster", 
            "expected_focus": "subject information",
            "description": "User wants subject information"
        },
        {
            "request": "emaildeki attachment var mı?",
            "expected_focus": "attachment information",
            "description": "User wants attachment information"
        }
    ]
    
    # Simulate Gmail API response data structure
    mock_gmail_api_response = {
        "success": True,
        "data": {
            "message": {
                "id": "18f12345678901234",
                "threadId": "18f12345678901234",
                "labelIds": ["INBOX", "UNREAD"],
                "snippet": "This is a test email for analysis...",
                "payload": {
                    "headers": [
                        {"name": "From", "value": "john.doe@example.com"},
                        {"name": "To", "value": "user@example.com"}, 
                        {"name": "Subject", "value": "Important Meeting Tomorrow"},
                        {"name": "Date", "value": "Mon, 26 Jul 2025 10:30:00 +0000"},
                        {"name": "Message-ID", "value": "<CAB123@mail.gmail.com>"}
                    ],
                    "parts": [
                        {
                            "mimeType": "text/plain",
                            "body": {"data": "VGVzdCBtZXNzYWdlIGNvbnRlbnQ="}
                        },
                        {
                            "mimeType": "application/pdf",
                            "filename": "report.pdf",
                            "body": {"attachmentId": "ANT123456"}
                        }
                    ]
                }
            }
        }
    }
    
    print("📧 Mock Gmail API Response Structure:")
    print(json.dumps(mock_gmail_api_response, indent=2)[:500] + "...")
    print()
    
    # Analyze how gmail_helper_tool processes this data
    print("🔧 Gmail Helper Tool Processing:")
    gmail_processed = analyze_gmail_helper_processing(mock_gmail_api_response)
    print(f"Processed fields: {list(gmail_processed.keys())}")
    print(f"Available data: {gmail_processed}")
    print()
    
    # Test each user request scenario
    for i, scenario in enumerate(user_requests, 1):
        print(f"📋 Scenario {i}: {scenario['request']}")
        print(f"   Expected Focus: {scenario['expected_focus']}")
        print(f"   Description: {scenario['description']}")
        
        # Analyze LLM response generation
        llm_analysis = analyze_llm_response_generation(
            scenario['request'], 
            gmail_processed,
            scenario['expected_focus']
        )
        
        print(f"   🤖 LLM Analysis:")
        print(f"     - Field selection: {llm_analysis['selected_fields']}")
        print(f"     - Intent preservation: {llm_analysis['intent_preserved']}")
        print(f"     - Issue: {llm_analysis['issue']}")
        print(f"     - Proposed fix: {llm_analysis['proposed_fix']}")
        print()
    
    # Propose LLM-based solution
    print("💡 Proposed LLM-Based Solution:")
    propose_llm_intent_solution()

def analyze_gmail_helper_processing(api_response):
    """Simulate how gmail_helper_tool processes API response"""
    try:
        message = api_response['data']['message']
        payload = message.get('payload', {})
        headers = payload.get('headers', [])
        
        # Extract header information (current logic)
        processed_data = {
            'message_id': message.get('id'),
            'subject': None,
            'from': None, 
            'to': None,
            'date': None,
            'snippet': message.get('snippet', ''),
            'thread_id': message.get('threadId'),
            'all_headers': headers
        }
        
        for header in headers:
            name = header.get('name', '').lower()
            value = header.get('value', '')
            
            if name == 'subject':
                processed_data['subject'] = value
            elif name == 'from':
                processed_data['from'] = value
            elif name == 'to':
                processed_data['to'] = value
            elif name == 'date':
                processed_data['date'] = value
        
        # Check for attachments
        parts = payload.get('parts', [])
        attachments = []
        for part in parts:
            if part.get('filename'):
                attachments.append({
                    'filename': part.get('filename'),
                    'mimeType': part.get('mimeType'),
                    'size': part.get('body', {}).get('size', 0)
                })
        
        processed_data['attachments'] = attachments
        processed_data['has_attachments'] = len(attachments) > 0
        
        return processed_data
        
    except Exception as e:
        return {'error': f"Processing error: {e}"}

def analyze_llm_response_generation(user_request, gmail_data, expected_focus):
    """Analyze how LLM would generate response for user request"""
    
    # Simulate LLM decision making process
    request_lower = user_request.lower()
    
    # Current problematic logic (field selection without intent preservation)
    if 'gönderen' in request_lower or 'sender' in request_lower:
        # User wants sender info
        intended_field = 'from'
        selected_fields = ['from']  # Should focus on this
        
        # But LLM might also include subject (causing confusion)
        actual_selected = ['subject', 'from', 'date']  # This is the problem
        
        intent_preserved = 'from' in actual_selected and actual_selected[0] == 'from'
        issue = "LLM includes too many fields, diluting user's specific request"
        
    elif 'subject' in request_lower or 'konu' in request_lower:
        intended_field = 'subject'
        selected_fields = ['subject']
        actual_selected = ['subject', 'from', 'date'] 
        intent_preserved = True
        issue = "Generally works correctly for subject requests"
        
    elif 'attachment' in request_lower or 'ek' in request_lower:
        intended_field = 'attachments'
        selected_fields = ['attachments', 'has_attachments']
        actual_selected = ['has_attachments', 'attachments']
        intent_preserved = True
        issue = "Attachment detection works when properly implemented"
        
    else:
        intended_field = 'unknown'
        selected_fields = ['all']
        actual_selected = ['subject', 'from', 'date']  # Default fallback
        intent_preserved = False
        issue = "Unknown intent defaults to generic response"
    
    # Analyze the gap
    return {
        'intended_field': intended_field,
        'selected_fields': selected_fields,
        'actual_selected': actual_selected,
        'intent_preserved': intent_preserved,
        'issue': issue,
        'proposed_fix': generate_intent_fix(user_request, intended_field)
    }

def generate_intent_fix(user_request, intended_field):
    """Generate proposed fix for intent preservation"""
    
    if intended_field == 'from':
        return """
        INTENT PRESERVATION FIX for 'from' requests:
        1. Add user_intent parameter to LLM tool calls
        2. When intent='sender_info', LLM should ONLY return from field
        3. Enhanced prompt: "User specifically asked for sender information. Focus ONLY on 'from' field."
        4. Response format: "Gönderen: {from_value}" (not include subject)
        """
    elif intended_field == 'subject':
        return """
        INTENT PRESERVATION FIX for 'subject' requests:
        1. When intent='subject_info', prioritize subject field
        2. Enhanced prompt: "User asked for subject. Lead with subject information."
        3. Response format: "Konu: {subject_value}"
        """
    elif intended_field == 'attachments':
        return """
        INTENT PRESERVATION FIX for 'attachment' requests:
        1. When intent='attachment_info', focus on attachment data
        2. Enhanced prompt: "User asked about attachments. Report attachment status first."
        3. Response format: "Ek dosya: {attachment_status}"
        """
    else:
        return "Generic intent detection needed with fallback handling"

def propose_llm_intent_solution():
    """Propose comprehensive LLM-based solution"""
    
    solution = """
    🎯 COMPREHENSIVE LLM INTENT PRESERVATION SOLUTION:
    
    1. INTENT DETECTION LAYER:
       - Add pre-processing step to detect user intent from request
       - Use LLM to classify: "sender_request", "subject_request", "attachment_request", etc.
       - Pass detected intent as parameter to response generation
    
    2. ENHANCED SYSTEM PROMPT:
       - Include intent-aware instructions in LLM system prompt
       - "When user_intent='sender_info', focus ONLY on sender information"
       - "When user_intent='subject_info', lead response with subject"
       - "When user_intent='attachment_info', prioritize attachment status"
    
    3. RESPONSE FILTERING:
       - Filter Gmail API response based on detected intent
       - Only pass relevant fields to LLM for specific intents
       - Example: sender_request → only pass 'from' field
    
    4. STRUCTURED RESPONSE FORMAT:
       - Define intent-specific response templates
       - sender_request: "Gönderen: {from}"
       - subject_request: "Konu: {subject}" 
       - attachment_request: "Ek dosya: {attachment_status}"
    
    5. IMPLEMENTATION STEPS:
       a) Add intent_detector() function to LLM tool
       b) Modify enhanced_system_prompt() to include intent awareness
       c) Add response_filter() function to gmail_helper_tool
       d) Update tool coordination to pass intent parameter
       e) Test with various user request patterns
    
    6. FALLBACK HANDLING:
       - When intent unclear, ask clarifying question
       - "Bu email hakkında ne öğrenmek istiyorsunuz? (gönderen/konu/ek dosya)"
    """
    
    print(solution)
    
    # Generate implementation code snippet
    print("\n📝 IMPLEMENTATION CODE SNIPPET:")
    
    implementation_code = '''
    def detect_user_intent(user_message: str) -> str:
        """Detect user intent from request"""
        message_lower = user_message.lower()
        
        if any(word in message_lower for word in ['gönderen', 'sender', 'kimden', 'from']):
            return 'sender_request'
        elif any(word in message_lower for word in ['konu', 'subject', 'başlık']):
            return 'subject_request'
        elif any(word in message_lower for word in ['ek', 'attachment', 'dosya']):
            return 'attachment_request'
        else:
            return 'general_request'
    
    def filter_gmail_response_by_intent(gmail_data: dict, intent: str) -> dict:
        """Filter Gmail response based on user intent"""
        if intent == 'sender_request':
            return {'from': gmail_data.get('from'), 'intent': intent}
        elif intent == 'subject_request':
            return {'subject': gmail_data.get('subject'), 'intent': intent}
        elif intent == 'attachment_request':
            return {
                'has_attachments': gmail_data.get('has_attachments'),
                'attachments': gmail_data.get('attachments', []),
                'intent': intent
            }
        else:
            return gmail_data  # Return all data for general requests
    
    def generate_intent_aware_response(filtered_data: dict, intent: str) -> str:
        """Generate response based on intent and filtered data"""
        if intent == 'sender_request':
            from_value = filtered_data.get('from', 'Bilinmiyor')
            return f"📧 Gönderen: {from_value}"
        elif intent == 'subject_request':
            subject = filtered_data.get('subject', 'Konu belirtilmemiş')
            return f"📝 Konu: {subject}"
        elif intent == 'attachment_request':
            has_attachments = filtered_data.get('has_attachments', False)
            if has_attachments:
                attachments = filtered_data.get('attachments', [])
                files = [att.get('filename', 'Unknown') for att in attachments]
                return f"📎 Ek dosya var: {', '.join(files)}"
            else:
                return "📎 Ek dosya yok"
        else:
            return "📧 Genel email bilgisi sağlandı"
    '''
    
    print(implementation_code)

if __name__ == "__main__":
    analyze_user_intent_issue()