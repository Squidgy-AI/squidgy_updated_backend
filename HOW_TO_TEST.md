# How to Test User Registration Flow

This guide shows you how to test the ACTUAL user registration flow and see all logs in real-time.

---

## Setup (3 Terminal Windows)

You need 3 terminals open to see everything:

### Terminal 1: Backend Server
```bash
cd /Users/somasekharaddakula/CascadeProjects/Backend_SquidgyBackend_Updated
source /Users/somasekharaddakula/CascadeProjects/TC_Soma/soma_TC_env/bin/activate
python3 main.py
```

**What you'll see**: Backend API logs, endpoint calls, database operations

---

### Terminal 2: Automation Service Logs (Heroku)
```bash
heroku logs --tail --app backgroundautomationuser1-1644057ede7b
```

**What you'll see**:
- Browser automation logs
- `[📊 INTERCEPT] Captured XXX requests` - Shows interceptor is working
- `[🔍 REQUEST] GHL API call to: ...` - Shows API calls
- `[✅ TOKENS] Found token-id (Firebase)` - Shows when token is captured
- `[📊 DEBUG] Total network requests intercepted: XXX` - Final count

**CRITICAL LOGS TO WATCH FOR**:
1. `[📧 EMAIL] Email age: X.X minutes` - Should be < 2 minutes
2. `[✅ EMAIL] This is a FRESH email` - Good! Using new OTP
3. `[❌ EMAIL] REJECTING - This email is X minutes old` - Bad! Using old OTP
4. `[📊 DEBUG] Total network requests intercepted: XXX` - Should be > 100
5. `[✅ TOKENS] Found token-id (Firebase)` - THIS IS SUCCESS!

---

### Terminal 3: Run Test Script
```bash
cd /Users/somasekharaddakula/CascadeProjects/Backend_SquidgyBackend_Updated
source /Users/somasekharaddakula/CascadeProjects/TC_Soma/soma_TC_env/bin/activate
python3 test_user_registration.py
```

**What you'll see**:
- Test user data
- HTTP response from backend
- Success/failure status
- Instructions to check database

---

## Step-by-Step Testing

### Step 1: Start All 3 Terminals

1. **Terminal 1**: Start backend server
2. **Terminal 2**: Start watching Heroku logs
3. Keep **Terminal 3** ready for test script

### Step 2: Run the Test

In Terminal 3:
```bash
python3 test_user_registration.py
```

Press ENTER when ready.

### Step 3: Watch the Logs

**In Terminal 1 (Backend)**, you'll see:
```
[GHL BACKGROUND] Creating GHL subaccount...
[GHL BACKGROUND] Subaccount created: location_id=XXXXX
[GHL BACKGROUND] Creating soma_ghl_user...
[GHL BACKGROUND] 🌐 Triggering BackgroundAutomationUser1...
```

**In Terminal 2 (Automation Service)**, you'll see:
```
[GHL COMPLETE] 🚀 Starting complete automation
[NAVIGATE] Going to Dashboard: https://app.gohighlevel.com/...
[LOGIN] Detected login page - filling credentials...
[LOGIN] ✅ Email filled successfully
[VERIFICATION] Email verification required!
[📧 EMAIL] Email age: 0.5 minutes  ← SHOULD BE < 2 MINUTES!
[✅ EMAIL] This is a FRESH email   ← GOOD!
[✅ VERIFICATION] All digits entered successfully!
[📊 INTERCEPT] Captured 50 requests so far...
[📊 INTERCEPT] Captured 100 requests so far...
[🔍 REQUEST] GHL API call to: https://backend.leadconnectorhq.com/...
[✅ TOKENS] Found token-id (Firebase): eyJhbGciOiJSUzI1NiIs...  ← SUCCESS!
[STEP 2.5] 🔥 Firebase Token captured! Saving to database...
[SUCCESS] Token capture workflow finished!
[📊 DEBUG] Total network requests intercepted: 284
```

---

## Success vs Failure

### ✅ Success Looks Like:

```
[✅ EMAIL] This is a FRESH email (0.5 minutes old)
[✅ VERIFICATION] All digits entered successfully!
[📊 INTERCEPT] Captured 200+ requests
[🔍 REQUEST] GHL API call to: ...
[✅ TOKENS] Found token-id (Firebase): eyJ...
[STEP 2.5] 🔥 Firebase Token captured!
[SUCCESS] Token capture workflow finished!
```

### ❌ Failure Looks Like:

**Old OTP Issue:**
```
[📧 EMAIL] Email age: 1787.3 minutes
[❌ EMAIL] REJECTING - This email is 1787.3 minutes old (> 2 minutes)
[INFO] OTP codes are only valid for a short time. This OTP is likely expired.
```
**Solution**: Wait for retry, new email should arrive

**No Requests Intercepted:**
```
[📊 DEBUG] Total network requests intercepted: 0
[⚠️ DEBUG] Network interceptor captured ZERO requests
```
**Solution**: Route setup failed, need to investigate

**Requests but No Token:**
```
[📊 DEBUG] Total network requests intercepted: 284
[✅ DEBUG] Interceptor is working (284 requests), but no GHL API calls with firebase_token
[FAILED] Automation completed but NO FIREBASE TOKEN was captured!
```
**Solution**: Page loaded but not authenticated (old OTP failed silently)

---

## Debugging Tips

### If you see "Email age: XXX minutes (> 2 minutes)":

The automation is using an OLD OTP code. This means:
1. New OTP email hasn't arrived yet, OR
2. "Send Security Code" button didn't actually send email

**Action**: Watch Terminal 2 for retries. It will attempt 30 times.

### If you see "Total network requests intercepted: 0":

The network interceptor isn't working.
**Action**: Check if Playwright browser setup succeeded

### If you see "Interceptor working but no firebase_token":

The page is making requests but NO requests have the `token-id` header.
This usually means the user is NOT actually logged in (authentication failed).

**Most Common Cause**: Old OTP code was used, verification appeared to succeed but actually didn't.

---

## After Test Completes

Check the database:
```bash
cd /Users/somasekharaddakula/CascadeProjects/Backend_SquidgyBackend_Updated
python3 << 'EOF'
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Use the firm_user_id from test output
firm_user_id = "TEST-XXXXX"  # Replace with actual test user ID

result = supabase.table('ghl_subaccounts').select('*').eq('firm_user_id', firm_user_id).execute()

if result.data:
    data = result.data[0]
    print("automation_status:", data.get('automation_status'))
    print("automation_error:", data.get('automation_error'))
    print("firebase_token:", "CAPTURED ✅" if data.get('firebase_token') else "NULL ❌")
EOF
```

---

## Quick Reference: Key Log Messages

| Log Message | Meaning | Good/Bad |
|------------|---------|----------|
| `[✅ EMAIL] This is a FRESH email (0.5 minutes old)` | Using new OTP | ✅ GOOD |
| `[❌ EMAIL] REJECTING - Email is 1787 minutes old` | Using old OTP | ❌ BAD |
| `[📊 INTERCEPT] Captured 200 requests` | Interceptor working | ✅ GOOD |
| `[🔍 REQUEST] GHL API call to: ...` | Making API calls | ✅ GOOD |
| `[✅ TOKENS] Found token-id (Firebase)` | Token captured! | ✅ SUCCESS! |
| `Total network requests intercepted: 0` | Interceptor failed | ❌ BAD |
| `Interceptor working but no firebase_token` | Not authenticated | ❌ BAD |

---

## Expected Timeline

1. **0-10 seconds**: Backend creates subaccount, triggers automation
2. **10-20 seconds**: Browser opens, navigates, login screen appears
3. **20-30 seconds**: Email/password filled, verification screen appears
4. **30-40 seconds**: OTP email received, code entered
5. **40-50 seconds**: Email verified, navigating to dashboard
6. **50-65 seconds**: Dashboard loads, API calls made, token captured
7. **65-70 seconds**: Token saved to database, automation complete

**Total**: ~60-70 seconds for successful run
