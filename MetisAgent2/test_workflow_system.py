#!/usr/bin/env python3
"""
Workflow Orchestration System Test Script
"""

import requests
import json
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:5001"

def test_workflow_system():
    """Test the new workflow orchestration system"""
    
    print("🚀 Testing Workflow Orchestration System")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        {
            "name": "Gmail Subject Retrieval",
            "message": "Gmail inbox'daki son mailin subject bilgisini paylaş",
            "expected_workflow": True,
            "description": "Should create a 2-step workflow: list messages → get message details"
        },
        {
            "name": "Complex Multi-step Request",
            "message": "Google'da MetisAgent araştırması yap ve sonuçları özetle",
            "expected_workflow": True,
            "description": "Should create workflow for research and summarization"
        },
        {
            "name": "Simple Request (No Workflow)",
            "message": "Merhaba, nasılsın?",
            "expected_workflow": False,
            "description": "Simple greeting should not trigger workflow"
        },
        {
            "name": "Sequential Operations",
            "message": "Önce sistem durumunu kontrol et, sonra disk alanını göster",
            "expected_workflow": True,
            "description": "Should create workflow with conditional steps"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}: {test_case['name']}")
        print(f"   Message: {test_case['message']}")
        print(f"   Expected Workflow: {test_case['expected_workflow']}")
        print(f"   Description: {test_case['description']}")
        
        # Execute test
        success = run_test_case(test_case)
        
        if success:
            print("   ✅ Test PASSED")
        else:
            print("   ❌ Test FAILED")
        
        print("-" * 40)
    
    # Test workflow API endpoints
    print("\n🔍 Testing Workflow API Endpoints")
    test_workflow_endpoints()
    
    print("\n🎯 Test Summary Complete")

def run_test_case(test_case):
    """Run a single test case"""
    try:
        # Send chat message
        response = requests.post(f"{BASE_URL}/api/chat", json={
            "message": test_case["message"],
            "provider": "openai",
            "model": "gpt-4o-mini",
            "conversation_id": f"test_{int(time.time())}"
        })
        
        if response.status_code != 200:
            print(f"   ❌ HTTP Error: {response.status_code}")
            return False
        
        data = response.json()
        
        if not data.get("success"):
            print(f"   ❌ API Error: {data.get('error', 'Unknown error')}")
            return False
        
        # Check workflow creation
        has_workflow = data.get("data", {}).get("has_workflow", False)
        workflow_id = data.get("data", {}).get("workflow_id")
        
        print(f"   📊 Has Workflow: {has_workflow}")
        print(f"   🔗 Workflow ID: {workflow_id}")
        
        # Validate expectation
        if test_case["expected_workflow"] != has_workflow:
            print(f"   ❌ Expectation mismatch: expected {test_case['expected_workflow']}, got {has_workflow}")
            return False
        
        # If workflow was created, test workflow status
        if has_workflow and workflow_id:
            return test_workflow_status(workflow_id)
        
        return True
        
    except Exception as e:
        print(f"   ❌ Exception: {str(e)}")
        return False

def test_workflow_status(workflow_id):
    """Test workflow status endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/api/workflows/{workflow_id}")
        
        if response.status_code != 200:
            print(f"   ❌ Workflow Status HTTP Error: {response.status_code}")
            return False
        
        data = response.json()
        
        if not data.get("success"):
            print(f"   ❌ Workflow Status Error: {data.get('error')}")
            return False
        
        workflow = data.get("workflow", {})
        
        print(f"   📋 Workflow Title: {workflow.get('title', 'N/A')}")
        print(f"   📊 Status: {workflow.get('status', 'N/A')}")
        print(f"   🎯 Progress: {workflow.get('progress_percentage', 0)}%")
        print(f"   📝 Steps: {workflow.get('completed_steps', 0)}/{workflow.get('total_steps', 0)}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Workflow Status Exception: {str(e)}")
        return False

def test_workflow_endpoints():
    """Test workflow-related endpoints"""
    try:
        # Test workflows list endpoint
        print("\n   🔍 Testing /api/workflows")
        response = requests.get(f"{BASE_URL}/api/workflows")
        
        if response.status_code == 200:
            data = response.json()
            workflow_count = len(data.get("workflows", []))
            print(f"   ✅ Workflows endpoint: {workflow_count} workflows found")
        else:
            print(f"   ❌ Workflows endpoint error: {response.status_code}")
        
        # Test health endpoint (should include workflow info)
        print("\n   🔍 Testing /api/health")
        response = requests.get(f"{BASE_URL}/api/health")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Health endpoint: System {data.get('status', 'unknown')}")
        else:
            print(f"   ❌ Health endpoint error: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Endpoint test exception: {str(e)}")

def test_gmail_workflow_specifically():
    """Test Gmail workflow with authentication simulation"""
    print("\n📧 Testing Gmail Workflow (Simulation)")
    
    # This would require actual Google OAuth2 setup
    # For now, we'll test the workflow planning part
    
    test_message = "Gmail inbox'daki son mailin subject bilgisini paylaş"
    
    try:
        response = requests.post(f"{BASE_URL}/api/chat", json={
            "message": test_message,
            "provider": "openai",
            "model": "gpt-4o-mini",
            "conversation_id": "gmail_test"
        })
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("data", {}).get("has_workflow"):
                workflow_id = data["data"]["workflow_id"]
                print(f"   ✅ Gmail workflow created: {workflow_id}")
                
                # Get workflow details
                workflow_response = requests.get(f"{BASE_URL}/api/workflows/{workflow_id}")
                if workflow_response.status_code == 200:
                    workflow_data = workflow_response.json()
                    workflow = workflow_data.get("workflow", {})
                    
                    print(f"   📋 Workflow: {workflow.get('title')}")
                    print(f"   📝 Steps: {len(workflow.get('steps', []))}")
                    
                    for i, step in enumerate(workflow.get('steps', []), 1):
                        print(f"     {i}. {step.get('title')} ({step.get('status')})")
                
            else:
                print("   ❌ Gmail workflow not created")
        else:
            print(f"   ❌ Gmail test failed: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Gmail test exception: {str(e)}")

if __name__ == "__main__":
    print("🧪 MetisAgent2 Workflow System Test Suite")
    print("Make sure the backend is running on localhost:5001")
    
    # Check if backend is running
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is running")
            test_workflow_system()
            test_gmail_workflow_specifically()
        else:
            print("❌ Backend is not responding correctly")
    except requests.exceptions.RequestException:
        print("❌ Cannot connect to backend. Please start the server first.")
        print("   Run: python app.py")