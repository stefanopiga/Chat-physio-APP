"""
Database Integrity Audit Script
Story 2.6 - Task 12: Database Integrity Audit

Query database per identificare:
- Orphan documents (completed senza chunks)
- Orphan chunks (embedding NULL)
- Index pgvector performance

Usage:
    python scripts/validation/database_integrity_audit.py
"""
import os
import asyncio
import asyncpg
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import json
from urllib.parse import urlparse


class DatabaseIntegrityAuditor:
    """Auditor per integrità database Supabase."""
    
    def __init__(self):
        # Ensure .env values override host environment for consistent audit behavior
        env_path = Path(__file__).resolve().parents[2] / ".env"
        load_dotenv(dotenv_path=env_path, override=True)
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL not set in environment")
        
        self.conn = None
    
    async def connect(self):
        """Connessione al database."""
        print("Connecting to database...", flush=True)
        try:
            parsed = urlparse(self.database_url)
            print(f"Host: {parsed.hostname}, Port: {parsed.port}, DB: {parsed.path.lstrip('/')}", flush=True)
        except Exception:
            pass
        # PgBouncer compatibility: disable prepared statement cache
        self.conn = await asyncpg.connect(self.database_url, statement_cache_size=0)
    
    async def close(self):
        """Chiusura connessione."""
        if self.conn:
            await self.conn.close()
    
    async def check_orphan_documents(self) -> dict:
        """
        Query documenti 'completed' senza chunks.
        Indica pipeline fallita silentemente dopo document save.
        """
        print("Checking for orphan documents (completed without chunks)...", flush=True)
        
        query = """
        SELECT 
            d.id, 
            d.file_name, 
            d.status, 
            d.created_at,
            COUNT(c.id) as chunk_count
        FROM documents d
        LEFT JOIN document_chunks c ON d.id = c.document_id
        WHERE d.status = 'completed'
        GROUP BY d.id
        HAVING COUNT(c.id) = 0
        ORDER BY d.created_at DESC
        LIMIT 20;
        """
        
        rows = await self.conn.fetch(query)
        
        orphans = []
        for row in rows:
            orphans.append({
                "id": str(row["id"]),
                "file_name": row["file_name"],
                "status": row["status"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "chunk_count": row["chunk_count"]
            })
        
        return {
            "query": "orphan_documents_completed_no_chunks",
            "count": len(orphans),
            "documents": orphans,
            "status": "WARN" if orphans else "OK"
        }
    
    async def check_null_embeddings(self) -> dict:
        """
        Query chunks con embedding NULL.
        Critical: impedisce semantic search.
        """
        print("Checking for chunks with NULL embeddings...", flush=True)
        
        # Count total
        count_query = """
        SELECT COUNT(*) as null_embeddings_count
        FROM document_chunks
        WHERE embedding IS NULL;
        """
        
        count_result = await self.conn.fetchrow(count_query)
        null_count = count_result["null_embeddings_count"]
        
        # Determine if chunk_index column exists (schema may differ per environment)
        chunk_index_exists = await self.conn.fetchval(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'document_chunks'
                  AND column_name = 'chunk_index'
            );
            """
        )
        if chunk_index_exists:
            chunk_index_column = "c.chunk_index"
        else:
            # Provide placeholder to keep consistent shape
            chunk_index_column = "NULL::int AS chunk_index"
        
        # Get sample
        sample_query = f"""
        SELECT 
            c.id,
            c.document_id,
            {chunk_index_column},
            c.content,
            c.created_at,
            d.file_name
        FROM document_chunks c
        LEFT JOIN documents d ON c.document_id = d.id
        WHERE c.embedding IS NULL
        ORDER BY c.created_at DESC
        LIMIT 10;
        """
        
        rows = await self.conn.fetch(sample_query)
        
        samples = []
        for row in rows:
            samples.append({
                "id": str(row["id"]),
                "document_id": str(row["document_id"]),
                "file_name": row["file_name"],
                "chunk_index": row["chunk_index"],
                "content_preview": row["content"][:100] if row["content"] else None,
                "created_at": row["created_at"].isoformat() if row["created_at"] else None
            })
        
        return {
            "query": "chunks_with_null_embeddings",
            "count": null_count,
            "sample": samples,
            "status": "CRITICAL" if null_count > 0 else "OK"
        }
    
    async def check_table_statistics(self) -> dict:
        """
        Statistiche tabelle documents e document_chunks.
        """
        print("Collecting table statistics...", flush=True)
        
        stats_query = """
        SELECT 
            (SELECT COUNT(*) FROM documents) as total_documents,
            (SELECT COUNT(*) FROM documents WHERE status = 'completed') as completed_documents,
            (SELECT COUNT(*) FROM documents WHERE status = 'processing') as processing_documents,
            (SELECT COUNT(*) FROM documents WHERE status = 'error') as error_documents,
            (SELECT COUNT(*) FROM document_chunks) as total_chunks,
            (SELECT COUNT(*) FROM document_chunks WHERE embedding IS NOT NULL) as chunks_with_embedding,
            (SELECT COUNT(DISTINCT document_id) FROM document_chunks) as documents_with_chunks;
        """
        
        result = await self.conn.fetchrow(stats_query)
        
        return {
            "query": "table_statistics",
            "documents": {
                "total": result["total_documents"],
                "completed": result["completed_documents"],
                "processing": result["processing_documents"],
                "error": result["error_documents"]
            },
            "chunks": {
                "total": result["total_chunks"],
                "with_embedding": result["chunks_with_embedding"],
                "null_embedding": result["total_chunks"] - result["chunks_with_embedding"]
            },
            "documents_with_chunks": result["documents_with_chunks"],
            "status": "OK"
        }
    
    async def check_pgvector_indices(self) -> dict:
        """
        Verifica indici pgvector presenti su document_chunks.
        """
        print("Checking pgvector indices...", flush=True)
        
        indices_query = """
        SELECT 
            indexname,
            tablename,
            indexdef
        FROM pg_indexes
        WHERE tablename = 'document_chunks'
        AND indexdef LIKE '%vector%';
        """
        
        rows = await self.conn.fetch(indices_query)
        
        indices = []
        for row in rows:
            indices.append({
                "index_name": row["indexname"],
                "table_name": row["tablename"],
                "definition": row["indexdef"]
            })
        
        return {
            "query": "pgvector_indices",
            "count": len(indices),
            "indices": indices,
            "status": "WARN" if len(indices) == 0 else "OK"
        }
    
    async def generate_report(self) -> dict:
        """Genera report completo database integrity audit."""
        await self.connect()
        
        try:
            report = {
                "timestamp": datetime.now().isoformat(),
                "story": "2.6",
                "task": "Task 12 - Database Integrity Audit",
                "checks": {}
            }
            
            # Run all checks
            report["checks"]["orphan_documents"] = await self.check_orphan_documents()
            report["checks"]["null_embeddings"] = await self.check_null_embeddings()
            report["checks"]["table_statistics"] = await self.check_table_statistics()
            report["checks"]["pgvector_indices"] = await self.check_pgvector_indices()
            
            # Overall status
            statuses = [
                report["checks"]["orphan_documents"]["status"],
                report["checks"]["null_embeddings"]["status"],
                report["checks"]["pgvector_indices"]["status"]
            ]
            
            if "CRITICAL" in statuses:
                report["overall_status"] = "CRITICAL"
            elif "WARN" in statuses:
                report["overall_status"] = "WARN"
            else:
                report["overall_status"] = "OK"
            
            return report
        finally:
            await self.close()
    
    def generate_markdown_report(self, report: dict) -> str:
        """Genera report Markdown."""
        lines = [
            "# Database Integrity Audit Report",
            "",
            f"**Timestamp:** {report['timestamp']}",
            f"**Story:** {report['story']}",
            f"**Task:** {report['task']}",
            "",
            f"## Overall Status: {report['overall_status']}",
            "",
            "## Table Statistics",
            ""
        ]
        
        stats = report["checks"]["table_statistics"]
        lines.extend([
            "### Documents",
            f"- **Total:** {stats['documents']['total']}",
            f"- **Completed:** {stats['documents']['completed']}",
            f"- **Processing:** {stats['documents']['processing']}",
            f"- **Error:** {stats['documents']['error']}",
            "",
            "### Chunks",
            f"- **Total:** {stats['chunks']['total']}",
            f"- **With Embedding:** {stats['chunks']['with_embedding']}",
            f"- **NULL Embedding:** {stats['chunks']['null_embedding']}",
            "",
            f"### Documents with Chunks: {stats['documents_with_chunks']}",
            ""
        ])
        
        # Orphan Documents
        orphans = report["checks"]["orphan_documents"]
        lines.extend([
            "## Orphan Documents (Completed without Chunks)",
            f"**Status:** {orphans['status']}",
            f"**Count:** {orphans['count']}",
            ""
        ])
        
        if orphans["documents"]:
            lines.append("| Document ID | File Name | Status | Created At |")
            lines.append("|-------------|-----------|--------|------------|")
            for doc in orphans["documents"][:10]:
                created_at = doc["created_at"][:19] if doc["created_at"] else "N/A"
                lines.append(f"| `{doc['id'][:8]}...` | {doc['file_name']} | {doc['status']} | {created_at} |")
            lines.append("")
        else:
            lines.extend([
                "[OK] No orphan documents found.",
                ""
            ])
        
        # NULL Embeddings
        null_emb = report["checks"]["null_embeddings"]
        lines.extend([
            "## Chunks with NULL Embeddings",
            f"**Status:** {null_emb['status']}",
            f"**Count:** {null_emb['count']}",
            ""
        ])
        
        if null_emb["count"] > 0:
            lines.extend([
                "[CRITICAL] Chunks with NULL embeddings found. These chunks cannot be searched.",
                "",
                "### Sample (First 10):",
                ""
            ])
            if null_emb["sample"]:
                lines.append("| Chunk ID | Document | File Name | Chunk Index | Created At |")
                lines.append("|----------|----------|-----------|-------------|------------|")
                for chunk in null_emb["sample"]:
                    created_at = chunk["created_at"][:19] if chunk["created_at"] else "N/A"
                    lines.append(f"| `{chunk['id'][:8]}...` | `{chunk['document_id'][:8]}...` | {chunk['file_name']} | {chunk['chunk_index']} | {created_at} |")
                lines.append("")
        else:
            lines.extend([
                "[OK] No chunks with NULL embeddings.",
                ""
            ])
        
        # pgvector Indices
        indices = report["checks"]["pgvector_indices"]
        lines.extend([
            "## pgvector Indices",
            f"**Status:** {indices['status']}",
            f"**Count:** {indices['count']}",
            ""
        ])
        
        if indices["indices"]:
            for idx in indices["indices"]:
                lines.extend([
                    f"### {idx['index_name']}",
                    f"**Table:** {idx['table_name']}",
                    f"**Definition:** `{idx['definition']}`",
                    ""
                ])
        else:
            lines.extend([
                "[WARN] No pgvector indices found on document_chunks table.",
                "Performance impact: Semantic search will be slow without vector index.",
                ""
            ])
        
        # Recommendations
        lines.extend([
            "## Recommendations",
            ""
        ])
        
        if report["overall_status"] == "CRITICAL":
            lines.extend([
                "### Critical Issues",
                f"1. **NULL Embeddings:** {null_emb['count']} chunks without embeddings",
                "   - Cause: Embedding generation failed or skipped",
                "   - Impact: These chunks invisible to semantic search",
                "   - Action: Re-index affected documents",
                ""
            ])
        
        if orphans["count"] > 0:
            lines.extend([
                "### Orphan Documents",
                f"{orphans['count']} documents marked 'completed' but have 0 chunks",
                "- Cause: Pipeline failed after document save but before chunking",
                "- Action: Investigate pipeline logs, consider re-ingestion",
                ""
            ])
        
        if indices["count"] == 0:
            lines.extend([
                "### Missing Vector Index",
                "No pgvector index on document_chunks table",
                "- Impact: Slow semantic search (full table scan)",
                "- Action: Create HNSW index with appropriate parameters",
                ""
            ])
        
        if report["overall_status"] == "OK":
            lines.extend([
                "[OK] Database integrity validated. No critical issues.",
                "- All completed documents have chunks",
                "- All chunks have embeddings",
                "- Vector indices present",
                ""
            ])
        
        return "\n".join(lines)


async def main():
    """Entry point."""
    project_root = Path(__file__).parent.parent.parent
    
    print("Starting Database Integrity Audit...")
    print()
    
    auditor = DatabaseIntegrityAuditor()
    
    try:
        # Generate report
        report = await auditor.generate_report()
        
        # Save JSON report
        json_output = project_root / "temp" / "database_integrity_report.json"
        json_output.parent.mkdir(parents=True, exist_ok=True)
        json_output.write_text(json.dumps(report, indent=2))
        print(f"[OK] JSON report saved: {json_output}")
        
        # Generate Markdown report
        markdown_report = auditor.generate_markdown_report(report)
        md_output = project_root / "docs" / "reports" / "rag-database-integrity.md"
        md_output.parent.mkdir(parents=True, exist_ok=True)
        md_output.write_text(markdown_report, encoding="utf-8")
        print(f"[OK] Markdown report saved: {md_output}")
        
        # Print summary
        print()
        print(f"Overall Status: {report['overall_status']}")
        print()
        
        stats = report["checks"]["table_statistics"]
        print(f"Documents: {stats['documents']['total']} total, {stats['documents']['completed']} completed")
        print(f"Chunks: {stats['chunks']['total']} total, {stats['chunks']['null_embedding']} NULL embeddings")
        
        orphans = report["checks"]["orphan_documents"]["count"]
        if orphans > 0:
            print(f"[WARN] {orphans} orphan document(s)")
        
        null_emb = report["checks"]["null_embeddings"]["count"]
        if null_emb > 0:
            print(f"[CRITICAL] {null_emb} chunk(s) with NULL embeddings")
        
        print()
        print("Full report: docs/reports/rag-database-integrity.md")
    
    except Exception as e:
        print(f"[ERROR] Audit failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

