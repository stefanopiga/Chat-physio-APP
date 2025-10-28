-- Story 4.4 Prerequisito: Tabella Documents
-- Migration: create documents table + foreign key constraint

-- Creazione tabella documents
CREATE TABLE IF NOT EXISTS documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  file_name TEXT NOT NULL,
  file_path TEXT NOT NULL,
  file_hash TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL DEFAULT 'pending',
  chunking_strategy JSONB,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indice per ricerca efficiente per hash (deduplicazione)
CREATE INDEX IF NOT EXISTS documents_file_hash_idx ON documents(file_hash);

-- Indice per filtraggio per status
CREATE INDEX IF NOT EXISTS documents_status_idx ON documents(status);

-- Indice per ordinamento temporale
CREATE INDEX IF NOT EXISTS documents_created_at_idx ON documents(created_at DESC);

-- Trigger per aggiornamento automatico updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_documents_updated_at
BEFORE UPDATE ON documents
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Foreign key constraint per document_chunks.document_id
-- Nota: Questa constraint verrà applicata solo se la tabella document_chunks
-- contiene già record con document_id validi. In caso contrario, sarà necessario
-- un passaggio di data migration preliminare.
ALTER TABLE document_chunks
ADD CONSTRAINT fk_document_chunks_document_id
FOREIGN KEY (document_id)
REFERENCES documents(id)
ON DELETE CASCADE;

-- Commento esplicativo
COMMENT ON TABLE documents IS 'Metadati per file sorgente caricati nel sistema';
COMMENT ON COLUMN documents.file_hash IS 'Hash SHA-256 per deduplicazione documenti';
COMMENT ON COLUMN documents.chunking_strategy IS 'Strategia chunking applicata (es. {"type": "recursive", "chunk_size": 800})';
COMMENT ON COLUMN documents.status IS 'Valori ammessi: pending, processing, completed, error';

