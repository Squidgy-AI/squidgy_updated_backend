#!/usr/bin/env python3
"""
Diagnostic Facebook API Test
============================
Test the actual Facebook API endpoint with detailed logging
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import List, Dict
from pydantic import BaseModel

# Import the actual function from the working API
from facebook_pages_api_working import FacebookPagesRequest, get_facebook_pages

async def diagnostic_facebook_test():
    """Test the actual Facebook Pages API with detailed diagnostics"""
    
    print("🔍 DIAGNOSTIC FACEBOOK API TEST")
    print("=" * 80)
    
    # Create test request
    test_request = FacebookPagesRequest(
        location_id="GJSb0aPcrBRne73LK3A3",
        user_id="ExLH8YJG8qfhdmeZTzMX", 
        email="info@squidgy.net",
        password="Dummy@123",
        firm_user_id=f"diagnostic_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    
    print(f"📦 Request details:")
    print(f"   Location ID: {test_request.location_id}")
    print(f"   User ID: {test_request.user_id}")
    print(f"   Email: {test_request.email}")
    print(f"   Firm User ID: {test_request.firm_user_id}")
    print("=" * 80)
    
    try:
        print("\n🚀 Calling get_facebook_pages function...")
        
        # Call the actual function
        result = await get_facebook_pages(test_request)
        
        print(f"\n📋 API Response:")
        print(f"   Success: {result.success}")
        print(f"   Message: {result.message}")
        
        if result.success:
            print(f"   Total Pages: {result.total_pages}")
            print(f"   JWT Captured: {result.jwt_token_captured}")
            print(f"   Database Saved: {result.database_saved}")
            
            if result.pages:
                print(f"\n📱 Pages Found ({len(result.pages)}):")
                for i, page in enumerate(result.pages, 1):
                    print(f"   Page {i}:")
                    print(f"   - ID: {page.page_id}")
                    print(f"   - Name: {page.page_name}")
                    print(f"   - Connected: {page.is_connected}")
                    print(f"   - Instagram: {page.instagram_available}")
            else:
                print("   No pages in response")
        
        else:
            print(f"   Error occurred: {result.message}")
            if result.manual_mode:
                print("   Manual mode required")
                if result.manual_instructions:
                    print(f"   Instructions: {result.manual_instructions}")
        
        print(f"\n📄 Full Response:")
        print(json.dumps(result.dict(), indent=2, default=str))
        
        # Check database after the call
        print(f"\n🔍 Checking database for new records...")
        from supabase import create_client, Client
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Check for records with this firm_user_id
        db_response = supabase.table('squidgy_facebook_pages')\
            .select("*")\
            .eq('firm_user_id', test_request.firm_user_id)\
            .execute()
        
        if db_response.data:
            print(f"✅ Found {len(db_response.data)} record(s) in database for this test:")
            for record in db_response.data:
                print(f"   - {record.get('page_name')} (Created: {record.get('created_at')})")
        else:
            print("❌ No records found in database for this test")
        
    except Exception as e:
        print(f"💥 Error during test: {e}")
        print(f"Error type: {type(e).__name__}")
        
        import traceback
        print(f"\n📜 Full traceback:")
        print(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(diagnostic_facebook_test())