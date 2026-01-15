#!/usr/bin/env python3
"""
Test script to debug user mapping issues
"""

import sys
import os
import json

# Add current directory to path
sys.path.insert(0, '/home/ahmet/MetisAgent/MetisAgent2')

from tools.user_storage import get_user_storage

def test_user_mappings():
    """Test user mapping functionality"""
    print("=== User Mapping Test ===")
    
    storage = get_user_storage()
    
    # List all users
    print("\n1. All users in database:")
    users = storage.list_users()
    for user in users:
        print(f"  - {user}")
    
    # Test specific mapping queries
    test_users = [
        "ahmetbahar.minor@gmail.com",
        "ahmetb@minor.com.tr", 
        "f75ba26d-0eb6-4f88-81de-96057fd6ed12"
    ]
    
    print("\n2. Testing user mappings:")
    for user_id in test_users:
        mapping = storage.get_user_mapping(user_id, 'google')
        print(f"  {user_id} -> google: {mapping}")
        
        # Also show all properties for this user
        all_props = storage.get_all_properties(user_id)
        mapping_props = {k: v for k, v in all_props.items() if k.startswith('mapping_')}
        if mapping_props:
            print(f"    All mappings: {mapping_props}")
        
        oauth_google = storage.get_oauth_token(user_id, 'google')
        print(f"    OAuth Google: {'Present' if oauth_google else 'None'}")
        print()
    
    # Test reverse lookup - find which user has Google mapping to ahmetbahar.minor@gmail.com
    print("\n3. Reverse lookup for ahmetbahar.minor@gmail.com:")
    for user_id in users:
        google_mapping = storage.get_user_mapping(user_id, 'google')
        if google_mapping == "ahmetbahar.minor@gmail.com":
            print(f"  Found mapping: {user_id} -> {google_mapping}")
            
            # Check if this user has OAuth tokens
            oauth_token = storage.get_oauth_token(user_id, 'google')
            print(f"  OAuth Token: {'Present' if oauth_token else 'None'}")
            
            if oauth_token:
                # Don't print token details, just structure
                print(f"    Token keys: {list(oauth_token.keys()) if oauth_token else 'None'}")

if __name__ == "__main__":
    test_user_mappings()