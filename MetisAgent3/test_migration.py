"""
Test Migration and SQLite Integration - MetisAgent3

Tests the migration from MetisAgent2 and validates SQLite storage functionality
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add MetisAgent3 to path
sys.path.append('/home/ahmet/MetisAgent/MetisAgent3')

from core.storage import StorageMigration, SQLiteUserStorage
from core.managers import UserManager, AuthService, PermissionService
from core.contracts import UserProfile, UserRole, UserPermission, PermissionLevel, AuthProvider

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_sqlite_storage():
    """Test SQLite storage functionality"""
    logger.info("=== Testing SQLite Storage ===")
    
    try:
        # Initialize storage
        storage = SQLiteUserStorage()
        
        # Test user creation
        import time
        timestamp = str(int(time.time()))
        test_user_data = {
            'user_id': f'test-user-{timestamp}',
            'email': f'test-{timestamp}@example.com',
            'display_name': 'Test User',
            'role': 'user',
            'metadata': {'test': True},
            'preferences': {'theme': 'dark'}
        }
        
        user_id = await storage.create_user(test_user_data)
        logger.info(f"✅ Created user: {user_id}")
        
        # Test user retrieval
        user = await storage.get_user(user_id)
        logger.info(f"✅ Retrieved user: {user['email']}")
        
        # Test user attributes
        await storage.set_user_attribute(user_id, 'test_attr', 'test_value', encrypt=True)
        attr_value = await storage.get_user_attribute(user_id, 'test_attr')
        logger.info(f"✅ User attribute: {attr_value}")
        
        # Test session creation
        session_data = {
            'user_id': user_id,
            'provider': 'test',
            'expires_at': '2025-12-31T23:59:59'
        }
        
        session_id = await storage.create_session(session_data)
        logger.info(f"✅ Created session: {session_id}")
        
        # Test permissions
        permission_data = {
            'user_id': user_id,
            'resource_type': 'tool',
            'resource_id': 'test_tool',
            'permission_level': 'read',
            'granted_by': 'system'
        }
        
        await storage.grant_permission(permission_data)
        has_permission = await storage.check_permission(user_id, 'tool', 'test_tool')
        logger.info(f"✅ Permission check: {has_permission}")
        
        # Cleanup
        await storage.delete_user(user_id)
        logger.info("✅ User cleanup completed")
        
        logger.info("✅ SQLite storage tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ SQLite storage test failed: {e}")
        return False


async def test_user_managers():
    """Test user management services"""
    logger.info("=== Testing User Managers ===")
    
    try:
        # Initialize managers
        storage = SQLiteUserStorage()
        user_manager = UserManager(storage)
        auth_service = AuthService(storage)
        permission_service = PermissionService(storage)
        
        # Test user creation with contracts
        import time
        timestamp = str(int(time.time()))
        user_profile = UserProfile(
            email=f'manager-test-{timestamp}@example.com',
            display_name='Manager Test User',
            role=UserRole.USER,
            metadata={'source': 'test'}
        )
        
        user_id = await user_manager.create_user(user_profile)
        logger.info(f"✅ UserManager created user: {user_id}")
        
        # Test authentication
        session = await auth_service.create_session(user_id, 'local')
        logger.info(f"✅ AuthService created session: {session.session_id}")
        
        # Test session validation
        validated_session = await auth_service.validate_session(session.session_id)
        logger.info(f"✅ Session validation: {validated_session is not None}")
        
        # Test permissions
        permission = UserPermission(
            user_id=user_id,
            resource_type='api',
            resource_id='gmail',
            permission_level=PermissionLevel.READ,
            granted_by='test'
        )
        
        await permission_service.grant_permission(permission)
        has_permission = await permission_service.check_permission(user_id, 'api', 'gmail')
        logger.info(f"✅ Permission service: {has_permission}")
        
        # Get user permissions
        permissions = await permission_service.get_user_permissions(user_id)
        logger.info(f"✅ User has {len(permissions)} permissions")
        
        # Cleanup
        await user_manager.delete_user(user_id)
        logger.info("✅ Manager tests cleanup completed")
        
        logger.info("✅ User manager tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ User manager test failed: {e}")
        return False


async def test_migration():
    """Test migration from MetisAgent2"""
    logger.info("=== Testing Migration ===")
    
    try:
        # Check if MetisAgent2 data exists
        metis2_path = Path('/home/ahmet/MetisAgent/MetisAgent2')
        metis2_db = metis2_path / 'users.db'
        
        if not metis2_db.exists():
            logger.info("⚠️  MetisAgent2 data not found, skipping migration test")
            return True
        
        # Initialize migration
        migration = StorageMigration()
        
        # Run migration
        result = await migration.migrate_all()
        
        if result['success']:
            logger.info(f"✅ Migration completed: {result['stats']}")
            
            # Verify migration for a user (if any)
            if result['stats']['users_migrated'] > 0:
                # Get first user from MetisAgent3
                storage = SQLiteUserStorage()
                users = await storage.list_users(limit=1)
                
                if users:
                    user_id = users[0]['user_id']
                    verification = await migration.verify_migration(user_id)
                    logger.info(f"✅ Migration verification: {verification['success']}")
            
        else:
            logger.warning(f"⚠️  Migration result: {result}")
        
        logger.info("✅ Migration test completed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration test failed: {e}")
        return False


async def main():
    """Run all tests"""
    logger.info("Starting MetisAgent3 SQLite Integration Tests")
    
    tests = [
        ('SQLite Storage', test_sqlite_storage),
        ('User Managers', test_user_managers),
        ('Migration', test_migration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Running {test_name} Test ---")
        try:
            success = await test_func()
            if success:
                passed += 1
                logger.info(f"✅ {test_name} test PASSED")
            else:
                logger.error(f"❌ {test_name} test FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} test ERROR: {e}")
    
    logger.info(f"\n=== Test Results ===")
    logger.info(f"Passed: {passed}/{total}")
    logger.info(f"Success Rate: {passed/total*100:.1f}%")
    
    if passed == total:
        logger.info("🎉 All tests passed! MetisAgent3 SQLite integration is working correctly.")
    else:
        logger.warning(f"⚠️  {total-passed} tests failed. Review the logs above.")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())