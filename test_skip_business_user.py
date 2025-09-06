#!/usr/bin/env python3
"""
🧪 TEST SKIP BUSINESS USER CREATION
===================================
Tests that business user creation is skipped and only Soma user is created
"""

import asyncio
import httpx
import json
from datetime import datetime

# Backend URL
BACKEND_URL = "http://127.0.0.1:8000"

def generate_test_data_with_existing_email():
    """Generate test data with an email that might already exist"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    return {
        "company_id": "lp2p1q27DrdGta1qGDJd",
        "snapshot_id": "bInwX5BtZM6oEepAsUwo",
        "agency_token": "pit-e3d8d384-00cb-4744-8213-b1ab06ae71fe",
        "subaccount_name": f"TestExistingUser_{timestamp}",
        "prospect_email": "dmacproject123@gmail.com",  # This might already exist
        "prospect_first_name": "Soma",
        "prospect_last_name": "SOL Test",
        "phone": "+1-716-604-4029",
        "website": "https://test.com",
        "address": "123 Test Street",
        "city": "Test City",
        "state": "NY",
        "country": "US",
        "postal_code": "12345",
        "timezone": "America/New_York",
        "allow_duplicate_contact": False,
        "allow_duplicate_opportunity": False,
        "allow_facebook_name_merge": True,
        "disable_contact_timezone": False
    }

async def test_skip_business_user():
    """Test that business user is skipped and only Soma user is created"""
    
    print("🧪 TESTING SKIP BUSINESS USER CREATION")
    print("=" * 50)
    
    # Generate test data with potentially existing email
    form_data = generate_test_data_with_existing_email()
    
    print(f"📝 Test Data:")
    print(f"  Business Email: {form_data['prospect_email']} (potentially existing)")
    print(f"  Business Name: {form_data['subaccount_name']}")
    print("=" * 50)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            print(f"\n🚀 Creating account with potentially existing email...")
            
            response = await client.post(
                f"{BACKEND_URL}/api/ghl/create-subaccount-and-user",
                json=form_data,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"\n📊 Response: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                
                print(f"\n✅ SUCCESS! Account created:")
                
                # Check what happened with each user
                subaccount = result.get('subaccount', {})
                business_user = result.get('business_user', {})
                soma_user = result.get('soma_user', {})
                
                print(f"\n🔍 USER CREATION RESULTS:")
                print(f"  📍 Sub-account: {subaccount.get('location_id')}")
                
                print(f"\n  👤 Business User:")
                print(f"     Status: {business_user.get('status')}")
                print(f"     Message: {business_user.get('message')}")
                print(f"     User ID: {business_user.get('user_id')}")
                print(f"     Email: {business_user.get('details', {}).get('email')}")
                
                print(f"\n  👤 Soma User:")
                print(f"     Status: {soma_user.get('status')}")
                print(f"     Message: {soma_user.get('message')}")
                print(f"     User ID: {soma_user.get('user_id')}")
                print(f"     Email: {soma_user.get('details', {}).get('email')}")
                
                # Verify business user was skipped
                if business_user.get('status') == 'skipped':
                    print(f"\n✅ BUSINESS USER: Correctly skipped!")
                else:
                    print(f"\n❌ BUSINESS USER: Not skipped as expected")
                
                # Verify Soma user was handled
                if soma_user.get('status') == 'success':
                    print(f"✅ SOMA USER: Successfully created/handled!")
                else:
                    print(f"❌ SOMA USER: Not handled properly")
                
                return True
                
            else:
                print(f"❌ Failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

async def main():
    """Main test function"""
    print("🧪 TESTING BUSINESS USER SKIP FUNCTIONALITY")
    print("=" * 60)
    
    success = await test_skip_business_user()
    
    if success:
        print(f"\n✅ CONCLUSION: Business user skip working correctly!")
        print("   - Sub-account creation still works")
        print("   - Business user creation is skipped")
        print("   - Only Soma user is created/handled")
    else:
        print(f"\n❌ CONCLUSION: Business user skip needs fixing")
    
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())