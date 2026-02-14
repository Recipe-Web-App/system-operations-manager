"""Unit tests for Kubernetes network policy commands."""

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
class TestNetworkPolicyCommands:
    """Tests for network policy commands."""

    @pytest.fixture
    def app(self, get_networking_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with network policy commands."""
        app = typer.Typer()
        register_networking_commands(app, get_networking_manager)
        return app

    def test_list_network_policies(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """list should list network policies."""
        mock_networking_manager.list_network_policies.return_value = []

        result = cli_runner.invoke(app, ["network-policies", "list"])

        assert result.exit_code == 0
        mock_networking_manager.list_network_policies.assert_called_once_with(
            namespace=None, all_namespaces=False, label_selector=None
        )

    def test_get_network_policy(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """get should retrieve a network policy."""
        result = cli_runner.invoke(app, ["network-policies", "get", "test-netpol"])

        assert result.exit_code == 0
        mock_networking_manager.get_network_policy.assert_called_once_with(
            "test-netpol", namespace=None
        )

    def test_create_network_policy(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """create should create a network policy."""
        result = cli_runner.invoke(
            app,
            [
                "network-policies",
                "create",
                "test-netpol",
                "--pod-selector",
                "app=web",
                "--policy-type",
                "Ingress",
            ],
        )

        assert result.exit_code == 0
        mock_networking_manager.create_network_policy.assert_called_once()
        call_args = mock_networking_manager.create_network_policy.call_args
        assert call_args.args[0] == "test-netpol"
        assert call_args.kwargs["pod_selector"] == {"app": "web"}
        assert call_args.kwargs["policy_types"] == ["Ingress"]

    def test_delete_network_policy_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """delete with --force should delete without confirmation."""
        result = cli_runner.invoke(app, ["network-policies", "delete", "test-netpol", "--force"])

        assert result.exit_code == 0
        mock_networking_manager.delete_network_policy.assert_called_once_with(
            "test-netpol", namespace=None
        )
        assert "deleted" in result.stdout.lower()

    def test_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """should handle KubernetesError appropriately."""
        mock_networking_manager.get_network_policy.side_effect = KubernetesNotFoundError(
            resource_type="NetworkPolicy", resource_name="nonexistent"
        )

        result = cli_runner.invoke(app, ["network-policies", "get", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()
