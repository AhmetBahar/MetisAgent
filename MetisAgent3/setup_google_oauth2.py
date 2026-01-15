#!/usr/bin/env python3
"""
Google OAuth2 Setup Script for MetisAgent3 Google Tool

This script helps configure Google OAuth2 credentials for the Google Tool plugin.
"""

import json
import os
import sys
from pathlib import Path

def main():
    print("🔧 Google OAuth2 Setup for MetisAgent3")
    print("=" * 50)
    
    # Get Google OAuth2 credentials from user
    print("\n📝 Please provide your Google OAuth2 credentials:")
    print("   (Get them from: https://console.cloud.google.com/)")
    
    client_id = input("\n🔑 Google Client ID: ").strip()
    if not client_id:
        print("❌ Client ID is required!")
        sys.exit(1)
        
    client_secret = input("🔐 Google Client Secret: ").strip()
    if not client_secret:
        print("❌ Client Secret is required!")
        sys.exit(1)
        
    # Update tool configuration
    config_dir = Path(__file__).parent / "config"
    config_dir.mkdir(exist_ok=True)
    
    # Create Google OAuth2 config
    oauth2_config = {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": "http://localhost:5001/oauth2/google/callback",
        "scopes": [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/drive"
        ],
        "enabled": True
    }
    
    # Save configuration
    oauth2_config_path = config_dir / "google_oauth2_config.json"
    with open(oauth2_config_path, 'w') as f:
        json.dump(oauth2_config, f, indent=2)
    
    print(f"✅ Google OAuth2 configuration saved to: {oauth2_config_path}")
    
    # Update Google Tool configuration
    google_tool_config_path = Path(__file__).parent / "plugins" / "google_tool" / "tool_config.json"
    
    if google_tool_config_path.exists():
        with open(google_tool_config_path, 'r') as f:
            tool_config = json.load(f)
        
        # Update client credentials in tool config
        tool_config["tool_configuration"]["config"]["client_id"] = client_id
        tool_config["tool_configuration"]["config"]["client_secret"] = client_secret
        
        with open(google_tool_config_path, 'w') as f:
            json.dump(tool_config, f, indent=2)
        
        print(f"✅ Updated Google Tool configuration: {google_tool_config_path}")
    
    print("\n🚀 Google OAuth2 setup completed!")
    print("📋 Next steps:")
    print("   1. Make sure your Google Cloud Console project has the following APIs enabled:")
    print("      • Gmail API")
    print("      • Google Calendar API") 
    print("      • Google Drive API")
    print("   2. Add authorized redirect URI in Google Cloud Console:")
    print("      • http://localhost:5001/oauth2/google/callback")
    print("   3. Start the MetisAgent3 bridge server")
    print("   4. Go to Settings -> Google OAuth2 in the frontend")
    print("   5. Click 'Google ile Yetkilendir' to start OAuth flow")
    
    print(f"\n🔐 Your credentials are stored securely in: {oauth2_config_path}")


if __name__ == "__main__":
    main()