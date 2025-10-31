"""Tests for ModelManager."""

import pytest

from kode.core import ModelConfig, ModelManager, ModelProvider


def test_model_config_creation():
    """Test creating a model configuration."""
    config = ModelConfig(
        name="test-model",
        provider=ModelProvider.ANTHROPIC,
        model_id="claude-sonnet-4-5",
        api_key="test-key",
    )

    assert config.name == "test-model"
    assert config.provider == ModelProvider.ANTHROPIC
    assert config.model_id == "claude-sonnet-4-5"
    assert config.temperature == 0.7  # Default


def test_model_manager_initialization():
    """Test ModelManager initialization."""
    manager = ModelManager()

    assert manager is not None
    assert len(manager.list_models()) == 0  # No models registered initially


def test_model_manager_register():
    """Test registering models."""
    manager = ModelManager()

    config = ModelConfig(
        name="test-model",
        provider=ModelProvider.ANTHROPIC,
        model_id="claude-sonnet-4-5",
        api_key="test-key",
    )

    manager.register_model(config)

    assert "test-model" in manager.list_models()


def test_model_manager_load_from_config():
    """Test loading models from configuration."""
    config = {
        "models": {
            "main": "claude-sonnet-4-5",
            "task": "claude-sonnet-4-5",
        },
        "apiKeys": {"anthropic": "test-key"},
    }

    manager = ModelManager(config)

    assert "main" in manager.list_models()
    assert "task" in manager.list_models()


def test_model_pointers():
    """Test model pointer resolution."""
    config = {
        "models": {"main": "claude-sonnet-4-5"},
        "modelPointers": {"main": "claude-sonnet-4-5"},
        "apiKeys": {"anthropic": "test-key"},
    }

    manager = ModelManager(config)

    pointers = manager.list_pointers()
    assert "main" in pointers
    assert pointers["main"] == "claude-sonnet-4-5"