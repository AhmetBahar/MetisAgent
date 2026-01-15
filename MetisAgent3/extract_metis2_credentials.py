"""
MetisAgent2 Credential Extractor
Direct encryption key approach to extract ALL credentials from MetisAgent2
"""

import sqlite3
import json
import logging
import sys
import asyncio
from pathlib import Path
from cryptography.fernet import Fernet
import base64

# Add MetisAgent3 to path
sys.path.append('/home/ahmet/MetisAgent/MetisAgent3')
from core.storage import SQLiteUserStorage

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MetisAgent2CredentialExtractor:
    """Extract credentials directly from MetisAgent2 with proper decryption"""
    
    def __init__(self, metis2_path="/home/ahmet/MetisAgent/MetisAgent2"):
        self.metis2_path = Path(metis2_path)
        self.metis2_db = self.metis2_path / "users.db"
        self.metis2_key_file = self.metis2_path / "storage.key"
        
        # Load encryption key
        self._load_encryption_key()
        
        # Initialize MetisAgent3 storage
        self.metis3_storage = SQLiteUserStorage()
        
        # Stats
        self.stats = {
            'total_users': 0,
            'users_with_credentials': 0,
            'oauth_tokens_extracted': 0,
            'api_keys_extracted': 0,
            'password_hashes_extracted': 0,
            'other_encrypted_props': 0,
            'decryption_failures': 0
        }
    
    def _load_encryption_key(self):
        """Load MetisAgent2 encryption key"""
        try:
            with open(self.metis2_key_file, 'rb') as f:
                self.encryption_key = f.read()
            
            self.cipher = Fernet(self.encryption_key)
            logger.info(f"✅ Loaded MetisAgent2 encryption key from {self.metis2_key_file}")
            
        except Exception as e:
            logger.error(f"❌ Failed to load encryption key: {e}")
            raise
    
    def decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt value using MetisAgent2's encryption key"""
        try:
            # MetisAgent2 uses base64 encoding before Fernet encryption
            decoded = base64.b64decode(encrypted_value.encode('utf-8'))
            decrypted = self.cipher.decrypt(decoded)
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.warning(f"⚠️  Decryption failed: {e}")
            self.stats['decryption_failures'] += 1
            return None
    
    def extract_all_credentials(self):
        """Extract all credentials from MetisAgent2"""
        logger.info("🔍 Starting credential extraction from MetisAgent2")
        
        try:
            with sqlite3.connect(self.metis2_db) as conn:
                conn.row_factory = sqlite3.Row
                
                # Get all users
                cursor = conn.execute("SELECT DISTINCT user_id FROM user_properties")
                users = [row['user_id'] for row in cursor.fetchall()]
                self.stats['total_users'] = len(users)
                
                logger.info(f"📊 Found {len(users)} users in MetisAgent2")
                
                # Extract credentials for each user
                for user_id in users:
                    self._extract_user_credentials(conn, user_id)
                
                # Extract system credentials
                self._extract_system_credentials(conn)
                
                logger.info("🎉 Credential extraction completed!")
                logger.info(f"📊 Final Stats: {self.stats}")
                
        except Exception as e:
            logger.error(f"❌ Credential extraction failed: {e}")
            raise
    
    def _extract_user_credentials(self, conn, user_id):
        """Extract credentials for a specific user"""
        try:
            cursor = conn.execute("""
                SELECT property_name, property_value, is_encrypted, property_type
                FROM user_properties 
                WHERE user_id = ?
            """, (user_id,))
            
            user_credentials = {}
            has_credentials = False
            
            for row in cursor.fetchall():
                prop_name = row['property_name']
                prop_value = row['property_value']
                is_encrypted = row['is_encrypted']
                prop_type = row['property_type']
                
                # Decrypt if needed
                if is_encrypted and prop_value:
                    decrypted_value = self.decrypt_value(prop_value)
                    if decrypted_value is not None:
                        # Parse based on property type
                        if prop_type == 'json':
                            try:
                                parsed_value = json.loads(decrypted_value)
                            except:
                                parsed_value = decrypted_value
                        else:
                            parsed_value = decrypted_value
                        
                        user_credentials[prop_name] = parsed_value
                        has_credentials = True
                        
                        # Categorize credential type
                        if prop_name.startswith('oauth_'):
                            self.stats['oauth_tokens_extracted'] += 1
                        elif prop_name.startswith('api_key_'):
                            self.stats['api_keys_extracted'] += 1
                        elif prop_name in ['password_hash', 'password', 'pwd_hash']:
                            self.stats['password_hashes_extracted'] += 1
                        else:
                            self.stats['other_encrypted_props'] += 1
                
                elif prop_value:  # Non-encrypted properties
                    if prop_type == 'json':
                        try:
                            user_credentials[prop_name] = json.loads(prop_value)
                        except:
                            user_credentials[prop_name] = prop_value
                    else:
                        user_credentials[prop_name] = prop_value
            
            if has_credentials or len(user_credentials) > 0:
                self.stats['users_with_credentials'] += 1
                logger.info(f"🔑 User {user_id}: {len(user_credentials)} properties extracted")
                
                # Store in MetisAgent3
                asyncio.run(self._store_user_credentials(user_id, user_credentials))
            else:
                logger.info(f"⚠️  User {user_id}: No credentials found")
                
        except Exception as e:
            logger.error(f"❌ Failed to extract credentials for user {user_id}: {e}")
    
    def _extract_system_credentials(self, conn):
        """Extract system-level credentials"""
        try:
            cursor = conn.execute("""
                SELECT property_name, property_value, is_encrypted, property_type
                FROM user_properties 
                WHERE user_id = 'system'
            """, )
            
            system_credentials = {}
            
            for row in cursor.fetchall():
                prop_name = row['property_name']
                prop_value = row['property_value']
                is_encrypted = row['is_encrypted']
                prop_type = row['property_type']
                
                if is_encrypted and prop_value:
                    decrypted_value = self.decrypt_value(prop_value)
                    if decrypted_value is not None:
                        if prop_type == 'json':
                            try:
                                system_credentials[prop_name] = json.loads(decrypted_value)
                            except:
                                system_credentials[prop_name] = decrypted_value
                        else:
                            system_credentials[prop_name] = decrypted_value
                
                elif prop_value:
                    if prop_type == 'json':
                        try:
                            system_credentials[prop_name] = json.loads(prop_value)
                        except:
                            system_credentials[prop_name] = prop_value
                    else:
                        system_credentials[prop_name] = prop_value
            
            if system_credentials:
                logger.info(f"🔑 System credentials: {len(system_credentials)} properties extracted")
                asyncio.run(self._store_system_credentials(system_credentials))
                
        except Exception as e:
            logger.error(f"❌ Failed to extract system credentials: {e}")
    
    async def _store_user_credentials(self, user_id, credentials):
        """Store user credentials in MetisAgent3"""
        try:
            # Ensure user exists in MetisAgent3
            user = await self.metis3_storage.get_user(user_id)
            if not user:
                # Create user
                email = credentials.get('email', f"{user_id}@migrated.local")
                display_name = credentials.get('display_name', credentials.get('name', user_id))
                
                user_data = {
                    'user_id': user_id,
                    'email': email,
                    'display_name': display_name,
                    'role': 'user',
                    'metadata': {
                        'migrated_from': 'MetisAgent2_direct_extraction',
                        'credential_count': len(credentials)
                    }
                }
                await self.metis3_storage.create_user(user_data)
                logger.info(f"✅ Created user {user_id} in MetisAgent3")
            
            # Store each credential
            for prop_name, prop_value in credentials.items():
                # Determine if this should be encrypted
                should_encrypt = any(keyword in prop_name.lower() for keyword in 
                                   ['oauth', 'api_key', 'token', 'password', 'credential', 'secret'])
                
                # Handle OAuth tokens specially
                if prop_name.startswith('oauth_'):
                    provider = prop_name.replace('oauth_', '')
                    
                    # Store in oauth_tokens table
                    with self.metis3_storage.db.transaction() as conn:
                        conn.execute("""
                            INSERT OR REPLACE INTO oauth_tokens 
                            (user_id, provider, token_encrypted, scope, expires_at)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            user_id,
                            provider,
                            self.metis3_storage.db.encrypt_data(json.dumps(prop_value)),
                            prop_value.get('scope', '') if isinstance(prop_value, dict) else '',
                            prop_value.get('expires_at') if isinstance(prop_value, dict) else None
                        ))
                    
                    logger.info(f"🔑 Stored OAuth token for {provider}")
                
                # Store as user attribute
                await self.metis3_storage.set_user_attribute(
                    user_id, prop_name, prop_value, encrypt=should_encrypt
                )
                
                if should_encrypt:
                    logger.info(f"🔐 Stored encrypted credential: {prop_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to store credentials for user {user_id}: {e}")
    
    async def _store_system_credentials(self, credentials):
        """Store system credentials in MetisAgent3"""
        try:
            for prop_name, prop_value in credentials.items():
                should_encrypt = any(keyword in prop_name.lower() for keyword in 
                                   ['oauth', 'api_key', 'token', 'password', 'credential', 'secret'])
                
                await self.metis3_storage.set_user_attribute(
                    'system', prop_name, prop_value, encrypt=should_encrypt
                )
                
                logger.info(f"🔧 Stored system credential: {prop_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to store system credentials: {e}")


def main():
    import asyncio
    
    extractor = MetisAgent2CredentialExtractor()
    extractor.extract_all_credentials()
    
    print("\n" + "="*60)
    print("🎉 CREDENTIAL EXTRACTION COMPLETED!")
    print("="*60)
    print(f"📊 FINAL STATISTICS:")
    for key, value in extractor.stats.items():
        print(f"   {key}: {value}")
    print("="*60)


if __name__ == "__main__":
    main()