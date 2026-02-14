"""Unit tests for multicluster status command."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.models.multicluster import (
    MultiClusterStatusResult,
)
from system_operations_manager.plugins.kubernetes.commands.multicluster import (
    register_multicluster_commands,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestMulticlusterStatusCommand:
    """Tests for the multicluster status CLI command."""

    @pytest.fixture
    def app(self, get_multicluster_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with multicluster commands."""
        app = typer.Typer()
        register_multicluster_commands(app, get_multicluster_manager)
        return app

    def test_status_all_clusters(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_multicluster_manager: MagicMock,
        sample_status_result: MultiClusterStatusResult,
    ) -> None:
        """multicluster status should show status for all clusters by default."""
        mock_multicluster_manager.multi_cluster_status.return_value = sample_status_result

        result = cli_runner.invoke(app, ["multicluster", "status"])

        assert result.exit_code == 0
        mock_multicluster_manager.multi_cluster_status.assert_called_once_with(None)

    def test_status_filtered_clusters(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_multicluster_manager: MagicMock,
        sample_status_result: MultiClusterStatusResult,
    ) -> None:
        """multicluster status --clusters should filter to specified clusters."""
        mock_multicluster_manager.multi_cluster_status.return_value = sample_status_result

        result = cli_runner.invoke(
            app, ["multicluster", "status", "--clusters", "staging,production"]
        )

        assert result.exit_code == 0
        mock_multicluster_manager.multi_cluster_status.assert_called_once_with(
            ["staging", "production"]
        )

    def test_status_with_disconnected(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_multicluster_manager: MagicMock,
        sample_status_partial_failure: MultiClusterStatusResult,
    ) -> None:
        """multicluster status should succeed even with disconnected clusters."""
        mock_multicluster_manager.multi_cluster_status.return_value = sample_status_partial_failure

        result = cli_runner.invoke(app, ["multicluster", "status"])

        assert result.exit_code == 0
        mock_multicluster_manager.multi_cluster_status.assert_called_once_with(None)

    def test_status_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_multicluster_manager: MagicMock,
        sample_status_result: MultiClusterStatusResult,
    ) -> None:
        """multicluster status --output json should output JSON format."""
        mock_multicluster_manager.multi_cluster_status.return_value = sample_status_result

        result = cli_runner.invoke(app, ["multicluster", "status", "--output", "json"])

        assert result.exit_code == 0
        mock_multicluster_manager.multi_cluster_status.assert_called_once_with(None)

    def test_status_yaml_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_multicluster_manager: MagicMock,
        sample_status_result: MultiClusterStatusResult,
    ) -> None:
        """multicluster status --output yaml should output YAML format."""
        mock_multicluster_manager.multi_cluster_status.return_value = sample_status_result

        result = cli_runner.invoke(app, ["multicluster", "status", "--output", "yaml"])

        assert result.exit_code == 0
        mock_multicluster_manager.multi_cluster_status.assert_called_once_with(None)

    def test_status_no_clusters_configured(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_multicluster_manager: MagicMock,
    ) -> None:
        """multicluster status should exit with error if no clusters configured."""
        mock_multicluster_manager.multi_cluster_status.side_effect = ValueError(
            "No clusters configured in multicluster config"
        )

        result = cli_runner.invoke(app, ["multicluster", "status"])

        assert result.exit_code == 1
        mock_multicluster_manager.multi_cluster_status.assert_called_once_with(None)
