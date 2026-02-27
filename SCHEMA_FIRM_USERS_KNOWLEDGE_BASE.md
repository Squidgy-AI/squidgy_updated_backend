# firm_users_knowledge_base Table Schema

## Overview
This table stores file uploads and text knowledge for users, with a unique constraint preventing duplicate file names per user.

## Database Constraint
```sql
ALTER TABLE firm_users_knowledge_base
ADD CONSTRAINT unique_firm_user_file
UNIQUE (firm_user_id, file_name);
```

## Upsert Behavior
When inserting records, the system uses ON CONFLICT handling:

```sql
INSERT INTO firm_users_knowledge_base (
  id, firm_user_id, file_id, file_name, file_url,
  agent_id, agent_name, extracted_text,
  processing_status, error_message, created_at, updated_at
)
VALUES (
  gen_random_uuid(), :firm_user_id, :file_id, :file_name, :file_url,
  :agent_id, :agent_name, :extracted_text,
  :processing_status, :error_message, NOW(), NOW()
)
ON CONFLICT (firm_user_id, file_name)
DO UPDATE SET
  file_id = EXCLUDED.file_id,
  file_url = EXCLUDED.file_url,
  agent_id = EXCLUDED.agent_id,
  agent_name = EXCLUDED.agent_name,
  extracted_text = EXCLUDED.extracted_text,
  processing_status = EXCLUDED.processing_status,
  error_message = EXCLUDED.error_message,
  updated_at = NOW();
```

## Table Columns

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key (auto-generated) |
| `firm_user_id` | String | User ID (part of unique constraint) |
| `file_id` | String | Unique file identifier (format: `file_{uuid}` or `text_{uuid}`) |
| `file_name` | String | Original filename (part of unique constraint) |
| `file_url` | String | Supabase storage public URL (empty for text input) |
| `agent_id` | String | Agent ID from YAML config |
| `agent_name` | String | Agent name from YAML config |
| `extracted_text` | Text | Extracted text content from file or direct text input |
| `processing_status` | String | Status: `pending`, `processing`, `completed`, `failed` |
| `error_message` | String | Error message if processing failed |
| `created_at` | Timestamp | Record creation timestamp |
| `updated_at` | Timestamp | Last update timestamp |

## Code Implementation

### Backend Service (file_processing_service.py)
The `FileProcessingService.create_processing_record()` method uses Supabase upsert:

```python
response = self.supabase.table("firm_users_knowledge_base").upsert(
    record_data,
    on_conflict="firm_user_id,file_name"
).execute()
```

### Backend Endpoints

#### 1. File Upload Processing (`/api/file/process`)
- **File Name**: Original filename from frontend
- **Behavior**: If user uploads same filename again, record is updated with new file_url and file_id
- **Note**: Old file in Supabase storage remains (potential orphan)

#### 2. Text Knowledge Save (`/api/knowledge-base/text`)
- **File Name**: Always `"User Input"` (static)
- **Behavior**: Multiple text inputs from same user update the same record
- **Use Case**: Consolidates all voice/manual text input into one record per user

## Important Behaviors

### 1. Duplicate File Uploads
When a user uploads a file with the same name twice:
- ✅ Database record is **updated** (not duplicated)
- ✅ New `file_id` is generated
- ✅ New `file_url` points to new storage location
- ✅ Old file in Supabase storage is **automatically deleted** (no orphans!)
- ✅ `processing_status` resets to `pending`
- ✅ `extracted_text` is cleared and re-extracted

### 2. Text Input Updates
When a user saves text knowledge multiple times:
- ✅ Same record is updated (file_name = "User Input")
- ✅ Latest text content replaces previous content
- ✅ Only one "User Input" record exists per user

### 3. Frontend Upload Flow
```
1. User selects file (e.g., "document.pdf")
2. Frontend uploads to Supabase storage as: "{userId}_{timestamp}_document.pdf"
3. Frontend calls /api/file/process with original filename: "document.pdf"
4. Backend creates/updates record with file_name: "document.pdf"
5. If user uploads "document.pdf" again:
   - Backend checks for existing record with same (firm_user_id, file_name)
   - Old storage file is automatically deleted: "{userId}_{oldTimestamp}_document.pdf"
   - New storage file uploaded: "{userId}_{newTimestamp}_document.pdf"
   - Database record updated with new file_url and file_id
   - ✅ No orphaned files!
```

## Orphaned Storage Files - RESOLVED ✅

### Implementation
The `FileProcessingService` now automatically deletes old storage files when a user re-uploads a file with the same name:

```python
# In create_processing_record():
# 1. Check if record exists for (firm_user_id, file_name)
existing_response = self.supabase.table("firm_users_knowledge_base").select("file_url").eq(
    "firm_user_id", firm_user_id
).eq("file_name", file_name).execute()

# 2. If exists and has different file_url, delete old storage file
if existing_response.data and len(existing_response.data) > 0:
    old_file_url = existing_response.data[0].get("file_url")
    if old_file_url and old_file_url != file_url:
        await self.delete_old_storage_file(old_file_url)

# 3. Then upsert the new record
```

### How It Works
1. **Extract storage path** from Supabase URL (e.g., `user123_1234567890_document.pdf`)
2. **Delete from storage** using `supabase.storage.from_('newsletter').remove([path])`
3. **Non-blocking**: Deletion failures are logged as warnings but don't fail the upload
4. **Automatic**: No manual cleanup needed

### Issue: File Name Collision
**Problem**: Users might upload different files with same name (e.g., "report.pdf" from different sources).

**Current Behavior**: Latest upload overwrites previous record.

**Recommendation**: Consider one of:
1. Keep current behavior (simple, users manage their files)
2. Add timestamp to file_name in database: `"report.pdf (2026-02-27)"`
3. Use unique constraint on `file_id` instead of `file_name`

## Migration Notes

If you have existing data with duplicate `(firm_user_id, file_name)` combinations:

```sql
-- Find duplicates
SELECT firm_user_id, file_name, COUNT(*) 
FROM firm_users_knowledge_base 
GROUP BY firm_user_id, file_name 
HAVING COUNT(*) > 1;

-- Keep only the most recent record per (firm_user_id, file_name)
DELETE FROM firm_users_knowledge_base
WHERE id NOT IN (
  SELECT DISTINCT ON (firm_user_id, file_name) id
  FROM firm_users_knowledge_base
  ORDER BY firm_user_id, file_name, created_at DESC
);

-- Then add the constraint
ALTER TABLE firm_users_knowledge_base
ADD CONSTRAINT unique_firm_user_file
UNIQUE (firm_user_id, file_name);
```

## Testing Checklist

- [ ] Upload same file twice - verify record is updated, not duplicated
- [ ] Upload different files with same name - verify latest overwrites
- [ ] Save text knowledge multiple times - verify single "User Input" record
- [ ] Check Supabase storage for orphaned files after re-uploads
- [ ] Verify extracted_text is re-processed on file re-upload
- [ ] Test with different agents - verify agent_id updates correctly
