"""Model management system supporting multiple AI providers."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Type

from langchain.chat_models.base import BaseChatModel
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from pydantic import BaseModel


class ModelProvider(str, Enum):
    """Supported model providers."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    CUSTOM = "custom"


class ModelCapability(str, Enum):
    """Model capabilities."""

    CHAT = "chat"
    VISION = "vision"
    FUNCTION_CALLING = "function_calling"
    STREAMING = "streaming"


@dataclass
class ModelConfig:
    """Configuration for a single model."""

    name: str
    provider: ModelProvider
    model_id: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    capabilities: list[ModelCapability] = field(default_factory=list)
    extra_params: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate and set defaults."""
        if not self.capabilities:
            # Default capabilities based on provider
            if self.provider == ModelProvider.ANTHROPIC:
                self.capabilities = [
                    ModelCapability.CHAT,
                    ModelCapability.VISION,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.STREAMING,
                ]
            elif self.provider == ModelProvider.OPENAI:
                self.capabilities = [
                    ModelCapability.CHAT,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.STREAMING,
                ]


class ModelManager:
    """
    Manages multiple AI models and provides unified interface for model switching.

    Equivalent to TypeScript's ModelManager in src/utils/model.ts
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize model manager.

        Args:
            config: Configuration dictionary with model definitions
        """
        self._models: Dict[str, ModelConfig] = {}
        self._instances: Dict[str, BaseChatModel] = {}
        self._current_model: Optional[str] = None
        self._model_pointers: Dict[str, str] = {
            "main": "claude-sonnet-4-5",
            "task": "claude-sonnet-4-5",
            "quick": "gpt-4-turbo-preview",
            "reasoning": "claude-sonnet-4-5",
        }

        if config:
            self._load_config(config)

    def _load_config(self, config: Dict[str, Any]) -> None:
        """Load models from configuration."""
        # Load model definitions
        if "models" in config:
            for name, model_def in config["models"].items():
                if isinstance(model_def, str):
                    # Simple string reference to model ID
                    self.register_model(
                        ModelConfig(
                            name=name,
                            provider=ModelProvider.ANTHROPIC,
                            model_id=model_def,
                            api_key=config.get("apiKeys", {}).get("anthropic"),
                        )
                    )
                elif isinstance(model_def, dict):
                    # Full model configuration
                    self.register_model(
                        ModelConfig(
                            name=name,
                            provider=ModelProvider(model_def.get("provider", "anthropic")),
                            model_id=model_def["model_id"],
                            api_key=model_def.get("api_key")
                            or config.get("apiKeys", {}).get(model_def.get("provider")),
                            base_url=model_def.get("base_url"),
                            temperature=model_def.get("temperature", 0.7),
                            max_tokens=model_def.get("max_tokens", 4096),
                        )
                    )

        # Load model pointers
        if "modelPointers" in config:
            self._model_pointers.update(config["modelPointers"])

    def register_model(self, config: ModelConfig) -> None:
        """
        Register a new model configuration.

        Args:
            config: Model configuration
        """
        self._models[config.name] = config

    def get_model(self, name: Optional[str] = None) -> BaseChatModel:
        """
        Get a model instance by name or pointer.

        Args:
            name: Model name, pointer (main/task/quick), or None for current

        Returns:
            LangChain chat model instance

        Raises:
            ValueError: If model not found
        """
        # Resolve model name
        if name is None:
            if self._current_model is None:
                name = self._model_pointers["main"]
            else:
                name = self._current_model
        elif name in self._model_pointers:
            name = self._model_pointers[name]

        # Return cached instance if available
        if name in self._instances:
            return self._instances[name]

        # Get model config
        if name not in self._models:
            raise ValueError(f"Model '{name}' not found. Available: {list(self._models.keys())}")

        config = self._models[name]

        # Create model instance
        model = self._create_model_instance(config)
        self._instances[name] = model
        return model

    def _create_model_instance(self, config: ModelConfig) -> BaseChatModel:
        """
        Create a LangChain model instance from configuration.

        Args:
            config: Model configuration

        Returns:
            LangChain chat model instance
        """
        if config.provider == ModelProvider.ANTHROPIC:
            return ChatAnthropic(
                model=config.model_id,
                anthropic_api_key=config.api_key,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                **config.extra_params,
            )
        elif config.provider == ModelProvider.OPENAI:
            params = {
                "model": config.model_id,
                "openai_api_key": config.api_key,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                **config.extra_params,
            }
            if config.base_url:
                params["openai_api_base"] = config.base_url
            return ChatOpenAI(**params)
        else:
            raise ValueError(f"Unsupported provider: {config.provider}")

    def switch_model(self, name: str) -> None:
        """
        Switch the current active model.

        Args:
            name: Model name or pointer to switch to
        """
        # Resolve pointer if needed
        if name in self._model_pointers:
            name = self._model_pointers[name]

        if name not in self._models:
            raise ValueError(f"Model '{name}' not found")

        self._current_model = name

    def get_current_model_name(self) -> str:
        """Get the name of the current active model."""
        if self._current_model is None:
            return self._model_pointers["main"]
        return self._current_model

    def list_models(self) -> list[str]:
        """List all registered model names."""
        return list(self._models.keys())

    def list_pointers(self) -> Dict[str, str]:
        """Get all model pointers."""
        return self._model_pointers.copy()

    def get_model_config(self, name: str) -> ModelConfig:
        """
        Get model configuration.

        Args:
            name: Model name

        Returns:
            Model configuration
        """
        if name not in self._models:
            raise ValueError(f"Model '{name}' not found")
        return self._models[name]