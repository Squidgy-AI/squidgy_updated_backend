#!/usr/bin/env python3
"""
Debug script using EXACT values from the Heroku logs
This replicates the exact API call that's failing with 422 error
"""

import asyncio
import httpx
import json

async def test_exact_user_creation():
    """Test user creation with EXACT values from the logs"""
    
    # EXACT values from the logs
    company_id = "lp2p1q27DrdGta1qGDJd"
    location_id = "pGR4zIkHS1pulopWjT3n"
    agency_token = "pit-e3d8d384-00cb-4744-8213-b1ab06ae71fe"
    
    # EXACT payload from the logs
    payload = {
        "companyId": "lp2p1q27DrdGta1qGDJd",
        "firstName": "Soma",
        "lastName": "Addakula",
        "email": "somashekhar34+pGR4zIkH@gmail.com",
        "password": "Dummy@123",
        "phone": "+17166044029",
        "type": "account",
        "role": "admin",
        "locationIds": [
            "pGR4zIkHS1pulopWjT3n"
        ],
        "permissions": {
            "campaignsEnabled": True,
            "campaignsReadOnly": False,
            "contactsEnabled": True,
            "workflowsEnabled": True,
            "workflowsReadOnly": False,
            "triggersEnabled": True,
            "funnelsEnabled": True,
            "websitesEnabled": True,
            "opportunitiesEnabled": True,
            "dashboardStatsEnabled": True,
            "bulkRequestsEnabled": True,
            "appointmentsEnabled": True,
            "reviewsEnabled": True,
            "onlineListingsEnabled": True,
            "phoneCallEnabled": True,
            "conversationsEnabled": True,
            "assignedDataOnly": False,
            "adwordsReportingEnabled": True,
            "membershipEnabled": True,
            "facebookAdsReportingEnabled": True,
            "attributionsReportingEnabled": True,
            "settingsEnabled": True,
            "tagsEnabled": True,
            "leadValueEnabled": True,
            "marketingEnabled": True,
            "agentReportingEnabled": True,
            "botService": True,
            "socialPlanner": True,
            "bloggingEnabled": True,
            "invoiceEnabled": True,
            "affiliateManagerEnabled": True,
            "contentAiEnabled": True,
            "refundsEnabled": True,
            "recordPaymentEnabled": True,
            "cancelSubscriptionEnabled": True,
            "paymentsEnabled": True,
            "communitiesEnabled": True,
            "exportPaymentsEnabled": True
        },
        "scopes": [
            "adPublishing.readonly",
            "adPublishing.write",
            "blogs.write",
            "calendars.readonly",
            "calendars.write",
            "calendars/events.write",
            "calendars/groups.write",
            "campaigns.write",
            "certificates.readonly",
            "certificates.write",
            "communities.write",
            "contacts.write",
            "contacts/bulkActions.write",
            "contentAI.write",
            "conversations.readonly",
            "conversations.write",
            "conversations/message.readonly",
            "conversations/message.write",
            "custom-menu-link.write",
            "dashboard/stats.readonly",
            "forms.write",
            "funnels.write",
            "gokollab.write",
            "invoices.readonly",
            "invoices.write",
            "invoices/schedule.readonly",
            "invoices/schedule.write",
            "invoices/template.readonly",
            "invoices/template.write",
            "locations/tags.readonly",
            "locations/tags.write",
            "marketing.write",
            "marketing/affiliate.write",
            "medias.readonly",
            "medias.write",
            "membership.write",
            "native-integrations.readonly",
            "native-integrations.write",
            "opportunities.write",
            "opportunities/bulkActions.write",
            "opportunities/leadValue.readonly",
            "prospecting.readonly",
            "prospecting.write",
            "prospecting/auditReport.write",
            "prospecting/reports.readonly",
            "qrcodes.write",
            "quizzes.write",
            "reporting/adwords.readonly",
            "reporting/agent.readonly",
            "reporting/attributions.readonly",
            "reporting/facebookAds.readonly",
            "reporting/phone.readonly",
            "reporting/reports.readonly",
            "reporting/reports.write",
            "reputation/listing.write",
            "reputation/review.write",
            "settings.write",
            "socialplanner/account.readonly",
            "socialplanner/account.write",
            "socialplanner/category.readonly",
            "socialplanner/category.write",
            "socialplanner/csv.readonly",
            "socialplanner/csv.write",
            "socialplanner/facebook.readonly",
            "socialplanner/filters.readonly",
            "socialplanner/group.write",
            "socialplanner/hashtag.readonly",
            "socialplanner/hashtag.write",
            "socialplanner/linkedin.readonly",
            "socialplanner/medias.readonly",
            "socialplanner/medias.write",
            "socialplanner/metatag.readonly",
            "socialplanner/notification.readonly",
            "socialplanner/notification.write",
            "socialplanner/oauth.readonly",
            "socialplanner/oauth.write",
            "socialplanner/post.readonly",
            "socialplanner/post.write",
            "socialplanner/recurring.readonly",
            "socialplanner/recurring.write",
            "socialplanner/review.readonly",
            "socialplanner/review.write",
            "socialplanner/rss.readonly",
            "socialplanner/rss.write",
            "socialplanner/search.readonly",
            "socialplanner/setting.readonly",
            "socialplanner/setting.write",
            "socialplanner/snapshot.readonly",
            "socialplanner/snapshot.write",
            "socialplanner/stat.readonly",
            "socialplanner/tag.readonly",
            "socialplanner/tag.write",
            "socialplanner/twitter.readonly",
            "socialplanner/watermarks.readonly",
            "socialplanner/watermarks.write",
            "surveys.write",
            "triggers.write",
            "voice-ai-agent-goals.readonly",
            "voice-ai-agent-goals.write",
            "voice-ai-agents.write",
            "voice-ai-dashboard.readonly",
            "websites.write",
            "wordpress.read",
            "wordpress.write",
            "workflows.write"
        ],
        "scopesAssignedToOnly": []
    }
    
    headers = {
        "Authorization": f"Bearer {agency_token}",
        "Version": "2021-07-28",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    print("🚀 Testing EXACT payload from logs")
    print("=" * 50)
    print(f"Company ID: {company_id}")
    print(f"Location ID: {location_id}")
    print(f"Token: {agency_token[:20]}...")
    print(f"Email: {payload['email']}")
    print(f"Scopes count: {len(payload['scopes'])}")
    print("=" * 50)
    
    print("\n🧪 Testing with ALL scopes (exact copy from logs)...")
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://services.leadconnectorhq.com/users/",
                json=payload,
                headers=headers
            )
        
        print(f"\n🌐 Response Status: {response.status_code}")
        print(f"📥 Response Body: {response.text}")
        
        if response.status_code in [200, 201]:
            print("✅ SUCCESS: User created successfully!")
        else:
            print(f"❌ FAILED: {response.status_code}")
            
            # If it's the scope error, let's test without scopes
            if "each value in scopes must be a valid enum value" in response.text:
                print("\n🔄 Testing WITHOUT scopes...")
                
                # Remove scopes and try again
                payload_no_scopes = payload.copy()
                del payload_no_scopes["scopes"]
                del payload_no_scopes["scopesAssignedToOnly"]
                
                # Use different email to avoid duplicate
                payload_no_scopes["email"] = "somashekhar34+test@gmail.com"
                
                response2 = await client.post(
                    "https://services.leadconnectorhq.com/users/",
                    json=payload_no_scopes,
                    headers=headers
                )
                
                print(f"🌐 No-scopes Response Status: {response2.status_code}")
                print(f"📥 No-scopes Response Body: {response2.text}")
                
                if response2.status_code in [200, 201]:
                    print("✅ SUCCESS WITHOUT SCOPES: The issue is definitely in the scopes!")
                else:
                    print("❌ STILL FAILED: Issue is not just scopes")
            
    except Exception as e:
        print(f"💥 EXCEPTION: {str(e)}")

async def test_individual_problematic_scopes():
    """Test the suspected problematic scopes individually"""
    
    company_id = "lp2p1q27DrdGta1qGDJd"
    location_id = "pGR4zIkHS1pulopWjT3n"
    agency_token = "pit-e3d8d384-00cb-4744-8213-b1ab06ae71fe"
    
    # Suspected problematic scopes from logs
    suspected_bad_scopes = [
        "payments/exports.write",
        "payments/refunds.write", 
        "payments/subscriptionsCancel.write"
    ]
    
    print("\n" + "="*50)
    print("🔍 Testing suspected problematic scopes individually...")
    
    headers = {
        "Authorization": f"Bearer {agency_token}",
        "Version": "2021-07-28",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    for i, scope in enumerate(suspected_bad_scopes):
        print(f"\n🧪 Testing scope: {scope}")
        
        payload = {
            "companyId": company_id,
            "firstName": "Test",
            "lastName": "User",
            "email": f"test+scope{i}@example.com",
            "password": "Dummy@123",
            "phone": "+17166044029",
            "type": "account",
            "role": "admin",
            "locationIds": [location_id],
            "scopes": [scope],  # Test just this one scope
            "scopesAssignedToOnly": []
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://services.leadconnectorhq.com/users/",
                    json=payload,
                    headers=headers
                )
            
            if response.status_code in [200, 201]:
                print(f"✅ {scope} is VALID")
            else:
                print(f"❌ {scope} is INVALID - {response.status_code}")
                print(f"   Error: {response.text}")
                
        except Exception as e:
            print(f"💥 {scope} caused exception: {str(e)}")

async def main():
    """Run all tests"""
    await test_exact_user_creation()
    await test_individual_problematic_scopes()

if __name__ == "__main__":
    asyncio.run(main())