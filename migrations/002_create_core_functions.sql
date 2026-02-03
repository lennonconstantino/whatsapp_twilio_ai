-- ============================================================================
-- CREATE CORE FUNCTIONS
-- ============================================================================
-- Core database functions that DON'T depend on tables
-- These must be created BEFORE tables
-- ============================================================================

-- Set search path for the session
SET search_path = app, extensions, public;

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Creating core functions...';
    RAISE NOTICE '==============================================';
END $$;

-- ============================================================================
-- ULID GENERATION FUNCTION
-- ============================================================================
-- ULID Format: 01ARZ3NDEKTSV4RRFFQ69G5FAV (26 characters)
-- Encoding: Crockford's Base32
-- Structure: TTTTTTTTTTRRRRRRRRRRRRRRRR
--            |________| |______________|
--             Timestamp   Randomness
--            (10 chars)    (16 chars)
-- ============================================================================

CREATE OR REPLACE FUNCTION generate_ulid() 
RETURNS TEXT
SET search_path = app, extensions, public, temp
AS $$
DECLARE
    -- Crockford's Base32 alphabet (excludes I, L, O, U to avoid confusion)
    encoding   TEXT := '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
    timestamp  BIGINT;
    output     TEXT := '';
    unix_time  BIGINT;
    random_part BIGINT;
BEGIN
    -- Get current timestamp in milliseconds
    unix_time := (EXTRACT(EPOCH FROM CLOCK_TIMESTAMP()) * 1000)::BIGINT;
    timestamp := unix_time;
    
    -- Encode timestamp (10 characters)
    FOR i IN 1..10 LOOP
        output := output || SUBSTRING(encoding FROM ((timestamp % 32) + 1)::INTEGER FOR 1);
        timestamp := timestamp / 32;
    END LOOP;
    
    -- Add random part (16 characters)
    FOR i IN 1..16 LOOP
        random_part := (RANDOM() * 31)::INTEGER;
        output := output || SUBSTRING(encoding FROM (random_part + 1)::INTEGER FOR 1);
    END LOOP;
    
    RETURN output;
END;
$$ LANGUAGE plpgsql VOLATILE;

COMMENT ON FUNCTION generate_ulid() IS 'Generate ULID (Universally Unique Lexicographically Sortable Identifier)';

-- ============================================================================
-- ULID VALIDATION FUNCTION
-- ============================================================================

CREATE OR REPLACE FUNCTION is_valid_ulid(ulid TEXT)
RETURNS BOOLEAN
SET search_path = app, extensions, public, temp
AS $$
DECLARE
    encoding TEXT := '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
    char TEXT;
BEGIN
    -- Check length
    IF LENGTH(ulid) != 26 THEN
        RETURN FALSE;
    END IF;
    
    -- Check if all characters are in the encoding alphabet
    FOR i IN 1..26 LOOP
        char := SUBSTRING(ulid FROM i FOR 1);
        IF POSITION(char IN encoding) = 0 THEN
            RETURN FALSE;
        END IF;
    END LOOP;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION is_valid_ulid(TEXT) IS 'Validate ULID format (26 chars, Crockford Base32)';

-- ============================================================================
-- ULID TO TIMESTAMP FUNCTION
-- ============================================================================

CREATE OR REPLACE FUNCTION ulid_to_timestamp(ulid TEXT)
RETURNS TIMESTAMP WITH TIME ZONE
SET search_path = app, extensions, public, temp
AS $$
DECLARE
    encoding TEXT := '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
    char TEXT;
    val BIGINT;
    timestamp BIGINT := 0;
BEGIN
    IF NOT is_valid_ulid(ulid) THEN
        RETURN NULL;
    END IF;

    -- Decode first 10 characters
    FOR i IN 1..10 LOOP
        char := SUBSTRING(ulid FROM i FOR 1);
        val := POSITION(char IN encoding) - 1;
        timestamp := timestamp * 32 + val;
    END LOOP;

    RETURN to_timestamp(timestamp / 1000.0);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION ulid_to_timestamp(TEXT) IS 'Extract timestamp from ULID';

-- ============================================================================
-- UPDATE TIMESTAMP FUNCTION
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER
SET search_path = app, extensions, public, temp
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_updated_at_column() IS 'Trigger function to automatically update updated_at timestamp';

-- ============================================================================
-- INSERT ID HELPERS (for backward compatibility if needed)
-- ============================================================================

CREATE OR REPLACE FUNCTION set_ulid_on_insert()
RETURNS TRIGGER
SET search_path = app, extensions, public, temp
AS $$
BEGIN
    IF NEW.id IS NULL THEN
        NEW.id := generate_ulid();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Specific ones for tables that might use different ID column names
-- Though in our schema most use {table}_id or id

CREATE OR REPLACE FUNCTION set_owners_id_on_insert()
RETURNS TRIGGER
SET search_path = app, extensions, public, temp
AS $$
BEGIN
    IF NEW.owner_id IS NULL THEN
        NEW.owner_id := generate_ulid();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION set_users_id_on_insert()
RETURNS TRIGGER
SET search_path = app, extensions, public, temp
AS $$
BEGIN
    IF NEW.user_id IS NULL THEN
        NEW.user_id := generate_ulid();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION set_history_id_on_insert()
RETURNS TRIGGER
SET search_path = app, extensions, public, temp
AS $$
BEGIN
    IF NEW.history_id IS NULL THEN
        NEW.history_id := generate_ulid();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Core functions created successfully!';
    RAISE NOTICE '✓ generate_ulid()';
    RAISE NOTICE '✓ is_valid_ulid()';
    RAISE NOTICE '✓ ulid_to_timestamp()';
    RAISE NOTICE '✓ update_updated_at_column()';
    RAISE NOTICE '==============================================';
END $$;
