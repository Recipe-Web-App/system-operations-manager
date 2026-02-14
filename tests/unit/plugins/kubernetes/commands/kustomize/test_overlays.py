"""Unit tests for kustomize overlays command."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.plugins.kubernetes.commands.kustomize import (
    register_kustomize_commands,
)
from system_operations_manager.services.kubernetes.kustomize_manager import OverlayInfo


@pytest.mark.unit
@pytest.mark.kubernetes
class TestOverlaysCommand:
    """Tests for the ``kustomize overlays`` command."""

    @pytest.fixture
    def app(self, get_kustomize_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with kustomize commands."""
        app = typer.Typer()
        register_kustomize_commands(app, get_kustomize_manager)
        return app

    def test_overlays_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kustomize_manager: MagicMock,
        sample_overlay_info: list[OverlayInfo],
        tmp_kustomization_dir: Path,
    ) -> None:
        """overlays should list discovered overlays."""
        mock_kustomize_manager.list_overlays.return_value = sample_overlay_info

        result = cli_runner.invoke(app, ["kustomize", "overlays", str(tmp_kustomization_dir)])

        assert result.exit_code == 0
        assert "base" in result.stdout
        assert "dev" in result.stdout

    def test_overlays_empty(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kustomize_manager: MagicMock,
        tmp_kustomization_dir: Path,
    ) -> None:
        """overlays should show message when none found."""
        mock_kustomize_manager.list_overlays.return_value = []

        result = cli_runner.invoke(app, ["kustomize", "overlays", str(tmp_kustomization_dir)])

        assert result.exit_code == 0
        assert "No overlays found" in result.stdout

    def test_overlays_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kustomize_manager: MagicMock,
        sample_overlay_info: list[OverlayInfo],
        tmp_kustomization_dir: Path,
    ) -> None:
        """overlays --output json should produce json output."""
        mock_kustomize_manager.list_overlays.return_value = sample_overlay_info

        result = cli_runner.invoke(
            app, ["kustomize", "overlays", str(tmp_kustomization_dir), "--output", "json"]
        )

        assert result.exit_code == 0
        mock_kustomize_manager.list_overlays.assert_called_once()
