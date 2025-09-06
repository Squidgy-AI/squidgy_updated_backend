#!/usr/bin/env python3
"""
Debug the WebSocket task directly without WebSocket connection
"""

import asyncio
import logging
import json
from datetime import datetime
from unittest.mock import AsyncMock

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import the required components
from main import process_websocket_message_with_n8n

# Create a mock WebSocket for testing
class MockWebSocket:
    def __init__(self):
        self.sent_messages = []
    
    async def send_json(self, data):
        print(f"📤 WebSocket would send: {json.dumps(data, indent=2)}")
        self.sent_messages.append(data)

async def test_websocket_processing():
    """Test the WebSocket processing function directly"""
    
    print("🔍 Testing process_websocket_message_with_n8n directly")
    print("=" * 60)
    
    # Create mock WebSocket
    mock_websocket = MockWebSocket()
    
    # Test data matching what WebSocket sends
    test_request_data = {
        "user_id": "debug_user",
        "user_mssg": "Hello, I need help with social media marketing",
        "session_id": "debug_session",
        "agent_name": "socialmediakb",
        "timestamp_of_call_made": datetime.now().isoformat()
    }
    
    request_id = "test_request_001"
    
    print(f"Request data: {json.dumps(test_request_data, indent=2)}")
    print(f"Request ID: {request_id}")
    print("\n🚀 Calling process_websocket_message_with_n8n...")
    
    try:
        # Call the exact function that's used in WebSocket handler
        await process_websocket_message_with_n8n(test_request_data, mock_websocket, request_id)
        
        print(f"✅ Task completed successfully!")
        print(f"📨 Messages sent via WebSocket: {len(mock_websocket.sent_messages)}")
        
        for i, msg in enumerate(mock_websocket.sent_messages):
            print(f"   Message {i+1}: {msg.get('type', 'unknown')} - {msg.get('message', msg.get('error', 'no message'))}")
        
    except Exception as e:
        print(f"❌ Task failed with error: {str(e)}")
        import traceback
        print(f"Traceback:\n{traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_websocket_processing())