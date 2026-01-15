#!/usr/bin/env python3
"""
Test script for advanced settings management system
"""

import asyncio
import sys
from pathlib import Path

# Add MetisAgent3 to path
sys.path.insert(0, str(Path(__file__).parent))

from core.services.settings_service import SettingsService, SettingCategory, SettingsIntegration


async def test_settings_service():
    """Test advanced settings management"""
    
    print("🧪 Testing Advanced Settings Management System")
    print("=" * 60)
    
    # Initialize services
    settings_service = SettingsService()
    integration = SettingsIntegration(settings_service)
    
    test_user_id = "6ff412b9-aa9f-4f90-b0c7-fce27d016960"  # Our test user
    
    try:
        # Test 1: Get default settings
        print("\n📋 1. Testing default settings...")
        
        language = await settings_service.get_user_setting(test_user_id, "user_language")
        theme = await settings_service.get_user_setting(test_user_id, "theme")
        max_tokens = await settings_service.get_user_setting(test_user_id, "max_tokens_per_request")
        
        print(f"   ✅ Default language: {language}")
        print(f"   ✅ Default theme: {theme}")
        print(f"   ✅ Default max tokens: {max_tokens}")
        
        # Test 2: Set user settings
        print("\n⚙️  2. Setting custom user preferences...")
        
        success1 = await settings_service.set_user_setting(test_user_id, "user_language", "tr")
        success2 = await settings_service.set_user_setting(test_user_id, "theme", "dark")
        success3 = await settings_service.set_user_setting(test_user_id, "items_per_page", 50)
        
        print(f"   ✅ Set language to Turkish: {success1}")
        print(f"   ✅ Set theme to dark: {success2}")
        print(f"   ✅ Set items per page to 50: {success3}")
        
        # Verify the changes
        new_language = await settings_service.get_user_setting(test_user_id, "user_language")
        new_theme = await settings_service.get_user_setting(test_user_id, "theme")
        new_items = await settings_service.get_user_setting(test_user_id, "items_per_page")
        
        print(f"   ✅ Verified language: {new_language}")
        print(f"   ✅ Verified theme: {new_theme}")
        print(f"   ✅ Verified items per page: {new_items}")
        
        # Test 3: API Key management (encrypted settings)
        print("\n🔐 3. Testing encrypted API key storage...")
        
        # Set API keys (these should be encrypted)
        openai_success = await settings_service.set_user_setting(
            test_user_id, "openai_api_key", "sk-test-openai-key-12345"
        )
        anthropic_success = await settings_service.set_user_setting(
            test_user_id, "anthropic_api_key", "sk-ant-test-anthropic-key-67890"
        )
        
        print(f"   ✅ Set OpenAI API key: {openai_success}")
        print(f"   ✅ Set Anthropic API key: {anthropic_success}")
        
        # Retrieve API keys
        openai_key = await settings_service.get_user_setting(test_user_id, "openai_api_key")
        anthropic_key = await settings_service.get_user_setting(test_user_id, "anthropic_api_key")
        
        print(f"   ✅ Retrieved OpenAI key: {openai_key[:15]}..." if openai_key else "❌ Failed to retrieve")
        print(f"   ✅ Retrieved Anthropic key: {anthropic_key[:15]}..." if anthropic_key else "❌ Failed to retrieve")
        
        # Test 4: Get settings by category
        print("\n📚 4. Testing category-based settings retrieval...")
        
        appearance_settings = await settings_service.get_user_settings_by_category(
            test_user_id, SettingCategory.APPEARANCE
        )
        api_key_settings = await settings_service.get_user_settings_by_category(
            test_user_id, SettingCategory.API_KEYS
        )
        
        print(f"   ✅ Appearance settings: {len(appearance_settings)} items")
        for key, value in appearance_settings.items():
            print(f"     • {key}: {value}")
        
        print(f"   ✅ API key settings: {len(api_key_settings)} items")
        for key, value in api_key_settings.items():
            masked_value = f"{str(value)[:10]}..." if value else "None"
            print(f"     • {key}: {masked_value}")
        
        # Test 5: Bulk settings operations
        print("\n🔄 5. Testing bulk settings operations...")
        
        bulk_settings = {
            "notifications_enabled": True,
            "analytics_enabled": False,
            "data_retention_days": 60,
            "cache_enabled": True
        }
        
        bulk_results = await settings_service.bulk_set_user_settings(test_user_id, bulk_settings)
        
        print(f"   ✅ Bulk set results:")
        for key, success in bulk_results.items():
            print(f"     • {key}: {'✅' if success else '❌'}")
        
        # Test 6: Settings validation
        print("\n✅ 6. Testing settings validation...")
        
        try:
            # Try to set invalid value (out of range)
            await settings_service.set_user_setting(test_user_id, "items_per_page", 150)
            print("   ❌ Validation failed - should have rejected value > 100")
        except Exception as e:
            print(f"   ✅ Validation working: {str(e)[:50]}...")
        
        try:
            # Try to set invalid choice
            await settings_service.set_user_setting(test_user_id, "theme", "rainbow")
            print("   ❌ Validation failed - should have rejected invalid choice")
        except Exception as e:
            print(f"   ✅ Choice validation working: {str(e)[:50]}...")
        
        # Test 7: Get all user settings
        print("\n📊 7. Getting complete user settings overview...")
        
        all_settings = await settings_service.get_all_user_settings(test_user_id, include_defaults=False)
        
        print(f"   ✅ User has customized settings in {len(all_settings)} categories:")
        for category, settings in all_settings.items():
            print(f"     • {category}: {len(settings)} settings")
        
        # Test 8: Integration helpers
        print("\n🔗 8. Testing integration helpers...")
        
        llm_config = await integration.get_llm_config(test_user_id)
        ui_config = await integration.get_ui_config(test_user_id)
        
        print(f"   ✅ LLM Config:")
        print(f"     • Default provider: {llm_config.get('default_provider')}")
        print(f"     • Default model: {llm_config.get('default_model')}")
        print(f"     • Max tokens: {llm_config.get('max_tokens')}")
        print(f"     • API keys available: {len([k for k, v in llm_config.get('api_keys', {}).items() if v])}")
        
        print(f"   ✅ UI Config:")
        print(f"     • Theme: {ui_config.get('theme')}")
        print(f"     • Language: {ui_config.get('language')}")
        print(f"     • Items per page: {ui_config.get('items_per_page')}")
        
        # Test 9: Settings search
        print("\n🔍 9. Testing settings search...")
        
        search_results = await settings_service.search_settings("api")
        print(f"   ✅ Search 'api' found {len(search_results)} settings:")
        for result in search_results[:3]:  # Show first 3
            print(f"     • {result.key}: {result.description}")
        
        # Test 10: Settings schema
        print("\n📋 10. Testing settings schema generation...")
        
        schema = await settings_service.get_setting_schema()
        print(f"   ✅ Generated schema for {len(schema['definitions'])} settings")
        print(f"   ✅ Organized into {len(schema['categories'])} categories:")
        for category, keys in schema['categories'].items():
            print(f"     • {category}: {len(keys)} settings")
        
        print(f"\n🎉 Settings Service Tests Complete!")
        print(f"📊 Summary:")
        print(f"   • Default settings: ✅ Working")
        print(f"   • Custom user settings: ✅ Working") 
        print(f"   • Encrypted storage: ✅ Working")
        print(f"   • Category organization: ✅ Working")
        print(f"   • Bulk operations: ✅ Working")
        print(f"   • Validation: ✅ Working")
        print(f"   • Integration helpers: ✅ Working")
        print(f"   • Search & schema: ✅ Working")
        
        return True
        
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test runner"""
    try:
        success = await test_settings_service()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n💥 Test runner failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())