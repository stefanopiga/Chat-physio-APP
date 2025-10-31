-- Story 4.2.4: Persistenza Feedback Database
-- Migration: Create public.feedback table with RLS policies and performance indexes
-- Date: 2025-10-30
-- Risk Mitigation: SEC-001 (RLS admin-only SELECT), DATA-001 (UNIQUE constraint + UPSERT)
-- =============================================================================
-- 1. CREATE TABLE public.feedback
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    message_id UUID NOT NULL,
    vote TEXT NOT NULL CHECK (vote IN ('up', 'down')),
    comment TEXT,
    user_id UUID REFERENCES auth.users(id),
    ip_address TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- DATA-001 MITIGATION: Prevent duplicate feedback for same session+message
    -- This constraint is critical for UPSERT logic robustness
    CONSTRAINT unique_session_message UNIQUE(session_id, message_id)
);
-- Add table comment
COMMENT ON TABLE public.feedback IS 'User feedback (thumbs up/down) for chat messages - Story 4.2.4';
COMMENT ON COLUMN public.feedback.vote IS 'Feedback vote: up or down';
COMMENT ON COLUMN public.feedback.user_id IS 'References auth.users(id) - NULL for anonymous students';
COMMENT ON COLUMN public.feedback.ip_address IS 'Client IP address (masked for GDPR compliance)';
-- =============================================================================
-- 2. PERFORMANCE INDEXES
-- =============================================================================
-- Index for session-based queries
CREATE INDEX idx_feedback_session_id ON public.feedback(session_id);
-- Index for message-based queries
CREATE INDEX idx_feedback_message_id ON public.feedback(message_id);
-- Index for time-range analytics queries (DESC for recent-first sorting)
CREATE INDEX idx_feedback_created_at ON public.feedback(created_at DESC);
-- Index for vote aggregations (COUNT by vote type)
CREATE INDEX idx_feedback_vote ON public.feedback(vote);
-- =============================================================================
-- 3. TRIGGER: Auto-update updated_at timestamp
-- =============================================================================
-- Create or replace function to update updated_at
CREATE OR REPLACE FUNCTION public.update_feedback_updated_at() RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = NOW();
RETURN NEW;
END;
$$ LANGUAGE plpgsql;
-- Attach trigger to feedback table
CREATE TRIGGER trigger_update_feedback_updated_at BEFORE
UPDATE ON public.feedback FOR EACH ROW EXECUTE FUNCTION public.update_feedback_updated_at();
-- =============================================================================
-- 4. ROW LEVEL SECURITY (RLS) POLICIES
-- =============================================================================
-- Enable RLS on feedback table
ALTER TABLE public.feedback ENABLE ROW LEVEL SECURITY;
-- Policy 1: Anyone can insert feedback (students with valid JWT can submit)
-- This allows authenticated users to create feedback entries
CREATE POLICY "Anyone can insert feedback" ON public.feedback FOR
INSERT WITH CHECK (true);
-- Policy 2: SEC-001 MITIGATION - Only admins can read all feedback
-- This prevents students from reading other users' feedback
-- Pattern aligned with existing users table RLS (see migration 20251009)
-- Checks 'admin' role from JWT app_metadata
CREATE POLICY "Admins can read all feedback" ON public.feedback FOR
SELECT USING (
        (
            SELECT auth.jwt()->'app_metadata'->>'role'
        ) = 'admin'
    );
-- =============================================================================
-- 5. VERIFICATION QUERIES (for manual testing after migration)
-- =============================================================================
-- Verify table structure
-- SELECT column_name, data_type, is_nullable 
-- FROM information_schema.columns 
-- WHERE table_name = 'feedback' AND table_schema = 'public';
-- Verify indexes
-- SELECT indexname, indexdef 
-- FROM pg_indexes 
-- WHERE tablename = 'feedback' AND schemaname = 'public';
-- Verify RLS policies
-- SELECT policyname, permissive, roles, cmd, qual 
-- FROM pg_policies 
-- WHERE tablename = 'feedback' AND schemaname = 'public';
-- Test insert (should succeed with any authenticated user)
-- INSERT INTO public.feedback (session_id, message_id, vote) 
-- VALUES (gen_random_uuid(), gen_random_uuid(), 'up');
-- Test UPSERT (should update existing record, not create duplicate)
-- INSERT INTO public.feedback (session_id, message_id, vote) 
-- VALUES ('same-session-uuid', 'same-message-uuid', 'up')
-- ON CONFLICT (session_id, message_id) 
-- DO UPDATE SET vote = EXCLUDED.vote, updated_at = NOW();