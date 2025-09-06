#!/usr/bin/env python3
"""
Extract GHL tokens from browser console
Run this after logging into GHL to extract access and refresh tokens
"""

import json
from datetime import datetime

def save_tokens():
    """
    After running ghl_automation_complete.py and getting the PIT token,
    you can manually extract the access token from the browser console:
    
    1. Open Chrome DevTools (F12)
    2. Go to Network tab
    3. Look for any API request to GHL
    4. Check the Request Headers for Authorization: Bearer <token>
    5. Copy the token and run this script
    """
    
    print("GHL Token Extractor")
    print("="*50)
    print("\nThis script helps you save all GHL tokens after automation.")
    
    # Get PIT token (already saved by automation)
    try:
        with open("highlevel_token.txt", "r") as f:
            pit_token = f.read().strip()
        print(f"✅ Found PIT token: {pit_token}")
    except:
        pit_token = input("Enter the Private Integration Token (PIT): ").strip()
    
    print("\nTo get the access token:")
    print("1. Open Chrome DevTools (F12) in the GHL browser window")
    print("2. Go to Network tab")
    print("3. Look for any API request (refresh the page if needed)")
    print("4. Click on a request and check Headers → Request Headers")
    print("5. Find 'Authorization: Bearer <token>'")
    print("6. Copy the token after 'Bearer '")
    print()
    
    access_token = input("Enter the Access Token (or press Enter to skip): ").strip()
    if access_token.startswith("Bearer "):
        access_token = access_token.replace("Bearer ", "")
    
    refresh_token = input("Enter the Refresh Token (if available, or press Enter to skip): ").strip()
    
    # Calculate expiry (tokens typically expire in 1 hour)
    from datetime import timedelta
    token_expiry = datetime.now() + timedelta(hours=1)
    
    # Save all tokens
    tokens_data = {
        "timestamp": datetime.now().isoformat(),
        "location_id": "MdY4KL72E0lc7TqMm3H0",
        "tokens": {
            "private_integration_token": pit_token,
            "access_token": access_token if access_token else None,
            "refresh_token": refresh_token if refresh_token else None
        },
        "expiry": {
            "token_expires_at": token_expiry.isoformat(),
            "expires_in_seconds": 3600,
            "expires_in_readable": "1:00:00"
        }
    }
    
    # Save to JSON file
    with open("highlevel_tokens_complete.json", "w") as f:
        json.dump(tokens_data, f, indent=2)
    
    print("\n" + "="*80)
    print("ALL TOKENS SAVED")
    print("="*80)
    print(f"\n1. PIT Token: {pit_token}")
    if access_token:
        print(f"2. Access Token: {access_token[:20]}...")
    if refresh_token:
        print(f"3. Refresh Token: {refresh_token[:20]}...")
    print(f"\n4. Tokens expire at: {token_expiry.strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nTokens saved to: highlevel_tokens_complete.json")
    print("="*80)

if __name__ == "__main__":
    save_tokens()