# Migration Guide: Clone PUBLIC to SQUIDGY_DEV Schema

## Overview
This migration script creates an exact copy of the `public` schema as `squidgy_dev`, including all tables, data, functions, procedures, views, sequences, triggers, RLS policies, and privileges.

## What Gets Copied

### ✅ Complete List:
1. **Schema Structure**
   - New schema: `squidgy_dev`
   - Same privileges as `public` schema

2. **Tables**
   - All table structures (columns, data types, constraints)
   - All table data (every single row)
   - Primary keys, unique constraints, check constraints
   - Indexes (automatically with `INCLUDING ALL`)

3. **Sequences**
   - All sequences
   - Current sequence values preserved

4. **Functions & Procedures**
   - All custom functions
   - All stored procedures
   - Function definitions adapted for new schema

5. **Views**
   - All views
   - View definitions adapted for new schema

6. **Triggers**
   - All triggers
   - Trigger definitions adapted for new schema

7. **Row Level Security (RLS)** *(if exists)*
   - RLS enabled on same tables as public (if any)
   - All RLS policies copied exactly (if any exist)
   - **Note:** If your public schema has no RLS policies, this step is skipped

8. **Privileges & Permissions**
   - Schema-level privileges
   - Table-level privileges
   - Default privileges for future objects

9. **Foreign Key Constraints**
   - All foreign key relationships preserved

## How to Run the Migration

### Option 1: Using Supabase Dashboard (Recommended)
1. Go to your Supabase project
2. Navigate to **SQL Editor**
3. Click **New Query**
4. Copy the entire content of `migration_clone_public_to_squidgy_dev.sql`
5. Paste it into the SQL Editor
6. Click **Run** (or press Cmd/Ctrl + Enter)
7. Wait for completion (check the Results tab for progress)

### Option 2: Using psql Command Line
```bash
# Navigate to the backend folder
cd /Users/somasekharaddakula/CascadeProjects/Backend_SquidgyBackend_Updated

# Run the migration
psql -h <your-supabase-host> \
     -U postgres \
     -d postgres \
     -f migration_clone_public_to_squidgy_dev.sql
```

### Option 3: Using Supabase CLI
```bash
# Make sure you're logged in to Supabase
supabase login

# Link to your project
supabase link --project-ref <your-project-ref>

# Run the migration
supabase db execute -f migration_clone_public_to_squidgy_dev.sql
```

## Expected Output

You should see NOTICE messages like:
```
NOTICE:  === Copying Tables ===
NOTICE:  Copying table: agents
NOTICE:    ✓ Copied table: agents with data
NOTICE:  Copying table: business_settings
NOTICE:    ✓ Copied table: business_settings with data
...
NOTICE:  === Copying Functions and Procedures ===
NOTICE:  === Copying Views ===
NOTICE:  === Copying Triggers ===
NOTICE:  === Copying RLS Policies ===
NOTICE:  === Copying Table Privileges ===
NOTICE:
NOTICE:  ============================================================
NOTICE:                 MIGRATION SUMMARY REPORT
NOTICE:  ============================================================
NOTICE:  Tables copied:     X
NOTICE:  Functions copied:  X
NOTICE:  Views copied:      X
NOTICE:  Sequences copied:  X
NOTICE:  Triggers copied:   X
NOTICE:  Policies copied:   X
NOTICE:  ============================================================
NOTICE:  ✅ Migration completed successfully!
NOTICE:  ============================================================
```

## After Migration - Update Environment Variables

Once the migration is complete, update your environment variables to use the new schema:

### 1. Backend (.env)
```bash
# Change from:
SUPABASE_SCHEMA=public

# To:
SUPABASE_SCHEMA=squidgy_dev
```

### 2. UI (.env)
```bash
# Change from:
VITE_SUPABASE_SCHEMA=public

# To:
VITE_SUPABASE_SCHEMA=squidgy_dev
```

### 3. Game (.env.local)
```bash
# Change from:
VITE_SUPABASE_SCHEMA=public

# To:
VITE_SUPABASE_SCHEMA=squidgy_dev
```

### Quick Update Commands:
```bash
# Backend
cd /Users/somasekharaddakula/CascadeProjects/Backend_SquidgyBackend_Updated
sed -i '' 's/SUPABASE_SCHEMA=public/SUPABASE_SCHEMA=squidgy_dev/' .env

# UI
cd /Users/somasekharaddakula/CascadeProjects/UI_SquidgyFrontend_Updated
sed -i '' 's/VITE_SUPABASE_SCHEMA=public/VITE_SUPABASE_SCHEMA=squidgy_dev/' .env

# Game
cd /Users/somasekharaddakula/CascadeProjects/squidgy-waitlist-game/squidgy-game
sed -i '' 's/VITE_SUPABASE_SCHEMA=public/VITE_SUPABASE_SCHEMA=squidgy_dev/' .env.local
```

## Verification Steps

### 1. Run Verification Queries
Uncomment the verification section at the bottom of the migration script and run:

```sql
-- Compare table counts
SELECT 'public' as schema, COUNT(*) as table_count FROM pg_tables WHERE schemaname = 'public'
UNION ALL
SELECT 'squidgy_dev', COUNT(*) FROM pg_tables WHERE schemaname = 'squidgy_dev';
```

### 2. Compare Row Counts
The script includes a verification query that compares row counts between schemas:
```sql
DO $$
DECLARE
    r RECORD;
    public_count BIGINT;
    dev_count BIGINT;
BEGIN
    FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename
    LOOP
        EXECUTE format('SELECT COUNT(*) FROM public.%I', r.tablename) INTO public_count;
        EXECUTE format('SELECT COUNT(*) FROM squidgy_dev.%I', r.tablename) INTO dev_count;

        IF public_count = dev_count THEN
            RAISE NOTICE '✓ %: % rows (match)', r.tablename, public_count;
        ELSE
            RAISE NOTICE '✗ %: public=%, dev=% (MISMATCH)', r.tablename, public_count, dev_count;
        END IF;
    END LOOP;
END $$;
```

### 3. Test Your Applications
1. Update environment variables as shown above
2. Restart your backend server
3. Refresh your UI application
4. Test critical functionality:
   - User authentication
   - Data fetching
   - Data updates
   - All CRUD operations

## Rollback Plan

If you need to rollback and continue using `public` schema:

### 1. Revert Environment Variables
```bash
# Backend
SUPABASE_SCHEMA=public

# UI
VITE_SUPABASE_SCHEMA=public

# Game
VITE_SUPABASE_SCHEMA=public
```

### 2. Delete the New Schema (Optional)
```sql
DROP SCHEMA IF EXISTS squidgy_dev CASCADE;
```

## Common Issues & Solutions

### Issue 1: Permission Denied
**Error:** `permission denied for schema squidgy_dev`

**Solution:** Make sure you're running the script as the `postgres` superuser or a user with sufficient privileges.

### Issue 2: Foreign Key Violations
**Error:** `foreign key constraint violation`

**Solution:** The script handles foreign keys automatically with `INCLUDING ALL`. If you see this error, it might be due to data integrity issues in the source schema.

### Issue 3: Function/View Dependencies
**Error:** `function X depends on view Y`

**Solution:** The script handles dependencies by copying in order (tables → functions → views → triggers). If you still see dependency issues, you may need to manually reorder some objects.

## Best Practices

1. **Backup First:** Always create a backup before running migrations
2. **Test Environment:** Run this first in a staging/test environment
3. **Maintenance Window:** Run during low-traffic periods
4. **Monitor Performance:** Watch database performance during migration
5. **Verify Data:** Always verify data integrity after migration

## Next Steps

After successful migration:

1. ✅ Verify all tables, data, and functions are copied
2. ✅ Update environment variables across all projects
3. ✅ Test all applications thoroughly
4. ✅ Monitor for any issues in the first 24 hours
5. ✅ Consider keeping `public` schema as backup for a while
6. ✅ Eventually drop `public` schema if no longer needed

## Support

If you encounter issues:
1. Check the migration output for specific error messages
2. Verify Supabase connection and permissions
3. Check the verification queries results
4. Review Supabase logs in the dashboard

## Schema Switching Strategy

You can easily switch between schemas for testing:

```bash
# Use squidgy_dev (development)
export SUPABASE_SCHEMA=squidgy_dev

# Use public (production)
export SUPABASE_SCHEMA=public
```

This allows you to:
- Test changes in `squidgy_dev` without affecting `public`
- Compare behavior between schemas
- Safely develop new features
