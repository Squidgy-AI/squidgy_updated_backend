#!/usr/bin/env python3
"""
Get Facebook Account Details after OAuth completion
Uses GHL's Social Media Posting API to fetch connected Facebook pages
"""

import requests
import json
from datetime import datetime

def get_facebook_account_details(location_id: str, account_id: str, access_token: str):
    """
    Get Facebook account details and pages after OAuth completion
    
    Args:
        location_id: GHL Location ID
        account_id: Facebook Account ID (from OAuth callback)
        access_token: GHL Access Token (Bearer token)
    """
    
    print("🔍 GETTING FACEBOOK ACCOUNT DETAILS")
    print("=" * 60)
    print(f"📍 Location ID: {location_id}")
    print(f"🆔 Account ID: {account_id}")
    print(f"🔑 Access Token: {access_token[:20]}...")
    print(f"⏰ Request Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Build the API URL
    url = f"https://services.leadconnectorhq.com/social-media-posting/oauth/{location_id}/facebook/accounts/{account_id}"
    
    # Headers as per API documentation
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Version": "2021-07-28",
        "Accept": "application/json"
    }
    
    print(f"🌐 Request URL: {url}")
    print("📋 Headers:")
    for key, value in headers.items():
        if key == "Authorization":
            print(f"   {key}: Bearer {value.split(' ')[1][:20]}...")
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
                
                # Parse and display the results
                if data.get("success") and "results" in data:
                    results = data["results"]
                    pages = results.get("pages", [])
                    
                    print(f"\n🎉 FACEBOOK ACCOUNT SUMMARY:")
                    print(f"   ✅ Success: {data.get('success')}")
                    print(f"   📊 Status Code: {data.get('statusCode')}")
                    print(f"   💬 Message: {data.get('message')}")
                    print(f"   📄 Total Pages: {len(pages)}")
                    print()
                    
                    if pages:
                        print("📄 CONNECTED FACEBOOK PAGES:")
                        print("-" * 40)
                        for i, page in enumerate(pages, 1):
                            print(f"   📄 Page {i}:")
                            print(f"      🆔 ID: {page.get('id', 'N/A')}")
                            print(f"      📝 Name: {page.get('name', 'N/A')}")
                            print(f"      🖼️  Avatar: {page.get('avatar', 'N/A')}")
                            print(f"      👤 Is Owned: {page.get('isOwned', False)}")
                            print(f"      🔗 Is Connected: {page.get('isConnected', False)}")
                            print()
                    else:
                        print("⚠️  No Facebook pages found in the response")
                
                return {
                    "success": True,
                    "data": data,
                    "pages": pages if 'pages' in locals() else []
                }
                
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON response: {e}")
                print("📄 Raw response:")
                print(response.text[:1000])
                
                return {
                    "success": False,
                    "error": f"JSON decode error: {e}",
                    "raw_response": response.text
                }
                
        else:
            print("❌ FAILED! API request returned error")
            try:
                error_data = response.json()
                print("📄 Error Response:")
                print(json.dumps(error_data, indent=2))
                
                # Handle common error cases
                if response.status_code == 401:
                    print("\n💡 SOLUTION: Check your access token")
                    print("   - Make sure you're using a valid Bearer token")
                    print("   - Token might be expired or incorrect")
                elif response.status_code == 404:
                    print("\n💡 SOLUTION: Check your IDs")
                    print("   - Verify the location_id is correct")
                    print("   - Verify the account_id from OAuth callback")
                elif response.status_code == 400:
                    print("\n💡 SOLUTION: Check request format")
                    print("   - Verify all required headers are present")
                    print("   - Check API version (2021-07-28)")
                
            except json.JSONDecodeError:
                print("📄 Error Text:")
                print(response.text)
            
            return {
                "success": False,
                "status_code": response.status_code,
                "error": response.text
            }
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def extract_account_id_from_oauth_url(oauth_callback_url: str):
    """
    Extract account ID from OAuth callback URL
    This might be in the state parameter or we might need to parse it differently
    """
    
    print("🔍 EXTRACTING ACCOUNT ID FROM OAUTH CALLBACK")
    print("=" * 50)
    print(f"📄 OAuth URL: {oauth_callback_url}")
    print()
    
    # For now, we'll need to determine how to get the account ID
    # It might be:
    # 1. In the state parameter (encoded)
    # 2. Returned by a separate API call
    # 3. The same as location ID in some cases
    
    # Let's try parsing the state parameter
    import urllib.parse
    
    try:
        parsed_url = urllib.parse.urlparse(oauth_callback_url)
        params = urllib.parse.parse_qs(parsed_url.query)
        
        print("📋 URL Parameters:")
        for key, value in params.items():
            print(f"   {key}: {value[0] if value else 'None'}")
        
        # The state parameter contains: du7GD0UrXKPuGjQxHJLU,QTFYuwxCgLyJQPouW0jV,integration,false,undefined,undefined,undefined
        state = params.get('state', [''])[0]
        if state:
            state_parts = state.split(',')
            location_id = state_parts[0] if len(state_parts) > 0 else None
            user_id = state_parts[1] if len(state_parts) > 1 else None
            
            print(f"\n📊 Parsed State:")
            print(f"   📍 Location ID: {location_id}")
            print(f"   👤 User ID: {user_id}")
            
            # For Facebook OAuth, the account_id might be the same as location_id
            # or we might need to make another API call to get it
            return {
                "location_id": location_id,
                "user_id": user_id,
                "potential_account_id": location_id  # This might be the account ID
            }
    
    except Exception as e:
        print(f"❌ Failed to parse OAuth URL: {e}")
        return None

def main():
    """Main function to test the Facebook account details API"""
    
    print("🔥 FACEBOOK ACCOUNT DETAILS AFTER OAUTH")
    print("=" * 60)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Your OAuth callback URL from the browser
    oauth_callback_url = "https://services.leadconnectorhq.com/social-media-posting/oauth/facebook/finish?code=AQBdFoca5WgfRWkx3yf_Gvp3mJHkutIPHHBlL0N1V6xh_SV_JDObY-NRpV6L_whe4rn-58oKkyxlQPyxR7gXnki9Oi98ZRurjmj5GKvsYA7Wr8dwzksNLejhlQpcrygT2GMcg6eKrT29uchtaLG542MI_cNRxtqeaclBVva_BxEGs3jpA8flRZ14iC-WXa2tQBfT0j9BnNT1XFXx-2td8qXrWO6lpCL2F2t_Cvl5ISKkFX63wfRZRMJf85vUcxRRjRAZOrPODhl9pyXcX8cJZ2wnOU849AHctSdrEUHxyUsa55ocCX8IfgdHlRdGbuGaxbwpUNTyifwTaodtWt6Je8rxwyYFtDZnHWwflUd2x0h2gV-9gi5PAibEYUF7Ph7zLi8&state=du7GD0UrXKPuGjQxHJLU%2CQTFYuwxCgLyJQPouW0jV%2Cintegration%2Cfalse%2Cundefined%2Cundefined%2Cundefined#_=_"
    
    # Extract IDs from OAuth callback
    oauth_data = extract_account_id_from_oauth_url(oauth_callback_url)
    
    if not oauth_data:
        print("❌ Failed to extract data from OAuth callback URL")
        return
    
    # Your credentials
    LOCATION_ID = oauth_data["location_id"]  # du7GD0UrXKPuGjQxHJLU
    
    # Try with Firebase token instead of PIT token (Social Media API might need Firebase auth)
    FIREBASE_TOKEN = "eyJhbGciOiJSUzI1NiIsImtpZCI6Ijk1MWRkZTkzMmViYWNkODhhZmIwMDM3YmZlZDhmNjJiMDdmMDg2NmIiLCJ0eXAiOiJKV1QifQ.eyJ1c2VyX2lkIjoiYVowbjRldHJOQ0VCMjlzb25hOE0iLCJjb21wYW55X2lkIjoibHAycDFxMjdEcmRHdGExcUdESmQiLCJyb2xlIjoiYWRtaW4iLCJ0eXBlIjoiYWdlbmN5IiwibG9jYXRpb25zIjpbIkxIMlk5SURmQWIyOFVIcXJQd3BHIiwibEJQcWdCb3dYMUNzakhheTEyTFkiLCIzQVVvNVNkOU1lY3N1VldHUGdkRyIsIkpBQTFBdDVUcU5vS1I2RmlwaThMIiwiSUt5WEVkUVV1d3l0YVl0aXlTaWwiLCIyWnJ0dDdzS3Fyd1I0ZGQ2SXhKUCIsInZ6ejlHakpDTG1KdjZXZVAycmVsIiwiTWRZNEtMNzJFMGxjN1RxTW0zSDAiLCJnRGYwbWo5ekt5RkJEemhhSmZqMiIsIlhiYW52U29YN2N0bTB6d3hieFhFIiwiT1VIbDJEdWo5UW5vVUdza3VGWWciLCJQRlc3V0wwME1VbzFId3MwMU9jdCIsIkFYTG1WOWpkV3dneUR2NHVvUmhvIiwid1dLNjhFTjRHZnBxNUluSjAxN04iLCIzbEtzRnRZcTM5T0o4MVBscENVaSIsIkpVVEZUbnk4RVhRT1NCNU5jdkFBIiwiRkl5Z0c3RGhUeTB3Q2xPbFBrTXAiLCI2TGJjTnNEZXBYZ0F1MEVPUThVZSIsIlMyZDFXR1lFeUlHODF5a1JENDJVIiwiS0hmakY3aFdQUHBCcURwdlJvemUiXSwidmVyc2lvbiI6MiwicGVybWlzc2lvbnMiOnsid29ya2Zsb3dzX2VuYWJsZWQiOnRydWUsIndvcmtmbG93c19yZWFkX29ubHkiOmZhbHNlfSwiaXNzIjoiaHR0cHM6Ly9zZWN1cmV0b2tlbi5nb29nbGUuY29tL2hpZ2hsZXZlbC1iYWNrZW5kIiwiYXVkIjoiaGlnaGxldmVsLWJhY2tlbmQiLCJhdXRoX3RpbWUiOjE3NTQ0MDg3MTEsInN1YiI6ImFaMG40ZXRyTkNFQjI5c29uYThNIiwiaWF0IjoxNzU0NDMzMTc0LCJleHAiOjE3NTQ0MzY3NzQsImZpcmViYXNlIjp7ImlkZW50aXRpZXMiOnt9LCJzaWduX2luX3Byb3ZpZGVyIjoiY3VzdG9tIn19.p61cG7YF-UHNs7wDb5YZxr8FODGsRNxclzy2eMzL5m9o8gfzewX-J4WXWv_estC09qOTHvZ0MndMKsnesCBecvGlmupEcazoY_RtRuJBqp-H2pCSWYFwHKWc34feZaBuIjN4aHmCLv71PT1FlKKepSERJ4J1Vv51FeWjUZGZw-Wn_98WpiWe1_9vZxWo-b8K4i_hT5GFb3bc9E0tS4vnxhBsPqAr1IXVmnQLt9z-yJ2k4PpezBCpS545Sa_k_C-rWQEb7dVHRqS9NMomBIykC7oOxbCLY7uZ8VnIFSkOqamIwhfsVPCahGUhRvl3TIbkBTBD9PTebsNlgiq-YEvCdQ"
    ACCESS_TOKEN = FIREBASE_TOKEN  # Use Firebase token instead of PIT
    
    # For account_id, we'll try a few approaches:
    # 1. Same as location_id (common case)
    # 2. Same as user_id 
    # 3. A Facebook-specific account ID we need to determine
    
    account_ids_to_try = [
        LOCATION_ID,  # Often the account_id is the same as location_id
        oauth_data["user_id"],  # Sometimes it's the user_id
        "facebook_account",  # Generic Facebook account identifier
    ]
    
    print("\n🧪 TRYING DIFFERENT ACCOUNT IDs:")
    print("=" * 40)
    
    for i, account_id in enumerate(account_ids_to_try, 1):
        print(f"\n🔍 Attempt {i}: Using account_id = {account_id}")
        print("-" * 30)
        
        result = get_facebook_account_details(LOCATION_ID, account_id, ACCESS_TOKEN)
        
        if result["success"]:
            print(f"✅ SUCCESS with account_id: {account_id}")
            break
        else:
            print(f"❌ Failed with account_id: {account_id}")
            if i < len(account_ids_to_try):
                print("   Trying next account_id...")
    
    print("\n" + "=" * 60)
    print("🎯 CONCLUSION:")
    print("If all attempts failed, you may need to:")
    print("1. Check if there's another API to list Facebook accounts first")
    print("2. Use a different account_id format")
    print("3. Verify your access token has the right permissions")

if __name__ == "__main__":
    main()