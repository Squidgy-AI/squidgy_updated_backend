import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from mcp.server import Server

# Import existing GHL tools
try:
    from Tools.GHL.Contacts.create_contact import create_contact
    from Tools.GHL.Contacts.get_contact import get_contact
    from Tools.GHL.Contacts.get_all_contacts import get_all_contacts
    from Tools.GHL.Contacts.update_contact import update_contact
    from Tools.GHL.Contacts.delete_contact import delete_contact
    
    from Tools.GHL.Calendars.create_calendar import create_calendar
    from Tools.GHL.Calendars.get_calendar import get_calendar
    from Tools.GHL.Calendars.get_all_calendars import get_all_calendars
    from Tools.GHL.Calendars.update_calendar import update_calendar
    from Tools.GHL.Calendars.delete_calendar import delete_calendar
    
    from Tools.GHL.Users.create_user import create_user
    from Tools.GHL.Users.get_user import get_user
    from Tools.GHL.Users.get_user_by_location_id import get_user_by_location_id
    from Tools.GHL.Users.update_user import update_user
    from Tools.GHL.Users.delete_user import delete_user
    
    from Tools.GHL.Appointments.create_appointment import create_appointment
    from Tools.GHL.Appointments.get_appointment import get_appointment
    from Tools.GHL.Appointments.update_appointment import update_appointment
    
except ImportError as e:
    print(f"Warning: Could not import GHL tools: {e}")

app = Server("ghl-bridge")

# Contact Management Tools
@app.tool("ghl_create_contact")
async def ghl_create_contact(
    first_name: str,
    last_name: str,
    email: str,
    phone: str,
    location_id: str = None,
    gender: str = None,
    address1: str = None,
    city: str = None,
    state: str = None,
    postal_code: str = None,
    website: str = None,
    timezone: str = "America/Chihuahua",
    dnd: bool = True,
    country: str = "US",
    company_name: str = None,
    assigned_to: str = None,
    tags: list = None,
    source: str = "mcp_api"
):
    """Create a new GHL contact using existing backend logic"""
    try:
        result = create_contact(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            location_id=location_id,
            gender=gender,
            address1=address1,
            city=city,
            state=state,
            postal_code=postal_code,
            website=website,
            timezone=timezone,
            dnd=dnd,
            country=country,
            company_name=company_name,
            assigned_to=assigned_to,
            tags=tags,
            source=source
        )
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.tool("ghl_get_contact")
async def ghl_get_contact(contact_id: str):
    """Get GHL contact details"""
    try:
        result = get_contact(contact_id)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.tool("ghl_get_all_contacts")
async def ghl_get_all_contacts(location_id: str = None, limit: int = 100):
    """Get all GHL contacts"""
    try:
        result = get_all_contacts(location_id=location_id, limit=limit)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.tool("ghl_update_contact")
async def ghl_update_contact(contact_id: str, **kwargs):
    """Update GHL contact"""
    try:
        result = update_contact(contact_id, **kwargs)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.tool("ghl_delete_contact")
async def ghl_delete_contact(contact_id: str):
    """Delete GHL contact"""
    try:
        result = delete_contact(contact_id)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

# Calendar Management Tools
@app.tool("ghl_create_calendar")
async def ghl_create_calendar(
    name: str,
    location_id: str = None,
    description: str = None,
    **kwargs
):
    """Create a new GHL calendar"""
    try:
        result = create_calendar(
            name=name,
            location_id=location_id,
            description=description,
            **kwargs
        )
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.tool("ghl_get_calendar")
async def ghl_get_calendar(calendar_id: str):
    """Get GHL calendar details"""
    try:
        result = get_calendar(calendar_id)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.tool("ghl_get_all_calendars")
async def ghl_get_all_calendars(location_id: str = None):
    """Get all GHL calendars"""
    try:
        result = get_all_calendars(location_id=location_id)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.tool("ghl_update_calendar")
async def ghl_update_calendar(calendar_id: str, **kwargs):
    """Update GHL calendar"""
    try:
        result = update_calendar(calendar_id, **kwargs)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.tool("ghl_delete_calendar")
async def ghl_delete_calendar(calendar_id: str):
    """Delete GHL calendar"""
    try:
        result = delete_calendar(calendar_id)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

# User Management Tools
@app.tool("ghl_create_user")
async def ghl_create_user(
    name: str,
    email: str,
    location_id: str = None,
    **kwargs
):
    """Create a new GHL user"""
    try:
        result = create_user(
            name=name,
            email=email,
            location_id=location_id,
            **kwargs
        )
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.tool("ghl_get_user")
async def ghl_get_user(user_id: str):
    """Get GHL user details"""
    try:
        result = get_user(user_id)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.tool("ghl_get_user_by_location")
async def ghl_get_user_by_location(location_id: str):
    """Get GHL users by location"""
    try:
        result = get_user_by_location_id(location_id)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.tool("ghl_update_user")
async def ghl_update_user(user_id: str, **kwargs):
    """Update GHL user"""
    try:
        result = update_user(user_id, **kwargs)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.tool("ghl_delete_user")
async def ghl_delete_user(user_id: str):
    """Delete GHL user"""
    try:
        result = delete_user(user_id)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

# Appointment Management Tools
@app.tool("ghl_create_appointment")
async def ghl_create_appointment(
    contact_id: str,
    calendar_id: str,
    start_time: str,
    end_time: str,
    title: str = None,
    **kwargs
):
    """Create a new GHL appointment"""
    try:
        result = create_appointment(
            contact_id=contact_id,
            calendar_id=calendar_id,
            start_time=start_time,
            end_time=end_time,
            title=title,
            **kwargs
        )
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.tool("ghl_get_appointment")
async def ghl_get_appointment(appointment_id: str):
    """Get GHL appointment details"""
    try:
        result = get_appointment(appointment_id)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.tool("ghl_update_appointment")
async def ghl_update_appointment(appointment_id: str, **kwargs):
    """Update GHL appointment"""
    try:
        result = update_appointment(appointment_id, **kwargs)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}