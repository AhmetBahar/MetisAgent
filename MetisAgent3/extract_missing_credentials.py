"""
Extract Missing Major Credentials
Focus on the main users: ahmetb@minor.com.tr and f75ba26d-0eb6-4f88-81de-96057fd6ed12
"""

import sqlite3
import json
import logging
import sys
import asyncio
from pathlib import Path
from cryptography.fernet import Fernet
import base64

sys.path.append('/home/ahmet/MetisAgent/MetisAgent3')
from core.storage import SQLiteUserStorage

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def extract_missing_credentials():
    """Extract missing credentials for main users"""
    
    # Load MetisAgent2 encryption key
    metis2_path = Path("/home/ahmet/MetisAgent/MetisAgent2")
    metis2_key_file = metis2_path / "storage.key"
    
    with open(metis2_key_file, 'rb') as f:
        encryption_key = f.read()
    
    cipher = Fernet(encryption_key)
    
    def decrypt_value(encrypted_value):
        try:
            decoded = base64.b64decode(encrypted_value.encode('utf-8'))
            decrypted = cipher.decrypt(decoded)
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.warning(f"Decryption failed: {e}")
            return None
    
    # Initialize storage
    metis3_storage = SQLiteUserStorage()
    metis2_db = metis2_path / "users.db"
    
    # Focus on main users
    main_users = ['ahmetb@minor.com.tr', 'f75ba26d-0eb6-4f88-81de-96057fd6ed12']
    
    extracted_count = 0
    
    for user_id in main_users:
        logger.info(f"🔄 Extracting credentials for: {user_id}")
        
        with sqlite3.connect(metis2_db) as conn:
            conn.row_factory = sqlite3.Row
            
            cursor = conn.execute("""
                SELECT property_name, property_value, is_encrypted, property_type
                FROM user_properties 
                WHERE user_id = ? AND is_encrypted = 1
            """, (user_id,))
            
            for row in cursor.fetchall():
                prop_name = row['property_name']
                prop_value = row['property_value']
                prop_type = row['property_type']
                
                # Decrypt the value
                decrypted_value = decrypt_value(prop_value)
                
                if decrypted_value is not None:
                    # Parse based on property type
                    if prop_type == 'json':
                        try:
                            parsed_value = json.loads(decrypted_value)
                        except:
                            parsed_value = decrypted_value
                    else:
                        parsed_value = decrypted_value
                    
                    # Determine target user ID in MetisAgent3
                    if user_id == 'ahmetb@minor.com.tr':
                        target_user_id = '6ff412b9-aa9f-4f90-b0c7-fce27d016960'  # From verification
                    elif user_id == 'f75ba26d-0eb6-4f88-81de-96057fd6ed12':
                        target_user_id = user_id  # Same ID
                    
                    # Check if user exists in MetisAgent3
                    user = await metis3_storage.get_user(target_user_id)
                    if not user:
                        logger.warning(f"⚠️  User {target_user_id} not found in MetisAgent3")
                        continue
                    
                    # Store credential
                    if prop_name.startswith('oauth_'):
                        provider = prop_name.replace('oauth_', '')
                        
                        # Store in oauth_tokens table
                        with metis3_storage.db.transaction() as conn:
                            conn.execute("""
                                INSERT OR REPLACE INTO oauth_tokens 
                                (user_id, provider, token_encrypted, scope, expires_at)
                                VALUES (?, ?, ?, ?, ?)
                            """, (
                                target_user_id,
                                provider,
                                metis3_storage.db.encrypt_data(json.dumps(parsed_value)),
                                parsed_value.get('scope', '') if isinstance(parsed_value, dict) else '',
                                parsed_value.get('expires_at') if isinstance(parsed_value, dict) else None
                            ))
                        
                        logger.info(f"🔑 Stored OAuth token: {user_id} → {provider}")
                    
                    # Store as encrypted user attribute
                    await metis3_storage.set_user_attribute(
                        target_user_id, prop_name, parsed_value, encrypt=True
                    )
                    
                    extracted_count += 1
                    logger.info(f"🔐 Stored credential: {user_id} → {prop_name}")
                
                else:
                    logger.warning(f"⚠️  Failed to decrypt: {user_id} → {prop_name}")
    
    logger.info(f"🎉 Extraction completed! {extracted_count} credentials processed")
    
    # Verify extraction
    print("\n" + "="*50)
    print("🔍 VERIFICATION - Major User Credentials")
    print("="*50)
    
    for user_id in ['6ff412b9-aa9f-4f90-b0c7-fce27d016960', 'f75ba26d-0eb6-4f88-81de-96057fd6ed12']:
        user = await metis3_storage.get_user(user_id)
        if user:
            print(f"\n👤 {user['email']} ({user_id})")
            
            # Get attributes
            attributes = await metis3_storage.get_user_attributes(user_id)
            
            oauth_tokens = [k for k in attributes.keys() if k.startswith('oauth_')]
            api_keys = [k for k in attributes.keys() if k.startswith('api_key_')]
            passwords = [k for k in attributes.keys() if 'password' in k]
            
            print(f"   🔑 OAuth Tokens: {len(oauth_tokens)} → {oauth_tokens}")
            print(f"   🗝️  API Keys: {len(api_keys)} → {api_keys}")
            print(f"   🔒 Passwords: {len(passwords)} → {passwords}")
    
    # Check OAuth tokens table
    print(f"\n🔍 OAuth Tokens in Database:")
    with metis3_storage.db.transaction() as conn:
        cursor = conn.execute("""
            SELECT user_id, provider 
            FROM oauth_tokens 
            WHERE user_id IN ('6ff412b9-aa9f-4f90-b0c7-fce27d016960', 'f75ba26d-0eb6-4f88-81de-96057fd6ed12')
        """)
        for row in cursor.fetchall():
            print(f"   🔑 {row['user_id']} → {row['provider']}")
    
    print("="*50)


if __name__ == "__main__":
    asyncio.run(extract_missing_credentials())