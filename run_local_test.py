#!/usr/bin/env python3
"""
Simple script to run the existing ghl_automation_complete_playwright.py locally
"""

import asyncio
import os
from ghl_automation_complete_playwright import HighLevelCompleteAutomationPlaywright

# Set required environment variables
os.environ['HIGHLEVEL_EMAIL'] = 'somashekhar34+MdY4KL72@gmail.com'
os.environ['HIGHLEVEL_PASSWORD'] = 'Dummy@123'
os.environ['GMAIL_2FA_EMAIL'] = 'somashekhar34@gmail.com'
os.environ['GMAIL_2FA_APP_PASSWORD'] = 'ytmfxlelgyojxjmf'

async def main():
    print("🚀 Running GHL Automation locally...")
    print("Using location: 8cBG0ykKKib7B9EP2PuD")
    
    # Create automation instance (not headless so you can see)
    automation = HighLevelCompleteAutomationPlaywright(headless=False)
    
    # Run the automation
    result = await automation.run_automation(
        email="somashekhar34+MdY4KL72@gmail.com",
        password="Dummy@123", 
        location_id="8cBG0ykKKib7B9EP2PuD",
        firm_user_id="test-local",
        agent_id="SOL",
        ghl_user_id="test-local-user",
        save_to_database=False
    )
    
    print(f"\n✅ Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())