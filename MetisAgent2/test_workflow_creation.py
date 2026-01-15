#!/usr/bin/env python3
"""
Test Workflow Creation - Debug workflow creation issue
"""

import sys
import os
sys.path.append('.')

from app.workflow_orchestrator import orchestrator

def test_workflow_creation():
    """Test workflow creation and storage"""
    
    print("🧪 Testing workflow creation...")
    
    # Test workflow creation
    user_request = "sosyal medya tool kullan"
    user_id = "test_user"
    conversation_id = "test_conversation"
    
    print(f"📤 Creating workflow for: '{user_request}'")
    
    try:
        # Create workflow
        workflow = orchestrator.create_workflow_from_user_input(
            user_request, user_id, conversation_id
        )
        
        print(f"✅ Workflow created: {workflow.id}")
        print(f"📋 Workflow status: {workflow.status.value}")
        print(f"📋 Number of steps: {len(workflow.steps)}")
        
        # Check if workflow is in active workflows
        if workflow.id in orchestrator.active_workflows:
            print(f"✅ Workflow found in active_workflows")
        else:
            print(f"❌ Workflow NOT found in active_workflows")
            print(f"📋 Active workflows: {list(orchestrator.active_workflows.keys())}")
        
        # Try to execute the workflow
        print(f"\n🔄 Attempting to execute workflow...")
        result = orchestrator.execute_workflow(workflow.id)
        
        print(f"📋 Execution result: {result}")
        
    except Exception as e:
        print(f"💥 Error during workflow creation/execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_workflow_creation()