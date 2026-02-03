-- 001_create_auth_schema.sql
-- Criar schema auth
CREATE SCHEMA IF NOT EXISTS auth;

-- Criar tabela básica de usuários (simplificada)
CREATE TABLE IF NOT EXISTS auth.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE,
    encrypted_password TEXT,
    email_confirmed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    raw_app_meta_data JSONB,
    raw_user_meta_data JSONB,
    is_super_admin BOOLEAN DEFAULT FALSE,
    role TEXT
);

-- Grants básicos
GRANT USAGE ON SCHEMA auth TO anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA auth TO service_role;
GRANT SELECT ON auth.users TO authenticated;

-- Função auxiliar para pegar o usuário atual (mock para desenvolvimento)
CREATE OR REPLACE FUNCTION auth.uid() 
RETURNS UUID AS $$
    SELECT COALESCE(
        NULLIF(current_setting('request.jwt.claim.sub', true), '')::UUID,
        (SELECT id FROM auth.users LIMIT 1)
    );
$$ LANGUAGE SQL STABLE;

-- Função auxiliar para pegar o role atual
CREATE OR REPLACE FUNCTION auth.role() 
RETURNS TEXT AS $$
    SELECT COALESCE(
        NULLIF(current_setting('request.jwt.claim.role', true), ''),
        current_user
    )::TEXT;
$$ LANGUAGE SQL STABLE;