"""Unit tests for Kubernetes TUI ecosystem screen.

Tests EcosystemScreen bindings, constants, color maps,
constructor, and default state.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from textual.binding import Binding

from system_operations_manager.tui.apps.kubernetes.ecosystem_screen import (
    ARGOCD_COLUMNS,
    CERT_COLUMNS,
    FLUX_COLUMNS,
    HEALTH_STATUS_COLORS,
    PHASE_COLORS,
    ROLLOUT_COLUMNS,
    SYNC_STATUS_COLORS,
    EcosystemScreen,
    _colorize,
    _flux_status,
    _ready_indicator,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture()
def mock_k8s_client() -> MagicMock:
    """Create a mock KubernetesClient."""
    return MagicMock()


# ============================================================================
# Binding Tests
# ============================================================================


def _binding_keys() -> list[str]:
    """Extract binding key strings from EcosystemScreen."""
    return [b.key if isinstance(b, Binding) else b[0] for b in EcosystemScreen.BINDINGS]


class TestEcosystemBindings:
    """Tests for EcosystemScreen key bindings."""

    @pytest.mark.unit
    def test_has_bindings(self) -> None:
        """Screen defines bindings."""
        assert len(EcosystemScreen.BINDINGS) > 0

    @pytest.mark.unit
    def test_escape_binding(self) -> None:
        """Escape navigates back."""
        assert "escape" in _binding_keys()

    @pytest.mark.unit
    def test_refresh_binding(self) -> None:
        """'r' triggers manual refresh."""
        assert "r" in _binding_keys()

    @pytest.mark.unit
    def test_panel_focus_bindings(self) -> None:
        """Number keys 1-4 focus individual panels."""
        keys = _binding_keys()
        assert "1" in keys
        assert "2" in keys
        assert "3" in keys
        assert "4" in keys


# ============================================================================
# Column Constant Tests
# ============================================================================


class TestColumnConstants:
    """Tests for column definition constants."""

    @pytest.mark.unit
    def test_argocd_columns_non_empty(self) -> None:
        """ArgoCD column list is non-empty."""
        assert len(ARGOCD_COLUMNS) > 0

    @pytest.mark.unit
    def test_flux_columns_non_empty(self) -> None:
        """Flux column list is non-empty."""
        assert len(FLUX_COLUMNS) > 0

    @pytest.mark.unit
    def test_cert_columns_non_empty(self) -> None:
        """Cert-Manager column list is non-empty."""
        assert len(CERT_COLUMNS) > 0

    @pytest.mark.unit
    def test_rollout_columns_non_empty(self) -> None:
        """Rollout column list is non-empty."""
        assert len(ROLLOUT_COLUMNS) > 0

    @pytest.mark.unit
    def test_columns_are_tuples_of_str_int(self) -> None:
        """All column definitions are (str, int) tuples."""
        for columns in [ARGOCD_COLUMNS, FLUX_COLUMNS, CERT_COLUMNS, ROLLOUT_COLUMNS]:
            for col_label, col_width in columns:
                assert isinstance(col_label, str)
                assert isinstance(col_width, int)
                assert col_width > 0


# ============================================================================
# Color Map Tests
# ============================================================================


class TestColorMaps:
    """Tests for status color maps."""

    @pytest.mark.unit
    def test_sync_status_colors_non_empty(self) -> None:
        """Sync status color map is non-empty."""
        assert len(SYNC_STATUS_COLORS) > 0

    @pytest.mark.unit
    def test_health_status_colors_non_empty(self) -> None:
        """Health status color map is non-empty."""
        assert len(HEALTH_STATUS_COLORS) > 0

    @pytest.mark.unit
    def test_phase_colors_non_empty(self) -> None:
        """Phase color map is non-empty."""
        assert len(PHASE_COLORS) > 0

    @pytest.mark.unit
    def test_color_maps_have_string_values(self) -> None:
        """All color maps map strings to strings."""
        for color_map in [SYNC_STATUS_COLORS, HEALTH_STATUS_COLORS, PHASE_COLORS]:
            for key, value in color_map.items():
                assert isinstance(key, str)
                assert isinstance(value, str)

    @pytest.mark.unit
    def test_sync_colors_cover_common_statuses(self) -> None:
        """Sync color map covers Synced and OutOfSync."""
        assert "Synced" in SYNC_STATUS_COLORS
        assert "OutOfSync" in SYNC_STATUS_COLORS

    @pytest.mark.unit
    def test_health_colors_cover_common_statuses(self) -> None:
        """Health color map covers Healthy, Degraded, Progressing."""
        assert "Healthy" in HEALTH_STATUS_COLORS
        assert "Degraded" in HEALTH_STATUS_COLORS
        assert "Progressing" in HEALTH_STATUS_COLORS

    @pytest.mark.unit
    def test_phase_colors_cover_common_phases(self) -> None:
        """Phase color map covers Healthy, Paused, Degraded."""
        assert "Healthy" in PHASE_COLORS
        assert "Paused" in PHASE_COLORS
        assert "Degraded" in PHASE_COLORS


# ============================================================================
# Constructor Tests
# ============================================================================


class TestEcosystemConstructor:
    """Tests for EcosystemScreen initialization."""

    @pytest.mark.unit
    def test_stores_client(self, mock_k8s_client: MagicMock) -> None:
        """Constructor stores the K8s client."""
        screen = EcosystemScreen(client=mock_k8s_client)
        assert screen._client is mock_k8s_client

    @pytest.mark.unit
    def test_lazy_managers_start_none(self, mock_k8s_client: MagicMock) -> None:
        """Lazy manager backing fields start as None."""
        screen = EcosystemScreen(client=mock_k8s_client)
        assert screen._EcosystemScreen__argocd_mgr is None
        assert screen._EcosystemScreen__flux_mgr is None
        assert screen._EcosystemScreen__cert_mgr is None
        assert screen._EcosystemScreen__rollouts_mgr is None


# ============================================================================
# Helper Function Tests
# ============================================================================


class TestHelperFunctions:
    """Tests for module-level helper functions."""

    @pytest.mark.unit
    def test_colorize_known_key(self) -> None:
        """_colorize applies color for known key."""
        result = _colorize("Synced", SYNC_STATUS_COLORS)
        assert result == "[green]Synced[/green]"

    @pytest.mark.unit
    def test_colorize_unknown_key(self) -> None:
        """_colorize returns plain text for unknown key."""
        result = _colorize("CustomStatus", SYNC_STATUS_COLORS)
        assert result == "CustomStatus"

    @pytest.mark.unit
    def test_ready_indicator_true(self) -> None:
        """_ready_indicator returns green Yes for True."""
        result = _ready_indicator(True)
        assert "Yes" in result
        assert "green" in result

    @pytest.mark.unit
    def test_ready_indicator_false(self) -> None:
        """_ready_indicator returns red No for False."""
        result = _ready_indicator(False)
        assert "No" in result
        assert "red" in result

    @pytest.mark.unit
    def test_flux_status_suspended(self) -> None:
        """_flux_status returns Suspended when suspended."""
        result = _flux_status(ready=False, reconciling=False, suspended=True)
        assert "Suspended" in result

    @pytest.mark.unit
    def test_flux_status_reconciling(self) -> None:
        """_flux_status returns Reconciling when reconciling."""
        result = _flux_status(ready=False, reconciling=True, suspended=False)
        assert "Reconciling" in result

    @pytest.mark.unit
    def test_flux_status_ready(self) -> None:
        """_flux_status returns Ready when ready."""
        result = _flux_status(ready=True, reconciling=False, suspended=False)
        assert "Ready" in result

    @pytest.mark.unit
    def test_flux_status_not_ready(self) -> None:
        """_flux_status returns Not Ready when none of the above."""
        result = _flux_status(ready=False, reconciling=False, suspended=False)
        assert "Not Ready" in result

    @pytest.mark.unit
    def test_flux_status_suspended_takes_priority(self) -> None:
        """Suspended takes priority over ready and reconciling."""
        result = _flux_status(ready=True, reconciling=True, suspended=True)
        assert "Suspended" in result
