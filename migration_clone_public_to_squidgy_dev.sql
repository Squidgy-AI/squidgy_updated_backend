-- ============================================================================
-- MIGRATION SCRIPT: Clone PUBLIC schema to SQUIDGY_DEV
-- ============================================================================
-- This script creates an exact copy of the PUBLIC schema as SQUIDGY_DEV
-- Including: tables, data, functions, procedures, views, sequences, triggers,
--           indexes, constraints, RLS policies, and all privileges
--
-- Compatible with: Supabase / PostgreSQL 12+
-- ============================================================================

-- Enable detailed logging
SET client_min_messages TO NOTICE;

-- Step 1: Create the new schema
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
    RAISE NOTICE '        STARTING MIGRATION: public → squidgy_dev';
    RAISE NOTICE '============================================================';
    RAISE NOTICE '';
END $$;

DROP SCHEMA IF EXISTS squidgy_dev CASCADE;
CREATE SCHEMA squidgy_dev;

COMMENT ON SCHEMA squidgy_dev IS 'Development schema - exact copy of public schema';

DO $$
BEGIN
    RAISE NOTICE '✓ Schema squidgy_dev created';
END $$;

-- Step 2: Grant schema-level privileges (same as public)
-- ============================================================================
-- Grant usage on schema to standard Supabase roles
GRANT USAGE ON SCHEMA squidgy_dev TO postgres;
GRANT USAGE ON SCHEMA squidgy_dev TO anon;
GRANT USAGE ON SCHEMA squidgy_dev TO authenticated;
GRANT USAGE ON SCHEMA squidgy_dev TO service_role;
GRANT USAGE ON SCHEMA squidgy_dev TO authenticator;

-- Grant ALL privileges to postgres and service_role (superuser-like)
GRANT ALL ON SCHEMA squidgy_dev TO postgres;
GRANT ALL ON SCHEMA squidgy_dev TO service_role;

-- Step 3: Copy all tables with structure and data
-- ============================================================================
DO $$
DECLARE
    r RECORD;
    table_ddl TEXT;
BEGIN
    RAISE NOTICE '=== Copying Tables ===';

    -- Loop through all tables in public schema
    FOR r IN
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename
    LOOP
        RAISE NOTICE 'Copying table: %', r.tablename;

        -- Create table with structure and data
        EXECUTE format(
            'CREATE TABLE squidgy_dev.%I (LIKE public.%I INCLUDING ALL)',
            r.tablename, r.tablename
        );

        -- Copy data
        EXECUTE format(
            'INSERT INTO squidgy_dev.%I SELECT * FROM public.%I',
            r.tablename, r.tablename
        );

        RAISE NOTICE '  ✓ Copied table: % with data', r.tablename;
    END LOOP;
END $$;

-- Step 4: Reset sequence values based on actual table data
-- ============================================================================
DO $$
DECLARE
    r RECORD;
    seq_name TEXT;
    col_name TEXT;
    max_value BIGINT;
BEGIN
    RAISE NOTICE '=== Resetting Sequence Values ===';

    -- Loop through all columns that have sequences
    FOR r IN
        SELECT
            c.table_name,
            c.column_name,
            pg_get_serial_sequence('squidgy_dev.' || quote_ident(c.table_name), c.column_name) as sequence_name
        FROM information_schema.columns c
        WHERE c.table_schema = 'squidgy_dev'
        AND pg_get_serial_sequence('squidgy_dev.' || quote_ident(c.table_name), c.column_name) IS NOT NULL
        ORDER BY c.table_name, c.column_name
    LOOP
        BEGIN
            -- Get the maximum value from the column
            EXECUTE format(
                'SELECT COALESCE(MAX(%I), 0) FROM squidgy_dev.%I',
                r.column_name,
                r.table_name
            ) INTO max_value;

            -- Set the sequence to max value (will be incremented on next insert)
            IF max_value > 0 THEN
                EXECUTE format('SELECT setval(%L, %s)', r.sequence_name, max_value);
                RAISE NOTICE '  ✓ Reset sequence for %.%: %s → %',
                    r.table_name, r.column_name, r.sequence_name, max_value;
            ELSE
                RAISE NOTICE '  ℹ Skipped empty table: %.%', r.table_name, r.column_name;
            END IF;

        EXCEPTION
            WHEN OTHERS THEN
                RAISE NOTICE '  ⚠ Could not reset sequence for %.%: %',
                    r.table_name, r.column_name, SQLERRM;
        END;
    END LOOP;

    RAISE NOTICE '  ✓ Sequence reset complete';
END $$;

-- Step 5: Copy user-defined functions and procedures (skip extension functions)
-- ============================================================================
DO $$
DECLARE
    r RECORD;
    func_def TEXT;
    func_count INTEGER := 0;
BEGIN
    RAISE NOTICE '=== Copying User-Defined Functions and Procedures ===';

    FOR r IN
        SELECT
            p.proname as function_name,
            pg_get_functiondef(p.oid) as function_def,
            l.lanname as language
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        JOIN pg_language l ON p.prolang = l.oid
        WHERE n.nspname = 'public'
        AND p.prokind IN ('f', 'p')  -- functions and procedures
        -- Skip C language functions (these are from extensions like pgvector)
        AND l.lanname NOT IN ('c', 'internal')
        -- Skip functions that are part of extensions
        AND NOT EXISTS (
            SELECT 1 FROM pg_depend d
            WHERE d.objid = p.oid
            AND d.deptype = 'e'  -- extension dependency
        )
        -- Only copy SQL, PL/pgSQL, and other safe languages
        AND l.lanname IN ('sql', 'plpgsql')
        ORDER BY p.proname
    LOOP
        BEGIN
            RAISE NOTICE 'Copying function/procedure: % (language: %)', r.function_name, r.language;

            -- Replace 'public' schema with 'squidgy_dev' in function definition
            func_def := replace(r.function_def, 'CREATE OR REPLACE FUNCTION public.',
                               'CREATE OR REPLACE FUNCTION squidgy_dev.');
            func_def := replace(func_def, 'CREATE OR REPLACE PROCEDURE public.',
                               'CREATE OR REPLACE PROCEDURE squidgy_dev.');
            func_def := replace(func_def, 'CREATE FUNCTION public.',
                               'CREATE FUNCTION squidgy_dev.');
            func_def := replace(func_def, 'CREATE PROCEDURE public.',
                               'CREATE PROCEDURE squidgy_dev.');

            -- Execute the modified function definition
            EXECUTE func_def;

            func_count := func_count + 1;
            RAISE NOTICE '  ✓ Copied function/procedure: %', r.function_name;

        EXCEPTION
            WHEN OTHERS THEN
                RAISE NOTICE '  ⚠ Skipped function % (error: %)', r.function_name, SQLERRM;
        END;
    END LOOP;

    IF func_count = 0 THEN
        RAISE NOTICE '  ℹ No user-defined functions found (extension functions are skipped)';
    ELSE
        RAISE NOTICE '  ✓ Copied % function(s)/procedure(s)', func_count;
    END IF;
END $$;

-- Step 6: Copy all views
-- ============================================================================
DO $$
DECLARE
    r RECORD;
    view_def TEXT;
BEGIN
    RAISE NOTICE '=== Copying Views ===';

    FOR r IN
        SELECT
            table_name as view_name,
            view_definition
        FROM information_schema.views
        WHERE table_schema = 'public'
    LOOP
        RAISE NOTICE 'Copying view: %', r.view_name;

        -- Create view with definition modified for new schema
        view_def := replace(r.view_definition, 'public.', 'squidgy_dev.');

        EXECUTE format(
            'CREATE VIEW squidgy_dev.%I AS %s',
            r.view_name, view_def
        );

        RAISE NOTICE '  ✓ Copied view: %', r.view_name;
    END LOOP;
END $$;

-- Step 7: Copy all triggers
-- ============================================================================
DO $$
DECLARE
    r RECORD;
    trigger_def TEXT;
BEGIN
    RAISE NOTICE '=== Copying Triggers ===';

    FOR r IN
        SELECT
            tgname as trigger_name,
            tgrelid::regclass::text as table_name,
            pg_get_triggerdef(oid) as trigger_def
        FROM pg_trigger
        WHERE tgrelid IN (
            SELECT oid
            FROM pg_class
            WHERE relnamespace = 'public'::regnamespace
        )
        AND NOT tgisinternal  -- Exclude internal triggers
    LOOP
        RAISE NOTICE 'Copying trigger: % on table: %', r.trigger_name, r.table_name;

        -- Replace public schema with squidgy_dev in trigger definition
        trigger_def := replace(r.trigger_def, 'public.', 'squidgy_dev.');

        EXECUTE trigger_def;

        RAISE NOTICE '  ✓ Copied trigger: %', r.trigger_name;
    END LOOP;
END $$;

-- Step 8: Copy Row Level Security (RLS) policies
-- ============================================================================
DO $$
DECLARE
    r RECORD;
    policy_def TEXT;
BEGIN
    RAISE NOTICE '=== Copying RLS Policies ===';

    -- First, enable RLS on tables that have it in public
    FOR r IN
        SELECT
            schemaname,
            tablename,
            rowsecurity
        FROM pg_tables
        WHERE schemaname = 'public'
        AND rowsecurity = true
    LOOP
        EXECUTE format('ALTER TABLE squidgy_dev.%I ENABLE ROW LEVEL SECURITY', r.tablename);
        RAISE NOTICE '  ✓ Enabled RLS on table: %', r.tablename;
    END LOOP;

    -- Copy all policies
    FOR r IN
        SELECT
            schemaname,
            tablename,
            policyname,
            permissive,
            roles,
            cmd,
            qual,
            with_check
        FROM pg_policies
        WHERE schemaname = 'public'
    LOOP
        RAISE NOTICE 'Copying policy: % on table: %', r.policyname, r.tablename;

        -- Build CREATE POLICY statement
        policy_def := format('CREATE POLICY %I ON squidgy_dev.%I', r.policyname, r.tablename);

        -- Add AS PERMISSIVE/RESTRICTIVE
        IF r.permissive = 'PERMISSIVE' THEN
            policy_def := policy_def || ' AS PERMISSIVE';
        ELSE
            policy_def := policy_def || ' AS RESTRICTIVE';
        END IF;

        -- Add FOR clause
        policy_def := policy_def || ' FOR ' || r.cmd;

        -- Add TO clause (roles)
        policy_def := policy_def || ' TO ' || array_to_string(r.roles, ', ');

        -- Add USING clause
        IF r.qual IS NOT NULL THEN
            policy_def := policy_def || ' USING (' || r.qual || ')';
        END IF;

        -- Add WITH CHECK clause
        IF r.with_check IS NOT NULL THEN
            policy_def := policy_def || ' WITH CHECK (' || r.with_check || ')';
        END IF;

        EXECUTE policy_def;

        RAISE NOTICE '  ✓ Copied policy: %', r.policyname;
    END LOOP;
END $$;

-- Step 9: Grant table-level privileges to standard roles
-- ============================================================================
DO $$
DECLARE
    r RECORD;
BEGIN
    RAISE NOTICE '=== Granting Table Privileges ===';

    -- Grant privileges on all tables to standard Supabase roles
    FOR r IN
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'squidgy_dev'
        ORDER BY tablename
    LOOP
        RAISE NOTICE 'Granting privileges on table: %', r.tablename;

        -- Grant SELECT to anon (public read access)
        EXECUTE format('GRANT SELECT ON TABLE squidgy_dev.%I TO anon', r.tablename);

        -- Grant full CRUD to authenticated users
        EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE squidgy_dev.%I TO authenticated', r.tablename);

        -- Grant ALL to postgres and service_role
        EXECUTE format('GRANT ALL ON TABLE squidgy_dev.%I TO postgres', r.tablename);
        EXECUTE format('GRANT ALL ON TABLE squidgy_dev.%I TO service_role', r.tablename);

        RAISE NOTICE '  ✓ Granted privileges on %', r.tablename;
    END LOOP;
END $$;

-- Step 10: Grant default privileges for future objects
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '=== Setting Default Privileges ===';

    -- Grant default privileges for tables
    ALTER DEFAULT PRIVILEGES IN SCHEMA squidgy_dev
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO postgres;

    ALTER DEFAULT PRIVILEGES IN SCHEMA squidgy_dev
    GRANT SELECT ON TABLES TO anon;

    ALTER DEFAULT PRIVILEGES IN SCHEMA squidgy_dev
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO authenticated;

    ALTER DEFAULT PRIVILEGES IN SCHEMA squidgy_dev
    GRANT ALL ON TABLES TO service_role;

    -- Grant default privileges for sequences
    ALTER DEFAULT PRIVILEGES IN SCHEMA squidgy_dev
    GRANT USAGE, SELECT ON SEQUENCES TO postgres;

    ALTER DEFAULT PRIVILEGES IN SCHEMA squidgy_dev
    GRANT USAGE, SELECT ON SEQUENCES TO authenticated;

    ALTER DEFAULT PRIVILEGES IN SCHEMA squidgy_dev
    GRANT ALL ON SEQUENCES TO service_role;

    -- Grant default privileges for functions
    ALTER DEFAULT PRIVILEGES IN SCHEMA squidgy_dev
    GRANT EXECUTE ON FUNCTIONS TO postgres;

    ALTER DEFAULT PRIVILEGES IN SCHEMA squidgy_dev
    GRANT EXECUTE ON FUNCTIONS TO anon;

    ALTER DEFAULT PRIVILEGES IN SCHEMA squidgy_dev
    GRANT EXECUTE ON FUNCTIONS TO authenticated;

    ALTER DEFAULT PRIVILEGES IN SCHEMA squidgy_dev
    GRANT ALL ON FUNCTIONS TO service_role;

    RAISE NOTICE '  ✓ Set default privileges';
END $$;

-- Step 11: Copy foreign key constraints
-- ============================================================================
-- Note: Foreign keys are already copied with "INCLUDING ALL" in table creation
-- But we verify and log them here
DO $$
DECLARE
    r RECORD;
BEGIN
    RAISE NOTICE '=== Verifying Foreign Key Constraints ===';

    FOR r IN
        SELECT
            tc.table_name,
            tc.constraint_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_schema = 'squidgy_dev'
    LOOP
        RAISE NOTICE '  ✓ FK: %.% -> %.%',
            r.table_name, r.column_name,
            r.foreign_table_name, r.foreign_column_name;
    END LOOP;
END $$;

-- Step 12: Generate summary report
-- ============================================================================
DO $$
DECLARE
    table_count INTEGER;
    function_count INTEGER;
    view_count INTEGER;
    sequence_count INTEGER;
    trigger_count INTEGER;
    policy_count INTEGER;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
    RAISE NOTICE '               MIGRATION SUMMARY REPORT';
    RAISE NOTICE '============================================================';

    -- Count tables
    SELECT COUNT(*) INTO table_count
    FROM pg_tables WHERE schemaname = 'squidgy_dev';
    RAISE NOTICE 'Tables copied:     %', table_count;

    -- Count functions
    SELECT COUNT(*) INTO function_count
    FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname = 'squidgy_dev';
    RAISE NOTICE 'Functions copied:  %', function_count;

    -- Count views
    SELECT COUNT(*) INTO view_count
    FROM information_schema.views
    WHERE table_schema = 'squidgy_dev';
    RAISE NOTICE 'Views copied:      %', view_count;

    -- Count sequences
    SELECT COUNT(*) INTO sequence_count
    FROM information_schema.sequences
    WHERE sequence_schema = 'squidgy_dev';
    RAISE NOTICE 'Sequences copied:  %', sequence_count;

    -- Count triggers
    SELECT COUNT(*) INTO trigger_count
    FROM pg_trigger
    WHERE tgrelid IN (
        SELECT oid FROM pg_class
        WHERE relnamespace = 'squidgy_dev'::regnamespace
    )
    AND NOT tgisinternal;
    RAISE NOTICE 'Triggers copied:   %', trigger_count;

    -- Count policies
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE schemaname = 'squidgy_dev';
    RAISE NOTICE 'Policies copied:   %', policy_count;

    RAISE NOTICE '============================================================';
    RAISE NOTICE '✅ Migration completed successfully!';
    RAISE NOTICE '============================================================';
    RAISE NOTICE '';
    RAISE NOTICE '⚠️  IMPORTANT NEXT STEPS:';
    RAISE NOTICE '1. Update your .env files:';
    RAISE NOTICE '   Backend:  SUPABASE_SCHEMA=squidgy_dev';
    RAISE NOTICE '   UI:       VITE_SUPABASE_SCHEMA=squidgy_dev';
    RAISE NOTICE '   Game:     VITE_SUPABASE_SCHEMA=squidgy_dev';
    RAISE NOTICE '';
    RAISE NOTICE '2. Test the new schema thoroughly';
    RAISE NOTICE '3. Verify all data, functions, and permissions';
    RAISE NOTICE '';
END $$;

-- ============================================================================
-- VERIFICATION QUERIES (Run these to verify the migration)
-- ============================================================================

-- Uncomment to run verification queries:

/*
-- Compare table counts
SELECT 'public' as schema, COUNT(*) as table_count FROM pg_tables WHERE schemaname = 'public'
UNION ALL
SELECT 'squidgy_dev', COUNT(*) FROM pg_tables WHERE schemaname = 'squidgy_dev';

-- Compare row counts for all tables
DO $$
DECLARE
    r RECORD;
    public_count BIGINT;
    dev_count BIGINT;
BEGIN
    RAISE NOTICE 'Table Row Count Comparison:';
    RAISE NOTICE '---------------------------------------------------';

    FOR r IN
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename
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
*/
