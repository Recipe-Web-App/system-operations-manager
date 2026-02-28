"""Unit tests for Kubernetes configmap commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import click
import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesError,
    KubernetesNotFoundError,
)
from system_operations_manager.plugins.kubernetes.commands.config_resources import (
    _parse_data,
    _parse_labels,
    register_config_commands,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestConfigMapCommands:
    """Tests for configmap commands."""

    @pytest.fixture
    def app(self, get_config_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with configmap commands."""
        app = typer.Typer()
        register_config_commands(app, get_config_manager)
        return app

    def test_list_configmaps(
        self, cli_runner: CliRunner, app: typer.Typer, mock_config_manager: MagicMock
    ) -> None:
        """list should list configmaps."""
        mock_config_manager.list_config_maps.return_value = []

        result = cli_runner.invoke(app, ["configmaps", "list"])

        assert result.exit_code == 0
        mock_config_manager.list_config_maps.assert_called_once_with(
            namespace=None, all_namespaces=False, label_selector=None
        )

    def test_list_configmaps_with_namespace(
        self, cli_runner: CliRunner, app: typer.Typer, mock_config_manager: MagicMock
    ) -> None:
        """list should accept namespace parameter."""
        mock_config_manager.list_config_maps.return_value = []

        result = cli_runner.invoke(app, ["configmaps", "list", "-n", "kube-system"])

        assert result.exit_code == 0
        mock_config_manager.list_config_maps.assert_called_once_with(
            namespace="kube-system", all_namespaces=False, label_selector=None
        )

    def test_get_configmap(
        self, cli_runner: CliRunner, app: typer.Typer, mock_config_manager: MagicMock
    ) -> None:
        """get should retrieve a configmap."""
        result = cli_runner.invoke(app, ["configmaps", "get", "test-config"])

        assert result.exit_code == 0
        mock_config_manager.get_config_map.assert_called_once_with("test-config", namespace=None)

    def test_get_configmap_data(
        self, cli_runner: CliRunner, app: typer.Typer, mock_config_manager: MagicMock
    ) -> None:
        """get-data should retrieve configmap data."""
        mock_config_manager.get_config_map_data.return_value = {"key1": "value1"}

        result = cli_runner.invoke(app, ["configmaps", "get-data", "test-config"])

        assert result.exit_code == 0
        mock_config_manager.get_config_map_data.assert_called_once_with(
            "test-config", namespace=None
        )

    def test_create_configmap(
        self, cli_runner: CliRunner, app: typer.Typer, mock_config_manager: MagicMock
    ) -> None:
        """create should create a configmap."""
        result = cli_runner.invoke(
            app,
            [
                "configmaps",
                "create",
                "test-config",
                "--data",
                "key1=value1",
                "--data",
                "key2=value2",
            ],
        )

        assert result.exit_code == 0
        mock_config_manager.create_config_map.assert_called_once()
        call_args = mock_config_manager.create_config_map.call_args
        assert call_args.args[0] == "test-config"
        assert call_args.kwargs["data"] == {"key1": "value1", "key2": "value2"}

    def test_update_configmap(
        self, cli_runner: CliRunner, app: typer.Typer, mock_config_manager: MagicMock
    ) -> None:
        """update should update a configmap."""
        result = cli_runner.invoke(
            app,
            ["configmaps", "update", "test-config", "--data", "key1=newvalue"],
        )

        assert result.exit_code == 0
        mock_config_manager.update_config_map.assert_called_once()
        call_args = mock_config_manager.update_config_map.call_args
        assert call_args.args[0] == "test-config"
        assert call_args.kwargs["data"] == {"key1": "newvalue"}

    def test_delete_configmap_force(
        self, cli_runner: CliRunner, app: typer.Typer, mock_config_manager: MagicMock
    ) -> None:
        """delete with --force should delete without confirmation."""
        result = cli_runner.invoke(app, ["configmaps", "delete", "test-config", "--force"])

        assert result.exit_code == 0
        mock_config_manager.delete_config_map.assert_called_once_with("test-config", namespace=None)
        assert "deleted" in result.stdout.lower()

    def test_handles_error(
        self, cli_runner: CliRunner, app: typer.Typer, mock_config_manager: MagicMock
    ) -> None:
        """should handle KubernetesError appropriately."""
        mock_config_manager.get_config_map.side_effect = KubernetesNotFoundError(
            resource_type="ConfigMap", resource_name="nonexistent"
        )

        result = cli_runner.invoke(app, ["configmaps", "get", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_list_configmaps_kubernetes_error(
        self, cli_runner: CliRunner, app: typer.Typer, mock_config_manager: MagicMock
    ) -> None:
        """list should handle KubernetesError."""
        mock_config_manager.list_config_maps.side_effect = KubernetesError("connection failed")

        result = cli_runner.invoke(app, ["configmaps", "list"])

        assert result.exit_code == 1

    def test_get_configmap_data_kubernetes_error(
        self, cli_runner: CliRunner, app: typer.Typer, mock_config_manager: MagicMock
    ) -> None:
        """get-data should handle KubernetesError."""
        mock_config_manager.get_config_map_data.side_effect = KubernetesError("connection failed")

        result = cli_runner.invoke(app, ["configmaps", "get-data", "test-config"])

        assert result.exit_code == 1

    def test_create_configmap_kubernetes_error(
        self, cli_runner: CliRunner, app: typer.Typer, mock_config_manager: MagicMock
    ) -> None:
        """create should handle KubernetesError."""
        mock_config_manager.create_config_map.side_effect = KubernetesError("connection failed")

        result = cli_runner.invoke(
            app,
            ["configmaps", "create", "test-config", "--data", "key1=value1"],
        )

        assert result.exit_code == 1

    def test_update_configmap_kubernetes_error(
        self, cli_runner: CliRunner, app: typer.Typer, mock_config_manager: MagicMock
    ) -> None:
        """update should handle KubernetesError."""
        mock_config_manager.update_config_map.side_effect = KubernetesError("connection failed")

        result = cli_runner.invoke(
            app,
            ["configmaps", "update", "test-config", "--data", "key1=newvalue"],
        )

        assert result.exit_code == 1

    def test_delete_configmap_aborts_without_confirmation(
        self, cli_runner: CliRunner, app: typer.Typer, mock_config_manager: MagicMock
    ) -> None:
        """delete without --force should abort when user declines confirmation."""
        result = cli_runner.invoke(app, ["configmaps", "delete", "test-config"], input="n\n")

        assert result.exit_code != 0
        mock_config_manager.delete_config_map.assert_not_called()

    def test_delete_configmap_kubernetes_error(
        self, cli_runner: CliRunner, app: typer.Typer, mock_config_manager: MagicMock
    ) -> None:
        """delete should handle KubernetesError."""
        mock_config_manager.delete_config_map.side_effect = KubernetesError("connection failed")

        result = cli_runner.invoke(app, ["configmaps", "delete", "test-config", "--force"])

        assert result.exit_code == 1

    def test_create_configmap_with_labels(
        self, cli_runner: CliRunner, app: typer.Typer, mock_config_manager: MagicMock
    ) -> None:
        """create should pass labels to manager."""
        result = cli_runner.invoke(
            app,
            [
                "configmaps",
                "create",
                "test-config",
                "--label",
                "env=prod",
                "--label",
                "team=ops",
            ],
        )

        assert result.exit_code == 0
        call_args = mock_config_manager.create_config_map.call_args
        assert call_args.kwargs["labels"] == {"env": "prod", "team": "ops"}


@pytest.mark.unit
@pytest.mark.kubernetes
class TestParseLabelsHelper:
    """Tests for _parse_labels helper function."""

    def test_parse_labels_none_returns_none(self) -> None:
        """_parse_labels with None should return None."""
        result = _parse_labels(None)
        assert result is None

    def test_parse_labels_empty_list_returns_none(self) -> None:
        """_parse_labels with empty list should return None."""
        result = _parse_labels([])
        assert result is None

    def test_parse_labels_valid(self) -> None:
        """_parse_labels should parse valid key=value entries."""
        result = _parse_labels(["env=prod", "team=ops"])
        assert result == {"env": "prod", "team": "ops"}

    def test_parse_labels_invalid_format_raises_exit(self) -> None:
        """_parse_labels with invalid format should raise typer.Exit."""
        with pytest.raises(click.exceptions.Exit):
            _parse_labels(["invalid-no-equals"])

    def test_parse_labels_invalid_format_exit_code(self) -> None:
        """_parse_labels with invalid format should exit with code 1."""
        with pytest.raises(click.exceptions.Exit) as exc_info:
            _parse_labels(["badlabel"])
        assert exc_info.value.exit_code == 1


@pytest.mark.unit
@pytest.mark.kubernetes
class TestParseDataHelper:
    """Tests for _parse_data helper function."""

    def test_parse_data_none_returns_none(self) -> None:
        """_parse_data with None should return None."""
        result = _parse_data(None)
        assert result is None

    def test_parse_data_empty_list_returns_none(self) -> None:
        """_parse_data with empty list should return None."""
        result = _parse_data([])
        assert result is None

    def test_parse_data_valid(self) -> None:
        """_parse_data should parse valid key=value entries."""
        result = _parse_data(["key1=value1", "key2=value2"])
        assert result == {"key1": "value1", "key2": "value2"}

    def test_parse_data_invalid_format_raises_exit(self) -> None:
        """_parse_data with invalid format should raise typer.Exit."""
        with pytest.raises(click.exceptions.Exit):
            _parse_data(["invalidnoequals"])
