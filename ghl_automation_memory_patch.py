#!/usr/bin/env python3
"""
Quick patch for existing GHL automation memory issues
Apply these changes to fix sporadic failures
"""

# MEMORY OPTIMIZATION PATCHES
memory_optimized_browser_args = [
    "--disable-blink-features=AutomationControlled",
    "--disable-extensions",
    "--disable-plugins", 
    "--disable-images",  # NEW: Save memory by not loading images
    "--disable-background-networking",  # NEW: Reduce background activity
    "--disable-background-timer-throttling",  # NEW: Reduce timers
    "--memory-pressure-off",  # NEW: Disable memory pressure handling
    "--max_old_space_size=128",  # NEW: Limit Node.js heap size
    "--no-sandbox",
    "--headless",  # Force headless to save memory
]

# IMPROVED BUTTON SELECTORS
improved_button_selectors = [
    # Original selectors
    "text=Create new integration",
    "button:has-text('Create new integration')",
    "//button[contains(text(), 'Create new integration')]",
    
    # More flexible selectors (ADD THESE)
    "button:has-text('Create new')",
    "button:has-text('Create')", 
    "a:has-text('Create new integration')",
    "//span[contains(text(), 'Create')]/parent::button",
    "//*[contains(text(), 'Create') and contains(text(), 'integration')]",
    
    # CSS class based (ADD THESE)
    "[data-testid*='create']",
    ".btn:has-text('Create')",
    "button[class*='create']",
    "button[class*='primary']:has-text('Create')",
]

# MEMORY CLEANUP FUNCTION (ADD THIS)
async def cleanup_memory_aggressive(browser, context, page):
    """Add this function to your automation class"""
    import gc
    
    try:
        if page:
            await page.close()
        if context: 
            await context.close()
        if browser:
            await browser.close()
            
        # Force garbage collection
        gc.collect()
        
        print("🧹 Aggressive memory cleanup complete")
        
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")

# HEROKU MEMORY MANAGEMENT
def check_memory_usage():
    """Add this to monitor memory usage"""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    memory_mb = process.memory_info().rss / 1024 / 1024
    
    print(f"📊 Current memory usage: {memory_mb:.1f} MB")
    
    if memory_mb > 400:  # Warn at 400MB (close to 512MB limit)
        print("⚠️ HIGH MEMORY USAGE - Consider cleanup")
        return True
    return False

print("""
🔧 QUICK FIXES FOR GHL AUTOMATION:

1. MEMORY OPTIMIZATION:
   - Add --disable-images to browser args
   - Add --memory-pressure-off
   - Add --max_old_space_size=128
   - Force headless=True

2. IMPROVED BUTTON DETECTION:
   - Add more flexible selectors
   - Try CSS class based selectors
   - Add data-testid selectors

3. MEMORY MANAGEMENT:
   - Add aggressive cleanup function
   - Monitor memory usage
   - Close resources immediately after use

4. HEROKU SCALING:
   - Consider upgrading to Standard-1X (1GB RAM)
   - Or Standard-2X (2GB RAM) for reliable automation

Apply these patches to your existing ghl_automation_complete_playwright.py
""")

# HEROKU SCALING COMMANDS
print("""
💡 HEROKU SCALING OPTIONS:

# Check current dyno type
heroku ps -a your-app-name

# Upgrade to Standard-1X (1GB RAM)
heroku ps:resize web=standard-1x -a your-app-name

# Or Standard-2X (2GB RAM) for heavy automation
heroku ps:resize web=standard-2x -a your-app-name

# Check pricing: ~$25/month for Standard-1X
""")