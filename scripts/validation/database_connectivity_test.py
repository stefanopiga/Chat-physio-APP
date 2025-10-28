"""Story 2.6.1 & 2.8.1 – Validate Supabase connectivity with optional downtime drill."""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import io
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import asyncpg
from dotenv import load_dotenv

LOG_DIVIDER = "=" * 31


def _now() -> str:
    """Return ISO timestamp for log records."""
    return dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def resolve_database_url(env_file: Optional[Path]) -> Optional[str]:
    """Read DATABASE_URL from the environment and ensure it is present."""
    if env_file:
        load_dotenv(dotenv_path=env_file, override=True)
    else:
        load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env", override=True)

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print(f"[{_now()}] [FAIL] DATABASE_URL not set in environment")
    return database_url


async def test_connection(database_url: str) -> bool:
    """Attempt to establish a connection and run a simple heartbeat query."""
    parsed = urlparse(database_url)

    print(LOG_DIVIDER)
    print(f"[{_now()}] DATABASE_URL Diagnostic")
    print(f"  Scheme     : {parsed.scheme}")
    print(f"  Username   : {parsed.username or '<missing>'}")
    print(f"  Host       : {parsed.hostname or '<missing>'}")
    print(f"  Port       : {parsed.port or '<missing>'}")
    print(f"  Database   : {parsed.path.lstrip('/') or '<missing>'}")
    if parsed.query:
        print(f"  Parameters : {parsed.query}")
    print(LOG_DIVIDER)

    try:
        conn = await asyncpg.connect(database_url, statement_cache_size=0)
        result = await conn.fetchval("SELECT 1;")
        await conn.close()
    except Exception as exc:  # noqa: BLE001
        print(f"[{_now()}] [FAIL] Connection failed: {exc}")
        return False

    if result == 1:
        print(f"[{_now()}] [OK] Database connection: SUCCESS")
        return True

    print(f"[{_now()}] [FAIL] Validation query returned unexpected result: {result}")
    return False


def write_log(out_path: Path, buffer: list[str]) -> None:
    """Persist log lines to the supplied path."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(buffer) + "\n", encoding="utf-8")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Supabase connectivity health check.")
    parser.add_argument(
        "--out",
        type=Path,
        help="Optional path to persist log output (e.g. reports/db_connectivity_test_YYYYMMDD.log).",
    )
    parser.add_argument(
        "--simulate-downtime",
        action="store_true",
        help="Skip real connection and emit a synthetic downtime event.",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Custom .env path to load before running the check (defaults to repository .env).",
    )

    args = parser.parse_args(argv)

    if args.simulate_downtime:
        lines = [
            LOG_DIVIDER,
            f"[{_now()}] [SIMULATION] Supabase downtime drill requested (--simulate-downtime).",
        ]
        database_url = resolve_database_url(args.env_file)
        if database_url:
            lines.append(f"[{_now()}] [SIMULATION] DATABASE_URL detected but connection intentionally skipped.")
        lines.extend([
            f"[{_now()}] [FAIL] Simulated Supabase outage – drill complete.",
            LOG_DIVIDER,
        ])
        if args.out:
            write_log(args.out, lines)
        else:
            print("\n".join(lines))
        return 2

    database_url = resolve_database_url(args.env_file)
    if not database_url:
        if args.out:
            write_log(args.out, [f"[{_now()}] [FAIL] DATABASE_URL not set in environment"])
        return 1

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        success = asyncio.run(test_connection(database_url))

    if args.out:
        lines = buffer.getvalue().strip().splitlines()
        if not lines:
            lines = [f"[{_now()}] [INFO] No output captured from connectivity check."]
        write_log(args.out, lines)

    else:
        # Re-print captured output to console when no log path was supplied
        print(buffer.getvalue().strip())

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
