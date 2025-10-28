"""
Audit script per trovare tutti gli import legacy da api.main.

Story 5.4 Task 4.1

Usage:
    cd apps/api
    poetry run python scripts/audit_legacy_imports.py > legacy_imports.txt
"""
import re
from pathlib import Path

legacy_patterns = [
    r"from api\.main import",
    r"from api import main",
    r"import api\.main",
]

test_dir = Path("tests")
issues = []

for test_file in test_dir.rglob("*.py"):
    content = test_file.read_text(encoding='utf-8')
    for pattern in legacy_patterns:
        if re.search(pattern, content):
            # Find specific line numbers
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    issues.append(f"{test_file}:{i}: {line.strip()}")

print(f"Found {len(issues)} legacy imports:")
for issue in issues:
    print(f"  - {issue}")

if len(issues) == 0:
    print("  ✅ No legacy imports found!")

