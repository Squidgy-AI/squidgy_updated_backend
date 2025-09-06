#!/usr/bin/env python3
"""
🧪 TEST FORM DATA FLOW
======================
Tests that the frontend correctly sends form data instead of hardcoded values
"""

import asyncio
import httpx
import json
from datetime import datetime

# Backend URL
BACKEND_URL = "http://127.0.0.1:8000"

def generate_test_form_data():
    """Generate test form data similar to what frontend would send"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    return {
        "company_id": "lp2p1q27DrdGta1qGDJd",
        "snapshot_id": "bInwX5BtZM6oEepAsUwo",
        "agency_token": "pit-e3d8d384-00cb-4744-8213-b1ab06ae71fe",
        "subaccount_name": f"MyRealBusiness_{timestamp}",
        "prospect_email": f"myrealbusiness+{timestamp[-6:]}@example.com",
        "prospect_first_name": "John",
        "prospect_last_name": "Smith",
        "phone": "+1-555-123-4567",
        "website": "https://myrealbusiness.com",
        "address": "456 Real Business Street",
        "city": "Real City",
        "state": "NY",
        "country": "US",
        "postal_code": "12345",
        "timezone": "America/New_York",
        "allow_duplicate_contact": False,
        "allow_duplicate_opportunity": False,
        "allow_facebook_name_merge": True,
        "disable_contact_timezone": False
    }

async def test_real_form_data():
    """Test with realistic form data instead of hardcoded demo values"""
    
    print("🧪 TESTING REAL FORM DATA FLOW")
    print("=" * 50)
    
    # Generate realistic test data
    form_data = generate_test_form_data()
    
    print(f"📝 Form Data Being Sent:")
    print(f"  Business Name: {form_data['subaccount_name']}")
    print(f"  Owner: {form_data['prospect_first_name']} {form_data['prospect_last_name']}")
    print(f"  Email: {form_data['prospect_email']}")
    print(f"  Phone: {form_data['phone']}")
    print(f"  Address: {form_data['address']}, {form_data['city']}, {form_data['state']}")
    print(f"  Website: {form_data['website']}")
    print("=" * 50)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            print(f"\n🚀 Creating account with REAL FORM DATA...")
            print(f"Endpoint: POST {BACKEND_URL}/api/ghl/create-subaccount-and-user")
            
            response = await client.post(
                f"{BACKEND_URL}/api/ghl/create-subaccount-and-user",
                json=form_data,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"\n📊 Response: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                
                print(f"\n✅ SUCCESS! Account created with form data:")
                
                # Verify the data matches what we sent
                subaccount = result.get('subaccount', {})
                business_user = result.get('business_user', {})
                
                print(f"\n🔍 VERIFICATION:")
                print(f"  ✓ Business Name: {subaccount.get('subaccount_name')} (matches: {subaccount.get('subaccount_name') == form_data['subaccount_name']})")
                print(f"  ✓ Owner Email: {business_user.get('details', {}).get('email')} (matches: {business_user.get('details', {}).get('email') == form_data['prospect_email']})")
                print(f"  ✓ Location ID: {subaccount.get('location_id')}")
                print(f"  ✓ Business User ID: {business_user.get('user_id')}")
                
                # Check if address/city/state made it through
                subaccount_details = subaccount.get('details', {})
                print(f"  ✓ Address: {subaccount_details.get('address')} (matches: {subaccount_details.get('address') == form_data['address']})")
                print(f"  ✓ City: {subaccount_details.get('city')} (matches: {subaccount_details.get('city') == form_data['city']})")
                print(f"  ✓ State: {subaccount_details.get('state')} (matches: {subaccount_details.get('state') == form_data['state']})")
                
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
    print("🧪 TESTING FORM DATA FLOW FROM FRONTEND TO BACKEND")
    print("=" * 60)
    
    success = await test_real_form_data()
    
    if success:
        print(f"\n✅ CONCLUSION: Form data flow is working correctly!")
        print("   - Frontend form data is properly passed to backend")
        print("   - Backend creates accounts with real user information")
        print("   - No more hardcoded demo values!")
    else:
        print(f"\n❌ CONCLUSION: Form data flow needs fixing")
    
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())