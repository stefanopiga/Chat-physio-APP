"""
Test suite for .coderabbit.yaml configuration validation.

This test ensures that the CodeRabbit configuration file is valid and contains
all required settings for proper CI/CD operation and test generation.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml


# Path to the repository root
REPO_ROOT = Path(__file__).parent.parent
CODERABBIT_CONFIG_PATH = REPO_ROOT / ".coderabbit.yaml"


@pytest.fixture
def coderabbit_config() -> Dict[str, Any]:
    """Load and parse the .coderabbit.yaml configuration file."""
    if not CODERABBIT_CONFIG_PATH.exists():
        pytest.fail(f"CodeRabbit configuration file not found at {CODERABBIT_CONFIG_PATH}")
    
    with open(CODERABBIT_CONFIG_PATH, 'r', encoding='utf-8') as f:
        try:
            config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            pytest.fail(f"Failed to parse YAML: {e}")
    
    return config


class TestCodeRabbitConfigStructure:
    """Test the basic structure and required keys of the configuration."""
    
    def test_config_file_exists(self):
        """Verify that .coderabbit.yaml exists in the repository root."""
        assert CODERABBIT_CONFIG_PATH.exists(), \
            f"CodeRabbit config file not found at {CODERABBIT_CONFIG_PATH}"
    
    def test_yaml_is_valid(self, coderabbit_config):
        """Verify that the YAML file is valid and parseable."""
        assert coderabbit_config is not None
        assert isinstance(coderabbit_config, dict)
    
    def test_has_required_top_level_keys(self, coderabbit_config):
        """Verify that all required top-level keys are present."""
        required_keys = ['language', 'reviews', 'knowledge_base', 'chat']
        for key in required_keys:
            assert key in coderabbit_config, \
                f"Missing required top-level key: {key}"
    
    def test_language_is_valid(self, coderabbit_config):
        """Verify that the language setting is valid."""
        assert 'language' in coderabbit_config
        language = coderabbit_config['language']
        assert isinstance(language, str)
        assert language in ['en-US', 'it-IT', 'es-ES', 'fr-FR', 'de-DE'], \
            f"Invalid language code: {language}"


class TestCodeRabbitReviewsConfig:
    """Test the reviews configuration section."""
    
    def test_reviews_section_exists(self, coderabbit_config):
        """Verify that the reviews section is present and is a dict."""
        assert 'reviews' in coderabbit_config
        assert isinstance(coderabbit_config['reviews'], dict)
    
    def test_has_profile_setting(self, coderabbit_config):
        """Verify that review profile is configured."""
        reviews = coderabbit_config['reviews']
        assert 'profile' in reviews
        assert isinstance(reviews['profile'], str)
        assert reviews['profile'] in ['chill', 'assertive', 'strict'], \
            f"Invalid profile: {reviews['profile']}"
    
    def test_auto_review_configuration(self, coderabbit_config):
        """Verify auto_review settings are properly configured."""
        reviews = coderabbit_config['reviews']
        assert 'auto_review' in reviews
        auto_review = reviews['auto_review']
        assert isinstance(auto_review, dict)
        assert 'enabled' in auto_review
        assert isinstance(auto_review['enabled'], bool)
        assert 'drafts' in auto_review
        assert isinstance(auto_review['drafts'], bool)
    
    def test_finishing_touches_configuration(self, coderabbit_config):
        """Verify finishing_touches settings for docstrings and unit tests."""
        reviews = coderabbit_config['reviews']
        assert 'finishing_touches' in reviews, \
            "Missing finishing_touches configuration"
        
        finishing_touches = reviews['finishing_touches']
        assert isinstance(finishing_touches, dict)
        
        # Check docstrings configuration
        assert 'docstrings' in finishing_touches
        docstrings = finishing_touches['docstrings']
        assert isinstance(docstrings, dict)
        assert 'enabled' in docstrings
        assert isinstance(docstrings['enabled'], bool)
        assert docstrings['enabled'] is True, \
            "Docstrings generation should be enabled"
        
        # Check unit_tests configuration
        assert 'unit_tests' in finishing_touches
        unit_tests = finishing_touches['unit_tests']
        assert isinstance(unit_tests, dict)
        assert 'enabled' in unit_tests
        assert isinstance(unit_tests['enabled'], bool)
        assert unit_tests['enabled'] is True, \
            "Unit tests generation should be enabled"
    
    def test_path_filters_are_valid(self, coderabbit_config):
        """Verify that path filters are properly configured."""
        reviews = coderabbit_config['reviews']
        assert 'path_filters' in reviews
        path_filters = reviews['path_filters']
        assert isinstance(path_filters, list)
        assert len(path_filters) > 0, "Path filters should not be empty"
        
        # Verify filters are strings
        for filter_pattern in path_filters:
            assert isinstance(filter_pattern, str)
    
    def test_excludes_common_build_artifacts(self, coderabbit_config):
        """Verify that common build artifacts are excluded from reviews."""
        reviews = coderabbit_config['reviews']
        path_filters = reviews['path_filters']
        
        expected_exclusions = [
            'node_modules',
            'dist',
            'coverage',
            '__pycache__',
        ]
        
        for exclusion in expected_exclusions:
            assert any(exclusion in filter_str for filter_str in path_filters), \
                f"Missing exclusion for: {exclusion}"
    
    def test_includes_project_paths(self, coderabbit_config):
        """Verify that main project paths are included."""
        reviews = coderabbit_config['reviews']
        path_filters = reviews['path_filters']
        
        expected_includes = ['apps/api/**', 'apps/web/**', 'docs/**']
        for include in expected_includes:
            assert any(include in filter_str for filter_str in path_filters), \
                f"Missing include for: {include}"
    
    def test_tools_configuration(self, coderabbit_config):
        """Verify that analysis tools are properly configured."""
        reviews = coderabbit_config['reviews']
        assert 'tools' in reviews
        tools = reviews['tools']
        assert isinstance(tools, dict)
        
        # Check for expected tools
        expected_tools = ['eslint', 'ruff', 'gitleaks', 'markdownlint']
        for tool in expected_tools:
            assert tool in tools, f"Missing tool configuration: {tool}"
            assert 'enabled' in tools[tool]
            assert isinstance(tools[tool]['enabled'], bool)


class TestCodeRabbitKnowledgeBase:
    """Test the knowledge_base configuration section."""
    
    def test_knowledge_base_exists(self, coderabbit_config):
        """Verify that knowledge_base section is present."""
        assert 'knowledge_base' in coderabbit_config
        assert isinstance(coderabbit_config['knowledge_base'], dict)
    
    def test_web_search_configuration(self, coderabbit_config):
        """Verify web_search is properly configured."""
        kb = coderabbit_config['knowledge_base']
        assert 'web_search' in kb
        assert 'enabled' in kb['web_search']
        assert isinstance(kb['web_search']['enabled'], bool)
    
    def test_code_guidelines_configuration(self, coderabbit_config):
        """Verify code_guidelines are properly configured."""
        kb = coderabbit_config['knowledge_base']
        assert 'code_guidelines' in kb
        guidelines = kb['code_guidelines']
        assert 'enabled' in guidelines
        assert isinstance(guidelines['enabled'], bool)
        assert 'filePatterns' in guidelines
        assert isinstance(guidelines['filePatterns'], list)


class TestCodeRabbitCodeGeneration:
    """Test the code_generation configuration section."""
    
    def test_code_generation_section_exists(self, coderabbit_config):
        """Verify that code_generation section is present."""
        assert 'code_generation' in coderabbit_config, \
            "Missing code_generation configuration section"
        assert isinstance(coderabbit_config['code_generation'], dict)
    
    def test_unit_tests_configuration_exists(self, coderabbit_config):
        """Verify that unit_tests configuration is present in code_generation."""
        code_gen = coderabbit_config['code_generation']
        assert 'unit_tests' in code_gen
        assert isinstance(code_gen['unit_tests'], dict)
    
    def test_path_instructions_exist(self, coderabbit_config):
        """Verify that path_instructions are configured for unit tests."""
        unit_tests = coderabbit_config['code_generation']['unit_tests']
        assert 'path_instructions' in unit_tests
        path_instructions = unit_tests['path_instructions']
        assert isinstance(path_instructions, list)
        assert len(path_instructions) > 0, \
            "path_instructions should not be empty"
    
    def test_api_python_test_instructions(self, coderabbit_config):
        """Verify that API Python test instructions are properly configured."""
        path_instructions = coderabbit_config['code_generation']['unit_tests']['path_instructions']
        
        # Find API Python instruction
        api_instruction = None
        for instruction in path_instructions:
            if instruction.get('path') == 'apps/api/**/*.py':
                api_instruction = instruction
                break
        
        assert api_instruction is not None, \
            "Missing path instruction for apps/api/**/*.py"
        
        assert 'instructions' in api_instruction
        instructions_text = api_instruction['instructions']
        assert isinstance(instructions_text, str)
        
        # Verify key requirements are mentioned
        assert 'pytest' in instructions_text.lower(), \
            "API instructions should mention pytest"
        assert 'mock' in instructions_text.lower(), \
            "API instructions should mention mocking"
        assert any(keyword in instructions_text.lower() 
                   for keyword in ['openai', 'supabase', 'database']), \
            "API instructions should mention external services to mock"
    
    def test_web_tsx_test_instructions(self, coderabbit_config):
        """Verify that Web TSX test instructions are properly configured."""
        path_instructions = coderabbit_config['code_generation']['unit_tests']['path_instructions']
        
        # Find Web TSX instruction
        web_instruction = None
        for instruction in path_instructions:
            if instruction.get('path') == 'apps/web/**/*.tsx':
                web_instruction = instruction
                break
        
        assert web_instruction is not None, \
            "Missing path instruction for apps/web/**/*.tsx"
        
        assert 'instructions' in web_instruction
        instructions_text = web_instruction['instructions']
        assert isinstance(instructions_text, str)
        
        # Verify key requirements are mentioned
        assert 'vitest' in instructions_text.lower(), \
            "Web instructions should mention Vitest"
        assert 'react testing library' in instructions_text.lower(), \
            "Web instructions should mention React Testing Library"
        assert 'render' in instructions_text.lower(), \
            "Web instructions should mention component rendering"
    
    def test_all_path_instructions_have_required_fields(self, coderabbit_config):
        """Verify that all path instructions have required fields."""
        path_instructions = coderabbit_config['code_generation']['unit_tests']['path_instructions']
        
        for idx, instruction in enumerate(path_instructions):
            assert 'path' in instruction, \
                f"path_instruction[{idx}] missing 'path' field"
            assert 'instructions' in instruction, \
                f"path_instruction[{idx}] missing 'instructions' field"
            assert isinstance(instruction['path'], str), \
                f"path_instruction[{idx}] 'path' must be a string"
            assert isinstance(instruction['instructions'], str), \
                f"path_instruction[{idx}] 'instructions' must be a string"
            assert len(instruction['instructions'].strip()) > 0, \
                f"path_instruction[{idx}] 'instructions' cannot be empty"


class TestCodeRabbitChatConfig:
    """Test the chat configuration section."""
    
    def test_chat_section_exists(self, coderabbit_config):
        """Verify that chat section is present."""
        assert 'chat' in coderabbit_config
        assert isinstance(coderabbit_config['chat'], dict)
    
    def test_auto_reply_setting(self, coderabbit_config):
        """Verify auto_reply setting is configured."""
        chat = coderabbit_config['chat']
        assert 'auto_reply' in chat
        assert isinstance(chat['auto_reply'], bool)


class TestCodeRabbitConfigIntegrity:
    """Test overall configuration integrity and consistency."""
    
    def test_no_duplicate_path_patterns(self, coderabbit_config):
        """Verify that there are no duplicate path patterns in path_instructions."""
        if 'code_generation' not in coderabbit_config:
            pytest.skip("code_generation section not present")
        
        path_instructions = coderabbit_config['code_generation']['unit_tests']['path_instructions']
        paths = [instr['path'] for instr in path_instructions]
        
        assert len(paths) == len(set(paths)), \
            f"Duplicate path patterns found: {[p for p in paths if paths.count(p) > 1]}"
    
    def test_config_file_size_reasonable(self):
        """Verify that the config file size is reasonable (not corrupted)."""
        file_size = CODERABBIT_CONFIG_PATH.stat().st_size
        assert file_size > 100, "Config file seems too small (possibly empty)"
        assert file_size < 100000, "Config file seems unusually large"
    
    def test_language_matches_project(self, coderabbit_config):
        """Verify language setting matches project (Italian for this project)."""
        language = coderabbit_config['language']
        assert language == 'it-IT', \
            f"Language should be 'it-IT' for this project, found: {language}"
    
    def test_critical_paths_not_excluded(self, coderabbit_config):
        """Verify that critical project paths are not accidentally excluded."""
        path_filters = coderabbit_config['reviews']['path_filters']
        
        # Critical paths that should NOT be excluded
        critical_paths = ['apps/api', 'apps/web', 'tests', 'docs']
        
        exclusion_patterns = [f for f in path_filters if f.startswith('!')]
        
        for critical_path in critical_paths:
            for exclusion in exclusion_patterns:
                # Simple check: critical path shouldn't be directly excluded
                assert not exclusion.endswith(f'{critical_path}/**'), \
                    f"Critical path {critical_path} appears to be excluded: {exclusion}"


class TestCodeRabbitConfigPerformance:
    """Test configuration settings that might affect performance."""
    
    def test_reasonable_number_of_path_filters(self, coderabbit_config):
        """Verify that the number of path filters is reasonable."""
        path_filters = coderabbit_config['reviews']['path_filters']
        assert len(path_filters) < 50, \
            f"Too many path filters ({len(path_filters)}), may impact performance"
    
    def test_tools_not_all_disabled(self, coderabbit_config):
        """Verify that at least some analysis tools are enabled."""
        tools = coderabbit_config['reviews']['tools']
        enabled_tools = [tool for tool, config in tools.items() 
                        if config.get('enabled', False)]
        
        assert len(enabled_tools) > 0, \
            "At least one analysis tool should be enabled"


# Integration test for actual file validation
class TestCodeRabbitConfigValidation:
    """Integration tests for configuration validation."""
    
    def test_yaml_loads_with_pyyaml(self):
        """Verify that the YAML file loads correctly with PyYAML."""
        try:
            with open(CODERABBIT_CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            assert config is not None
        except Exception as e:
            pytest.fail(f"Failed to load YAML with PyYAML: {e}")
    
    def test_no_yaml_aliases_or_anchors(self, coderabbit_config):
        """Verify that the config doesn't use complex YAML features."""
        # Read raw content
        with open(CODERABBIT_CONFIG_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Simple check for YAML anchors/aliases
        assert '&' not in content or content.count('&') < 2, \
            "YAML anchors found - keep config simple"
        assert '*' not in content or content.count('*') < 2, \
            "YAML aliases found - keep config simple"
    
    def test_config_matches_project_structure(self):
        """Verify that configured paths actually exist in the project."""
        # Check that configured paths exist
        api_path = REPO_ROOT / "apps" / "api"
        web_path = REPO_ROOT / "apps" / "web"
        docs_path = REPO_ROOT / "docs"
        
        assert api_path.exists(), "apps/api directory not found"
        assert web_path.exists(), "apps/web directory not found"
        assert docs_path.exists(), "docs directory not found"