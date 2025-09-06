#!/usr/bin/env python3
"""
Test script for GHL contacts retrieval
"""
import sys
import os
import json

# Add the Tools directory to Python path
sys.path.append('./Tools')

try:
    from GHL.Contacts.get_all_contacts import get_all_contacts
    
    print("🔍 Testing GHL Contacts API...")
    print("=" * 50)
    
    # Test with default parameters (should use config values)
    contacts = get_all_contacts()
    
    print(f"✅ Success! Retrieved contacts data")
    print(f"📊 Response type: {type(contacts)}")
    
    if isinstance(contacts, dict):
        print(f"🔑 Response keys: {list(contacts.keys())}")
        
        # Show contacts count if available
        if 'contacts' in contacts:
            contacts_list = contacts['contacts']
            print(f"👥 Total contacts found: {len(contacts_list)}")
            
            # Show first contact as sample
            if contacts_list and len(contacts_list) > 0:
                first_contact = contacts_list[0]
                print("\n📋 Sample contact:")
                print(f"   ID: {first_contact.get('id', 'N/A')}")
                print(f"   Name: {first_contact.get('firstName', '')} {first_contact.get('lastName', '')}")
                print(f"   Email: {first_contact.get('email', 'N/A')}")
                print(f"   Phone: {first_contact.get('phone', 'N/A')}")
        
        # Show pagination info if available
        if 'meta' in contacts:
            meta = contacts['meta']
            print(f"\n📄 Pagination info:")
            print(f"   Total: {meta.get('total', 'N/A')}")
            print(f"   Current Page: {meta.get('currentPage', 'N/A')}")
            print(f"   Next Page: {meta.get('nextPage', 'N/A')}")
    
    else:
        print(f"📄 Raw response (first 500 chars): {str(contacts)[:500]}")
        
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("   Make sure the GHL module structure is correct")
    
except ValueError as e:
    print(f"❌ Configuration Error: {e}")
    print("   Check if location_id and access_token are properly configured")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print(f"   Error type: {type(e).__name__}")
    
    # Show more details for requests exceptions
    if hasattr(e, 'response'):
        try:
            error_response = e.response.json()
            print(f"   API Response: {json.dumps(error_response, indent=2)}")
        except:
            print(f"   API Response (raw): {e.response.text}")

print("\n" + "=" * 50)
print("🏁 Test completed")