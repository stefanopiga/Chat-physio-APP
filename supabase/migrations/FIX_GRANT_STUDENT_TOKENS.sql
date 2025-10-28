-- FIX: Aggiunge GRANT mancanti per service_role su tabelle student_tokens e refresh_tokens
-- Errore: permission denied for table student_tokens (42501)
-- Causa: service_role non ha privilegi SELECT/INSERT/UPDATE/DELETE sulle tabelle

-- GRANT su student_tokens
GRANT ALL ON TABLE public.student_tokens TO service_role;
GRANT ALL ON TABLE public.student_tokens TO postgres;

-- GRANT su refresh_tokens  
GRANT ALL ON TABLE public.refresh_tokens TO service_role;
GRANT ALL ON TABLE public.refresh_tokens TO postgres;

-- Verifica GRANT applicati (esegui dopo per conferma)
-- SELECT grantee, privilege_type 
-- FROM information_schema.table_privileges 
-- WHERE table_name IN ('student_tokens', 'refresh_tokens')
--   AND table_schema = 'public'
-- ORDER BY table_name, grantee, privilege_type;

-- Output atteso:
-- grantee       | privilege_type | table_name
-- --------------|----------------|------------------
-- postgres      | SELECT         | student_tokens
-- postgres      | INSERT         | student_tokens
-- postgres      | UPDATE         | student_tokens
-- postgres      | DELETE         | student_tokens
-- service_role  | SELECT         | student_tokens
-- service_role  | INSERT         | student_tokens
-- service_role  | UPDATE         | student_tokens
-- service_role  | DELETE         | student_tokens
-- (e lo stesso per refresh_tokens)

