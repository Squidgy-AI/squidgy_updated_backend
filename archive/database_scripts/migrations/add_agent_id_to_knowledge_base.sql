-- ============================================================================
-- Migration: Add agent_id to user_vector_knowledge_base table
-- Date: 2026-01-30
-- Description: Adds agent_id column and indexes to isolate knowledge base per agent
-- ============================================================================

-- Step 1: Add agent_id column with default value for existing records
ALTER TABLE user_vector_knowledge_base
ADD COLUMN IF NOT EXISTS agent_id TEXT NOT NULL DEFAULT 'personal_assistant';

-- Step 2: Create indexes for performance optimization
-- Index on agent_id alone
CREATE INDEX IF NOT EXISTS idx_uvkb_agent_id
ON user_vector_knowledge_base USING BTREE (agent_id);

-- Composite index for user_id + agent_id (most common query pattern)
CREATE INDEX IF NOT EXISTS idx_uvkb_user_agent
ON user_vector_knowledge_base USING BTREE (user_id, agent_id);

-- Composite index for user_id + agent_id + category (filtered queries)
CREATE INDEX IF NOT EXISTS idx_uvkb_user_agent_category
ON user_vector_knowledge_base USING BTREE (user_id, agent_id, category);

-- Composite index for user_id + agent_id + source (source filtering)
CREATE INDEX IF NOT EXISTS idx_uvkb_user_agent_source
ON user_vector_knowledge_base USING BTREE (user_id, agent_id, source);

-- Step 3: Drop old composite index that doesn't include agent_id
DROP INDEX IF EXISTS idx_uvkb_user_category;

-- Step 4: Remove default value (optional - forces agent_id for new inserts)
-- Uncomment the line below if you want to enforce agent_id on all new records
-- ALTER TABLE user_vector_knowledge_base ALTER COLUMN agent_id DROP DEFAULT;

-- ============================================================================
-- Verification Queries (run these to verify migration)
-- ============================================================================

-- Check column exists
-- SELECT column_name, data_type, is_nullable, column_default
-- FROM information_schema.columns
-- WHERE table_name = 'user_vector_knowledge_base' AND column_name = 'agent_id';

-- Check indexes
-- SELECT indexname, indexdef
-- FROM pg_indexes
-- WHERE tablename = 'user_vector_knowledge_base' AND indexname LIKE '%agent%';

-- Count records per agent
-- SELECT agent_id, COUNT(*) as record_count
-- FROM user_vector_knowledge_base
-- GROUP BY agent_id
-- ORDER BY record_count DESC;

-- ============================================================================
-- Rollback (if needed)
-- ============================================================================

-- To rollback this migration, run:
-- DROP INDEX IF EXISTS idx_uvkb_agent_id;
-- DROP INDEX IF EXISTS idx_uvkb_user_agent;
-- DROP INDEX IF EXISTS idx_uvkb_user_agent_category;
-- DROP INDEX IF EXISTS idx_uvkb_user_agent_source;
-- ALTER TABLE user_vector_knowledge_base DROP COLUMN IF EXISTS agent_id;

-- ============================================================================
-- END MIGRATION
-- ============================================================================
