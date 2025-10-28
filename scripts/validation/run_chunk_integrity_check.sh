#!/usr/bin/env bash
# Script per eseguire la verifica di integrità dei chunk.
# Può essere usato in locale o in CI.

set -e

echo "========================================="
echo "Verifica Integrità Chunk - Story 2.11 AC4"
echo "========================================="
echo ""

# Verifica DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERROR: DATABASE_URL environment variable non configurata"
    echo ""
    echo "Configura DATABASE_URL prima di eseguire questo script:"
    echo "  export DATABASE_URL='postgresql://user:pass@host:port/dbname'"
    echo ""
    exit 1
fi

echo "✓ DATABASE_URL configurata"
echo ""

# Opzione 1: Usa lo script Python standalone
echo "--- Verifica con script Python standalone ---"
cd "$(dirname "$0")/../.."
python scripts/validation/verify_chunk_ids.py
echo ""

# Opzione 2: Esegui test pytest di integrità
echo "--- Verifica con pytest (test di integrità) ---"
cd apps/api
poetry run pytest tests/test_chunk_integrity.py -v
echo ""

echo "========================================="
echo "✅ Verifica completata con successo!"
echo "========================================="

