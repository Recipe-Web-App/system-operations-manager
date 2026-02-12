"""Unit tests for Kyverno ClusterPolicy commands."""

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
class TestClusterPolicyCommands:
    """Tests for Kyverno ClusterPolicy commands."""

    @pytest.fixture
    def app(self, get_kyverno_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with policy commands."""
        app = typer.Typer()
        register_policy_commands(app, get_kyverno_manager)
        return app

    def test_list_cluster_policies(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """list should list ClusterPolicies."""
        mock_kyverno_manager.list_cluster_policies.return_value = []

        result = cli_runner.invoke(app, ["cluster-policies", "list"])

        assert result.exit_code == 0
        mock_kyverno_manager.list_cluster_policies.assert_called_once_with(
            label_selector=None,
        )

    def test_list_cluster_policies_with_selector(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """list with --selector should pass label selector."""
        result = cli_runner.invoke(app, ["cluster-policies", "list", "-l", "app=security"])

        assert result.exit_code == 0
        mock_kyverno_manager.list_cluster_policies.assert_called_once_with(
            label_selector="app=security",
        )

    def test_get_cluster_policy(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """get should retrieve a ClusterPolicy."""
        result = cli_runner.invoke(app, ["cluster-policies", "get", "require-labels"])

        assert result.exit_code == 0
        mock_kyverno_manager.get_cluster_policy.assert_called_once_with("require-labels")

    def test_create_cluster_policy(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """create should create a ClusterPolicy."""
        result = cli_runner.invoke(
            app,
            [
                "cluster-policies",
                "create",
                "require-labels",
                "--action",
                "Enforce",
                "--no-background",
            ],
        )

        assert result.exit_code == 0
        mock_kyverno_manager.create_cluster_policy.assert_called_once()
        call_kwargs = mock_kyverno_manager.create_cluster_policy.call_args
        assert call_kwargs.args[0] == "require-labels"
        assert call_kwargs.kwargs["validation_failure_action"] == "Enforce"
        assert call_kwargs.kwargs["background"] is False

    def test_create_cluster_policy_with_rule(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """create with --rule should parse JSON rules."""
        rule_json = '{"name":"check","validate":{"message":"required"}}'
        result = cli_runner.invoke(
            app,
            ["cluster-policies", "create", "test-pol", "--rule", rule_json],
        )

        assert result.exit_code == 0
        call_kwargs = mock_kyverno_manager.create_cluster_policy.call_args
        assert call_kwargs.kwargs["rules"] == [
            {"name": "check", "validate": {"message": "required"}}
        ]

    def test_delete_cluster_policy_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """delete with --force should delete without confirmation."""
        result = cli_runner.invoke(app, ["cluster-policies", "delete", "require-labels", "--force"])

        assert result.exit_code == 0
        mock_kyverno_manager.delete_cluster_policy.assert_called_once_with("require-labels")
        assert "deleted" in result.stdout.lower()

    def test_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """should handle KubernetesError appropriately."""
        mock_kyverno_manager.get_cluster_policy.side_effect = KubernetesNotFoundError(
            resource_type="ClusterPolicy", resource_name="nonexistent"
        )

        result = cli_runner.invoke(app, ["cluster-policies", "get", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()
