# CodeRabbit Configuration Validation Tests

## Overview

The test suite in `test_coderabbit_config.py` validates the `.coderabbit.yaml` configuration file to ensure:

1. **YAML Syntax**: The file is valid YAML and can be parsed
2. **Schema Compliance**: All required keys and sections are present
3. **Value Validation**: Configuration values are within acceptable ranges and types
4. **Path Instructions**: Test generation instructions are properly configured for both API and Web components
5. **Tool Configuration**: Analysis tools (ESLint, Ruff, Gitleaks, etc.) are properly enabled
6. **Project Consistency**: Configuration matches the actual project structure

## Test Categories

### Structure Tests (`TestCodeRabbitConfigStructure`)
- Validates file existence and YAML parsing
- Checks required top-level keys
- Validates language setting

### Reviews Configuration (`TestCodeRabbitReviewsConfig`)
- Validates review profile settings
- Checks auto-review configuration
- Validates finishing touches (docstrings and unit tests)
- Ensures proper path filters
- Verifies tool configurations

### Knowledge Base (`TestCodeRabbitKnowledgeBase`)
- Validates web search settings
- Checks code guidelines configuration

### Code Generation (`TestCodeRabbitCodeGeneration`)
- **Critical**: Validates test generation instructions
- Ensures API Python tests use pytest and pytest-asyncio
- Ensures Web TSX tests use Vitest and React Testing Library
- Validates mocking requirements

### Chat Configuration (`TestCodeRabbitChatConfig`)
- Validates auto-reply settings

### Integrity Tests (`TestCodeRabbitConfigIntegrity`)
- Checks for duplicate path patterns
- Validates file size
- Ensures critical paths aren't excluded

### Performance Tests (`TestCodeRabbitConfigPerformance`)
- Ensures reasonable number of path filters
- Validates at least some tools are enabled

### Integration Tests (`TestCodeRabbitConfigValidation`)
- Validates YAML loading
- Checks for complex YAML features
- Validates paths match project structure

## Running the Tests

```bash
# Run all CodeRabbit config tests
pytest tests/test_coderabbit_config.py -v

# Run specific test class
pytest tests/test_coderabbit_config.py::TestCodeRabbitCodeGeneration -v

# Run with coverage
pytest tests/test_coderabbit_config.py --cov=. --cov-report=term-missing
```

## Test Coverage

The test suite includes **35+ individual test cases** covering:
- ✅ YAML syntax validation
- ✅ Required keys verification
- ✅ Type checking for all values
- ✅ Path instruction validation
- ✅ Tool configuration validation
- ✅ Integration with project structure

## Maintenance

When updating `.coderabbit.yaml`:
1. Run the test suite to ensure no regression
2. Update tests if adding new configuration sections
3. Ensure new path instructions have corresponding validation tests

## Why These Tests Matter

Configuration file validation prevents:
- ❌ Syntax errors that break CI/CD
- ❌ Missing critical configuration sections
- ❌ Invalid tool settings
- ❌ Incorrect test generation instructions
- ❌ Path filter misconfigurations

These tests ensure CodeRabbit operates correctly and generates appropriate tests for the project.