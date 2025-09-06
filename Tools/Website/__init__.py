# Website Analysis Tools
# Contains website screenshot and favicon capture functionality

from .web_scrape import capture_website_screenshot, capture_website_screenshot_sync, get_website_favicon, get_website_favicon_async

# For backward compatibility, alias the sync version
capture_website_screenshot_async = capture_website_screenshot

__all__ = [
    'capture_website_screenshot', 
    'capture_website_screenshot_async',
    'get_website_favicon',
    'get_website_favicon_async'
]