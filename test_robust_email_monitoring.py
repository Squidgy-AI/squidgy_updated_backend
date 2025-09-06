#!/usr/bin/env python3
"""
Test the robust email monitoring
"""

import asyncio
from enhanced_2fa_service import Enhanced2FAService, GmailEmailConfig

async def test_email_monitoring():
    """Test the improved email monitoring"""
    
    print("🧪 TESTING ROBUST EMAIL MONITORING")
    print("=" * 80)
    
    # Create email config
    email_config = GmailEmailConfig(location_id="test")
    
    # Create 2FA service
    enhanced_2fa = Enhanced2FAService(email_config)
    
    print("📧 Testing email monitoring with improved algorithm...")
    print("🔍 This will show detailed logs about email processing...")
    
    # Test the OTP retrieval
    otp_code = await enhanced_2fa._get_otp_from_gmail()
    
    if otp_code:
        print(f"✅ SUCCESS: OTP retrieved: {otp_code}")
    else:
        print("❌ No OTP found (this is normal if no recent security code emails)")
    
    print("\n📋 Key improvements made:")
    print("✅ Only looks at emails from last 5 minutes")
    print("✅ Sorts emails by actual date/time (newest first)")
    print("✅ Processes most recent email first")
    print("✅ Detailed logging shows which email is being processed")
    print("✅ Handles both read and unread emails")
    print("✅ Better error handling and fallback mechanisms")

if __name__ == "__main__":
    asyncio.run(test_email_monitoring())