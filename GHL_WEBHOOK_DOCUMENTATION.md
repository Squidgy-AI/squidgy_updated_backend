# GHL Message Webhook Implementation

## Overview
This document describes the webhook implementation for receiving messages from GoHighLevel (GHL) and displaying them as notifications in the Squidgy platform.

## Architecture Flow
```
Customer → Messenger/SMS → GHL → Webhook → Squidgy Backend → Database → Squidgy Frontend
                                     ↓
                              WebSocket → Real-time Notification
```

## 1. Webhook Endpoint

### URL
```
POST /api/webhooks/ghl/messages
```

### Purpose
Receives incoming messages from GHL when customers send messages through various channels (SMS, Facebook Messenger, Instagram, etc.)

### Request Format
```json
{
  "ghl_location_id": "string (required)",
  "ghl_contact_id": "string (required)",
  "message": "string (required)",
  "sender_name": "string (optional)",
  "sender_phone": "string (optional)",
  "sender_email": "string (optional)",
  "message_type": "string (optional, default: SMS)",
  "conversation_id": "string (optional)",
  "timestamp": "string (optional, ISO format)",
  "metadata": {
    // Any additional data from GHL
  }
}
```

### Response Format
```json
{
  "success": true,
  "notification_id": "uuid",
  "message": "Notification received and stored successfully"
}
```

## 2. Database Schema

### Table: `notifications`

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| ghl_location_id | VARCHAR(255) | GHL Location/Account ID |
| ghl_contact_id | VARCHAR(255) | GHL Contact ID |
| message_content | TEXT | The actual message |
| message_type | VARCHAR(50) | SMS, Facebook, Instagram, etc. |
| sender_name | VARCHAR(255) | Name of the sender |
| sender_phone | VARCHAR(50) | Phone number |
| sender_email | VARCHAR(255) | Email address |
| conversation_id | VARCHAR(255) | Thread/conversation ID |
| read_status | BOOLEAN | Read/unread status |
| responded_status | BOOLEAN | Whether responded |
| metadata | JSONB | Additional data |
| created_at | TIMESTAMP | When received |
| updated_at | TIMESTAMP | Last modified |

### Run the migration:
```sql
-- Execute the file: create_notifications_table.sql
```

## 3. API Endpoints

### Get User Notifications
```
GET /api/notifications/{user_id}
```
**Query Parameters:**
- `limit`: Number of notifications (default: 50)
- `offset`: Pagination offset (default: 0)
- `unread_only`: Filter only unread (default: false)

**Response:**
```json
{
  "notifications": [...],
  "total": 100,
  "unread_count": 5,
  "limit": 50,
  "offset": 0
}
```

### Mark as Read
```
PUT /api/notifications/{notification_id}/read
```

### Mark All as Read
```
PUT /api/notifications/user/{user_id}/read-all
```

## 4. Real-time Updates

The webhook automatically sends real-time notifications via WebSocket to connected users:

```javascript
// WebSocket message format
{
  "type": "notification",
  "notification_id": "uuid",
  "message": "Customer message",
  "sender_name": "John Doe",
  "message_type": "SMS",
  "timestamp": "ISO timestamp",
  "ghl_contact_id": "contact_id"
}
```

## 5. GHL Configuration

### Setting up the Webhook in GHL:

1. **Navigate to GHL Settings**
   - Go to Settings → Webhooks
   
2. **Create New Webhook**
   - Name: "Squidgy Message Notifications"
   - URL: `https://your-backend-url/api/webhooks/ghl/messages`
   - Method: POST
   - Content Type: application/json

3. **Configure Triggers**
   Select the following events:
   - Message Received (SMS)
   - Facebook Message Received
   - Instagram Message Received
   - Any other messaging channels you use

4. **Map Fields**
   Ensure these fields are mapped in the webhook payload:
   - Location ID → `ghl_location_id`
   - Contact ID → `ghl_contact_id`
   - Message Body → `message`
   - Contact Name → `sender_name`
   - Contact Phone → `sender_phone`
   - Contact Email → `sender_email`

5. **Optional: Add Webhook Secret**
   - Generate a secret key
   - Add to GHL webhook configuration
   - Set `GHL_WEBHOOK_SECRET` environment variable in backend

## 6. Testing

### Local Testing
```bash
# 1. Run the backend server
cd Backend_SquidgyBackend_Updated
python main.py

# 2. Run the test script
python test_ghl_webhook.py
```

### Manual Testing with cURL
```bash
curl -X POST http://localhost:8000/api/webhooks/ghl/messages \
  -H "Content-Type: application/json" \
  -d '{
    "ghl_location_id": "loc_123",
    "ghl_contact_id": "contact_456",
    "message": "Test message from GHL",
    "sender_name": "Test User",
    "message_type": "SMS"
  }'
```

## 7. Environment Variables

Add to your `.env` file:
```bash
# Optional: For webhook signature verification
GHL_WEBHOOK_SECRET=your-secret-key-here
```

## 8. Security Considerations

1. **Webhook Signature Verification** (Optional but recommended)
   - Set a webhook secret in GHL
   - Verify the `X-GHL-Signature` header in the webhook endpoint
   
2. **Rate Limiting**
   - Consider implementing rate limiting to prevent webhook spam
   
3. **Data Validation**
   - All required fields are validated using Pydantic models
   - Database constraints ensure data integrity

## 9. Troubleshooting

### Common Issues:

1. **Notifications not appearing**
   - Check if user's `ghl_location_id` is correctly mapped in `ghl_subaccounts` table
   - Verify WebSocket connection is established

2. **Webhook returns 500 error**
   - Check database connection
   - Ensure `notifications` table exists
   - Check logs for specific error messages

3. **Real-time updates not working**
   - Verify WebSocket connection status
   - Check if user_id matches in connection string

### Debug Logging
The webhook logs all incoming requests:
```python
logger.info(f"Received GHL message webhook: {webhook_data.model_dump()}")
```

Check logs for troubleshooting:
```bash
tail -f backend.log
```

## 10. Next Steps

1. **Frontend Implementation**
   - Create notification bell icon with unread count
   - Build notification dropdown/panel
   - Implement mark as read functionality
   
2. **Enhanced Features**
   - Add response capability from Squidgy
   - Implement notification grouping by conversation
   - Add notification preferences/filters
   
3. **Monitoring**
   - Set up webhook monitoring/alerts
   - Track delivery success rates
   - Monitor response times

## 11. Sample GHL Webhook Payload

Here's what GHL typically sends (adjust field mapping as needed):
```json
{
  "locationId": "loc_ABC123",
  "contactId": "con_XYZ789",
  "body": "Hi, I need help with my solar installation",
  "type": "SMS",
  "direction": "inbound",
  "conversationId": "conv_123",
  "dateAdded": "2024-01-15T10:30:00Z",
  "contact": {
    "id": "con_XYZ789",
    "name": "John Smith",
    "phone": "+1234567890",
    "email": "john@example.com"
  }
}
```

Map these fields to our webhook structure in GHL webhook configuration.