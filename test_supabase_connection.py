#!/usr/bin/env python3
"""
Quick test script to verify Supabase connection
"""

import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

def test_connection():
    """Test basic Supabase connection"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    print(f"Supabase URL: {supabase_url}")
    print(f"Supabase Key: {supabase_key[:20]}..." if supabase_key else "No key found")
    
    try:
        client = create_client(supabase_url, supabase_key)
        print("\nSuccessfully created Supabase client!")
        
        # Try to query the table (even if empty)
        response = client.table('squidgy_facebook_pages').select('*').limit(1).execute()
        print(f"Successfully queried table! Found {len(response.data)} records.")
        
        return True
    except Exception as e:
        print(f"\nError: {e}")
        return False

if __name__ == "__main__":
    print("Testing Supabase connection...")
    if test_connection():
        print("\nConnection test passed!")
    else:
        print("\nConnection test failed!")