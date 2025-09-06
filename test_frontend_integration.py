#!/usr/bin/env python3
"""
Test frontend integration - simulate the exact call the frontend will make
"""

import httpx
import asyncio
import json

async def test_frontend_call():
    """Test the exact call that the frontend will make"""
    print("🧪 Testing Frontend Integration Call...")
    print("=" * 50)
    
    # This is the exact payload the frontend will send
    frontend_payload = {
        "company_id": "lp2p1q27DrdGta1qGDJd",
        "snapshot_id": "bInwX5BtZM6oEepAsUwo",  # SOL - Solar Assistant snapshot
        "agency_token": "pit-e3d8d384-00cb-4744-8213-b1ab06ae71fe"
    }
    
    # Backend URL (same as frontend will use)
    backend_url = "http://localhost:8000"
    
    try:
        async with httpx.AsyncClient() as client:
            print("📡 Making request to:", f"{backend_url}/api/ghl/create-subaccount-and-user")
            print("📦 Payload:", json.dumps(frontend_payload, indent=2))
            
            response = await client.post(
                f"{backend_url}/api/ghl/create-subaccount-and-user",
                json=frontend_payload,
                headers={"Content-Type": "application/json"},
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                print("\n✅ Frontend integration test SUCCESSFUL!")
                print("\n📋 Response that frontend will receive:")
                print(json.dumps(result, indent=2))
                
                # Verify the structure the frontend expects
                required_fields = [
                    "status", "message", "subaccount", "user", "created_at"
                ]
                
                missing_fields = [field for field in required_fields if field not in result]
                
                if not missing_fields:
                    print("\n✅ Response structure is correct for frontend!")
                else:
                    print(f"\n⚠️  Missing fields: {missing_fields}")
                    
                return True
            else:
                print(f"\n❌ Failed: {response.status_code}")
                print(f"Error: {response.text}")
                return False
                
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False

async def main():
    print("🚀 Frontend Integration Test")
    print("This simulates the exact call the ProgressiveSOLSetup component will make")
    
    success = await test_frontend_call()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Frontend integration is ready!")
        print("\n📝 What happens in the frontend:")
        print("1. User completes Solar + Calendar + Notification setup")
        print("2. Frontend calls our combined endpoint")
        print("3. GHL sub-account and user are created")
        print("4. Success message appears in chat")
    else:
        print("❌ Frontend integration needs fixing")

if __name__ == "__main__":
    asyncio.run(main())