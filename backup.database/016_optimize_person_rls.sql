-- Migration: Optimize RLS for Person Table
-- Created at: 2026-02-02
-- Description: Improves performance by avoiding per-row evaluation of auth.role()
-- Reference: https://supabase.com/docs/guides/database/postgres/row-level-security#performance

DROP POLICY IF EXISTS "Authenticated users can view person" ON public.person;

CREATE POLICY "Authenticated users can view person"
ON public.person
FOR ALL
USING (
    (SELECT auth.role()) = 'authenticated'
);
