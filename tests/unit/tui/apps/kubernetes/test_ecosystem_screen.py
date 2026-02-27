"""Unit tests for Kubernetes TUI ecosystem screen.

Tests EcosystemScreen bindings, constants, color maps,
constructor, and default state.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock, PropertyMock, patch

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


# ============================================================================
# Helper
# ============================================================================

from system_operations_manager.integrations.kubernetes.exceptions import (  # noqa: E402
    KubernetesNotFoundError,
)


def _make_ecosystem_screen() -> EcosystemScreen:
    """Create an EcosystemScreen bypassing __init__."""
    screen = EcosystemScreen.__new__(EcosystemScreen)
    screen._client = MagicMock()
    screen.go_back = MagicMock()
    screen.notify_user = MagicMock()
    screen._EcosystemScreen__argocd_mgr = None
    screen._EcosystemScreen__flux_mgr = None
    screen._EcosystemScreen__cert_mgr = None
    screen._EcosystemScreen__rollouts_mgr = None
    mock_table = MagicMock()
    screen.query_one = MagicMock(return_value=mock_table)
    return screen


@pytest.fixture(autouse=True)
def _patch_ecosystem_app() -> Iterator[None]:
    """Patch 'app' property on EcosystemScreen for all tests in this module.

    The Textual MessagePump.app property is read-only. We need to
    replace it with a mock so that _load_* methods can call
    self.app.call_from_thread(...).
    """
    mock_app = MagicMock()
    mock_app.call_from_thread = MagicMock(side_effect=lambda fn, *a, **kw: fn(*a, **kw))
    with patch.object(EcosystemScreen, "app", new_callable=PropertyMock, return_value=mock_app):
        yield


# ============================================================================
# Lazy Manager Property Tests
# ============================================================================


@pytest.mark.unit
class TestLazyManagerProperties:
    """Tests for lazy manager property accessors."""

    def test_argocd_mgr_creates_on_first_access(self) -> None:
        """_argocd_mgr creates ArgoCDManager on first access."""
        screen = _make_ecosystem_screen()
        with patch(
            "system_operations_manager.services.kubernetes.argocd_manager.ArgoCDManager"
        ) as mock_cls:
            mock_cls.return_value = MagicMock()
            mgr = screen._argocd_mgr
            assert mgr is mock_cls.return_value

    def test_argocd_mgr_caches_on_second_access(self) -> None:
        """_argocd_mgr returns cached on second access."""
        screen = _make_ecosystem_screen()
        cached = MagicMock()
        screen._EcosystemScreen__argocd_mgr = cached
        assert screen._argocd_mgr is cached

    def test_flux_mgr_creates_on_first_access(self) -> None:
        """_flux_mgr creates FluxManager on first access."""
        screen = _make_ecosystem_screen()
        with patch(
            "system_operations_manager.services.kubernetes.flux_manager.FluxManager"
        ) as mock_cls:
            mock_cls.return_value = MagicMock()
            mgr = screen._flux_mgr
            assert mgr is mock_cls.return_value

    def test_cert_mgr_creates_on_first_access(self) -> None:
        """_cert_mgr creates CertManagerManager on first access."""
        screen = _make_ecosystem_screen()
        with patch(
            "system_operations_manager.services.kubernetes.certmanager_manager.CertManagerManager"
        ) as mock_cls:
            mock_cls.return_value = MagicMock()
            mgr = screen._cert_mgr
            assert mgr is mock_cls.return_value

    def test_rollouts_mgr_creates_on_first_access(self) -> None:
        """_rollouts_mgr creates RolloutsManager on first access."""
        screen = _make_ecosystem_screen()
        with patch(
            "system_operations_manager.services.kubernetes.rollouts_manager.RolloutsManager"
        ) as mock_cls:
            mock_cls.return_value = MagicMock()
            mgr = screen._rollouts_mgr
            assert mgr is mock_cls.return_value


# ============================================================================
# Add Info Row Tests
# ============================================================================


@pytest.mark.unit
class TestAddInfoRow:
    """Tests for _add_info_row helper."""

    def test_adds_info_row_to_table(self) -> None:
        """_add_info_row adds a dimmed message row."""
        screen = _make_ecosystem_screen()
        mock_table = MagicMock()
        screen.query_one = MagicMock(return_value=mock_table)
        screen._add_info_row("argocd-table", "No data", 6)
        mock_table.add_row.assert_called_once()
        args = mock_table.add_row.call_args[0]
        assert "No data" in args[0]
        assert len(args) == 6


# ============================================================================
# Ecosystem Action Tests
# ============================================================================


@pytest.mark.unit
class TestEcosystemActions:
    """Tests for EcosystemScreen keyboard actions."""

    def test_action_back(self) -> None:
        """action_back calls go_back."""
        screen = _make_ecosystem_screen()
        screen.action_back()
        screen.go_back.assert_called_once()

    def test_action_refresh(self) -> None:
        """action_refresh calls _refresh_all."""
        screen = _make_ecosystem_screen()
        screen._refresh_all = MagicMock()
        screen.action_refresh()
        screen._refresh_all.assert_called_once()

    def test_action_focus_argocd(self) -> None:
        """action_focus_argocd focuses the argocd table."""
        screen = _make_ecosystem_screen()
        mock_table = MagicMock()
        screen.query_one = MagicMock(return_value=mock_table)
        screen.action_focus_argocd()
        mock_table.focus.assert_called_once()

    def test_action_focus_flux(self) -> None:
        """action_focus_flux focuses the flux table."""
        screen = _make_ecosystem_screen()
        mock_table = MagicMock()
        screen.query_one = MagicMock(return_value=mock_table)
        screen.action_focus_flux()
        mock_table.focus.assert_called_once()

    def test_action_focus_certs(self) -> None:
        """action_focus_certs focuses the cert table."""
        screen = _make_ecosystem_screen()
        mock_table = MagicMock()
        screen.query_one = MagicMock(return_value=mock_table)
        screen.action_focus_certs()
        mock_table.focus.assert_called_once()

    def test_action_focus_rollouts(self) -> None:
        """action_focus_rollouts focuses the rollouts table."""
        screen = _make_ecosystem_screen()
        mock_table = MagicMock()
        screen.query_one = MagicMock(return_value=mock_table)
        screen.action_focus_rollouts()
        mock_table.focus.assert_called_once()


# ============================================================================
# Load ArgoCD Tests
# ============================================================================


@pytest.mark.unit
class TestLoadArgocd:
    """Tests for _load_argocd worker method."""

    def test_with_apps(self) -> None:
        """_load_argocd adds rows for ArgoCD apps."""
        screen = _make_ecosystem_screen()
        mock_mgr = MagicMock()
        app_obj = MagicMock()
        app_obj.name = "my-app"
        app_obj.namespace = "argocd"
        app_obj.project = "default"
        app_obj.sync_status = "Synced"
        app_obj.health_status = "Healthy"
        app_obj.repo_url = "https://git.example.com"
        mock_mgr.list_applications.return_value = [app_obj]
        screen._EcosystemScreen__argocd_mgr = mock_mgr
        mock_table = MagicMock()
        screen.query_one = MagicMock(return_value=mock_table)
        EcosystemScreen._load_argocd.__wrapped__(screen)
        mock_table.add_row.assert_called_once()

    def test_empty_apps(self) -> None:
        """_load_argocd shows info row when no apps found."""
        screen = _make_ecosystem_screen()
        mock_mgr = MagicMock()
        mock_mgr.list_applications.return_value = []
        screen._EcosystemScreen__argocd_mgr = mock_mgr
        screen._add_info_row = MagicMock()
        EcosystemScreen._load_argocd.__wrapped__(screen)
        screen._add_info_row.assert_called_once()

    def test_not_found_error(self) -> None:
        """_load_argocd handles KubernetesNotFoundError."""
        screen = _make_ecosystem_screen()
        mock_mgr = MagicMock()
        mock_mgr.list_applications.side_effect = KubernetesNotFoundError("CRD missing")
        screen._EcosystemScreen__argocd_mgr = mock_mgr
        screen._add_info_row = MagicMock()
        EcosystemScreen._load_argocd.__wrapped__(screen)
        screen._add_info_row.assert_called_once()

    def test_generic_error(self) -> None:
        """_load_argocd handles generic exceptions."""
        screen = _make_ecosystem_screen()
        mock_mgr = MagicMock()
        mock_mgr.list_applications.side_effect = RuntimeError("boom")
        screen._EcosystemScreen__argocd_mgr = mock_mgr
        screen._add_info_row = MagicMock()
        EcosystemScreen._load_argocd.__wrapped__(screen)
        screen._add_info_row.assert_called_once()


# ============================================================================
# Load Flux Tests
# ============================================================================


@pytest.mark.unit
class TestLoadFlux:
    """Tests for _load_flux worker method."""

    def _make_flux_screen(self) -> tuple[EcosystemScreen, MagicMock]:
        screen = _make_ecosystem_screen()
        mock_mgr = MagicMock()
        screen._EcosystemScreen__flux_mgr = mock_mgr
        return screen, mock_mgr

    def test_with_resources(self) -> None:
        """_load_flux adds rows for git repos, kustomizations, and helm releases."""
        screen, mgr = self._make_flux_screen()
        repo = MagicMock(
            name="repo1",
            namespace="flux",
            ready=True,
            reconciling=False,
            suspended=False,
            artifact_revision="abc",
        )
        ks = MagicMock(
            name="ks1",
            namespace="flux",
            ready=True,
            reconciling=False,
            suspended=False,
            last_applied_revision="def",
        )
        hr = MagicMock(
            name="hr1",
            namespace="flux",
            ready=True,
            reconciling=False,
            suspended=False,
            chart_name="nginx",
        )
        mgr.list_git_repositories.return_value = [repo]
        mgr.list_kustomizations.return_value = [ks]
        mgr.list_helm_releases.return_value = [hr]
        mock_table = MagicMock()
        screen.query_one = MagicMock(return_value=mock_table)
        EcosystemScreen._load_flux.__wrapped__(screen)
        assert mock_table.add_row.call_count == 3

    def test_empty_resources(self) -> None:
        """_load_flux shows info row when all lists empty."""
        screen, mgr = self._make_flux_screen()
        mgr.list_git_repositories.return_value = []
        mgr.list_kustomizations.return_value = []
        mgr.list_helm_releases.return_value = []
        screen._add_info_row = MagicMock()
        EcosystemScreen._load_flux.__wrapped__(screen)
        screen._add_info_row.assert_called_once()

    def test_not_found_error(self) -> None:
        """_load_flux handles KubernetesNotFoundError."""
        screen, mgr = self._make_flux_screen()
        mgr.list_git_repositories.side_effect = KubernetesNotFoundError("missing")
        screen._add_info_row = MagicMock()
        EcosystemScreen._load_flux.__wrapped__(screen)
        screen._add_info_row.assert_called_once()

    def test_generic_error(self) -> None:
        """_load_flux handles generic exceptions."""
        screen, mgr = self._make_flux_screen()
        mgr.list_git_repositories.side_effect = RuntimeError("boom")
        screen._add_info_row = MagicMock()
        EcosystemScreen._load_flux.__wrapped__(screen)
        screen._add_info_row.assert_called_once()


# ============================================================================
# Load Certs Tests
# ============================================================================


@pytest.mark.unit
class TestLoadCerts:
    """Tests for _load_certs worker method."""

    def test_with_certs(self) -> None:
        """_load_certs adds rows for certificates."""
        screen = _make_ecosystem_screen()
        mock_mgr = MagicMock()
        cert = MagicMock()
        cert.name = "my-cert"
        cert.namespace = "default"
        cert.ready = True
        cert.not_after = "2027-01-01"
        cert.issuer_name = "letsencrypt"
        cert.dns_names = ["example.com", "www.example.com"]
        mock_mgr.list_certificates.return_value = [cert]
        screen._EcosystemScreen__cert_mgr = mock_mgr
        mock_table = MagicMock()
        screen.query_one = MagicMock(return_value=mock_table)
        EcosystemScreen._load_certs.__wrapped__(screen)
        mock_table.add_row.assert_called_once()

    def test_cert_with_many_dns_names(self) -> None:
        """_load_certs truncates >3 DNS names."""
        screen = _make_ecosystem_screen()
        mock_mgr = MagicMock()
        cert = MagicMock()
        cert.name = "big-cert"
        cert.namespace = "default"
        cert.ready = True
        cert.not_after = "2027-01-01"
        cert.issuer_name = "letsencrypt"
        cert.dns_names = ["a.com", "b.com", "c.com", "d.com", "e.com"]
        mock_mgr.list_certificates.return_value = [cert]
        screen._EcosystemScreen__cert_mgr = mock_mgr
        mock_table = MagicMock()
        screen.query_one = MagicMock(return_value=mock_table)
        EcosystemScreen._load_certs.__wrapped__(screen)
        call_args = mock_table.add_row.call_args[0]
        assert "(+2)" in call_args[5]

    def test_cert_with_none_not_after(self) -> None:
        """_load_certs shows N/A for None not_after."""
        screen = _make_ecosystem_screen()
        mock_mgr = MagicMock()
        cert = MagicMock()
        cert.name = "no-expiry"
        cert.namespace = "default"
        cert.ready = False
        cert.not_after = None
        cert.issuer_name = "self-signed"
        cert.dns_names = ["internal.local"]
        mock_mgr.list_certificates.return_value = [cert]
        screen._EcosystemScreen__cert_mgr = mock_mgr
        mock_table = MagicMock()
        screen.query_one = MagicMock(return_value=mock_table)
        EcosystemScreen._load_certs.__wrapped__(screen)
        call_args = mock_table.add_row.call_args[0]
        assert call_args[3] == "N/A"

    def test_empty_certs(self) -> None:
        """_load_certs shows info row when no certs."""
        screen = _make_ecosystem_screen()
        mock_mgr = MagicMock()
        mock_mgr.list_certificates.return_value = []
        screen._EcosystemScreen__cert_mgr = mock_mgr
        screen._add_info_row = MagicMock()
        EcosystemScreen._load_certs.__wrapped__(screen)
        screen._add_info_row.assert_called_once()

    def test_not_found_error(self) -> None:
        """_load_certs handles KubernetesNotFoundError."""
        screen = _make_ecosystem_screen()
        mock_mgr = MagicMock()
        mock_mgr.list_certificates.side_effect = KubernetesNotFoundError("missing")
        screen._EcosystemScreen__cert_mgr = mock_mgr
        screen._add_info_row = MagicMock()
        EcosystemScreen._load_certs.__wrapped__(screen)
        screen._add_info_row.assert_called_once()


# ============================================================================
# Load Rollouts Tests
# ============================================================================


@pytest.mark.unit
class TestLoadRollouts:
    """Tests for _load_rollouts worker method."""

    def test_with_canary_rollout(self) -> None:
        """_load_rollouts adds row with weight for canary strategy."""
        screen = _make_ecosystem_screen()
        mock_mgr = MagicMock()
        ro = MagicMock()
        ro.name = "my-rollout"
        ro.namespace = "default"
        ro.strategy = "canary"
        ro.phase = "Healthy"
        ro.ready_replicas = 3
        ro.replicas = 3
        ro.canary_weight = 50
        mock_mgr.list_rollouts.return_value = [ro]
        screen._EcosystemScreen__rollouts_mgr = mock_mgr
        mock_table = MagicMock()
        screen.query_one = MagicMock(return_value=mock_table)
        EcosystemScreen._load_rollouts.__wrapped__(screen)
        call_args = mock_table.add_row.call_args[0]
        assert "50%" in call_args[5]

    def test_with_bluegreen_rollout(self) -> None:
        """_load_rollouts shows '-' for blueGreen weight."""
        screen = _make_ecosystem_screen()
        mock_mgr = MagicMock()
        ro = MagicMock()
        ro.name = "bg-rollout"
        ro.namespace = "default"
        ro.strategy = "blueGreen"
        ro.phase = "Healthy"
        ro.ready_replicas = 2
        ro.replicas = 2
        ro.canary_weight = 0
        mock_mgr.list_rollouts.return_value = [ro]
        screen._EcosystemScreen__rollouts_mgr = mock_mgr
        mock_table = MagicMock()
        screen.query_one = MagicMock(return_value=mock_table)
        EcosystemScreen._load_rollouts.__wrapped__(screen)
        call_args = mock_table.add_row.call_args[0]
        assert call_args[5] == "-"

    def test_empty_rollouts(self) -> None:
        """_load_rollouts shows info row when none found."""
        screen = _make_ecosystem_screen()
        mock_mgr = MagicMock()
        mock_mgr.list_rollouts.return_value = []
        screen._EcosystemScreen__rollouts_mgr = mock_mgr
        screen._add_info_row = MagicMock()
        EcosystemScreen._load_rollouts.__wrapped__(screen)
        screen._add_info_row.assert_called_once()

    def test_not_found_error(self) -> None:
        """_load_rollouts handles KubernetesNotFoundError."""
        screen = _make_ecosystem_screen()
        mock_mgr = MagicMock()
        mock_mgr.list_rollouts.side_effect = KubernetesNotFoundError("missing")
        screen._EcosystemScreen__rollouts_mgr = mock_mgr
        screen._add_info_row = MagicMock()
        EcosystemScreen._load_rollouts.__wrapped__(screen)
        screen._add_info_row.assert_called_once()

    def test_generic_error(self) -> None:
        """_load_rollouts handles generic exceptions."""
        screen = _make_ecosystem_screen()
        mock_mgr = MagicMock()
        mock_mgr.list_rollouts.side_effect = RuntimeError("connection failed")
        screen._EcosystemScreen__rollouts_mgr = mock_mgr
        screen._add_info_row = MagicMock()
        EcosystemScreen._load_rollouts.__wrapped__(screen)
        screen._add_info_row.assert_called_once()
        assert "Error" in screen._add_info_row.call_args[0][1]


# ============================================================================
# Certs Generic Error Tests
# ============================================================================


@pytest.mark.unit
class TestLoadCertsGenericError:
    """Tests for _load_certs generic Exception branch."""

    def test_generic_error(self) -> None:
        """_load_certs handles generic exceptions."""
        screen = _make_ecosystem_screen()
        mock_mgr = MagicMock()
        mock_mgr.list_certificates.side_effect = RuntimeError("timeout")
        screen._EcosystemScreen__cert_mgr = mock_mgr
        screen._add_info_row = MagicMock()
        EcosystemScreen._load_certs.__wrapped__(screen)
        screen._add_info_row.assert_called_once()
        assert "Error" in screen._add_info_row.call_args[0][1]


# ============================================================================
# Setup Tables / Refresh / Event Handlers
# ============================================================================


@pytest.mark.unit
class TestSetupTables:
    """Tests for _setup_tables DataTable configuration."""

    def test_setup_tables_configures_four_tables(self) -> None:
        """_setup_tables configures all four DataTables."""
        screen = _make_ecosystem_screen()
        tables: dict[str, MagicMock] = {}

        def _query(selector: str, *a: Any, **kw: Any) -> MagicMock:
            tid = selector.lstrip("#")
            if tid not in tables:
                tables[tid] = MagicMock()
            return tables[tid]

        screen.query_one = MagicMock(side_effect=_query)
        screen._setup_tables()

        for tid in ("argocd-table", "flux-table", "cert-table", "rollouts-table"):
            tbl = tables[tid]
            assert tbl.cursor_type == "row"
            assert tbl.zebra_stripes is True
            assert tbl.add_column.call_count > 0


@pytest.mark.unit
class TestRefreshAll:
    """Tests for _refresh_all dispatch."""

    def test_refresh_all_calls_all_loaders(self) -> None:
        """_refresh_all triggers all four load methods."""
        screen = _make_ecosystem_screen()
        screen._load_argocd = MagicMock()
        screen._load_flux = MagicMock()
        screen._load_certs = MagicMock()
        screen._load_rollouts = MagicMock()
        screen._refresh_all()
        screen._load_argocd.assert_called_once()
        screen._load_flux.assert_called_once()
        screen._load_certs.assert_called_once()
        screen._load_rollouts.assert_called_once()


@pytest.mark.unit
class TestEcosystemEventHandlers:
    """Tests for event handler methods."""

    def test_handle_auto_refresh_calls_refresh_all(self) -> None:
        """handle_auto_refresh delegates to _refresh_all."""
        screen = _make_ecosystem_screen()
        screen._refresh_all = MagicMock()
        event = MagicMock()
        screen.handle_auto_refresh(event)
        screen._refresh_all.assert_called_once()

    def test_handle_interval_changed_notifies(self) -> None:
        """handle_interval_changed notifies user with interval."""
        screen = _make_ecosystem_screen()
        event = MagicMock()
        event.interval = 45
        screen.handle_interval_changed(event)
        screen.notify_user.assert_called_once()
        assert "45" in screen.notify_user.call_args[0][0]
