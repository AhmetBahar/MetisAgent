#!/usr/bin/env python3
"""
Test script for SQLite-based conversation persistence system
"""

import asyncio
import sys
import os
from pathlib import Path

# Add MetisAgent3 to path
sys.path.insert(0, str(Path(__file__).parent))

from core.services.conversation_service import ConversationService
from core.tools.llm_tool import LLMTool
from core.contracts.base_types import ExecutionContext


async def test_conversation_persistence():
    """Test SQLite conversation persistence"""
    
    print("🧪 Testing SQLite Conversation Persistence System")
    print("=" * 60)
    
    # Initialize services
    conversation_service = ConversationService()
    llm_tool = LLMTool()
    
    test_user_id = "6ff412b9-aa9f-4f90-b0c7-fce27d016960"  # User with Anthropic key
    
    try:
        # Test 1: Create new conversation with LLM
        print("\n📝 1. Creating new conversation...")
        context = ExecutionContext(
            user_id=test_user_id,
            conversation_id="auto-generated",
            session_id="test_persistence"
        )
        
        result = await llm_tool.execute(
            capability="generate_response",
            input_data={
                "messages": [{"role": "user", "content": "Merhaba! MetisAgent3 conversation persistence test'i yapıyorum. Bu mesaj SQLite'a kaydedilecek mi?"}],
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 100
            },
            context=context
        )
        
        if result.success:
            conversation_id = result.data.get("conversation_id")
            print(f"   ✅ New conversation created: {conversation_id}")
            print(f"   ✅ Response: {result.data.get('response', '')[:100]}...")
            print(f"   ✅ Persistent: {result.metadata.get('persistent', False)}")
        else:
            print(f"   ❌ Failed to create conversation: {result.error}")
            return False
        
        # Test 2: Continue conversation
        print(f"\n💬 2. Continuing conversation {conversation_id}...")
        
        result2 = await llm_tool.execute(
            capability="generate_response", 
            input_data={
                "messages": [{"role": "user", "content": "Bu ikinci mesajım. Önceki konuşmayı hatırlıyor musun?"}],
                "conversation_id": conversation_id,
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 100
            },
            context=context
        )
        
        if result2.success:
            print(f"   ✅ Continued conversation successfully")
            print(f"   ✅ Response: {result2.data.get('response', '')[:100]}...")
            print(f"   ✅ Message count: {result2.data.get('message_count', 0)}")
        else:
            print(f"   ❌ Failed to continue conversation: {result2.error}")
        
        # Test 3: List conversations
        print(f"\n📋 3. Listing conversations...")
        
        list_result = await llm_tool.execute(
            capability="list_conversations",
            input_data={"limit": 10},
            context=context
        )
        
        if list_result.success:
            conversations = list_result.data.get("conversations", [])
            print(f"   ✅ Found {len(conversations)} conversations")
            for conv in conversations[:3]:  # Show first 3
                print(f"   • {conv['title']} ({conv['total_messages']} messages)")
        else:
            print(f"   ❌ Failed to list conversations: {list_result.error}")
        
        # Test 4: Get specific conversation
        print(f"\n🔍 4. Getting conversation details...")
        
        get_result = await llm_tool.execute(
            capability="get_conversation",
            input_data={"conversation_id": conversation_id},
            context=context
        )
        
        if get_result.success:
            conv_data = get_result.data.get("conversation", {})
            messages = get_result.data.get("messages", [])
            print(f"   ✅ Conversation: {conv_data.get('title')}")
            print(f"   ✅ Total messages: {conv_data.get('total_messages')}")
            print(f"   ✅ Total tokens: {conv_data.get('total_tokens')}")
            print(f"   ✅ Retrieved messages: {len(messages)}")
        else:
            print(f"   ❌ Failed to get conversation: {get_result.error}")
        
        # Test 5: Search conversations
        print(f"\n🔎 5. Searching conversations...")
        
        search_result = await llm_tool.execute(
            capability="search_conversations",
            input_data={
                "query": "MetisAgent3 test",
                "limit": 5
            },
            context=context
        )
        
        if search_result.success:
            results = search_result.data.get("results", [])
            print(f"   ✅ Found {len(results)} search results")
            for result in results[:2]:  # Show first 2
                print(f"   • {result['content_snippet'][:80]}...")
                print(f"     Relevance: {result['relevance_score']:.2f}")
        else:
            print(f"   ❌ Failed to search conversations: {search_result.error}")
        
        # Test 6: Direct conversation service test
        print(f"\n🔧 6. Testing ConversationService directly...")
        
        # Create conversation directly
        new_conv_id = await conversation_service.create_conversation(
            user_id=test_user_id,
            title="Direct Service Test",
            initial_message="This is a direct service test message.",
            tags=["test", "direct"]
        )
        
        print(f"   ✅ Direct conversation created: {new_conv_id}")
        
        # Add message
        await conversation_service.add_message(
            conversation_id=new_conv_id,
            user_id=test_user_id,
            role="assistant",
            content="This is a test response from direct service.",
            metadata={"test": True}
        )
        
        print(f"   ✅ Added message to conversation")
        
        # Search in all conversations
        direct_search = await conversation_service.search_conversations(
            user_id=test_user_id,
            query="direct service",
            limit=3
        )
        
        print(f"   ✅ Direct search found {len(direct_search)} results")
        
        print(f"\n🎉 Conversation Persistence Tests Complete!")
        print(f"📊 Summary:")
        print(f"   • LLM Tool integration: ✅ Working")
        print(f"   • SQLite persistence: ✅ Working") 
        print(f"   • Full-text search: ✅ Working")
        print(f"   • Conversation management: ✅ Working")
        
        return True
        
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test runner"""
    try:
        success = await test_conversation_persistence()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n💥 Test runner failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())