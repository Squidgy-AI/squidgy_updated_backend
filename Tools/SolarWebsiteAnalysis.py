"""
Solar Website Analysis Tool
Uses Real Wave Solar API to provide solar insights and analysis
"""
import asyncio
import logging
from typing import Dict, Any

# Import from parent directory
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solar_api_connector import (
    SolarApiConnector, 
    SolarInsightsRequest, 
    SolarDataLayersRequest,
    SolarApiMode
)

logger = logging.getLogger(__name__)

# Initialize connector once
solar_connector = SolarApiConnector()

def get_insights(address: str) -> Dict[str, Any]:
    """
    Get solar insights for an address (synchronous wrapper)
    
    Args:
        address: Property address
        
    Returns:
        Solar insights including potential, financial estimates, etc.
    """
    try:
        # Create request with summary mode for quick insights
        request = SolarInsightsRequest(
            address=address,
            mode=SolarApiMode.SUMMARY,
            demo=False  # Use real data
        )
        
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                solar_connector.get_building_insights(request)
            )
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error getting solar insights: {str(e)}")
        return {
            "error": "Failed to get solar insights",
            "message": str(e)
        }

def get_data_layers(address: str) -> Dict[str, Any]:
    """
    Get solar data layers for visualization (synchronous wrapper)
    
    Args:
        address: Property address
        
    Returns:
        Solar data layers with panel visualization
    """
    try:
        # Create request for data layers
        request = SolarDataLayersRequest(
            address=address,
            render_panels=True,
            file_format="jpeg",
            demo=False
        )
        
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                solar_connector.get_solar_data_layers(request)
            )
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error getting solar data layers: {str(e)}")
        return {
            "error": "Failed to get solar data layers",
            "message": str(e)
        }

def generate_report(address: str, monthly_bill: float = None) -> Dict[str, Any]:
    """
    Generate comprehensive solar report (synchronous wrapper)
    
    Args:
        address: Property address
        monthly_bill: Optional monthly electric bill
        
    Returns:
        Comprehensive solar report with all details
    """
    try:
        # Create request for full report
        request = SolarInsightsRequest(
            address=address,
            mode=SolarApiMode.FULL,
            monthly_electric_bill=monthly_bill,
            demo=False
        )
        
        # Run async function in sync context  
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            insights_result = loop.run_until_complete(
                solar_connector.get_building_insights(request)
            )
            
            # Also get data layers for comprehensive report
            layers_request = SolarDataLayersRequest(
                address=address,
                render_panels=True,
                demo=False
            )
            
            layers_result = loop.run_until_complete(
                solar_connector.get_solar_data_layers(layers_request)
            )
            
            # Combine results into comprehensive report
            if "error" not in insights_result and "error" not in layers_result:
                return {
                    "status": "success",
                    "address": address,
                    "insights": insights_result,
                    "data_layers": layers_result,
                    "credits_remaining": insights_result.get("creditsLeft", "N/A")
                }
            else:
                return {
                    "error": "Failed to generate complete report",
                    "insights_error": insights_result.get("error"),
                    "layers_error": layers_result.get("error")
                }
                
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error generating solar report: {str(e)}")
        return {
            "error": "Failed to generate solar report", 
            "message": str(e)
        }

# Async versions for use in async contexts
async def get_insights_async(address: str, monthly_bill: float = None) -> Dict[str, Any]:
    """
    Get solar insights asynchronously
    
    Args:
        address: Property address
        monthly_bill: Optional monthly electric bill
        
    Returns:
        Solar insights formatted for agent use
    """
    try:
        request = SolarInsightsRequest(
            address=address,
            mode=SolarApiMode.SUMMARY,
            monthly_electric_bill=monthly_bill,
            demo=False
        )
        
        result = await solar_connector.get_building_insights(request)
        
        if "error" in result:
            return result
            
        # Extract and format key insights
        summary = result.get("rwResult", {}).get("summary", {})
        
        return {
            "status": "success",
            "address": address,
            "solar_potential": {
                "max_array_area_m2": summary.get("maxArrayAreaMeters2"),
                "max_sunshine_hours_per_year": summary.get("maxSunshineHoursPerYear"),
                "carbon_offset_factor_kg_per_mwh": summary.get("carbonOffsetFactorKgPerMwh")
            },
            "financial_analysis": {
                "monthly_bill": monthly_bill,
                "estimated_savings": summary.get("financialAnalysis", {}).get("monthlyBill", {}).get("monthlyBillAvgKwhPerMonth"),
                "payback_period_years": summary.get("financialAnalysis", {}).get("cashPurchaseSavings", {}).get("paybackYears"),
                "lifetime_savings": summary.get("financialAnalysis", {}).get("cashPurchaseSavings", {}).get("savingsLifetime")
            },
            "recommended_installation": {
                "panel_count": summary.get("idealConfiguration", {}).get("panelCount"),
                "yearly_energy_dc_kwh": summary.get("idealConfiguration", {}).get("yearlyEnergyDcKwh")
            },
            "credits_remaining": result.get("creditsLeft", "N/A")
        }
        
    except Exception as e:
        logger.error(f"Error in async solar insights: {str(e)}")
        return {
            "error": "Failed to get solar insights",
            "message": str(e)
        }