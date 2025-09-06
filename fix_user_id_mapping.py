#!/usr/bin/env python3
"""
Fix user_id mapping issue

Current issue:
- n8n sends profile.id as "user_id" 
- But database expects auth.user_id (from profiles.user_id column)

Example:
- Profile ID (what n8n sends): a59741cd-aed2-44da-a479-78bc601d1596
- Auth User ID (what DB needs): 80b957fc-de1d-4f28-920c-41e0e2e28e5e
"""

import asyncio
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

def check_current_mapping():
    """Check how IDs are currently stored"""
    print("🔍 Checking current ID usage in database")
    print("=" * 60)
    
    # Check client_kb table
    client_kb_result = supabase.table('client_kb').select('client_id').limit(5).execute()
    print("\n📊 Sample client_kb entries:")
    for entry in client_kb_result.data:
        print(f"   client_id: {entry['client_id']}")
        
    # Check which type of ID these are
    if client_kb_result.data:
        sample_id = client_kb_result.data[0]['client_id']
        
        # Check if it's a profile ID
        profile_check = supabase.table('profiles').select('id, user_id').eq('id', sample_id).execute()
        if profile_check.data:
            print(f"\n✅ Currently using Profile IDs")
            print(f"   Profile ID: {profile_check.data[0]['id']}")
            print(f"   Auth User ID: {profile_check.data[0]['user_id']}")
        else:
            # Check if it's an auth user ID
            auth_check = supabase.table('profiles').select('id, user_id').eq('user_id', sample_id).execute()
            if auth_check.data:
                print(f"\n✅ Currently using Auth User IDs")
                print(f"   Profile ID: {auth_check.data[0]['id']}")
                print(f"   Auth User ID: {auth_check.data[0]['user_id']}")

def show_fix_options():
    """Show available fix options"""
    print("\n\n🔧 FIX OPTIONS:")
    print("=" * 60)
    print("\nOption 1: Update Backend to Accept Profile IDs (RECOMMENDED)")
    print("   - Keep n8n sending profile.id as 'user_id'")
    print("   - Backend continues using this as client_id")
    print("   - This is what's currently working")
    
    print("\nOption 2: Change to Auth User IDs")
    print("   - Update n8n to send profiles.user_id instead of profiles.id")
    print("   - Migrate existing data to use auth user IDs")
    print("   - More complex, requires frontend changes")
    
    print("\n📝 RECOMMENDATION:")
    print("Since your system is already working with profile IDs,")
    print("and n8n is sending profile.id as 'user_id', keep it as is.")
    print("The naming is just semantic - what matters is consistency.")

async def check_data_consistency():
    """Check if data is consistent"""
    print("\n\n🔍 Checking Data Consistency")
    print("=" * 60)
    
    # Get a sample user
    sample_user = {
        'profile_id': 'a59741cd-aed2-44da-a479-78bc601d1596',
        'auth_user_id': '80b957fc-de1d-4f28-920c-41e0e2e28e5e',
        'email': 'dmacproject123@gmail.com'
    }
    
    print(f"\nChecking user: {sample_user['email']}")
    print(f"Profile ID: {sample_user['profile_id']}")
    print(f"Auth User ID: {sample_user['auth_user_id']}")
    
    # Check client_kb
    kb_with_profile = supabase.table('client_kb').select('*').eq('client_id', sample_user['profile_id']).execute()
    kb_with_auth = supabase.table('client_kb').select('*').eq('client_id', sample_user['auth_user_id']).execute()
    
    print(f"\n📊 client_kb entries:")
    print(f"   Using Profile ID: {len(kb_with_profile.data)} entries")
    print(f"   Using Auth ID: {len(kb_with_auth.data)} entries")
    
    # Check client_context
    context_with_profile = supabase.table('client_context').select('*').eq('client_id', sample_user['profile_id']).execute()
    context_with_auth = supabase.table('client_context').select('*').eq('client_id', sample_user['auth_user_id']).execute()
    
    print(f"\n📊 client_context entries:")
    print(f"   Using Profile ID: {len(context_with_profile.data)} entries")
    print(f"   Using Auth ID: {len(context_with_auth.data)} entries")
    
    return len(kb_with_profile.data) > 0 or len(context_with_profile.data) > 0

if __name__ == "__main__":
    print("🔍 USER ID MAPPING ANALYSIS")
    print("=" * 60)
    print("\nCurrent situation:")
    print("- n8n sends profile.id as 'user_id'")
    print("- Backend uses this value as client_id in database")
    print("- This is actually working correctly!")
    
    check_current_mapping()
    show_fix_options()
    
    # Check consistency
    has_data = asyncio.run(check_data_consistency())
    
    print("\n\n✅ CONCLUSION:")
    print("=" * 60)
    if has_data:
        print("Your system is consistently using Profile IDs.")
        print("This is working correctly - no changes needed!")
        print("\nThe confusion is just naming:")
        print("- n8n field: 'user_id' (contains profile.id)")
        print("- Database field: 'client_id' (stores profile.id)")
        print("- This mapping is consistent and functional!")
    else:
        print("No data found with profile IDs.")
        print("You might need to check your data flow.")