#!/usr/bin/env python3
"""
🔍 DEBUG SCRIPT FOR SUBACCOUNT AND USER CREATION
=================================================
Tests the complete flow from frontend to backend to identify the exact issue
"""

import asyncio
import httpx
import json
from datetime import datetime

# Backend URL
BACKEND_URL = "http://127.0.0.1:8000"  # Local backend
# BACKEND_URL = "https://squidgy-back-919bc0659e35.herokuapp.com"  # Production

def generate_unique_test_data():
    """Generate unique test data to avoid conflicts"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_suffix = timestamp[-6:]  # Last 6 digits
    
    return {
        "company_id": "lp2p1q27DrdGta1qGDJd",
        "snapshot_id": "bInwX5BtZM6oEepAsUwo",
        "agency_token": "pit-e3d8d384-00cb-4744-8213-b1ab06ae71fe",
        "subaccount_name": f"TestBusiness_{random_suffix}",
        "prospect_email": f"testbusiness+{random_suffix}@testdomain.com",
        "prospect_first_name": "Test",
        "prospect_last_name": f"Business_{random_suffix}",
        "phone": f"+1555{random_suffix}",
        "website": "https://test-business.com",
        "address": "123 Test Business St",
        "city": "Test City",
        "state": "CA",
        "country": "US",
        "postal_code": "90210",
        "timezone": "America/Los_Angeles",
        "allow_duplicate_contact": False,
        "allow_duplicate_opportunity": False,
        "allow_facebook_name_merge": True,
        "disable_contact_timezone": False
    }

async def test_subaccount_and_user_creation():
    """Test the complete subaccount and user creation flow"""
    
    print("🔍 DEBUGGING SUBACCOUNT AND USER CREATION")
    print("=" * 60)
    
    # Generate unique test data
    test_data = generate_unique_test_data()
    
    print(f"📋 Test Data Generated:")
    print(f"  Business Name: {test_data['subaccount_name']}")
    print(f"  Business Email: {test_data['prospect_email']}")
    print(f"  Phone: {test_data['phone']}")
    print(f"  Backend URL: {BACKEND_URL}")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            print("\n🚀 STEP 1: Making API call to create subaccount and users...")
            print(f"Endpoint: POST {BACKEND_URL}/api/ghl/create-subaccount-and-user")
            
            # Make the API call
            response = await client.post(
                f"{BACKEND_URL}/api/ghl/create-subaccount-and-user",
                json=test_data,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"\n📊 RESPONSE STATUS: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            
            # Get response text first
            response_text = response.text
            print(f"\n📄 RAW RESPONSE:")
            print(response_text)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"\n✅ SUCCESS RESPONSE:")
                    print(json.dumps(result, indent=2))
                    
                    # Check if location_id is properly passed
                    if "subaccount" in result:
                        location_id = result["subaccount"].get("location_id")
                        print(f"\n🔍 LOCATION ID ANALYSIS:")
                        print(f"  Sub-account Location ID: {location_id}")
                        
                        if "business_user" in result:
                            business_user = result["business_user"]
                            print(f"  Business User ID: {business_user.get('user_id')}")
                            print(f"  Business User Details: {business_user.get('details', {})}")
                        
                        if "soma_user" in result:
                            soma_user = result["soma_user"]
                            print(f"  Soma User ID: {soma_user.get('user_id')}")
                            print(f"  Soma User Details: {soma_user.get('details', {})}")
                    
                except json.JSONDecodeError as e:
                    print(f"❌ JSON DECODE ERROR: {e}")
                    
            elif response.status_code == 422:
                print(f"\n❌ VALIDATION ERROR (422):")
                try:
                    error_detail = response.json()
                    print(json.dumps(error_detail, indent=2))
                except:
                    print(response_text)
                    
            else:
                print(f"\n❌ HTTP ERROR {response.status_code}:")
                print(response_text)
                
                # Check if it's a "user already exists" error
                if "user already exists" in response_text.lower():
                    print(f"\n🔍 USER EXISTS ERROR DETECTED:")
                    print("This confirms the issue is with existing user email")
                    
        except httpx.TimeoutException:
            print(f"❌ TIMEOUT ERROR: Request took longer than 60 seconds")
        except httpx.ConnectError:
            print(f"❌ CONNECTION ERROR: Could not connect to {BACKEND_URL}")
            print("Make sure the backend server is running!")
        except Exception as e:
            print(f"❌ UNEXPECTED ERROR: {e}")
            print(f"Error type: {type(e)}")

async def test_backend_health():
    """Test if backend is accessible"""
    print("\n🏥 TESTING BACKEND HEALTH...")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{BACKEND_URL}/health")
            print(f"Health check: {response.status_code}")
            if response.status_code == 200:
                print("✅ Backend is accessible")
                return True
        except:
            pass
            
        # Try root endpoint
        try:
            response = await client.get(f"{BACKEND_URL}/")
            print(f"Root endpoint: {response.status_code}")
            if response.status_code == 200:
                print("✅ Backend is accessible via root")
                return True
        except Exception as e:
            print(f"❌ Backend not accessible: {e}")
            return False

async def main():
    """Main test function"""
    print("🔍 STARTING COMPREHENSIVE DEBUG TEST")
    print("=" * 60)
    
    # Test backend health first
    backend_accessible = await test_backend_health()
    
    if not backend_accessible:
        print("\n❌ Backend is not accessible. Please start the backend server:")
        print("   cd /Users/somasekharaddakula/CascadeProjects/SquidgyBackend")
        print("   python main.py")
        return
    
    # Run the main test
    await test_subaccount_and_user_creation()
    
    print(f"\n" + "=" * 60)
    print("🏁 DEBUG TEST COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())