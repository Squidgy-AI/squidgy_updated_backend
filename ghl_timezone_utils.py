"""
Consolidated GoHighLevel Timezone Utilities
Provides country-to-timezone mapping for GHL subaccount creation
"""

import requests
import logging
from typing import Dict, Optional, List

# Configure logging
logger = logging.getLogger(__name__)

# Common country to timezone mapping for well-known countries
COUNTRY_TIMEZONE_MAP = {
    # North America
    "US": "America/New_York",  # United States
    "CA": "America/Toronto",   # Canada
    "MX": "America/Mexico_City",  # Mexico
    
    # Europe
    "GB": "Europe/London",     # United Kingdom
    "UK": "Europe/London",     # United Kingdom (alternative code)
    "DE": "Europe/Berlin",     # Germany
    "FR": "Europe/Paris",      # France
    "IT": "Europe/Rome",       # Italy
    "ES": "Europe/Madrid",     # Spain
    "NL": "Europe/Amsterdam",  # Netherlands
    
    # Asia
    "JP": "Asia/Tokyo",        # Japan
    "CN": "Asia/Shanghai",     # China
    "IN": "Asia/Kolkata",      # India
    "SG": "Asia/Singapore",    # Singapore
    "AE": "Asia/Dubai",        # United Arab Emirates
    
    # Oceania
    "AU": "Australia/Sydney",  # Australia
    "NZ": "Pacific/Auckland",  # New Zealand
    
    # South America
    "BR": "America/Sao_Paulo", # Brazil
    "AR": "America/Argentina/Buenos_Aires", # Argentina
    
    # Africa
    "ZA": "Africa/Johannesburg", # South Africa
    "EG": "Africa/Cairo",      # Egypt
}

# Common timezone list as fallback if API fails
COMMON_TIMEZONES = [
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "America/Toronto",
    "America/Mexico_City",
    "America/Sao_Paulo",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "Europe/Rome",
    "Europe/Madrid",
    "Asia/Tokyo",
    "Asia/Shanghai",
    "Asia/Singapore",
    "Asia/Dubai",
    "Asia/Kolkata",
    "Australia/Sydney",
    "Pacific/Auckland",
    "Africa/Johannesburg"
]

def get_ghl_timezones(api_key: Optional[str] = None) -> List[str]:
    """
    Fetch available timezones from GoHighLevel API
    Returns a list of timezone strings
    
    Args:
        api_key: Optional API key to use for authentication
        
    Returns:
        List of timezone strings
    """
    try:
        # If no API key provided, try to get it from constants
        if not api_key:
            try:
                from GHL.environment.constant import Constant
                constants = Constant()
                api_key = constants.Nestle_Api_Key
            except ImportError:
                logger.warning("Failed to import constants, using fallback timezone list")
                return COMMON_TIMEZONES
        
        # Set up headers with the API key
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Make the API request
        response = requests.get(
            "https://rest.gohighlevel.com/v1/timezones/",
            headers=headers,
            timeout=10  # Add timeout for safety
        )
        
        # Check if request was successful
        if response.status_code == 200:
            timezones = response.json()
            if isinstance(timezones, list) and len(timezones) > 0:
                logger.info(f"Successfully fetched {len(timezones)} timezones from GHL API")
                return timezones
            else:
                logger.warning(f"GHL API returned unexpected timezone format")
                return COMMON_TIMEZONES
        else:
            logger.warning(f"Failed to fetch GHL timezones: {response.status_code}")
            return COMMON_TIMEZONES
            
    except Exception as e:
        logger.error(f"Error fetching GHL timezones: {str(e)}")
        return COMMON_TIMEZONES

def get_timezone_for_country(country_code: str, default_timezone: str = "America/New_York") -> str:
    """
    Get timezone for a country code
    
    Args:
        country_code: ISO 2-letter country code (e.g., 'US', 'GB')
        default_timezone: Default timezone to return if country code not found
        
    Returns:
        Timezone string compatible with GoHighLevel API
    """
    if not country_code:
        return default_timezone
        
    # Normalize country code
    country_code = country_code.upper().strip()
    
    # Return timezone from map or default
    return COUNTRY_TIMEZONE_MAP.get(country_code, default_timezone)

def validate_timezone(timezone: str, available_timezones: Optional[List[str]] = None) -> str:
    """
    Validate that a timezone is available in GHL
    If not valid, returns a safe default timezone
    
    Args:
        timezone: Timezone string to validate
        available_timezones: Optional list of available timezones
        
    Returns:
        Valid timezone string for GHL API
    """
    if not timezone:
        return "America/New_York"
    
    try:
        # If available_timezones not provided, get them
        if not available_timezones:
            available_timezones = get_ghl_timezones()
        
        # Case-insensitive check if timezone is valid
        for tz in available_timezones:
            if timezone.lower() == tz.lower():
                return tz
                
        # If we get here, timezone is not valid
        logger.warning(f"Timezone '{timezone}' not found in GHL available timezones")
        return "America/New_York"
        
    except Exception as e:
        logger.error(f"Error validating timezone: {str(e)}")
        return "America/New_York"

def get_timezone_for_ghl(country_code: str) -> str:
    """
    Convenience function to get a valid GHL timezone for a country code
    
    Args:
        country_code: ISO 2-letter country code (e.g., 'US', 'GB')
        
    Returns:
        Valid timezone string for GHL API
    """
    # Get timezone for country
    timezone = get_timezone_for_country(country_code)
    
    # Validate timezone against GHL available timezones
    return validate_timezone(timezone)