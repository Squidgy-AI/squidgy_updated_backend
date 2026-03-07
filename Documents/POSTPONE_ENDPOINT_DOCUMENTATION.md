# Social Media Post Postpone Endpoint Documentation

## Overview
This endpoint allows users to postpone scheduled social media posts. It can be accessed via email links (returns HTML) or programmatically via API calls (returns JSON).

## Endpoint Details

**URL:** `https://squidgy-backend-00f664bf1f3d.herokuapp.com/api/social/scheduled/posts/{post_id}/postpone`

**Method:** `GET`

**Authentication:** None required (uses query parameters for identification)

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `post_id` | string | Yes | - | The ID of the social media post to postpone (path parameter) |
| `firm_user_id` | string | Yes | - | The user ID (query parameter) |
| `agent_id` | string | No | "SOL" | The agent ID (query parameter) |
| `format` | string | No | auto-detect | Force response format: 'html' or 'json' (query parameter) |

## Usage in Email

### Email Link Format

```
https://squidgy-backend-00f664bf1f3d.herokuapp.com/api/social/scheduled/posts/{post_id}/postpone?firm_user_id={user_id}&agent_id=SOL
```

### Example Email Link

```
https://squidgy-backend-00f664bf1f3d.herokuapp.com/api/social/scheduled/posts/abc123xyz/postpone?firm_user_id=user_456&agent_id=SOL
```

### Email Template Example

```html
<p>Your social media post is scheduled for publication soon.</p>
<p>If you'd like to postpone this post, click the button below:</p>
<a href="https://squidgy-backend-00f664bf1f3d.herokuapp.com/api/social/scheduled/posts/{{post_id}}/postpone?firm_user_id={{firm_user_id}}&agent_id={{agent_id}}" 
   style="display: inline-block; background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px;">
   Postpone Post
</a>
```

### User Experience (Email Flow)

1. User receives email with postpone link
2. User clicks the link in their email client
3. Browser opens and displays a beautiful success page with:
   - Animated checkmark icon
   - "Post Postponed Successfully!" message
   - Post details (Post ID and schedule status)
   - "Go to Dashboard" button linking to `https://app.squidgy.ai/`

## Response Formats

### HTML Response (Browser/Email)

When accessed from a browser (via email link), the endpoint returns a styled HTML page.

**Success Response:**
- Status Code: `200 OK`
- Content-Type: `text/html`
- Displays success page with dashboard redirect button

**Error Response:**
- Status Code: `400`, `404`, or `500`
- Content-Type: `text/html`
- Displays error page with error details and dashboard redirect button

### JSON Response (API Call)

When accessed programmatically with `Accept: application/json` header, returns JSON.

**Success Response:**
```json
{
  "success": true,
  "message": "Post postponed successfully to 2099-12-31T23:59:59.999Z",
  "old_post_id": "abc123xyz",
  "new_post_id": "xyz789abc",
  "new_schedule_date": "2099-12-31T23:59:59.999Z",
  "ghl_response": { ... }
}
```

**Error Response:**
```json
{
  "detail": "Error message here"
}
```

## How It Works

1. **Content Negotiation**: The endpoint detects the request source by checking the `Accept` header or `format` parameter
   - Browser requests (from email): `Accept: text/html` → Returns HTML
   - API requests: `Accept: application/json` → Returns JSON
   - Override with `?format=html` or `?format=json` query parameter

2. **Post Postponement Process**:
   - Fetches the existing post from GHL (GoHighLevel)
   - Validates the post can be postponed (not already published)
   - Deletes the original scheduled post
   - Recreates the post with a far-future date (2099-12-31)
   - Updates the internal tracking database

3. **Error Handling**: All errors return appropriate responses based on request type:
   - Missing credentials
   - Post not found
   - Already published posts
   - API failures

## Error Scenarios

| Error | Status Code | Description |
|-------|-------------|-------------|
| GHL account not found | 404 | User hasn't completed GHL setup |
| Missing credentials | 400 | Location ID or PIT token missing |
| Post not found | 4xx | Invalid post ID or post doesn't exist |
| Already published | 400 | Cannot postpone posts that are already published |
| API failure | 500 | GHL API error or internal server error |

## Frontend Integration

When calling from the frontend (e.g., Social Media Generated Content tab):

```typescript
const response = await fetch(
  `https://squidgy-backend-00f664bf1f3d.herokuapp.com/api/social/scheduled/posts/${postId}/postpone?firm_user_id=${userId}&agent_id=${agentId}`,
  {
    method: 'GET',
    headers: {
      'Accept': 'application/json'
    }
  }
);

const data = await response.json();
if (data.success) {
  console.log('Post postponed:', data.new_post_id);
}
```

## Testing

### Test Email Link (Replace with actual values)
```
https://squidgy-backend-00f664bf1f3d.herokuapp.com/api/social/scheduled/posts/TEST_POST_ID/postpone?firm_user_id=TEST_USER_ID&agent_id=SOL
```

### Test via Browser
Simply paste the URL with valid parameters into a browser to see the HTML response.

**Force HTML response (useful for testing):**
```
https://squidgy-backend-00f664bf1f3d.herokuapp.com/api/social/scheduled/posts/TEST_POST_ID/postpone?firm_user_id=TEST_USER_ID&agent_id=SOL&format=html
```

### Test via API
Use curl or Postman with `Accept: application/json` header to see JSON response.

```bash
curl -H "Accept: application/json" \
  "https://squidgy-backend-00f664bf1f3d.herokuapp.com/api/social/scheduled/posts/POST_ID/postpone?firm_user_id=USER_ID&agent_id=SOL"
```

## Notes

- The postponed post is scheduled for 2099-12-31, effectively removing it from the active schedule
- The original post is deleted and recreated to avoid GHL's immediate publishing behavior
- The endpoint maintains backward compatibility with existing frontend code
- All HTML pages include a redirect button to the dashboard at `https://app.squidgy.ai/`
- Use `?format=html` parameter to force HTML response for testing (bypasses Accept header detection)
- Use `?format=json` parameter to force JSON response
