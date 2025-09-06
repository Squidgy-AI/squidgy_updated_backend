#!/usr/bin/env python3
"""
Memory-optimized fixes for GHL automation sporadic failures
"""

import gc
import asyncio
from playwright.async_api import async_playwright

class GHLAutomationMemoryFix:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
    
    async def setup_browser_optimized(self):
        """Memory-optimized browser setup"""
        try:
            self.playwright = await async_playwright().start()
            
            # Memory-optimized browser args
            browser_args = [
                "--disable-blink-features=AutomationControlled",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-images",  # Save memory by not loading images
                "--disable-javascript-harmony-shipping",
                "--disable-background-networking",
                "--disable-background-timer-throttling",
                "--disable-renderer-backgrounding",
                "--disable-backgrounding-occluded-windows",
                "--memory-pressure-off",  # Disable memory pressure handling
                "--max_old_space_size=128",  # Limit Node.js memory
                "--no-sandbox",
                "--headless",  # Force headless to save memory
            ]
            
            self.browser = await self.playwright.chromium.launch(
                headless=True,  # Always headless to save memory
                args=browser_args
            )
            
            # Create context with minimal resources
            self.context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                java_script_enabled=True,
                ignore_https_errors=True,
                bypass_csp=True
            )
            
            # Create single page
            self.page = await self.context.new_page()
            
            # Disable resource loading to save memory
            await self.page.route("**/*.{png,jpg,jpeg,gif,webp,svg,css,woff,woff2}", 
                                lambda route: route.abort())
            
            print("✅ Memory-optimized browser setup complete")
            return True
            
        except Exception as e:
            print(f"❌ Browser setup failed: {e}")
            return False
    
    async def find_create_button_improved(self):
        """Improved button detection with more selectors and retries"""
        
        # Extended list of selectors to try
        button_selectors = [
            # Original selectors
            "text=Create new integration",
            "button:has-text('Create new integration')",
            "//button[contains(text(), 'Create new integration')]",
            
            # More flexible selectors
            "button:has-text('Create new')",
            "button:has-text('Create')",
            "a:has-text('Create new integration')",
            "//span[contains(text(), 'Create')]/parent::button",
            "//*[contains(text(), 'Create') and contains(text(), 'integration')]",
            
            # CSS class based
            "[data-testid*='create']",
            ".btn:has-text('Create')",
            "button[class*='create']",
            "button[class*='primary']:has-text('Create')",
            
            # Broader search
            "button, a, [role='button']",  # Find all clickable elements
        ]
        
        max_attempts = 3
        
        for attempt in range(max_attempts):
            print(f"🔄 Button search attempt {attempt + 1}/{max_attempts}")
            
            # Wait for page to be stable
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            
            # Try each selector
            for i, selector in enumerate(button_selectors):
                try:
                    print(f"   Trying selector {i+1}: {selector[:50]}...")
                    
                    if selector == "button, a, [role='button']":
                        # Special case: find all clickable elements and filter
                        elements = await self.page.query_selector_all(selector)
                        for element in elements:
                            text = await element.inner_text()
                            if 'create' in text.lower() and 'integration' in text.lower():
                                print(f"✅ Found button with text: '{text}'")
                                return element
                    else:
                        # Regular selector
                        element = await self.page.wait_for_selector(selector, timeout=3000)
                        if element:
                            text = await element.inner_text()
                            print(f"✅ Found button: '{text}'")
                            return element
                            
                except Exception:
                    continue
            
            # If not found, wait and try again
            if attempt < max_attempts - 1:
                print("   ⏳ Waiting 5 seconds before retry...")
                await asyncio.sleep(5)
                
                # Try scrolling to reveal hidden elements
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)
                await self.page.evaluate("window.scrollTo(0, 0)")
        
        print("❌ Could not find Create new integration button")
        return None
    
    async def cleanup_memory(self):
        """Aggressive memory cleanup"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
                
            # Python garbage collection
            gc.collect()
            
            print("🧹 Memory cleanup complete")
            
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")

# Quick test function
async def test_memory_optimization():
    automation = GHLAutomationMemoryFix()
    
    try:
        # Test browser setup
        if await automation.setup_browser_optimized():
            print("✅ Memory-optimized browser works")
            
            # Test navigation to a simple page
            await automation.page.goto("https://app.onetoo.com/", timeout=30000)
            print("✅ Navigation test passed")
            
        else:
            print("❌ Browser setup failed")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        await automation.cleanup_memory()

if __name__ == "__main__":
    asyncio.run(test_memory_optimization())