#!/usr/bin/env python3
"""
Create test user for MetisAgent3 system
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.managers.user_manager import UserManager
from core.contracts.user_contracts import UserProfile, UserRole
import asyncio
import uuid

async def main():
    """Create test user ahmetb@minor.com.tr with password 12345678"""
    try:
        # Initialize user manager
        user_manager = UserManager()
        
        # User data
        email = "ahmetb@minor.com.tr"
        password = "12345678"
        username = "ahmetb"
        
        print(f"Creating user: {email}")
        
        # Create UserProfile
        user_profile = UserProfile(
            user_id=str(uuid.uuid4()),
            email=email,
            display_name=username,
            role=UserRole.USER
        )
        
        # Create user
        user_id = await user_manager.create_user(user_profile)
        
        # Set password using auth service
        auth_result = await user_manager.auth_service.create_user_credentials(
            user_id=user_id,
            email=email,
            password=password
        )
        
        if user_id and auth_result:
            print(f"✅ User created successfully!")
            print(f"User ID: {user_id}")
            print(f"Email: {email}")
            print(f"Username: {username}")
        else:
            print(f"❌ Failed to create user")
            
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    asyncio.run(main())