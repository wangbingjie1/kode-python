"""Hierarchical configuration management system."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigManager:
    """
    Manages hierarchical configuration for Kode.

    Equivalent to TypeScript's config system in src/utils/config.ts

    Priority order (highest to lowest):
    1. Environment variables
    2. CLI parameters
    3. Project config (./.kode.json)
    4. User config (~/.kode.json)
    5. Default values
    """

    DEFAULT_CONFIG = {
        "models": {
            "main": "claude-sonnet-4-5",
            "task": "claude-sonnet-4-5",
            "quick": "gpt-4-turbo-preview",
            "reasoning": "claude-sonnet-4-5",
        },
        "modelPointers": {
            "main": "claude-sonnet-4-5",
            "task": "claude-sonnet-4-5",
            "quick": "gpt-4-turbo-preview",
            "reasoning": "claude-sonnet-4-5",
        },
        "apiKeys": {},
        "verbose": False,
        "maxTokens": 4096,
        "temperature": 0.7,
        "theme": "dark",
    }

    def __init__(self, project_root: Optional[str] = None, cli_params: Optional[Dict] = None):
        """
        Initialize configuration manager.

        Args:
            project_root: Project root directory
            cli_params: CLI parameters to override config
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.cli_params = cli_params or {}

        # Load configurations
        self._user_config = self._load_user_config()
        self._project_config = self._load_project_config()

        # Merge configurations
        self._config = self._merge_configs()

    def _load_user_config(self) -> Dict[str, Any]:
        """Load user configuration from ~/.kode.json."""
        user_config_path = Path.home() / ".kode.json"
        if user_config_path.exists():
            try:
                with open(user_config_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load user config: {e}")
        return {}

    def _load_project_config(self) -> Dict[str, Any]:
        """Load project configuration from ./.kode.json."""
        project_config_path = self.project_root / ".kode.json"
        if project_config_path.exists():
            try:
                with open(project_config_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load project config: {e}")
        return {}

    def _merge_configs(self) -> Dict[str, Any]:
        """Merge all configuration sources."""
        # Start with defaults
        config = self.DEFAULT_CONFIG.copy()

        # Merge user config
        config = self._deep_merge(config, self._user_config)

        # Merge project config
        config = self._deep_merge(config, self._project_config)

        # Apply environment variables
        config = self._apply_env_vars(config)

        # Apply CLI parameters (highest priority)
        config = self._deep_merge(config, self.cli_params)

        return config

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _apply_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variables to configuration."""
        # API Keys
        if "ANTHROPIC_API_KEY" in os.environ:
            config["apiKeys"]["anthropic"] = os.environ["ANTHROPIC_API_KEY"]
        if "OPENAI_API_KEY" in os.environ:
            config["apiKeys"]["openai"] = os.environ["OPENAI_API_KEY"]

        # Other settings
        if "KODE_VERBOSE" in os.environ:
            config["verbose"] = os.environ["KODE_VERBOSE"].lower() in ("true", "1", "yes")
        if "KODE_MODEL" in os.environ:
            config["models"]["main"] = os.environ["KODE_MODEL"]

        return config

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.

        Args:
            key: Configuration key (supports dot notation, e.g., "models.main")
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value (runtime only).

        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        keys = key.split(".")
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value

    def get_all(self) -> Dict[str, Any]:
        """Get entire configuration."""
        return self._config.copy()

    def save_user_config(self) -> None:
        """Save current configuration to user config file."""
        user_config_path = Path.home() / ".kode.json"
        try:
            with open(user_config_path, "w") as f:
                json.dump(self._config, f, indent=2)
            print(f"Configuration saved to {user_config_path}")
        except Exception as e:
            print(f"Error saving user config: {e}")

    def save_project_config(self) -> None:
        """Save current configuration to project config file."""
        project_config_path = self.project_root / ".kode.json"
        try:
            with open(project_config_path, "w") as f:
                json.dump(self._config, f, indent=2)
            print(f"Configuration saved to {project_config_path}")
        except Exception as e:
            print(f"Error saving project config: {e}")

    def create_example_config(self, path: Optional[Path] = None) -> None:
        """
        Create an example configuration file.

        Args:
            path: Path to save example config (default: ./.kode.json.example)
        """
        if path is None:
            path = self.project_root / ".kode.json.example"

        example_config = {
            "models": {
                "main": "claude-sonnet-4-5",
                "task": "claude-sonnet-4-5",
                "quick": "gpt-4-turbo-preview",
            },
            "apiKeys": {
                "anthropic": "your-anthropic-api-key",
                "openai": "your-openai-api-key",
            },
            "verbose": False,
            "maxTokens": 4096,
            "temperature": 0.7,
        }

        try:
            with open(path, "w") as f:
                json.dump(example_config, f, indent=2)
            print(f"Example configuration created at {path}")
        except Exception as e:
            print(f"Error creating example config: {e}")