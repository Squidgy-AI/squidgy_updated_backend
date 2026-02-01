# 🔐 Token Capture Mechanism - Complete Step-by-Step Guide

## Overview
The browser automation uses **network request interception** to capture authentication tokens. When you log into GoHighLevel (GHL), the web application makes API calls to GHL's backend, and these API calls include authentication tokens in their headers. We intercept these network requests and extract the tokens.

---

## 📋 Step-by-Step Process

### **STEP 1: Browser Initialization with Network Interception** 🌐

**File**: `ghl_automation_complete_playwright.py`
**Method**: `setup_browser()` (lines 54-86)

```python
async def setup_browser(self):
    # 1. Start Playwright browser
    self.playwright = await async_playwright().start()

    # 2. Launch Chromium browser
    self.browser = await self.playwright.chromium.launch(
        headless=True,  # No visible browser on Heroku
        args=['--no-sandbox', '--disable-dev-shm-usage']
    )

    # 3. Create browser context and page
    self.context = await self.browser.new_context(
        viewport={'width': 1920, 'height': 1080}
    )
    self.page = await self.context.new_page()

    # 🔑 CRITICAL: Set up request interception
    # This intercepts EVERY network request the page makes
    await self.page.route('**/*', self.intercept_requests)
    #                      ^^^^^^   ^^^^^^^^^^^^^^^^^^^
    #                      Match     Callback function
    #                      all URLs  for each request
```

**What happens**:
- Playwright browser launches (headless on Heroku, visible for debugging locally)
- `page.route('**/*', ...)` registers a callback that will be called for **EVERY HTTP request** the page makes
- The `**/*` pattern means "intercept ALL URLs"
- Every request (images, CSS, JavaScript, API calls, etc.) goes through our `intercept_requests()` function

---

### **STEP 2: Network Request Interception** 🕵️

**Method**: `intercept_requests()` (lines 88-121)

```python
async def intercept_requests(self, route):
    """Called for EVERY network request"""

    # 1. Get the request object and its headers
    request = route.request
    headers = request.headers

    # 2. Check for Authorization header (access_token)
    auth_header = headers.get('authorization', '')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.replace('Bearer ', '').strip()
        if token and len(token) > 20:  # Sanity check
            self.access_token = token  # ✅ CAPTURED!
            print(f"[✅ TOKENS] Found Authorization Bearer token: {token[:20]}...")

    # 3. Check for token-id header (firebase_token)
    token_id = headers.get('token-id', '')
    if token_id and len(token_id) > 20:
        self.firebase_token = token_id  # ✅ CAPTURED!
        print(f"[✅ TOKENS] Found token-id (Firebase): {token_id[:20]}...")

        # 4. Extract user_id from firebase token JWT
        if not self.agency_user_id:
            user_id = self.extract_user_id_from_firebase_token(token_id)
            if user_id:
                self.agency_user_id = user_id  # ✅ EXTRACTED!

    # 5. Continue with the request (don't block it)
    await route.continue_()
```

**What happens**:
- Every time the page makes an HTTP request (to ANY URL), this function is called
- We inspect the request headers looking for:
  - `authorization: Bearer <token>` → access_token
  - `token-id: <firebase_token>` → firebase_token
- When found, we store them in instance variables
- The request continues normally (we're just "listening", not blocking)

---

### **STEP 3: User Login Flow** 🔐

**Methods**: `navigate_to_target()`, `handle_login_and_verification()`

#### 3.1: Navigate to Private Integrations Page

```python
# Go directly to the target URL
target_url = f"https://app.gohighlevel.com/v2/location/{location_id}/settings/private-integrations/"
await self.page.goto(target_url)
```

**What happens**:
- Browser tries to go to the Private Integrations page
- GHL detects user is not logged in
- **GHL redirects to login page** automatically

#### 3.2: Fill Login Credentials

```python
# Fill email field
await self.page.fill('input[placeholder="Your email address"]', email)
# email = "somashekhar34+MdY4KL72@gmail.com"

# Fill password field
await self.page.fill('input[placeholder="The password you picked"]', password)
# password = "Dummy@123"

# Click Sign In button
await self.page.click('button:has-text("Sign in")')
```

**What happens**:
- Automation fills in the hardcoded credentials
- Clicks "Sign In" button
- GHL processes login...

---

### **STEP 4: GHL Makes API Calls → Tokens Captured!** ⚡

After clicking "Sign In", GHL's frontend JavaScript makes several API calls to their backend:

#### Example API Call 1: Login Authentication
```
POST https://backend.leadconnectorhq.com/users/authenticate
Headers:
  Content-Type: application/json
Body:
  {
    "email": "somashekhar34+MdY4KL72@gmail.com",
    "password": "Dummy@123"
  }

Response:
  {
    "success": true,
    "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
    "firebase_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6ImY3NThlNTYz...",
    "expires_at": "2026-02-01T05:30:12Z"
  }
```

**Our interceptor doesn't catch this** because tokens are in the RESPONSE body, not request headers.

#### Example API Call 2: User Lookup (TOKENS IN HEADERS!)
```
GET https://backend.leadconnectorhq.com/users/lookup
Headers:
  authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...  ⬅️ ACCESS_TOKEN!
  token-id: eyJhbGciOiJSUzI1NiIsImtpZCI6ImY3NThlNTYz...      ⬅️ FIREBASE_TOKEN!
  channel: APP
  source: WEB_USER
  version: 2021-07-28
```

**✅ OUR INTERCEPTOR CATCHES THIS!**

```python
# In intercept_requests():
auth_header = headers.get('authorization')
# = "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
self.access_token = auth_header.replace('Bearer ', '')  # ✅ CAPTURED!

token_id = headers.get('token-id')
# = "eyJhbGciOiJSUzI1NiIsImtpZCI6ImY3NThlNTYz..."
self.firebase_token = token_id  # ✅ CAPTURED!
```

#### More API Calls with Tokens

After login, GHL makes MANY API calls, all with tokens in headers:

```
GET https://backend.leadconnectorhq.com/locations/{location_id}
Headers:
  authorization: Bearer <access_token>  ⬅️ Captured!
  token-id: <firebase_token>            ⬅️ Captured!

GET https://backend.leadconnectorhq.com/users/me
Headers:
  authorization: Bearer <access_token>  ⬅️ Captured again!
  token-id: <firebase_token>            ⬅️ Captured again!

GET https://backend.leadconnectorhq.com/locations/{location_id}/integrations
Headers:
  authorization: Bearer <access_token>  ⬅️ Captured again!
  token-id: <firebase_token>            ⬅️ Captured again!
```

**We capture tokens from the FIRST API call that contains them** and store in instance variables.

---

### **STEP 5: Handle 2FA (If Required)** 📧

If GHL requires 2FA verification:

#### 5.1: Click "Send Security Code" Button
```python
await self.page.click('button:has-text("Send Security Code")')
```

#### 5.2: Fetch OTP from Gmail
```python
otp_code = self.get_otp_from_gmail()
# Returns: "463787" (6-digit code)
```

**How `get_otp_from_gmail()` works**:
```python
# 1. Connect to Gmail via IMAP
mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
mail.login('somashekhar34@gmail.com', 'ytmfxlelgyojxjmf')  # App password

# 2. Search for latest security code email
search_criteria = '(FROM "noreply@emails.squidgy.ai" SUBJECT "Login security code")'
result, data = mail.search(None, search_criteria)

# 3. Fetch the latest email
latest_email_id = max(email_ids)
result, msg_data = mail.fetch(latest_email_id, '(BODY.PEEK[])')

# 4. Parse email body to extract OTP
# Email contains: "...login code for logging into app.gohighlevel.com is 463787"
otp_match = re.search(r'login code for logging into app\.gohighlevel\.com is (\d{6})', email_body)
otp = otp_match.group(1)  # "463787"
```

#### 5.3: Enter OTP into Browser
```python
# Find the 6 OTP input fields
digit_inputs = await self.page.locator('input[maxlength="1"]').all()
# Found 6 inputs

# Fill each digit
for i, digit in enumerate("463787"):
    await digit_inputs[i].fill(digit)
    # Input 0: "4"
    # Input 1: "6"
    # Input 2: "3"
    # Input 3: "7"
    # Input 4: "8"
    # Input 5: "7"
```

#### 5.4: GHL Verifies OTP → More API Calls with Tokens!

After entering OTP, GHL makes verification API calls:

```
POST https://backend.leadconnectorhq.com/users/verify-otp
Headers:
  authorization: Bearer <access_token>  ⬅️ Already captured!
  token-id: <firebase_token>            ⬅️ Already captured!
Body:
  { "code": "463787" }
```

**Our interceptor sees this too** (but tokens already captured from previous calls).

---

### **STEP 6: Token Extraction from Firebase JWT** 🔓

**Method**: `extract_user_id_from_firebase_token()` (lines 234-253)

The firebase_token is a **JWT (JSON Web Token)** with 3 parts:

```
eyJhbGciOiJSUzI1NiIsImtpZCI6ImY3NThlNTYz...
  ↑ Header (base64)

.eyJ1c2VyX2lkIjoia2F1UDhNa2FvUFUzWGFzNzlucGci...
  ↑ Payload (base64) - CONTAINS USER_ID!

.dWwxJfidYn3kDj9f...
  ↑ Signature
```

**Decode the payload**:

```python
# 1. Split JWT into 3 parts
parts = firebase_token.split('.')
# parts[0] = header (we don't need this)
# parts[1] = payload (THIS CONTAINS user_id!)
# parts[2] = signature (we don't need this)

# 2. Get the payload part
payload_part = parts[1]

# 3. Add base64 padding if needed
padding = 4 - len(payload_part) % 4
if padding != 4:
    payload_part += '=' * padding

# 4. Decode from base64
payload_json = base64.urlsafe_b64decode(payload_part)

# 5. Parse JSON
payload = json.loads(payload_json)
# Result:
{
  "user_id": "k2uP8MkaoPU3Xas79npg",  # ⬅️ THIS!
  "company_id": "lp2p1q27DrdGta1qGDJd",
  "role": "admin",
  "type": "agency",
  "locations": ["MdY4KL72E0lc7TqMm3H0"],
  "iat": 1769920218,
  "exp": 1769923818
}

# 6. Extract user_id
agency_user_id = payload.get('user_id')
# = "k2uP8MkaoPU3Xas79npg"
```

---

### **STEP 7: Navigation to Private Integrations** 🎯

After successful login and 2FA:

```python
# GHL redirects to original target URL
final_url = self.page.url
# = "https://app.gohighlevel.com/v2/location/MdY4KL72E0lc7TqMm3H0/settings/private-integrations/"

# Page loads → GHL makes MORE API calls with tokens
GET https://backend.leadconnectorhq.com/locations/MdY4KL72E0lc7TqMm3H0/integrations/private
Headers:
  authorization: Bearer <access_token>  ⬅️ Already captured!
  token-id: <firebase_token>            ⬅️ Already captured!
```

---

### **STEP 8: Create PIT Token** 🔑

After navigation, automation creates a Private Integration Token:

```python
# Click "Create new integration" button
await self.page.click('#no-apps-found-btn-positive-action')

# Fill integration name
await self.page.fill('input[placeholder*="name"]', 'location key')

# Select scopes (checkboxes)
# ... select 15 different scopes ...

# Click Create button
await self.page.click('button:has-text("Create")')

# GHL creates the PIT token via API call
POST https://backend.leadconnectorhq.com/locations/{location_id}/integrations/private
Headers:
  authorization: Bearer <access_token>  ⬅️ Using captured token!
  token-id: <firebase_token>            ⬅️ Using captured token!
Body:
  {
    "name": "location key",
    "scopes": ["contacts.readonly", "contacts.write", ...]
  }

Response:
  {
    "success": true,
    "token": "pit-f7092854-a6de-4748-bc12-129eca6a6fa7"  # ⬅️ PIT TOKEN!
  }
```

---

## 📊 Summary: When Are Tokens Captured?

| **Event** | **API Calls Made** | **Tokens Present?** | **Result** |
|-----------|-------------------|---------------------|------------|
| Click "Sign In" | POST `/users/authenticate` | ❌ No (tokens in response body) | No capture |
| After login success | GET `/users/lookup`<br>GET `/users/me`<br>GET `/locations/{id}` | ✅ Yes (in headers) | **✅ CAPTURED!** |
| Click "Send Code" | POST `/users/send-otp` | ✅ Yes | Already captured |
| Enter OTP | POST `/users/verify-otp` | ✅ Yes | Already captured |
| Navigate to page | GET `/locations/{id}/integrations`<br>GET `/locations/{id}/settings` | ✅ Yes | Already captured |
| Create PIT | POST `/locations/{id}/integrations/private` | ✅ Yes (using captured tokens) | Returns PIT token |

---

## 🎯 Key Insights

### Why Network Interception Works:
1. **Modern web apps make tons of API calls** - After login, GHL frontend makes 10-20+ API calls
2. **Every API call includes auth tokens** - For security, every request to GHL backend needs authentication
3. **Playwright can see ALL network traffic** - Network interception gives us access to every request
4. **Tokens are reused** - The same access_token and firebase_token are used for ALL subsequent API calls

### Why We Don't Need GHL's Login API:
- We don't call GHL's authentication API directly
- We just fill the login form like a real user would
- GHL's frontend JavaScript handles the actual authentication
- We **passively listen** to the network traffic and extract tokens

### Token Lifetime:
- **access_token**: Expires in ~1 hour (JWT with `exp` claim)
- **firebase_token**: Long-lived (days/weeks)
- **pit_token**: Long-lived API key (never expires unless revoked)

---

## 🔧 What We Capture:

```python
# After automation completes:
automation.access_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
automation.firebase_token = "eyJhbGciOiJSUzI1NiIsImtpZCI6ImY3NThlNTYz..."
automation.agency_user_id = "k2uP8MkaoPU3Xas79npg"  # Extracted from firebase_token
automation.pit_token = "pit-f7092854-a6de-4748-bc12-129eca6a6fa7"
automation.facebook_pages = [...]  # Fetched using tokens
automation.connected_pages = [...]  # Filtered from facebook_pages
```

All of this is then saved to the Supabase database! 💾
