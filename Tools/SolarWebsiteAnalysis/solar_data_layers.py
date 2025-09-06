"""
Solar Data Layers Tool
Provides visual solar analysis layers for addresses using RealWave API
"""

import os
import requests
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API Configuration
SOLAR_API_KEY = os.getenv('SOLAR_API_KEY', 'your_solar_api_key_here')

def get_data_layers(address):
    """Get solar data layers for an address and process images for display"""
    base_url = "https://api.realwave.com/googleSolar"
    
    # Base headers
    headers = {
        "Authorization": f"Bearer {SOLAR_API_KEY}",
        "Accept": "application/json"
    }
    
    # API parameters - demo must be string "true"
    params = {
        "address": address,
        "renderPanels": "true",
        "fileFormat": "jpeg",
        "demo": "true"  # Must be string "true" not boolean
    }
    
    try:
        logger.info(f"Sending request for address: {address}")
        
        # Send request with query parameters
        response = requests.post(
            url=f"{base_url}/dataLayers",
            headers=headers,
            params=params
        )
        
        # Log response status and headers for debugging
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
        
        # Process image URLs if they exist
        if "rwResult" in result:
            rwResult = result["rwResult"]
            layers = []
            
            # Define the layers to extract and their display names
            layer_mappings = {
                "satelliteImageURL": {
                    "name": "Satellite View",
                    "description": "Satellite image of the property"
                },
                "compositedMarkedRGBURL": {
                    "name": "Property Marker",
                    "description": "Satellite image with property marked"
                },
                "compositedAnnualFluxURL": {
                    "name": "Solar Potential",
                    "description": "Annual solar energy potential overlay"
                },
                "compositedMarkedPanelsURL": {
                    "name": "Solar Panel Layout",
                    "description": "Recommended solar panel configuration"
                }
            }
            
            # Extract layers that exist in the response
            for key, info in layer_mappings.items():
                if key in rwResult and rwResult[key]:
                    layers.append({
                        "name": info["name"],
                        "description": info["description"],
                        "imageUrl": rwResult[key],
                        "type": key.replace("URL", "").lower()
                    })
            
            processed_result["layers"] = layers
            
            # Add expiration info if available
            if "imagesExpireOn" in rwResult:
                processed_result["expiresOn"] = rwResult["imagesExpireOn"]
                
            # Add raw response for agent processing
            processed_result["raw_response"] = result
        else:
            # Log the actual response structure for debugging
            logger.warning(f"No 'rwResult' found in API response. Response keys: {result.keys()}")
            return {
                "error": "Unexpected API response format - no 'rwResult' found",
                "raw_data": result
            }
        
        return processed_result
        
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Request error occurred: {str(req_err)}")
        return {"error": f"Request error: {str(req_err)}"}
    except Exception as e:
        logger.exception(f"Error fetching solar data layers: {str(e)}")
        return {"error": str(e)}

# For standalone testing
if __name__ == "__main__":
    # Set API key for testing
    os.environ["SOLAR_API_KEY"] = "paIpD0y6+aZt7+nFjXBL7EQdtcXTswIF8zDjyUPTmnU="
    SOLAR_API_KEY = os.environ["SOLAR_API_KEY"]
    
    # Sample address to test
    test_address = "1600 Amphitheatre Parkway, Mountain View, CA 94043"
    
    print(f"Testing solar data layers for address: {test_address}")
    
    # Call the function
    result = get_data_layers(test_address)
    
    # Check if there was an error
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        # Display the results
        print(f"Found {len(result.get('layers', []))} data layers:")
        
        for i, layer in enumerate(result.get('layers', []), 1):
            print(f"\n{i}. {layer['name']}")
            print(f"   Description: {layer['description']}")
            print(f"   Image URL: {layer['imageUrl'][:50]}..." if len(layer['imageUrl']) > 50 else layer['imageUrl'])
            print(f"   Type: {layer['type']}")
        
        # Display expiration if available
        if "expiresOn" in result:
            print(f"\nImages expire on: {result['expiresOn']}")