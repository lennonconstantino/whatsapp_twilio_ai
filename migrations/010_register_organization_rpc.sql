-- Migration: Create atomic RPC for organization registration and ensure users have email

SET search_path = app, extensions, public;

-- 1. Ensure users table has email column (missing in initial schema)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_schema = 'app' 
                   AND table_name = 'users' 
                   AND column_name = 'email') THEN
        ALTER TABLE users ADD COLUMN email TEXT;
        CREATE INDEX idx_users_email ON users(email);
    END IF;
END $$;

-- 2. Create RPC for atomic registration
CREATE OR REPLACE FUNCTION register_organization_atomic(
    p_owner_name TEXT,
    p_owner_email TEXT,
    p_user_auth_id TEXT,
    p_user_email TEXT,
    p_user_first_name TEXT,
    p_user_last_name TEXT,
    p_user_phone TEXT,
    p_user_role TEXT DEFAULT 'admin'
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = app, extensions, public
AS $$
DECLARE
    v_owner_id TEXT;
    v_user_id TEXT;
BEGIN
    -- 1. Create Owner
    INSERT INTO owners (name, email, active)
    VALUES (p_owner_name, p_owner_email, TRUE)
    RETURNING owner_id INTO v_owner_id;

    -- 2. Create Admin User
    INSERT INTO users (
        owner_id,
        auth_id,
        email,
        profile_name,
        first_name,
        last_name,
        phone,
        role,
        active
    )
    VALUES (
        v_owner_id,
        p_user_auth_id,
        p_user_email,
        COALESCE(p_user_first_name || ' ' || p_user_last_name, p_user_email, 'Admin'),
        p_user_first_name,
        p_user_last_name,
        p_user_phone,
        p_user_role,
        TRUE
    )
    RETURNING user_id INTO v_user_id;

    -- Return the IDs
    RETURN jsonb_build_object(
        'owner_id', v_owner_id,
        'user_id', v_user_id
    );
EXCEPTION WHEN OTHERS THEN
    -- Transaction will be automatically rolled back
    RAISE;
END;
$$;

COMMENT ON FUNCTION register_organization_atomic IS 'Creates Owner and Admin User atomically. Rolls back both if either fails.';
