import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from mcp.server import Server

# Import existing website tools
try:
    from Website.web_scrape import capture_website_screenshot, get_website_favicon_async
    from Tools.Website.web_scrape import capture_website_screenshot as tools_screenshot
    from Tools.SolarWebsiteAnalysis.solar_data_layers import analyze_solar_data
    from Tools.SolarWebsiteAnalysis.solar_insights import generate_solar_insights
    from Tools.SolarWebsiteAnalysis.solar_report import generate_solar_report
except ImportError as e:
    print(f"Warning: Could not import website tools: {e}")

app = Server("website-bridge")

@app.tool("capture_website_screenshot")
async def capture_screenshot(
    url: str,
    width: int = 1920,
    height: int = 1080,
    full_page: bool = False
):
    """Capture website screenshot using existing backend logic"""
    try:
        # Try the main website scraper first
        try:
            result = await capture_website_screenshot(url, width, height, full_page)
        except:
            # Fallback to tools version
            result = await tools_screenshot(url, width, height, full_page)
        
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.tool("get_website_favicon")
async def get_favicon(url: str):
    """Get website favicon using existing backend logic"""
    try:
        result = await get_website_favicon_async(url)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.tool("analyze_solar_website_data")
async def analyze_solar_data_layers(url: str):
    """Analyze solar website data layers"""
    try:
        result = await analyze_solar_data(url)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.tool("generate_solar_insights")
async def create_solar_insights(url: str, analysis_data: dict = None):
    """Generate solar website insights"""
    try:
        result = await generate_solar_insights(url, analysis_data)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.tool("generate_solar_report")
async def create_solar_report(url: str, insights_data: dict = None):
    """Generate comprehensive solar website report"""
    try:
        result = await generate_solar_report(url, insights_data)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.tool("full_solar_analysis")
async def full_solar_website_analysis(url: str):
    """Complete solar website analysis pipeline"""
    try:
        # Step 1: Analyze data layers
        data_analysis = await analyze_solar_data(url)
        
        # Step 2: Generate insights
        insights = await generate_solar_insights(url, data_analysis)
        
        # Step 3: Generate report
        report = await generate_solar_report(url, insights)
        
        return {
            "success": True,
            "data": {
                "url": url,
                "data_analysis": data_analysis,
                "insights": insights,
                "report": report
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}