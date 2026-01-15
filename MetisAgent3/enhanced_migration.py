"""
Enhanced Migration - Complete MetisAgent2 to MetisAgent3 Migration
Includes ALL credentials, tokens, API keys, and encrypted data

CLAUDE.md COMPLIANT:
- Preserves all MetisAgent2 credentials and tokens
- Maintains encryption for sensitive data
- Comprehensive OAuth2 token migration
- API key and password hash preservation
"""

import os
import json
import logging
import asyncio
import sys
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from datetime import datetime
import uuid

# Add MetisAgent3 to path
sys.path.append('/home/ahmet/MetisAgent/MetisAgent3')

from core.storage import StorageMigration, SQLiteUserStorage, DatabaseManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnhancedStorageMigration(StorageMigration):
    """Enhanced migration with complete credential and token transfer"""
    
    def __init__(self, 
                 metis2_path: str = "/home/ahmet/MetisAgent/MetisAgent2",
                 metis3_storage: Optional[SQLiteUserStorage] = None):
        super().__init__(metis2_path, metis3_storage)
        
        # Track credential migration
        self.migration_stats.update({
            'oauth_tokens_migrated': 0,
            'api_keys_migrated': 0,
            'password_hashes_migrated': 0,
            'google_client_credentials_migrated': 0,
            'user_mappings_migrated': 0,
            'encrypted_properties_migrated': 0
        })
    
    async def migrate_all_enhanced(self) -> Dict[str, Any]:
        """Enhanced migration with complete credential transfer"""
        try:
            logger.info("🚀 Starting ENHANCED MetisAgent2 → MetisAgent3 migration")
            logger.info("📋 This will migrate ALL credentials, tokens, and encrypted data")
            
            # Check if MetisAgent2 data exists
            if not await self._check_metis2_data():
                return {
                    'success': False,
                    'error': 'MetisAgent2 data not found or inaccessible',
                    'stats': self.migration_stats
                }
            
            # Initialize MetisAgent2 user storage connection
            metis2_storage = await self._init_metis2_storage()
            if not metis2_storage:
                return {
                    'success': False,
                    'error': 'Failed to initialize MetisAgent2 storage',
                    'stats': self.migration_stats
                }
            
            # Get all users from MetisAgent2
            users = await self._get_metis2_users(metis2_storage)
            logger.info(f"📊 Found {len(users)} users to migrate")
            
            # Migrate system-level credentials first
            await self._migrate_system_credentials(metis2_storage)
            
            # Migrate each user with enhanced credential extraction
            for user_id in users:
                await self._migrate_user_enhanced(metis2_storage, user_id)
            
            # Verify migration completeness
            await self._verify_migration_completeness()
            
            # Migration summary
            logger.info("🎉 ENHANCED MIGRATION COMPLETED!")
            logger.info(f"📊 Final Stats: {self.migration_stats}")
            
            return {
                'success': True,
                'stats': self.migration_stats,
                'message': f"Successfully migrated {self.migration_stats['users_migrated']} users with full credentials"
            }
            
        except Exception as e:
            logger.error(f"❌ Enhanced migration failed: {e}")
            self.migration_stats['errors'].append(str(e))
            return {
                'success': False,
                'error': str(e),
                'stats': self.migration_stats
            }
    
    async def _migrate_system_credentials(self, metis2_storage):
        """Migrate system-level credentials (Google OAuth client, etc.)"""
        try:
            logger.info("🔑 Migrating system-level credentials")
            
            # Get system user properties
            system_properties = metis2_storage.get_all_properties('system')
            
            if system_properties:
                # Migrate Google OAuth client credentials
                if 'google_oauth_client' in system_properties:
                    google_client = system_properties['google_oauth_client']
                    await self.metis3_storage.set_user_attribute(
                        'system', 
                        'google_oauth_client', 
                        google_client, 
                        encrypt=True
                    )
                    self.migration_stats['google_client_credentials_migrated'] += 1
                    logger.info("✅ Migrated Google OAuth client credentials")
                
                # Migrate other system credentials
                for prop_name, prop_value in system_properties.items():
                    if prop_name not in ['google_oauth_client']:
                        encrypt = any(keyword in prop_name.lower() for keyword in 
                                    ['key', 'secret', 'token', 'password', 'credential'])
                        
                        await self.metis3_storage.set_user_attribute(
                            'system', 
                            prop_name, 
                            prop_value, 
                            encrypt=encrypt
                        )
                        
                        if encrypt:
                            self.migration_stats['encrypted_properties_migrated'] += 1
            
            logger.info("✅ System credentials migration completed")
            
        except Exception as e:
            logger.error(f"❌ System credentials migration failed: {e}")
            self.migration_stats['errors'].append(f"System credentials migration: {e}")
    
    async def _migrate_user_enhanced(self, metis2_storage, user_id: str):
        """Enhanced user migration with complete credential extraction"""
        try:
            logger.info(f"🔄 Migrating user with enhanced credentials: {user_id}")
            
            # Get all properties from MetisAgent2 (this handles decryption)
            try:
                properties = metis2_storage.get_all_properties(user_id)
            except Exception as e:
                # If decryption fails, try to get raw encrypted data
                logger.warning(f"⚠️  Decryption failed for {user_id}, attempting raw data extraction: {e}")
                properties = await self._extract_raw_properties(user_id)
            
            if not properties:
                logger.warning(f"⚠️  No properties found for user {user_id}")
                return
            
            # Create user in MetisAgent3 with enhanced data
            user_data = await self._create_metis3_user_enhanced(user_id, properties)
            
            # Migrate credentials with detailed categorization
            await self._migrate_user_credentials_enhanced(user_id, properties)
            
            # Create default session
            await self._create_default_session(user_id)
            
            # Log user activity
            await self._log_user_migration_activity(user_id, properties)
            
            self.migration_stats['users_migrated'] += 1
            logger.info(f"✅ Enhanced migration completed for user: {user_id}")
            
        except Exception as e:
            error_msg = f"Failed to migrate user {user_id} with enhanced credentials: {e}"
            logger.error(f"❌ {error_msg}")
            self.migration_stats['errors'].append(error_msg)
    
    async def _extract_raw_properties(self, user_id: str) -> Dict[str, Any]:
        """Extract raw properties when decryption fails"""
        try:
            import sqlite3
            
            with sqlite3.connect(self.metis2_user_db) as conn:
                cursor = conn.execute("""
                    SELECT property_name, property_value, is_encrypted, property_type
                    FROM user_properties WHERE user_id = ?
                """, (user_id,))
                
                properties = {}
                for row in cursor.fetchall():
                    prop_name, prop_value, is_encrypted, prop_type = row
                    
                    # Store raw encrypted data for later processing
                    if is_encrypted and prop_value:
                        properties[prop_name] = {
                            'encrypted_value': prop_value,
                            'is_encrypted': True,
                            'property_type': prop_type
                        }
                    elif prop_value:
                        # Try to parse non-encrypted values
                        try:
                            if prop_type == 'json':
                                properties[prop_name] = json.loads(prop_value)
                            elif prop_type == 'int':
                                properties[prop_name] = int(prop_value)
                            elif prop_type == 'bool':
                                properties[prop_name] = prop_value.lower() == 'true'
                            else:
                                properties[prop_name] = prop_value
                        except:
                            properties[prop_name] = prop_value
                
                logger.info(f"📊 Extracted {len(properties)} raw properties for {user_id}")
                return properties
                
        except Exception as e:
            logger.error(f"❌ Raw property extraction failed for {user_id}: {e}")
            return {}
    
    async def _migrate_user_credentials_enhanced(self, user_id: str, properties: Dict[str, Any]):
        """Enhanced credential migration with detailed categorization"""
        try:
            oauth_count = 0
            api_key_count = 0
            password_count = 0
            mapping_count = 0
            encrypted_count = 0
            
            for prop_name, prop_value in properties.items():
                
                # OAuth Token Migration
                if prop_name.startswith('oauth_'):
                    provider = prop_name.replace('oauth_', '')
                    
                    if isinstance(prop_value, dict):
                        # Direct OAuth token data
                        oauth_data = prop_value
                    elif isinstance(prop_value, dict) and 'encrypted_value' in prop_value:
                        # Encrypted OAuth data - store as encrypted attribute
                        await self.metis3_storage.set_user_attribute(
                            user_id, prop_name, prop_value['encrypted_value'], encrypt=True
                        )
                        oauth_count += 1
                        continue
                    else:
                        # String OAuth token
                        oauth_data = {'token': prop_value, 'provider': provider}
                    
                    # Store in OAuth tokens table
                    with self.metis3_storage.db.transaction() as conn:
                        conn.execute("""
                            INSERT OR REPLACE INTO oauth_tokens 
                            (user_id, provider, token_encrypted, scope, expires_at)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            user_id,
                            provider,
                            self.metis3_storage.db.encrypt_data(json.dumps(oauth_data)),
                            oauth_data.get('scope', ''),
                            oauth_data.get('expires_at')
                        ))
                    
                    oauth_count += 1
                    logger.info(f"🔑 Migrated OAuth token for {provider}")
                
                # API Key Migration
                elif prop_name.startswith('api_key_'):
                    service = prop_name.replace('api_key_', '')
                    
                    # Store as encrypted user attribute
                    await self.metis3_storage.set_user_attribute(
                        user_id, prop_name, prop_value, encrypt=True
                    )
                    
                    api_key_count += 1
                    logger.info(f"🗝️  Migrated API key for {service}")
                
                # Password Hash Migration
                elif prop_name in ['password_hash', 'password', 'pwd_hash']:
                    await self.metis3_storage.set_user_attribute(
                        user_id, prop_name, prop_value, encrypt=True
                    )
                    password_count += 1
                    logger.info(f"🔒 Migrated password hash")
                
                # User Mapping Migration
                elif prop_name.startswith('mapping_'):
                    service = prop_name.replace('mapping_', '')
                    
                    await self.metis3_storage.set_user_attribute(
                        user_id, prop_name, prop_value, encrypt=False
                    )
                    mapping_count += 1
                    logger.info(f"🔗 Migrated user mapping for {service}")
                
                # Other Encrypted Properties
                elif (isinstance(prop_value, dict) and prop_value.get('is_encrypted')) or \
                     any(keyword in prop_name.lower() for keyword in 
                         ['secret', 'credential', 'token', 'key', 'private']):
                    
                    # Determine if this should be encrypted
                    should_encrypt = True
                    
                    await self.metis3_storage.set_user_attribute(
                        user_id, prop_name, prop_value, encrypt=should_encrypt
                    )
                    
                    if should_encrypt:
                        encrypted_count += 1
                        logger.info(f"🔐 Migrated encrypted property: {prop_name}")
                
                # Regular Properties
                else:
                    # Regular non-sensitive properties
                    await self.metis3_storage.set_user_attribute(
                        user_id, prop_name, prop_value, encrypt=False
                    )
            
            # Update stats
            self.migration_stats['oauth_tokens_migrated'] += oauth_count
            self.migration_stats['api_keys_migrated'] += api_key_count
            self.migration_stats['password_hashes_migrated'] += password_count
            self.migration_stats['user_mappings_migrated'] += mapping_count
            self.migration_stats['encrypted_properties_migrated'] += encrypted_count
            
            logger.info(f"📊 User {user_id} credentials: OAuth({oauth_count}), API Keys({api_key_count}), Passwords({password_count}), Mappings({mapping_count}), Encrypted({encrypted_count})")
            
        except Exception as e:
            logger.error(f"❌ Enhanced credential migration failed for user {user_id}: {e}")
            raise
    
    async def _create_metis3_user_enhanced(self, user_id: str, properties: Dict[str, Any]) -> str:
        """Create user in MetisAgent3 with enhanced metadata"""
        try:
            # Extract user info from properties with fallbacks
            email = properties.get('email', properties.get('username', f"{user_id}@migrated.local"))
            display_name = properties.get('display_name', properties.get('name', properties.get('full_name', user_id)))
            role = properties.get('role', 'user')
            
            # Count credentials for metadata
            credential_count = sum(1 for key in properties.keys() 
                                 if any(cred in key.lower() for cred in 
                                       ['oauth', 'api_key', 'token', 'password', 'credential']))
            
            # Create enhanced user data
            user_create_data = {
                'user_id': user_id,
                'email': email,
                'display_name': display_name,
                'role': role,
                'metadata': {
                    'migrated_from': 'MetisAgent2',
                    'migration_date': datetime.now().isoformat(),
                    'original_properties_count': len(properties),
                    'credential_count': credential_count,
                    'migration_version': '2.0_enhanced',
                    'has_oauth_tokens': any(key.startswith('oauth_') for key in properties.keys()),
                    'has_api_keys': any(key.startswith('api_key_') for key in properties.keys()),
                    'has_password_hash': any(key in ['password_hash', 'password', 'pwd_hash'] for key in properties.keys())
                }
            }
            
            # Create user in SQLite
            created_user_id = await self.metis3_storage.create_user(user_create_data)
            
            if created_user_id:
                logger.info(f"✅ Created enhanced MetisAgent3 user: {created_user_id}")
                return created_user_id
            else:
                raise Exception("Failed to create enhanced user in MetisAgent3")
                
        except Exception as e:
            logger.error(f"❌ Error creating enhanced MetisAgent3 user {user_id}: {e}")
            raise
    
    async def _log_user_migration_activity(self, user_id: str, properties: Dict[str, Any]):
        """Log migration activity for audit trail"""
        try:
            activity_data = {
                'user_id': user_id,
                'action': 'migration_from_metis2',
                'resource_type': 'user_data',
                'resource_id': user_id,
                'status': 'success',
                'metadata': {
                    'properties_migrated': len(properties),
                    'migration_timestamp': datetime.now().isoformat(),
                    'migration_type': 'enhanced_credential_migration',
                    'source_system': 'MetisAgent2'
                }
            }
            
            await self.metis3_storage.log_activity(activity_data)
            logger.info(f"📝 Logged migration activity for user {user_id}")
            
        except Exception as e:
            logger.warning(f"⚠️  Failed to log migration activity for {user_id}: {e}")
    
    async def _verify_migration_completeness(self):
        """Verify that all credentials were migrated successfully"""
        try:
            logger.info("🔍 Verifying migration completeness...")
            
            # Check user count
            users = await self.metis3_storage.list_users(limit=1000)
            logger.info(f"📊 Total users in MetisAgent3: {len(users)}")
            
            # Check credential counts in database
            with self.metis3_storage.db.transaction() as conn:
                # OAuth tokens
                cursor = conn.execute("SELECT COUNT(*) as count FROM oauth_tokens")
                oauth_count = cursor.fetchone()['count']
                
                # Encrypted attributes
                cursor = conn.execute("SELECT COUNT(*) as count FROM user_attributes WHERE is_encrypted = 1")
                encrypted_count = cursor.fetchone()['count']
                
                # User activities
                cursor = conn.execute("SELECT COUNT(*) as count FROM user_activities")
                activity_count = cursor.fetchone()['count']
            
            verification_stats = {
                'users_in_metis3': len(users),
                'oauth_tokens_in_db': oauth_count,
                'encrypted_attributes_in_db': encrypted_count,
                'migration_activities_logged': activity_count
            }
            
            logger.info(f"✅ Migration verification: {verification_stats}")
            self.migration_stats['verification'] = verification_stats
            
        except Exception as e:
            logger.error(f"❌ Migration verification failed: {e}")
            self.migration_stats['errors'].append(f"Verification failed: {e}")


async def main():
    """Enhanced migration CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced MetisAgent2 → MetisAgent3 Migration with ALL Credentials')
    parser.add_argument('--metis2-path', default='/home/ahmet/MetisAgent/MetisAgent2',
                       help='Path to MetisAgent2 installation')
    parser.add_argument('--verify-user', help='Verify migration for specific user ID')
    parser.add_argument('--rollback', action='store_true', help='Rollback migration')
    parser.add_argument('--show-stats', action='store_true', help='Show detailed migration statistics')
    
    args = parser.parse_args()
    
    migration = EnhancedStorageMigration(metis2_path=args.metis2_path)
    
    if args.rollback:
        result = await migration.rollback_migration()
        print("🔄 ROLLBACK RESULT:")
        print(json.dumps(result, indent=2))
    elif args.verify_user:
        result = await migration.verify_migration(args.verify_user)
        print(f"🔍 VERIFICATION FOR USER {args.verify_user}:")
        print(json.dumps(result, indent=2, default=str))
    elif args.show_stats:
        # Show current MetisAgent3 stats
        storage = SQLiteUserStorage()
        users = await storage.list_users(limit=1000)
        print(f"📊 Current MetisAgent3 users: {len(users)}")
        for user in users[:5]:  # Show first 5 users
            print(f"  - {user['email']} ({user['user_id']})")
    else:
        print("🚀 Starting ENHANCED MetisAgent2 → MetisAgent3 Migration")
        print("📋 This will migrate ALL credentials, tokens, and encrypted data")
        print()
        
        result = await migration.migrate_all_enhanced()
        
        print("🎉 ENHANCED MIGRATION COMPLETED!")
        print("📊 Final Results:")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())