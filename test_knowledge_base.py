"""
Test script for querying Knowledge Base directly from Neon database
Uses vector similarity search with embeddings (same as backend)
Queries the user_vector_knowledge_base table
"""

import asyncio
import asyncpg
import httpx
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Neon PostgreSQL configuration
NEON_DB_HOST = os.getenv('NEON_DB_HOST')
NEON_DB_PORT = os.getenv('NEON_DB_PORT', '5432')
NEON_DB_USER = os.getenv('NEON_DB_USER')
NEON_DB_PASSWORD = os.getenv('NEON_DB_PASSWORD')
NEON_DB_NAME = os.getenv('NEON_DB_NAME', 'neondb')

# OpenRouter API for embeddings
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

# Optional filters
TEST_USER_ID = os.getenv("TEST_USER_ID", "61a0306e-2018-4c86-99f8-6287e12fd1ce")
TEST_AGENT_ID = os.getenv("TEST_AGENT_ID", None)


async def generate_embedding(text: str) -> list:
    """
    Generate embedding for text using OpenRouter API (same as backend).
    Uses openai/text-embedding-3-small model.
    Returns list of floats (embedding vector).
    """
    if not OPENROUTER_API_KEY:
        print("❌ OPENROUTER_API_KEY not set")
        return None

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                'https://openrouter.ai/api/v1/embeddings',
                headers={
                    'Authorization': f'Bearer {OPENROUTER_API_KEY}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'openai/text-embedding-3-small',
                    'input': text[:8000]  # Limit input size
                },
                timeout=60.0
            )

            if response.status_code == 200:
                result = response.json()
                embedding = result.get('data', [{}])[0].get('embedding', [])
                if embedding and len(embedding) > 0:
                    return embedding
                else:
                    print("❌ OpenRouter returned empty embedding")
                    return None
            else:
                print(f"❌ OpenRouter embedding failed ({response.status_code}): {response.text}")
                return None
    except Exception as e:
        print(f"❌ Embedding generation error: {e}")
        return None


async def get_db_connection():
    """Create and return a connection to the Neon database"""
    if not all([NEON_DB_HOST, NEON_DB_USER, NEON_DB_PASSWORD]):
        print("❌ Database configuration missing!")
        print(f"   NEON_DB_HOST: {'Set' if NEON_DB_HOST else 'Missing'}")
        print(f"   NEON_DB_USER: {'Set' if NEON_DB_USER else 'Missing'}")
        print(f"   NEON_DB_PASSWORD: {'Set' if NEON_DB_PASSWORD else 'Missing'}")
        return None

    try:
        conn = await asyncpg.connect(
            host=NEON_DB_HOST,
            port=int(NEON_DB_PORT),
            user=NEON_DB_USER,
            password=NEON_DB_PASSWORD,
            database=NEON_DB_NAME,
            ssl='require',
            timeout=30
        )
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to Neon database: {e}")
        return None


async def list_all_entries(limit: int = 50):
    """List all knowledge base entries"""
    conn = await get_db_connection()
    if not conn:
        return

    try:
        print("=" * 70)
        print("All Knowledge Base Entries")
        print("=" * 70)

        query = """
            SELECT 
                id,
                user_id,
                agent_id,
                category,
                source,
                file_name,
                LEFT(document, 100) as document_preview,
                created_at
            FROM user_vector_knowledge_base
            ORDER BY created_at DESC
            LIMIT $1
        """

        rows = await conn.fetch(query, limit)

        print(f"\nTotal entries (showing up to {limit}):")
        print("-" * 70)

        for row in rows:
            print(f"\n  ID: {row['id']}")
            print(f"  User ID: {row['user_id']}")
            print(f"  Agent ID: {row['agent_id']}")
            print(f"  Category: {row['category']}")
            print(f"  Source: {row['source']}")
            print(f"  File Name: {row['file_name']}")
            print(f"  Document: {row['document_preview']}...")
            print(f"  Created: {row['created_at']}")
            print("-" * 70)

        print(f"\n✅ Found {len(rows)} entries")

    except Exception as e:
        print(f"❌ Query failed: {e}")
    finally:
        await conn.close()


async def get_files_for_user(user_id: str, agent_id: str = None):
    """Get uploaded files for a specific user/agent"""
    conn = await get_db_connection()
    if not conn:
        return

    try:
        print("=" * 70)
        print("Files for User")
        print("=" * 70)
        print(f"\nUser ID: {user_id}")
        print(f"Agent ID: {agent_id or 'All agents'}")

        if agent_id:
            query = """
                SELECT
                    (MIN(id::text))::uuid as file_id,
                    file_name,
                    file_url,
                    MAX(created_at) as created_at,
                    category,
                    source,
                    COUNT(*) as chunk_count
                FROM user_vector_knowledge_base
                WHERE user_id = $1
                  AND agent_id = $2
                  AND category = 'documents'
                  AND file_name IS NOT NULL
                GROUP BY file_name, file_url, category, source
                ORDER BY MAX(created_at) DESC
            """
            rows = await conn.fetch(query, user_id, agent_id)
        else:
            query = """
                SELECT
                    (MIN(id::text))::uuid as file_id,
                    agent_id,
                    file_name,
                    file_url,
                    MAX(created_at) as created_at,
                    category,
                    source,
                    COUNT(*) as chunk_count
                FROM user_vector_knowledge_base
                WHERE user_id = $1
                  AND category = 'documents'
                  AND file_name IS NOT NULL
                GROUP BY agent_id, file_name, file_url, category, source
                ORDER BY MAX(created_at) DESC
            """
            rows = await conn.fetch(query, user_id)

        print(f"\n{'-' * 70}")

        for row in rows:
            print(f"\n  File ID: {row['file_id']}")
            if not agent_id:
                print(f"  Agent ID: {row['agent_id']}")
            print(f"  File Name: {row['file_name']}")
            print(f"  URL: {row['file_url'][:80] if row['file_url'] else 'N/A'}...")
            print(f"  Chunks: {row['chunk_count']}")
            print(f"  Created: {row['created_at']}")
            print("-" * 70)

        print(f"\n✅ Found {len(rows)} files")

    except Exception as e:
        print(f"❌ Query failed: {e}")
    finally:
        await conn.close()


async def get_instructions_for_user(user_id: str, agent_id: str):
    """Get custom instructions for a specific user/agent"""
    conn = await get_db_connection()
    if not conn:
        return

    try:
        print("=" * 70)
        print("Custom Instructions")
        print("=" * 70)
        print(f"\nUser ID: {user_id}")
        print(f"Agent ID: {agent_id}")

        query = """
            SELECT id, document, created_at
            FROM user_vector_knowledge_base
            WHERE user_id = $1
              AND agent_id = $2
              AND category = 'custom_instructions'
            ORDER BY created_at DESC, id ASC
        """

        rows = await conn.fetch(query, user_id, agent_id)

        if not rows:
            print("\n  No custom instructions found")
            return

        # Combine chunks from most recent save
        latest_timestamp = rows[0]['created_at']
        chunks = [row['document'] for row in rows if row['created_at'] == latest_timestamp]
        combined = '\n\n'.join(chunks)

        print(f"\n{'-' * 70}")
        print(f"  First Chunk ID: {rows[0]['id']}")
        print(f"  Total Chunks: {len(chunks)}")
        print(f"  Created: {latest_timestamp}")
        print(f"  Total Length: {len(combined)} characters")
        print(f"\n  Instructions:\n{'-' * 40}")
        preview = combined[:1000] + "..." if len(combined) > 1000 else combined
        print(preview)
        print(f"{'-' * 40}")

        print(f"\n✅ Found instructions")

    except Exception as e:
        print(f"❌ Query failed: {e}")
    finally:
        await conn.close()


async def get_summary_stats():
    """Get summary statistics of the knowledge base"""
    conn = await get_db_connection()
    if not conn:
        return

    try:
        print("=" * 70)
        print("Knowledge Base Summary Statistics")
        print("=" * 70)

        # Total entries
        total = await conn.fetchval("SELECT COUNT(*) FROM user_vector_knowledge_base")
        print(f"\n  Total Entries: {total}")

        # By category
        category_query = """
            SELECT category, COUNT(*) as count
            FROM user_vector_knowledge_base
            GROUP BY category
            ORDER BY count DESC
        """
        categories = await conn.fetch(category_query)
        print("\n  By Category:")
        for row in categories:
            print(f"    - {row['category']}: {row['count']}")

        # By agent
        agent_query = """
            SELECT agent_id, COUNT(*) as count
            FROM user_vector_knowledge_base
            GROUP BY agent_id
            ORDER BY count DESC
            LIMIT 10
        """
        agents = await conn.fetch(agent_query)
        print("\n  By Agent (top 10):")
        for row in agents:
            print(f"    - {row['agent_id']}: {row['count']}")

        # Unique users
        users = await conn.fetchval("SELECT COUNT(DISTINCT user_id) FROM user_vector_knowledge_base")
        print(f"\n  Unique Users: {users}")

        # Recent entries
        recent_query = """
            SELECT user_id, agent_id, category, file_name, created_at
            FROM user_vector_knowledge_base
            ORDER BY created_at DESC
            LIMIT 5
        """
        recent = await conn.fetch(recent_query)
        print("\n  Most Recent Entries:")
        for row in recent:
            print(f"    - {row['created_at']}: {row['agent_id']} / {row['category']} / {row['file_name']}")

        print(f"\n{'=' * 70}")

    except Exception as e:
        print(f"❌ Query failed: {e}")
    finally:
        await conn.close()


async def search_by_content(search_term: str, limit: int = 10):
    """Search knowledge base by document content (text search)"""
    conn = await get_db_connection()
    if not conn:
        return

    try:
        print("=" * 70)
        print(f"Text Search Results for: '{search_term}'")
        print("=" * 70)

        query = """
            SELECT 
                id,
                user_id,
                agent_id,
                category,
                file_name,
                LEFT(document, 200) as document_preview,
                created_at
            FROM user_vector_knowledge_base
            WHERE document ILIKE $1
            ORDER BY created_at DESC
            LIMIT $2
        """

        rows = await conn.fetch(query, f"%{search_term}%", limit)

        for row in rows:
            print(f"\n  ID: {row['id']}")
            print(f"  User: {row['user_id']}")
            print(f"  Agent: {row['agent_id']}")
            print(f"  Category: {row['category']}")
            print(f"  File: {row['file_name']}")
            print(f"  Preview: {row['document_preview']}...")
            print("-" * 70)

        print(f"\n✅ Found {len(rows)} matching entries")

    except Exception as e:
        print(f"❌ Query failed: {e}")
    finally:
        await conn.close()


async def semantic_search(query_text: str, user_id: str = None, agent_id: str = None, limit: int = 5):
    """
    Semantic search using vector similarity (cosine distance).
    This is how an AI agent would search the knowledge base.
    
    1. Generates embedding for the query text
    2. Finds most similar documents using pgvector cosine distance
    3. Returns ranked results with similarity scores
    """
    print("=" * 70)
    print("Semantic Search (Vector Similarity)")
    print("=" * 70)
    print(f"\nQuery: {query_text}")
    if user_id:
        print(f"Filter - User ID: {user_id}")
    if agent_id:
        print(f"Filter - Agent ID: {agent_id}")
    print(f"Limit: {limit}")

    # Step 1: Generate embedding for query
    print("\n🔄 Generating embedding for query...")
    query_embedding = await generate_embedding(query_text)
    
    if not query_embedding:
        print("❌ Failed to generate embedding for query")
        return []

    print(f"✅ Generated embedding ({len(query_embedding)} dimensions)")

    # Step 2: Connect to database and search
    conn = await get_db_connection()
    if not conn:
        return []

    try:
        # Format embedding as PostgreSQL vector string
        vector_str = '[' + ','.join(str(x) for x in query_embedding) + ']'

        # Build query with optional filters
        # Using cosine distance: 1 - (a <=> b) gives similarity score (1 = identical, 0 = orthogonal)
        where_clauses = ["embedding IS NOT NULL"]
        params = [vector_str]
        param_idx = 2

        if user_id:
            where_clauses.append(f"user_id = ${param_idx}")
            params.append(user_id)
            param_idx += 1

        if agent_id:
            where_clauses.append(f"agent_id = ${param_idx}")
            params.append(agent_id)
            param_idx += 1

        where_clause = " AND ".join(where_clauses)
        
        # Add limit as the last parameter
        params.append(limit)

        query = f"""
            SELECT 
                id,
                user_id,
                agent_id,
                category,
                file_name,
                LEFT(document, 500) as document_preview,
                created_at,
                1 - (embedding <=> $1::vector) as similarity
            FROM user_vector_knowledge_base
            WHERE {where_clause}
            ORDER BY embedding <=> $1::vector
            LIMIT ${param_idx}
        """

        print("\n🔍 Searching knowledge base...")
        rows = await conn.fetch(query, *params)

        print(f"\n{'-' * 70}")
        print(f"Found {len(rows)} results:")
        print(f"{'-' * 70}")

        results = []
        for i, row in enumerate(rows, 1):
            similarity = row['similarity']
            similarity_pct = similarity * 100 if similarity else 0

            print(f"\n[{i}] Similarity: {similarity_pct:.1f}%")
            print(f"    ID: {row['id']}")
            print(f"    User: {row['user_id']}")
            print(f"    Agent: {row['agent_id']}")
            print(f"    Category: {row['category']}")
            print(f"    File: {row['file_name']}")
            print(f"    Created: {row['created_at']}")
            print(f"    Content Preview:")
            print(f"    {'-' * 40}")
            # Indent the preview
            preview = row['document_preview'] or ""
            for line in preview.split('\n')[:10]:
                print(f"    {line}")
            print(f"    {'-' * 40}")

            results.append({
                'id': str(row['id']),
                'user_id': row['user_id'],
                'agent_id': row['agent_id'],
                'category': row['category'],
                'file_name': row['file_name'],
                'document': row['document_preview'],
                'similarity': similarity,
                'created_at': row['created_at']
            })

        print(f"\n{'=' * 70}")
        return results

    except Exception as e:
        print(f"❌ Search failed: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        await conn.close()


async def run_custom_query(query: str):
    """Run a custom SQL query and display results"""
    conn = await get_db_connection()
    if not conn:
        return

    try:
        print("=" * 70)
        print("Query Results")
        print("=" * 70)
        print(f"\nQuery: {query[:100]}{'...' if len(query) > 100 else ''}")
        print("-" * 70)

        rows = await conn.fetch(query)

        if not rows:
            print("\n  No results found")
            return

        # Get column names from first row
        columns = list(rows[0].keys())
        print(f"\nColumns: {', '.join(columns)}")
        print(f"Rows: {len(rows)}")
        print("-" * 70)

        for i, row in enumerate(rows, 1):
            print(f"\n[{i}]")
            for col in columns:
                value = row[col]
                # Truncate long values
                if isinstance(value, str) and len(value) > 200:
                    value = value[:200] + "..."
                print(f"  {col}: {value}")

        print("\n" + "=" * 70)

    except Exception as e:
        print(f"\n❌ Query failed: {e}")
    finally:
        await conn.close()


async def interactive_mode():
    """Interactive query mode - prompts user for natural language queries"""
    print("\n" + "=" * 70)
    print("Neon Knowledge Base - AI Agent Query Tool")
    print("=" * 70)
    print(f"\nDatabase: {NEON_DB_NAME}@{NEON_DB_HOST}:{NEON_DB_PORT}")
    print(f"Embeddings: OpenRouter (openai/text-embedding-3-small)")
    print("\n📝 Enter your query in natural language to search the knowledge base.")
    print("   The tool will embed your query and find semantically similar documents.")
    print("\nCommands:")
    print("  exit/quit  - Exit the tool")
    print("  stats      - Show summary statistics")
    print("  sql        - Switch to raw SQL mode")
    print("  help       - Show help")
    print("=" * 70)

    # Check configuration
    if not all([NEON_DB_HOST, NEON_DB_USER, NEON_DB_PASSWORD]):
        print("\n⚠️  Database credentials missing in .env file:")
        print("   NEON_DB_HOST, NEON_DB_USER, NEON_DB_PASSWORD")
        return

    if not OPENROUTER_API_KEY:
        print("\n⚠️  OPENROUTER_API_KEY not set - semantic search won't work")

    sql_mode = False

    while True:
        print("\n")
        try:
            if sql_mode:
                user_input = input("SQL> ").strip()
            else:
                user_input = input("🔍 Search: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nExiting...")
            break

        if not user_input:
            continue

        if user_input.lower() in ('exit', 'quit', 'q'):
            print("Exiting...")
            break

        if user_input.lower() == 'stats':
            await get_summary_stats()
            continue

        if user_input.lower() == 'sql':
            sql_mode = not sql_mode
            if sql_mode:
                print("📊 Switched to SQL mode. Type 'sql' again to switch back.")
            else:
                print("� Switched to semantic search mode.")
            continue

        if user_input.lower() == 'help':
            print("\n📖 Help:")
            print("-" * 50)
            print("\n🔍 SEMANTIC SEARCH MODE (default):")
            print("   Just type your question in natural language.")
            print("   Examples:")
            print("   - What are the pricing details?")
            print("   - How do I contact support?")
            print("   - Tell me about the company's services")
            print("\n📊 SQL MODE (type 'sql' to toggle):")
            print("   Enter raw SQL queries directly.")
            print("   Example: SELECT * FROM user_vector_knowledge_base LIMIT 5")
            print("\n🎯 FILTERED SEARCH:")
            print("   Add filters with @user:<uuid> or @agent:<id>")
            print("   Example: What is the pricing? @agent:personal_assistant")
            print("-" * 50)
            continue

        if sql_mode:
            # Raw SQL mode
            await run_custom_query(user_input)
        else:
            # Semantic search mode - parse optional filters
            user_id = TEST_USER_ID  # Use TEST_USER_ID by default
            agent_id = TEST_AGENT_ID
            query_text = user_input

            # Parse @user: and @agent: filters
            import re
            user_match = re.search(r'@user:(\S+)', user_input)
            agent_match = re.search(r'@agent:(\S+)', user_input)

            if user_match:
                user_id = user_match.group(1)
                query_text = query_text.replace(user_match.group(0), '').strip()

            if agent_match:
                agent_id = agent_match.group(1)
                query_text = query_text.replace(agent_match.group(0), '').strip()

            if not query_text:
                print("❌ Please enter a search query")
                continue

            # Run semantic search
            await semantic_search(query_text, user_id=user_id, agent_id=agent_id, limit=50)


if __name__ == "__main__":
    asyncio.run(interactive_mode())
