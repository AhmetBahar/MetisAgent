#!/usr/bin/env python3
"""
Debug Gmail Workflow Test - Test Gmail workflow directly
"""

import sys
import json
import logging
sys.path.append('.')

from app.tool_coordinator import ToolCoordinator
from app.workflow_orchestrator import WorkflowOrchestrator
from app.mcp_core import registry
from tools.internal.sequential_thinking_tool import SequentialThinkingTool

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_gmail_workflow():
    """Test Gmail workflow end to end"""
    try:
        # Setup coordinator and orchestrator
        coordinator = ToolCoordinator()
        orchestrator = WorkflowOrchestrator()
        orchestrator.initialize_planner(registry)
        
        # Get Sequential Thinking tool
        seq_thinking = SequentialThinkingTool()
        
        print("🔍 Testing Gmail workflow...")
        
        # Plan workflow
        user_request = "Gmail'deki son maili kim göndermiş?"
        planning_result = seq_thinking._plan_workflow(user_request, user_id="ahmetb@minor.com.tr")
        
        print(f"📋 Planning Result: {json.dumps(planning_result.to_dict(), indent=2)}")
        
        if planning_result.success:
            workflow_data = planning_result.data
            print(f"✅ Planning successful, {len(workflow_data['steps'])} steps generated")
            
            # Create workflow
            workflow = orchestrator.create_workflow(
                user_id="ahmetb@minor.com.tr",
                title="Gmail Test Workflow",
                steps=workflow_data['steps']
            )
            
            print(f"📝 Workflow created: {workflow.id}")
            
            # Execute workflow
            print("🚀 Executing workflow...")
            execution_result = orchestrator.execute_workflow(workflow.id)
            
            print(f"📊 Execution Result: {json.dumps(execution_result.to_dict(), indent=2)}")
            
            # Check workflow status
            final_workflow = orchestrator.get_workflow(workflow.id)
            print(f"📈 Final workflow status: {final_workflow.status.value}")
            
            # Print step results
            for i, step in enumerate(final_workflow.steps):
                print(f"Step {i+1}: {step.title}")
                print(f"  Status: {step.status.value}")
                if step.result:
                    print(f"  Result keys: {list(step.result.keys())}")
                    if step.result.get('data'):
                        data = step.result['data']
                        if 'messages' in data:
                            print(f"  Gmail messages count: {len(data['messages'])}")
                            if data['messages']:
                                msg = data['messages'][0]
                                print(f"  First message from: {msg.get('from', 'N/A')}")
                print()
            
            return True
            
        else:
            print(f"❌ Planning failed: {planning_result.error}")
            return False
            
    except Exception as e:
        print(f"💥 Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_gmail_workflow()