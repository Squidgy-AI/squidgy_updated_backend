import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

firm_user_id = "fdd48dd5-dabe-426d-a861-416d0a6adc0f"

result = supabase.table('ghl_subaccounts').select('*').eq('firm_user_id', firm_user_id).eq('agent_id', 'SOL').execute()

if result.data:
    data = result.data[0]
    print("="*80)
    print("TOKEN STATUS CHECK:")
    print("="*80)
    print(f"automation_status: {data.get('automation_status')}")
    
    firebase_token = data.get('firebase_token')
    if firebase_token:
        print(f"✅ firebase_token: {firebase_token[:50]}... (length: {len(firebase_token)})")
        
        # Decode to verify user_id
        import base64, json
        parts = firebase_token.split('.')
        if len(parts) >= 2:
            payload = json.loads(base64.urlsafe_b64decode(parts[1] + '=='))
            print(f"✅ Token user_id: {payload.get('user_id')}")
            print(f"✅ Expected user_id: J0XySnQIvotmMEX4fkRY")
            if payload.get('user_id') == 'J0XySnQIvotmMEX4fkRY':
                print("🎉 CORRECT! Token belongs to soma_ghl_user!")
            else:
                print("❌ WRONG! Token belongs to different user!")
    else:
        print(f"❌ firebase_token: NULL")
    
    access_token = data.get('access_token')
    if access_token:
        print(f"✅ access_token: {access_token[:50]}... (length: {len(access_token)})")
    else:
        print(f"❌ access_token: NULL")
    
    print("="*80)
else:
    print("❌ No record found")
