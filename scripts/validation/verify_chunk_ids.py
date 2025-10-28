from __future__ import annotations

import asyncio
import os
from typing import Sequence

import asyncpg


CHECK_DUPLICATE_IDS = """
SELECT id, COUNT(*) AS occurrences
FROM document_chunks
GROUP BY id
HAVING COUNT(*) > 1;
"""

CHECK_DUPLICATE_INDEXES = """
SELECT document_id, metadata->>'chunk_index' AS chunk_index, COUNT(*) AS occurrences
FROM document_chunks
GROUP BY document_id, metadata->>'chunk_index'
HAVING COUNT(*) > 1
ORDER BY occurrences DESC;
"""


async def verify_chunk_ids(dsn: str) -> None:
    # statement_cache_size=0 per compatibilità con pgbouncer (Supabase)
    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        duplicate_ids: Sequence[asyncpg.Record] = await conn.fetch(CHECK_DUPLICATE_IDS)
        duplicate_indexes: Sequence[asyncpg.Record] = await conn.fetch(CHECK_DUPLICATE_INDEXES)

        if duplicate_ids:
            print("❌ Found duplicate chunk IDs:")
            for row in duplicate_ids:
                print(f"  - {row['id']} (occurrences: {row['occurrences']})")
        else:
            print("✅ document_chunks.id values are globally unique.")

        if duplicate_indexes:
            print("\n⚠️  Found duplicate (document_id, chunk_index) pairs:")
            for row in duplicate_indexes:
                idx = row["chunk_index"] or "NULL"
                print(f"  - document {row['document_id']} / chunk_index {idx} (occurrences: {row['occurrences']})")
        else:
            print("✅ (document_id, chunk_index) pairs are unique.")
    finally:
        await conn.close()


def main() -> None:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL environment variable is required to verify chunk IDs.")

    asyncio.run(verify_chunk_ids(dsn))


if __name__ == "__main__":
    main()
