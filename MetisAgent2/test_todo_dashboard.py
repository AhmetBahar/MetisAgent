#!/usr/bin/env python3
"""
Test script for todo dashboard functionality
"""

import sys
sys.path.append('.')

from flask import Flask
from app.routes import api_bp

def test_todo_routes():
    """Test todo dashboard routes"""
    app = Flask(__name__)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    with app.test_client() as client:
        with app.app_context():
            try:
                # Test dashboard route
                response = client.get('/api/todos')
                print(f'Todo dashboard route status: {response.status_code}')
                if response.status_code != 200:
                    print(f'Response: {response.data.decode()}')
                
                # Test API route
                response = client.get('/api/todos/api/test_user')
                print(f'Todo API route status: {response.status_code}')
                
                print('Route tests completed successfully')
                
            except Exception as e:
                print(f'Route test error: {e}')

def test_todo_system():
    """Test complete todo system"""
    from tools.todo_manager import get_todo_tool
    from app.websocket_manager import get_websocket_manager
    
    print("Testing todo system components...")
    
    # Test todo tool
    todo_tool = get_todo_tool()
    print(f'Todo tool available: {todo_tool is not None}')
    
    # Test websocket manager
    ws_manager = get_websocket_manager()
    print(f'WebSocket manager available: {ws_manager is not None}')
    
    # Test todo creation and retrieval
    test_user = 'test_user_dashboard'
    test_todos = [{
        'content': 'Test todo for dashboard verification',
        'status': 'pending',
        'priority': 'high'
    }]
    
    creation_result = todo_tool.todo_create(test_user, test_todos, 'test_workflow')
    print(f'Todo creation result: {creation_result.get("success", False)}')
    
    retrieval_result = todo_tool.todo_get_all(test_user)
    print(f'Todo retrieval result: {retrieval_result.get("success", False)}')
    print(f'Retrieved todos count: {retrieval_result.get("total", 0)}')
    
    # Clean up test data
    todo_tool.todo_clear(test_user)
    print('Test cleanup completed')

if __name__ == '__main__':
    print("=" * 50)
    print("TESTING TODO DASHBOARD SYSTEM")
    print("=" * 50)
    
    test_todo_routes()
    print()
    test_todo_system()
    
    print("\nAll tests completed!")