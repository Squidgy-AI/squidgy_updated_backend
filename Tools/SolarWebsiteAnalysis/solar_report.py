"""
Solar Report Generation Tool
Generates comprehensive solar analysis reports using RealWave API
"""

import os
import json
import requests
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API Configuration
SOLAR_API_KEY = os.getenv('SOLAR_API_KEY', 'your_solar_api_key_here')

def generate_report(address):
    """Get solar report for an address and extract PDF download link"""
    base_url = "https://api.realwave.com/googleSolar"
    
    # Base headers
    headers = {
        "Authorization": f"Bearer {SOLAR_API_KEY}",
        "Accept": "application/json"
    }
    
    # Query parameters - demo must be string "true"
    params = {
        "address": address,
        "organizationName": "Squidgy Solar",
        "leadName": "Potential Client",
        "demo": "true"  # Must be string "true" not boolean
    }
    
    try:
        logger.info(f"Sending report request for address: {address}")
        
        # Send request with query parameters
        response = requests.post(
            url=f"{base_url}/report",
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
        
        # Extract the PDF report URL
        if "rwResult" in result and result["rwResult"] and "reportURL" in result["rwResult"]:
            processed_result["reportUrl"] = result["rwResult"]["reportURL"]
        
        # Extract expiration date
        if "rwResult" in result and result["rwResult"] and "reportExpiresOn" in result["rwResult"]:
            processed_result["expiresOn"] = result["rwResult"]["reportExpiresOn"]
        
        # Extract structured data if available
        if "rwResult" in result and result["rwResult"] and "structuredDataForAgents" in result["rwResult"]:
            try:
                structured_data = json.loads(result["rwResult"]["structuredDataForAgents"])
                
                # Create a summary from the structured data
                summary_parts = []
                
                if "SampleInstallation" in structured_data:
                    sample = structured_data["SampleInstallation"]
                    if "InstallationSizeKwh" in sample:
                        # Convert the string to float for proper formatting
                        size_str = sample["InstallationSizeKwh"].replace(",", "")
                        size_kw = float(size_str) / 1000  # Convert from Wh to kW
                        summary_parts.append(f"System size: {size_kw:.1f} kW")
                    if "PanelCount" in sample:
                        summary_parts.append(f"Panel count: {sample['PanelCount']}")
                
                if "FinancialAnalysis" in structured_data:
                    financial = structured_data["FinancialAnalysis"]
                    if "CashPurchase" in financial and "LifetimeSavingsUSD" in financial["CashPurchase"]:
                        # Parse the savings value
                        savings_str = financial["CashPurchase"]["LifetimeSavingsUSD"].replace("$", "").replace(",", "")
                        summary_parts.append(f"Lifetime savings: ${float(savings_str):,.2f}")
                    
                    # Calculate payback period if we have the data
                    if "CashPurchase" in financial and "UpfrontCostUSD" in financial["CashPurchase"]:
                        upfront_str = financial["CashPurchase"]["UpfrontCostUSD"].replace("$", "").replace(",", "")
                        upfront_cost = float(upfront_str)
                        if "LifetimeSavingsUSD" in financial["CashPurchase"]:
                            savings_str = financial["CashPurchase"]["LifetimeSavingsUSD"].replace("$", "").replace(",", "")
                            lifetime_savings = float(savings_str)
                            if "InstallationLifeSpanYears" in financial:
                                lifespan = float(financial["InstallationLifeSpanYears"])
                                yearly_savings = lifetime_savings / lifespan
                                if yearly_savings > 0:
                                    payback_years = upfront_cost / yearly_savings
                                    summary_parts.append(f"Payback period: {payback_years:.1f} years")
                
                processed_result["summary"] = ". ".join(summary_parts)
                processed_result["reportData"] = structured_data
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                # If parsing fails, provide a basic summary
                logger.warning(f"Error parsing structured data: {str(e)}")
                processed_result["summary"] = f"Solar report generated for {address}."
                
        # Add raw response for agent processing
        processed_result["raw_response"] = result
        
        return processed_result
        
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Request error occurred: {str(req_err)}")
        return {"error": f"Request error: {str(req_err)}"}
    except Exception as e:
        logger.exception(f"Error generating solar report: {str(e)}")
        return {"error": str(e)}

# For standalone testing
if __name__ == "__main__":
    # Set API key for testing
    os.environ["SOLAR_API_KEY"] = "paIpD0y6+aZt7+nFjXBL7EQdtcXTswIF8zDjyUPTmnU="
    SOLAR_API_KEY = os.environ["SOLAR_API_KEY"]
    
    # Sample address to test
    test_address = "1600 Amphitheatre Parkway, Mountain View, CA 94043"
    
    print(f"Testing solar report generation for address: {test_address}")
    
    # Call the function
    result = generate_report(test_address)
    
    # Check if there was an error
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        # Display the results
        print("\nSOLAR REPORT SUMMARY:")
        
        if "summary" in result:
            print(f"\n{result['summary']}")
        
        if "reportUrl" in result:
            print(f"\nReport URL: {result['reportUrl']}")
        
        if "expiresOn" in result:
            print(f"Report expires on: {result['expiresOn']}")
        
        if "reportData" in result:
            print("\nDetailed report data available for processing.")