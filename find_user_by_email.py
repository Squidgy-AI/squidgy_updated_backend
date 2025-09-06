import requests
import asyncio
from GHL.environment import config, constant

async def find_user_by_email(email: str, agency_token: str) -> dict:
    """
    Find an existing user by email address using GHL API
    
    Args:
        email (str): Email address to search for
        agency_token (str): Agency access token
        
    Returns:
        dict: User details if found, None if not found
    """
    
    # Unfortunately, GHL doesn't have a direct "search by email" API
    # We need to use a workaround - the most reliable way is to try to get
    # users from the company and filter by email
    
    headers = {
        "Authorization": f"Bearer {agency_token}",
        "Version": "2021-07-28",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        # Try to get all users from the company
        # Note: This might not be the most efficient for large companies
        response = requests.get(
            f"https://services.leadconnectorhq.com/users/",
            headers=headers,
            params={"companyId": constant.constant.Company_Id}
        )
        
        if response.status_code == 200:
            data = response.json()
            users = data.get('users', [])
            
            # Search for user with matching email
            for user in users:
                if user.get('email', '').lower() == email.lower():
                    return user
                    
        return None
        
    except Exception as e:
        print(f"Error finding user by email: {e}")
        return None

# Known Soma user ID from previous tests
KNOWN_SOMA_USER_ID = "tEjvHaqaIUF1t0oR4SrX"  # This should be the real Soma user ID

async def get_soma_user_details(agency_token: str) -> dict:
    """
    Get Soma's user details directly using known user ID
    """
    headers = {
        "Authorization": f"Bearer {agency_token}",
        "Version": "2021-07-28",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(
            f"https://services.leadconnectorhq.com/users/{KNOWN_SOMA_USER_ID}",
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
            
    except Exception as e:
        print(f"Error getting Soma user details: {e}")
        return None