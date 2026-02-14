"""Unit tests for Kubernetes ingress commands."""

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
class TestIngressCommands:
    """Tests for ingress commands."""

    @pytest.fixture
    def app(self, get_networking_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with ingress commands."""
        app = typer.Typer()
        register_networking_commands(app, get_networking_manager)
        return app

    def test_list_ingresses(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """list should list ingresses."""
        mock_networking_manager.list_ingresses.return_value = []

        result = cli_runner.invoke(app, ["ingresses", "list"])

        assert result.exit_code == 0
        mock_networking_manager.list_ingresses.assert_called_once_with(
            namespace=None, all_namespaces=False, label_selector=None
        )

    def test_get_ingress(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """get should retrieve an ingress."""
        result = cli_runner.invoke(app, ["ingresses", "get", "test-ingress"])

        assert result.exit_code == 0
        mock_networking_manager.get_ingress.assert_called_once_with("test-ingress", namespace=None)

    def test_create_ingress(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """create should create an ingress."""
        rule_json = '{"host":"example.com","paths":[{"path":"/","path_type":"Prefix","service_name":"web","service_port":80}]}'

        result = cli_runner.invoke(
            app,
            [
                "ingresses",
                "create",
                "test-ingress",
                "--class-name",
                "nginx",
                "--rule",
                rule_json,
            ],
        )

        assert result.exit_code == 0
        mock_networking_manager.create_ingress.assert_called_once()
        call_args = mock_networking_manager.create_ingress.call_args
        assert call_args.args[0] == "test-ingress"
        assert call_args.kwargs["class_name"] == "nginx"
        assert len(call_args.kwargs["rules"]) == 1

    def test_update_ingress(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """update should update an ingress."""
        result = cli_runner.invoke(
            app, ["ingresses", "update", "test-ingress", "--class-name", "nginx"]
        )

        assert result.exit_code == 0
        mock_networking_manager.update_ingress.assert_called_once()
        call_args = mock_networking_manager.update_ingress.call_args
        assert call_args.args[0] == "test-ingress"
        assert call_args.kwargs["class_name"] == "nginx"

    def test_delete_ingress_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """delete with --force should delete without confirmation."""
        result = cli_runner.invoke(app, ["ingresses", "delete", "test-ingress", "--force"])

        assert result.exit_code == 0
        mock_networking_manager.delete_ingress.assert_called_once_with(
            "test-ingress", namespace=None
        )
        assert "deleted" in result.stdout.lower()

    def test_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """should handle KubernetesError appropriately."""
        mock_networking_manager.get_ingress.side_effect = KubernetesNotFoundError(
            resource_type="Ingress", resource_name="nonexistent"
        )

        result = cli_runner.invoke(app, ["ingresses", "get", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()
