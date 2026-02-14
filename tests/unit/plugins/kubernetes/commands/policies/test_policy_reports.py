"""Unit tests for Kyverno PolicyReport and ClusterPolicyReport commands."""

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
class TestClusterPolicyReportCommands:
    """Tests for Kyverno ClusterPolicyReport commands."""

    @pytest.fixture
    def app(self, get_kyverno_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with policy commands."""
        app = typer.Typer()
        register_policy_commands(app, get_kyverno_manager)
        return app

    def test_list_cluster_policy_reports(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """list should list ClusterPolicyReports."""
        result = cli_runner.invoke(app, ["cluster-policy-reports", "list"])

        assert result.exit_code == 0
        mock_kyverno_manager.list_cluster_policy_reports.assert_called_once()

    def test_get_cluster_policy_report(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """get should retrieve a ClusterPolicyReport."""
        result = cli_runner.invoke(app, ["cluster-policy-reports", "get", "cpolr-test"])

        assert result.exit_code == 0
        mock_kyverno_manager.get_cluster_policy_report.assert_called_once_with("cpolr-test")

    def test_get_cluster_policy_report_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """get should handle not found error."""
        mock_kyverno_manager.get_cluster_policy_report.side_effect = KubernetesNotFoundError(
            resource_type="ClusterPolicyReport",
            resource_name="nonexistent",
        )

        result = cli_runner.invoke(app, ["cluster-policy-reports", "get", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()


@pytest.mark.unit
@pytest.mark.kubernetes
class TestPolicyReportCommands:
    """Tests for Kyverno namespaced PolicyReport commands."""

    @pytest.fixture
    def app(self, get_kyverno_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with policy commands."""
        app = typer.Typer()
        register_policy_commands(app, get_kyverno_manager)
        return app

    def test_list_policy_reports(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """list should list PolicyReports."""
        result = cli_runner.invoke(app, ["policy-reports", "list"])

        assert result.exit_code == 0
        mock_kyverno_manager.list_policy_reports.assert_called_once_with(
            namespace=None,
        )

    def test_list_policy_reports_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """list with --namespace should pass namespace."""
        result = cli_runner.invoke(app, ["policy-reports", "list", "-n", "production"])

        assert result.exit_code == 0
        mock_kyverno_manager.list_policy_reports.assert_called_once_with(
            namespace="production",
        )

    def test_get_policy_report(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """get should retrieve a PolicyReport."""
        result = cli_runner.invoke(app, ["policy-reports", "get", "polr-test"])

        assert result.exit_code == 0
        mock_kyverno_manager.get_policy_report.assert_called_once_with("polr-test", namespace=None)

    def test_get_policy_report_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """get with --namespace should pass namespace."""
        result = cli_runner.invoke(app, ["policy-reports", "get", "polr-test", "-n", "production"])

        assert result.exit_code == 0
        mock_kyverno_manager.get_policy_report.assert_called_once_with(
            "polr-test", namespace="production"
        )
