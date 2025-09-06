#!/usr/bin/env python3
"""
🧪 FACEBOOK INTEGRATION TEST
============================
Test the Facebook integration endpoints
"""

import asyncio
import httpx
import json
from datetime import datetime

async def test_facebook_integration():
    """Test the Facebook integration endpoints"""
    
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Facebook Integration Endpoints")
    print("=" * 50)
    
    # Test 1: Health check
    print("\n📡 TEST 1: Health Check")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{base_url}/api/facebook/oauth-health")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            
            if response.status_code == 200:
                print("✅ Health check passed")
            else:
                print("❌ Health check failed")
                
        except Exception as e:
            print(f"❌ Health check error: {e}")
    
    # Test 2: Start integration
    print("\n📡 TEST 2: Start Facebook Integration")
    integration_request = {
        "location_id": "test_location_123",
        "user_id": "test_user_456",
        "email": "test@example.com",
        "password": "test_password",
        "firm_user_id": "firm_test_789",
        "enable_2fa_bypass": True
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{base_url}/api/facebook/integrate",
                json=integration_request
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            
            if response.status_code == 200:
                print("✅ Integration started successfully")
            else:
                print("❌ Integration failed to start")
                
        except Exception as e:
            print(f"❌ Integration error: {e}")
    
    # Test 3: Check status
    print("\n📡 TEST 3: Check Integration Status")
    await asyncio.sleep(2)  # Wait a bit for processing
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{base_url}/api/facebook/integration-status/test_location_123")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            
            if response.status_code == 200:
                print("✅ Status check passed")
            else:
                print("❌ Status check failed")
                
        except Exception as e:
            print(f"❌ Status check error: {e}")
    
    # Test 4: Connect page
    print("\n📡 TEST 4: Connect Facebook Page")
    connect_request = {
        "location_id": "test_location_123",
        "page_id": "test_page_456"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{base_url}/api/facebook/connect-page",
                json=connect_request
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            
            if response.status_code == 200:
                print("✅ Page connection test passed")
            else:
                print("❌ Page connection test failed")
                
        except Exception as e:
            print(f"❌ Page connection error: {e}")
    
    print("\n🎉 Facebook Integration Tests Complete!")

if __name__ == "__main__":
    try:
        asyncio.run(test_facebook_integration())
    except KeyboardInterrupt:
        print("\n👋 Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test error: {e}")