"""
Test script to trigger PIT token automation for a specific GHL subaccount
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path, override=True)

# Import the automation function
sys.path.insert(0, os.path.dirname(__file__))

async def test_pit_automation():
    """Test PIT automation for Chester's test account"""
    
    # Test account details
    ghl_record_id = "b9e6dc5d-f313-480c-b81f-2152b51e1d9a"
    firm_user_id = "55b33685-4481-4289-850e-db21c6f5a8c0"
    location_id = "y6s9fyyiisMvJGWdFLzD"
    email = "somashekhar34+y6s9fyyi@gmail.com"
    password = "Dummy@123"
    ghl_user_id = "BOftjgujCczOTvOEi4vJ"
    
    print("="*80)
    print("🔑 PIT TOKEN AUTOMATION TEST")
    print("="*80)
    print(f"📋 Test Account Details:")
    print(f"   GHL Record ID: {ghl_record_id}")
    print(f"   Firm User ID: {firm_user_id}")
    print(f"   Location ID: {location_id}")
    print(f"   Email: {email}")
    print(f"   GHL User ID: {ghl_user_id}")
    print("="*80)
    print()
    
    # Import Supabase client
    try:
        from supabase import create_client, Client
        from supabase.lib.client_options import SyncClientOptions

        # Use credentials directly for testing
        supabase_url = "https://aoteeitreschwzkbpqyd.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvdGVlaXRyZXNjaHd6a2JwcXlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQxMjAwMzQsImV4cCI6MjA1OTY5NjAzNH0.S7P9-G4CaSE6DWycNq0grv-x6UCIsfLvXooCtMwaKHM"
        supabase_schema = os.getenv('SUPABASE_SCHEMA', 'public')

        supabase: Client = create_client(supabase_url, supabase_key, options=SyncClientOptions(schema=supabase_schema))
        print("✅ Connected to Supabase")
        
        # Check current pit_token status
        print("\n📊 Checking current pit_token status...")
        result = supabase.table('ghl_subaccounts').select('pit_token, automation_status').eq('id', ghl_record_id).single().execute()
        
        if result.data:
            current_pit = result.data.get('pit_token')
            current_status = result.data.get('automation_status')
            print(f"   Current pit_token: {current_pit[:30] + '...' if current_pit else 'NULL'}")
            print(f"   Current Status: {current_status}")
        else:
            print("❌ ERROR: GHL record not found")
            return
        
    except Exception as e:
        print(f"❌ ERROR: Could not connect to Supabase: {e}")
        return
    
    # Import and run the Playwright automation
    try:
        print("\n🚀 Starting PIT Token Automation...")
        print("="*80)
        
        from ghl_automation_complete_playwright import HighLevelCompleteAutomationPlaywright
        
        # Update status to running
        supabase.table('ghl_subaccounts').update({
            'automation_status': 'pit_running'
        }).eq('id', ghl_record_id).execute()
        
        print("✅ Updated automation_status to 'pit_running'")
        print("\n🤖 Initializing Playwright automation...")
        
        # Run automation in non-headless mode so you can see it
        automation = HighLevelCompleteAutomationPlaywright(headless=False)
        
        print("▶️  Starting automation workflow...")
        print("   This will:")
        print("   1. Login to GoHighLevel")
        print("   2. Navigate to Private Integrations")
        print("   3. Create PIT token with all scopes")
        print("   4. Extract and save the token")
        print()
        
        success = await automation.run_automation(
            email=email,
            password=password,
            location_id=location_id,
            firm_user_id=firm_user_id,
            agent_id='SOL',
            ghl_user_id=ghl_user_id,
            save_to_database=False  # We handle database operations here
        )
        
        print("\n" + "="*80)
        
        if success:
            # Extract PIT token
            pit_token = automation.pit_token if hasattr(automation, 'pit_token') else None
            
            if pit_token:
                print("✅ PIT TOKEN GENERATED SUCCESSFULLY!")
                print(f"🎉 PIT Token: {pit_token[:30]}...")
                print(f"📏 Token Length: {len(pit_token)} characters")
                
                # Update ghl_subaccounts with pit_token
                print("\n💾 Updating ghl_subaccounts table...")
                supabase.table('ghl_subaccounts').update({
                    'pit_token': pit_token,
                    'automation_status': 'pit_completed'
                }).eq('id', ghl_record_id).execute()
                
                print("✅ Database updated successfully!")
                
                # Verify the update
                print("\n🔍 Verifying database update...")
                verify_result = supabase.table('ghl_subaccounts').select('pit_token, automation_status').eq('id', ghl_record_id).single().execute()
                
                if verify_result.data:
                    saved_pit = verify_result.data.get('pit_token')
                    saved_status = verify_result.data.get('automation_status')
                    
                    if saved_pit == pit_token:
                        print("✅ VERIFICATION SUCCESSFUL!")
                        print(f"   pit_token in DB: {saved_pit[:30]}...")
                        print(f"   Status in DB: {saved_status}")
                    else:
                        print("❌ VERIFICATION FAILED: Token mismatch!")
                
                print("\n" + "="*80)
                print("🎊 TEST COMPLETED SUCCESSFULLY!")
                print("="*80)
                
            else:
                print("❌ PIT TOKEN NOT FOUND!")
                print("   Automation completed but token was not extracted")
                
                supabase.table('ghl_subaccounts').update({
                    'automation_status': 'pit_failed',
                    'automation_error': 'PIT token not extracted'
                }).eq('id', ghl_record_id).execute()
                
        else:
            print("❌ AUTOMATION FAILED!")
            print("   Check the logs above for details")
            
            supabase.table('ghl_subaccounts').update({
                'automation_status': 'pit_failed',
                'automation_error': 'Automation workflow failed'
            }).eq('id', ghl_record_id).execute()
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print(f"   Error type: {type(e).__name__}")
        
        try:
            supabase.table('ghl_subaccounts').update({
                'automation_status': 'pit_failed',
                'automation_error': str(e)
            }).eq('id', ghl_record_id).execute()
        except:
            pass

if __name__ == "__main__":
    print("\n🔑 PIT Token Automation Test Script")
    print("   Account: Chester Conrad Test Account")
    print("   Location: y6s9fyyiisMvJGWdFLzD")
    print()
    
    asyncio.run(test_pit_automation())
