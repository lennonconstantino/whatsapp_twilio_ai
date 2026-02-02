ALTER TABLE users ADD COLUMN auth_id TEXT UNIQUE;
CREATE INDEX idx_users_auth_id ON users(auth_id);
COMMENT ON COLUMN users.auth_id IS 'External authentication ID (e.g. from Supabase Auth)';
