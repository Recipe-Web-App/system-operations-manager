"""Unit tests for Kubernetes pod commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesNotFoundError,
)
from system_operations_manager.plugins.kubernetes.commands.workloads import (
    register_workload_commands,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestPodCommands:
    """Tests for pod CLI commands."""

    @pytest.fixture
    def app(self, get_workload_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with workload commands."""
        app = typer.Typer()
        register_workload_commands(app, get_workload_manager)
        return app

    def test_list_pods(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
        sample_pod: MagicMock,
    ) -> None:
        """pods list should display pods."""
        mock_workload_manager.list_pods.return_value = [sample_pod]

        result = cli_runner.invoke(app, ["pods", "list"])

        assert result.exit_code == 0
        mock_workload_manager.list_pods.assert_called_once_with(
            namespace=None,
            all_namespaces=False,
            label_selector=None,
            field_selector=None,
        )

    def test_list_pods_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """pods list -n should filter by namespace."""
        mock_workload_manager.list_pods.return_value = []

        result = cli_runner.invoke(app, ["pods", "list", "-n", "production"])

        assert result.exit_code == 0
        mock_workload_manager.list_pods.assert_called_once_with(
            namespace="production",
            all_namespaces=False,
            label_selector=None,
            field_selector=None,
        )

    def test_list_pods_all_namespaces(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """pods list -A should list from all namespaces."""
        mock_workload_manager.list_pods.return_value = []

        result = cli_runner.invoke(app, ["pods", "list", "--all-namespaces"])

        assert result.exit_code == 0
        mock_workload_manager.list_pods.assert_called_once_with(
            namespace=None,
            all_namespaces=True,
            label_selector=None,
            field_selector=None,
        )

    def test_list_pods_with_label_selector(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """pods list -l should filter by label selector."""
        mock_workload_manager.list_pods.return_value = []

        result = cli_runner.invoke(app, ["pods", "list", "-l", "app=nginx"])

        assert result.exit_code == 0
        mock_workload_manager.list_pods.assert_called_once_with(
            namespace=None,
            all_namespaces=False,
            label_selector="app=nginx",
            field_selector=None,
        )

    def test_get_pod(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
        sample_pod: MagicMock,
    ) -> None:
        """pods get should display pod details."""
        mock_workload_manager.get_pod.return_value = sample_pod

        result = cli_runner.invoke(app, ["pods", "get", "test-pod"])

        assert result.exit_code == 0
        mock_workload_manager.get_pod.assert_called_once_with("test-pod", None)

    def test_get_pod_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """pods get should handle not found error."""
        mock_workload_manager.get_pod.side_effect = KubernetesNotFoundError(
            resource_type="Pod", resource_name="missing-pod"
        )

        result = cli_runner.invoke(app, ["pods", "get", "missing-pod"])

        assert result.exit_code == 1

    def test_delete_pod_confirmed(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """pods delete should delete pod when confirmed."""
        result = cli_runner.invoke(app, ["pods", "delete", "test-pod"], input="y\n")

        assert result.exit_code == 0
        mock_workload_manager.delete_pod.assert_called_once_with("test-pod", None)

    def test_delete_pod_cancelled(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """pods delete should cancel when not confirmed."""
        result = cli_runner.invoke(app, ["pods", "delete", "test-pod"], input="n\n")

        assert result.exit_code == 0
        mock_workload_manager.delete_pod.assert_not_called()

    def test_delete_pod_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """pods delete --force should skip confirmation."""
        result = cli_runner.invoke(app, ["pods", "delete", "test-pod", "--force"])

        assert result.exit_code == 0
        mock_workload_manager.delete_pod.assert_called_once_with("test-pod", None)

    def test_pod_logs(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """pods logs should display pod logs."""
        mock_workload_manager.get_pod_logs.return_value = "Log line 1\nLog line 2"

        result = cli_runner.invoke(app, ["pods", "logs", "test-pod"])

        assert result.exit_code == 0
        mock_workload_manager.get_pod_logs.assert_called_once_with(
            "test-pod", None, container=None, tail_lines=None, previous=False
        )

    def test_pod_logs_with_options(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """pods logs should support container, tail, and previous options."""
        mock_workload_manager.get_pod_logs.return_value = "Recent logs"

        result = cli_runner.invoke(
            app,
            ["pods", "logs", "test-pod", "-c", "sidecar", "--tail", "100", "--previous"],
        )

        assert result.exit_code == 0
        mock_workload_manager.get_pod_logs.assert_called_once_with(
            "test-pod", None, container="sidecar", tail_lines=100, previous=True
        )

    def test_list_pods_output_json(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
        sample_pod: MagicMock,
    ) -> None:
        """pods list --output json should output JSON format."""
        mock_workload_manager.list_pods.return_value = [sample_pod]

        result = cli_runner.invoke(app, ["pods", "list", "--output", "json"])

        assert result.exit_code == 0

    def test_handles_k8s_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """pods commands should handle KubernetesError properly."""
        from system_operations_manager.integrations.kubernetes.exceptions import (
            KubernetesError,
        )

        mock_workload_manager.list_pods.side_effect = KubernetesError("API error")

        result = cli_runner.invoke(app, ["pods", "list"])

        assert result.exit_code == 1
