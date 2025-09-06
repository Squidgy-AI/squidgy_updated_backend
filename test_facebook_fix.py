#!/usr/bin/env python3
"""
Test script for Facebook integration fix
Uses the correct credentials provided by user
"""

import asyncio
import os
from facebook_pages_api_working import get_facebook_pages, FacebookPagesRequest

async def test_facebook_integration():
    """Test Facebook integration with correct credentials"""
    
    print("🧪 Testing Facebook Integration Fix")
    print("=" * 50)
    
    # Use the correct credentials provided
    test_request = FacebookPagesRequest(
        email="info+zt1rcl49@squidgy.net",
        password="Dummy@123",
        user_id="MHwz5yMaG0JrTfGXjvxB",  # This is the user_id
        location_id="rlRJ1n5Hoy3X53WDOJlq",  # This is the location_id  
        firm_user_id="80b957fc-de1d-4f28-920c-41e0e2e28e5e",  # Original firm_user_id
        step="get_pages_only",
        manual_jwt_token=None  # Let it auto-extract
    )
    
    # Set environment variables for Gmail 2FA
    os.environ["GMAIL_2FA_EMAIL"] = "info+zt1rcl49@squidgy.net"
    os.environ["GMAIL_2FA_APP_PASSWORD"] = "qfwfjrfedcjbzdam"
    
    print(f"📧 Using email: {test_request.email}")
    print(f"🔑 Using password: {test_request.password}")
    print(f"👤 User ID: {test_request.user_id}")
    print(f"📍 Location ID: {test_request.location_id}")
    print("")
    
    try:
        print("🚀 Starting Facebook integration test...")
        result = await get_facebook_pages(test_request)
        
        if result.success:
            print("✅ SUCCESS! Facebook integration completed")
            print(f"📄 Found {len(result.pages)} pages")
            print(f"🔑 JWT Token: {result.jwt_token[:50]}..." if result.jwt_token else "No JWT token")
            
            for i, page in enumerate(result.pages, 1):
                print(f"   {i}. {page.page_name} (ID: {page.page_id})")
            
        else:
            print("❌ FAILED! Facebook integration failed")
            print(f"💬 Message: {result.message}")
            if result.manual_mode:
                print("🔧 Manual mode required")
                print("📋 Instructions:")
                print(result.manual_instructions)
            
    except Exception as e:
        print(f"💥 ERROR! Exception during test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_facebook_integration())