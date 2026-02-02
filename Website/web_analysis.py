# Website/web_analysis.py - Web scraping and analysis module

import os
import time
import logging
import httpx
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urljoin
from typing import Dict, Any, Optional, List, Set
import re
from collections import Counter

logger = logging.getLogger(__name__)


def extract_colors_from_website(url: str) -> List[str]:
    """
    Extract hex color codes from a website by parsing CSS and inline styles.
    
    Args:
        url: The website URL to extract colors from
        
    Returns:
        List of unique hex color codes (e.g., ['#FF5733', '#2C3E50', '#FFFFFF'])
    """
    try:
        # Ensure URL has protocol
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        logger.info(f"Extracting colors from: {url}")
        
        # Fetch the page
        with httpx.Client(
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
            timeout=15.0,
            follow_redirects=True
        ) as client:
            response = client.get(url)
            
            if response.status_code >= 400:
                logger.warning(f"HTTP {response.status_code} when fetching {url} for color extraction")
                return []
                
            html_content = response.text
            
            # Also try to fetch main CSS files
            soup = BeautifulSoup(html_content, 'html.parser')
            css_content = ""
            
            # Get inline styles from style tags
            for style_tag in soup.find_all('style'):
                if style_tag.string:
                    css_content += style_tag.string + "\n"
            
            # Get external CSS files (limit to first 3 to avoid slowdown)
            css_links = soup.find_all('link', rel='stylesheet')[:3]
            for link in css_links:
                href = link.get('href')
                if href:
                    css_url = urljoin(url, href)
                    try:
                        css_response = client.get(css_url)
                        if css_response.status_code == 200:
                            css_content += css_response.text + "\n"
                    except Exception as css_err:
                        logger.debug(f"Could not fetch CSS {css_url}: {css_err}")
        
        # Combine HTML and CSS for color extraction
        all_content = html_content + "\n" + css_content
        
        # Extract colors using regex patterns
        colors = extract_hex_colors(all_content)
        
        logger.info(f"Extracted {len(colors)} unique colors from {url}")
        return colors
        
    except Exception as e:
        logger.error(f"Color extraction failed for {url}: {str(e)}")
        return []


def extract_hex_colors(content: str) -> List[str]:
    """
    Extract and normalize hex color codes from CSS/HTML content.
    Returns the most frequently used colors, sorted by frequency.
    
    Args:
        content: HTML/CSS content string
        
    Returns:
        List of unique hex colors, most frequent first (max 10)
    """
    # Regex patterns for different color formats
    # 6-digit hex: #RRGGBB
    hex6_pattern = r'#([0-9A-Fa-f]{6})(?![0-9A-Fa-f])'
    # 3-digit hex: #RGB
    hex3_pattern = r'#([0-9A-Fa-f]{3})(?![0-9A-Fa-f])'
    # RGB/RGBA: rgb(r, g, b) or rgba(r, g, b, a)
    rgb_pattern = r'rgba?\s*\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})(?:\s*,\s*[\d.]+)?\s*\)'
    
    all_colors = []
    
    # Extract 6-digit hex colors
    for match in re.finditer(hex6_pattern, content):
        hex_color = f"#{match.group(1).upper()}"
        all_colors.append(hex_color)
    
    # Extract 3-digit hex colors and expand to 6-digit
    for match in re.finditer(hex3_pattern, content):
        short_hex = match.group(1).upper()
        # Expand #RGB to #RRGGBB
        hex_color = f"#{short_hex[0]}{short_hex[0]}{short_hex[1]}{short_hex[1]}{short_hex[2]}{short_hex[2]}"
        all_colors.append(hex_color)
    
    # Extract RGB/RGBA colors and convert to hex
    for match in re.finditer(rgb_pattern, content):
        try:
            r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
            if 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255:
                hex_color = f"#{r:02X}{g:02X}{b:02X}"
                all_colors.append(hex_color)
        except ValueError:
            continue
    
    # Filter out common non-brand colors (pure black, white, transparent equivalents)
    excluded_colors = {'#000000', '#FFFFFF', '#FEFEFE', '#010101', '#FDFDFD', '#020202'}
    filtered_colors = [c for c in all_colors if c not in excluded_colors]
    
    # If we filtered everything, use original list
    if not filtered_colors and all_colors:
        filtered_colors = all_colors
    
    # Count frequency and get top colors
    color_counts = Counter(filtered_colors)
    
    # Get unique colors sorted by frequency (most common first), max 10
    unique_colors = [color for color, count in color_counts.most_common(10)]
    
    return unique_colors


# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "deepseek/deepseek-r1-0528:free"  # Free model


def openrouter_web_search_fallback(url: str) -> Dict[str, Any]:
    """
    Fallback to OpenRouter Web Search when direct scraping fails (403, etc.)

    Args:
        url: The website URL to analyze

    Returns:
        Dict with content formatted like scraper output
    """
    try:
        if not OPENROUTER_API_KEY:
            raise Exception("OPENROUTER_API_KEY environment variable not set")

        logger.info(f"Using OpenRouter Web Search fallback for {url}")

        response = httpx.post(
            OPENROUTER_API_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": OPENROUTER_MODEL,
                "plugins": [{"id": "web", "engine": "native", "max_results": 5}],
                "messages": [{
                    "role": "user",
                    "content": f"""Analyze this website: {url}

Please provide:
1. Website/Company Title
2. Main headings and sections
3. Company description and what they do
4. Value proposition
5. Business niche/industry
6. Key services or products

Format your response with clear headings and paragraphs."""
                }]
            },
            timeout=30.0
        )

        response.raise_for_status()
        data = response.json()

        # Extract the AI response
        ai_content = data.get('choices', [{}])[0].get('message', {}).get('content', '')

        if not ai_content:
            raise Exception("No content returned from OpenRouter")

        # Format response to match scraper output
        formatted_content = f"TITLE: Analysis via Web Search\n\n{ai_content}"

        logger.info(f"OpenRouter Web Search successful for {url}")

        return {
            'url': url,
            'depth': 0,
            'content': formatted_content,
            'status': 'web_search_fallback',
            'links': set()
        }

    except Exception as e:
        logger.error(f"OpenRouter Web Search fallback failed for {url}: {str(e)}")
        return {
            'url': url,
            'depth': 0,
            'content': '',
            'status': 'error',
            'error': f"Web search fallback failed: {str(e)}",
            'links': set()
        }


class WebScraper:
    """Web scraper for extracting content from websites"""

    def __init__(self, max_depth: int = 1, delay: float = 0, max_pages: int = 10):
        self.max_depth = max_depth
        self.delay = delay
        self.max_pages = max_pages
        self.visited = set()
        self.session = httpx.Client(
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
            timeout=10.0
        )

    def is_valid_url(self, url: str, base_domain: str) -> bool:
        """Check if URL is valid and belongs to the same domain"""
        try:
            parsed = urlparse(url)
            base_parsed = urlparse(base_domain)
            return (parsed.netloc == base_parsed.netloc and
                    parsed.scheme in ['http', 'https'])
        except:
            return False

    def extract_text_content(self, soup: BeautifulSoup) -> str:
        """Extract meaningful text content from HTML"""
        # Remove non-content elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()

        text_parts = []

        # Get title
        title = soup.find('title')
        if title:
            text_parts.append(f"TITLE: {title.get_text().strip()}")

        # Get main content
        main_content = soup.find('main') or soup.find('article') or soup.find('body')
        if main_content:
            # Extract headings
            headings = main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            for heading in headings:
                text_parts.append(f"\n{heading.name.upper()}: {heading.get_text().strip()}")

            # Extract paragraphs
            paragraphs = main_content.find_all('p')
            for p in paragraphs:
                text = p.get_text().strip()
                if text:
                    text_parts.append(text)

            # Extract lists
            lists = main_content.find_all(['ul', 'ol'])
            for lst in lists:
                items = lst.find_all('li')
                for item in items:
                    text = item.get_text().strip()
                    if text:
                        text_parts.append(f"• {text}")

        return '\n'.join(text_parts)

    def get_links(self, soup: BeautifulSoup, base_url: str) -> set:
        """Extract all valid links from the page"""
        links = set()
        for link in soup.find_all('a', href=True):
            url = urljoin(base_url, link['href'])
            url = url.split('#')[0]  # Remove fragment
            if self.is_valid_url(url, base_url):
                links.add(url)
        return links

    def fetch_page(self, url: str, depth: int) -> Dict[str, Any]:
        """Fetch and parse a single page"""
        start_time = time.time()
        try:
            if self.delay > 0:
                time.sleep(self.delay)

            fetch_start = time.time()
            response = self.session.get(url)

            # Check for 403 or other client/server errors - trigger fallback
            if response.status_code >= 400:
                logger.warning(f"HTTP {response.status_code} for {url} - using OpenRouter Web Search fallback")
                return openrouter_web_search_fallback(url)

            response.raise_for_status()
            fetch_time = time.time() - fetch_start

            parse_start = time.time()
            soup = BeautifulSoup(response.content, 'html.parser')
            text_content = self.extract_text_content(soup)
            links = self.get_links(soup, url) if depth < self.max_depth else set()
            parse_time = time.time() - parse_start

            total_time = time.time() - start_time
            logger.info(f"Fetched {url} | Depth: {depth} | Fetch: {fetch_time:.2f}s | Parse: {parse_time:.2f}s | Total: {total_time:.2f}s | Links: {len(links)}")

            return {
                'url': url,
                'depth': depth,
                'content': text_content,
                'status': response.status_code,
                'links': links
            }
        except httpx.HTTPStatusError as e:
            # HTTP error - only use fallback for main page (depth 0), skip subpages
            if depth == 0:
                logger.warning(f"HTTP error fetching {url}: {str(e)} - using OpenRouter Web Search fallback")
                return openrouter_web_search_fallback(url)
            else:
                logger.warning(f"HTTP error fetching {url} (depth {depth}): {str(e)} - skipping subpage")
                return {
                    'url': url,
                    'depth': depth,
                    'content': '',
                    'status': 'error',
                    'error': str(e),
                    'links': set()
                }
        except Exception as e:
            # Other errors (network, timeout, etc.) - only use fallback for main page
            if depth == 0:
                logger.warning(f"Error fetching {url}: {str(e)} - trying OpenRouter Web Search fallback")
                fallback_result = openrouter_web_search_fallback(url)
                # If fallback also fails, return original error
                if fallback_result['status'] == 'error':
                    logger.error(f"Both scraping and fallback failed for {url}")
                    return {
                        'url': url,
                        'depth': depth,
                        'content': '',
                        'status': 'error',
                        'error': str(e),
                        'links': set()
                    }
                return fallback_result
            else:
                logger.warning(f"Error fetching {url} (depth {depth}): {str(e)} - skipping subpage")
                return {
                    'url': url,
                    'depth': depth,
                    'content': '',
                    'status': 'error',
                    'error': str(e),
                    'links': set()
                }


    def scrape(self, start_url: str) -> Dict[str, Any]:
        """Scrape website with concurrent requests up to max_depth"""
        scrape_start = time.time()
        logger.info(f"Starting scrape of {start_url} | Max depth: {self.max_depth} | Max pages: {self.max_pages}")

        results = {}
        to_scrape = [(start_url, 0)]
        self.visited.add(start_url)

        with ThreadPoolExecutor(max_workers=5) as executor:
            while to_scrape and len(results) < self.max_pages:
                current_batch = to_scrape[:min(5, self.max_pages - len(results))]
                to_scrape = to_scrape[len(current_batch):]

                futures = {executor.submit(self.fetch_page, url, depth): (url, depth)
                          for url, depth in current_batch}

                for future in as_completed(futures):
                    result = future.result()
                    url = result['url']
                    depth = result['depth']

                    results[url] = {
                        'depth': depth,
                        'content': result['content'],
                        'status': result['status']
                    }
                    if result.get('error'):
                        results[url]['error'] = result['error']

                    # Add new links to scrape
                    if depth < self.max_depth and len(results) < self.max_pages:
                        for link in result.get('links', []):
                            if link not in self.visited and len(self.visited) < self.max_pages:
                                self.visited.add(link)
                                to_scrape.append((link, depth + 1))

        total_time = time.time() - scrape_start
        logger.info(f"Scrape complete | Pages: {len(results)} | Total time: {total_time:.2f}s | Avg per page: {total_time/max(len(results), 1):.2f}s")
        return results

    def close(self):
        """Close the HTTP session"""
        self.session.close()


def format_scrape_as_text(results: Dict[str, Any]) -> str:
    """Format scraping results as plain text for AI analysis"""
    output = []
    output.append("=" * 80)
    output.append("WEBSITE SCRAPING RESULTS")
    output.append("=" * 80)
    output.append(f"\nTotal pages scraped: {len(results)}\n")

    for url, data in results.items():
        output.append("\n" + "=" * 80)
        output.append(f"URL: {url}")
        output.append(f"Depth Level: {data['depth']}")
        output.append(f"Status: {data['status']}")
        output.append("-" * 80)

        if data.get('error'):
            output.append(f"ERROR: {data['error']}")
        elif data['content']:
            output.append(data['content'])
        else:
            output.append("(No content extracted)")

        output.append("")

    output.append("\n" + "=" * 80)
    output.append("END OF SCRAPING RESULTS")
    output.append("=" * 80)

    return '\n'.join(output)


def analyze_website(url: str, max_depth: int = 1, max_pages: int = 10) -> Dict[str, Any]:
    """
    Analyze a website by scraping its content.

    Args:
        url: The website URL to analyze
        max_depth: Maximum depth to crawl (default: 1)
        max_pages: Maximum pages to scrape (default: 10)

    Returns:
        Dict with success status and scraped content
    """
    try:
        # Ensure URL has protocol
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        logger.info(f"Starting website analysis for: {url}")

        scraper = WebScraper(max_depth=max_depth, max_pages=max_pages)
        results = scraper.scrape(url)
        scraper.close()

        # Format results as text
        response_text = format_scrape_as_text(results)

        return {
            "success": True,
            "data": {
                "response_text": response_text,
                "pages_scraped": len(results),
                "results": results
            },
            "status_code": 200
        }

    except Exception as e:
        logger.error(f"Website analysis failed: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "status_code": None
        }
