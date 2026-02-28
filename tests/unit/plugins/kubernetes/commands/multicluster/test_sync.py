"""Unit tests for multicluster sync command."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesConnectionError,
)
from system_operations_manager.integrations.kubernetes.models.multicluster import (
    MultiClusterSyncResult,
)
from system_operations_manager.plugins.kubernetes.commands.multicluster import (
    register_multicluster_commands,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestMulticlusterSyncCommand:
    """Tests for the multicluster sync CLI command."""

    @pytest.fixture
    def app(self, get_multicluster_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with multicluster commands."""
        app = typer.Typer()
        register_multicluster_commands(app, get_multicluster_manager)
        return app

    def test_sync_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_multicluster_manager: MagicMock,
        sample_sync_result: MultiClusterSyncResult,
    ) -> None:
        """multicluster sync should successfully sync resource to target cluster."""
        mock_multicluster_manager.sync_resource.return_value = sample_sync_result

        result = cli_runner.invoke(
            app,
            [
                "multicluster",
                "sync",
                "--source",
                "staging",
                "--target",
                "production",
                "--kind",
                "ConfigMap",
                "--name",
                "app-config",
                "-n",
                "default",
            ],
        )

        assert result.exit_code == 0
        mock_multicluster_manager.sync_resource.assert_called_once_with(
            "staging",
            ["production"],
            resource_type="ConfigMap",
            resource_name="app-config",
            namespace="default",
            dry_run=False,
        )

    def test_sync_multiple_targets(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_multicluster_manager: MagicMock,
        sample_sync_result: MultiClusterSyncResult,
    ) -> None:
        """multicluster sync should handle multiple target clusters."""
        mock_multicluster_manager.sync_resource.return_value = sample_sync_result

        result = cli_runner.invoke(
            app,
            [
                "multicluster",
                "sync",
                "--source",
                "staging",
                "--target",
                "production,dr-site",
                "--kind",
                "ConfigMap",
                "--name",
                "app-config",
                "-n",
                "default",
            ],
        )

        assert result.exit_code == 0
        mock_multicluster_manager.sync_resource.assert_called_once_with(
            "staging",
            ["production", "dr-site"],
            resource_type="ConfigMap",
            resource_name="app-config",
            namespace="default",
            dry_run=False,
        )

    def test_sync_dry_run(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_multicluster_manager: MagicMock,
        sample_sync_result: MultiClusterSyncResult,
    ) -> None:
        """multicluster sync --dry-run should call manager with dry_run=True."""
        mock_multicluster_manager.sync_resource.return_value = sample_sync_result

        result = cli_runner.invoke(
            app,
            [
                "multicluster",
                "sync",
                "--source",
                "staging",
                "--target",
                "production",
                "--kind",
                "ConfigMap",
                "--name",
                "app-config",
                "-n",
                "default",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        mock_multicluster_manager.sync_resource.assert_called_once_with(
            "staging",
            ["production"],
            resource_type="ConfigMap",
            resource_name="app-config",
            namespace="default",
            dry_run=True,
        )

    def test_sync_failure(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_multicluster_manager: MagicMock,
        sample_sync_failure: MultiClusterSyncResult,
    ) -> None:
        """multicluster sync should exit with error code if sync fails."""
        mock_multicluster_manager.sync_resource.return_value = sample_sync_failure

        result = cli_runner.invoke(
            app,
            [
                "multicluster",
                "sync",
                "--source",
                "staging",
                "--target",
                "production",
                "--kind",
                "ConfigMap",
                "--name",
                "app-config",
                "-n",
                "default",
            ],
        )

        assert result.exit_code == 1

    def test_sync_source_is_target(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_multicluster_manager: MagicMock,
    ) -> None:
        """multicluster sync should exit with error when source is the only target."""
        result = cli_runner.invoke(
            app,
            [
                "multicluster",
                "sync",
                "--source",
                "staging",
                "--target",
                "staging",
                "--kind",
                "ConfigMap",
                "--name",
                "app-config",
                "-n",
                "default",
            ],
        )

        assert result.exit_code == 1

    def test_sync_no_clusters_configured(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_multicluster_manager: MagicMock,
    ) -> None:
        """multicluster sync should exit with error if clusters are not configured."""
        mock_multicluster_manager.sync_resource.side_effect = ValueError(
            "Unknown clusters: production"
        )

        result = cli_runner.invoke(
            app,
            [
                "multicluster",
                "sync",
                "--source",
                "staging",
                "--target",
                "production",
                "--kind",
                "ConfigMap",
                "--name",
                "app-config",
                "-n",
                "default",
            ],
        )

        assert result.exit_code == 1
        mock_multicluster_manager.sync_resource.assert_called_once()

    def test_sync_empty_target_string(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_multicluster_manager: MagicMock,
    ) -> None:
        """multicluster sync should exit 1 when target string parses to empty list (lines 260-261)."""
        result = cli_runner.invoke(
            app,
            [
                "multicluster",
                "sync",
                "--source",
                "staging",
                "--target",
                ",,,",
                "--kind",
                "ConfigMap",
                "--name",
                "app-config",
                "-n",
                "default",
            ],
        )

        assert result.exit_code == 1
        assert "No target clusters specified" in result.stdout

    def test_sync_kubernetes_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_multicluster_manager: MagicMock,
    ) -> None:
        """multicluster sync should handle KubernetesError gracefully (line 301)."""
        mock_multicluster_manager.sync_resource.side_effect = KubernetesConnectionError(
            "Cannot connect to cluster"
        )

        result = cli_runner.invoke(
            app,
            [
                "multicluster",
                "sync",
                "--source",
                "staging",
                "--target",
                "production",
                "--kind",
                "ConfigMap",
                "--name",
                "app-config",
                "-n",
                "default",
            ],
        )

        assert result.exit_code == 1
        mock_multicluster_manager.sync_resource.assert_called_once()

    def test_sync_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_multicluster_manager: MagicMock,
        sample_sync_result: MultiClusterSyncResult,
    ) -> None:
        """multicluster sync --output json should output JSON format."""
        mock_multicluster_manager.sync_resource.return_value = sample_sync_result

        result = cli_runner.invoke(
            app,
            [
                "multicluster",
                "sync",
                "--source",
                "staging",
                "--target",
                "production",
                "--kind",
                "ConfigMap",
                "--name",
                "app-config",
                "-n",
                "default",
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0
