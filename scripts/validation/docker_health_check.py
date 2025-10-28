"""
Docker Infrastructure Health Check Script
Story 2.6 - Task 2: Docker Infrastructure Validation

Valida stato Docker services, network, volumes, logs.

Usage:
    python scripts/validation/docker_health_check.py
"""
import subprocess
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List


class DockerHealthChecker:
    """Health checker per infrastruttura Docker."""
    
    def __init__(self):
        self.services = ["api", "celery-worker", "redis"]
        self.compose_prefix = "fisio-rag"  # Docker Compose project name
        
    def run_command(self, cmd: List[str]) -> tuple[int, str]:
        """Esegue comando e ritorna (exit_code, output)."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return -1, "Timeout expired"
        except Exception as e:
            return -1, str(e)
    
    def check_compose_status(self) -> Dict:
        """Verifica stato docker compose services."""
        print("Checking Docker Compose services status...")
        exit_code, output = self.run_command(["docker", "compose", "ps", "--format", "json"])
        
        services_status = []
        if exit_code == 0 and output.strip():
            # Parse JSON output
            for line in output.strip().split('\n'):
                try:
                    service_data = json.loads(line)
                    services_status.append({
                        "name": service_data.get("Service"),
                        "state": service_data.get("State"),
                        "status": service_data.get("Status"),
                        "health": service_data.get("Health", "N/A")
                    })
                except json.JSONDecodeError:
                    pass
        
        return {
            "command": "docker compose ps",
            "exit_code": exit_code,
            "services": services_status,
            "status": "OK" if exit_code == 0 else "FAIL"
        }
    
    def check_api_health(self) -> Dict:
        """Verifica API health endpoint."""
        print("Checking API health endpoint...")
        exit_code, output = self.run_command(["curl", "-s", "http://localhost/health"])
        
        is_healthy = exit_code == 0 and "ok" in output.lower()
        
        return {
            "service": "api",
            "endpoint": "http://localhost/health",
            "exit_code": exit_code,
            "response": output[:200],
            "status": "OK" if is_healthy else "FAIL"
        }
    
    def check_redis(self) -> Dict:
        """Verifica Redis connectivity."""
        print("Checking Redis connectivity...")
        exit_code, output = self.run_command([
            "docker", "exec", f"{self.compose_prefix}-redis", "redis-cli", "PING"
        ])
        
        is_healthy = exit_code == 0 and "PONG" in output
        
        return {
            "service": "redis",
            "command": "redis-cli PING",
            "exit_code": exit_code,
            "response": output.strip(),
            "status": "OK" if is_healthy else "FAIL"
        }
    
    def check_celery_worker(self) -> Dict:
        """Verifica Celery worker logs per 'ready' message."""
        print("Checking Celery worker logs...")
        exit_code, output = self.run_command([
            "docker", "logs", f"{self.compose_prefix}-celery-worker", "--tail", "50"
        ])
        
        is_ready = "ready" in output.lower()
        
        return {
            "service": "celery-worker",
            "command": "docker logs",
            "exit_code": exit_code,
            "ready": is_ready,
            "last_50_lines_sample": output[:500],
            "status": "OK" if is_ready else "WARN"
        }
    
    def check_network(self) -> Dict:
        """Verifica Docker network."""
        print("Checking Docker network...")
        # Try multiple possible network names
        for network_name in [
            f"{self.compose_prefix}_default",
            "fisio-rag-net",
            "fisio-rag-master_default",
            "applicazione_fisio-rag-net",  # observed compose project prefix on this repo
        ]:
            exit_code, output = self.run_command([
                "docker", "network", "inspect", network_name
            ])
            if exit_code == 0:
                break
        
        network_info = {}
        if exit_code == 0:
            try:
                network_data = json.loads(output)
                if network_data:
                    network_info = {
                        "name": network_data[0].get("Name"),
                        "driver": network_data[0].get("Driver"),
                        "containers_count": len(network_data[0].get("Containers", {}))
                    }
            except json.JSONDecodeError:
                pass
        
        return {
            "command": "docker network inspect",
            "exit_code": exit_code,
            "network_info": network_info,
            "status": "OK" if exit_code == 0 else "FAIL"
        }
    
    def check_volumes(self) -> Dict:
        """Verifica Docker volumes."""
        print("Checking Docker volumes...")
        # Specifically validate the named Redis volume required by Story 2.6.1
        # Try both project-prefixed and plain names
        candidates = ["applicazione_redis_data", "redis_data", f"{self.compose_prefix}_redis_data"]
        inspect_code = 1
        for name in candidates:
            code, _ = self.run_command(["docker", "volume", "inspect", name])
            if code == 0:
                inspect_code = 0
                break
        status = "OK" if inspect_code == 0 else "FAIL"
        return {
            "command": "docker volume inspect redis_data",
            "exit_code": inspect_code,
            "volumes_found": 1 if inspect_code == 0 else 0,
            "status": status,
        }
    
    def generate_report(self) -> Dict:
        """Genera report completo health check."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "story": "2.6",
            "task": "Task 2 - Docker Infrastructure Validation",
            "checks": {}
        }
        
        # Run all checks
        report["checks"]["compose_status"] = self.check_compose_status()
        report["checks"]["api_health"] = self.check_api_health()
        report["checks"]["redis"] = self.check_redis()
        report["checks"]["celery_worker"] = self.check_celery_worker()
        report["checks"]["network"] = self.check_network()
        report["checks"]["volumes"] = self.check_volumes()
        
        # Overall status
        all_checks = [
            report["checks"]["compose_status"]["status"],
            report["checks"]["api_health"]["status"],
            report["checks"]["redis"]["status"],
            report["checks"]["network"]["status"],
            report["checks"]["volumes"]["status"]
        ]
        
        report["overall_status"] = "PASS" if all(s == "OK" for s in all_checks) else "FAIL"
        
        return report
    
    def generate_markdown_report(self, report: Dict) -> str:
        """Genera report Markdown."""
        lines = [
            "# Docker Infrastructure Health Report",
            "",
            f"**Timestamp:** {report['timestamp']}",
            f"**Story:** {report['story']}",
            f"**Task:** {report['task']}",
            "",
            f"## Overall Status: {report['overall_status']}",
            "",
            "## Service Health Checks",
            ""
        ]
        
        # Docker Compose Status
        compose = report["checks"]["compose_status"]
        lines.extend([
            "### Docker Compose Services",
            f"**Status:** {compose['status']}",
            ""
        ])
        
        if compose["services"]:
            lines.append("| Service | State | Status | Health |")
            lines.append("|---------|-------|--------|--------|")
            for svc in compose["services"]:
                lines.append(f"| {svc['name']} | {svc['state']} | {svc['status']} | {svc['health']} |")
            lines.append("")
        else:
            lines.extend([
                "[ERROR] No services found. Docker Compose not running?",
                ""
            ])
        
        # API Health
        api = report["checks"]["api_health"]
        lines.extend([
            "### API Health Endpoint",
            f"**Status:** {api['status']}",
            f"**Endpoint:** {api['endpoint']}",
            f"**Response:** `{api['response']}`",
            ""
        ])
        
        # Redis
        redis = report["checks"]["redis"]
        lines.extend([
            "### Redis Connectivity",
            f"**Status:** {redis['status']}",
            f"**Command:** {redis['command']}",
            f"**Response:** `{redis['response']}`",
            ""
        ])
        
        # Celery Worker
        celery = report["checks"]["celery_worker"]
        lines.extend([
            "### Celery Worker",
            f"**Status:** {celery['status']}",
            f"**Ready:** {celery['ready']}",
            "**Log Sample:**",
            "```",
            celery['last_50_lines_sample'],
            "```",
            ""
        ])
        
        # Network
        network = report["checks"]["network"]
        lines.extend([
            "### Docker Network",
            f"**Status:** {network['status']}",
        ])
        if network.get("network_info"):
            info = network["network_info"]
            lines.extend([
                f"**Name:** {info.get('name')}",
                f"**Driver:** {info.get('driver')}",
                f"**Containers:** {info.get('containers_count')}",
            ])
        lines.append("")
        
        # Volumes
        volumes = report["checks"]["volumes"]
        lines.extend([
            "### Docker Volumes",
            f"**Status:** {volumes['status']}",
            f"**Volumes Found:** {volumes['volumes_found']}",
            ""
        ])
        
        # Recommendations
        lines.extend([
            "## Recommendations",
            ""
        ])
        
        if report["overall_status"] == "PASS":
            lines.extend([
                "[OK] All infrastructure checks passed.",
                "- Services are running and healthy",
                "- Network connectivity verified",
                "- Ready for production deployment validation",
                ""
            ])
        else:
            lines.extend([
                "[WARNING] Some infrastructure checks failed.",
                "**Actions Required:**",
                "1. Check failed services and restart if needed",
                "2. Verify Docker Compose configuration",
                "3. Check container logs for errors",
                "4. Ensure all required ports are available",
                ""
            ])
        
        return "\n".join(lines)


def main():
    """Entry point."""
    project_root = Path(__file__).parent.parent.parent
    
    print("Starting Docker Infrastructure Health Check...")
    print()
    
    checker = DockerHealthChecker()
    
    # Generate report
    report = checker.generate_report()
    
    # Save JSON report
    json_output = project_root / "temp" / "docker_health_report.json"
    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(report, indent=2))
    print(f"[OK] JSON report saved: {json_output}")
    
    # Generate Markdown report
    markdown_report = checker.generate_markdown_report(report)
    md_output = project_root / "docs" / "reports" / "rag-infrastructure-health.md"
    md_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.write_text(markdown_report, encoding="utf-8")
    print(f"[OK] Markdown report saved: {md_output}")
    
    # Print summary
    print()
    print(f"Overall Status: {report['overall_status']}")
    print()
    print("Full report: docs/reports/rag-infrastructure-health.md")


if __name__ == "__main__":
    main()

