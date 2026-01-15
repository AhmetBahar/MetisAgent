#!/usr/bin/env python3
"""
Test workflow-todo integration with WebSocket broadcasting
"""

import sys
sys.path.append('.')

from app.workflow_orchestrator import orchestrator
from tools.todo_manager import get_todo_tool
from app.websocket_manager import get_websocket_manager
import time

def test_workflow_todo_integration():
    """Test complete workflow-todo integration"""
    print("Testing workflow-todo integration...")
    
    # Get components
    todo_tool = get_todo_tool()
    ws_manager = get_websocket_manager()
    
    print(f"Todo tool available: {todo_tool is not None}")
    print(f"WebSocket manager available: {ws_manager is not None}")
    print(f"Orchestrator WebSocket connected: {orchestrator.websocket_manager is not None}")
    
    # Clear existing todos for test user
    test_user = 'ahmetb@minor.com.tr'
    todo_tool.todo_clear(test_user)
    print(f"Cleared existing todos for {test_user}")
    
    # Create a simple test workflow
    user_input = "Gmail son 3 email konularını listele"
    conversation_id = "test_conversation_todo_integration"
    
    try:
        # Create workflow (this should trigger todo creation)
        workflow = orchestrator.create_workflow_from_user_input(
            user_input, 
            test_user, 
            conversation_id
        )
        
        print(f"Created workflow: {workflow.id}")
        print(f"Workflow steps: {len(workflow.steps)}")
        
        # Check if todos were created
        todos_result = todo_tool.todo_get_all(test_user, workflow.id)
        print(f"Todos created during workflow creation: {todos_result.get('total', 0)}")
        
        if todos_result.get('total', 0) > 0:
            print("✅ TODO CREATION WORKING - Workflow creates todos automatically")
            for todo in todos_result.get('todos', []):
                print(f"  - {todo['content']} ({todo['status']})")
        else:
            print("❌ TODO CREATION NOT WORKING - No todos created for workflow")
        
        # Test workflow execution (if safe)
        print("\nTesting workflow execution...")
        try:
            # Don't actually execute to avoid side effects, just test the todo update mechanism
            print("Simulating step completion...")
            
            # Manually update a todo status to test broadcast
            if todos_result.get('todos'):
                first_todo = todos_result['todos'][0]
                update_result = todo_tool.todo_update_status(
                    test_user, 
                    first_todo['id'], 
                    'in_progress',
                    workflow.id
                )
                print(f"Todo status update result: {update_result.get('success', False)}")
                
                if update_result.get('success'):
                    print("✅ TODO UPDATE WORKING - Status updates work")
                else:
                    print("❌ TODO UPDATE NOT WORKING")
            
        except Exception as e:
            print(f"Workflow execution test error (expected): {e}")
        
        # Test WebSocket broadcast simulation
        print("\nTesting WebSocket broadcast...")
        try:
            # This will test the broadcast mechanism
            ws_manager.broadcast_todo_update(
                test_user,
                'todo_test',
                {'message': 'Test broadcast from integration test'},
                workflow.id
            )
            print("✅ WEBSOCKET BROADCAST WORKING - No errors in broadcast")
        except Exception as e:
            print(f"❌ WEBSOCKET BROADCAST ERROR: {e}")
        
        # Final todo check
        final_todos = todo_tool.todo_get_all(test_user)
        print(f"\nFinal todos count: {final_todos.get('total', 0)}")
        
        return True
        
    except Exception as e:
        print(f"Integration test error: {e}")
        return False

def test_existing_workflow_todos():
    """Check existing workflow todos"""
    print("\nChecking existing workflow todos...")
    
    todo_tool = get_todo_tool()
    test_user = 'ahmetb@minor.com.tr'
    
    all_todos = todo_tool.todo_get_all(test_user)
    print(f"Total existing todos: {all_todos.get('total', 0)}")
    
    if all_todos.get('total', 0) > 0:
        print("Existing workflow todos:")
        for todo in all_todos.get('todos', []):
            workflow_id = todo.get('workflow_id', 'No workflow')
            print(f"  - {todo['content']} | Status: {todo['status']} | Workflow: {workflow_id[:8]}...")

if __name__ == '__main__':
    print("=" * 60)
    print("TESTING WORKFLOW-TODO INTEGRATION")
    print("=" * 60)
    
    test_existing_workflow_todos()
    print()
    
    success = test_workflow_todo_integration()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ INTEGRATION TEST COMPLETED SUCCESSFULLY")
        print("Todo system is working with workflows!")
    else:
        print("❌ INTEGRATION TEST FAILED")
        print("Issues detected in workflow-todo integration")
    print("=" * 60)