"""Unit tests for multicluster deploy command."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.models.multicluster import (
    MultiClusterDeployResult,
)
from system_operations_manager.plugins.kubernetes.commands.multicluster import (
    register_multicluster_commands,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestMulticlusterDeployCommand:
    """Tests for the ``multicluster deploy`` command."""

    @pytest.fixture
    def app(self, get_multicluster_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with multicluster commands."""
        app = typer.Typer()
        register_multicluster_commands(app, get_multicluster_manager)
        return app

    def test_deploy_file_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_multicluster_manager: MagicMock,
        sample_deploy_result: MultiClusterDeployResult,
        tmp_path: Path,
    ) -> None:
        """deploy should succeed when deploying from a file."""
        # Create a temporary YAML file
        manifest_file = tmp_path / "test-manifest.yaml"
        manifest_file.write_text("apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: test\n")

        # Set up mock returns
        test_manifest = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "test"},
        }
        mock_multicluster_manager.load_manifests_from_path.return_value = [test_manifest]
        mock_multicluster_manager.deploy_manifests_to_clusters.return_value = sample_deploy_result

        result = cli_runner.invoke(app, ["multicluster", "deploy", "--file", str(manifest_file)])

        assert result.exit_code == 0
        mock_multicluster_manager.load_manifests_from_path.assert_called_once()
        mock_multicluster_manager.deploy_manifests_to_clusters.assert_called_once()

    def test_deploy_with_clusters_and_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_multicluster_manager: MagicMock,
        sample_deploy_result: MultiClusterDeployResult,
        tmp_path: Path,
    ) -> None:
        """deploy should pass clusters and namespace to manager."""
        # Create a temporary YAML file
        manifest_file = tmp_path / "test-manifest.yaml"
        manifest_file.write_text("apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: test\n")

        # Set up mock returns
        test_manifest = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "test"},
        }
        mock_multicluster_manager.load_manifests_from_path.return_value = [test_manifest]
        mock_multicluster_manager.deploy_manifests_to_clusters.return_value = sample_deploy_result

        result = cli_runner.invoke(
            app,
            [
                "multicluster",
                "deploy",
                "--file",
                str(manifest_file),
                "--clusters",
                "staging,production",
                "--namespace",
                "app",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_multicluster_manager.deploy_manifests_to_clusters.call_args.kwargs
        assert call_kwargs["clusters"] == ["staging", "production"]
        assert call_kwargs["namespace"] == "app"

    def test_deploy_dry_run(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_multicluster_manager: MagicMock,
        sample_deploy_result: MultiClusterDeployResult,
        tmp_path: Path,
    ) -> None:
        """deploy should pass dry_run flag to manager."""
        # Create a temporary YAML file
        manifest_file = tmp_path / "test-manifest.yaml"
        manifest_file.write_text("apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: test\n")

        # Set up mock returns
        test_manifest = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "test"},
        }
        mock_multicluster_manager.load_manifests_from_path.return_value = [test_manifest]
        mock_multicluster_manager.deploy_manifests_to_clusters.return_value = sample_deploy_result

        result = cli_runner.invoke(
            app,
            ["multicluster", "deploy", "--file", str(manifest_file), "--dry-run"],
        )

        assert result.exit_code == 0
        call_kwargs = mock_multicluster_manager.deploy_manifests_to_clusters.call_args.kwargs
        assert call_kwargs["dry_run"] is True
        assert "Dry run mode" in result.stdout

    def test_deploy_partial_failure(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_multicluster_manager: MagicMock,
        sample_deploy_partial_failure: MultiClusterDeployResult,
        tmp_path: Path,
    ) -> None:
        """deploy should exit 1 when some clusters fail."""
        # Create a temporary YAML file
        manifest_file = tmp_path / "test-manifest.yaml"
        manifest_file.write_text("apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: test\n")

        # Set up mock returns
        test_manifest = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "test"},
        }
        mock_multicluster_manager.load_manifests_from_path.return_value = [test_manifest]
        mock_multicluster_manager.deploy_manifests_to_clusters.return_value = (
            sample_deploy_partial_failure
        )

        result = cli_runner.invoke(app, ["multicluster", "deploy", "--file", str(manifest_file)])

        assert result.exit_code == 1

    def test_deploy_file_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_multicluster_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """deploy should exit 1 when file does not exist."""
        non_existent_file = tmp_path / "non-existent.yaml"

        result = cli_runner.invoke(
            app, ["multicluster", "deploy", "--file", str(non_existent_file)]
        )

        assert result.exit_code == 1
        assert "Path not found" in result.stdout

    def test_deploy_no_manifests(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_multicluster_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """deploy should exit 0 with warning when no manifests found."""
        # Create a temporary YAML file
        manifest_file = tmp_path / "empty.yaml"
        manifest_file.write_text("")

        # Set up mock to return empty list
        mock_multicluster_manager.load_manifests_from_path.return_value = []

        result = cli_runner.invoke(app, ["multicluster", "deploy", "--file", str(manifest_file)])

        assert result.exit_code == 0
        assert "No manifests found" in result.stdout

    def test_deploy_stdin(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_multicluster_manager: MagicMock,
        sample_deploy_result: MultiClusterDeployResult,
    ) -> None:
        """deploy should read from stdin when file is '-'."""
        yaml_content = "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: test\n"

        # Set up mock returns
        test_manifest = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "test"},
        }
        mock_multicluster_manager.load_manifests_from_string.return_value = [test_manifest]
        mock_multicluster_manager.deploy_manifests_to_clusters.return_value = sample_deploy_result

        result = cli_runner.invoke(
            app, ["multicluster", "deploy", "--file", "-"], input=yaml_content
        )

        assert result.exit_code == 0
        mock_multicluster_manager.load_manifests_from_string.assert_called_once_with(yaml_content)
        mock_multicluster_manager.deploy_manifests_to_clusters.assert_called_once()
