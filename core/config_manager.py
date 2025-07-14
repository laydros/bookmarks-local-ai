"""
Configuration management for bookmark tools.
"""

import os
import yaml
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Model configuration settings."""

    embedding: str = "nomic-embed-text"
    llm: str = "llama3.1:8b"
    fallback_embedding: Optional[str] = "mxbai-embed-large"
    fallback_llm: Optional[str] = "mistral:7b"
    ollama_url: str = "http://localhost:11434"


@dataclass
class ProcessingConfig:
    """Processing configuration settings."""

    batch_size: int = 50
    delay_between_requests: float = 0.5
    max_retries: int = 3
    timeout: int = 10
    web_extraction_timeout: int = 10
    enable_web_extraction: bool = True


@dataclass
class OutputConfig:
    """Output configuration settings."""

    preserve_field_order: bool = True
    backup_original: bool = True
    backup_suffix: str = ".backup"
    indent: int = 2
    ensure_ascii: bool = False


@dataclass
class QualityConfig:
    """Quality control settings."""

    min_description_length: int = 10
    max_description_length: int = 500
    min_tags: int = 1
    max_tags: int = 10
    enable_url_validation: bool = True
    standardize_tags: bool = True


@dataclass
class BookmarkConfig:
    """Complete configuration for bookmark tools."""

    models: ModelConfig
    processing: ProcessingConfig
    output: OutputConfig
    quality: QualityConfig

    @classmethod
    def load_from_file(cls, config_path: str) -> "BookmarkConfig":
        """Load configuration from YAML or JSON file."""
        if not os.path.exists(config_path):
            logger.info(f"Config file {config_path} not found, using defaults")
            return cls.default()

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                if config_path.endswith(".yaml") or config_path.endswith(".yml"):
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)

            return cls.from_dict(data)

        except Exception as e:
            logger.warning(f"Error loading config from {config_path}: {e}")
            logger.info("Using default configuration")
            return cls.default()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BookmarkConfig":
        """Create configuration from dictionary."""
        models = ModelConfig(**data.get("models", {}))
        processing = ProcessingConfig(**data.get("processing", {}))
        output = OutputConfig(**data.get("output", {}))
        quality = QualityConfig(**data.get("quality", {}))

        return cls(models=models, processing=processing, output=output, quality=quality)

    @classmethod
    def default(cls) -> "BookmarkConfig":
        """Create default configuration."""
        return cls(
            models=ModelConfig(),
            processing=ProcessingConfig(),
            output=OutputConfig(),
            quality=QualityConfig(),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "models": asdict(self.models),
            "processing": asdict(self.processing),
            "output": asdict(self.output),
            "quality": asdict(self.quality),
        }

    def save_to_file(self, config_path: str) -> bool:
        """Save configuration to file."""
        try:
            data = self.to_dict()

            with open(config_path, "w", encoding="utf-8") as f:
                if config_path.endswith(".yaml") or config_path.endswith(".yml"):
                    yaml.dump(data, f, default_flow_style=False, indent=2)
                else:
                    json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Configuration saved to {config_path}")
            return True

        except Exception as e:
            logger.error(f"Error saving config to {config_path}: {e}")
            return False

    def validate(self) -> tuple[bool, list[str]]:
        """Validate configuration settings."""
        errors = []

        # Validate models
        if not self.models.embedding:
            errors.append("Embedding model cannot be empty")
        if not self.models.llm:
            errors.append("LLM model cannot be empty")

        # Validate processing
        if self.processing.batch_size <= 0:
            errors.append("Batch size must be positive")
        if self.processing.delay_between_requests < 0:
            errors.append("Delay between requests cannot be negative")
        if self.processing.max_retries < 0:
            errors.append("Max retries cannot be negative")

        # Validate quality
        if self.quality.min_description_length < 0:
            errors.append("Min description length cannot be negative")
        if self.quality.max_description_length <= self.quality.min_description_length:
            errors.append("Max description length must be greater than min")
        if self.quality.min_tags < 0:
            errors.append("Min tags cannot be negative")
        if self.quality.max_tags <= 0:
            errors.append("Max tags must be positive")

        return len(errors) == 0, errors


def create_default_config(config_path: str = "bookmark_config.yaml") -> BookmarkConfig:
    """Create and save a default configuration file."""
    config = BookmarkConfig.default()
    config.save_to_file(config_path)
    return config


def load_config(config_path: Optional[str] = None) -> BookmarkConfig:
    """Load configuration from file or create default."""
    if config_path is None:
        # Look for config files in common locations
        possible_paths = [
            "bookmark_config.yaml",
            "bookmark_config.yml",
            "bookmark_config.json",
            "config/bookmark_config.yaml",
            os.path.expanduser("~/.bookmark_config.yaml"),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                config_path = path
                break
        else:
            # No config found, use defaults
            return BookmarkConfig.default()

    return BookmarkConfig.load_from_file(config_path)
