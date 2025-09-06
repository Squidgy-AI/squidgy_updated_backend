#!/usr/bin/env python3
"""
Test the focused email monitoring (UNSEEN security emails only)
"""

import asyncio
from enhanced_2fa_service import Enhanced2FAService, GmailEmailConfig

async def test_focused_email_monitoring():
    """Test the improved focused email monitoring"""
    
    print("🎯 TESTING FOCUSED EMAIL MONITORING")
    print("=" * 80)
    print("🔍 This version will ONLY look for:")
    print("   ✅ UNSEEN emails (fresh, not read)")
    print("   ✅ From specific senders (noreply@talk.onetoo.com, etc.)")
    print("   ✅ With security-related subjects ('Login security code', etc.)")
    print("   ✅ Sorted by date (newest first)")
    print("=" * 80)
    
    # Create email config
    email_config = GmailEmailConfig(location_id="test")
    
    # Create 2FA service
    enhanced_2fa = Enhanced2FAService(email_config)
    
    print("\n📧 Testing focused email monitoring...")
    
    # Test the OTP retrieval
    otp_code = await enhanced_2fa._get_otp_from_gmail()
    
    if otp_code:
        print(f"\n✅ SUCCESS: FRESH OTP retrieved: {otp_code}")
        print("🎉 This should be the latest, unused security code!")
    else:
        print("\n❌ No FRESH OTP found")
        print("💡 This is normal if no new security code emails were sent recently")
    
    print("\n📋 Key improvements made:")
    print("🎯 FOCUSED SEARCH: Only looks at UNSEEN emails")
    print("📧 SPECIFIC SENDERS: Only from noreply@talk.onetoo.com and GHL senders")
    print("🔍 SUBJECT FILTERING: Only emails with 'login security code' etc.")
    print("📅 NEWEST FIRST: Processes most recent email first")
    print("⏭️ SKIPS TUTORING: Ignores tutoring and other non-security emails")
    print("🚫 NO OLD CODES: Won't pick up expired/used codes")

if __name__ == "__main__":
    asyncio.run(test_focused_email_monitoring())