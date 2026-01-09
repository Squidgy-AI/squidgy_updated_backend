#!/usr/bin/env python3

import requests
import json
from typing import Dict, Any, Optional


class WebAnalysisClient:
    """
    Client for calling the CRA web analysis endpoint
    """
    
    def __init__(self):
        self.base_url = "https://cra-web-analysis-676761218b7a.herokuapp.com"
    
    def analyze_website(self, url: str) -> Dict[str, Any]:
        """
        Call the web analysis endpoint with a URL parameter
        
        Args:
            url (str): The website URL to analyze
            
        Returns:
            Dict[str, Any]: The analysis response from the endpoint
        """
        try:
            endpoint = f"{self.base_url}/scrape"
            params = {"url": url}
            
            print(f"Calling web analysis endpoint: {endpoint}")
            print(f"URL parameter: {url}")
            
            # Try POST request first, then GET if that fails
            response = requests.post(endpoint, json=params, timeout=30)
            
            print(f"Response status code: {response.status_code}")
            print(f"Response content: {response.text[:200]}...")  # First 200 chars
            
            if response.status_code == 200:
                if response.text.strip():
                    try:
                        result = response.json()
                        print("Analysis successful!")
                        return {
                            "success": True,
                            "data": result,
                            "status_code": response.status_code
                        }
                    except json.JSONDecodeError:
                        # Response might not be JSON, return as text
                        print("Response is not JSON, returning as text")
                        return {
                            "success": True,
                            "data": {"response_text": response.text},
                            "status_code": response.status_code
                        }
                else:
                    return {
                        "success": False,
                        "error": "Empty response body",
                        "status_code": response.status_code
                    }
            else:
                print(f"Error: HTTP {response.status_code}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "status_code": response.status_code
                }
                
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Request timeout (30s)",
                "status_code": None
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}",
                "status_code": None
            }
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Invalid JSON response",
                "status_code": response.status_code if 'response' in locals() else None
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "status_code": None
            }


def test_web_analysis(url: str):
    """
    Test function to analyze a website URL
    """
    client = WebAnalysisClient()
    result = client.analyze_website(url)
    
    print("\n" + "="*50)
    print("WEB ANALYSIS RESULT")
    print("="*50)
    print(f"URL Analyzed: {url}")
    print(f"Success: {result['success']}")
    
    if result['success']:
        print(f"Status Code: {result['status_code']}")
        print("\nAnalysis Data:")
        print(json.dumps(result['data'], indent=2))
    else:
        print(f"Error: {result['error']}")
        if result['status_code']:
            print(f"Status Code: {result['status_code']}")
    
    return result


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    else:
        test_url = input("Enter website URL to analyze: ")
    
    if not test_url.startswith(('http://', 'https://')):
        test_url = f"https://{test_url}"
    
    test_web_analysis(test_url)