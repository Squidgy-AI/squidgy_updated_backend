#!/usr/bin/env python3
"""
Test the fixed website analysis for jackwacker.com
"""
import httpx
import asyncio
from bs4 import BeautifulSoup

async def test_scraping():
    url = "https://www.jackwacker.com"

    print("Testing DIRECT WEB SCRAPING approach...")
    print("=" * 80)

    try:
        # Fetch website
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as http_client:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            fetch_response = await http_client.get(url, headers=headers)

            print(f"Status Code: {fetch_response.status_code}")

            if fetch_response.status_code == 200:
                # Parse HTML content
                soup = BeautifulSoup(fetch_response.text, 'html.parser')

                # Remove unwanted elements
                for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                    element.decompose()

                # Extract text content
                text_content = soup.get_text(separator='\n', strip=True)

                # Clean up whitespace
                lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                cleaned_content = '\n'.join(lines)

                content_length = len(cleaned_content)
                print(f"Content Length: {content_length} characters")
                print("=" * 80)
                print("\nFirst 1000 characters of scraped content:")
                print("=" * 80)
                print(cleaned_content[:1000])
                print("=" * 80)

                # Check for key fishing-related terms
                keywords = ['fishing', 'fish', 'rig', 'walleye', 'perch', 'pike', 'tackle', 'lure', 'bait']
                found_keywords = [kw for kw in keywords if kw.lower() in cleaned_content.lower()]

                print(f"\nFishing-related keywords found: {found_keywords}")

                if len(found_keywords) >= 3:
                    print("\n✅ SUCCESS: Direct scraping correctly identifies this as fishing-related content!")
                else:
                    print("\n❌ PROBLEM: Direct scraping doesn't show strong fishing signals")

                if "digital marketing" in cleaned_content.lower() or "web development" in cleaned_content.lower():
                    print("⚠️ WARNING: Content mentions digital marketing/web dev (shouldn't be there!)")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_scraping())
