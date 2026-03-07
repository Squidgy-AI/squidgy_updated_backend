# Semantic Search API Documentation

## Overview

The semantic search endpoint allows AI agents to query the knowledge base using natural language queries. It uses vector similarity search with OpenAI embeddings to find the most relevant documents.

**No more need for n8n for retrieving data!** Agents can now call this endpoint directly from the backend.

---

## Endpoint

```
POST /api/knowledge-base/search
```

---

## Request Body

```json
{
  "query": "What are the company's marketing strategies?",
  "user_id": "61a0306e-2018-4c86-99f8-6287e12fd1ce",
  "agent_id": "personal_assistant",
  "limit": 5,
  "similarity_threshold": 0.7
}
```

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | ✅ Yes | - | Natural language search query |
| `user_id` | string | ✅ Yes | - | User UUID to filter results |
| `agent_id` | string | ❌ No | null | Agent ID to filter results (e.g., "personal_assistant") |
| `limit` | integer | ❌ No | 5 | Maximum number of results to return |
| `similarity_threshold` | float | ❌ No | 0.0 | Minimum similarity score (0.0 to 1.0) |

---

## Response

```json
{
  "success": true,
  "query": "What are the company's marketing strategies?",
  "count": 3,
  "results": [
    {
      "id": "uuid-123",
      "user_id": "61a0306e-2018-4c86-99f8-6287e12fd1ce",
      "agent_id": "personal_assistant",
      "category": "documents",
      "file_name": "marketing_plan.pdf",
      "document": "Our marketing strategy focuses on...",
      "similarity": 0.89,
      "created_at": "2026-02-11T18:26:45.730465+00:00"
    },
    {
      "id": "uuid-456",
      "user_id": "61a0306e-2018-4c86-99f8-6287e12fd1ce",
      "agent_id": "personal_assistant",
      "category": "documents",
      "file_name": "business_plan.pdf",
      "document": "Marketing channels include...",
      "similarity": 0.82,
      "created_at": "2026-02-10T15:30:22.123456+00:00"
    }
  ]
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether the search was successful |
| `query` | string | The original search query |
| `count` | integer | Number of results returned |
| `results` | array | Array of search results (ordered by similarity) |
| `results[].id` | string | Unique ID of the document |
| `results[].user_id` | string | User UUID |
| `results[].agent_id` | string | Agent ID |
| `results[].category` | string | Category (e.g., "documents", "custom_instructions") |
| `results[].file_name` | string | Original file name |
| `results[].document` | string | Full document text |
| `results[].similarity` | float | Similarity score (0.0 to 1.0, higher is better) |
| `results[].created_at` | string | ISO 8601 timestamp |

---

## How It Works

1. **Generate Embedding**: The query text is sent to OpenRouter API (`text-embedding-3-small` model) to generate a 1536-dimension vector
2. **Vector Search**: PostgreSQL pgvector extension performs cosine similarity search against stored embeddings
3. **Filter Results**: Results are filtered by `user_id`, optional `agent_id`, and `similarity_threshold`
4. **Rank & Return**: Results are ranked by similarity score and limited to the specified `limit`

---

## Example Usage

### Python (httpx)

```python
import httpx
import asyncio

async def search_knowledge_base():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/knowledge-base/search",
            json={
                "query": "What are the product features?",
                "user_id": "61a0306e-2018-4c86-99f8-6287e12fd1ce",
                "agent_id": "personal_assistant",
                "limit": 5,
                "similarity_threshold": 0.5
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"Found {data['count']} results")
            
            for result in data['results']:
                print(f"- {result['file_name']}: {result['similarity']*100:.1f}%")
                print(f"  {result['document'][:200]}...")

asyncio.run(search_knowledge_base())
```

### JavaScript (fetch)

```javascript
async function searchKnowledgeBase() {
  const response = await fetch('http://localhost:8000/api/knowledge-base/search', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      query: 'What are the product features?',
      user_id: '61a0306e-2018-4c86-99f8-6287e12fd1ce',
      agent_id: 'personal_assistant',
      limit: 5,
      similarity_threshold: 0.5
    })
  });
  
  const data = await response.json();
  console.log(`Found ${data.count} results`);
  
  data.results.forEach(result => {
    console.log(`- ${result.file_name}: ${(result.similarity * 100).toFixed(1)}%`);
    console.log(`  ${result.document.substring(0, 200)}...`);
  });
}

searchKnowledgeBase();
```

### cURL

```bash
curl -X POST http://localhost:8000/api/knowledge-base/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the product features?",
    "user_id": "61a0306e-2018-4c86-99f8-6287e12fd1ce",
    "agent_id": "personal_assistant",
    "limit": 5,
    "similarity_threshold": 0.5
  }'
```

---

## Testing

Run the test script to verify the endpoint:

```bash
python test_search_endpoint.py
```

Or use the interactive test tool:

```bash
python test_knowledge_base.py
```

---

## Error Responses

### 500 - Failed to generate embedding

```json
{
  "detail": "Failed to generate embedding for query"
}
```

**Cause**: OpenRouter API key not set or API call failed

**Solution**: Set `OPENROUTER_API_KEY` in `.env` file

### 500 - Database connection failed

```json
{
  "detail": "Database connection failed: connection timeout"
}
```

**Cause**: Cannot connect to Neon database

**Solution**: Check Neon database credentials in `.env` file

### 500 - Search failed

```json
{
  "detail": "Search failed: column 'embedding' does not exist"
}
```

**Cause**: Database schema issue

**Solution**: Run database migrations to ensure `embedding` column exists

---

## Performance

- **Embedding Generation**: ~500ms (OpenRouter API)
- **Vector Search**: ~50-200ms (depends on table size)
- **Total Response Time**: ~600-800ms

For better performance:
- Use lower `limit` values (default: 5)
- Add `similarity_threshold` to filter low-quality results
- Ensure pgvector index exists on `embedding` column

---

## Comparison: n8n vs Backend Endpoint

| Feature | n8n Workflow | Backend Endpoint |
|---------|--------------|------------------|
| **Setup** | Complex workflow | Single API call |
| **Latency** | Higher (multiple hops) | Lower (direct) |
| **Debugging** | Difficult | Easy (logs) |
| **Maintenance** | Manual updates | Automatic |
| **Cost** | n8n hosting | Backend only |
| **Flexibility** | Limited | Full control |

---

## Next Steps

1. ✅ Endpoint created: `/api/knowledge-base/search`
2. ✅ Uses same logic as `test_knowledge_base.py`
3. ✅ Test script created: `test_search_endpoint.py`
4. 🔄 Update agents to use this endpoint instead of n8n
5. 🔄 Remove n8n search workflow (optional)

---

## Related Files

- **Endpoint**: `routes/knowledge_base.py` (lines 726-849)
- **Test Script**: `test_search_endpoint.py`
- **Interactive Tool**: `test_knowledge_base.py`
- **Main Backend**: `main.py` (includes router)
