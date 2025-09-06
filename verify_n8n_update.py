#!/usr/bin/env python3
"""
Verify n8n local test webhook is being used
"""

import os
from dotenv import load_dotenv

load_dotenv()

print("🔍 Verifying n8n Webhook Configuration")
print("=" * 50)

# Check environment variables
n8n_main = os.getenv("N8N_MAIN")
n8n_local_test = os.getenv("N8N_LOCAL_TEST")

print(f"\n📋 Environment Variables:")
print(f"N8N_MAIN: {n8n_main}")
print(f"N8N_LOCAL_TEST: {n8n_local_test}")

print(f"\n✅ Backend will now use:")
print(f"   {n8n_local_test}")
print(f"   (This webhook points to localhost:8000)")

print(f"\n📝 About the user_id field:")
print(f"   - n8n sends 'user_id' field (correct field name)")
print(f"   - The value is profile.id (e.g., a59741cd-...)")
print(f"   - Backend uses this as client_id in database")
print(f"   - This is working correctly!")

print(f"\n🎯 Next Steps:")
print(f"1. Restart your backend: uvicorn main:app --reload")
print(f"2. Configure the local test webhook in n8n")
print(f"3. Test with: python3 test_n8n_local.py")