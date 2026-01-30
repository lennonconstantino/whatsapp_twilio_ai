-- Add preferences column to users table
ALTER TABLE public.users
ADD COLUMN IF NOT EXISTS preferences JSONB DEFAULT '{}'::jsonb;

-- Create index for preferences for faster lookups if needed (optional but good practice)
CREATE INDEX IF NOT EXISTS idx_users_preferences ON public.users USING gin (preferences);
