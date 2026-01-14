#!/usr/bin/env python3
"""
Test OAuth Automation - Test the Facebook OAuth URL capture automation
Uses Chester's account information to test the automation locally
"""

import asyncio
from ghl_oauth_automation import get_oauth_automation

async def test_oauth_automation():
    """Test the OAuth automation with Chester's account info"""
    
    # Chester's account information
    location_id = "y6s9fyyiisMvJGWdFLzD"
    user_id = "BOftjgujCczOTvOEi4vJ"
    
    print("=" * 80)
    print("TESTING OAUTH AUTOMATION")
    print("=" * 80)
    print(f"Location ID: {location_id}")
    print(f"User ID: {user_id}")
    print("=" * 80)
    
    try:
        # Get the automation instance
        automation = get_oauth_automation()
        
        # Run the automation
        print("\n[TEST] Starting OAuth automation...")
        result = await automation.get_facebook_oauth_url(location_id)
        
        print("\n" + "=" * 80)
        print("AUTOMATION RESULT")
        print("=" * 80)
        print(f"Success: {result['success']}")
        print(f"Message: {result['message']}")
        
        if result['oauth_url']:
            # Add user_id to the OAuth URL
            separator = '&' if '?' in result['oauth_url'] else '?'
            final_url = f"{result['oauth_url']}{separator}userId={user_id}"
            
            print(f"\nOAuth URL (without userId):")
            print(result['oauth_url'])
            print(f"\nFinal OAuth URL (with userId):")
            print(final_url)
        else:
            print("\nNo OAuth URL captured")
        
        print("=" * 80)
        
        return result
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_oauth_automation())
    
    if result and result['success']:
        print("\n[SUCCESS] TEST PASSED - OAuth URL captured successfully!")
    else:
        print("\n[FAILED] TEST FAILED - Could not capture OAuth URL")
