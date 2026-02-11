"""Unit tests for Kubernetes service commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesNotFoundError,
)
from system_operations_manager.plugins.kubernetes.commands.networking import (
    register_networking_commands,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestServiceCommands:
    """Tests for service commands."""

    @pytest.fixture
    def app(self, get_networking_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with service commands."""
        app = typer.Typer()
        register_networking_commands(app, get_networking_manager)
        return app

    def test_list_services(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """list should list services."""
        mock_networking_manager.list_services.return_value = []

        result = cli_runner.invoke(app, ["services", "list"])

        assert result.exit_code == 0
        mock_networking_manager.list_services.assert_called_once_with(
            namespace=None, all_namespaces=False, label_selector=None
        )

    def test_get_service(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """get should retrieve a service."""
        result = cli_runner.invoke(app, ["services", "get", "test-service"])

        assert result.exit_code == 0
        mock_networking_manager.get_service.assert_called_once_with("test-service", namespace=None)

    def test_create_service(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """create should create a service."""
        result = cli_runner.invoke(
            app,
            [
                "services",
                "create",
                "test-service",
                "--type",
                "ClusterIP",
                "--port",
                "80:8080/TCP",
                "--selector",
                "app=web",
            ],
        )

        assert result.exit_code == 0
        mock_networking_manager.create_service.assert_called_once()
        call_args = mock_networking_manager.create_service.call_args
        assert call_args.args[0] == "test-service"
        assert call_args.kwargs["type"] == "ClusterIP"
        assert call_args.kwargs["selector"] == {"app": "web"}
        assert call_args.kwargs["ports"] == [{"port": 80, "target_port": 8080, "protocol": "TCP"}]

    def test_update_service(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """update should update a service."""
        result = cli_runner.invoke(
            app, ["services", "update", "test-service", "--type", "LoadBalancer"]
        )

        assert result.exit_code == 0
        mock_networking_manager.update_service.assert_called_once()
        call_args = mock_networking_manager.update_service.call_args
        assert call_args.args[0] == "test-service"
        assert call_args.kwargs["type"] == "LoadBalancer"

    def test_delete_service_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """delete with --force should delete without confirmation."""
        result = cli_runner.invoke(app, ["services", "delete", "test-service", "--force"])

        assert result.exit_code == 0
        mock_networking_manager.delete_service.assert_called_once_with(
            "test-service", namespace=None
        )
        assert "deleted" in result.stdout.lower()

    def test_output_json(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """should accept output format parameter."""
        result = cli_runner.invoke(app, ["services", "get", "test-service", "-o", "json"])

        assert result.exit_code == 0
        mock_networking_manager.get_service.assert_called_once()

    def test_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """should handle KubernetesError appropriately."""
        mock_networking_manager.get_service.side_effect = KubernetesNotFoundError(
            resource_type="Service", resource_name="nonexistent"
        )

        result = cli_runner.invoke(app, ["services", "get", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()
