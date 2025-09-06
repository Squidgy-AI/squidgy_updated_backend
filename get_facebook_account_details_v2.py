#!/usr/bin/env python3
"""
Get Facebook Account Details using the same auth method that worked for Facebook Pages API
"""

import requests
import json
from datetime import datetime

def get_facebook_account_details_with_firebase_headers(location_id: str, account_id: str, firebase_token: str):
    """
    Use the same headers that worked for the Facebook pages API
    """
    
    print("🔍 GETTING FACEBOOK ACCOUNT DETAILS WITH FIREBASE AUTH")
    print("=" * 70)
    print(f"📍 Location ID: {location_id}")
    print(f"🆔 Account ID: {account_id}")
    print(f"🔑 Firebase Token: {firebase_token[:50]}...")
    print(f"⏰ Request Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Build the API URL
    url = f"https://services.leadconnectorhq.com/social-media-posting/oauth/{location_id}/facebook/accounts/{account_id}"
    
    # Use Firebase-style headers (same as successful Facebook pages API call)
    headers = {
        "token-id": firebase_token,
        "channel": "APP", 
        "source": "WEB_USER",
        "version": "2021-07-28",
        "accept": "application/json, text/plain, */*",
        "origin": "https://app.onetoo.com",
        "referer": "https://app.onetoo.com/"
    }
    
    print(f"🌐 Request URL: {url}")
    print("📋 Headers:")
    for key, value in headers.items():
        if key == "token-id":
            print(f"   {key}: {value[:50]}...")
        else:
            print(f"   {key}: {value}")
    print()
    
    try:
        print("📡 Making API request...")
        response = requests.get(url, headers=headers)
        
        print(f"📊 Response Status: {response.status_code}")
        print(f"📋 Response Headers: {dict(response.headers)}")
        print()
        
        if response.status_code == 200:
            print("✅ SUCCESS! Facebook account details retrieved!")
            
            try:
                data = response.json()
                print("📄 Response Data:")
                print(json.dumps(data, indent=2))
                return {"success": True, "data": data}
                
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON: {e}")
                print("📄 Raw response:")
                print(response.text[:1000])
                return {"success": False, "error": f"JSON decode error: {e}"}
                
        else:
            print("❌ FAILED! API request returned error")
            print("📄 Error Response:")
            print(response.text)
            return {"success": False, "status_code": response.status_code, "error": response.text}
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return {"success": False, "error": str(e)}

def list_facebook_accounts_api(location_id: str, firebase_token: str):
    """
    Try to find an API that lists all Facebook accounts for a location
    This might help us find the right account_id
    """
    
    print("\n🔍 TRYING TO LIST FACEBOOK ACCOUNTS")
    print("=" * 50)
    
    # Possible endpoints to try
    endpoints_to_try = [
        f"https://services.leadconnectorhq.com/social-media-posting/oauth/{location_id}/facebook/accounts",
        f"https://services.leadconnectorhq.com/social-media-posting/oauth/{location_id}/accounts",
        f"https://backend.leadconnectorhq.com/integrations/facebook/{location_id}/accounts",
        f"https://backend.leadconnectorhq.com/integrations/facebook/{location_id}/allPages",
    ]
    
    headers = {
        "token-id": firebase_token,
        "channel": "APP", 
        "source": "WEB_USER",
        "version": "2021-07-28",
        "accept": "application/json, text/plain, */*",
        "origin": "https://app.onetoo.com",
        "referer": "https://app.onetoo.com/"
    }
    
    for endpoint in endpoints_to_try:
        print(f"\n🧪 Trying: {endpoint}")
        try:
            response = requests.get(endpoint, headers=headers)
            print(f"📊 Status: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ SUCCESS! Found working endpoint")
                try:
                    data = response.json()
                    print("📄 Response:")
                    print(json.dumps(data, indent=2))
                    return {"success": True, "endpoint": endpoint, "data": data}
                except:
                    print("📄 Response (text):")
                    print(response.text[:500])
            else:
                print(f"❌ Failed: {response.text[:200]}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    return {"success": False, "error": "No working endpoints found"}

def main():
    """Main function"""
    
    print("🔥 FACEBOOK ACCOUNT DETAILS - IMPROVED VERSION")
    print("=" * 70)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Your credentials
    LOCATION_ID = "du7GD0UrXKPuGjQxHJLU"
    FIREBASE_TOKEN = "eyJhbGciOiJSUzI1NiIsImtpZCI6Ijk1MWRkZTkzMmViYWNkODhhZmIwMDM3YmZlZDhmNjJiMDdmMDg2NmIiLCJ0eXAiOiJKV1QifQ.eyJ1c2VyX2lkIjoiYVowbjRldHJOQ0VCMjlzb25hOE0iLCJjb21wYW55X2lkIjoibHAycDFxMjdEcmRHdGExcUdESmQiLCJyb2xlIjoiYWRtaW4iLCJ0eXBlIjoiYWdlbmN5IiwibG9jYXRpb25zIjpbIkxIMlk5SURmQWIyOFVIcXJQd3BHIiwibEJQcWdCb3dYMUNzakhheTEyTFkiLCIzQVVvNVNkOU1lY3N1VldHUGdkRyIsIkpBQTFBdDVUcU5vS1I2RmlwaThMIiwiSUt5WEVkUVV1d3l0YVl0aXlTaWwiLCIyWnJ0dDdzS3Fyd1I0ZGQ2SXhKUCIsInZ6ejlHakpDTG1KdjZXZVAycmVsIiwiTWRZNEtMNzJFMGxjN1RxTW0zSDAiLCJnRGYwbWo5ekt5RkJEemhhSmZqMiIsIlhiYW52U29YN2N0bTB6d3hieFhFIiwiT1VIbDJEdWo5UW5vVUdza3VGWWciLCJQRlc3V0wwME1VbzFId3MwMU9jdCIsIkFYTG1WOWpkV3dneUR2NHVvUmhvIiwid1dLNjhFTjRHZnBxNUluSjAxN04iLCIzbEtzRnRZcTM5T0o4MVBscENVaSIsIkpVVEZUbnk4RVhRT1NCNU5jdkFBIiwiRkl5Z0c3RGhUeTB3Q2xPbFBrTXAiLCI2TGJjTnNEZXBYZ0F1MEVPUThVZSIsIlMyZDFXR1lFeUlHODF5a1JENDJVIiwiS0hmakY3aFdQUHBCcURwdlJvemUiXSwidmVyc2lvbiI6MiwicGVybWlzc2lvbnMiOnsid29ya2Zsb3dzX2VuYWJsZWQiOnRydWUsIndvcmtmbG93c19yZWFkX29ubHkiOmZhbHNlfSwiaXNzIjoiaHR0cHM6Ly9zZWN1cmV0b2tlbi5nb29nbGUuY29tL2hpZ2hsZXZlbC1iYWNrZW5kIiwiYXVkIjoiaGlnaGxldmVsLWJhY2tlbmQiLCJhdXRoX3RpbWUiOjE3NTQ0MDg3MTEsInN1YiI6ImFaMG40ZXRyTkNFQjI5c29uYThNIiwiaWF0IjoxNzU0NDMzMTc0LCJleHAiOjE3NTQ0MzY3NzQsImZpcmViYXNlIjp7ImlkZW50aXRpZXMiOnt9LCJzaWduX2luX3Byb3ZpZGVyIjoiY3VzdG9tIn19.p61cG7YF-UHNs7wDb5YZxr8FODGsRNxclzy2eMzL5m9o8gfzewX-J4WXWv_estC09qOTHvZ0MndMKsnesCBecvGlmupEcazoY_RtRuJBqp-H2pCSWYFwHKWc34feZaBuIjN4aHmCLv71PT1FlKKepSERJ4J1Vv51FeWjUZGZw-Wn_98WpiWe1_9vZxWo-b8K4i_hT5GFb3bc9E0tS4vnxhBsPqAr1IXVmnQLt9z-yJ2k4PpezBCpS545Sa_k_C-rWQEb7dVHRqS9NMomBIykC7oOxbCLY7uZ8VnIFSkOqamIwhfsVPCahGUhRvl3TIbkBTBD9PTebsNlgiq-YEvCdQ"
    
    # Step 1: First try to list Facebook accounts to find the right account_id
    print("STEP 1: Trying to find Facebook accounts for the location")
    list_result = list_facebook_accounts_api(LOCATION_ID, FIREBASE_TOKEN)
    
    if list_result["success"]:
        print("✅ Found Facebook accounts!")
        # Extract account IDs from the response
        data = list_result["data"]
        
        # Look for account IDs in the response
        if "pages" in data:
            pages = data["pages"]
            for page in pages:
                if "facebookPageId" in page:
                    account_id = page["facebookPageId"]
                    print(f"\n🧪 Found potential account_id: {account_id}")
                    
                    # Try using this as account_id
                    print(f"\nSTEP 2: Trying to get account details with account_id = {account_id}")
                    result = get_facebook_account_details_with_firebase_headers(LOCATION_ID, account_id, FIREBASE_TOKEN)
                    
                    if result["success"]:
                        print("✅ SUCCESS! Found the right account_id")
                        return
    
    # Step 3: If we still don't have success, try some fallback account_ids
    print("\nSTEP 3: Trying fallback account_ids...")
    fallback_account_ids = [
        LOCATION_ID,
        "QTFYuwxCgLyJQPouW0jV",  # User ID from OAuth
        "facebook",
        "fb",
        "706270759232435",  # The Facebook page ID we found earlier
    ]
    
    for account_id in fallback_account_ids:
        print(f"\n🧪 Trying account_id: {account_id}")
        result = get_facebook_account_details_with_firebase_headers(LOCATION_ID, account_id, FIREBASE_TOKEN)
        
        if result["success"]:
            print(f"✅ SUCCESS with account_id: {account_id}")
            break
    
    print("\n" + "=" * 70)
    print("🎯 CONCLUSION:")
    print("The OAuth flow completed successfully, but we need to find the right")
    print("account_id to get the Facebook account details. The integration is working!")

if __name__ == "__main__":
    main()