"""
Example of how to integrate the organized tools into main.py

This shows how to replace the scattered tool functions with organized imports
"""

# OLD WAY (scattered in main.py):
# def get_insights(address: str) -> Dict[str, Any]:
#     # 80 lines of code here...

# def get_datalayers(address: str) -> Dict[str, Any]:
#     # 80 lines of code here...

# def get_report(address: str) -> Dict[str, Any]:
#     # 80 lines of code here...


# NEW WAY (organized):
from tools_connector import tools

# FastAPI endpoints can now simply call:

@app.get("/api/solar/insights")
async def solar_insights_endpoint(address: str):
    """Solar insights endpoint"""
    result = tools.get_solar_insights(address)
    return result

@app.get("/api/solar/data-layers") 
async def solar_data_layers_endpoint(address: str):
    """Solar data layers endpoint"""
    result = tools.get_solar_data_layers(address)
    return result

@app.get("/api/solar/report")
async def solar_report_endpoint(address: str):
    """Solar report endpoint"""
    result = tools.generate_solar_report(address)
    return result

@app.get("/api/website/screenshot")
async def website_screenshot_endpoint(url: str, session_id: str = None):
    """Website screenshot endpoint"""
    result = await tools.capture_website_screenshot_async(url, session_id)
    return result

@app.get("/api/website/favicon")
async def website_favicon_endpoint(url: str, session_id: str = None):
    """Website favicon endpoint"""
    result = await tools.get_website_favicon_async(url, session_id)
    return result


# For agent tool execution, you can also use:
def execute_agent_tool(agent_name: str, tool_name: str, **kwargs):
    """Execute a tool for a specific agent"""
    if hasattr(tools, tool_name):
        tool_function = getattr(tools, tool_name)
        return tool_function(**kwargs)
    else:
        return {"error": f"Tool {tool_name} not found"}

# Example usage:
# result = execute_agent_tool('presaleskb', 'get_solar_insights', address='123 Main St')