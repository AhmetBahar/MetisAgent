#!/usr/bin/env python3
"""
Test memory storage without ChromaDB dependencies
"""

import json
import os
from datetime import datetime
import uuid

def test_memory_storage():
    print("🧠 Testing Memory Storage for Instagram Credentials...")
    
    # Create memory storage directory
    storage_dir = "memory_storage"
    user_id = "ahmetb@minor.com.tr"
    os.makedirs(storage_dir, exist_ok=True)
    
    try:
        # Create memory data
        memory_data = {
            "memory_id": str(uuid.uuid4()),
            "content": "Instagram login credentials: username=ahmet__bahar, password=bahaT4121, email=ahmetb@minor.com.tr. Successfully tested login and logout.",
            "category": "instagram_credentials",
            "tags": ["instagram", "login", "credentials", "ahmet__bahar"],
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id
        }
        
        # Save to user-specific file
        user_dir = os.path.join(storage_dir, user_id)
        os.makedirs(user_dir, exist_ok=True)
        
        memories_file = os.path.join(user_dir, "memories.json")
        
        # Load existing or create new
        if os.path.exists(memories_file):
            with open(memories_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {"memories": []}
        
        # Add new memory
        data["memories"].append(memory_data)
        
        # Save back
        with open(memories_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Memory stored: {memories_file}")
        print(f"✅ Memory ID: {memory_data['memory_id']}")
        print(f"✅ Content: {memory_data['content'][:100]}...")
        
        # Test search functionality
        print("\n🔍 Testing Memory Search...")
        
        # Load and search
        with open(memories_file, 'r', encoding='utf-8') as f:
            stored_data = json.load(f)
        
        # Search for Instagram related memories
        search_keywords = ["instagram", "login", "ahmet__bahar"]
        found_memories = []
        
        for memory in stored_data["memories"]:
            content_lower = memory["content"].lower()
            if any(keyword.lower() in content_lower for keyword in search_keywords):
                found_memories.append(memory)
        
        print(f"✅ Found {len(found_memories)} relevant memories")
        
        for i, memory in enumerate(found_memories, 1):
            print(f"\n{i}. Memory found:")
            print(f"   Category: {memory['category']}")
            print(f"   Tags: {memory['tags']}")
            print(f"   Content: {memory['content'][:100]}...")
            print(f"   Timestamp: {memory['timestamp']}")
        
        # Test parameter extraction
        print("\n📋 Testing Parameter Extraction...")
        if found_memories:
            content = found_memories[0]["content"]
            
            # Extract credentials using simple parsing
            import re
            
            username_match = re.search(r'username=(\w+)', content)
            password_match = re.search(r'password=(\w+)', content)
            email_match = re.search(r'email=([^\s,]+)', content)
            
            if username_match and password_match and email_match:
                extracted_creds = {
                    "username": username_match.group(1),
                    "password": password_match.group(1),
                    "user_id": email_match.group(1)
                }
                
                print("✅ Successfully extracted credentials:")
                print(f"   Username: {extracted_creds['username']}")
                print(f"   Password: {extracted_creds['password'][:5]}*****")
                print(f"   User ID: {extracted_creds['user_id']}")
                
                return True, extracted_creds
            else:
                print("❌ Failed to extract credentials from memory")
                return False, None
        else:
            print("❌ No memories found for search")
            return False, None
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False, None

def test_memory_api():
    print("\n🔧 Testing Memory API Integration...")
    
    # Simulate the API call that should work
    test_request = {
        "tool_name": "memory_manager",
        "action_name": "store_memory",
        "params": {
            "content": "Instagram login credentials: username=ahmet__bahar, password=bahaT4121, email=ahmetb@minor.com.tr",
            "category": "instagram_credentials", 
            "tags": ["instagram", "login", "credentials"],
            "user_id": "ahmetb@minor.com.tr"
        }
    }
    
    print("API Request that should be made:")
    print(json.dumps(test_request, indent=2))
    
    test_search = {
        "tool_name": "memory_manager",
        "action_name": "retrieve_memories",
        "params": {
            "query": "instagram login",
            "user_id": "ahmetb@minor.com.tr",
            "limit": 5
        }
    }
    
    print("\nAPI Search that should be made:")
    print(json.dumps(test_search, indent=2))

if __name__ == "__main__":
    print("🧪 Memory Storage Test Suite\n")
    
    success, credentials = test_memory_storage()
    test_memory_api()
    
    if success:
        print("\n🎉 MEMORY STORAGE TEST PASSED!")
        print("✅ Can store Instagram credentials")
        print("✅ Can search and retrieve memories") 
        print("✅ Can extract parameters for workflow")
        print("\n💡 Next Steps:")
        print("1. Store credentials via API")
        print("2. Test memory search in workflow")
        print("3. Auto-fill parameters from memory")
    else:
        print("\n💥 Tests failed - check implementation")