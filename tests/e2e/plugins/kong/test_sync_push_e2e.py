"""E2E tests for sync push CLI command.

These tests verify the CLI workflow for sync push.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from system_operations_manager.cli.main import app


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.mark.e2e
class TestSyncPushE2E:
    """E2E tests for sync push command."""

    def test_sync_push_command_exists(self, cli_runner: CliRunner) -> None:
        """Verify sync push command is registered."""
        result = cli_runner.invoke(app, ["kong", "sync", "push", "--help"])

        # Command should be found and show help
        assert result.exit_code == 0
        assert "Push Gateway configuration to Konnect" in result.stdout

    def test_sync_push_dry_run_option(self, cli_runner: CliRunner) -> None:
        """Verify --dry-run option is available."""
        result = cli_runner.invoke(app, ["kong", "sync", "push", "--help"])

        assert "--dry-run" in result.stdout
        assert "-n" in result.stdout  # Short option

    def test_sync_push_type_option(self, cli_runner: CliRunner) -> None:
        """Verify --type option is available."""
        result = cli_runner.invoke(app, ["kong", "sync", "push", "--help"])

        assert "--type" in result.stdout
        assert "-t" in result.stdout  # Short option
        assert "services" in result.stdout or "routes" in result.stdout

    def test_sync_push_force_option(self, cli_runner: CliRunner) -> None:
        """Verify --force option is available."""
        result = cli_runner.invoke(app, ["kong", "sync", "push", "--help"])

        assert "--force" in result.stdout
        assert "-f" in result.stdout  # Short option

    def test_sync_push_invalid_type_shows_error(self, cli_runner: CliRunner) -> None:
        """Verify invalid --type value shows error or Konnect not configured."""
        result = cli_runner.invoke(app, ["kong", "sync", "push", "--type", "invalid_type"])

        assert result.exit_code == 1
        # Either Konnect not configured (checked first) or invalid entity type
        assert "Invalid entity type" in result.stdout or "Konnect not configured" in result.stdout

    def test_sync_push_dry_run_with_no_konnect(self, cli_runner: CliRunner) -> None:
        """Verify proper message when Konnect is not configured."""
        # This test depends on whether Konnect is configured in the test environment
        # It will either show "Konnect not configured" or proceed with the push
        result = cli_runner.invoke(app, ["kong", "sync", "push", "--dry-run"])

        # Command should either succeed or fail gracefully
        assert result.exit_code in [0, 1]
        if result.exit_code == 1:
            # Could fail due to Konnect not configured or Kong Gateway connection error
            assert "Konnect" in result.stdout or "Kong" in result.stdout

    def test_sync_push_shows_examples_in_help(self, cli_runner: CliRunner) -> None:
        """Verify help text includes usage examples."""
        result = cli_runner.invoke(app, ["kong", "sync", "push", "--help"])

        assert result.exit_code == 0
        assert "Examples:" in result.stdout
        assert "ops kong sync push" in result.stdout

    def test_sync_status_command_exists(self, cli_runner: CliRunner) -> None:
        """Verify sync status command is still registered alongside push."""
        result = cli_runner.invoke(app, ["kong", "sync", "status", "--help"])

        # Status command should still work
        assert result.exit_code == 0
        assert "drift" in result.stdout.lower() or "status" in result.stdout.lower()

    def test_sync_subcommand_help(self, cli_runner: CliRunner) -> None:
        """Verify sync subcommand shows both status and push."""
        result = cli_runner.invoke(app, ["kong", "sync", "--help"])

        assert result.exit_code == 0
        assert "status" in result.stdout
        assert "push" in result.stdout
