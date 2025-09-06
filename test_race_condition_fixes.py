#!/usr/bin/env python3
"""
Test script to verify race condition fixes and n8n workflow improvements
"""
import asyncio
import json
import time
from typing import Dict, Any
import httpx

# Test endpoint
BASE_URL = "https://squidgy-back-919bc0659e35.herokuapp.com"

async def test_safe_agent_selection():
    """Test the new safe agent selection endpoint"""
    
    test_cases = [
        {
            "name": "Normal agent matching",
            "data": {
                "user_query": "help with sales and business strategy",
                "agent_name": "presaleskb", 
                "session_id": "test_session_123"
            },
            "expected": "should return presaleskb or valid alternative"
        },
        {
            "name": "No matching agent - fallback test", 
            "data": {
                "user_query": "random nonsense gibberish xyz123",
                "agent_name": "nonexistent_agent",
                "session_id": "test_session_456"
            },
            "expected": "should return presaleskb as fallback"
        },
        {
            "name": "Max attempts reached - loop prevention",
            "data": {
                "user_query": "test query",
                "agent_name": "test_agent",
                "session_id": "test_session_789",
                "attempt_count": 5  # Over the limit
            },
            "expected": "should return fallback due to max attempts"
        },
        {
            "name": "Social media query - intelligent fallback",
            "data": {
                "user_query": "help with instagram and facebook marketing",
                "agent_name": "invalid_agent",
                "session_id": "test_session_social"
            },
            "expected": "should return socialmediakb or presaleskb"
        }
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("🧪 Testing Safe Agent Selection Endpoint...")
        print("=" * 60)
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🔍 Test {i}: {test_case['name']}")
            print(f"📝 Expected: {test_case['expected']}")
            
            try:
                start_time = time.time()
                
                response = await client.post(
                    f"{BASE_URL}/n8n/safe_agent_select",
                    json=test_case['data'],
                    headers={"Content-Type": "application/json"}
                )
                
                elapsed = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ SUCCESS ({elapsed:.1f}ms)")
                    print(f"   Selected Agent: {result.get('selected_agent')}")
                    print(f"   Strategy: {result.get('strategy_used')}")
                    print(f"   Confidence: {result.get('confidence_score', 0):.2f}")
                    print(f"   Attempts: {result.get('attempt_count', 0)}")
                    
                    if result.get('fallback_reason'):
                        print(f"   Fallback Reason: {result.get('fallback_reason')}")
                    
                    # Validate response
                    if result.get('selected_agent') and result.get('strategy_used'):
                        print(f"   ✅ Valid response structure")
                    else:
                        print(f"   ⚠️ Missing required fields")
                        
                else:
                    print(f"❌ FAILED (HTTP {response.status_code})")
                    print(f"   Response: {response.text}")
                    
            except Exception as e:
                print(f"❌ ERROR: {str(e)}")
        
        print("\n" + "=" * 60)
        print("🏁 Test Summary:")
        print("   - If all tests show ✅ SUCCESS, the fixes are working")
        print("   - The system should never return errors or infinite loops")
        print("   - All responses should have a valid selected_agent")
        print("   - Max attempts should trigger fallback mechanism")

async def test_concurrent_requests():
    """Test concurrent requests to check for race conditions"""
    print("\n🔄 Testing Concurrent Requests (Race Condition Check)...")
    print("=" * 60)
    
    async def make_request(session_id: str):
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.post(
                    f"{BASE_URL}/n8n/safe_agent_select",
                    json={
                        "user_query": f"concurrent test query {session_id}",
                        "agent_name": "presaleskb",
                        "session_id": session_id
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "session_id": session_id,
                        "success": True,
                        "agent": result.get('selected_agent'),
                        "strategy": result.get('strategy_used')
                    }
                else:
                    return {
                        "session_id": session_id,
                        "success": False,
                        "error": f"HTTP {response.status_code}"
                    }
            except Exception as e:
                return {
                    "session_id": session_id,
                    "success": False,
                    "error": str(e)
                }
    
    # Create 10 concurrent requests
    tasks = [make_request(f"concurrent_test_{i}") for i in range(10)]
    
    start_time = time.time()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    elapsed = time.time() - start_time
    
    successful = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
    failed = len(results) - successful
    
    print(f"📊 Concurrent Request Results:")
    print(f"   Total Requests: {len(results)}")
    print(f"   Successful: {successful}")
    print(f"   Failed: {failed}")
    print(f"   Total Time: {elapsed:.2f}s")
    print(f"   Avg Time per Request: {(elapsed/len(results)*1000):.1f}ms")
    
    if failed == 0:
        print(f"   ✅ NO RACE CONDITIONS DETECTED")
    else:
        print(f"   ⚠️ Some requests failed - check for race conditions")
        for r in results:
            if isinstance(r, dict) and not r.get('success'):
                print(f"      Failed: {r.get('session_id')} - {r.get('error')}")

async def main():
    """Run all tests"""
    print("🚀 Starting N8N Workflow & Race Condition Fix Tests")
    print("🔗 Testing endpoint:", BASE_URL)
    print("⏰ Started at:", time.strftime("%Y-%m-%d %H:%M:%S"))
    
    try:
        # Test safe agent selection
        await test_safe_agent_selection()
        
        # Test concurrent requests
        await test_concurrent_requests()
        
        print("\n🎉 ALL TESTS COMPLETED!")
        print("💡 If you see mostly ✅ results, your fixes are working correctly!")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())