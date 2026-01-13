-- ============================================================================
-- Fix ULID generation function type casting
-- ============================================================================

CREATE OR REPLACE FUNCTION generate_ulid() RETURNS TEXT AS $$
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
        -- Explicitly cast position to INTEGER to fix 'function substring does not exist' error
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

COMMENT ON FUNCTION generate_ulid() IS 'Generate ULID (Universally Unique Lexicographically Sortable Identifier) - Fixed Type Casting';
