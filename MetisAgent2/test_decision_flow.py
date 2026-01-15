#!/usr/bin/env python3
"""
Test Decision Flow - Test social media workflow decision handling
"""

import requests
import json

# Test the complete decision flow
def test_social_media_decision():
    """Test social media workflow decision flow"""
    
    # Backend URL
    base_url = "http://localhost:5001/api"
    
    # Test message
    test_message = "sosyal medya tool kullan"
    
    print(f"🧪 Testing social media decision flow with: '{test_message}'")
    print("="*60)
    
    # Send chat request
    chat_url = f"{base_url}/chat"
    payload = {
        "message": test_message,
        "user_id": "test_user",
        "enable_tools": True
    }
    
    try:
        print("📤 Sending chat request...")
        response = requests.post(chat_url, json=payload, timeout=30)
        
        print(f"📋 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                response_data = data.get('data', {})
                
                print(f"✅ Chat request successful")
                print(f"📝 Response: {response_data.get('response', 'No response')[:200]}...")
                print(f"⚙️  Has workflow: {response_data.get('has_workflow', False)}")
                print(f"🔗 Workflow ID: {response_data.get('workflow_id', 'None')}")
                
                # Check for decision requirements
                requires_decision = response_data.get('requires_decision', False)
                decision_options = response_data.get('decision_options', [])
                decision_id = response_data.get('decision_id')
                
                print(f"🤔 Requires decision: {requires_decision}")
                print(f"🎯 Decision ID: {decision_id}")
                print(f"📋 Decision options: {decision_options}")
                
                if requires_decision and decision_options and decision_id:
                    print("\n" + "="*60)
                    print("🎯 Testing decision submission...")
                    
                    # Test decision submission
                    decision_url = f"{base_url}/decision"
                    decision_payload = {
                        "decision_id": decision_id,
                        "choice": decision_options[0]  # Choose first option
                    }
                    
                    print(f"📤 Submitting decision: {decision_options[0]}")
                    decision_response = requests.post(decision_url, json=decision_payload, timeout=30)
                    
                    print(f"📋 Decision Response Status: {decision_response.status_code}")
                    
                    if decision_response.status_code == 200:
                        decision_data = decision_response.json()
                        print(f"✅ Decision submission successful")
                        print(f"📝 Decision response: {decision_data}")
                    else:
                        print(f"❌ Decision submission failed: {decision_response.text}")
                        
                else:
                    print("⚠️  No decision detected in response")
                    
            else:
                print(f"❌ Chat request failed: {data}")
                
        else:
            print(f"❌ HTTP Error {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"💥 Request failed: {e}")

if __name__ == "__main__":
    test_social_media_decision()