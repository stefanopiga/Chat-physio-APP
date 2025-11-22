#!/bin/bash
# Quick test runner for CodeRabbit configuration validation
# Usage: ./scripts/validation/test_coderabbit_config.sh

cd "$(dirname "$0")/../.." || exit 1

echo "=== CodeRabbit Configuration Validation ==="
echo ""

# Run the validation tests
pytest tests/test_coderabbit_config.py -v --tb=short

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo ""
    echo "✓ All CodeRabbit configuration tests passed!"
else
    echo ""
    echo "✗ Some tests failed. Please review the output above."
fi

exit $exit_code