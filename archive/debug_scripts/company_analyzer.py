#!/usr/bin/env python3

import requests
import sys

def analyze_company(url):
    import os
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        return "Error: ANTHROPIC_API_KEY environment variable not set"
    
    prompt = f"""Please analyze the website {url} and extract accurate company information. Use web scraping to get real data - do not make up or guess any information. If data is not available, explicitly state 'Not found on website'. Provide a structured summary in exactly this format: Company name: [Extract from website or state 'Not found'] | Website: {url} | Contact Information: [Only include actual contact details found on the website - email, phone, address. If not found, state 'Not available on website'] | Description: [2-3 sentences about what the company actually does based on website content] | Tags: [Actual business categories found on site, separated by periods] | Takeaways: [Real value propositions mentioned on the website] | Niche: [Specific market/audience the company actually serves based on website content] | IMPORTANT: Only include information that is explicitly stated on the website. Do not infer, assume, or make up any data."""
    
    response = requests.post(
        'https://api.anthropic.com/v1/messages',
        headers={
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json'
        },
        json={
            'model': 'claude-sonnet-4-5',
            'max_tokens': 1024,
            'system': 'You are a highly accurate information extractor. Extract only verified information from web search results.',
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'tools': [
                {
                    'type': 'web_search_20250305',
                    'name': 'web_search',
                    'max_uses': 1
                }
            ]
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        if 'content' in result and len(result['content']) > 0:
            return result['content'][0]['text']
        else:
            return "No content in response"
    else:
        return f"Error: {response.status_code} - {response.text}"

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("Enter company website URL: ")
    
    print("Analyzing website...")
    result = analyze_company(url)
    print("\n" + result)