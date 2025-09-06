#!/usr/bin/env python3
"""
Script to enable debug browser mode in production
This will make the browser visible for debugging Facebook integration
"""

import os
import subprocess

def enable_debug_browser():
    """Enable debug browser mode in Heroku"""
    try:
        # Set the environment variable in Heroku
        cmd = ["heroku", "config:set", "DEBUG_BROWSER=true", "-a", "squidgy-back-919bc0659e35"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ DEBUG_BROWSER=true set in Heroku")
            print("🔍 Browser will now be VISIBLE during Facebook integration")
            print("🎯 Test the integration again - you should see a browser window")
        else:
            print(f"❌ Failed to set environment variable: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Manual setup: Run this command in terminal:")
        print("   heroku config:set DEBUG_BROWSER=true -a squidgy-back-919bc0659e35")

def disable_debug_browser():
    """Disable debug browser mode in Heroku"""
    try:
        cmd = ["heroku", "config:unset", "DEBUG_BROWSER", "-a", "squidgy-back-919bc0659e35"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ DEBUG_BROWSER removed from Heroku")
            print("🚀 Browser will now run HEADLESS in production")
        else:
            print(f"❌ Failed to unset environment variable: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Manual setup: Run this command in terminal:")
        print("   heroku config:unset DEBUG_BROWSER -a squidgy-back-919bc0659e35")

if __name__ == "__main__":
    print("🔧 Facebook Integration Debug Mode")
    print("=" * 40)
    print("1. Enable debug browser (VISIBLE)")
    print("2. Disable debug browser (HEADLESS)")
    print("3. Check current settings")
    
    choice = input("\nEnter choice (1/2/3): ").strip()
    
    if choice == "1":
        enable_debug_browser()
    elif choice == "2":
        disable_debug_browser()
    elif choice == "3":
        try:
            cmd = ["heroku", "config:get", "DEBUG_BROWSER", "-a", "squidgy-back-919bc0659e35"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            debug_value = result.stdout.strip()
            
            if debug_value.lower() == "true":
                print("🔍 DEBUG MODE: Browser is VISIBLE")
            else:
                print("🚀 PRODUCTION MODE: Browser is HEADLESS")
                
        except Exception as e:
            print(f"❌ Error checking config: {e}")
    else:
        print("❌ Invalid choice")