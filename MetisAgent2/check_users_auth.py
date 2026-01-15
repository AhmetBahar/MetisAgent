#!/usr/bin/env python3
"""
Check users authentication database
"""

import os
import sys
import json

# Add the current directory to the path
sys.path.insert(0, '.')

from app.database import db_manager

def check_users_auth():
    """Check users authentication database"""
    
    print("🔍 Checking users authentication database...")
    
    try:
        # Get all users from the users collection
        all_users = db_manager.users_collection.get()
        
        print(f"\n👥 Found {len(all_users['ids'])} users in auth database:")
        
        for i, user_id in enumerate(all_users['ids']):
            metadata = all_users['metadatas'][i]
            username = metadata.get('username', 'Unknown')
            email = metadata.get('email', 'Unknown')
            status = metadata.get('status', 'Unknown')
            created_at = metadata.get('created_at', 'Unknown')[:19]
            last_login = metadata.get('last_login', 'Never')
            
            print(f"\n🔹 User ID: {user_id}")
            print(f"   Username: {username}")
            print(f"   Email: {email}")
            print(f"   Status: {status}")
            print(f"   Created: {created_at}")
            print(f"   Last Login: {last_login[:19] if last_login and last_login != 'Never' else 'Never'}")
            
            # Check permissions
            permissions = metadata.get('permissions', '[]')
            try:
                perms = json.loads(permissions)
                print(f"   Permissions: {perms}")
            except:
                print(f"   Permissions: {permissions}")
        
        print(f"\n🔍 Looking for user with ID: 2f525c55-8b7c-40f1-8ec6-a4e6ffad0aef")
        
        # Check if the specific user ID exists
        target_user_id = "2f525c55-8b7c-40f1-8ec6-a4e6ffad0aef"
        
        if target_user_id in all_users['ids']:
            index = all_users['ids'].index(target_user_id)
            metadata = all_users['metadatas'][index]
            print(f"✅ Found target user:")
            print(f"   Username: {metadata.get('username')}")
            print(f"   Email: {metadata.get('email')}")
            print(f"   Status: {metadata.get('status')}")
        else:
            print(f"❌ User with ID {target_user_id} not found in auth database")
        
        # Check sessions
        print(f"\n🔐 Checking sessions...")
        all_sessions = db_manager.sessions_collection.get()
        
        active_sessions = []
        for i, session_id in enumerate(all_sessions['ids']):
            metadata = all_sessions['metadatas'][i]
            if metadata.get('status') == 'active':
                active_sessions.append({
                    'session_id': session_id,
                    'user_id': metadata.get('user_id'),
                    'created_at': metadata.get('created_at')
                })
        
        print(f"   Active sessions: {len(active_sessions)}")
        for session in active_sessions:
            print(f"   - Session for user {session['user_id']} (created: {session['created_at'][:19]})")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_users_auth()