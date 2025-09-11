"""
Solar Insights Analysis Tool
Provides comprehensive solar potential analysis for addresses using RealWave API
"""

import os
import requests
import logging
from typing import Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API Configuration
SOLAR_API_KEY = os.getenv('SOLAR_API_KEY', 'your_solar_api_key_here')

def get_insights(address: str) -> Dict[str, Any]:
    """Get solar insights for an address with enhanced visualization data"""
    base_url = "https://api.realwave.com/googleSolar"
    headers = {
        "Authorization": f"Bearer {SOLAR_API_KEY}",
        "Accept": "application/json"
    }
    
    # Parameters - demo must be string "true"
    params = {
        "address": address,
        "mode": "full",
        "demo": "true"  # Must be string "true" not boolean
    }
    
    try:
        logger.info(f"Sending insights request for address: {address}")
        
        # Send request with query parameters
        response = requests.post(
            url=f"{base_url}/insights",
            headers=headers,
            params=params
        )
        
        # Log response status
        logger.info(f"Response status: {response.status_code}")
        
        # Check if response is successful
        if response.status_code != 200:
            logger.error(f"API returned error status: {response.status_code}")
            try:
                error_data = response.json()
                logger.error(f"Error details: {error_data}")
                return {"error": f"API error: {response.status_code}", "details": error_data}
            except:
                return {"error": f"API error: {response.status_code}", "response": response.text[:500]}
        
        # Try to parse JSON
        try:
            result = response.json()
        except Exception as json_err:
            logger.error(f"Invalid JSON response: {str(json_err)}")
            return {"error": f"Invalid JSON response: {str(json_err)}", "raw_response": response.text[:1000]}
        
        # Process the response for visualization
        processed_result = {}
        
        # Extract location data for map visualization
        if "rwResult" in result and result["rwResult"]:
            rwResult = result["rwResult"]
            
            # Check for location data in solarResults
            if "solarResults" in rwResult and rwResult["solarResults"] and "center" in rwResult["solarResults"]:
                center = rwResult["solarResults"]["center"]
                processed_result["location"] = {
                    "latitude": center.get("latitude"),
                    "longitude": center.get("longitude"),
                    "address": address
                }
            
            # Extract solar potential data from summary
            if "summary" in rwResult and rwResult["summary"]:
                summary = rwResult["summary"]
                
                # Basic solar potential metrics
                solar_potential = {
                    "maxSunshineHoursPerYear": summary.get("maxSunshineHoursPerYear"),
                    "minPanelCount": summary.get("minPossiblePanelCount"),
                    "maxPanelCount": summary.get("maxPossiblePanelCount"),
                    "maxYearlyEnergy": summary.get("maxIdealYearlyEnergyDcKwh")
                }
                
                # Get ideal panel count from ideal configurations
                if "idealConfigurations" in summary and len(summary["idealConfigurations"]) > 0:
                    solar_potential["idealPanelCount"] = summary["idealConfigurations"][0].get("panelCount")
                
                # Get financial details from cash purchase savings
                if "idealCashPurchaseSavings" in summary and summary["idealCashPurchaseSavings"]:
                    cash_savings = summary["idealCashPurchaseSavings"]
                    if "financialDetails" in cash_savings:
                        financial_details = cash_savings["financialDetails"]
                        solar_potential["estimatedSavings"] = financial_details.get("lifetimeSavingsUsd", {}).get("cents", 0) / 100
                
                processed_result["solarPotential"] = solar_potential
                
                # Add financial data if available
                if "idealCashPurchaseSavings" in summary and summary["idealCashPurchaseSavings"]:
                    cash_savings = summary["idealCashPurchaseSavings"]
                    if "financialDetails" in cash_savings:
                        financial_details = cash_savings["financialDetails"]
                        
                        financials = {}
                        
                        # Installation cost
                        if "initialAcquisitionCostUsd" in financial_details:
                            financials["installationCost"] = financial_details["initialAcquisitionCostUsd"].get("cents", 0) / 100
                        
                        # Annual savings (calculate from lifetime savings and years)
                        if "lifetimeSavingsUsd" in financial_details and "solarInstallationLifespan" in summary:
                            lifetime_savings = financial_details["lifetimeSavingsUsd"].get("cents", 0) / 100
                            lifespan = summary["solarInstallationLifespan"]
                            financials["annualSavings"] = lifetime_savings / lifespan if lifespan > 0 else 0
                        
                        # Payback period
                        if "paybackPeriodYears" in financial_details:
                            financials["paybackPeriodYears"] = financial_details["paybackPeriodYears"]
                        
                        processed_result["financials"] = financials
            
            # Add raw building insights for detailed analysis if available
            if "solarResults" in rwResult and rwResult["solarResults"] and "solarPotential" in rwResult["solarResults"]:
                solar_potential = rwResult["solarResults"]["solarPotential"]
                processed_result["roofData"] = {
                    "maxArrayAreaMeters2": solar_potential.get("maxArrayAreaMeters2"),
                    "maxSunshineHoursPerYear": solar_potential.get("maxSunshineHoursPerYear"),
                    "carbonOffsetFactorKgPerMwh": solar_potential.get("carbonOffsetFactorKgPerMwh"),
                    "panelCapacityWatts": solar_potential.get("panelCapacityWatts"),
                    "roofSegmentStats": solar_potential.get("roofSegmentStats", [])
                }
        
        # Add raw response for debugging
        processed_result["raw_response"] = result
        
        return processed_result
        
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Request error occurred: {str(req_err)}")
        return {"error": f"Request error: {str(req_err)}"}
    except Exception as e:
        logger.exception(f"Error fetching solar insights: {str(e)}")
        return {"error": str(e)}

# For standalone testing
if __name__ == "__main__":
    # Set API key for testing
    os.environ["SOLAR_API_KEY"] = "paIpD0y6+aZt7+nFjXBL7EQdtcXTswIF8zDjyUPTmnU="
    SOLAR_API_KEY = os.environ["SOLAR_API_KEY"]
    
    # Sample address to test
    test_address = "1600 Amphitheatre Parkway, Mountain View, CA 94043"
    
    print(f"Testing solar insights for address: {test_address}")
    
    # Call the function
    result = get_insights(test_address)
    
    # Check if there was an error
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        # Display the results
        print("\nSOLAR INSIGHTS SUMMARY:")
        
        if "location" in result:
            loc = result["location"]
            print(f"\nLocation: {loc['address']}")
            print(f"Coordinates: {loc['latitude']}, {loc['longitude']}")
        
        if "solarPotential" in result:
            sp = result["solarPotential"]
            print(f"\nSolar Potential:")
            print(f"- Max sunshine hours/year: {sp.get('maxSunshineHoursPerYear', 'N/A')}")
            print(f"- Panel count range: {sp.get('minPanelCount', 'N/A')} - {sp.get('maxPanelCount', 'N/A')}")
            print(f"- Ideal panel count: {sp.get('idealPanelCount', 'N/A')}")
            print(f"- Max yearly energy: {sp.get('maxYearlyEnergy', 'N/A')} kWh")
            if sp.get('estimatedSavings'):
                print(f"- Estimated lifetime savings: ${sp['estimatedSavings']:,.2f}")
        
        if "financials" in result:
            fin = result["financials"]
            print(f"\nFinancial Analysis:")
            if fin.get('installationCost'):
                print(f"- Installation cost: ${fin['installationCost']:,.2f}")
            if fin.get('annualSavings'):
                print(f"- Annual savings: ${fin['annualSavings']:,.2f}")
            if fin.get('paybackPeriodYears'):
                print(f"- Payback period: {fin['paybackPeriodYears']:.1f} years")
        
        if "roofData" in result:
            print(f"\nRoof analysis data available for {len(result['roofData'].get('roofSegmentStats', []))} segments")