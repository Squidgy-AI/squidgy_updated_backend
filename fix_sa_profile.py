#!/usr/bin/env python3
"""
Simple script to create profile for sa@squidgy.ai
Much simpler than complex SQL triggers
"""

import os
import uuid
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def fix_sa_profile():
    print('🔧 Creating profile for sa@squidgy.ai...')
    
    supabase = create_client(
        os.getenv('SUPABASE_URL'),
        os.getenv('SUPABASE_KEY')
    )
    
    try:
        # Check if profile already exists
        existing = supabase.from_('profiles').select('*').eq('email', 'sa@squidgy.ai').execute()
        
        if existing.data:
            print('✅ Profile already exists for sa@squidgy.ai')
            return
        
        # Get user info from auth.users (if accessible)
        # Since we can't access auth.users directly with anon key, we'll create based on what we know
        
        # Create profile with known data
        profile_data = {
            'id': str(uuid.uuid4()),
            'user_id': str(uuid.uuid4()),  # This should match auth.users.id but we don't have access
            'email': 'sa@squidgy.ai',
            'full_name': 'Soma Microsoft Email',  # From the signup request we saw
            'role': 'member',
            'email_confirmed': False,  # Until they click confirmation email
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        result = supabase.from_('profiles').insert(profile_data).execute()
        
        if result.data:
            print('✅ Profile created successfully for sa@squidgy.ai')
            print(f'   📧 Email: {profile_data["email"]}')
            print(f'   👤 Full Name: {profile_data["full_name"]}')
            print(f'   🆔 Profile ID: {profile_data["id"]}')
        else:
            print('❌ Failed to create profile')
            
    except Exception as e:
        print(f'❌ Error: {e}')
        print('\n💡 Note: This might fail due to user_id mismatch with auth.users')
        print('   The frontend fix is the proper solution for new users')

if __name__ == '__main__':
    fix_sa_profile()