#!/usr/bin/env python3
"""
Debug script for settings cards discovery
"""

import asyncio
import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Import our services
from core.services.tool_card_discovery_service import ToolCardDiscoveryService
from core.services.settings_card_service import SettingsCardService
from core.services.tool_execution_service import ToolExecutionService

async def debug_card_discovery():
    """Debug card discovery process"""
    print("🔍 Starting Card Discovery Debug...")
    
    # 1. Check if Google Tool directory exists
    plugins_dir = Path("plugins")
    google_tool_dir = plugins_dir / "google_tool"
    cards_file = google_tool_dir / "settings_cards.json"
    
    print(f"📂 Plugins directory: {plugins_dir.absolute()} (exists: {plugins_dir.exists()})")
    print(f"📂 Google tool directory: {google_tool_dir.absolute()} (exists: {google_tool_dir.exists()})")
    print(f"📄 Cards file: {cards_file.absolute()} (exists: {cards_file.exists()})")
    
    if cards_file.exists():
        print("📖 Reading cards file content...")
        with open(cards_file, 'r') as f:
            content = json.load(f)
        print(f"📋 Cards file content: {json.dumps(content, indent=2)}")
    
    # 2. Test card discovery service
    print("\n🔧 Testing Card Discovery Service...")
    discovery_service = ToolCardDiscoveryService()
    
    try:
        # Test single tool discovery
        cards = await discovery_service.discover_tool_cards(
            str(google_tool_dir), 
            "google_tool"
        )
        print(f"✅ Discovered {len(cards)} cards for google_tool")
        for card in cards:
            print(f"  - {card.card_id}: {card.title} ({card.type})")
        
        # Test all tools discovery  
        all_cards = await discovery_service.discover_all_tool_cards(str(plugins_dir))
        print(f"✅ Discovered cards from {len(all_cards)} tools total")
        for tool_name, tool_cards in all_cards.items():
            print(f"  - {tool_name}: {len(tool_cards)} cards")
            
    except Exception as e:
        print(f"❌ Card discovery failed: {e}")
        logger.exception("Card discovery error")
    
    # 3. Test settings card service
    print("\n⚙️ Testing Settings Card Service...")
    try:
        # Create minimal tool execution service (mock)
        tool_execution_service = ToolExecutionService(None, None)
        settings_service = SettingsCardService(tool_execution_service)
        settings_service.set_card_discovery_service(discovery_service)
        
        # Try to discover and register cards
        await settings_service.discover_and_register_tool_cards(str(plugins_dir))
        
        # Check registered cards
        categories = settings_service.get_card_categories()
        print(f"📋 Available categories: {len(categories)}")
        for cat in categories:
            print(f"  - {cat['id']}: {cat['name']}")
            
        # Get cards for anonymous user (testing)
        cards = await settings_service.get_user_cards("anonymous")
        print(f"🃏 Cards for anonymous user: {len(cards)}")
        for card in cards:
            print(f"  - {card['card_id']}: {card['title']} ({card['type']})")
            
    except Exception as e:
        print(f"❌ Settings service test failed: {e}")
        logger.exception("Settings service error")

if __name__ == "__main__":
    asyncio.run(debug_card_discovery())