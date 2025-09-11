"""
Tools Connector
Central hub for all agent tools to improve organization and efficiency
"""

# Import Solar Analysis Tools
from Tools.SolarWebsiteAnalysis import get_insights, get_data_layers, generate_report

# Import Website Tools
from Tools.Website import capture_website_screenshot, capture_website_screenshot_async, get_website_favicon, get_website_favicon_async

# Import GHL Tools
from Tools.GHL import (
    create_contact, get_contact, update_contact, delete_contact, get_all_contacts,
    create_appointment, get_appointment, update_appointment,
    create_calendar, get_calendar, update_calendar, delete_calendar, get_all_calendars,
    create_user, get_user, update_user, delete_user, get_user_by_location_id,
    create_sub_acc, get_sub_acc, update_sub_acc, delete_sub_acc,
    get_access_token
)

class ToolsManager:
    """Centralized manager for all tools"""
    
    @staticmethod
    def get_solar_insights(address: str):
        """Get solar insights for an address"""
        return get_insights(address)
    
    @staticmethod 
    def get_solar_data_layers(address: str):
        """Get solar data layers for visualization"""
        return get_data_layers(address)
    
    @staticmethod
    def generate_solar_report(address: str):
        """Generate comprehensive solar report"""
        return generate_report(address)
    
    @staticmethod
    def capture_website_screenshot(url: str, session_id: str = None):
        """Capture website screenshot"""
        return capture_website_screenshot(url, session_id)
    
    @staticmethod
    async def capture_website_screenshot_async(url: str, session_id: str = None):
        """Async capture website screenshot"""
        return await capture_website_screenshot_async(url, session_id)
    
    @staticmethod
    def get_website_favicon(url: str, session_id: str = None):
        """Get website favicon"""
        return get_website_favicon(url, session_id)
    
    @staticmethod
    async def get_website_favicon_async(url: str, session_id: str = None):
        """Async get website favicon"""
        return await get_website_favicon_async(url, session_id)
    
    # GHL Tools
    @staticmethod
    def create_contact(**kwargs):
        """Create a new contact in GHL"""
        return create_contact(**kwargs)
    
    @staticmethod
    def get_contact(contact_id: str, location_id: str = None):
        """Get contact details from GHL"""
        return get_contact(contact_id, location_id)
    
    @staticmethod
    def create_appointment(**kwargs):
        """Create appointment in GHL"""
        return create_appointment(**kwargs)
    
    @staticmethod
    def get_access_token():
        """Get GHL access token"""
        return get_access_token()

# Create global instance
tools = ToolsManager()

# Define tool mappings for easy agent access
AGENT_TOOLS = {
    'presaleskb': [
        'get_solar_insights',
        'get_solar_data_layers', 
        'generate_solar_report',
        'capture_website_screenshot',
        'get_website_favicon',
        'create_contact',
        'get_contact',
        'create_appointment'
    ],
    'leadgenkb': [
        'capture_website_screenshot',
        'get_website_favicon',
        'create_contact',
        'get_contact'
    ],
    'socialmediakb': [
        'capture_website_screenshot',
        'get_website_favicon',
        'create_contact',
        'get_contact'
    ]
}

def get_tools_for_agent(agent_name: str) -> list:
    """Get available tools for a specific agent"""
    return AGENT_TOOLS.get(agent_name, [])