"""Unit tests for core config models."""

from __future__ import annotations

import pytest

from system_operations_manager.core.config.models import ProfileConfig


class TestProfileConfig:
    """Tests for ProfileConfig model."""

    @pytest.mark.unit
    def test_default_editor_optional(self) -> None:
        """ProfileConfig default_editor field is optional and defaults to None."""
        config = ProfileConfig()
        assert config.default_editor is None

    @pytest.mark.unit
    def test_default_editor_accepts_string(self) -> None:
        """ProfileConfig default_editor accepts a string value."""
        config = ProfileConfig(default_editor="code --wait")
        assert config.default_editor == "code --wait"

    @pytest.mark.unit
    def test_default_editor_accepts_various_editors(self) -> None:
        """ProfileConfig default_editor accepts various editor commands."""
        # Test vim
        config_vim = ProfileConfig(default_editor="vim")
        assert config_vim.default_editor == "vim"

        # Test nano
        config_nano = ProfileConfig(default_editor="nano")
        assert config_nano.default_editor == "nano"

        # Test vscode with wait flag
        config_vscode = ProfileConfig(default_editor="code --wait")
        assert config_vscode.default_editor == "code --wait"

        # Test sublime with wait flag
        config_subl = ProfileConfig(default_editor="subl -w")
        assert config_subl.default_editor == "subl -w"

    @pytest.mark.unit
    def test_profile_config_debug_default(self) -> None:
        """ProfileConfig debug defaults to False."""
        config = ProfileConfig()
        assert config.debug is False

    @pytest.mark.unit
    def test_profile_config_log_level_default(self) -> None:
        """ProfileConfig log_level defaults to INFO."""
        config = ProfileConfig()
        assert config.log_level == "INFO"

    @pytest.mark.unit
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
