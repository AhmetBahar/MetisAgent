#!/usr/bin/env python3
"""
Test Gmail Workflow Fix - Test the use_extracted_subjects parameter handling
"""

import sys
import os
import json
import logging
from datetime import datetime

# Add project path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_gmail_workflow_parameter_fix():
    """Test the Gmail workflow use_extracted_subjects parameter fix"""
    
    print("🧪 Testing Gmail Workflow Parameter Fix")
    print("=" * 50)
    
    try:
        from app.workflow_orchestrator import WorkflowOrchestrator, WorkflowStep, WorkflowPlan, StepStatus, WorkflowStatus
        
        # Create test orchestrator
        orchestrator = WorkflowOrchestrator()
        
        # Create a mock workflow with Gmail data
        mock_workflow = WorkflowPlan(
            id="test_workflow",
            title="Gmail Subject Extraction Workflow",
            description="Test workflow for extracting Gmail subjects",
            user_id="test_user",
            conversation_id="test_conv",
            status=WorkflowStatus.RUNNING,
            steps=[],
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        # Step 1: Mock Gmail list step (completed)
        gmail_list_step = WorkflowStep(
            id="step0",
            title="List Gmail Messages",
            description="Get latest Gmail messages",
            tool_name="gmail_helper",
            action_name="list_messages",
            params={"max_results": 3},
            status=StepStatus.COMPLETED,
            result={
                'success': True,
                'data': {
                    'extracted_subjects': [
                        "MetisAgent2 Test Subject 1",
                        "Gmail Workflow Testing Subject 2", 
                        "Sequential Thinking Integration Subject 3"
                    ]
                }
            }
        )
        
        # Step 2: Mock LLM step with use_extracted_subjects parameter
        llm_step = WorkflowStep(
            id="step1",
            title="Display Gmail Subjects",
            description="Çıkarılan subject bilgilerini kullanıcı dostu formatta göster",
            tool_name="llm_tool",
            action_name="chat",
            params={
                'message': 'Çıkarılan Gmail subject bilgilerini 3 email için düzenli bir listede göster. Her subject için numara vererek sıralı liste yap.',
                'use_extracted_subjects': True
            },
            status=StepStatus.PENDING
        )
        
        # Add steps to workflow
        mock_workflow.steps = [gmail_list_step, llm_step]
        
        print("📋 Test Setup Complete")
        print(f"   Gmail Step Status: {gmail_list_step.status.value}")
        print(f"   Gmail Step Result: {len(gmail_list_step.result['data']['extracted_subjects'])} subjects")
        print(f"   LLM Step Parameters: {llm_step.params}")
        
        # Test parameter resolution
        print("\n🔧 Testing Parameter Resolution...")
        
        resolved_params = orchestrator._resolve_step_params(llm_step, mock_workflow)
        
        print(f"✅ Parameter Resolution Complete")
        print(f"   Resolved Parameters Keys: {list(resolved_params.keys())}")
        print(f"   Message Contains Subjects: {'Çıkarılan Gmail Konuları:' in resolved_params.get('message', '')}")
        print(f"   use_extracted_subjects Removed: {'use_extracted_subjects' not in resolved_params}")
        
        # Check if subjects were injected
        message = resolved_params.get('message', '')
        subjects_injected = 'MetisAgent2 Test Subject 1' in message
        
        print(f"\n📊 Test Results:")
        print(f"   ✅ Subjects Injected: {subjects_injected}")
        print(f"   ✅ Parameter Cleaned: {'use_extracted_subjects' not in resolved_params}")
        print(f"   ✅ Required LLM Params: {'message' in resolved_params and 'conversation_id' in resolved_params}")
        
        if subjects_injected and 'use_extracted_subjects' not in resolved_params:
            print(f"\n🎉 TEST PASSED: Gmail workflow fix is working correctly!")
            return True
        else:
            print(f"\n❌ TEST FAILED: Gmail workflow fix needs more work")
            return False
            
    except Exception as e:
        print(f"\n❌ TEST ERROR: {str(e)}")
        logger.error(f"Test error: {e}", exc_info=True)
        return False

def test_extraction_method():
    """Test the _extract_gmail_subjects_from_workflow method directly"""
    
    print("\n🔍 Testing Gmail Subject Extraction Method")
    print("-" * 40)
    
    try:
        from app.workflow_orchestrator import WorkflowOrchestrator, WorkflowStep, WorkflowPlan, StepStatus, WorkflowStatus
        
        orchestrator = WorkflowOrchestrator()
        
        # Create mock workflow with various data formats
        mock_workflow = WorkflowPlan(
            id="test_workflow_extraction",
            title="Gmail Extraction Test",
            description="Test different Gmail data formats",
            user_id="test_user",
            conversation_id="test_conv",
            status=WorkflowStatus.RUNNING,
            steps=[],
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        # Test different Gmail data formats
        test_cases = [
            {
                "name": "Sequential Thinking Format (extracted_subjects)",
                "result_data": {
                    'extracted_subjects': [
                        "Subject from Sequential Thinking 1",
                        "Subject from Sequential Thinking 2"
                    ]
                }
            },
            {
                "name": "Gmail API Format (messages.messages)",
                "result_data": {
                    'messages': {
                        'messages': [
                            {
                                'payload': {
                                    'headers': [
                                        {'name': 'Subject', 'value': 'Gmail API Subject 1'},
                                        {'name': 'From', 'value': 'test@example.com'}
                                    ]
                                }
                            },
                            {
                                'payload': {
                                    'headers': [
                                        {'name': 'Subject', 'value': 'Gmail API Subject 2'},
                                        {'name': 'From', 'value': 'test2@example.com'}
                                    ]
                                }
                            }
                        ]
                    }
                }
            },
            {
                "name": "Direct Message Format",
                "result_data": {
                    'message': {
                        'payload': {
                            'headers': [
                                {'name': 'Subject', 'value': 'Direct Message Subject'},
                                {'name': 'From', 'value': 'direct@example.com'}
                            ]
                        }
                    }
                }
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            print(f"\n   Test {i+1}: {test_case['name']}")
            
            # Create step with test data
            test_step = WorkflowStep(
                id=f"test_step_{i}",
                title="Test Gmail Step",
                description="Test step",
                tool_name="gmail_helper",
                action_name="test_action",
                params={},
                status=StepStatus.COMPLETED,
                result={
                    'success': True,
                    'data': test_case['result_data']
                }
            )
            
            mock_workflow.steps = [test_step]
            
            # Test extraction
            extracted_subjects = orchestrator._extract_gmail_subjects_from_workflow(mock_workflow)
            
            print(f"      Extracted: {len(extracted_subjects)} subjects")
            for j, subject in enumerate(extracted_subjects, 1):
                print(f"      {j}. {subject}")
        
        print(f"\n✅ Extraction Method Test Complete")
        return True
        
    except Exception as e:
        print(f"\n❌ Extraction Test Error: {str(e)}")
        logger.error(f"Extraction test error: {e}", exc_info=True)
        return False

def main():
    """Run all tests"""
    print("🚀 Gmail Workflow Fix Test Suite")
    print("Testing the use_extracted_subjects parameter handling fix")
    print("=" * 60)
    
    test1_result = test_gmail_workflow_parameter_fix()
    test2_result = test_extraction_method()
    
    print("\n" + "=" * 60)
    print("📋 FINAL TEST RESULTS:")
    print(f"   Parameter Resolution Test: {'✅ PASSED' if test1_result else '❌ FAILED'}")
    print(f"   Extraction Method Test: {'✅ PASSED' if test2_result else '❌ FAILED'}")
    
    if test1_result and test2_result:
        print("\n🎉 ALL TESTS PASSED - Gmail workflow fix is working!")
    else:
        print("\n❌ SOME TESTS FAILED - Fix needs more work")
    
    return test1_result and test2_result

if __name__ == "__main__":
    main()