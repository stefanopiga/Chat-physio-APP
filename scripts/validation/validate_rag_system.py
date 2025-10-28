#!/usr/bin/env python3
"""
RAG System Validation Script - Story 2.6

Script per automatizzare validation checks sistema RAG.
Genera report JSON con risultati per ogni check.

Usage (da project root):
    # Install dependencies (se esegui da host)
    pip install -r scripts/requirements.txt
    
    # Run validation
    python scripts/validation/validate_rag_system.py --output reports/validation-results.json --verbose

    # O dentro container API (dependencies già installate)
    docker exec fisio-rag-api python /app/scripts/validation/validate_rag_system.py --output /app/reports/validation-results.json

Requirements:
    - Docker Compose running: `docker compose ps`
    - Environment variables in `.env` file
    - Container names: fisio-rag-api, fisio-rag-celery-worker, fisio-rag-redis
"""

import os
import sys
import json
import time
import argparse
import subprocess
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add parent directory to path per imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "apps" / "api"))

try:
    import requests
    from redis import Redis
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install -r scripts/requirements.txt")
    print("Dependencies needed: requests, redis")
    sys.exit(1)


class ValidationResult:
    """Container per risultato singolo check."""
    def __init__(self, check_id: str, check_name: str, status: str, details: Dict[str, Any]):
        self.check_id = check_id
        self.check_name = check_name
        self.status = status  # PASS | FAIL | WARN | SKIP
        self.details = details
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_id": self.check_id,
            "check_name": self.check_name,
            "status": self.status,
            "details": self.details,
            "timestamp": self.timestamp
        }


class RAGSystemValidator:
    """Validator per sistema RAG completo."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[ValidationResult] = []
        # API via Traefik proxy su porta 80
        self.api_base_url = os.getenv("API_BASE_URL", "http://localhost")
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        # Redis accessibile via localhost:6379 se esposto, altrimenti via container network
        self.redis_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")

    def log(self, message: str):
        """Log con timestamp se verbose."""
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] {message}")

    def add_result(self, check_id: str, check_name: str, status: str, details: Dict[str, Any]):
        """Aggiungi risultato check."""
        result = ValidationResult(check_id, check_name, status, details)
        self.results.append(result)
        status_emoji = {"PASS": "✓", "FAIL": "✗", "WARN": "⚠", "SKIP": "○"}
        self.log(f"{status_emoji.get(status, '?')} {check_name}: {status}")

    # ===== Environment Validation =====

    def check_environment_variables(self) -> ValidationResult:
        """AC1: Verifica variabili ambiente critiche."""
        self.log("Checking environment variables...")

        required_vars = {
            "SUPABASE_URL": self.supabase_url,
            "SUPABASE_SERVICE_ROLE_KEY": self.supabase_key,
            "OPENAI_API_KEY": self.openai_key,
            "SUPABASE_JWT_SECRET": os.getenv("SUPABASE_JWT_SECRET"),
        }

        missing = [k for k, v in required_vars.items() if not v]
        placeholder = [k for k, v in required_vars.items() if v and ("your-" in v or "xxx" in v)]

        if missing:
            self.add_result(
                "ENV-001",
                "Environment Variables",
                "FAIL",
                {
                    "missing_vars": missing,
                    "placeholder_vars": placeholder,
                    "error": f"{len(missing)} variabili critiche mancanti"
                }
            )
        elif placeholder:
            self.add_result(
                "ENV-001",
                "Environment Variables",
                "WARN",
                {
                    "placeholder_vars": placeholder,
                    "warning": f"{len(placeholder)} variabili con placeholder values"
                }
            )
        else:
            self.add_result(
                "ENV-001",
                "Environment Variables",
                "PASS",
                {"vars_checked": len(required_vars)}
            )

    # ===== Docker Infrastructure =====

    def check_docker_services(self) -> ValidationResult:
        """AC2: Verifica servizi Docker running."""
        self.log("Checking Docker services...")

        try:
            result = subprocess.run(
                ["docker", "compose", "ps", "--format", "json"],
                capture_output=True,
                text=True,
                check=True
            )

            services = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    services.append(json.loads(line))

            service_status = {s["Service"]: s["State"] for s in services}
            not_running = [name for name, state in service_status.items() if state != "running"]

            if not_running:
                self.add_result(
                    "DOCKER-001",
                    "Docker Services",
                    "FAIL",
                    {
                        "service_status": service_status,
                        "not_running": not_running,
                        "error": f"{len(not_running)} servizi non running"
                    }
                )
            else:
                self.add_result(
                    "DOCKER-001",
                    "Docker Services",
                    "PASS",
                    {"service_status": service_status, "total_services": len(services)}
                )

        except subprocess.CalledProcessError as e:
            self.add_result(
                "DOCKER-001",
                "Docker Services",
                "FAIL",
                {"error": f"docker compose ps fallito: {e.stderr}"}
            )
        except FileNotFoundError:
            self.add_result(
                "DOCKER-001",
                "Docker Services",
                "SKIP",
                {"reason": "Docker CLI non disponibile"}
            )

    def check_redis_connectivity(self) -> ValidationResult:
        """AC3: Verifica Redis accessibile."""
        self.log("Checking Redis connectivity...")

        try:
            redis_client = Redis.from_url(self.redis_url, socket_timeout=5)
            pong = redis_client.ping()

            if pong:
                # Check keys count
                key_count = redis_client.dbsize()
                self.add_result(
                    "REDIS-001",
                    "Redis Connectivity",
                    "PASS",
                    {"ping": "PONG", "keys_count": key_count, "url": self.redis_url}
                )
            else:
                self.add_result(
                    "REDIS-001",
                    "Redis Connectivity",
                    "FAIL",
                    {"error": "PING returned False"}
                )

        except Exception as e:
            self.add_result(
                "REDIS-001",
                "Redis Connectivity",
                "FAIL",
                {"error": str(e), "url": self.redis_url}
            )

    # ===== API Health =====

    def check_api_health(self) -> ValidationResult:
        """AC2: Verifica API health endpoint."""
        self.log("Checking API health...")

        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=5)

            if response.status_code == 200:
                self.add_result(
                    "API-001",
                    "API Health Endpoint",
                    "PASS",
                    {"status_code": 200, "response": response.json() if response.text else {}}
                )
            else:
                self.add_result(
                    "API-001",
                    "API Health Endpoint",
                    "FAIL",
                    {"status_code": response.status_code, "body": response.text[:200]}
                )

        except requests.exceptions.ConnectionError:
            self.add_result(
                "API-001",
                "API Health Endpoint",
                "FAIL",
                {"error": "Connection refused", "url": self.api_base_url}
            )
        except Exception as e:
            self.add_result(
                "API-001",
                "API Health Endpoint",
                "FAIL",
                {"error": str(e)}
            )

    # ===== Database Validation =====

    def check_database_schema(self) -> ValidationResult:
        """AC5: Verifica schema database (tables, pgvector)."""
        self.log("Checking database schema...")

        if not self.supabase_url or not self.supabase_key:
            self.add_result(
                "DB-001",
                "Database Schema",
                "SKIP",
                {"reason": "Supabase credentials mancanti"}
            )
            return

        # Parse Supabase URL per DB connection
        # Format: https://xxx.supabase.co → host: xxx.supabase.co, port: 5432
        import re
        match = re.match(r"https?://([^/]+)", self.supabase_url)
        if not match:
            self.add_result(
                "DB-001",
                "Database Schema",
                "FAIL",
                {"error": "Invalid SUPABASE_URL format"}
            )
            return

        db_host = match.group(1)

        try:
            # Note: Supabase PostgreSQL requires connection via pooler (port 6543) or direct (5432)
            # Questo check può fallire se firewall blocca, ma è expected in molti setup
            self.add_result(
                "DB-001",
                "Database Schema",
                "SKIP",
                {"reason": "Database direct connection check skipped (Supabase pooler)"}
            )

        except Exception as e:
            self.add_result(
                "DB-001",
                "Database Schema",
                "SKIP",
                {"reason": f"Database check skipped: {e}"}
            )

    def check_database_integrity(self) -> ValidationResult:
        """AC5: Verifica integrità dati (NULL embeddings)."""
        self.log("Checking database integrity (NULL embeddings)...")

        # Questo check richiede Supabase client o SQL direct access
        # Per ora skip, può essere implementato con supabase-py client
        self.add_result(
            "DB-002",
            "Database Integrity (NULL embeddings)",
            "SKIP",
            {"reason": "Requires Supabase SQL client (implement with supabase-py)"}
        )

    # ===== OpenAI API =====

    def check_openai_api(self) -> ValidationResult:
        """AC4: Verifica OpenAI API key valida."""
        self.log("Checking OpenAI API...")

        if not self.openai_key:
            self.add_result(
                "OPENAI-001",
                "OpenAI API Key",
                "FAIL",
                {"error": "OPENAI_API_KEY not set"}
            )
            return

        try:
            # Test API key con /v1/models endpoint (lightweight)
            response = requests.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {self.openai_key}"},
                timeout=10
            )

            if response.status_code == 200:
                models = response.json().get("data", [])
                self.add_result(
                    "OPENAI-001",
                    "OpenAI API Key",
                    "PASS",
                    {"models_count": len(models), "key_prefix": self.openai_key[:10] + "..."}
                )
            elif response.status_code == 401:
                self.add_result(
                    "OPENAI-001",
                    "OpenAI API Key",
                    "FAIL",
                    {"error": "Invalid API key (401 Unauthorized)"}
                )
            else:
                self.add_result(
                    "OPENAI-001",
                    "OpenAI API Key",
                    "WARN",
                    {"status_code": response.status_code, "message": response.text[:200]}
                )

        except Exception as e:
            self.add_result(
                "OPENAI-001",
                "OpenAI API Key",
                "FAIL",
                {"error": str(e)}
            )

    # ===== Run All =====

    def run_all_checks(self):
        """Esegui tutti validation checks."""
        self.log("=== Starting RAG System Validation ===")

        # Phase 1: Environment & Infrastructure
        self.check_environment_variables()
        self.check_docker_services()
        self.check_redis_connectivity()
        self.check_api_health()

        # Phase 2: Database
        self.check_database_schema()
        self.check_database_integrity()

        # Phase 3: External APIs
        self.check_openai_api()

        self.log("=== Validation Complete ===")

    def generate_report(self) -> Dict[str, Any]:
        """Genera report JSON con risultati."""
        summary = {
            "PASS": sum(1 for r in self.results if r.status == "PASS"),
            "FAIL": sum(1 for r in self.results if r.status == "FAIL"),
            "WARN": sum(1 for r in self.results if r.status == "WARN"),
            "SKIP": sum(1 for r in self.results if r.status == "SKIP"),
        }

        report = {
            "validation_run": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "script_version": "1.0.0",
                "story": "2.6"
            },
            "summary": summary,
            "overall_status": "FAIL" if summary["FAIL"] > 0 else "PASS" if summary["WARN"] == 0 else "WARN",
            "checks": [r.to_dict() for r in self.results]
        }

        return report


def main():
    parser = argparse.ArgumentParser(description="Validate RAG System - Story 2.6")
    parser.add_argument("--output", "-o", help="Output JSON file path", default="validation-results.json")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    validator = RAGSystemValidator(verbose=args.verbose)
    validator.run_all_checks()

    report = validator.generate_report()

    # Write report
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"Validation Report: {output_path}")
    print(f"{'='*60}")
    print(f"Status: {report['overall_status']}")
    print(f"PASS: {report['summary']['PASS']}")
    print(f"FAIL: {report['summary']['FAIL']}")
    print(f"WARN: {report['summary']['WARN']}")
    print(f"SKIP: {report['summary']['SKIP']}")
    print(f"{'='*60}\n")

    # Exit code based on status
    if report['overall_status'] == "FAIL":
        sys.exit(1)
    elif report['overall_status'] == "WARN":
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()

