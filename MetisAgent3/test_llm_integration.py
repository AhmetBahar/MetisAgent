#!/usr/bin/env python3
"""
Test script to verify LLM integration with migrated API keys from MetisAgent2
"""

import asyncio
import sys
import os
from pathlib import Path

# Add MetisAgent3 to path
sys.path.insert(0, str(Path(__file__).parent))

from core.storage.sqlite_storage import SQLiteUserStorage
from core.tools.llm_tool import LLMTool
from core.contracts.base_types import ExecutionContext


async def test_llm_integration():
    """Test LLM integration with migrated credentials"""
    
    print("🧪 Testing LLM Integration with Migrated API Keys")
    print("=" * 60)
    
    # Initialize storage
    storage = SQLiteUserStorage()
    
    # Check migrated credentials
    print("\n📋 1. Checking migrated credentials...")
    
    # Check for API keys (using user with real API keys)
    test_user_id = "6ff412b9-aa9f-4f90-b0c7-fce27d016960"  # ahmetb@minor.com.tr user
    openai_key = await storage.get_user_attribute("test_clean", "api_key_openai")  # OpenAI from test_clean
    anthropic_key = await storage.get_user_attribute(test_user_id, "anthropic_api_key")  # Real Anthropic key
    
    print(f"   • OpenAI API Key: {'✅ Found' if openai_key else '❌ Missing'}")
    print(f"   • Anthropic API Key: {'✅ Found' if anthropic_key else '❌ Missing'}")
    
    if not openai_key and not anthropic_key:
        print("\n❌ No API keys found! Please run migration first.")
        return False
    
    # Initialize LLM Tool
    print("\n🤖 2. Initializing LLM Tool...")
    llm_tool = LLMTool()
    
    # Create test execution context (use real user for Anthropic, test_clean for OpenAI)
    context = ExecutionContext(
        user_id=test_user_id,  # Use real user with Anthropic key
        conversation_id="test_llm_integration",
        session_id="test_session_001"
    )
    
    # Test with available provider
    test_models = []
    if openai_key:
        test_models.append(("gpt-4o-mini", "OpenAI"))
    if anthropic_key:
        test_models.append(("claude-3-5-sonnet-20241022", "Anthropic"))
    
    success_count = 0
    
    for model, provider in test_models:
        print(f"\n🔄 3. Testing {provider} ({model})...")
        
        # Use appropriate user context for each provider
        if provider == "OpenAI":
            test_context = ExecutionContext(
                user_id="test_clean",  # OpenAI key is here
                conversation_id="test_llm_integration",
                session_id="test_session_001"
            )
        else:  # Anthropic
            test_context = ExecutionContext(
                user_id=test_user_id,  # Real Anthropic key is here
                conversation_id="test_llm_integration", 
                session_id="test_session_001"
            )
        
        try:
            # Simple test prompt
            result = await llm_tool.execute(
                capability="generate_response",
                input_data={
                    "messages": [{"role": "user", "content": "MetisAgent3 test başarılı! Türkçe olarak 'Test successful!' yanıtı ver."}],
                    "model": model,
                    "provider": provider.lower(),
                    "max_tokens": 50
                },
                context=test_context
            )
            
            if result.success and result.data:
                print(f"   ✅ {provider} API Response: {result.data.get('response', 'No response')[:100]}")
                success_count += 1
            else:
                print(f"   ❌ {provider} API Failed: {result.error}")
                
        except Exception as e:
            print(f"   ❌ {provider} API Error: {str(e)[:100]}")
    
    # Test conversation management
    print(f"\n💭 4. Testing conversation management...")
    try:
        conversations = await llm_tool.list_conversations(test_user_id)
        print(f"   ✅ Conversation Management: Found {len(conversations)} conversations")
        
        # Check if our test conversation was saved
        test_conv = [c for c in conversations if c.conversation_id == "test_llm_integration"]
        if test_conv:
            print(f"   ✅ Test conversation saved with {len(test_conv[0].messages)} messages")
        
    except Exception as e:
        print(f"   ❌ Conversation Management Error: {str(e)}")
    
    # Final report
    print(f"\n📊 Test Results:")
    print(f"   • API Tests: {success_count}/{len(test_models)} passed")
    print(f"   • Overall Status: {'✅ SUCCESS' if success_count > 0 else '❌ FAILED'}")
    
    if success_count > 0:
        print(f"\n🎉 LLM Integration is working! MetisAgent3 can use migrated API keys.")
        return True
    else:
        print(f"\n❌ LLM Integration failed. Check API keys and network connectivity.")
        return False


async def main():
    """Main test runner"""
    try:
        success = await test_llm_integration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())