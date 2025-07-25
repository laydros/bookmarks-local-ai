"""
Tests for configuration management.
"""

import os
import tempfile
from core.config_manager import (
    BookmarkConfig,
    ModelConfig,
    ProcessingConfig,
    OutputConfig,
    QualityConfig,
)


class TestBookmarkConfig:
    """Test BookmarkConfig class."""

    def test_default_config(self):
        """Test default configuration creation."""
        config = BookmarkConfig.default()

        assert config.models.embedding == "nomic-embed-text"
        assert config.models.llm == "llama3.1:8b"
        assert config.processing.delay_between_requests == 0.5
        assert config.output.backup_original is True
        assert config.quality.enable_url_validation is True

    def test_config_validation_success(self):
        """Test successful configuration validation."""
        config = BookmarkConfig.default()
        is_valid, errors = config.validate()

        assert is_valid
        assert len(errors) == 0

    def test_config_validation_errors(self):
        """Test configuration validation with errors."""
        config = BookmarkConfig.default()
        config.models.embedding = ""  # Invalid
        config.processing.batch_size = -1  # Invalid
        config.quality.min_tags = -1  # Invalid

        is_valid, errors = config.validate()

        assert not is_valid
        assert len(errors) >= 3
        assert any(
            "embedding model cannot be empty" in error.lower() for error in errors
        )

    def test_save_and_load_yaml(self):
        """Test saving and loading YAML configuration."""
        config = BookmarkConfig.default()
        config.models.embedding = "test-model"
        config.processing.batch_size = 25

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            temp_path = f.name

        try:
            # Save configuration
            success = config.save_to_file(temp_path)
            assert success
            assert os.path.exists(temp_path)

            # Load configuration
            loaded_config = BookmarkConfig.load_from_file(temp_path)
            assert loaded_config.models.embedding == "test-model"
            assert loaded_config.processing.batch_size == 25

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_save_and_load_json(self):
        """Test saving and loading JSON configuration."""
        config = BookmarkConfig.default()
        config.models.llm = "test-llm"
        config.output.indent = 4

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            # Save configuration
            success = config.save_to_file(temp_path)
            assert success
            assert os.path.exists(temp_path)

            # Load configuration
            loaded_config = BookmarkConfig.load_from_file(temp_path)
            assert loaded_config.models.llm == "test-llm"
            assert loaded_config.output.indent == 4

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_load_nonexistent_file(self):
        """Test loading non-existent configuration file."""
        config = BookmarkConfig.load_from_file("nonexistent.yaml")

        # Should return default config
        assert config.models.embedding == "nomic-embed-text"
        assert config.models.llm == "llama3.1:8b"

    def test_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "models": {"embedding": "custom-embed", "llm": "custom-llm"},
            "processing": {"batch_size": 100, "delay_between_requests": 1.0},
        }

        config = BookmarkConfig.from_dict(data)

        assert config.models.embedding == "custom-embed"
        assert config.models.llm == "custom-llm"
        assert config.processing.batch_size == 100
        assert config.processing.delay_between_requests == 1.0

        # Should use defaults for missing values
        assert config.output.backup_original is True
        assert config.quality.enable_url_validation is True

    def test_to_dict(self):
        """Test converting config to dictionary."""
        config = BookmarkConfig.default()
        config.models.embedding = "test-model"

        data = config.to_dict()

        assert isinstance(data, dict)
        assert data["models"]["embedding"] == "test-model"
        assert "processing" in data
        assert "output" in data
        assert "quality" in data


class TestModelConfig:
    """Test ModelConfig class."""

    def test_model_config_defaults(self):
        """Test ModelConfig default values."""
        config = ModelConfig()

        assert config.embedding == "nomic-embed-text"
        assert config.llm == "llama3.1:8b"
        assert config.fallback_embedding == "mxbai-embed-large"
        assert config.fallback_llm == "mistral:7b"
        assert config.ollama_url == "http://localhost:11434"


class TestProcessingConfig:
    """Test ProcessingConfig class."""

    def test_processing_config_defaults(self):
        """Test ProcessingConfig default values."""
        config = ProcessingConfig()

        assert config.batch_size == 50
        assert config.delay_between_requests == 0.5
        assert config.max_retries == 3
        assert config.timeout == 10
        assert config.web_extraction_timeout == 10
        assert config.enable_web_extraction is True


class TestOutputConfig:
    """Test OutputConfig class."""

    def test_output_config_defaults(self):
        """Test OutputConfig default values."""
        config = OutputConfig()

        assert config.preserve_field_order is True
        assert config.backup_original is True
        assert config.backup_suffix == ".backup"
        assert config.indent == 2
        assert config.ensure_ascii is False


class TestQualityConfig:
    """Test QualityConfig class."""

    def test_quality_config_defaults(self):
        """Test QualityConfig default values."""
        config = QualityConfig()

        assert config.min_description_length == 10
        assert config.max_description_length == 500
        assert config.min_tags == 1
        assert config.max_tags == 10
        assert config.enable_url_validation is True
        assert config.standardize_tags is True
