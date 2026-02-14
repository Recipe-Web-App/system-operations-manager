"""Unit tests for Kubernetes port-forward command."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesNotFoundError,
)
from system_operations_manager.plugins.kubernetes.commands.streaming import (
    _parse_port_mappings,
    _parse_target,
    register_streaming_commands,
)


@pytest.mark.unit
class TestParseTarget:
    """Tests for the _parse_target helper."""

    def test_plain_pod_name(self) -> None:
        assert _parse_target("my-pod") == ("pod", "my-pod")

    def test_pod_prefix(self) -> None:
        assert _parse_target("pod/my-pod") == ("pod", "my-pod")

    def test_svc_prefix(self) -> None:
        assert _parse_target("svc/my-service") == ("svc", "my-service")

    def test_service_prefix(self) -> None:
        assert _parse_target("service/my-service") == ("svc", "my-service")


@pytest.mark.unit
class TestParsePortMappings:
    """Tests for the _parse_port_mappings helper."""

    def test_single_port(self) -> None:
        assert _parse_port_mappings(["80"]) == [(80, 80)]

    def test_local_remote(self) -> None:
        assert _parse_port_mappings(["8080:80"]) == [(8080, 80)]

    def test_multiple_ports(self) -> None:
        assert _parse_port_mappings(["8080:80", "9090:9090"]) == [
            (8080, 80),
            (9090, 9090),
        ]

    def test_invalid_port(self) -> None:
        with pytest.raises(typer.BadParameter):
            _parse_port_mappings(["invalid"])

    def test_empty_mapping(self) -> None:
        assert _parse_port_mappings([]) == []


@pytest.mark.unit
@pytest.mark.kubernetes
class TestPortForwardCommand:
    """Tests for the port-forward CLI command."""

    @pytest.fixture
    def app(self, get_streaming_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with streaming commands."""
        app = typer.Typer()
        register_streaming_commands(app, get_streaming_manager)
        return app

    @patch("system_operations_manager.plugins.kubernetes.commands.streaming._run_port_forward")
    def test_port_forward_pod(
        self,
        mock_run_pf: MagicMock,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_streaming_manager: MagicMock,
    ) -> None:
        """port-forward should forward to a pod."""
        mock_pf = MagicMock()
        mock_streaming_manager.port_forward.return_value = mock_pf

        result = cli_runner.invoke(app, ["port-forward", "my-pod", "8080:80"])

        assert result.exit_code == 0
        mock_streaming_manager.port_forward.assert_called_once_with(
            "my-pod", None, ports=[(8080, 80)]
        )
        mock_run_pf.assert_called_once_with(mock_pf, [(8080, 80)], "127.0.0.1")

    @patch("system_operations_manager.plugins.kubernetes.commands.streaming._run_port_forward")
    def test_port_forward_service(
        self,
        mock_run_pf: MagicMock,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_streaming_manager: MagicMock,
    ) -> None:
        """port-forward svc/ should resolve service to pod."""
        mock_streaming_manager.resolve_service_to_pod.return_value = "nginx-abc123"
        mock_pf = MagicMock()
        mock_streaming_manager.port_forward.return_value = mock_pf

        result = cli_runner.invoke(app, ["port-forward", "svc/my-service", "8080:80"])

        assert result.exit_code == 0
        mock_streaming_manager.resolve_service_to_pod.assert_called_once_with("my-service", None)
        mock_streaming_manager.port_forward.assert_called_once_with(
            "nginx-abc123", None, ports=[(8080, 80)]
        )

    @patch("system_operations_manager.plugins.kubernetes.commands.streaming._run_port_forward")
    def test_port_forward_with_namespace(
        self,
        mock_run_pf: MagicMock,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_streaming_manager: MagicMock,
    ) -> None:
        """port-forward -n should pass namespace."""
        mock_streaming_manager.port_forward.return_value = MagicMock()

        result = cli_runner.invoke(app, ["port-forward", "my-pod", "8080:80", "-n", "staging"])

        assert result.exit_code == 0
        call_args = mock_streaming_manager.port_forward.call_args
        assert call_args[0][1] == "staging"

    @patch("system_operations_manager.plugins.kubernetes.commands.streaming._run_port_forward")
    def test_port_forward_custom_address(
        self,
        mock_run_pf: MagicMock,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_streaming_manager: MagicMock,
    ) -> None:
        """port-forward --address should bind to custom address."""
        mock_streaming_manager.port_forward.return_value = MagicMock()

        result = cli_runner.invoke(
            app,
            ["port-forward", "my-pod", "8080:80", "--address", "0.0.0.0"],
        )

        assert result.exit_code == 0
        mock_run_pf.assert_called_once()
        assert mock_run_pf.call_args[0][2] == "0.0.0.0"

    @patch("system_operations_manager.plugins.kubernetes.commands.streaming._run_port_forward")
    def test_port_forward_multiple_ports(
        self,
        mock_run_pf: MagicMock,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_streaming_manager: MagicMock,
    ) -> None:
        """port-forward should handle multiple port mappings."""
        mock_streaming_manager.port_forward.return_value = MagicMock()

        result = cli_runner.invoke(app, ["port-forward", "my-pod", "8080:80", "9090:9090"])

        assert result.exit_code == 0
        call_kwargs = mock_streaming_manager.port_forward.call_args[1]
        assert call_kwargs["ports"] == [(8080, 80), (9090, 9090)]

    def test_port_forward_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_streaming_manager: MagicMock,
    ) -> None:
        """port-forward should handle KubernetesError."""
        mock_streaming_manager.port_forward.side_effect = KubernetesNotFoundError(
            resource_type="Pod", resource_name="missing-pod"
        )

        result = cli_runner.invoke(app, ["port-forward", "missing-pod", "8080:80"])

        assert result.exit_code == 1
