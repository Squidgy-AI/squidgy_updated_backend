#!/usr/bin/env python3
"""
Check expiry time of GHL access token
"""

import json
import base64
from datetime import datetime

def decode_jwt_token(token):
    """Decode JWT token to extract expiry information"""
    try:
        # JWT tokens have 3 parts separated by dots
        parts = token.split('.')
        if len(parts) != 3:
            print("Invalid JWT token format")
            return None
        
        # The payload is the second part
        payload_part = parts[1]
        
        # Add padding if needed (JWT uses URL-safe base64 without padding)
        padding = 4 - len(payload_part) % 4
        if padding != 4:
            payload_part += '=' * padding
        
        # Decode the payload
        payload_json = base64.urlsafe_b64decode(payload_part)
        payload = json.loads(payload_json)
        
        print("JWT Token Payload:")
        print(json.dumps(payload, indent=2))
        
        # Extract expiry time
        if 'exp' in payload:
            exp_timestamp = payload['exp']
            exp_datetime = datetime.fromtimestamp(exp_timestamp)
            
            print(f"\nToken Expiry Information:")
            print(f"Expires at: {exp_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Expires timestamp: {exp_timestamp}")
            print(f"Time remaining: {exp_datetime - datetime.now()}")
            
            if 'iat' in payload:
                iat_timestamp = payload['iat']
                iat_datetime = datetime.fromtimestamp(iat_timestamp)
                print(f"\nIssued at: {iat_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Token lifetime: {exp_datetime - iat_datetime}")
        else:
            print("No expiry information found in token")
            
    except Exception as e:
        print(f"Error decoding token: {e}")

# Read the token from the saved file
try:
    with open("highlevel_tokens_complete.json", "r") as f:
        data = json.load(f)
        access_token = data['tokens']['access_token']
        
    if access_token:
        print("Analyzing access token from highlevel_tokens_complete.json")
        print("="*60)
        decode_jwt_token(access_token)
    else:
        print("No access token found in highlevel_tokens_complete.json")
except Exception as e:
    print(f"Error reading token file: {e}")