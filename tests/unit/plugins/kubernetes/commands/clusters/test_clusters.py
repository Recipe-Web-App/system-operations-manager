"""Unit tests for Kubernetes cluster commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesError,
)
from system_operations_manager.plugins.kubernetes.commands.clusters import (
    register_cluster_commands,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestNodeCommands:
    """Tests for node CLI commands."""

    @pytest.fixture
    def app(self, get_namespace_cluster_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with cluster commands."""
        app = typer.Typer()
        register_cluster_commands(app, get_namespace_cluster_manager)
        return app

    def test_list_nodes(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_namespace_cluster_manager: MagicMock,
        sample_node: MagicMock,
    ) -> None:
        """nodes list should display nodes."""
        mock_namespace_cluster_manager.list_nodes.return_value = [sample_node]

        result = cli_runner.invoke(app, ["nodes", "list"])

        assert result.exit_code == 0
        mock_namespace_cluster_manager.list_nodes.assert_called_once()

    def test_list_nodes_with_label_selector(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_namespace_cluster_manager: MagicMock,
    ) -> None:
        """nodes list -l should filter by label selector."""
        mock_namespace_cluster_manager.list_nodes.return_value = []

        result = cli_runner.invoke(
            app, ["nodes", "list", "-l", "node-role.kubernetes.io/control-plane="]
        )

        assert result.exit_code == 0
        mock_namespace_cluster_manager.list_nodes.assert_called_once()

    def test_get_node(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_namespace_cluster_manager: MagicMock,
        sample_node: MagicMock,
    ) -> None:
        """nodes get should display node details."""
        mock_namespace_cluster_manager.get_node.return_value = sample_node

        result = cli_runner.invoke(app, ["nodes", "get", "worker-1"])

        assert result.exit_code == 0
        mock_namespace_cluster_manager.get_node.assert_called_once_with("worker-1")

    def test_list_nodes_output_json(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_namespace_cluster_manager: MagicMock,
        sample_node: MagicMock,
    ) -> None:
        """nodes list --output json should output JSON format."""
        mock_namespace_cluster_manager.list_nodes.return_value = [sample_node]

        result = cli_runner.invoke(app, ["nodes", "list", "--output", "json"])

        assert result.exit_code == 0


@pytest.mark.unit
@pytest.mark.kubernetes
class TestEventCommands:
    """Tests for event CLI commands."""

    @pytest.fixture
    def app(self, get_namespace_cluster_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with cluster commands."""
        app = typer.Typer()
        register_cluster_commands(app, get_namespace_cluster_manager)
        return app

    def test_list_events(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_namespace_cluster_manager: MagicMock,
        sample_event: MagicMock,
    ) -> None:
        """events list should display events."""
        mock_namespace_cluster_manager.list_events.return_value = [sample_event]

        result = cli_runner.invoke(app, ["events", "list"])

        assert result.exit_code == 0
        mock_namespace_cluster_manager.list_events.assert_called_once()

    def test_list_events_all_namespaces(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_namespace_cluster_manager: MagicMock,
    ) -> None:
        """events list -A should list from all namespaces."""
        mock_namespace_cluster_manager.list_events.return_value = []

        result = cli_runner.invoke(app, ["events", "list", "--all-namespaces"])

        assert result.exit_code == 0

    def test_list_events_with_involved_object(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_namespace_cluster_manager: MagicMock,
    ) -> None:
        """events list --involved-object should filter by object."""
        mock_namespace_cluster_manager.list_events.return_value = []

        result = cli_runner.invoke(app, ["events", "list", "--involved-object", "my-pod"])

        assert result.exit_code == 0
        call_kwargs = mock_namespace_cluster_manager.list_events.call_args[1]
        assert call_kwargs["involved_object"] == "my-pod"

    def test_list_events_with_field_selector(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_namespace_cluster_manager: MagicMock,
    ) -> None:
        """events list --field-selector should filter by field."""
        mock_namespace_cluster_manager.list_events.return_value = []

        result = cli_runner.invoke(app, ["events", "list", "--field-selector", "type=Warning"])

        assert result.exit_code == 0

    def test_list_events_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_namespace_cluster_manager: MagicMock,
    ) -> None:
        """events list -n should filter by namespace."""
        mock_namespace_cluster_manager.list_events.return_value = []

        result = cli_runner.invoke(app, ["events", "list", "-n", "production"])

        assert result.exit_code == 0


@pytest.mark.unit
@pytest.mark.kubernetes
class TestClusterInfoCommand:
    """Tests for cluster-info command."""

    @pytest.fixture
    def app(self, get_namespace_cluster_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with cluster commands."""
        app = typer.Typer()
        register_cluster_commands(app, get_namespace_cluster_manager)
        return app

    def test_cluster_info(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_namespace_cluster_manager: MagicMock,
    ) -> None:
        """cluster-info should display cluster information."""
        mock_namespace_cluster_manager.get_cluster_info.return_value = {
            "version": "v1.28.0",
            "platform": "linux/amd64",
            "api_server": "https://192.168.49.2:8443",
        }

        result = cli_runner.invoke(app, ["cluster-info"])

        assert result.exit_code == 0
        mock_namespace_cluster_manager.get_cluster_info.assert_called_once()

    def test_cluster_info_output_json(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_namespace_cluster_manager: MagicMock,
    ) -> None:
        """cluster-info -o json should output JSON format."""
        mock_namespace_cluster_manager.get_cluster_info.return_value = {
            "version": "v1.28.0",
        }

        result = cli_runner.invoke(app, ["cluster-info", "-o", "json"])

        assert result.exit_code == 0

    def test_cluster_info_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_namespace_cluster_manager: MagicMock,
    ) -> None:
        """cluster-info should handle errors gracefully."""
        mock_namespace_cluster_manager.get_cluster_info.side_effect = KubernetesError(
            "Failed to get cluster info"
        )

        result = cli_runner.invoke(app, ["cluster-info"])

        assert result.exit_code == 1


@pytest.mark.unit
@pytest.mark.kubernetes
class TestNodeCommandErrorPaths:
    """Tests for node CLI command error handling paths."""

    @pytest.fixture
    def app(self, get_namespace_cluster_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with cluster commands."""
        app = typer.Typer()
        register_cluster_commands(app, get_namespace_cluster_manager)
        return app

    def test_list_nodes_kubernetes_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_namespace_cluster_manager: MagicMock,
    ) -> None:
        """nodes list should handle KubernetesError and exit with code 1."""
        mock_namespace_cluster_manager.list_nodes.side_effect = KubernetesError(
            "Failed to list nodes"
        )

        result = cli_runner.invoke(app, ["nodes", "list"])

        assert result.exit_code == 1

    def test_get_node_kubernetes_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_namespace_cluster_manager: MagicMock,
    ) -> None:
        """nodes get should handle KubernetesError and exit with code 1."""
        mock_namespace_cluster_manager.get_node.side_effect = KubernetesError("Failed to get node")

        result = cli_runner.invoke(app, ["nodes", "get", "worker-1"])

        assert result.exit_code == 1


@pytest.mark.unit
@pytest.mark.kubernetes
class TestEventCommandErrorPaths:
    """Tests for event CLI command error handling paths."""

    @pytest.fixture
    def app(self, get_namespace_cluster_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with cluster commands."""
        app = typer.Typer()
        register_cluster_commands(app, get_namespace_cluster_manager)
        return app

    def test_list_events_kubernetes_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_namespace_cluster_manager: MagicMock,
    ) -> None:
        """events list should handle KubernetesError and exit with code 1."""
        mock_namespace_cluster_manager.list_events.side_effect = KubernetesError(
            "Failed to list events"
        )

        result = cli_runner.invoke(app, ["events", "list"])

        assert result.exit_code == 1
