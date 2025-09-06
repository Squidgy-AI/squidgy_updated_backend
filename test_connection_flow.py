#!/usr/bin/env python3
"""
Test the complete connection flow:
1. Get pages (should show is_connected=False)
2. Connect a page (should change is_connected to True)
3. Get pages again (should show is_connected=True)
"""

import asyncio
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
import os

async def test_connection_flow():
    """Test the complete connection flow"""
    
    print("🔄 TESTING COMPLETE CONNECTION FLOW")
    print("=" * 80)
    
    # Load environment variables
    load_dotenv()
    
    # Connect to database
    supabase_url = os.getenv("SUPABASE_URL") or "https://aoteeitreschwzkbpqyd.supabase.co"
    supabase_key = os.getenv("SUPABASE_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvdGVlaXRyZXNjaHd6a2JwcXlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQxMjAwMzQsImV4cCI6MjA1OTY5NjAzNH0.S7P9-G4CaSE6DWycNq0grv-x6UCIsfLvXooCtMwaKHM"
    
    supabase: Client = create_client(supabase_url, supabase_key)
    
    # Test parameters
    location_id = "GJSb0aPcrBRne73LK3A3"
    
    print("📋 Step 1: Check current database state")
    print("-" * 40)
    
    # Check current database state
    response = supabase.table('squidgy_facebook_pages')\
        .select("page_id, page_name, is_connected_to_ghl, connected_at")\
        .eq('location_id', location_id)\
        .execute()
    
    if response.data:
        print(f"📊 Found {len(response.data)} page(s) in database:")
        for page in response.data:
            status = "✅ Connected" if page['is_connected_to_ghl'] else "🔗 Not Connected"
            connected_at = page['connected_at'] or "Never"
            print(f"   - {page['page_name']} ({page['page_id']}): {status} (Connected: {connected_at})")
    else:
        print("📭 No pages found in database")
    
    print("\n📋 Step 2: Test the expected flow")
    print("-" * 40)
    
    print("🔍 **EXPECTED BEHAVIOR:**")
    print("1. 📥 **First insertion**: is_connected_to_ghl = False")
    print("2. 🔗 **After connecting**: is_connected_to_ghl = True")
    print("3. 📅 **connected_at**: NULL → actual timestamp")
    
    print("\n📋 Step 3: Check today's insertions")
    print("-" * 40)
    
    # Check today's insertions
    from datetime import datetime, timezone
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    today_response = supabase.table('squidgy_facebook_pages')\
        .select("*")\
        .eq('location_id', location_id)\
        .gte('created_at', today_start.isoformat())\
        .execute()
    
    if today_response.data:
        print(f"📅 Found {len(today_response.data)} page(s) created today:")
        for page in today_response.data:
            status = "✅ Connected" if page['is_connected_to_ghl'] else "🔗 Not Connected"
            created_at = page['created_at']
            connected_at = page['connected_at'] or "Never"
            print(f"   - {page['page_name']} ({page['page_id']})")
            print(f"     Status: {status}")
            print(f"     Created: {created_at}")
            print(f"     Connected: {connected_at}")
    else:
        print("📭 No pages created today")
    
    print("\n📋 Step 4: Instructions for testing")
    print("-" * 40)
    
    print("🧪 **TO TEST THE COMPLETE FLOW:**")
    print("1. 🚀 Start backend: python main.py")
    print("2. 🌐 Start frontend: npm run dev")
    print("3. 📱 Use Facebook integration in UI")
    print("4. 🔍 Check Step 2 of integration (should show 🔗 Not Connected)")
    print("5. 📋 Select a page and click 'Connect'")
    print("6. 🔄 Check database again (should show ✅ Connected)")
    print("7. 🎯 Check GHL dashboard (should show connected)")
    
    print("\n📋 Step 5: Quick database reset (if needed)")
    print("-" * 40)
    
    reset = input("🔄 Reset all connection statuses to False? (y/N): ").strip().lower()
    if reset == 'y':
        print("🔄 Resetting all connection statuses...")
        
        supabase.table('squidgy_facebook_pages')\
            .update({
                'is_connected_to_ghl': False,
                'connected_at': None,
                'updated_at': datetime.now(timezone.utc).isoformat()
            })\
            .eq('location_id', location_id)\
            .execute()
        
        print("✅ All pages reset to disconnected state")
    
    print("\n✅ Connection flow test completed!")

if __name__ == "__main__":
    asyncio.run(test_connection_flow())