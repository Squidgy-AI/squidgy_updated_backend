#!/usr/bin/env python3
"""
🧪 TEST OUTLOOK 2FA INTEGRATION
===============================
Test Microsoft Outlook email monitoring for GHL 2FA codes
"""

import asyncio
import os
from enhanced_2fa_service import Enhanced2FAService, OutlookEmailConfig

async def test_outlook_email_connection():
    """Test connection to Outlook email"""
    
    print("🧪 TESTING OUTLOOK EMAIL CONNECTION")
    print("=" * 50)
    
    # Configure for your specific email
    email_config = OutlookEmailConfig()
    email_config.email_address = os.environ.get("OUTLOOK_2FA_EMAIL", "sa+01@squidgy.ai")
    email_config.email_password = os.environ.get("OUTLOOK_2FA_PASSWORD", "your-password")
    
    print(f"📧 Testing email: {email_config.email_address}")
    print(f"🏢 IMAP server: {email_config.imap_server}")
    
    # Create service
    service = Enhanced2FAService(email_config)
    
    try:
        # Test email connection
        print("\n🔌 Testing email connection...")
        otp = await service._get_otp_from_outlook()
        
        if otp:
            print(f"✅ SUCCESS: Found OTP code: {otp}")
        else:
            print("ℹ️ No OTP found in recent emails (this is normal if no 2FA was recently sent)")
            
        print("✅ Email connection successful!")
        
    except Exception as e:
        print(f"❌ Email connection failed: {e}")
        print("\n💡 Troubleshooting:")
        print("1. Check if email address is correct")
        print("2. Verify app-specific password is set")
        print("3. Ensure IMAP is enabled in Outlook")
        print("4. Check environment variables")

def print_setup_instructions():
    """Print setup instructions for Outlook email"""
    
    print("\n📋 OUTLOOK EMAIL SETUP INSTRUCTIONS")
    print("=" * 50)
    print("1. **Enable IMAP in Outlook:**")
    print("   - Go to Outlook.com → Settings → Mail → Sync email")
    print("   - Enable IMAP access")
    print()
    print("2. **Create App-Specific Password:**")
    print("   - Go to Microsoft Account → Security → Advanced security options")
    print("   - Generate app password for 'Email apps'")
    print()
    print("3. **Set Environment Variables:**")
    print("   export OUTLOOK_2FA_EMAIL='sa+01@squidgy.ai'")
    print("   export OUTLOOK_2FA_PASSWORD='your-app-password'")
    print()
    print("4. **Or set in Heroku:**")
    print("   heroku config:set OUTLOOK_2FA_EMAIL=sa+01@squidgy.ai")
    print("   heroku config:set OUTLOOK_2FA_PASSWORD=your-app-password")

async def test_2fa_patterns():
    """Test OTP extraction patterns"""
    
    print("\n🔍 TESTING OTP EXTRACTION PATTERNS")
    print("=" * 50)
    
    email_config = OutlookEmailConfig()
    service = Enhanced2FAService(email_config)
    
    # Test email bodies
    test_emails = [
        "Your GoHighLevel verification code is: 123456",
        "Security code: 789012",
        "Your code is 456789 for GoHighLevel login",
        "Access code 321654",
        "Login verification: 987654",
        "Code: 135246",
        "456123",  # Just numbers
    ]
    
    for i, body in enumerate(test_emails, 1):
        otp = service._extract_otp_from_body(body)
        status = "✅" if otp else "❌"
        print(f"{status} Test {i}: '{body}' → {otp}")

if __name__ == "__main__":
    print("🚀 OUTLOOK 2FA TEST SUITE")
    print("=" * 50)
    
    print_setup_instructions()
    
    print("\n🧪 Running tests...")
    
    # Test OTP patterns
    asyncio.run(test_2fa_patterns())
    
    # Test email connection
    asyncio.run(test_outlook_email_connection())
    
    print("\n✅ Tests complete!")
    print("\n💡 Next steps:")
    print("1. Set up your Outlook email credentials")
    print("2. Test the full 2FA flow in browser automation")
    print("3. Deploy to production with environment variables")