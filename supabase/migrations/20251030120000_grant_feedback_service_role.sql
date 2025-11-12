-- Story 4.2.4: Hotfix - Grant permissions to service_role on feedback table
-- Issue: Backend service_role cannot access public.feedback (permission denied 42501)
-- Root Cause: Missing explicit GRANT in initial migration

-- Grant ALL privileges to service_role (backend FastAPI)
GRANT ALL ON TABLE public.feedback TO service_role;

-- Grant ALL to postgres superuser (admin operations)
GRANT ALL ON TABLE public.feedback TO postgres;

-- Grant USAGE on sequence if exists (for id generation)
-- Note: gen_random_uuid() doesn't need sequence, but keeping for consistency
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO service_role;

-- Verify grants with:
-- SELECT grantee, privilege_type 
-- FROM information_schema.table_privileges 
-- WHERE table_schema = 'public' AND table_name = 'feedback';










