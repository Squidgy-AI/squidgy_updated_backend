# BackgroundAutomationUser1 Service - Required Endpoints

The main backend now calls the external BackgroundAutomationUser1 service for all browser automation tasks, including website screenshots and favicon capture.

## Required Endpoints

### 1. POST `/website/screenshot`

Captures a full-page screenshot of a website using Playwright.

**Request:**
```json
{
  "url": "https://example.com",
  "session_id": "optional-session-id"  // optional
}
```

**Response (Success):**
```json
{
  "status": "success",
  "message": "Screenshot captured successfully",
  "path": "screenshots/session_id_screenshot.jpg",
  "public_url": "https://supabase-storage-url/...",
  "filename": "session_id_screenshot.jpg"
}
```

**Response (Error):**
```json
{
  "status": "error",
  "message": "Error description",
  "path": null
}
```

**Implementation Notes:**
- Use Playwright to launch headless browser
- Navigate to URL with 30s timeout
- Capture full-page screenshot as JPEG (quality 80)
- Upload to Supabase Storage `static` bucket under `screenshots/` folder
- Return public URL
- Filename format: `{session_id}_screenshot.jpg` or `screenshot_{timestamp}.jpg`

---

### 2. POST `/website/favicon`

Extracts and captures the favicon from a website using Playwright.

**Request:**
```json
{
  "url": "https://example.com",
  "session_id": "optional-session-id"  // optional
}
```

**Response (Success):**
```json
{
  "status": "success",
  "message": "Favicon captured successfully",
  "path": "favicons/session_id_logo.jpg",
  "public_url": "https://supabase-storage-url/...",
  "filename": "session_id_logo.jpg"
}
```

**Response (Error):**
```json
{
  "status": "error",
  "message": "Error description",
  "path": null
}
```

**Implementation Notes:**
- Use Playwright to launch headless browser and navigate to URL
- Use JavaScript to find favicon: `document.querySelector('link[rel="icon"]')` etc.
- Fallback to `/favicon.ico` if no favicon link found
- Download favicon using browser session
- Convert to JPEG using PIL/Pillow
- Upload to Supabase Storage `static` bucket under `favicons/` folder
- Return public URL
- Filename format: `{session_id}_logo.jpg` or `logo_{timestamp}.jpg`

---

## Environment Variables Required

The BackgroundAutomationUser1 service needs these environment variables:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
```

---

## Architecture Overview

```
┌─────────────────┐      HTTP POST      ┌──────────────────────────┐
│  Main Backend   │ ─────────────────▶  │ BackgroundAutomationUser1│
│ (FastAPI/Render)│                      │   (Flask/Heroku)         │
└─────────────────┘                      └──────────────────────────┘
                                                     │
                                                     │ Playwright
                                                     ▼
                                           ┌──────────────────┐
                                           │  Target Website  │
                                           └──────────────────┘
                                                     │
                                                     │ Upload
                                                     ▼
                                           ┌──────────────────┐
                                           │ Supabase Storage │
                                           └──────────────────┘
```

## Timeout Considerations

- Screenshot timeout: 120 seconds (main backend waits up to 2 minutes)
- Favicon timeout: 120 seconds
- Browser operations should complete within these limits
- Consider implementing queuing for long-running operations

## Testing

Test the endpoints using curl:

```bash
# Test screenshot
curl -X POST https://backgroundautomationuser1-xxxx.herokuapp.com/website/screenshot \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "session_id": "test123"}'

# Test favicon
curl -X POST https://backgroundautomationuser1-xxxx.herokuapp.com/website/favicon \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "session_id": "test123"}'
```
