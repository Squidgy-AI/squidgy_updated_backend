#!/usr/bin/env python3
"""
Check Supabase database for today's Facebook pages records
"""
import os
from datetime import datetime, timezone
from supabase import create_client, Client
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: Missing SUPABASE_URL or SUPABASE_KEY in .env file")
    exit(1)

# Create Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("🔍 Checking squidgy_facebook_pages table for today's records...")
print(f"📅 Today's date (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d')}")
print("=" * 80)

try:
    # Get today's date in UTC
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_start_str = today_start.isoformat()
    
    # Query for today's records
    response = supabase.table('squidgy_facebook_pages')\
        .select("*")\
        .gte('created_at', today_start_str)\
        .execute()
    
    if response.data:
        print(f"✅ Found {len(response.data)} record(s) created today:\n")
        
        for idx, record in enumerate(response.data, 1):
            print(f"📱 Record #{idx}:")
            print(f"   Page Name: {record.get('page_name', 'N/A')}")
            print(f"   Page ID: {record.get('page_id', 'N/A')}")
            print(f"   Location ID: {record.get('location_id', 'N/A')}")
            print(f"   User ID: {record.get('user_id', 'N/A')}")
            print(f"   Firm User ID: {record.get('firm_user_id', 'N/A')}")
            print(f"   Instagram Available: {record.get('is_instagram_available', False)}")
            print(f"   Connected to GHL: {record.get('is_connected_to_ghl', False)}")
            print(f"   Created At: {record.get('created_at', 'N/A')}")
            print("-" * 40)
    else:
        print("❌ No records found for today.")
        print("\n🔍 Checking for ALL records in the table...")
        
        # Get all records to see what's there
        all_response = supabase.table('squidgy_facebook_pages')\
            .select("*")\
            .order('created_at', desc=True)\
            .limit(10)\
            .execute()
        
        if all_response.data:
            print(f"\n📊 Found {len(all_response.data)} recent record(s) (showing latest 10):\n")
            
            for idx, record in enumerate(all_response.data, 1):
                created_at = record.get('created_at', 'N/A')
                print(f"Record #{idx}: {record.get('page_name', 'N/A')} - Created: {created_at}")
        else:
            print("❌ No records found in the table at all.")
    
    # Also check the count
    count_response = supabase.table('squidgy_facebook_pages')\
        .select("*", count='exact', head=True)\
        .execute()
    
    print(f"\n📊 Total records in table: {count_response.count}")
    
except Exception as e:
    print(f"❌ Error querying database: {str(e)}")
    print(f"   Error type: {type(e).__name__}")