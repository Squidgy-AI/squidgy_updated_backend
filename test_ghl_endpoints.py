#!/usr/bin/env python3
"""
Test script for GHL subaccount and user creation endpoints
"""

import httpx
import asyncio
import json
from datetime import datetime

# Backend URL - adjust this based on your setup
BACKEND_URL = "http://localhost:8000"

# Test data - using environment variables in production
import os
from dotenv import load_dotenv

load_dotenv()

test_data = {
    "company_id": os.getenv("GHL_COMPANY_ID", "lp2p1q27DrdGta1qGDJd"),
    "snapshot_id": os.getenv("GHL_SNAPSHOT_ID", "bInwX5BtZM6oEepAsUwo"),  # SOL - Solar Assistant
    "agency_token": os.getenv("GHL_AGENCY_TOKEN", "pit-e3d8d384-00cb-4744-8213-b1ab06ae71fe")
}

async def test_create_subaccount():
    """Test the subaccount creation endpoint"""
    print("🧪 Testing GHL subaccount creation endpoint...")
    
    url = f"{BACKEND_URL}/api/ghl/create-subaccount"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=test_data, timeout=30.0)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Subaccount created successfully!")
            print(f"   Location ID: {result['location_id']}")
            print(f"   Name: {result['subaccount_name']}")
            return result['location_id']
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

async def test_create_user(location_id):
    """Test the user creation endpoint"""
    print("\n🧪 Testing GHL user creation endpoint...")
    
    url = f"{BACKEND_URL}/api/ghl/create-user"
    
    user_data = {
        "company_id": test_data["company_id"],
        "location_id": location_id,
        "agency_token": test_data["agency_token"]
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=user_data, timeout=30.0)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ User created successfully!")
            print(f"   User ID: {result['user_id']}")
            print(f"   Name: {result['details']['name']}")
            print(f"   Email: {result['details']['email']}")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

async def test_combined_endpoint():
    """Test the combined subaccount and user creation endpoint"""
    print("\n🧪 Testing combined GHL creation endpoint...")
    
    url = f"{BACKEND_URL}/api/ghl/create-subaccount-and-user"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=test_data, timeout=30.0)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Both subaccount and user created successfully!")
            print("\n📋 Subaccount Details:")
            print(f"   Location ID: {result['subaccount']['location_id']}")
            print(f"   Name: {result['subaccount']['subaccount_name']}")
            print("\n👤 User Details:")
            print(f"   User ID: {result['user']['user_id']}")
            print(f"   Name: {result['user']['details']['name']}")
            print(f"   Email: {result['user']['details']['email']}")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

async def main():
    print("🚀 GHL Endpoint Test Suite")
    print("=" * 50)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Test started at: {datetime.now().strftime('%I:%M:%S %p')}")
    print("=" * 50)
    
    # Test individual endpoints
    print("\n1️⃣ Testing individual endpoints:")
    location_id = await test_create_subaccount()
    
    if location_id:
        await test_create_user(location_id)
    
    # Test combined endpoint
    print("\n2️⃣ Testing combined endpoint:")
    await test_combined_endpoint()
    
    print("\n" + "=" * 50)
    print("✅ Test suite completed!")

if __name__ == "__main__":
    asyncio.run(main())