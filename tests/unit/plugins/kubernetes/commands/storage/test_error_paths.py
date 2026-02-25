"""Tests for Kubernetes storage command error paths and helper functions.

Covers:
- _parse_labels valid and invalid input
- KubernetesError handling in every command
- delete abort paths (confirm_delete returns False)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import click
import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesError,
)
from system_operations_manager.plugins.kubernetes.commands.storage import (
    _parse_labels,
    register_storage_commands,
)

# =============================================================================
# Helper function tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestParseLabels:
    """Tests for the _parse_labels helper function in storage commands."""

    def test_returns_none_for_none_input(self) -> None:
        """_parse_labels should return None when given None."""
        result = _parse_labels(None)
        assert result is None

    def test_returns_none_for_empty_list(self) -> None:
        """_parse_labels should return None when given an empty list."""
        result = _parse_labels([])
        assert result is None

    def test_parses_single_label(self) -> None:
        """_parse_labels should parse a single key=value label."""
        result = _parse_labels(["tier=fast"])
        assert result == {"tier": "fast"}

    def test_parses_multiple_labels(self) -> None:
        """_parse_labels should parse multiple key=value labels."""
        result = _parse_labels(["tier=fast", "env=production"])
        assert result == {"tier": "fast", "env": "production"}

    def test_invalid_label_raises_exit(self) -> None:
        """_parse_labels should raise click.exceptions.Exit for labels without '='."""
        with pytest.raises(click.exceptions.Exit) as exc_info:
            _parse_labels(["noequalssign"])
        assert exc_info.value.exit_code == 1


# =============================================================================
# KubernetesError handling for persistent volume commands
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestPersistentVolumeCommandErrors:
    """Tests for KubernetesError handling in persistent volume commands."""

    @pytest.fixture
    def app(self, get_storage_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with storage commands."""
        app = typer.Typer()
        register_storage_commands(app, get_storage_manager)
        return app

    def test_list_pvs_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_storage_manager: MagicMock,
    ) -> None:
        """list pvs should handle KubernetesError."""
        mock_storage_manager.list_persistent_volumes.side_effect = KubernetesError("list failed")
        result = cli_runner.invoke(app, ["pvs", "list"])
        assert result.exit_code == 1

    def test_delete_pv_abort_when_not_confirmed(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_storage_manager: MagicMock,
    ) -> None:
        """delete pv should abort when user does not confirm."""
        cli_runner.invoke(app, ["pvs", "delete", "test-pv"], input="n\n")
        mock_storage_manager.delete_persistent_volume.assert_not_called()

    def test_delete_pv_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_storage_manager: MagicMock,
    ) -> None:
        """delete pv should handle KubernetesError."""
        mock_storage_manager.delete_persistent_volume.side_effect = KubernetesError("delete failed")
        result = cli_runner.invoke(app, ["pvs", "delete", "test-pv", "--force"])
        assert result.exit_code == 1


# =============================================================================
# KubernetesError handling for persistent volume claim commands
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestPersistentVolumeClaimCommandErrors:
    """Tests for KubernetesError handling in persistent volume claim commands."""

    @pytest.fixture
    def app(self, get_storage_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with storage commands."""
        app = typer.Typer()
        register_storage_commands(app, get_storage_manager)
        return app

    def test_list_pvcs_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_storage_manager: MagicMock,
    ) -> None:
        """list pvcs should handle KubernetesError."""
        mock_storage_manager.list_persistent_volume_claims.side_effect = KubernetesError(
            "list failed"
        )
        result = cli_runner.invoke(app, ["pvcs", "list"])
        assert result.exit_code == 1

    def test_create_pvc_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_storage_manager: MagicMock,
    ) -> None:
        """create pvc should handle KubernetesError."""
        mock_storage_manager.create_persistent_volume_claim.side_effect = KubernetesError(
            "create failed"
        )
        result = cli_runner.invoke(
            app,
            [
                "pvcs",
                "create",
                "test-pvc",
                "--storage",
                "10Gi",
                "--access-mode",
                "ReadWriteOnce",
            ],
        )
        assert result.exit_code == 1

    def test_delete_pvc_abort_when_not_confirmed(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_storage_manager: MagicMock,
    ) -> None:
        """delete pvc should abort when user does not confirm."""
        cli_runner.invoke(app, ["pvcs", "delete", "test-pvc"], input="n\n")
        mock_storage_manager.delete_persistent_volume_claim.assert_not_called()

    def test_delete_pvc_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_storage_manager: MagicMock,
    ) -> None:
        """delete pvc should handle KubernetesError."""
        mock_storage_manager.delete_persistent_volume_claim.side_effect = KubernetesError(
            "delete failed"
        )
        result = cli_runner.invoke(app, ["pvcs", "delete", "test-pvc", "--force"])
        assert result.exit_code == 1


# =============================================================================
# KubernetesError handling for storage class commands
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestStorageClassCommandErrors:
    """Tests for KubernetesError handling in storage class commands."""

    @pytest.fixture
    def app(self, get_storage_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with storage commands."""
        app = typer.Typer()
        register_storage_commands(app, get_storage_manager)
        return app

    def test_list_storage_classes_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_storage_manager: MagicMock,
    ) -> None:
        """list storage classes should handle KubernetesError."""
        mock_storage_manager.list_storage_classes.side_effect = KubernetesError("list failed")
        result = cli_runner.invoke(app, ["storage-classes", "list"])
        assert result.exit_code == 1


# =============================================================================
# Label parsing via CLI (exercises _parse_labels success path)
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestLabelParsingViaCLI:
    """Tests for _parse_labels success path invoked through CLI commands."""

    @pytest.fixture
    def app(self, get_storage_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with storage commands."""
        app = typer.Typer()
        register_storage_commands(app, get_storage_manager)
        return app

    def test_create_pvc_with_labels(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_storage_manager: MagicMock,
    ) -> None:
        """create pvc with --label should pass parsed labels."""
        result = cli_runner.invoke(
            app,
            [
                "pvcs",
                "create",
                "test-pvc",
                "--storage",
                "5Gi",
                "--access-mode",
                "ReadWriteOnce",
                "--label",
                "app=myapp",
                "--label",
                "env=staging",
            ],
        )
        assert result.exit_code == 0
        call_kwargs: Any = mock_storage_manager.create_persistent_volume_claim.call_args
        assert call_kwargs.kwargs["labels"] == {"app": "myapp", "env": "staging"}

    def test_create_pvc_with_invalid_label_exits(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_storage_manager: MagicMock,
    ) -> None:
        """create pvc with an invalid label format should exit with error."""
        result = cli_runner.invoke(
            app,
            [
                "pvcs",
                "create",
                "test-pvc",
                "--storage",
                "5Gi",
                "--label",
                "invalidlabel",
            ],
        )
        assert result.exit_code != 0
