#!/usr/bin/env python3
"""
Facebook OAuth Integration Script using GHL Social Media Posting API
Handles the complete OAuth flow and account setup
"""

import requests
import json
import time
import webbrowser
from datetime import datetime
from urllib.parse import urlencode

class FacebookOAuthIntegrator:
    def __init__(self, location_id: str, user_id: str, access_token: str):
        self.location_id = location_id
        self.user_id = user_id
        self.access_token = access_token
        self.base_url = "https://services.leadconnectorhq.com/social-media-posting/oauth/facebook"
        
    def start_oauth_flow(self, page: str = "integration", reconnect: str = "false"):
        """
        Start the Facebook OAuth flow
        Opens browser window for user authentication
        """
        
        print("🚀 Starting Facebook OAuth Flow")
        print("=" * 50)
        print(f"📍 Location ID: {self.location_id}")
        print(f"👤 User ID: {self.user_id}")
        print(f"📄 Page: {page}")
        print(f"🔄 Reconnect: {reconnect}")
        print()
        
        # Prepare the OAuth start URL
        oauth_start_url = f"{self.base_url}/start"
        
        # Query parameters
        params = {
            "locationId": self.location_id,
            "userId": self.user_id,
            "page": page,
            "reconnect": reconnect
        }
        
        # Headers
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Version": "2021-07-28",
            "Accept": "application/json"
        }
        
        print("📡 Making OAuth start request...")
        print(f"🌐 URL: {oauth_start_url}")
        print(f"📋 Params: {params}")
        print("-" * 30)
        
        try:
            # Make the request to get OAuth URL
            response = requests.get(oauth_start_url, headers=headers, params=params)
            
            print(f"📊 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ OAuth start request successful!")
                
                # Handle different response types
                try:
                    response_data = response.json()
                    print(f"📄 JSON Response: {json.dumps(response_data, indent=2)}")
                    oauth_url = response_data.get('url') or response_data.get('redirectUrl') or response_data.get('oauthUrl')
                except json.JSONDecodeError:
                    # Response might be HTML redirect or plain text URL
                    response_text = response.text.strip()
                    print(f"📄 Response Text: {response_text}")
                    
                    # Check if response contains a URL
                    if response_text.startswith('http'):
                        oauth_url = response_text
                        response_data = {"url": oauth_url}
                    elif 'facebook.com' in response_text:
                        # Extract URL from HTML - look for the full OAuth URL
                        import re
                        # Look for the meta refresh redirect URL
                        url_match = re.search(r'content="0; URL=([^"]+)"', response_text)
                        if url_match:
                            oauth_url = url_match.group(1).replace('&amp;', '&')
                            # Make URL absolute if it's relative
                            if oauth_url.startswith('/'):
                                oauth_url = 'https://www.facebook.com' + oauth_url
                        else:
                            # Fallback: look for any facebook.com URL
                            url_match = re.search(r'https://[^\s"\'<>]+facebook[^\s"\'<>]+', response_text)
                            oauth_url = url_match.group() if url_match else None
                        response_data = {"html_response": response_text[:500] + "..."}
                    else:
                        oauth_url = None
                        response_data = {"text_response": response_text}
                
                # Check if we got a redirect URL for Facebook OAuth
                
                if oauth_url:
                    print(f"\n🔗 Facebook OAuth URL: {oauth_url}")
                    print("\n🌐 Opening Facebook OAuth in browser...")
                    print("👆 Please complete the Facebook login process in the browser window")
                    print("📱 The browser will handle the OAuth callback automatically")
                    
                    # Try multiple methods to open browser
                    import subprocess
                    import platform
                    import os
                    
                    try:
                        # Method 1: Use webbrowser module
                        webbrowser.open(oauth_url)
                        print("✅ Browser opened via webbrowser module")
                    except Exception as e1:
                        print(f"❌ webbrowser.open failed: {e1}")
                        
                        try:
                            # Method 2: Platform-specific commands
                            system = platform.system().lower()
                            if system == "darwin":  # macOS
                                subprocess.run(["open", oauth_url], check=True)
                                print("✅ Browser opened via macOS 'open' command")
                            elif system == "windows":
                                os.startfile(oauth_url)
                                print("✅ Browser opened via Windows startfile")
                            elif system == "linux":
                                subprocess.run(["xdg-open", oauth_url], check=True)
                                print("✅ Browser opened via Linux xdg-open")
                            else:
                                raise Exception(f"Unsupported platform: {system}")
                        except Exception as e2:
                            print(f"❌ Platform-specific method failed: {e2}")
                            print("\n🔗 MANUAL BROWSER OPENING REQUIRED:")
                            print("=" * 60)
                            print("Copy and paste this URL into your browser:")
                            print(f"{oauth_url}")
                            print("=" * 60)
                    
                    print("\n⏰ Waiting for OAuth completion...")
                    print("💡 After successful Facebook login, the system will automatically handle the callback")
                    print("🔄 You can check the integration status using the account details API")
                    
                    return {
                        "success": True,
                        "oauth_url": oauth_url,
                        "response_data": response_data
                    }
                else:
                    print("❌ No OAuth URL found in response")
                    return {
                        "success": False,
                        "error": "No OAuth URL in response",
                        "response_data": response_data
                    }
            else:
                print("❌ OAuth start request failed!")
                try:
                    error_data = response.json()
                    print(f"📄 Error Response: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"📄 Error Text: {response.text}")
                
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
    
    def get_facebook_accounts(self, account_id: str, page: str = "integration", reconnect: str = "false"):
        """
        Get Facebook account details after OAuth completion
        """
        
        print(f"\n📱 Getting Facebook Account Details")
        print("=" * 40)
        print(f"🆔 Account ID: {account_id}")
        
        # Build the accounts URL
        accounts_url = f"{self.base_url}/accounts/{account_id}"
        
        # Query parameters
        params = {
            "locationId": self.location_id,
            "userId": self.user_id,
            "page": page,
            "reconnect": reconnect
        }
        
        # Headers
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Version": "2021-07-28",
            "Accept": "application/json"
        }
        
        print(f"🌐 URL: {accounts_url}")
        print(f"📋 Params: {params}")
        print()
        
        try:
            response = requests.get(accounts_url, headers=headers, params=params)
            
            print(f"📊 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                account_data = response.json()
                print("✅ Facebook account details retrieved!")
                print(f"📄 Account Data: {json.dumps(account_data, indent=2)}")
                
                # Parse account information
                if isinstance(account_data, dict):
                    print(f"\n📋 FACEBOOK ACCOUNT SUMMARY:")
                    print(f"   🆔 Account ID: {account_data.get('id', 'N/A')}")
                    print(f"   📄 Name: {account_data.get('name', 'N/A')}")
                    print(f"   📱 Platform: {account_data.get('platform', 'N/A')}")
                    print(f"   ✅ Status: {account_data.get('status', 'N/A')}")
                    
                    # Check for Facebook pages
                    pages = account_data.get('pages', [])
                    if pages:
                        print(f"   📄 Pages: {len(pages)} page(s)")
                        for i, page in enumerate(pages[:3]):  # Show first 3 pages
                            print(f"      📄 Page {i+1}: {page.get('name', 'Unknown')} (ID: {page.get('id', 'N/A')})")
                
                return {
                    "success": True,
                    "account_data": account_data
                }
            else:
                print("❌ Failed to get account details!")
                try:
                    error_data = response.json()
                    print(f"📄 Error: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"📄 Error Text: {response.text}")
                
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
    
    def wait_for_oauth_completion(self, timeout_minutes: int = 5):
        """
        Wait for OAuth completion by checking integration status
        """
        print(f"\n⏳ Waiting for OAuth completion (timeout: {timeout_minutes} minutes)")
        print("💡 Complete the Facebook login in your browser...")
        
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        
        while time.time() - start_time < timeout_seconds:
            print(".", end="", flush=True)
            time.sleep(10)  # Check every 10 seconds
            
            # Here you could check if the integration is complete
            # by calling another API endpoint if available
        
        print(f"\n⏰ Timeout after {timeout_minutes} minutes")
        print("💡 You can manually check integration status or call get_facebook_accounts() with the account ID")
    
    def complete_integration_flow(self):
        """
        Complete the full Facebook integration flow
        """
        print("🔥 COMPLETE FACEBOOK OAUTH INTEGRATION")
        print("=" * 60)
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Step 1: Start OAuth flow
        oauth_result = self.start_oauth_flow()
        
        if not oauth_result["success"]:
            print("❌ OAuth flow failed to start")
            return oauth_result
        
        print("\n" + "="*50)
        print("📱 NEXT STEPS:")
        print("="*50)
        print("1. ✅ OAuth URL opened in browser")
        print("2. 👤 Complete Facebook login in browser window")
        print("3. 🔄 Facebook will redirect back to GHL")
        print("4. 📱 Use the account ID from browser callback to get account details")
        print()
        print("💡 BROWSER CALLBACK LISTENER:")
        print("   Add this JavaScript to your frontend to capture the account ID:")
        print()
        print("   window.addEventListener('message', function(e) {")
        print("       if (e.data && e.data.page === 'social_media_posting') {")
        print("           const { actionType, accountId, platform } = e.data;")
        print("           console.log('Facebook OAuth Result:', e.data);")
        print("           // Use accountId to call get_facebook_accounts()")
        print("       }")
        print("   }, false);")
        print()
        print("📞 MANUAL ACCOUNT CHECK:")
        print(f"   If you have the account ID, call:")
        print(f"   python3 facebook_oauth_integration.py get-accounts <account_id>")
        
        return oauth_result

def main():
    """Main function for CLI usage"""
    
    # Your credentials
    LOCATION_ID = "du7GD0UrXKPuGjQxHJLU"
    USER_ID = "QTFYuwxCgLyJQPouW0jV" 
    ACCESS_TOKEN = "pit-78171be4-bfb0-4a89-9586-26087d789907"
    
    integrator = FacebookOAuthIntegrator(LOCATION_ID, USER_ID, ACCESS_TOKEN)
    
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "start":
            # Start OAuth flow
            integrator.complete_integration_flow()
            
        elif command == "get-accounts" and len(sys.argv) > 2:
            # Get account details with provided account ID
            account_id = sys.argv[2]
            integrator.get_facebook_accounts(account_id)
            
        elif command == "reconnect":
            # Start OAuth with reconnect=true
            integrator.start_oauth_flow(page="integration", reconnect="true")
            
        else:
            print("Usage:")
            print("  python3 facebook_oauth_integration.py start")
            print("  python3 facebook_oauth_integration.py get-accounts <account_id>")
            print("  python3 facebook_oauth_integration.py reconnect")
    else:
        # Default: run complete integration flow
        integrator.complete_integration_flow()

if __name__ == "__main__":
    main()