# Knowledge Base Implementation - Complete Guide

## Overview

Implemented complete CRUD API for user knowledge base using **Neon PostgreSQL database** (`user_vector_knowledge_base` table). Each agent now has isolated knowledge base via `agent_id` column.

---

## 🚨 CRITICAL: What Changed

### Database Architecture

**BEFORE:**
- Used Supabase database table: `firm_users_knowledge_base`
- No agent isolation - all agents shared same knowledge base per user
- No proper chunking or embedding support

**AFTER:**
- Uses Neon database table: `user_vector_knowledge_base`
- Agent-specific isolation via `agent_id` column
- Proper text chunking (1000 chars)
- Vector embeddings support (VECTOR(1536))
- File deduplication (multiple chunks per file)

---

## 📋 Step 1: Run Database Migration

**YOU MUST RUN THIS SQL ON YOUR NEON DATABASE:**

```bash
# Navigate to migrations folder
cd /Users/somasekharaddakula/CascadeProjects/Backend_SquidgyBackend_Updated/migrations

# Execute migration (replace with your Neon connection string)
psql "postgresql://YOUR_NEON_CONNECTION_STRING" -f add_agent_id_to_knowledge_base.sql
```

**What the migration does:**
1. Adds `agent_id TEXT NOT NULL` column with default 'personal_assistant'
2. Creates performance indexes:
   - `idx_uvkb_agent_id` (agent_id)
   - `idx_uvkb_user_agent` (user_id, agent_id)
   - `idx_uvkb_user_agent_category` (user_id, agent_id, category)
   - `idx_uvkb_user_agent_source` (user_id, agent_id, source)
3. Drops old index `idx_uvkb_user_category` (doesn't include agent_id)

**Verification:**
```sql
-- Check column exists
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'user_vector_knowledge_base' AND column_name = 'agent_id';

-- Check indexes
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'user_vector_knowledge_base' AND indexname LIKE '%agent%';
```

---

## 🎯 Updated Schema

```sql
CREATE TABLE user_vector_knowledge_base (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    agent_id TEXT NOT NULL,  -- NEW: Isolates knowledge per agent
    document TEXT NOT NULL,
    category TEXT NOT NULL,  -- 'documents', 'custom_instructions'
    embedding VECTOR(1536),
    source TEXT DEFAULT 'N8N-agent',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    file_name TEXT,
    file_url TEXT
);

-- Indexes for performance
CREATE INDEX idx_uvkb_user_id ON user_vector_knowledge_base(user_id);
CREATE INDEX idx_uvkb_agent_id ON user_vector_knowledge_base(agent_id);
CREATE INDEX idx_uvkb_user_agent ON user_vector_knowledge_base(user_id, agent_id);
CREATE INDEX idx_uvkb_user_agent_category ON user_vector_knowledge_base(user_id, agent_id, category);
CREATE INDEX idx_uvkb_category ON user_vector_knowledge_base(category);
CREATE INDEX idx_uvkb_file_url ON user_vector_knowledge_base(file_url);
CREATE INDEX idx_uvkb_embedding ON user_vector_knowledge_base USING ivfflat(embedding);
```

---

## 📡 New API Endpoints

All endpoints in `routes/knowledge_base.py` use **Neon database ONLY**.

### 1. GET Files - Fetch User's Uploaded Files

```http
GET /api/knowledge-base/files/{user_id}/{agent_id}
```

**Response:**
```json
{
  "success": true,
  "files": [
    {
      "file_id": "uuid-123",
      "file_name": "business_plan.pdf",
      "file_url": "https://supabase.co/.../file.pdf",
      "created_at": "2026-01-30T10:30:00Z",
      "processing_status": "completed"
    }
  ]
}
```

**Notes:**
- Deduplicates by `file_url` (multiple chunks per file)
- Only returns files for specific agent (agent isolation)
- Category filter: `documents` only

---

### 2. GET Instructions - Fetch Custom Instructions

```http
GET /api/knowledge-base/instructions/{user_id}/{agent_id}
```

**Response:**
```json
{
  "success": true,
  "file_id": "uuid-456",
  "instructions": "I prefer professional tone. Use bullet points."
}
```

**Notes:**
- Returns LATEST instructions by timestamp
- Combines all chunks (long text split into 1000 char chunks)
- Returns `file_id` for UPDATE operations
- Agent-specific instructions

---

### 3. POST Instructions - Create Custom Instructions

```http
POST /api/knowledge-base/instructions
Content-Type: application/json

{
  "user_id": "user-123",
  "agent_id": "personal_assistant",
  "agent_name": "Personal Assistant",
  "instructions": "I prefer professional tone..."
}
```

**Response:**
```json
{
  "success": true,
  "message": "Custom instructions saved successfully",
  "file_id": "uuid-789"
}
```

**Notes:**
- Chunks text into 1000 char segments
- All chunks share same `created_at` timestamp
- Returns `file_id` of first chunk

---

### 4. PUT Instructions - Update Custom Instructions

```http
PUT /api/knowledge-base/instructions/{file_id}
Content-Type: application/json

{
  "user_id": "user-123",
  "agent_id": "personal_assistant",
  "instructions": "Updated instructions..."
}
```

**Response:**
```json
{
  "success": true,
  "message": "Custom instructions updated successfully",
  "file_id": "uuid-new-123"
}
```

**Notes:**
- Deletes ALL old chunks (by timestamp)
- Creates new chunks with new timestamp
- Returns new `file_id`
- No duplicates - clean replace

---

### 5. POST File - Save File Metadata

```http
POST /api/knowledge-base/file
Content-Type: application/json

{
  "user_id": "user-123",
  "agent_id": "personal_assistant",
  "agent_name": "Personal Assistant",
  "file_name": "report.pdf",
  "file_url": "https://supabase.co/.../report.pdf"
}
```

**Response:**
```json
{
  "success": true,
  "message": "File metadata saved successfully",
  "file_id": "uuid-file-123",
  "processing_status": "pending"
}
```

**Notes:**
- Saves metadata immediately
- Text extraction happens via n8n workflow (async)
- Frontend uploads file to Supabase Storage first
- Backend only saves metadata to Neon

---

### 6. DELETE File - Delete File and Chunks

```http
DELETE /api/knowledge-base/file/{file_id}
```

**Response:**
```json
{
  "success": true,
  "message": "File and 15 chunks deleted successfully"
}
```

**Notes:**
- Deletes ALL chunks with same `file_url`
- Requires Supabase Storage deletion from frontend
- Complete cleanup (no orphaned records)

---

## 🔄 Complete Flow Examples

### Custom Instructions Flow:

```
1. User loads page
   ↓
2. Frontend: GET /api/knowledge-base/instructions/{userId}/{agentId}
   ↓
3. Backend: Query Neon for latest instructions by timestamp
   ↓
4. Backend: Combine all chunks, return instructions + file_id
   ↓
5. Frontend: Display in textarea, store file_id

--- User edits text and clicks Save ---

6. Frontend: Check if file_id exists
   ↓
7a. If file_id EXISTS:
    PUT /api/knowledge-base/instructions/{file_id}
    Backend: Delete old chunks, insert new chunks
   ↓
7b. If file_id NULL:
    POST /api/knowledge-base/instructions
    Backend: Insert new chunks
   ↓
8. Backend: Return new file_id
   ↓
9. Frontend: Store new file_id for next update
```

### File Upload Flow:

```
1. User selects PDF file
   ↓
2. Frontend: Upload to Supabase Storage
   ↓
3. Frontend: Get public URL from Supabase
   ↓
4. Frontend: POST /api/knowledge-base/file with file_url
   ↓
5. Backend: INSERT metadata to Neon (placeholder text)
   ↓
6. Backend: Return file_id
   ↓
7. n8n workflow: Extract text, generate embeddings
   ↓
8. n8n: UPDATE Neon record with extracted text + embeddings
   ↓
9. Frontend: Refresh files list (shows new file)
```

### File Delete Flow:

```
1. User clicks trash icon
   ↓
2. Frontend: Confirm dialog
   ↓
3. Frontend: Delete from Supabase Storage
   ↓
4. Frontend: DELETE /api/knowledge-base/file/{file_id}
   ↓
5. Backend: Query file_url from file_id
   ↓
6. Backend: DELETE all chunks with same file_url
   ↓
7. Backend: Return success
   ↓
8. Frontend: Remove from local state (disappears from UI)
```

---

## 🎨 Frontend Implementation

**File:** `client/pages/AgentSettings.tsx`

All API calls already updated to use new endpoints:

```typescript
// GET instructions
GET /api/knowledge-base/instructions/{userId}/{agentId}

// GET files
GET /api/knowledge-base/files/{userId}/{agentId}

// POST instructions (create)
POST /api/knowledge-base/instructions
Body: { user_id, agent_id, agent_name, instructions }

// PUT instructions (update)
PUT /api/knowledge-base/instructions/{fileId}
Body: { user_id, agent_id, instructions }

// POST file
POST /api/knowledge-base/file
Body: { user_id, agent_id, agent_name, file_name, file_url }

// DELETE file
DELETE /api/knowledge-base/file/{fileId}
```

---

## ✅ Verification Checklist

After running migration:

### 1. Check Database:
```sql
-- Verify agent_id column exists
SELECT * FROM user_vector_knowledge_base LIMIT 1;

-- Check indexes
\d+ user_vector_knowledge_base
```

### 2. Test Endpoints:
```bash
# Test debug endpoint
curl http://localhost:8000/api/knowledge-base/debug/config

# Test GET instructions (should return empty for new agent)
curl http://localhost:8000/api/knowledge-base/instructions/USER_ID/AGENT_ID

# Test GET files (should return empty for new agent)
curl http://localhost:8000/api/knowledge-base/files/USER_ID/AGENT_ID
```

### 3. Test Frontend:
1. Open https://app.squidgy.ai/agent-settings/personal_assistant
2. Type custom instructions → Click Save
3. Refresh page → Instructions should persist
4. Upload PDF file → Should appear in files list
5. Delete file → Should disappear immediately

---

## 🔧 Environment Variables Required

```bash
# .env file
NEON_DB_HOST=your-neon-host.neon.tech
NEON_DB_PORT=5432
NEON_DB_USER=your-username
NEON_DB_PASSWORD=your-password
NEON_DB_NAME=neondb
```

---

## 📊 Data Isolation Per Agent

Each agent now has completely isolated knowledge base:

```
user_vector_knowledge_base table:
┌─────────┬────────────┬─────────────────────┬──────────┬────────────┐
│ user_id │ agent_id   │ document            │ category │ file_name  │
├─────────┼────────────┼─────────────────────┼──────────┼────────────┤
│ user123 │ personal   │ "I prefer formal"   │ custom   │ User Input │
│ user123 │ social     │ "Be casual"         │ custom   │ User Input │
│ user123 │ personal   │ "Q1 report text..." │ document │ report.pdf │
│ user123 │ social     │ "Brand guide..."    │ document │ brand.pdf  │
└─────────┴────────────┴─────────────────────┴──────────┴────────────┘

Personal Assistant only sees rows with agent_id='personal'
Social Media Agent only sees rows with agent_id='social'
```

---

## 🚨 Common Issues

### Issue 1: "Database configuration missing"
**Solution:** Set environment variables in `.env` file

### Issue 2: "Column agent_id does not exist"
**Solution:** Run SQL migration on Neon database

### Issue 3: "Connection failed"
**Solution:** Check Neon connection string, ensure SSL enabled

### Issue 4: Old endpoints still being called
**Solution:** Frontend already updated. Ensure backend routes loaded:
```python
# main.py line 8074-8080
from routes.knowledge_base import router as knowledge_base_router
app.include_router(knowledge_base_router)
```

---

## 📝 Next Steps

1. ✅ **RUN SQL MIGRATION** on Neon database
2. ✅ Verify environment variables set
3. ✅ Restart backend server
4. ✅ Test endpoints via curl
5. ✅ Test frontend UI flows
6. ✅ Verify agent isolation (personal_assistant vs social_media_agent)

---

## 🎯 Summary

**What Was Done:**
- ✅ Added `agent_id` to Neon schema
- ✅ Created 6 CRUD endpoints (all use Neon)
- ✅ Implemented text chunking for long instructions
- ✅ Implemented file deduplication
- ✅ Implemented UPDATE vs INSERT logic
- ✅ Frontend already updated (no changes needed)
- ✅ Complete agent isolation

**What You Need To Do:**
- 🚨 Run SQL migration on Neon database
- 🚨 Restart backend server
- 🚨 Test the flows

**Architecture:**
- Supabase Storage: File hosting ONLY (S3-like)
- Neon Database: All metadata, text, embeddings
- Backend API: All database operations
- Frontend: UI + file uploads

**Result:**
Each agent (personal_assistant, social_media_agent, etc.) now has its own isolated knowledge base. No cross-contamination. Clean separation. Always fetches latest data.
