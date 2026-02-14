"""Unit tests for Kubernetes logs command."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesNotFoundError,
)
from system_operations_manager.plugins.kubernetes.commands.streaming import (
    _parse_duration,
    register_streaming_commands,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestLogsCommand:
    """Tests for the logs CLI command."""

    @pytest.fixture
    def app(self, get_streaming_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with streaming commands."""
        app = typer.Typer()
        register_streaming_commands(app, get_streaming_manager)
        return app

    def test_logs_static_default(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_streaming_manager: MagicMock,
    ) -> None:
        """logs should display static pod logs."""
        mock_streaming_manager.stream_logs.return_value = "Log line 1\nLog line 2"

        result = cli_runner.invoke(app, ["logs", "my-pod"])

        assert result.exit_code == 0
        mock_streaming_manager.stream_logs.assert_called_once_with(
            "my-pod",
            None,
            container=None,
            follow=False,
            tail_lines=None,
            previous=False,
            timestamps=False,
            since_seconds=None,
        )

    def test_logs_with_follow(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_streaming_manager: MagicMock,
    ) -> None:
        """logs --follow should stream logs."""
        mock_streaming_manager.stream_logs.return_value = iter(["line1\n", "line2\n"])

        result = cli_runner.invoke(app, ["logs", "my-pod", "--follow"])

        assert result.exit_code == 0
        call_kwargs = mock_streaming_manager.stream_logs.call_args
        assert call_kwargs[1]["follow"] is True

    def test_logs_with_all_options(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_streaming_manager: MagicMock,
    ) -> None:
        """logs should pass all options to the manager."""
        mock_streaming_manager.stream_logs.return_value = "filtered logs"

        result = cli_runner.invoke(
            app,
            [
                "logs",
                "my-pod",
                "-n",
                "production",
                "-c",
                "sidecar",
                "--tail",
                "100",
                "--previous",
                "--timestamps",
                "--since",
                "1h",
            ],
        )

        assert result.exit_code == 0
        mock_streaming_manager.stream_logs.assert_called_once_with(
            "my-pod",
            "production",
            container="sidecar",
            follow=False,
            tail_lines=100,
            previous=True,
            timestamps=True,
            since_seconds=3600,
        )

    def test_logs_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_streaming_manager: MagicMock,
    ) -> None:
        """logs should handle KubernetesError."""
        mock_streaming_manager.stream_logs.side_effect = KubernetesNotFoundError(
            resource_type="Pod", resource_name="missing-pod"
        )

        result = cli_runner.invoke(app, ["logs", "missing-pod"])

        assert result.exit_code == 1

    def test_logs_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_streaming_manager: MagicMock,
    ) -> None:
        """logs -n should pass namespace."""
        mock_streaming_manager.stream_logs.return_value = "logs"

        result = cli_runner.invoke(app, ["logs", "my-pod", "-n", "staging"])

        assert result.exit_code == 0
        call_args = mock_streaming_manager.stream_logs.call_args
        assert call_args[0][1] == "staging"


@pytest.mark.unit
class TestParseDuration:
    """Tests for the _parse_duration helper."""

    def test_parse_hours(self) -> None:
        assert _parse_duration("1h") == 3600

    def test_parse_minutes(self) -> None:
        assert _parse_duration("30m") == 1800

    def test_parse_seconds(self) -> None:
        assert _parse_duration("5s") == 5

    def test_parse_combined(self) -> None:
        assert _parse_duration("1h30m") == 5400

    def test_parse_full(self) -> None:
        assert _parse_duration("2h15m30s") == 8130

    def test_parse_invalid(self) -> None:
        with pytest.raises(typer.BadParameter):
            _parse_duration("invalid")

    def test_parse_empty(self) -> None:
        with pytest.raises(typer.BadParameter):
            _parse_duration("")
