#!/usr/bin/env python3
"""
Python script to delete sa@squidgy.ai from Supabase
Using Supabase client methods
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def delete_sa_user():
    print('🗑️ Deleting sa@squidgy.ai from all Supabase tables...')
    
    supabase = create_client(
        os.getenv('SUPABASE_URL'),
        os.getenv('SUPABASE_KEY')
    )
    
    email = 'sa@squidgy.ai'
    
    try:
        # 1. Delete from profiles table
        print('1️⃣ Deleting from profiles table...')
        result = supabase.from_('profiles').delete().eq('email', email).execute()
        print(f'   Profiles deleted: {len(result.data) if result.data else 0}')
        
        # 2. Delete from invitations table (as recipient)
        print('2️⃣ Deleting from invitations table...')
        result = supabase.from_('invitations').delete().eq('recipient_email', email).execute()
        print(f'   Invitations deleted: {len(result.data) if result.data else 0}')
        
        # 3. Delete from auth.users (this might fail with anon key)
        print('3️⃣ Attempting to delete from auth.users...')
        try:
            # This requires admin/service role key
            result = supabase.auth.admin.delete_user(user_id="user-id-here")
            print('   ✅ User deleted from auth.users')
        except Exception as auth_error:
            print(f'   ❌ Failed to delete from auth.users: {auth_error}')
            print('   💡 You need to delete from Supabase Dashboard → Authentication → Users')
            print('   💡 Or use a service role key instead of anon key')
        
        print('\n✅ Cleanup completed (except auth.users - do manually)')
        
    except Exception as e:
        print(f'❌ Error during cleanup: {e}')

def verify_deletion():
    print('\n🔍 Verifying deletion...')
    
    supabase = create_client(
        os.getenv('SUPABASE_URL'),
        os.getenv('SUPABASE_KEY')
    )
    
    email = 'sa@squidgy.ai'
    
    try:
        # Check profiles
        profiles = supabase.from_('profiles').select('*').eq('email', email).execute()
        print(f'📋 Profiles remaining: {len(profiles.data) if profiles.data else 0}')
        
        # Check invitations
        invitations = supabase.from_('invitations').select('*').eq('recipient_email', email).execute()
        print(f'📧 Invitations remaining: {len(invitations.data) if invitations.data else 0}')
        
        print('\n✅ Verification complete')
        print('⚠️ Note: Cannot verify auth.users with anon key')
        
    except Exception as e:
        print(f'❌ Error during verification: {e}')

if __name__ == '__main__':
    delete_sa_user()
    verify_deletion()
    
    print('\n📋 Manual Steps Required:')
    print('1. Go to Supabase Dashboard → Authentication → Users')
    print('2. Search for sa@squidgy.ai')
    print('3. Click Delete to remove from auth.users')
    print('4. Then test signup again with fresh user')