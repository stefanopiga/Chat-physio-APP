-- Script data migration per chunk orfani
-- Genera documenti placeholder per chunk esistenti senza document_id valido

WITH orphan_metadata AS (
    SELECT DISTINCT
        dc.metadata->>'document_name' AS file_name,
        COALESCE(dc.metadata->>'document_id', gen_random_uuid()::text) AS placeholder_id,
        dc.metadata->>'chunking_strategy' AS chunking_strategy
    FROM document_chunks dc
    LEFT JOIN documents d ON dc.document_id = d.id
    WHERE d.id IS NULL
)
INSERT INTO documents (id, file_name, file_path, file_hash, status, chunking_strategy, metadata)
SELECT 
    placeholder_id::uuid,
    COALESCE(file_name, 'unknown_document'),
    'retroactive_migration',
    md5(random()::text),  -- Hash placeholder
    'completed',
    chunking_strategy,
    '{"source": "retroactive_migration"}'::jsonb
FROM orphan_metadata
ON CONFLICT (file_hash) DO NOTHING;

DO $$
DECLARE
    fixed_count INT;
BEGIN
    SELECT COUNT(*) INTO fixed_count
    FROM document_chunks dc
    WHERE EXISTS (SELECT 1 FROM documents d WHERE d.id = dc.document_id);
    RAISE NOTICE 'Fixed orphan chunks: %', fixed_count;
END $$;