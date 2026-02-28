"""Unit tests for Kubernetes job CLI commands (gap-fill coverage)."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesAuthError,
    KubernetesConnectionError,
    KubernetesError,
    KubernetesNotFoundError,
    KubernetesTimeoutError,
)
from system_operations_manager.plugins.kubernetes.commands.jobs import (
    _parse_labels,
    register_job_commands,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_job_manager() -> MagicMock:
    """Create a mock JobManager."""
    manager = MagicMock()

    manager.list_jobs.return_value = []
    manager.get_job.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "test-job",
            "namespace": "default",
            "completions": 1,
            "succeeded": 1,
        }
    )
    manager.create_job.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "test-job", "namespace": "default"}
    )
    manager.delete_job.return_value = None

    manager.list_cron_jobs.return_value = []
    manager.get_cron_job.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "test-cronjob",
            "namespace": "default",
            "schedule": "*/5 * * * *",
        }
    )
    manager.create_cron_job.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "test-cronjob", "namespace": "default"}
    )
    manager.update_cron_job.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "test-cronjob", "namespace": "default"}
    )
    manager.delete_cron_job.return_value = None
    manager.suspend_cron_job.return_value = None
    manager.resume_cron_job.return_value = None

    return manager


@pytest.fixture
def get_job_manager(mock_job_manager: MagicMock) -> Callable[[], MagicMock]:
    """Factory returning the mock JobManager."""
    return lambda: mock_job_manager


@pytest.fixture
def app(get_job_manager: Callable[[], MagicMock]) -> typer.Typer:
    """Create a test Typer app with job commands registered."""
    test_app = typer.Typer()
    register_job_commands(test_app, get_job_manager)
    return test_app


# =============================================================================
# Tests for _parse_labels helper
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestParseLabels:
    """Tests for the _parse_labels helper function in jobs module."""

    def test_returns_none_for_none_input(self) -> None:
        """Should return None when labels is None."""
        result = _parse_labels(None)
        assert result is None

    def test_returns_none_for_empty_list(self) -> None:
        """Should return None when labels is an empty list."""
        result = _parse_labels([])
        assert result is None

    def test_parses_valid_labels(self) -> None:
        """Should parse valid key=value labels into a dict."""
        result = _parse_labels(["app=nginx", "env=prod"])
        assert result == {"app": "nginx", "env": "prod"}

    def test_invalid_label_format_exits(self) -> None:
        """Should exit with code 1 when label has no = sign."""
        with pytest.raises(typer.Exit) as exc_info:
            _parse_labels(["invalid-label"])
        assert exc_info.value.exit_code == 1

    def test_invalid_label_no_separator(self) -> None:
        """Should exit when label string has no = separator."""
        with pytest.raises(typer.Exit):
            _parse_labels(["keyonly"])


# =============================================================================
# Tests for Job command error handling
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestJobCommandErrors:
    """Tests for error-path coverage in job commands."""

    def test_list_jobs_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_job_manager: MagicMock,
    ) -> None:
        """list_jobs should handle KubernetesError."""
        mock_job_manager.list_jobs.side_effect = KubernetesConnectionError("Cannot connect")

        result = cli_runner.invoke(app, ["jobs", "list"])

        assert result.exit_code == 1

    def test_create_job_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_job_manager: MagicMock,
    ) -> None:
        """create_job should handle KubernetesError."""
        mock_job_manager.create_job.side_effect = KubernetesError("Server error", status_code=500)

        result = cli_runner.invoke(
            app,
            ["jobs", "create", "test-job", "--image", "busybox"],
        )

        assert result.exit_code == 1

    def test_create_job_with_invalid_label(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_job_manager: MagicMock,
    ) -> None:
        """create_job should exit on invalid label format."""
        result = cli_runner.invoke(
            app,
            [
                "jobs",
                "create",
                "test-job",
                "--image",
                "busybox",
                "--label",
                "invalid-no-equals",
            ],
        )

        assert result.exit_code == 1
        mock_job_manager.create_job.assert_not_called()

    def test_delete_job_user_aborts(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_job_manager: MagicMock,
    ) -> None:
        """delete_job should abort when user does not confirm."""
        with patch(
            "system_operations_manager.plugins.kubernetes.commands.base.typer.confirm",
            return_value=False,
        ):
            result = cli_runner.invoke(app, ["jobs", "delete", "test-job"])

        assert result.exit_code != 0
        mock_job_manager.delete_job.assert_not_called()

    def test_delete_job_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_job_manager: MagicMock,
    ) -> None:
        """delete_job should handle KubernetesError after confirmation."""
        mock_job_manager.delete_job.side_effect = KubernetesNotFoundError(
            resource_type="Job", resource_name="test-job"
        )

        result = cli_runner.invoke(app, ["jobs", "delete", "test-job", "--force"])

        assert result.exit_code == 1


# =============================================================================
# Tests for CronJob command error handling
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestCronJobCommandErrors:
    """Tests for error-path coverage in cronjob commands."""

    def test_list_cronjobs_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_job_manager: MagicMock,
    ) -> None:
        """list_cronjobs should handle KubernetesError."""
        mock_job_manager.list_cron_jobs.side_effect = KubernetesConnectionError("Cannot connect")

        result = cli_runner.invoke(app, ["cronjobs", "list"])

        assert result.exit_code == 1

    def test_get_cronjob_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_job_manager: MagicMock,
    ) -> None:
        """get_cronjob should handle KubernetesError."""
        mock_job_manager.get_cron_job.side_effect = KubernetesNotFoundError(
            resource_type="CronJob", resource_name="missing-cron"
        )

        result = cli_runner.invoke(app, ["cronjobs", "get", "missing-cron"])

        assert result.exit_code == 1

    def test_create_cronjob_with_invalid_label(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_job_manager: MagicMock,
    ) -> None:
        """create_cronjob should exit on invalid label format."""
        result = cli_runner.invoke(
            app,
            [
                "cronjobs",
                "create",
                "test-cron",
                "--image",
                "busybox",
                "--schedule",
                "*/5 * * * *",
                "--label",
                "invalid-no-equals",
            ],
        )

        assert result.exit_code == 1
        mock_job_manager.create_cron_job.assert_not_called()

    def test_create_cronjob_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_job_manager: MagicMock,
    ) -> None:
        """create_cronjob should handle KubernetesError."""
        mock_job_manager.create_cron_job.side_effect = KubernetesError(
            "Server error", status_code=500
        )

        result = cli_runner.invoke(
            app,
            [
                "cronjobs",
                "create",
                "test-cron",
                "--image",
                "busybox",
                "--schedule",
                "*/5 * * * *",
            ],
        )

        assert result.exit_code == 1

    def test_update_cronjob_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_job_manager: MagicMock,
    ) -> None:
        """update_cronjob should handle KubernetesError."""
        mock_job_manager.update_cron_job.side_effect = KubernetesNotFoundError(
            resource_type="CronJob", resource_name="test-cron"
        )

        result = cli_runner.invoke(
            app,
            ["cronjobs", "update", "test-cron", "--schedule", "0 * * * *"],
        )

        assert result.exit_code == 1

    def test_delete_cronjob_user_aborts(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_job_manager: MagicMock,
    ) -> None:
        """delete_cronjob should abort when user does not confirm."""
        with patch(
            "system_operations_manager.plugins.kubernetes.commands.base.typer.confirm",
            return_value=False,
        ):
            result = cli_runner.invoke(app, ["cronjobs", "delete", "test-cron"])

        assert result.exit_code != 0
        mock_job_manager.delete_cron_job.assert_not_called()

    def test_delete_cronjob_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_job_manager: MagicMock,
    ) -> None:
        """delete_cronjob should handle KubernetesError."""
        mock_job_manager.delete_cron_job.side_effect = KubernetesNotFoundError(
            resource_type="CronJob", resource_name="test-cron"
        )

        result = cli_runner.invoke(app, ["cronjobs", "delete", "test-cron", "--force"])

        assert result.exit_code == 1

    def test_suspend_cronjob_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_job_manager: MagicMock,
    ) -> None:
        """suspend_cronjob should handle KubernetesError."""
        mock_job_manager.suspend_cron_job.side_effect = KubernetesNotFoundError(
            resource_type="CronJob", resource_name="test-cron"
        )

        result = cli_runner.invoke(app, ["cronjobs", "suspend", "test-cron"])

        assert result.exit_code == 1

    def test_resume_cronjob_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_job_manager: MagicMock,
    ) -> None:
        """resume_cronjob should handle KubernetesError."""
        mock_job_manager.resume_cron_job.side_effect = KubernetesTimeoutError("Operation timed out")

        result = cli_runner.invoke(app, ["cronjobs", "resume", "test-cron"])

        assert result.exit_code == 1

    def test_list_cronjobs_with_auth_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_job_manager: MagicMock,
    ) -> None:
        """list_cronjobs should handle KubernetesAuthError."""
        mock_job_manager.list_cron_jobs.side_effect = KubernetesAuthError(
            "Forbidden", status_code=403
        )

        result = cli_runner.invoke(app, ["cronjobs", "list"])

        assert result.exit_code == 1
