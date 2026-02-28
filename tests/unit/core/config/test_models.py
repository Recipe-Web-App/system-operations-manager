"""Unit tests for core config models."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from system_operations_manager.core.config.models import (
    PluginsConfig,
    ProfileConfig,
    SystemConfig,
    load_config,
    load_raw_config,
)


@pytest.mark.unit
class TestProfileConfig:
    """Tests for ProfileConfig model."""

    def test_default_editor_optional(self) -> None:
        """ProfileConfig default_editor field is optional and defaults to None."""
        config = ProfileConfig()
        assert config.default_editor is None

    def test_default_editor_accepts_string(self) -> None:
        """ProfileConfig default_editor accepts a string value."""
        config = ProfileConfig(default_editor="code --wait")
        assert config.default_editor == "code --wait"

    def test_default_editor_accepts_various_editors(self) -> None:
        """ProfileConfig default_editor accepts various editor commands."""
        config_vim = ProfileConfig(default_editor="vim")
        assert config_vim.default_editor == "vim"

        config_nano = ProfileConfig(default_editor="nano")
        assert config_nano.default_editor == "nano"

        config_vscode = ProfileConfig(default_editor="code --wait")
        assert config_vscode.default_editor == "code --wait"

        config_subl = ProfileConfig(default_editor="subl -w")
        assert config_subl.default_editor == "subl -w"

    def test_profile_config_debug_default(self) -> None:
        """ProfileConfig debug defaults to False."""
        config = ProfileConfig()
        assert config.debug is False

    def test_profile_config_log_level_default(self) -> None:
        """ProfileConfig log_level defaults to INFO."""
        config = ProfileConfig()
        assert config.log_level == "INFO"

    def test_profile_config_combined_settings(self) -> None:
        """ProfileConfig accepts combined settings."""
        config = ProfileConfig(
            debug=True,
            log_level="DEBUG",
            default_editor="vim",
        )
        assert config.debug is True
        assert config.log_level == "DEBUG"
        assert config.default_editor == "vim"

    def test_validate_log_level_raises_on_invalid(self) -> None:
        """ProfileConfig.validate_log_level raises ValueError for unknown log levels."""
        with pytest.raises(ValueError, match="Invalid log_level"):
            ProfileConfig(log_level="VERBOSE")

    def test_validate_log_level_normalises_to_upper(self) -> None:
        """ProfileConfig.validate_log_level normalises lowercase input."""
        config = ProfileConfig(log_level="debug")
        assert config.log_level == "DEBUG"

    def test_validate_log_level_accepts_all_valid_levels(self) -> None:
        """ProfileConfig.validate_log_level accepts every supported level."""
        for level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            config = ProfileConfig(log_level=level)
            assert config.log_level == level


@pytest.mark.unit
class TestPluginsConfig:
    """Tests for PluginsConfig model."""

    def test_default_enabled_list(self) -> None:
        """PluginsConfig.enabled defaults to ['core']."""
        config = PluginsConfig()
        assert config.enabled == ["core"]

    def test_custom_enabled_list(self) -> None:
        """PluginsConfig.enabled accepts a custom list."""
        config = PluginsConfig(enabled=["core", "kubernetes"])
        assert config.enabled == ["core", "kubernetes"]


@pytest.mark.unit
class TestSystemConfig:
    """Tests for SystemConfig model."""

    def test_defaults(self) -> None:
        """SystemConfig has expected default values."""
        config = SystemConfig()
        assert config.version == "1.0"
        assert config.environment == "development"
        assert "default" in config.profiles
        assert isinstance(config.plugins, PluginsConfig)

    def test_validate_environment_raises_on_invalid(self) -> None:
        """SystemConfig.validate_environment raises ValueError for unknown environments."""
        with pytest.raises(ValueError, match="Invalid environment"):
            SystemConfig(environment="local")

    def test_validate_environment_accepts_valid_values(self) -> None:
        """SystemConfig.validate_environment accepts all supported environments."""
        for env in ("development", "staging", "production"):
            config = SystemConfig(environment=env)
            assert config.environment == env

    def test_to_yaml_returns_string_with_header(self) -> None:
        """SystemConfig.to_yaml produces a YAML string prefixed with a comment header."""
        config = SystemConfig()
        result = config.to_yaml()
        assert isinstance(result, str)
        assert "# System Control CLI Configuration" in result
        assert "version:" in result

    def test_to_yaml_contains_model_data(self) -> None:
        """SystemConfig.to_yaml embeds the model's data in the output."""
        config = SystemConfig(environment="staging")
        result = config.to_yaml()
        assert "staging" in result

    def test_to_yaml_header_present(self) -> None:
        """SystemConfig.to_yaml starts with the expected comment block."""
        config = SystemConfig()
        result = config.to_yaml()
        assert result.startswith("# System Control CLI Configuration")


@pytest.mark.unit
class TestLoadConfig:
    """Tests for load_config() function."""

    def test_returns_none_when_file_absent(self, tmp_path: Path) -> None:
        """load_config returns None when the config file does not exist."""
        missing = tmp_path / "nonexistent.yaml"
        result = load_config(missing)
        assert result is None

    def test_returns_system_config_for_valid_yaml(self, tmp_path: Path) -> None:
        """load_config parses a valid YAML file into a SystemConfig instance."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: '1.0'\nenvironment: staging\n")
        result = load_config(config_file)
        assert isinstance(result, SystemConfig)
        assert result.environment == "staging"

    def test_returns_system_config_for_empty_yaml(self, tmp_path: Path) -> None:
        """load_config returns a default SystemConfig for an empty YAML file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("")
        result = load_config(config_file)
        assert isinstance(result, SystemConfig)

    def test_raises_value_error_on_invalid_yaml(self, tmp_path: Path) -> None:
        """load_config raises ValueError when the file contains malformed YAML."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("key: [\nunclosed bracket")
        with pytest.raises(ValueError, match="Invalid YAML"):
            load_config(config_file)

    def test_uses_default_path_when_none_given(self) -> None:
        """load_config falls back to CONFIG_FILE when no path is supplied."""
        fake_path = MagicMock(spec=Path)
        fake_path.exists.return_value = False
        with patch("system_operations_manager.core.config.models.CONFIG_FILE", fake_path):
            result = load_config()
        assert result is None
        fake_path.exists.assert_called_once()


@pytest.mark.unit
class TestLoadRawConfig:
    """Tests for load_raw_config() function."""

    def test_returns_empty_dict_when_file_absent(self, tmp_path: Path) -> None:
        """load_raw_config returns {} when the config file does not exist."""
        missing = tmp_path / "nonexistent.yaml"
        result = load_raw_config(missing)
        assert result == {}

    def test_returns_dict_for_valid_yaml(self, tmp_path: Path) -> None:
        """load_raw_config returns the raw parsed dict for a valid YAML file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("key: value\nnested:\n  a: 1\n")
        result = load_raw_config(config_file)
        assert result == {"key": "value", "nested": {"a": 1}}

    def test_returns_empty_dict_for_empty_yaml(self, tmp_path: Path) -> None:
        """load_raw_config returns {} for an empty YAML file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("")
        result = load_raw_config(config_file)
        assert result == {}

    def test_returns_empty_dict_on_yaml_error(self, tmp_path: Path) -> None:
        """load_raw_config swallows YAML errors and returns {}."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("key: [\nunclosed bracket")
        result = load_raw_config(config_file)
        assert result == {}

    def test_uses_default_path_when_none_given(self) -> None:
        """load_raw_config falls back to CONFIG_FILE when no path is supplied."""
        fake_path = MagicMock(spec=Path)
        fake_path.exists.return_value = False
        with patch("system_operations_manager.core.config.models.CONFIG_FILE", fake_path):
            result = load_raw_config()
        assert result == {}
        fake_path.exists.assert_called_once()
