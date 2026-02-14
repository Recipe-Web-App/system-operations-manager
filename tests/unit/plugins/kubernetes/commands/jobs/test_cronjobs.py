"""Unit tests for Kubernetes cronjob commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.plugins.kubernetes.commands.jobs import (
    register_job_commands,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestCronJobCommands:
    """Tests for cronjob commands."""

    @pytest.fixture
    def app(self, get_job_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with cronjob commands."""
        app = typer.Typer()
        register_job_commands(app, get_job_manager)
        return app

    def test_list_cronjobs(
        self, cli_runner: CliRunner, app: typer.Typer, mock_job_manager: MagicMock
    ) -> None:
        """list should list cronjobs."""
        mock_job_manager.list_cron_jobs.return_value = []

        result = cli_runner.invoke(app, ["cronjobs", "list"])

        assert result.exit_code == 0
        mock_job_manager.list_cron_jobs.assert_called_once_with(
            namespace=None, all_namespaces=False, label_selector=None
        )

    def test_get_cronjob(
        self, cli_runner: CliRunner, app: typer.Typer, mock_job_manager: MagicMock
    ) -> None:
        """get should retrieve a cronjob."""
        result = cli_runner.invoke(app, ["cronjobs", "get", "test-cronjob"])

        assert result.exit_code == 0
        mock_job_manager.get_cron_job.assert_called_once_with("test-cronjob", namespace=None)

    def test_create_cronjob(
        self, cli_runner: CliRunner, app: typer.Typer, mock_job_manager: MagicMock
    ) -> None:
        """create should create a cronjob."""
        result = cli_runner.invoke(
            app,
            [
                "cronjobs",
                "create",
                "test-cronjob",
                "--image",
                "busybox",
                "--schedule",
                "*/5 * * * *",
                "--command",
                "echo",
                "--command",
                "hello",
            ],
        )

        assert result.exit_code == 0
        mock_job_manager.create_cron_job.assert_called_once()
        call_args = mock_job_manager.create_cron_job.call_args
        assert call_args.args[0] == "test-cronjob"
        assert call_args.kwargs["image"] == "busybox"
        assert call_args.kwargs["schedule"] == "*/5 * * * *"
        assert call_args.kwargs["command"] == ["echo", "hello"]

    def test_update_cronjob_schedule(
        self, cli_runner: CliRunner, app: typer.Typer, mock_job_manager: MagicMock
    ) -> None:
        """update should update cronjob schedule."""
        result = cli_runner.invoke(
            app,
            ["cronjobs", "update", "test-cronjob", "--schedule", "0 * * * *"],
        )

        assert result.exit_code == 0
        mock_job_manager.update_cron_job.assert_called_once()
        call_args = mock_job_manager.update_cron_job.call_args
        assert call_args.args[0] == "test-cronjob"
        assert call_args.kwargs["schedule"] == "0 * * * *"

    def test_update_cronjob_suspend(
        self, cli_runner: CliRunner, app: typer.Typer, mock_job_manager: MagicMock
    ) -> None:
        """update should suspend/unsuspend cronjob."""
        result = cli_runner.invoke(app, ["cronjobs", "update", "test-cronjob", "--suspend"])

        assert result.exit_code == 0
        mock_job_manager.update_cron_job.assert_called_once()
        call_args = mock_job_manager.update_cron_job.call_args
        assert call_args.kwargs["suspend"] is True

    def test_delete_cronjob_force(
        self, cli_runner: CliRunner, app: typer.Typer, mock_job_manager: MagicMock
    ) -> None:
        """delete with --force should delete without confirmation."""
        result = cli_runner.invoke(app, ["cronjobs", "delete", "test-cronjob", "--force"])

        assert result.exit_code == 0
        mock_job_manager.delete_cron_job.assert_called_once_with("test-cronjob", namespace=None)
        assert "deleted" in result.stdout.lower()

    def test_suspend_cronjob(
        self, cli_runner: CliRunner, app: typer.Typer, mock_job_manager: MagicMock
    ) -> None:
        """suspend should suspend a cronjob."""
        result = cli_runner.invoke(app, ["cronjobs", "suspend", "test-cronjob"])

        assert result.exit_code == 0
        mock_job_manager.suspend_cron_job.assert_called_once_with("test-cronjob", namespace=None)
        assert "suspended" in result.stdout.lower()

    def test_resume_cronjob(
        self, cli_runner: CliRunner, app: typer.Typer, mock_job_manager: MagicMock
    ) -> None:
        """resume should resume a cronjob."""
        result = cli_runner.invoke(app, ["cronjobs", "resume", "test-cronjob"])

        assert result.exit_code == 0
        mock_job_manager.resume_cron_job.assert_called_once_with("test-cronjob", namespace=None)
        assert "resumed" in result.stdout.lower()
