#!/usr/bin/env python3
"""
Debug the specific issue with WebSocket message processing
"""

import asyncio
import logging
import os
import json
from datetime import datetime

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import the required components
from main import conversational_handler

async def test_conversational_handler():
    """Test the conversational handler directly"""
    
    print("🔍 Testing ConversationalHandler.handle_message directly")
    print("=" * 60)
    
    # Test data matching what WebSocket sends
    test_request_data = {
        "user_id": "debug_user",
        "user_mssg": "Hello, I need help with social media marketing",
        "session_id": "debug_session",
        "agent_name": "socialmediakb",
        "timestamp_of_call_made": datetime.now().isoformat()
    }
    
    print(f"Request data: {json.dumps(test_request_data, indent=2)}")
    print("\n🚀 Calling conversational_handler.handle_message...")
    
    try:
        # Call the same method that's failing in WebSocket
        response = await conversational_handler.handle_message(test_request_data)
        
        print(f"✅ SUCCESS! Response received:")
        print(f"Response: {json.dumps(response, indent=2)}")
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        print(f"Traceback:\n{traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_conversational_handler())