#!/usr/bin/env python3
"""
Batch ingest documents into FisioRAG knowledge base.

This script recursively scans a directory for documents and ingests them
via the /api/v1/admin/knowledge-base/sync-jobs endpoint with rate limiting,
retry logic, and state management for resume capability.

Usage:
    python ingest_all_documents.py [options]

Environment variables required:
    OPENAI_API_KEY - OpenAI API key for embeddings
    SUPABASE_URL - Supabase project URL
    SUPABASE_SERVICE_KEY - Supabase service role key
    API_BASE_URL - FisioRAG API base URL (default: http://localhost)
    SUPABASE_JWT_SECRET - For JWT generation

Examples:
    # Full ingestion
    python ingest_all_documents.py

    # Test run with 3 files
    python ingest_all_documents.py --limit 3

    # Resume interrupted run
    python ingest_all_documents.py --state-file temp/ingestion_state.json
"""
import os
import sys
import json
import time
import random
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timezone
from dataclasses import dataclass, asdict

import requests
from docx import Document
from dotenv import load_dotenv

# Import JWT generation from admin script
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "admin"))
from generate_jwt import generate_admin_jwt

# Load environment
project_root = Path(__file__).resolve().parents[2]
load_dotenv(project_root / ".env", override=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%S%z",
)
logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    """Result of a single document ingestion."""

    file_path: str
    status: str  # success, failed, skipped
    job_id: Optional[str] = None
    inserted_chunks: Optional[int] = None
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class IngestionState:
    """Manages state file for resume capability."""

    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.processed_files: Set[str] = set()
        self.load()

    def load(self):
        """Load state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.processed_files = set(data.get("processed_files", []))
                logger.info(
                    f"Loaded state: {len(self.processed_files)} files already processed"
                )
            except Exception as e:
                logger.warning(f"Failed to load state file: {e}")

    def save(self):
        """Save state to file."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump({"processed_files": list(self.processed_files)}, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state file: {e}")

    def mark_processed(self, file_path: str):
        """Mark file as processed."""
        self.processed_files.add(file_path)
        self.save()

    def is_processed(self, file_path: str) -> bool:
        """Check if file was already processed."""
        return file_path in self.processed_files


def preflight_check() -> bool:
    """
    Verify required environment variables are present.

    Returns:
        bool: True if all required vars are set, False otherwise.
    """
    # Core required vars (must be present)
    required_vars = [
        "OPENAI_API_KEY",
        "SUPABASE_URL",
        "SUPABASE_JWT_SECRET",
    ]
    
    # SUPABASE_SERVICE_KEY can be either SUPABASE_SERVICE_KEY or SUPABASE_SERVICE_ROLE_KEY
    service_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
            logger.error(f"Missing environment variable: {var}")
    
    if not service_key:
        missing_vars.append("SUPABASE_SERVICE_KEY or SUPABASE_SERVICE_ROLE_KEY")
        logger.error("Missing environment variable: SUPABASE_SERVICE_KEY or SUPABASE_SERVICE_ROLE_KEY")

    if missing_vars:
        logger.error(
            f"Preflight check failed. Missing variables: {', '.join(missing_vars)}"
        )
        return False

    # Log masked values for verification
    logger.info("Preflight check passed. Environment variables loaded:")
    for var in required_vars:
        value = os.getenv(var, "")
        if len(value) > 10:
            masked = value[:4] + "..." + value[-4:]
        else:
            masked = "***"
        logger.info(f"  {var}: {masked}")
    
    # Log service key (whichever was found)
    service_key_name = "SUPABASE_SERVICE_KEY" if os.getenv("SUPABASE_SERVICE_KEY") else "SUPABASE_SERVICE_ROLE_KEY"
    masked = service_key[:4] + "..." + service_key[-4:] if len(service_key) > 10 else "***"
    logger.info(f"  {service_key_name}: {masked}")
    
    # API_BASE_URL is optional with default
    api_base = os.getenv("API_BASE_URL", "http://localhost")
    logger.info(f"  API_BASE_URL: {api_base} (default if not set)")

    return True


def extract_text_from_docx(file_path: Path) -> str:
    """Extract text from .docx file."""
    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def extract_text_from_file(file_path: Path) -> str:
    """
    Extract text from file based on extension.

    Supports: .docx, .txt, .md
    """
    suffix = file_path.suffix.lower()

    if suffix == ".docx":
        return extract_text_from_docx(file_path)
    elif suffix in [".txt", ".md"]:
        return file_path.read_text(encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file format: {suffix}")


def prepare_payload(file_path: Path, document_text: str, category: str) -> Dict[str, Any]:
    """
    Prepare ingestion payload.

    Args:
        file_path: Path to the document
        document_text: Extracted text content
        category: Document category (e.g., "fisioterapia")

    Returns:
        Payload dict for sync-jobs API
    """
    # Extract topic from parent directory name
    topic = file_path.parent.name

    # Resolve to absolute path and calculate relative path
    absolute_path = file_path.resolve()
    try:
        source_path = str(absolute_path.relative_to(project_root.resolve()))
    except ValueError:
        # If path is outside project root, use readable format
        source_path = str(Path(file_path.parent.name) / file_path.name)

    return {
        "document_text": document_text,
        "metadata": {
            "document_name": file_path.name,
            "category": category,
            "topic": topic,
            "source_path": source_path,
            "ingestion_batch": datetime.now(timezone.utc).isoformat(),
            "file_size": absolute_path.stat().st_size,
        },
    }


def ingest_document(
    api_url: str,
    jwt_token: str,
    payload: Dict[str, Any],
    max_retries: int = 5,
) -> Dict[str, Any]:
    """
    Call sync-jobs endpoint to ingest document with retry logic.

    Args:
        api_url: Full API endpoint URL
        jwt_token: Admin JWT token
        payload: Ingestion payload
        max_retries: Maximum number of retries for transient errors

    Returns:
        Response JSON from API

    Raises:
        requests.HTTPError: On non-retryable errors (400, 401, 403)
    """
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json",
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(
                api_url, headers=headers, json=payload, timeout=60
            )

            # Handle rate limiting (429)
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 10))
                # Add jitter to avoid thundering herd
                sleep_time = retry_after + random.uniform(0, 2)
                logger.warning(
                    f"Rate limited (429). Retry after {sleep_time:.1f}s (attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(sleep_time)
                continue

            # Check for non-retryable client errors (4xx except 429)
            if 400 <= response.status_code < 500 and response.status_code != 429:
                # Don't retry on auth errors, bad requests, etc.
                response.raise_for_status()
                # Will never reach here if status is error

            # Handle server errors (5xx) with exponential backoff
            if 500 <= response.status_code < 600:
                backoff_time = (2**attempt) + random.uniform(0, 1)
                logger.warning(
                    f"Server error {response.status_code}. Retry after {backoff_time:.1f}s (attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(backoff_time)
                continue

            # Success - raise for any other unexpected status and return
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            # HTTPError from raise_for_status() - check if it's retryable
            if hasattr(e.response, 'status_code'):
                status_code = e.response.status_code
                # Don't retry client errors (4xx except 429)
                if 400 <= status_code < 500 and status_code != 429:
                    raise
            # Otherwise, treat as retryable
            if attempt < max_retries - 1:
                backoff_time = (2**attempt) + random.uniform(0, 1)
                logger.warning(
                    f"HTTP error: {e}. Retry after {backoff_time:.1f}s (attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(backoff_time)
                continue
            raise

        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                backoff_time = (2**attempt) + random.uniform(0, 1)
                logger.warning(
                    f"Request timeout. Retry after {backoff_time:.1f}s (attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(backoff_time)
                continue
            raise

        except requests.exceptions.RequestException as e:
            # Other request errors (connection, etc.) are retryable
            if attempt < max_retries - 1:
                backoff_time = (2**attempt) + random.uniform(0, 1)
                logger.warning(
                    f"Request error: {e}. Retry after {backoff_time:.1f}s (attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(backoff_time)
                continue
            raise

    # If we exhausted retries
    raise Exception(f"Max retries ({max_retries}) exceeded")


def wait_for_job_completion(
    api_url: str,
    jwt_token: str,
    job_id: str,
    timeout_seconds: int = 300,
    poll_interval: int = 5,
) -> Dict[str, Any]:
    """
    Poll sync job status endpoint until completion or timeout.

    Args:
        api_url: Base sync-jobs endpoint
        jwt_token: Admin JWT token
        job_id: Identifier returned by StartSyncJobResponse
        timeout_seconds: Max seconds to wait
        poll_interval: Seconds between polls

    Returns:
        Final JSON payload from status endpoint when job completes successfully.

    Raises:
        RuntimeError: If job transitions to failed state
        TimeoutError: If job does not complete before timeout
    """
    status_url = api_url.rstrip("/") + f"/{job_id}"
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json",
    }

    deadline = time.time() + timeout_seconds
    last_payload: Dict[str, Any] | None = None

    while time.time() < deadline:
        response = requests.get(status_url, headers=headers, timeout=30)
        if response.status_code == 200:
            payload = response.json()
            last_payload = payload
            state = (payload.get("status") or "").lower()

            if state in {"success", "successful", "completed", "complete"}:
                return payload
            if state in {"failure", "failed"}:
                error_msg = payload.get("error") or "unknown error"
                raise RuntimeError(f"Sync job {job_id} failed: {error_msg}")

        elif response.status_code == 404:
            # Allow a short grace period for task registration
            time.sleep(1)
        else:
            response.raise_for_status()

        time.sleep(poll_interval)

    raise TimeoutError(f"Sync job {job_id} did not complete within {timeout_seconds}s (last payload: {last_payload})")


def find_documents(root_dir: Path, pattern: str) -> List[Path]:
    """
    Recursively find documents matching pattern.

    Args:
        root_dir: Root directory to scan
        pattern: Glob pattern (e.g., "*.docx")

    Returns:
        List of document paths
    """
    return sorted(root_dir.rglob(pattern))


def process_documents(
    files: List[Path],
    api_url: str,
    jwt_token: str,
    category: str,
    sleep_seconds: float,
    max_retries: int,
    state: IngestionState,
    limit: Optional[int] = None,
) -> List[IngestionResult]:
    """
    Process list of documents with rate limiting and state management.

    Args:
        files: List of file paths to process
        api_url: API endpoint URL
        jwt_token: Admin JWT token
        category: Document category
        sleep_seconds: Seconds to sleep between requests
        max_retries: Max retries for transient errors
        state: Ingestion state manager
        limit: Optional limit on number of files to process

    Returns:
        List of IngestionResult objects
    """
    results = []
    processed_count = 0

    for i, file_path in enumerate(files, 1):
        # Check limit
        if limit and processed_count >= limit:
            logger.info(f"Reached limit of {limit} files. Stopping.")
            break

        # Check if already processed - resolve to absolute path first
        absolute_path = file_path.resolve()
        try:
            relative_path = str(absolute_path.relative_to(project_root))
        except ValueError:
            # If path is outside project root, use the file name with parent directory
            relative_path = str(Path(file_path.parent.name) / file_path.name)
        if state.is_processed(relative_path):
            logger.info(f"[{i}/{len(files)}] Skipping {file_path.name} (already processed)")
            results.append(
                IngestionResult(
                    file_path=relative_path,
                    status="skipped",
                    error="Already processed in previous run",
                )
            )
            continue

        logger.info(f"[{i}/{len(files)}] Processing: {file_path.name}")

        start_time = time.time()
        result = None

        try:
            # Extract text
            document_text = extract_text_from_file(file_path)
            logger.info(f"  Extracted {len(document_text)} characters")

            # Prepare payload
            payload = prepare_payload(file_path, document_text, category)

            # Call API
            response_data = ingest_document(api_url, jwt_token, payload, max_retries)

            latency_ms = (time.time() - start_time) * 1000

            job_id = response_data.get("job_id")
            inserted = response_data.get("inserted")
            document_id = response_data.get("document_id")

            if job_id and (inserted is None or inserted == 0):
                logger.info(f"  Waiting for job completion (job_id={job_id})")
                status_payload = wait_for_job_completion(api_url, jwt_token, job_id)
                inserted = status_payload.get("inserted")
                document_id = document_id or status_payload.get("document_id")
                logger.info(
                    json.dumps(
                        {
                            "event": "ingestion_job_completed",
                            "file": file_path.name,
                            "job_id": job_id,
                            "inserted": inserted,
                            "status": status_payload.get("status"),
                        }
                    )
                )

            inserted = inserted or 0
            if inserted <= 0:
                raise RuntimeError(f"Ingestion completed without inserting chunks (job_id={job_id})")

            result = IngestionResult(
                file_path=relative_path,
                status="success",
                job_id=job_id,
                inserted_chunks=inserted,
                latency_ms=latency_ms,
            )

            logger.info(
                json.dumps(
                    {
                        "event": "ingestion_success",
                        "file": file_path.name,
                        "job_id": job_id,
                        "document_id": document_id,
                        "inserted": inserted,
                        "latency_ms": f"{latency_ms:.0f}",
                    }
                )
            )

            # Mark as processed
            state.mark_processed(relative_path)
            processed_count += 1

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            error_msg = str(e)

            result = IngestionResult(
                file_path=relative_path,
                status="failed",
                latency_ms=latency_ms,
                error=error_msg,
            )

            logger.error(
                json.dumps(
                    {
                        "event": "ingestion_failed",
                        "file": file_path.name,
                        "error": error_msg,
                        "latency_ms": f"{latency_ms:.0f}",
                    }
                )
            )

        results.append(result)

        # Rate limiting: sleep between requests (except for last file)
        if i < len(files) and (not limit or processed_count < limit):
            jitter = random.uniform(0, 1)
            sleep_time = sleep_seconds + jitter
            logger.info(f"  Sleeping {sleep_time:.1f}s (rate limit)")
            time.sleep(sleep_time)

    return results


def generate_reports(
    results: List[IngestionResult],
    report_path: Path,
    start_time: datetime,
    end_time: datetime,
):
    """
    Generate markdown, JSON, and CSV reports.

    Args:
        results: List of ingestion results
        report_path: Base path for reports (without extension)
        start_time: Batch start time
        end_time: Batch end time
    """
    # Ensure reports directory exists
    report_path.parent.mkdir(parents=True, exist_ok=True)

    # Calculate statistics
    total = len(results)
    success = sum(1 for r in results if r.status == "success")
    failed = sum(1 for r in results if r.status == "failed")
    skipped = sum(1 for r in results if r.status == "skipped")

    total_chunks = sum(r.inserted_chunks or 0 for r in results)
    duration_seconds = (end_time - start_time).total_seconds()

    # Top files by chunks
    top_files = sorted(
        [r for r in results if r.inserted_chunks],
        key=lambda x: x.inserted_chunks or 0,
        reverse=True,
    )[:10]

    # Generate Markdown report
    md_path = report_path.with_suffix(".md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Batch Ingestion Report\n\n")
        f.write(f"**Generated:** {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")
        f.write("## Summary\n\n")
        f.write(f"- **Total Files:** {total}\n")
        f.write(f"- **Success:** {success}\n")
        f.write(f"- **Failed:** {failed}\n")
        f.write(f"- **Skipped:** {skipped}\n")
        f.write(f"- **Total Chunks:** {total_chunks}\n")
        f.write(f"- **Duration:** {duration_seconds:.1f}s\n")
        f.write(
            f"- **Throughput:** {success / duration_seconds * 60:.1f} files/min\n\n"
        )

        f.write("## Top Files by Chunks\n\n")
        f.write("| File | Chunks | Latency (ms) |\n")
        f.write("|------|--------|-------------|\n")
        for r in top_files:
            f.write(
                f"| {Path(r.file_path).name} | {r.inserted_chunks} | {r.latency_ms:.0f} |\n"
            )
        f.write("\n")

        if failed > 0:
            f.write("## Failed Files\n\n")
            f.write("| File | Error |\n")
            f.write("|------|-------|\n")
            for r in results:
                if r.status == "failed":
                    f.write(f"| {Path(r.file_path).name} | {r.error} |\n")
            f.write("\n")

    # Generate JSON report
    json_path = report_path.with_suffix(".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "summary": {
                    "total": total,
                    "success": success,
                    "failed": failed,
                    "skipped": skipped,
                    "total_chunks": total_chunks,
                    "duration_seconds": duration_seconds,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                },
                "results": [asdict(r) for r in results],
            },
            f,
            indent=2,
        )

    # Generate CSV report
    csv_path = report_path.with_suffix(".csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("file_path,status,job_id,inserted_chunks,latency_ms,error,timestamp\n")
        for r in results:
            f.write(
                f'"{r.file_path}",{r.status},{r.job_id or ""},{r.inserted_chunks or ""},'
                f'{r.latency_ms or ""},"{r.error or ""}",{r.timestamp}\n'
            )

    logger.info(f"Reports generated:")
    logger.info(f"  - {md_path}")
    logger.info(f"  - {json_path}")
    logger.info(f"  - {csv_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Batch ingest documents into FisioRAG knowledge base",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--root-dir",
        type=Path,
        default=Path("conoscenza/fisioterapia/"),
        help="Root directory to scan recursively",
    )
    parser.add_argument(
        "--pattern",
        default="*.docx",
        help="Glob pattern for file selection",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=6.0,
        help="Minimum delay between requests (rate limiting)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=5,
        help="Maximum retries for transient errors",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of files to process (for testing)",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/batch_ingestion_report.md"),
        help="Path for report output (without extension)",
    )
    parser.add_argument(
        "--state-file",
        type=Path,
        default=Path("temp/ingestion_state.json"),
        help="State file for resume capability",
    )
    parser.add_argument(
        "--api-url",
        help="API endpoint URL (defaults to API_BASE_URL + sync-jobs path)",
    )
    parser.add_argument(
        "--category",
        default="fisioterapia",
        help="Document category",
    )

    args = parser.parse_args()

    # Preflight check - blocking
    if not preflight_check():
        logger.error("Preflight check failed. Exiting.")
        return 1

    # Construct API URL
    if args.api_url:
        api_url = args.api_url
    else:
        api_base = os.getenv("API_BASE_URL", "http://localhost")
        api_url = f"{api_base}/api/v1/admin/knowledge-base/sync-jobs"

    logger.info("=" * 80)
    logger.info("BATCH INGESTION STARTED")
    logger.info("=" * 80)
    logger.info(f"Root directory: {args.root_dir}")
    logger.info(f"Pattern: {args.pattern}")
    logger.info(f"API URL: {api_url}")
    logger.info(f"Rate limit: {args.sleep_seconds}s + jitter")
    logger.info(f"Max retries: {args.max_retries}")
    logger.info(f"Limit: {args.limit or 'None'}")
    logger.info("=" * 80)

    start_time = datetime.now(timezone.utc)

    try:
        # Find documents
        logger.info(f"Scanning {args.root_dir} for {args.pattern}...")
        files = find_documents(args.root_dir, args.pattern)
        logger.info(f"Found {len(files)} files matching pattern")

        if not files:
            logger.warning("No files found. Exiting.")
            return 0

        # Generate JWT
        logger.info("Generating admin JWT...")
        jwt_token = generate_admin_jwt(
            os.getenv("ADMIN_EMAIL", "admin@fisiorag.local"), expires_days=1
        )
        logger.info("JWT generated successfully")

        # Initialize state
        state = IngestionState(args.state_file)

        # Process documents
        logger.info("Starting document processing...")
        results = process_documents(
            files,
            api_url,
            jwt_token,
            args.category,
            args.sleep_seconds,
            args.max_retries,
            state,
            args.limit,
        )

        end_time = datetime.now(timezone.utc)

        # Generate reports
        logger.info("Generating reports...")
        # Remove .md extension if present
        report_base = args.report.with_suffix("")
        generate_reports(results, report_base, start_time, end_time)

        # Summary
        success = sum(1 for r in results if r.status == "success")
        failed = sum(1 for r in results if r.status == "failed")

        logger.info("=" * 80)
        logger.info("BATCH INGESTION COMPLETED")
        logger.info("=" * 80)
        logger.info(f"Total: {len(results)}")
        logger.info(f"Success: {success}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Duration: {(end_time - start_time).total_seconds():.1f}s")
        logger.info("=" * 80)

        return 0 if failed == 0 else 1

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
