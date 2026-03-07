"""
Test script for the new semantic search endpoint
Tests the /api/knowledge-base/search endpoint
"""

import asyncio
import httpx
import json

# Backend URL
BACKEND_URL = "http://localhost:8000"

# Test parameters
TEST_USER_ID = "61a0306e-2018-4c86-99f8-6287e12fd1ce"
TEST_AGENT_ID = "personal_assistant"  # Optional


async def test_semantic_search():
    """Test the semantic search endpoint"""
    
    print("=" * 70)
    print("Testing Semantic Search Endpoint")
    print("=" * 70)
    
    # Test query
    query = "What are the marketing strategies?"
    
    payload = {
        "query": query,
        "user_id": TEST_USER_ID,
        "agent_id": TEST_AGENT_ID,
        "limit": 5,
        "similarity_threshold": 0.0
    }
    
    print(f"\nQuery: {query}")
    print(f"User ID: {TEST_USER_ID}")
    print(f"Agent ID: {TEST_AGENT_ID}")
    print(f"\nSending request to: {BACKEND_URL}/api/knowledge-base/search")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{BACKEND_URL}/api/knowledge-base/search",
                json=payload
            )
            
            print(f"\nResponse Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n✅ Success!")
                print(f"Found {data['count']} results\n")
                
                for i, result in enumerate(data['results'], 1):
                    print(f"[{i}] Similarity: {result['similarity']*100:.1f}%")
                    print(f"    ID: {result['id']}")
                    print(f"    Agent: {result['agent_id']}")
                    print(f"    Category: {result['category']}")
                    print(f"    File: {result['file_name']}")
                    print(f"    Created: {result['created_at']}")
                    print(f"    Content Preview:")
                    print(f"    {'-' * 40}")
                    preview = result['document'][:200]
                    for line in preview.split('\n')[:5]:
                        print(f"    {line}")
                    print(f"    {'-' * 40}\n")
            else:
                print(f"\n❌ Error: {response.status_code}")
                print(f"Response: {response.text}")
                
    except Exception as e:
        print(f"\n❌ Request failed: {e}")
        import traceback
        traceback.print_exc()


async def test_multiple_queries():
    """Test multiple queries"""
    
    queries = [
        "What are the company's goals?",
        "Tell me about the product features",
        "What is the pricing strategy?",
        "Who are the target customers?",
    ]
    
    print("\n" + "=" * 70)
    print("Testing Multiple Queries")
    print("=" * 70)
    
    for query in queries:
        print(f"\n{'─' * 70}")
        print(f"Query: {query}")
        print(f"{'─' * 70}")
        
        payload = {
            "query": query,
            "user_id": TEST_USER_ID,
            "agent_id": TEST_AGENT_ID,
            "limit": 3,
            "similarity_threshold": 0.5
        }
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{BACKEND_URL}/api/knowledge-base/search",
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Found {data['count']} results")
                    
                    for i, result in enumerate(data['results'], 1):
                        print(f"  [{i}] {result['similarity']*100:.1f}% - {result['file_name']} ({result['category']})")
                else:
                    print(f"❌ Error: {response.status_code}")
                    
        except Exception as e:
            print(f"❌ Request failed: {e}")
        
        await asyncio.sleep(1)  # Rate limiting


if __name__ == "__main__":
    print("\n🚀 Starting Semantic Search Endpoint Tests\n")
    
    # Run single test
    asyncio.run(test_semantic_search())
    
    # Uncomment to test multiple queries
    # asyncio.run(test_multiple_queries())
    
    print("\n✅ Tests completed\n")
