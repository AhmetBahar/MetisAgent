#!/usr/bin/env python3
"""
Google Tools Test Script
"""

import os
import sys

# Add the current directory to the path
sys.path.insert(0, '.')

from tools.google_tools import google_tools

def test_google_tools():
    """Test Google tools with manual credentials"""
    
    user_id = "ahmetb@minor.com.tr"
    
    print(f"🔍 Testing Google Tools for user: {user_id}")
    print()
    
    # Check credentials status
    print("1. Checking credentials status...")
    status = google_tools.check_credentials_status(user_id)
    
    for key, value in status.items():
        print(f"   {key}: {value}")
    
    print()
    
    # Test Gmail functionality
    if status.get('has_credentials'):
        print("2. Testing Gmail functionality...")
        
        result = google_tools.send_gmail(
            user_id=user_id,
            to_email="test@example.com",
            subject="Test Email from MetisAgent",
            body="Bu MetisAgent'dan gönderilen bir test emailidir."
        )
        
        print(f"   Success: {result.get('success')}")
        print(f"   Method: {result.get('method', 'N/A')}")
        print(f"   Message: {result.get('message', result.get('error'))}")
        
        if result.get('suggestion'):
            print(f"   Suggestion: {result.get('suggestion')}")
    else:
        print("2. Cannot test Gmail - No credentials available")
        print("   Add credentials via Settings > Google Account")
    
    print()
    print("✅ Google Tools test complete")

if __name__ == "__main__":
    test_google_tools()