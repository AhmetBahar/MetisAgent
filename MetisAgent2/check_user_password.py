#!/usr/bin/env python3
"""
Kullanıcı şifresini kontrol et ve sıfırla
"""

import os
import sys

# Add the current directory to the path
sys.path.insert(0, '.')

from app.auth_manager import auth_manager

def check_and_reset_password():
    """Kullanıcı şifresini kontrol et ve sıfırla"""
    
    username = "ahmetb@minor.com.tr"
    new_password = "123456"  # Basit test şifresi
    
    print(f"🔍 Checking user: {username}")
    
    # Kullanıcı bilgilerini getir
    user = auth_manager.get_user(username)
    
    if user:
        print(f"✅ User found:")
        print(f"   Username: {user['username']}")
        print(f"   Email: {user['email']}")
        print(f"   User ID: {user['user_id']}")
        print(f"   Status: {user['status']}")
        print(f"   Password Hash: {user['password_hash'][:50]}...")
        
        # Şifreyi test edelim
        print(f"\n🔧 Testing some common passwords...")
        
        common_passwords = ["123456", "admin", "password", "ahmet", "test", ""]
        
        for test_password in common_passwords:
            try:
                result = auth_manager.authenticate_user(username, test_password)
                if result['status'] == 'success':
                    print(f"✅ Correct password found: '{test_password}'")
                    return test_password
                else:
                    print(f"❌ '{test_password}': {result.get('message', 'Failed')}")
            except Exception as e:
                print(f"❌ '{test_password}': Error - {e}")
        
        # Şifre bulunamazsa yeni şifre ata
        print(f"\n🔧 Setting new password: '{new_password}'")
        
        try:
            # Yeni kullanıcı oluştur (mevcut silinecek)
            result = auth_manager.create_user(
                username, 
                new_password, 
                user['email'], 
                user['permissions']
            )
            
            if result['status'] == 'error' and 'zaten mevcut' in result['message']:
                print("⚠️  User already exists. Let me delete and recreate...")
                
                # Manual password update gerekli - şimdilik yeni şifre ile login test edelim
                auth_result = auth_manager.authenticate_user(username, new_password)
                if auth_result['status'] == 'success':
                    print(f"✅ Password is already: '{new_password}'")
                else:
                    print(f"❌ Need manual password reset in database")
                    print(f"   Current hash: {user['password_hash']}")
                    
                    # Hash'i manual olarak hesapla
                    import hashlib
                    import secrets
                    
                    salt = secrets.token_hex(16)
                    hash_obj = hashlib.pbkdf2_hmac(
                        'sha256', 
                        new_password.encode('utf-8'), 
                        salt.encode('utf-8'), 
                        100000
                    )
                    new_hash = f"{salt}${hash_obj.hex()}"
                    
                    print(f"   New hash should be: {new_hash}")
                    
        except Exception as e:
            print(f"❌ Password reset error: {e}")
    else:
        print(f"❌ User not found: {username}")

if __name__ == "__main__":
    check_and_reset_password()