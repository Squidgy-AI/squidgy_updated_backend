#!/usr/bin/env python3
"""
Mock Facebook Pages Database Test
=================================
Test database insertion without browser automation
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import List, Dict
from supabase import create_client, Client
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Mock data structures
class MockFacebookPagesRequest:
    def __init__(self):
        self.location_id = "GJSb0aPcrBRne73LK3A3"
        self.user_id = "ExLH8YJG8qfhdmeZTzMX"
        self.email = "info@squidgy.net"
        self.password = "Dummy@123"
        self.firm_user_id = f"test_firm_user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

async def mock_store_pages_in_database(pages: List[Dict], request: MockFacebookPagesRequest, jwt_token: str) -> bool:
    """Store Facebook pages in database - MOCK VERSION with detailed logging"""
    
    try:
        supabase_url = os.getenv("SUPABASE_URL") or "https://aoteeitreschwzkbpqyd.supabase.co"
        supabase_key = os.getenv("SUPABASE_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvdGVlaXRyZXNjaHd6a2JwcXlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQxMjAwMzQsImV4cCI6MjA1OTY5NjAzNH0.S7P9-G4CaSE6DWycNq0grv-x6UCIsfLvXooCtMwaKHM"
        
        print(f"🔑 Using Supabase URL: {supabase_url}")
        print(f"🔑 Using Supabase Key: {supabase_key[:20]}...")
        
        supabase: Client = create_client(supabase_url, supabase_key)
        
        print(f"💾 Attempting to save {len(pages)} pages to database...")
        print(f"📍 Location ID: {request.location_id}")
        print(f"👤 User ID: {request.user_id}")
        print(f"🏢 Firm User ID: {request.firm_user_id}")
        print("=" * 80)
        
        for i, page in enumerate(pages, 1):
            print(f"\n📱 Processing Page #{i}:")
            print(f"   Raw page data: {json.dumps(page, indent=2)}")
            
            # Create page data structure
            page_data = {
                "firm_user_id": request.firm_user_id,
                "location_id": request.location_id,
                "user_id": request.user_id,
                "page_id": page.get("facebookPageId", f"mock_page_{i}"),
                "page_name": page.get("facebookPageName", f"Mock Page {i}"),
                "page_access_token": jwt_token,
                "page_category": "business",
                "instagram_business_account_id": "",
                "is_instagram_available": page.get("isInstagramAvailable", False),
                "is_connected_to_ghl": True,
                "connected_at": datetime.now(timezone.utc).isoformat(),
                "raw_page_data": {
                    "page_data": page,
                    "integration_info": {
                        "ghl_login_email": request.email,
                        "user_name": "Soma Addakula",
                        "location_name": f"SolarBusiness_{request.location_id}",
                        "jwt_token": jwt_token,
                        "integration_completed_at": datetime.now(timezone.utc).isoformat(),
                        "ghl_integration_status": "connected"
                    }
                },
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            print(f"   📋 Prepared data for insertion:")
            print(f"   - Page ID: {page_data['page_id']}")
            print(f"   - Page Name: {page_data['page_name']}")
            print(f"   - Created At: {page_data['created_at']}")
            
            try:
                # Test the database insertion
                print(f"   💾 Attempting database upsert...")
                
                response = supabase.table('squidgy_facebook_pages').upsert(
                    page_data,
                    on_conflict='location_id,page_id'
                ).execute()
                
                print(f"   ✅ Database response: {response}")
                print(f"   ✅ Saved page: {page.get('facebookPageName', f'Mock Page {i}')} to database")
                
                # Verify the insertion
                verify_response = supabase.table('squidgy_facebook_pages')\
                    .select("*")\
                    .eq('page_id', page_data['page_id'])\
                    .eq('location_id', page_data['location_id'])\
                    .execute()
                
                if verify_response.data:
                    print(f"   ✅ Verification: Record found in database")
                    print(f"      Created at: {verify_response.data[0].get('created_at')}")
                else:
                    print(f"   ❌ Verification: Record NOT found in database!")
                
            except Exception as insert_error:
                print(f"   ❌ Database insertion failed: {insert_error}")
                print(f"   Error type: {type(insert_error).__name__}")
                return False
        
        print(f"\n🎉 All {len(pages)} pages processed successfully!")
        return True
        
    except Exception as e:
        print(f"💥 Database error: {e}")
        print(f"Error type: {type(e).__name__}")
        return False

async def run_mock_test():
    """Run the mock Facebook pages database test"""
    
    print("🧪 MOCK FACEBOOK PAGES DATABASE TEST")
    print("=" * 80)
    
    # Create mock request
    request = MockFacebookPagesRequest()
    
    # Create mock JWT token
    mock_jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.mock_jwt_token_for_testing"
    
    # Create mock Facebook pages data (simulating GHL API response)
    mock_pages = [
        {
            "facebookPageId": f"mock_page_id_{datetime.now().strftime('%Y%m%d_%H%M%S')}_1",
            "facebookPageName": "Mock Test Business Page 1",
            "isInstagramAvailable": True,
            "connected": True,
            "category": "Business",
            "access_token": "mock_page_access_token_1"
        },
        {
            "facebookPageId": f"mock_page_id_{datetime.now().strftime('%Y%m%d_%H%M%S')}_2",
            "facebookPageName": "Mock Test Business Page 2",
            "isInstagramAvailable": False,
            "connected": False,
            "category": "Local Business",
            "access_token": "mock_page_access_token_2"
        }
    ]
    
    print(f"📦 Mock pages to insert: {len(mock_pages)}")
    for i, page in enumerate(mock_pages, 1):
        print(f"   Page {i}: {page['facebookPageName']} (ID: {page['facebookPageId']})")
    
    print("\n🚀 Starting database insertion test...")
    
    # Test the database insertion
    success = await mock_store_pages_in_database(mock_pages, request, mock_jwt_token)
    
    if success:
        print("\n✅ MOCK TEST PASSED: Database insertion successful!")
        
        # Check today's records
        print("\n🔍 Checking today's records in database...")
        try:
            supabase_url = os.getenv("SUPABASE_URL") or "https://aoteeitreschwzkbpqyd.supabase.co"
            supabase_key = os.getenv("SUPABASE_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvdGVlaXRyZXNjaHd6a2JwcXlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQxMjAwMzQsImV4cCI6MjA1OTY5NjAzNH0.S7P9-G4CaSE6DWycNq0grv-x6UCIsfLvXooCtMwaKHM"
            
            supabase: Client = create_client(supabase_url, supabase_key)
            
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            today_start_str = today_start.isoformat()
            
            response = supabase.table('squidgy_facebook_pages')\
                .select("*")\
                .gte('created_at', today_start_str)\
                .execute()
            
            print(f"📊 Found {len(response.data)} record(s) created today:")
            for record in response.data:
                print(f"   - {record.get('page_name')} (Created: {record.get('created_at')})")
        
        except Exception as check_error:
            print(f"❌ Error checking today's records: {check_error}")
    else:
        print("\n❌ MOCK TEST FAILED: Database insertion failed!")

if __name__ == "__main__":
    asyncio.run(run_mock_test())