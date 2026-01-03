"""Tests for main CLI module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from system_operations_manager.cli.main import app


class TestCLIMain:
    """Test main CLI entry point."""

    @pytest.mark.unit
    def test_help_option(self, cli_runner: CliRunner) -> None:
        """Test --help option displays help text."""
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "System Control CLI" in result.stdout

    @pytest.mark.unit
    def test_version_option(self, cli_runner: CliRunner) -> None:
        """Test --version option displays version."""
        result = cli_runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "ops version" in result.stdout

    @pytest.mark.unit
    def test_verbose_flag(self, cli_runner: CliRunner) -> None:
        """Test --verbose flag is accepted."""
        result = cli_runner.invoke(app, ["--verbose", "--help"])
        assert result.exit_code == 0


class TestStatusCommand:
    """Test status command."""

    @pytest.mark.unit
    def test_status_runs(self, cli_runner: CliRunner) -> None:
        """Test status command executes successfully."""
        result = cli_runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "System Control Status" in result.stdout

    @pytest.mark.unit
    def test_status_verbose(self, cli_runner: CliRunner) -> None:
        """Test status command with verbose flag."""
        result = cli_runner.invoke(app, ["status", "--verbose"])
        assert result.exit_code == 0
        assert "Architecture" in result.stdout


class TestInitCommand:
    """Test init command."""

    @pytest.mark.unit
    def test_init_creates_config(self, cli_runner: CliRunner, temp_dir: Path) -> None:
        """Test init command creates configuration file."""
        config_dir = temp_dir / "config"
        config_file = config_dir / "config.yaml"

        with (
            patch("system_operations_manager.cli.commands.init.CONFIG_DIR", config_dir),
            patch("system_operations_manager.cli.commands.init.CONFIG_FILE", config_file),
        ):
            result = cli_runner.invoke(app, ["init"])
            assert result.exit_code == 0
            assert "initialized successfully" in result.stdout

    @pytest.mark.unit
    def test_init_existing_config_fails(self, cli_runner: CliRunner, temp_dir: Path) -> None:
        """Test init fails if config already exists."""
        config_dir = temp_dir / "config"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text("version: 1.0")

        with (
            patch("system_operations_manager.cli.commands.init.CONFIG_DIR", config_dir),
            patch("system_operations_manager.cli.commands.init.CONFIG_FILE", config_file),
        ):
            result = cli_runner.invoke(app, ["init"])
            assert result.exit_code == 1
            assert "already exists" in result.stdout

    @pytest.mark.unit
    def test_init_force_overwrites(self, cli_runner: CliRunner, temp_dir: Path) -> None:
        """Test init --force overwrites existing config."""
        config_dir = temp_dir / "config"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text("version: old")

        with (
            patch("system_operations_manager.cli.commands.init.CONFIG_DIR", config_dir),
            patch("system_operations_manager.cli.commands.init.CONFIG_FILE", config_file),
        ):
            result = cli_runner.invoke(app, ["init", "--force"])
            assert result.exit_code == 0
            assert "initialized successfully" in result.stdout
