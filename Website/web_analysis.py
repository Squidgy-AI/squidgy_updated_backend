# Website/web_analysis.py - Web scraping and analysis module

import time
import logging
import httpx
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urljoin
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


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
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
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
