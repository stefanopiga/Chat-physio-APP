"""
Environment Configuration Audit Script
Story 2.6 - Task 1: Environment Configuration Audit

Estrae tutte le variabili d'ambiente usate nel codebase e le confronta
con i template disponibili per identificare gap e security issues.

Usage:
    python scripts/validation/env_audit.py
"""
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass
import json


@dataclass
class EnvVariable:
    """Rappresenta una variabile d'ambiente."""
    name: str
    found_in_files: List[str]
    template_locations: List[str]
    default_value: str | None
    risk_level: str  # P0, P1, P2
    description: str


class EnvironmentAuditor:
    """Auditor per configurazione environment multi-ambiente."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.api_root = project_root / "apps" / "api"
        self.web_root = project_root / "apps" / "web"
        
        # Template file paths
        self.templates = {
            "root": project_root / "ENV_TEMPLATE.txt",
            "api_test": project_root / "apps" / "api" / "ENV_TEST_TEMPLATE.txt",
            "web": project_root / "apps" / "web" / "ENV_WEB_TEMPLATE.txt",
        }
        
        # Patterns per extraction
        self.patterns = {
            "os_getenv": re.compile(r'os\.getenv\(["\']([^"\']+)["\'](?:,\s*["\']?([^"\']*)["\']?)?\)'),
            "settings_field": re.compile(r'(\w+):\s*(?:str|int|bool)\s*=\s*Field\(default=["\']?([^"\']*)["\']?\)'),
            "env_template": re.compile(r'^([A-Z_][A-Z0-9_]*)=(.*)$', re.MULTILINE)
        }
        
    def extract_variables_from_code(self) -> Dict[str, EnvVariable]:
        """Estrae tutte le variabili d'ambiente dal codice Python."""
        variables: Dict[str, EnvVariable] = {}
        
        # Scan codebase Python
        for py_file in self.api_root.rglob("*.py"):
            if "tests" in py_file.parts or "__pycache__" in str(py_file):
                continue
                
            content = py_file.read_text(encoding="utf-8")
            relative_path = str(py_file.relative_to(self.project_root))
            
            # Extract os.getenv() calls
            for match in self.patterns["os_getenv"].finditer(content):
                var_name = match.group(1)
                default_val = match.group(2) if match.group(2) else None
                
                if var_name not in variables:
                    variables[var_name] = EnvVariable(
                        name=var_name,
                        found_in_files=[relative_path],
                        template_locations=[],
                        default_value=default_val,
                        risk_level="P2",
                        description=""
                    )
                else:
                    if relative_path not in variables[var_name].found_in_files:
                        variables[var_name].found_in_files.append(relative_path)
        
        return variables
    
    def load_template_variables(self) -> Dict[str, List[str]]:
        """Carica variabili da tutti i template."""
        template_vars: Dict[str, List[str]] = {}
        
        for template_name, template_path in self.templates.items():
            if not template_path.exists():
                continue
                
            content = template_path.read_text(encoding="utf-8")
            vars_in_template = []
            
            for match in self.patterns["env_template"].finditer(content):
                var_name = match.group(1)
                if not var_name.startswith("#"):
                    vars_in_template.append(var_name)
                    
            template_vars[template_name] = vars_in_template
        
        return template_vars
    
    def assess_risk_level(self, var: EnvVariable) -> str:
        """Valuta risk level della variabile."""
        # P0: Secret critici
        if any(keyword in var.name.upper() for keyword in ["SECRET", "KEY", "PASSWORD", "TOKEN"]):
            if "JWT" in var.name or "SERVICE_ROLE" in var.name or "OPENAI" in var.name:
                return "P0"
            return "P1"
        
        # P1: Config production-critical
        if any(keyword in var.name.upper() for keyword in ["DATABASE_URL", "SUPABASE_URL", "CELERY"]):
            return "P1"
        
        # P2: Config non-critical
        return "P2"
    
    def generate_audit_report(self) -> Dict:
        """Genera report completo audit environment."""
        # Extract variables
        code_vars = self.extract_variables_from_code()
        template_vars = self.load_template_variables()
        
        # Assess risk levels
        for var in code_vars.values():
            var.risk_level = self.assess_risk_level(var)
            
            # Check template presence
            for template_name, vars_list in template_vars.items():
                if var.name in vars_list:
                    var.template_locations.append(template_name)
        
        # Categorize variables
        report = {
            "timestamp": "2025-10-10",
            "summary": {
                "total_variables": len(code_vars),
                "p0_critical": sum(1 for v in code_vars.values() if v.risk_level == "P0"),
                "p1_high": sum(1 for v in code_vars.values() if v.risk_level == "P1"),
                "p2_medium": sum(1 for v in code_vars.values() if v.risk_level == "P2"),
                "missing_in_templates": sum(1 for v in code_vars.values() if not v.template_locations),
            },
            "variables": {},
            "gaps": [],
            "security_findings": []
        }
        
        # Add variables to report
        for var_name, var in sorted(code_vars.items(), key=lambda x: (x[1].risk_level, x[0])):
            report["variables"][var_name] = {
                "risk_level": var.risk_level,
                "found_in_files": var.found_in_files,
                "template_locations": var.template_locations,
                "default_value": var.default_value,
                "status": "OK" if var.template_locations else "MISSING_TEMPLATE"
            }
            
            # Identify gaps
            if not var.template_locations and var.risk_level in ["P0", "P1"]:
                report["gaps"].append({
                    "variable": var_name,
                    "risk": var.risk_level,
                    "issue": "Missing from all templates",
                    "files": var.found_in_files
                })
        
        # Security findings
        for var_name, var in code_vars.items():
            if "SECRET" in var_name or "KEY" in var_name:
                if var.default_value and var.default_value not in ["", "None", None]:
                    report["security_findings"].append({
                        "variable": var_name,
                        "severity": "HIGH",
                        "issue": f"Hardcoded default value in code: {var.default_value[:20]}...",
                        "recommendation": "Remove default value, require explicit config"
                    })
        
        return report
    
    def generate_markdown_report(self, report: Dict) -> str:
        """Genera report Markdown per documentazione."""
        lines = [
            "# Environment Configuration Audit Report",
            "",
            f"**Date:** {report['timestamp']}",
            "**Story:** 2.6 - RAG System Production Readiness Validation",
            "**Task:** Task 1 - Environment Configuration Audit",
            "",
            "## Executive Summary",
            "",
            f"- **Total Variables:** {report['summary']['total_variables']}",
            f"- **P0 Critical:** {report['summary']['p0_critical']}",
            f"- **P1 High:** {report['summary']['p1_high']}",
            f"- **P2 Medium:** {report['summary']['p2_medium']}",
            f"- **Missing in Templates:** {report['summary']['missing_in_templates']}",
            "",
            "## Variables Inventory",
            "",
            "| Variable | Risk Level | Template Locations | Status | Found In Files |",
            "|----------|------------|-------------------|--------|----------------|"
        ]
        
        for var_name, var_info in report["variables"].items():
            templates = ", ".join(var_info["template_locations"]) if var_info["template_locations"] else "NONE"
            files = ", ".join([f.split('/')[-1] for f in var_info["found_in_files"][:2]])
            if len(var_info["found_in_files"]) > 2:
                files += f" (+{len(var_info['found_in_files'])-2} more)"
            
            lines.append(
                f"| `{var_name}` | {var_info['risk_level']} | {templates} | {var_info['status']} | {files} |"
            )
        
        lines.extend([
            "",
            "## Gap Analysis",
            ""
        ])
        
        if report["gaps"]:
            lines.append("### Critical Gaps (P0/P1 Missing from Templates)")
            lines.append("")
            for gap in report["gaps"]:
                lines.extend([
                    f"#### `{gap['variable']}` ({gap['risk']})",
                    f"- **Issue:** {gap['issue']}",
                    f"- **Files:** {', '.join(gap['files'])}",
                    ""
                ])
        else:
            lines.append("✅ No critical gaps found. All P0/P1 variables present in templates.")
            lines.append("")
        
        lines.extend([
            "## Security Findings",
            ""
        ])
        
        if report["security_findings"]:
            for finding in report["security_findings"]:
                lines.extend([
                    f"### ⚠️ {finding['variable']} ({finding['severity']})",
                    f"- **Issue:** {finding['issue']}",
                    f"- **Recommendation:** {finding['recommendation']}",
                    ""
                ])
        else:
            lines.append("✅ No security issues found. No secrets hardcoded in code.")
            lines.append("")
        
        lines.extend([
            "## Recommendations",
            "",
            "### Production Deployment",
            "1. Verify all P0/P1 variables set in production `.env` file",
            "2. Rotate all secrets (JWT_SECRET, SERVICE_ROLE_KEY) before deployment",
            "3. Use environment-specific DATABASE_URL (not shared with test)",
            "4. Enable rate limiting (RATE_LIMITING_ENABLED=true) in production",
            "",
            "### Development Environment",
            "1. Copy `ENV_TEMPLATE.txt` to `.env` and fill all `<placeholder>` values",
            "2. For test suite, copy `apps/api/ENV_TEST_TEMPLATE.txt` to `apps/api/.env.test.local`",
            "3. For frontend, copy `apps/web/ENV_WEB_TEMPLATE.txt` to `apps/web/.env`",
            "",
            "### Secrets Management",
            "1. Never commit `.env` files to git (already gitignored)",
            "2. Store production secrets in secure vault (e.g., 1Password, Vault)",
            "3. Use different secrets for each environment (dev/staging/prod)",
            "4. Document secret rotation policy (recommended: every 90 days)",
            ""
        ])
        
        return "\n".join(lines)


def main():
    """Entry point per audit script."""
    project_root = Path(__file__).parent.parent.parent
    
    print("Starting Environment Configuration Audit...")
    print(f"Project root: {project_root}")
    print()
    
    auditor = EnvironmentAuditor(project_root)
    
    # Generate report
    report = auditor.generate_audit_report()
    
    # Save JSON report
    json_output = project_root / "temp" / "env_audit_report.json"
    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(report, indent=2))
    print(f"[OK] JSON report saved: {json_output}")
    
    # Generate Markdown report
    markdown_report = auditor.generate_markdown_report(report)
    md_output = project_root / "docs" / "reports" / "rag-environment-audit.md"
    md_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.write_text(markdown_report, encoding="utf-8")
    print(f"[OK] Markdown report saved: {md_output}")
    
    # Print summary
    print()
    print("Audit Summary:")
    print(f"   Total Variables: {report['summary']['total_variables']}")
    print(f"   P0 Critical: {report['summary']['p0_critical']}")
    print(f"   P1 High: {report['summary']['p1_high']}")
    print(f"   P2 Medium: {report['summary']['p2_medium']}")
    print(f"   Missing Templates: {report['summary']['missing_in_templates']}")
    print()
    
    if report['gaps']:
        print(f"[WARNING] {len(report['gaps'])} critical gap(s) found")
    else:
        print("[OK] No critical gaps")
    
    if report['security_findings']:
        print(f"[WARNING] {len(report['security_findings'])} security finding(s)")
    else:
        print("[OK] No security issues")
    
    print()
    print("Full report: docs/reports/rag-environment-audit.md")


if __name__ == "__main__":
    main()

