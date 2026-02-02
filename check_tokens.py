"""
Quick script to check tokens in database for a specific user
"""
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

firm_user_id = "8ad341fa-d2aa-480b-b2ef-d28cefaa8e40"

result = supabase.table('ghl_subaccounts').select('*').eq('firm_user_id', firm_user_id).eq('agent_id', 'SOL').execute()

if result.data:
    data = result.data[0]
    print("="*80)
    print("DATABASE RECORD:")
    print("="*80)
    print(f"firm_user_id: {data.get('firm_user_id')}")
    print(f"ghl_location_id: {data.get('ghl_location_id')}")
    print(f"soma_ghl_user_id: {data.get('soma_ghl_user_id')}")
    print(f"soma_ghl_email: {data.get('soma_ghl_email')}")
    print(f"soma_ghl_password: {data.get('soma_ghl_password')}")
    print()
    print("TOKENS:")
    print(f"firebase_token: {data.get('firebase_token')[:50] if data.get('firebase_token') else '❌ MISSING'}")
    print(f"access_token: {data.get('access_token')[:50] if data.get('access_token') else '❌ MISSING'}")
    print(f"pit_token: {data.get('pit_token')[:50] if data.get('pit_token') else '❌ MISSING'}")
    print()
    print("STATUS:")
    print(f"creation_status: {data.get('creation_status')}")
    print(f"automation_status: {data.get('automation_status')}")
    print(f"created_at: {data.get('created_at')}")
    print(f"updated_at: {data.get('updated_at')}")
    print("="*80)

    # Check if we can authenticate to get tokens
    if data.get('soma_ghl_email') and data.get('soma_ghl_password'):
        print("\n🔧 TRYING TO AUTHENTICATE AS soma_ghl_user...")
        import httpx
        import asyncio

        async def auth_test():
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://backend.leadconnectorhq.com/users/authenticate",
                    json={
                        "email": data.get('soma_ghl_email'),
                        "password": data.get('soma_ghl_password')
                    }
                )

                if response.status_code == 200:
                    auth_data = response.json()
                    print("✅ AUTHENTICATION SUCCESSFUL!")
                    print(f"firebase_token: {auth_data.get('firebase_token')[:50]}...")
                    print(f"access_token: {auth_data.get('access_token')[:50]}...")

                    # Offer to update database
                    print("\n💾 UPDATE DATABASE? (y/n)")
                    choice = input().lower()
                    if choice == 'y':
                        supabase.table('ghl_subaccounts').update({
                            'firebase_token': auth_data.get('firebase_token'),
                            'access_token': auth_data.get('access_token'),
                            'firebase_token_time': __import__('datetime').datetime.now().isoformat()
                        }).eq('firm_user_id', firm_user_id).eq('agent_id', 'SOL').execute()
                        print("✅ Database updated!")
                else:
                    print(f"❌ Authentication failed: {response.status_code}")
                    print(response.text)

        asyncio.run(auth_test())
else:
    print("❌ No record found for this user")
