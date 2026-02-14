"""Unit tests for ArgoCD sync commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.plugins.kubernetes.commands.argocd import (
    register_argocd_commands,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestSyncCommands:
    """Tests for ArgoCD sync-related commands."""

    @pytest.fixture
    def app(self, get_argocd_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with argocd commands."""
        app = typer.Typer()
        register_argocd_commands(app, get_argocd_manager)
        return app

    def test_sync_application(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """sync should trigger application sync."""
        result = cli_runner.invoke(app, ["argocd", "app", "sync", "my-app"])

        assert result.exit_code == 0
        mock_argocd_manager.sync_application.assert_called_once_with(
            "my-app",
            namespace=None,
            revision=None,
            prune=False,
            dry_run=False,
        )

    def test_sync_with_revision(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """sync with --revision should pass revision."""
        result = cli_runner.invoke(app, ["argocd", "app", "sync", "my-app", "--revision", "v1.2.3"])

        assert result.exit_code == 0
        call_kwargs = mock_argocd_manager.sync_application.call_args
        assert call_kwargs.kwargs["revision"] == "v1.2.3"

    def test_sync_with_prune(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """sync with --prune should enable pruning."""
        result = cli_runner.invoke(app, ["argocd", "app", "sync", "my-app", "--prune"])

        assert result.exit_code == 0
        call_kwargs = mock_argocd_manager.sync_application.call_args
        assert call_kwargs.kwargs["prune"] is True

    def test_sync_with_dry_run(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """sync with --dry-run should enable dry-run mode."""
        result = cli_runner.invoke(app, ["argocd", "app", "sync", "my-app", "--dry-run"])

        assert result.exit_code == 0
        call_kwargs = mock_argocd_manager.sync_application.call_args
        assert call_kwargs.kwargs["dry_run"] is True

    def test_rollback_application(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """rollback should trigger application rollback."""
        result = cli_runner.invoke(app, ["argocd", "app", "rollback", "my-app"])

        assert result.exit_code == 0
        mock_argocd_manager.rollback_application.assert_called_once_with(
            "my-app",
            namespace=None,
            revision_id=0,
        )

    def test_rollback_with_revision_id(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """rollback with --revision-id should pass revision ID."""
        result = cli_runner.invoke(
            app, ["argocd", "app", "rollback", "my-app", "--revision-id", "2"]
        )

        assert result.exit_code == 0
        call_kwargs = mock_argocd_manager.rollback_application.call_args
        assert call_kwargs.kwargs["revision_id"] == 2

    def test_application_health(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """health should show application health."""
        result = cli_runner.invoke(app, ["argocd", "app", "health", "my-app"])

        assert result.exit_code == 0
        mock_argocd_manager.get_application_health.assert_called_once_with("my-app", namespace=None)

    def test_application_diff(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_argocd_manager: MagicMock,
    ) -> None:
        """diff should show application diff."""
        result = cli_runner.invoke(app, ["argocd", "app", "diff", "my-app"])

        assert result.exit_code == 0
        mock_argocd_manager.diff_application.assert_called_once_with("my-app", namespace=None)
