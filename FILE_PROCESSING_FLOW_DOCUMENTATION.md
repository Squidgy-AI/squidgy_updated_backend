# File Processing System - Complete Flow Documentation

## Overview
This document explains the complete step-by-step flow of the simplified file processing system that accepts file storage URLs from the frontend and processes text extraction in the background.

## System Architecture

### Components
1. **Frontend**: Handles file upload to Supabase storage
2. **Backend API**: Accepts file URLs and manages processing
3. **Background Processor**: Downloads files and extracts text
4. **Database**: Tracks processing status and stores extracted text

### Database Schema
```sql
CREATE TABLE firm_users_knowledge_base (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    firm_user_id TEXT NOT NULL,
    file_id TEXT NOT NULL UNIQUE,
    file_name TEXT NOT NULL,
    file_url TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    extracted_text TEXT,
    processing_status TEXT DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Complete Step-by-Step Flow

### Step 1: Frontend Uploads File to Supabase Storage
```javascript
// Frontend handles file upload directly to Supabase
const { data, error } = await supabase.storage
  .from('newsletter')
  .upload(`${firm_user_id}_${timestamp}_${filename}`, file);

// Frontend gets the public URL
const fileUrl = supabase.storage
  .from('newsletter')
  .getPublicUrl(data.path);
```

**Result**: File is stored at: 
`https://aoteeitreschwzkbpqyd.supabase.co/storage/v1/object/public/newsletter/user123_1729212345_document.pdf`

### Step 2: Frontend Calls Backend Processing Endpoint
```javascript
// Frontend sends form data to backend
const formData = new FormData();
formData.append('firm_user_id', 'user-123');
formData.append('file_name', 'business_report.pdf');
formData.append('file_url', fileUrl); // Supabase storage URL
formData.append('agent_id', 'newsletter'); // From YAML config
formData.append('agent_name', 'Newsletter Assistant'); // From YAML config

const response = await fetch('/api/file/process', {
  method: 'POST',
  body: formData
});
```

### Step 3: Backend Immediately Responds "Thanks!"
```python
# Endpoint: POST /api/file/process
@app.post("/api/file/process")
async def process_file_from_url(...):
    # 1. Validate all required fields
    # 2. Generate unique file_id: "file_abc123def456"
    # 3. Create database record with status="pending"
    # 4. Start background processing task
    # 5. Return immediate response
```

**Response to Frontend**:
```json
{
  "success": true,
  "message": "Thank you! Your file has been received and is being processed.",
  "data": {
    "file_id": "file_abc123def456",
    "firm_user_id": "user-123",
    "file_name": "business_report.pdf",
    "agent_id": "newsletter",
    "agent_name": "Newsletter Assistant",
    "status": "processing_started",
    "processing_url": "/api/file/status/file_abc123def456"
  }
}
```

### Step 4: Database Record Created
```sql
-- Immediate insert into firm_users_knowledge_base
INSERT INTO firm_users_knowledge_base (
  firm_user_id,     -- "user-123"
  file_id,          -- "file_abc123def456" (unique)
  file_name,        -- "business_report.pdf"
  file_url,         -- "https://aoteeitreschwzkbpqyd.supabase.co/..."
  agent_id,         -- "newsletter"
  agent_name,       -- "Newsletter Assistant"
  processing_status -- "pending"
);
```

### Step 5: Background Processing Starts
```python
# background_text_processor.py
class BackgroundTextProcessor:
    async def process_file(file_id):
        # 1. Update status to "processing"
        # 2. Download file from Supabase URL
        # 3. Extract text using TextExtractor
        # 4. Update database with results
```

**Processing Steps**:
1. **Status Update**: `pending` → `processing`
2. **Download**: Get file bytes from Supabase storage URL using httpx
3. **Text Extraction**: 
   - **PDF**: PyPDF2 extracts text from all pages
   - **TXT**: Handle multiple encodings (UTF-8, Latin-1, etc.)
   - **DOCX**: Extract paragraphs and tables using python-docx
4. **Final Update**: 
   - **Success**: `processing` → `completed` (with extracted text)
   - **Failure**: `processing` → `failed` (with error message)

### Step 6: Frontend Can Check Status
```javascript
// Frontend polls status endpoint
const statusResponse = await fetch(`/api/file/status/${file_id}`);
const status = await statusResponse.json();

console.log(status.data.status); // "pending" → "processing" → "completed"
console.log(status.data.extracted_text); // Full text content
```

**Status Responses**:

**While Processing**:
```json
{
  "success": true,
  "data": {
    "file_id": "file_abc123def456",
    "status": "processing",
    "file_name": "business_report.pdf",
    "agent_id": "newsletter",
    "agent_name": "Newsletter Assistant",
    "created_at": "2024-10-18T01:45:30Z",
    "updated_at": "2024-10-18T01:45:35Z"
  }
}
```

**When Completed**:
```json
{
  "success": true,
  "data": {
    "file_id": "file_abc123def456", 
    "status": "completed",
    "file_name": "business_report.pdf",
    "agent_id": "newsletter",
    "agent_name": "Newsletter Assistant",
    "extracted_text": "The complete extracted text content from the PDF document...",
    "created_at": "2024-10-18T01:45:30Z",
    "updated_at": "2024-10-18T01:45:45Z"
  }
}
```

**If Failed**:
```json
{
  "success": true,
  "data": {
    "file_id": "file_abc123def456",
    "status": "failed",
    "file_name": "business_report.pdf",
    "error_message": "Failed to download file: HTTP 404 Not Found",
    "created_at": "2024-10-18T01:45:30Z",
    "updated_at": "2024-10-18T01:45:32Z"
  }
}
```

### Step 7: Frontend Can List All User Files
```javascript
// Get all files for a user
const userFiles = await fetch(`/api/files/user/${firm_user_id}`);

// Or filter by specific agent
const newsletterFiles = await fetch(`/api/files/user/${firm_user_id}?agent_id=newsletter`);
```

**Response**:
```json
{
  "success": true,
  "count": 3,
  "data": [
    {
      "file_id": "file_abc123def456",
      "file_name": "business_report.pdf",
      "agent_id": "newsletter",
      "agent_name": "Newsletter Assistant",
      "processing_status": "completed",
      "created_at": "2024-10-18T01:45:30Z"
    },
    {
      "file_id": "file_xyz789ghi012",
      "file_name": "marketing_data.docx",
      "agent_id": "newsletter",
      "agent_name": "Newsletter Assistant", 
      "processing_status": "processing",
      "created_at": "2024-10-18T01:40:15Z"
    }
  ]
}
```

## API Endpoints

### 1. Process File
- **Method**: POST
- **URL**: `/api/file/process`
- **Parameters**: 
  - `firm_user_id` (required): User ID from frontend
  - `file_name` (required): Original filename
  - `file_url` (required): Supabase storage URL
  - `agent_id` (required): Agent ID from YAML config
  - `agent_name` (required): Agent name from YAML config
- **Response**: Immediate "thanks" message with file_id

### 2. Check Processing Status
- **Method**: GET
- **URL**: `/api/file/status/{file_id}`
- **Response**: Current processing status and results

### 3. Get User Files
- **Method**: GET
- **URL**: `/api/files/user/{firm_user_id}`
- **Query Parameters**: 
  - `agent_id` (optional): Filter by specific agent
- **Response**: List of all files for the user

## Key Benefits

### 1. ⚡ Immediate Response
- Frontend gets instant "thanks" message
- No waiting for file processing to complete
- Better user experience

### 2. 🚫 No Timeouts
- No risk of upload timeouts on large files
- Frontend handles upload directly to Supabase
- Backend only processes file URLs

### 3. 📊 Progress Tracking
- Frontend can poll status endpoint
- Real-time progress updates
- Clear status transitions

### 4. 🔄 Async Processing
- Backend handles text extraction in background
- Non-blocking architecture
- Scalable processing

### 5. 💾 Simple Storage
- Clean database schema
- All metadata tracked
- Easy querying by user/agent

### 6. 🎯 Agent-Specific
- Each file linked to specific agent
- Agent information from YAML config
- Organized by agent type

## Supported File Types

- **PDF**: Text extraction from all pages using PyPDF2
- **TXT**: Multiple encoding support (UTF-8, Latin-1, CP1252, ISO-8859-1)
- **DOCX**: Paragraph and table extraction using python-docx

## Error Handling

### File Download Errors
- HTTP errors (404, 403, etc.)
- Network timeouts
- Invalid URLs

### Text Extraction Errors
- Corrupted files
- Unsupported formats
- Empty content

### Database Errors
- Connection issues
- Constraint violations
- Update failures

All errors are captured and stored in the `error_message` field with status set to "failed".

## Testing

Use the provided test script to verify the system:

```bash
python3 test_simplified_file_processing.py
```

The test covers:
1. File processing request
2. Status checking
3. User files listing
4. Error handling

## Implementation Files

### Core Files
- `main.py`: FastAPI endpoints
- `file_processing_service.py`: Database operations
- `background_text_processor.py`: Background processing
- `text_extraction.py`: Text extraction utilities

### Test Files
- `test_simplified_file_processing.py`: Comprehensive testing

### Database
- `firm_users_knowledge_base` table with proper indexes and triggers

This system provides a robust, scalable, and user-friendly file processing solution that handles the complete flow from frontend upload to background text extraction and status tracking.