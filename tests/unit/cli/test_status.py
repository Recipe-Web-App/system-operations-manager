"""Tests for cli/commands/status.py covering missing lines 53-59."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from system_operations_manager.cli.main import app
from system_operations_manager.core.config.models import PluginsConfig, SystemConfig


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def _make_config(
    environment: str = "development", plugins: list[str] | None = None
) -> SystemConfig:
    """Build a minimal SystemConfig for mocking."""
    enabled = plugins or ["core"]
    return SystemConfig(
        version="1.0",
        environment=environment,
        plugins=PluginsConfig(enabled=enabled),
    )


@pytest.mark.unit
class TestStatusCommandConfigBranches:
    """Targeted tests for the configuration-reporting section of status (lines 51-65)."""

    # ------------------------------------------------------------------
    # Line 54-57: config is truthy, verbose shows environment + plugins
    # ------------------------------------------------------------------

    def test_status_with_valid_config_non_verbose(self, runner: CliRunner) -> None:
        """Valid config: prints 'Configuration valid' line (non-verbose)."""
        mock_cfg = _make_config()
        with patch(
            "system_operations_manager.cli.commands.status.load_config", return_value=mock_cfg
        ):
            result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "Configuration valid" in result.stdout

    def test_status_with_valid_config_verbose_shows_environment(self, runner: CliRunner) -> None:
        """Verbose + valid config: lines 55-57 are executed (environment and plugins)."""
        mock_cfg = _make_config(environment="development", plugins=["core", "monitoring"])
        with patch(
            "system_operations_manager.cli.commands.status.load_config", return_value=mock_cfg
        ):
            result = runner.invoke(app, ["status", "--verbose"])
        assert result.exit_code == 0
        assert "Configuration valid" in result.stdout
        assert "Environment" in result.stdout or "development" in result.stdout
        assert "core" in result.stdout

    def test_status_with_valid_config_verbose_shows_plugins(self, runner: CliRunner) -> None:
        """Verbose mode prints the joined plugin list."""
        mock_cfg = _make_config(plugins=["core", "kubernetes"])
        with patch(
            "system_operations_manager.cli.commands.status.load_config", return_value=mock_cfg
        ):
            result = runner.invoke(app, ["status", "--verbose"])
        assert result.exit_code == 0
        assert "kubernetes" in result.stdout

    # ------------------------------------------------------------------
    # Lines 58-60: config is None (no file found)
    # ------------------------------------------------------------------

    def test_status_no_config_file_prints_warning(self, runner: CliRunner) -> None:
        """When load_config returns None the 'No configuration found' message appears."""
        with patch("system_operations_manager.cli.commands.status.load_config", return_value=None):
            result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "No configuration found" in result.stdout

    # ------------------------------------------------------------------
    # Lines 62-65: ValidationError / ValueError from load_config
    # ------------------------------------------------------------------

    def test_status_invalid_config_shows_error(self, runner: CliRunner) -> None:
        """When load_config raises ValueError the error message is printed."""
        with patch(
            "system_operations_manager.cli.commands.status.load_config",
            side_effect=ValueError("bad yaml"),
        ):
            result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "Configuration invalid" in result.stdout
        assert "bad yaml" in result.stdout

    def test_status_validation_error_shows_error(self, runner: CliRunner) -> None:
        """When load_config raises ValidationError the error section is printed."""
        # Build a real ValidationError from a Pydantic model.

        try:
            SystemConfig.model_validate({"environment": "invalid-env"})
        except ValidationError as exc:
            validation_exc = exc
        else:
            pytest.skip("Could not produce ValidationError for test setup")

        with patch(
            "system_operations_manager.cli.commands.status.load_config",
            side_effect=validation_exc,
        ):
            result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "Configuration invalid" in result.stdout
