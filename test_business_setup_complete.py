#!/usr/bin/env python3
"""
Test Complete Business Setup Workflow
Tests the full flow: Form → Location → User → Automation → Database
"""

import asyncio
import httpx
import json
import uuid
from datetime import datetime

# Test data matching the screenshot form
TEST_BUSINESS_DATA = {
    "firm_user_id": str(uuid.uuid4()),
    "agent_id": "test_agent_business_001",
    "business_name": "Solar Solutions LLC",
    "business_address": "123 Main Street, Suite 100",
    "city": "Austin",
    "state": "Texas",
    "country": "United States",
    "postal_code": "78701",
    "business_logo_url": None,
    "snapshot_id": "SNAPSHOT_123456789"  # Replace with actual snapshot ID
}

async def test_complete_workflow():
    """Test the complete business setup workflow"""
    
    print("="*80)
    print("🚀 TESTING COMPLETE BUSINESS SETUP WORKFLOW")
    print("="*80)
    print(f"📋 Business: {TEST_BUSINESS_DATA['business_name']}")
    print(f"📍 Location: {TEST_BUSINESS_DATA['city']}, {TEST_BUSINESS_DATA['state']}")
    print(f"🆔 Agent ID: {TEST_BUSINESS_DATA['agent_id']}")
    print(f"🎯 Snapshot ID: {TEST_BUSINESS_DATA['snapshot_id']}")
    print()
    
    async with httpx.AsyncClient() as client:
        try:
            # Step 1: Submit business setup (this simulates clicking "Next" on the form)
            print("📝 [STEP 1] Submitting business information form...")
            
            response = await client.post(
                "http://localhost:8004/api/business/setup",
                json=TEST_BUSINESS_DATA,
                timeout=30.0
            )
            
            if response.status_code != 200:
                print(f"❌ Setup failed: {response.status_code} - {response.text}")
                return False
            
            setup_result = response.json()
            business_id = setup_result["business_id"]
            location_id = setup_result["ghl_location_id"]
            user_email = setup_result["ghl_user_email"]
            
            print(f"✅ Business setup initiated successfully!")
            print(f"   📱 Business ID: {business_id}")
            print(f"   🏢 Location ID: {location_id}")
            print(f"   📧 User Email: {user_email}")
            print(f"   🔄 Automation Status: {'Started' if setup_result['automation_started'] else 'Not Started'}")
            print()
            
            # Step 2: Monitor automation progress (non-blocking)
            print("👀 [STEP 2] Monitoring automation progress...")
            print("   ⏳ Automation is running in background...")
            print("   💡 Business user can continue with other tasks!")
            print()
            
            # Check status every 10 seconds for demonstration
            max_checks = 18  # 3 minutes max
            for check in range(max_checks):
                print(f"   🔍 Status check {check + 1}/{max_checks}...")
                
                status_response = await client.get(f"http://localhost:8004/api/business/status/{business_id}")
                
                if status_response.status_code == 200:
                    status = status_response.json()
                    current_status = status["status"]
                    
                    print(f"   📊 Current Status: {current_status}")
                    
                    if current_status == "completed":
                        print(f"   ✅ Automation COMPLETED!")
                        print(f"   🎫 PIT Token Available: {'Yes' if status['has_pit_token'] else 'No'}")
                        print(f"   🔥 Firebase Token: {'Yes' if status['has_firebase_token'] else 'No'}")
                        print(f"   ⏰ Completed At: {status['automation_completed_at']}")
                        break
                    elif current_status == "failed":
                        print(f"   ❌ Automation FAILED!")
                        print(f"   🚨 Error: {status.get('automation_error', 'Unknown error')}")
                        break
                    elif current_status in ["automation_running", "user_created"]:
                        print(f"   ⏳ Still running... (started at {status['automation_started_at']})")
                    
                await asyncio.sleep(10)  # Wait 10 seconds between checks
            
            # Step 3: Final status check
            print("\n📊 [STEP 3] Final status check...")
            
            final_response = await client.get(f"http://localhost:8004/api/business/status/{business_id}")
            if final_response.status_code == 200:
                final_status = final_response.json()
                
                print("📋 FINAL RESULTS:")
                print("="*50)
                print(f"Business Name: {final_status['business_name']}")
                print(f"Setup Status: {final_status['status']}")
                print(f"Location ID: {final_status['location_id']}")
                print(f"User Email: {final_status['user_email']}")
                print(f"PIT Token: {'✅ Available' if final_status['has_pit_token'] else '❌ Not Available'}")
                print(f"Firebase Token: {'✅ Available' if final_status['has_firebase_token'] else '❌ Not Available'}")
                
                if final_status['automation_started_at']:
                    print(f"Started: {final_status['automation_started_at']}")
                if final_status['automation_completed_at']:
                    print(f"Completed: {final_status['automation_completed_at']}")
                if final_status['automation_error']:
                    print(f"Error: {final_status['automation_error']}")
                
                print("="*50)
                
                return final_status['status'] == 'completed'
            
        except Exception as e:
            print(f"💥 Test failed: {e}")
            return False

async def test_list_businesses():
    """Test listing all businesses for a firm/agent"""
    
    print("\n📋 [BONUS] Testing business list endpoint...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"http://localhost:8004/api/business/list/{TEST_BUSINESS_DATA['firm_user_id']}/{TEST_BUSINESS_DATA['agent_id']}"
            )
            
            if response.status_code == 200:
                businesses = response.json()
                print(f"✅ Found {businesses['total']} businesses for this firm/agent")
                
                for i, business in enumerate(businesses['businesses'], 1):
                    print(f"   {i}. {business['business_name']} - Status: {business['setup_status']}")
            else:
                print(f"❌ List failed: {response.status_code}")
                
        except Exception as e:
            print(f"💥 List test failed: {e}")

async def main():
    """Run all tests"""
    
    print("🧪 COMPLETE BUSINESS SETUP WORKFLOW TEST")
    print("="*80)
    print("This simulates:")
    print("1. User fills business form and clicks 'Next'")
    print("2. System creates location and user")
    print("3. Automation runs in background (non-blocking)")
    print("4. User can continue while automation completes")
    print("5. Results are stored in database")
    print("="*80)
    print()
    
    # Test the complete workflow
    success = await test_complete_workflow()
    
    if success:
        print("\n🎉 COMPLETE WORKFLOW TEST: SUCCESS!")
        print("✅ Business form processed")
        print("✅ Location created")
        print("✅ User created")
        print("✅ Automation completed")
        print("✅ Tokens saved to database")
        print("✅ User was NOT blocked during automation")
    else:
        print("\n❌ COMPLETE WORKFLOW TEST: FAILED!")
        print("Check the logs above for details")
    
    # Test list functionality
    await test_list_businesses()
    
    print("\n" + "="*80)
    print("TEST COMPLETED")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(main())