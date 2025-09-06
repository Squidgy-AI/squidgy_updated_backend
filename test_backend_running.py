#!/usr/bin/env python3
"""
Test if backend is running with updated code
"""

import asyncio
import websockets
import json
import requests
import time

def test_backend_health():
    """Test backend health and version"""
    print("🏥 Testing Backend Health")
    print("=" * 30)
    
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Backend is running")
            print(f"   Status: {data.get('status', 'unknown')}")
            print(f"   Active Connections: {data.get('active_connections', 0)}")
            return True
        else:
            print(f"❌ Backend error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend not reachable: {e}")
        return False

async def test_websocket_with_logging():
    """Test WebSocket with enhanced logging"""
    print("\n🔌 Testing WebSocket Connection")
    print("=" * 35)
    
    uri = "ws://localhost:8000/ws/test_debug/session_debug"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connected")
            
            # Get connection message
            response = await websocket.recv()
            data = json.loads(response)
            print(f"📡 {data.get('message', 'Connected')}")
            
            # Send test message
            test_msg = {
                "message": "test message to trigger n8n",
                "agent": "socialmediakb",
                "requestId": f"debug_{int(time.time())}"
            }
            
            print(f"\n📤 Sending: '{test_msg['message']}'")
            await websocket.send(json.dumps(test_msg))
            
            # Listen for responses with timeout
            responses = []
            for i in range(5):  # Try 5 times
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    data = json.loads(response)
                    responses.append(data)
                    
                    msg_type = data.get('type', 'unknown')
                    print(f"📨 Response {i+1}: {msg_type}")
                    
                    if msg_type == 'response':
                        print("   🎉 SUCCESS: Got response from n8n!")
                        return True
                    elif msg_type == 'error':
                        print(f"   ❌ ERROR: {data.get('error', 'Unknown')}")
                        return False
                    elif msg_type == 'ack':
                        print("   ✅ Message acknowledged, waiting for processing...")
                    elif msg_type == 'ping':
                        await websocket.send(json.dumps({"type": "pong", "timestamp": int(time.time() * 1000)}))
                        print("   🏓 Ping/pong")
                        
                except asyncio.TimeoutError:
                    print(f"   ⏰ Timeout {i+1}/5")
                    
            print("\n📋 All responses received:")
            for i, resp in enumerate(responses, 1):
                print(f"   {i}. {resp.get('type', 'unknown')}: {resp}")
                
            return False
            
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        return False

def test_direct_n8n():
    """Test direct n8n call"""
    print("\n🔗 Testing Direct n8n Call")
    print("=" * 30)
    
    n8n_url = "https://n8n.theaiteam.uk/webhook/c2fcbad6-abc0-43af-8aa8-d1661ff4461d"
    
    payload = {
        "user_id": "direct_test",
        "user_mssg": "direct test message",
        "session_id": "direct_session",
        "agent_name": "socialmediakb"
    }
    
    try:
        response = requests.post(n8n_url, json=payload, timeout=10)
        print(f"📊 Status: {response.status_code}")
        print(f"📄 Content Length: {len(response.content)}")
        print(f"📝 Content: '{response.text[:100]}'")
        
        if response.status_code == 200 and response.text.strip():
            print("✅ n8n returns data")
            return True
        else:
            print("⚠️ n8n returns empty/error")
            return False
            
    except Exception as e:
        print(f"❌ n8n call failed: {e}")
        return False

async def main():
    print("🧪 BACKEND INTEGRATION DIAGNOSIS")
    print("=" * 50)
    
    # Test each component
    backend_ok = test_backend_health()
    
    if backend_ok:
        websocket_ok = await test_websocket_with_logging()
    else:
        websocket_ok = False
        
    n8n_ok = test_direct_n8n()
    
    print("\n🎯 DIAGNOSIS SUMMARY")
    print("=" * 25)
    print(f"Backend Health: {'✅' if backend_ok else '❌'}")
    print(f"WebSocket Flow: {'✅' if websocket_ok else '❌'}")
    print(f"n8n Direct Call: {'✅' if n8n_ok else '❌'}")
    
    if not websocket_ok and backend_ok:
        print("\n🔧 LIKELY ISSUES:")
        if not n8n_ok:
            print("- n8n workflow not returning data")
            print("- Add 'Respond to Webhook' node in n8n")
        print("- Backend async task failing silently")
        print("- Check backend server console for errors")

if __name__ == "__main__":
    asyncio.run(main())