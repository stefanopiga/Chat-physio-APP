"""
Configuration Gap Analysis Script
Story 2.6 - Task 15: Configuration Gap Analysis

Analizza docker-compose.yml, .env files, test config, e documentazione
per identificare gap di configurazione.

Usage:
    python scripts/validation/config_gap_analysis.py
"""
from pathlib import Path
import yaml
from typing import Dict, List
from datetime import datetime
import json


class ConfigGapAnalyzer:
    """Analyzer per gap configurazione multi-environment."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.docker_compose_file = project_root / "docker-compose.yml"
        
    def analyze_docker_compose(self) -> Dict:
        """Analizza docker-compose.yml."""
        print("Analyzing docker-compose.yml...")
        
        if not self.docker_compose_file.exists():
            return {
                "status": "MISSING",
                "file": str(self.docker_compose_file),
                "issues": ["docker-compose.yml not found"]
            }
        
        with open(self.docker_compose_file, 'r') as f:
            compose_data = yaml.safe_load(f)
        
        services = compose_data.get("services", {})
        networks = compose_data.get("networks", {})
        
        findings = {
            "services_count": len(services),
            "services": list(services.keys()),
            "networks": list(networks.keys()),
            "issues": [],
            "recommendations": []
        }
        
        # Check API service
        if "api" in services:
            api = services["api"]
            
            # Check env_file
            if "env_file" not in api:
                findings["issues"].append("API service: missing env_file configuration")
            
            # Check restart policy
            if "restart" not in api:
                findings["recommendations"].append("API service: add restart policy (e.g., restart: unless-stopped)")
            
            # Check healthcheck
            if "healthcheck" not in api:
                findings["recommendations"].append("API service: add healthcheck for monitoring")
        
        # Check celery-worker service
        if "celery-worker" in services:
            celery = services["celery-worker"]
            
            if "restart" not in celery:
                findings["recommendations"].append("Celery service: add restart policy")
            
            if "healthcheck" not in celery:
                findings["recommendations"].append("Celery service: add healthcheck (e.g., celery inspect ping)")
        
        # Check redis service
        if "redis" in services:
            redis = services["redis"]
            
            if "restart" not in redis:
                findings["recommendations"].append("Redis service: add restart policy")
            
            # Check persistence
            if "volumes" not in redis:
                findings["issues"].append("Redis service: no volume mounted - data loss on restart")
        
        # Network check
        if not networks:
            findings["issues"].append("No custom network defined")
        
        findings["status"] = "CONCERNS" if findings["issues"] or findings["recommendations"] else "OK"
        
        return findings
    
    def check_documentation_alignment(self) -> Dict:
        """Verifica allineamento con documentazione."""
        print("Checking documentation alignment...")
        
        docs = {
            "admin-setup-guide": self.project_root / "docs" / "admin-setup-guide.md",
            "architecture": self.project_root / "docs" / "architecture",
            "env-templates": [
                self.project_root / "ENV_TEMPLATE.txt",
                self.project_root / "apps" / "api" / "ENV_TEST_TEMPLATE.txt",
                self.project_root / "apps" / "web" / "ENV_WEB_TEMPLATE.txt"
            ]
        }
        
        findings = {
            "documentation_present": {},
            "missing_documentation": [],
            "status": "OK"
        }
        
        # Check admin setup guide
        if docs["admin-setup-guide"].exists():
            findings["documentation_present"]["admin-setup-guide"] = True
        else:
            findings["missing_documentation"].append("admin-setup-guide.md")
        
        # Check architecture docs
        if docs["architecture"].exists() and docs["architecture"].is_dir():
            arch_files = list(docs["architecture"].glob("*.md"))
            findings["documentation_present"]["architecture_files"] = len(arch_files)
        else:
            findings["missing_documentation"].append("architecture docs")
        
        # Check env templates
        templates_present = []
        for template_path in docs["env-templates"]:
            if template_path.exists():
                templates_present.append(template_path.name)
            else:
                findings["missing_documentation"].append(str(template_path.relative_to(self.project_root)))
        
        findings["documentation_present"]["env_templates"] = templates_present
        
        if findings["missing_documentation"]:
            findings["status"] = "CONCERNS"
        
        return findings
    
    def generate_report(self) -> Dict:
        """Genera report completo gap analysis."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "story": "2.6",
            "task": "Task 15 - Configuration Gap Analysis",
            "analyses": {}
        }
        
        # Run analyses
        report["analyses"]["docker_compose"] = self.analyze_docker_compose()
        report["analyses"]["documentation"] = self.check_documentation_alignment()
        
        # Overall status
        statuses = [
            report["analyses"]["docker_compose"]["status"],
            report["analyses"]["documentation"]["status"]
        ]
        
        if "MISSING" in statuses or any("CRITICAL" in s for s in statuses):
            report["overall_status"] = "FAIL"
        elif "CONCERNS" in statuses:
            report["overall_status"] = "CONCERNS"
        else:
            report["overall_status"] = "PASS"
        
        return report
    
    def generate_markdown_report(self, report: Dict) -> str:
        """Genera report Markdown."""
        lines = [
            "# Configuration Gap Analysis Report",
            "",
            f"**Timestamp:** {report['timestamp']}",
            f"**Story:** {report['story']}",
            f"**Task:** {report['task']}",
            "",
            f"## Overall Status: {report['overall_status']}",
            "",
            "## Docker Compose Analysis",
            ""
        ]
        
        dc = report["analyses"]["docker_compose"]
        lines.extend([
            f"**Status:** {dc.get('status', 'UNKNOWN')}",
            f"**Services:** {dc.get('services_count', 0)} ({', '.join(dc.get('services', []))})",
            f"**Networks:** {', '.join(dc.get('networks', []))}",
            ""
        ])
        
        if dc.get("issues"):
            lines.extend([
                "### Issues",
                ""
            ])
            for issue in dc["issues"]:
                lines.append(f"- [ISSUE] {issue}")
            lines.append("")
        
        if dc.get("recommendations"):
            lines.extend([
                "### Recommendations",
                ""
            ])
            for rec in dc["recommendations"]:
                lines.append(f"- [REC] {rec}")
            lines.append("")
        
        if not dc.get("issues") and not dc.get("recommendations"):
            lines.extend([
                "[OK] Docker Compose configuration validated.",
                ""
            ])
        
        # Documentation
        docs = report["analyses"]["documentation"]
        lines.extend([
            "## Documentation Alignment",
            f"**Status:** {docs['status']}",
            ""
        ])
        
        if docs.get("documentation_present"):
            lines.extend([
                "### Present",
                ""
            ])
            for doc_name, value in docs["documentation_present"].items():
                if isinstance(value, bool):
                    lines.append(f"- [OK] {doc_name}")
                elif isinstance(value, int):
                    lines.append(f"- [OK] {doc_name}: {value} files")
                elif isinstance(value, list):
                    lines.append(f"- [OK] {doc_name}: {', '.join(value)}")
            lines.append("")
        
        if docs.get("missing_documentation"):
            lines.extend([
                "### Missing",
                ""
            ])
            for missing in docs["missing_documentation"]:
                lines.append(f"- [MISSING] {missing}")
            lines.append("")
        
        # Production Readiness Summary
        lines.extend([
            "## Production Readiness Summary",
            ""
        ])
        
        if report["overall_status"] == "PASS":
            lines.extend([
                "[OK] Configuration validated for production deployment.",
                "- Docker Compose services configured",
                "- Documentation present",
                "- Environment templates available",
                ""
            ])
        elif report["overall_status"] == "CONCERNS":
            lines.extend([
                "[WARNING] Configuration has concerns. Review recommendations.",
                "",
                "**Pre-Deployment Actions:**",
                "1. Review and implement Docker Compose recommendations",
                "2. Add missing documentation",
                "3. Configure restart policies for production",
                "4. Setup health checks for monitoring",
                ""
            ])
        else:
            lines.extend([
                "[FAIL] Configuration has critical issues.",
                "- Cannot proceed to production without fixes",
                ""
            ])
        
        return "\n".join(lines)


def main():
    """Entry point."""
    project_root = Path(__file__).parent.parent.parent
    
    print("Starting Configuration Gap Analysis...")
    print()
    
    analyzer = ConfigGapAnalyzer(project_root)
    
    # Generate report
    report = analyzer.generate_report()
    
    # Save JSON report
    json_output = project_root / "temp" / "config_gap_report.json"
    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(report, indent=2))
    print(f"[OK] JSON report saved: {json_output}")
    
    # Generate Markdown report
    markdown_report = analyzer.generate_markdown_report(report)
    md_output = project_root / "docs" / "reports" / "rag-config-gap-analysis.md"
    md_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.write_text(markdown_report, encoding="utf-8")
    print(f"[OK] Markdown report saved: {md_output}")
    
    # Print summary
    print()
    print(f"Overall Status: {report['overall_status']}")
    print()
    
    dc = report["analyses"]["docker_compose"]
    print(f"Docker Compose: {dc['status']}")
    if dc.get("issues"):
        print(f"  Issues: {len(dc['issues'])}")
    if dc.get("recommendations"):
        print(f"  Recommendations: {len(dc['recommendations'])}")
    
    docs = report["analyses"]["documentation"]
    print(f"Documentation: {docs['status']}")
    if docs.get("missing_documentation"):
        print(f"  Missing: {len(docs['missing_documentation'])}")
    
    print()
    print("Full report: docs/reports/rag-config-gap-analysis.md")


if __name__ == "__main__":
    main()

