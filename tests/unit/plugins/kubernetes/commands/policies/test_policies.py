"""Unit tests for Kyverno namespaced Policy commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesNotFoundError,
)
from system_operations_manager.plugins.kubernetes.commands.policies import (
    register_policy_commands,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestPolicyCommands:
    """Tests for Kyverno namespaced Policy commands."""

    @pytest.fixture
    def app(self, get_kyverno_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with policy commands."""
        app = typer.Typer()
        register_policy_commands(app, get_kyverno_manager)
        return app

    def test_list_policies(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """list should list Policies."""
        mock_kyverno_manager.list_policies.return_value = []

        result = cli_runner.invoke(app, ["policies", "list"])

        assert result.exit_code == 0
        mock_kyverno_manager.list_policies.assert_called_once_with(
            namespace=None,
            label_selector=None,
        )

    def test_list_policies_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """list with --namespace should pass the namespace."""
        result = cli_runner.invoke(app, ["policies", "list", "-n", "production"])

        assert result.exit_code == 0
        mock_kyverno_manager.list_policies.assert_called_once_with(
            namespace="production",
            label_selector=None,
        )

    def test_get_policy(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """get should retrieve a Policy."""
        result = cli_runner.invoke(app, ["policies", "get", "restrict-images"])

        assert result.exit_code == 0
        mock_kyverno_manager.get_policy.assert_called_once_with("restrict-images", namespace=None)

    def test_get_policy_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """get with --namespace should pass namespace."""
        result = cli_runner.invoke(app, ["policies", "get", "restrict-images", "-n", "production"])

        assert result.exit_code == 0
        mock_kyverno_manager.get_policy.assert_called_once_with(
            "restrict-images", namespace="production"
        )

    def test_create_policy(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """create should create a Policy."""
        result = cli_runner.invoke(
            app,
            [
                "policies",
                "create",
                "restrict-images",
                "-n",
                "production",
                "--action",
                "Enforce",
            ],
        )

        assert result.exit_code == 0
        mock_kyverno_manager.create_policy.assert_called_once()
        call_kwargs = mock_kyverno_manager.create_policy.call_args
        assert call_kwargs.args[0] == "restrict-images"
        assert call_kwargs.kwargs["namespace"] == "production"
        assert call_kwargs.kwargs["validation_failure_action"] == "Enforce"

    def test_delete_policy_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """delete with --force should delete without confirmation."""
        result = cli_runner.invoke(app, ["policies", "delete", "restrict-images", "--force"])

        assert result.exit_code == 0
        mock_kyverno_manager.delete_policy.assert_called_once_with(
            "restrict-images", namespace=None
        )
        assert "deleted" in result.stdout.lower()

    def test_delete_policy_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """delete with --namespace should pass namespace."""
        result = cli_runner.invoke(
            app,
            ["policies", "delete", "restrict-images", "-n", "production", "--force"],
        )

        assert result.exit_code == 0
        mock_kyverno_manager.delete_policy.assert_called_once_with(
            "restrict-images", namespace="production"
        )

    def test_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """should handle KubernetesError appropriately."""
        mock_kyverno_manager.get_policy.side_effect = KubernetesNotFoundError(
            resource_type="Policy", resource_name="nonexistent"
        )

        result = cli_runner.invoke(app, ["policies", "get", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()
