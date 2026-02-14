"""Unit tests for Kubernetes TUI dashboard screen and widgets.

Tests DashboardScreen, ResourceBar, and RefreshTimer.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from textual.binding import Binding

from system_operations_manager.tui.apps.kubernetes.screens import (
    DASHBOARD_EVENT_COLUMNS,
    DASHBOARD_MAX_EVENTS,
    DASHBOARD_MAX_NAMESPACES,
    DASHBOARD_NODE_COLUMNS,
    DashboardScreen,
)
from system_operations_manager.tui.apps.kubernetes.widgets import (
    REFRESH_DEFAULT_INTERVAL,
    REFRESH_MAX_INTERVAL,
    REFRESH_MIN_INTERVAL,
    RefreshTimer,
    ResourceBar,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock KubernetesClient."""
    client = MagicMock()
    client.default_namespace = "default"
    client.get_current_context.return_value = "minikube"
    client.list_contexts.return_value = [
        {"name": "minikube", "cluster": "minikube", "namespace": "default"},
    ]
    return client


# ============================================================================
# DashboardScreen Init & Bindings Tests
# ============================================================================


class TestDashboardScreenInit:
    """Tests for DashboardScreen initialization and bindings."""

    @pytest.mark.unit
    def test_screen_has_bindings(self) -> None:
        """DashboardScreen defines keyboard bindings."""
        assert len(DashboardScreen.BINDINGS) > 0

    @pytest.mark.unit
    def test_screen_bindings_include_back(self) -> None:
        """Screen bindings include escape for back navigation."""
        binding_keys = [b.key if isinstance(b, Binding) else b[0] for b in DashboardScreen.BINDINGS]
        assert "escape" in binding_keys

    @pytest.mark.unit
    def test_screen_bindings_include_refresh(self) -> None:
        """Screen bindings include r for manual refresh."""
        binding_keys = [b.key if isinstance(b, Binding) else b[0] for b in DashboardScreen.BINDINGS]
        assert "r" in binding_keys

    @pytest.mark.unit
    def test_screen_bindings_include_interval_controls(self) -> None:
        """Screen bindings include +/- for interval adjustment."""
        binding_keys = [b.key if isinstance(b, Binding) else b[0] for b in DashboardScreen.BINDINGS]
        assert "plus" in binding_keys
        assert "minus" in binding_keys


# ============================================================================
# Dashboard Constants Tests
# ============================================================================


class TestDashboardConstants:
    """Tests for dashboard-level constants."""

    @pytest.mark.unit
    def test_node_columns_defined(self) -> None:
        """Node table has expected columns."""
        col_names = [c[0] for c in DASHBOARD_NODE_COLUMNS]
        assert "Name" in col_names
        assert "Status" in col_names
        assert "CPU" in col_names
        assert "Memory" in col_names
        assert "Pods" in col_names

    @pytest.mark.unit
    def test_event_columns_defined(self) -> None:
        """Event table has expected columns."""
        col_names = [c[0] for c in DASHBOARD_EVENT_COLUMNS]
        assert "Type" in col_names
        assert "Reason" in col_names
        assert "Message" in col_names

    @pytest.mark.unit
    def test_max_events_is_positive(self) -> None:
        """Max events limit is a positive integer."""
        assert DASHBOARD_MAX_EVENTS > 0

    @pytest.mark.unit
    def test_max_namespaces_is_positive(self) -> None:
        """Max namespaces limit is a positive integer."""
        assert DASHBOARD_MAX_NAMESPACES > 0


# ============================================================================
# CPU Parsing Tests
# ============================================================================


class TestParseCpu:
    """Tests for DashboardScreen._parse_cpu static method."""

    @pytest.mark.unit
    def test_parse_whole_cores(self) -> None:
        """Parses whole core count like '8'."""
        assert DashboardScreen._parse_cpu("8") == 8

    @pytest.mark.unit
    def test_parse_single_core(self) -> None:
        """Parses single core '1'."""
        assert DashboardScreen._parse_cpu("1") == 1

    @pytest.mark.unit
    def test_parse_millicores(self) -> None:
        """Parses millicore format like '4000m' to 4 cores."""
        assert DashboardScreen._parse_cpu("4000m") == 4

    @pytest.mark.unit
    def test_parse_millicores_rounds_down(self) -> None:
        """Millicore parsing uses integer division."""
        assert DashboardScreen._parse_cpu("2500m") == 2

    @pytest.mark.unit
    def test_parse_invalid_returns_none(self) -> None:
        """Invalid CPU string returns None."""
        assert DashboardScreen._parse_cpu("abc") is None

    @pytest.mark.unit
    def test_parse_empty_returns_none(self) -> None:
        """Empty string returns None."""
        assert DashboardScreen._parse_cpu("") is None


# ============================================================================
# Memory Parsing Tests
# ============================================================================


class TestParseMemory:
    """Tests for DashboardScreen._parse_memory static method."""

    @pytest.mark.unit
    def test_parse_gi(self) -> None:
        """Parses GiB format like '16Gi'."""
        assert DashboardScreen._parse_memory("16Gi") == 16

    @pytest.mark.unit
    def test_parse_mi(self) -> None:
        """Parses MiB format like '16384Mi' to 16 GiB."""
        assert DashboardScreen._parse_memory("16384Mi") == 16

    @pytest.mark.unit
    def test_parse_mi_rounds_down(self) -> None:
        """MiB parsing uses integer division."""
        assert DashboardScreen._parse_memory("1500Mi") == 1

    @pytest.mark.unit
    def test_parse_ki(self) -> None:
        """Parses KiB format (very large values)."""
        # 16 GiB = 16 * 1024 * 1024 KiB = 16777216 KiB
        assert DashboardScreen._parse_memory("16777216Ki") == 16

    @pytest.mark.unit
    def test_parse_invalid_returns_none(self) -> None:
        """Invalid memory string returns None."""
        assert DashboardScreen._parse_memory("abc") is None

    @pytest.mark.unit
    def test_parse_empty_returns_none(self) -> None:
        """Empty string returns None."""
        assert DashboardScreen._parse_memory("") is None


# ============================================================================
# ResourceBar Widget Tests
# ============================================================================


class TestResourceBar:
    """Tests for ResourceBar widget initialization and rendering."""

    @pytest.mark.unit
    def test_stores_capacity_and_used(self) -> None:
        """ResourceBar stores capacity and used values."""
        bar = ResourceBar(label="CPU", capacity=8, used=4, unit=" cores")
        assert bar._capacity == 8
        assert bar._used == 4
        assert bar._label == "CPU"
        assert bar._unit == " cores"

    @pytest.mark.unit
    def test_stores_none_used(self) -> None:
        """ResourceBar stores None for unknown usage."""
        bar = ResourceBar(label="CPU", capacity=8, used=None)
        assert bar._used is None

    @pytest.mark.unit
    def test_render_bar_with_known_usage_green(self) -> None:
        """50% utilization renders with green color."""
        bar = ResourceBar(label="CPU", capacity=10, used=5, bar_width=10)
        rendered = bar._render_bar()
        assert "5/10" in rendered
        assert "green" in rendered

    @pytest.mark.unit
    def test_render_bar_high_usage_yellow(self) -> None:
        """75% utilization renders with yellow color."""
        bar = ResourceBar(label="CPU", capacity=100, used=75, bar_width=10)
        rendered = bar._render_bar()
        assert "yellow" in rendered

    @pytest.mark.unit
    def test_render_bar_critical_usage_red(self) -> None:
        """95% utilization renders with red color."""
        bar = ResourceBar(label="CPU", capacity=100, used=95, bar_width=10)
        rendered = bar._render_bar()
        assert "red" in rendered

    @pytest.mark.unit
    def test_render_bar_unknown_usage(self) -> None:
        """Unknown usage renders N/A and question marks."""
        bar = ResourceBar(label="CPU", capacity=8, used=None, bar_width=10)
        rendered = bar._render_bar()
        assert "N/A" in rendered
        assert "?" in rendered

    @pytest.mark.unit
    def test_render_bar_zero_capacity(self) -> None:
        """Zero capacity does not cause division error."""
        bar = ResourceBar(label="CPU", capacity=0, used=0, bar_width=10)
        rendered = bar._render_bar()
        assert "0/0" in rendered

    @pytest.mark.unit
    def test_default_bar_width(self) -> None:
        """Default bar width is 20."""
        bar = ResourceBar(label="CPU", capacity=8)
        assert bar._bar_width == 20


# ============================================================================
# RefreshTimer Widget Tests
# ============================================================================


class TestRefreshTimer:
    """Tests for RefreshTimer widget initialization and controls."""

    @pytest.mark.unit
    def test_default_interval(self) -> None:
        """Default interval matches the constant."""
        timer = RefreshTimer()
        assert timer._interval == REFRESH_DEFAULT_INTERVAL

    @pytest.mark.unit
    def test_custom_interval(self) -> None:
        """Custom interval is stored."""
        timer = RefreshTimer(interval=60)
        assert timer._interval == 60
        assert timer._remaining == 60

    @pytest.mark.unit
    def test_increase_interval(self) -> None:
        """Increasing interval adds 5 seconds."""
        timer = RefreshTimer(interval=30)
        with patch.object(timer, "_update_display"):
            timer.increase_interval()
        assert timer._interval == 35

    @pytest.mark.unit
    def test_increase_interval_caps_at_max(self) -> None:
        """Interval cannot exceed maximum."""
        timer = RefreshTimer(interval=REFRESH_MAX_INTERVAL)
        with patch.object(timer, "_update_display"):
            timer.increase_interval()
        assert timer._interval == REFRESH_MAX_INTERVAL

    @pytest.mark.unit
    def test_decrease_interval(self) -> None:
        """Decreasing interval removes 5 seconds."""
        timer = RefreshTimer(interval=30)
        with patch.object(timer, "_update_display"):
            timer.decrease_interval()
        assert timer._interval == 25

    @pytest.mark.unit
    def test_decrease_interval_caps_at_min(self) -> None:
        """Interval cannot go below minimum."""
        timer = RefreshTimer(interval=REFRESH_MIN_INTERVAL)
        with patch.object(timer, "_update_display"):
            timer.decrease_interval()
        assert timer._interval == REFRESH_MIN_INTERVAL

    @pytest.mark.unit
    def test_reset_restores_remaining(self) -> None:
        """Reset sets remaining back to full interval."""
        timer = RefreshTimer(interval=30)
        timer._remaining = 5
        with patch.object(timer, "_update_display"):
            timer.reset()
        assert timer._remaining == 30

    @pytest.mark.unit
    def test_pause_sets_flag(self) -> None:
        """Pause sets the paused flag."""
        timer = RefreshTimer()
        timer.pause()
        assert timer._paused is True

    @pytest.mark.unit
    def test_resume_clears_flag(self) -> None:
        """Resume clears the paused flag."""
        timer = RefreshTimer()
        timer.pause()
        timer.resume()
        assert timer._paused is False

    @pytest.mark.unit
    def test_refresh_triggered_message(self) -> None:
        """RefreshTriggered message can be instantiated."""
        msg = RefreshTimer.RefreshTriggered()
        assert msg is not None

    @pytest.mark.unit
    def test_interval_changed_message(self) -> None:
        """IntervalChanged message stores the interval."""
        msg = RefreshTimer.IntervalChanged(45)
        assert msg.interval == 45

    @pytest.mark.unit
    def test_tick_decrements_remaining(self) -> None:
        """Each tick decrements the remaining counter."""
        timer = RefreshTimer(interval=30)
        timer._remaining = 10
        with patch.object(timer, "query_one"):
            timer._tick()
        assert timer._remaining == 9

    @pytest.mark.unit
    def test_tick_paused_does_not_decrement(self) -> None:
        """Tick does nothing when paused."""
        timer = RefreshTimer(interval=30)
        timer._remaining = 10
        timer._paused = True
        timer._tick()
        assert timer._remaining == 10


# ============================================================================
# DashboardScreen Integration with App Tests
# ============================================================================


class TestDashboardAppIntegration:
    """Tests for dashboard integration with KubernetesApp."""

    @pytest.mark.unit
    def test_app_has_dashboard_binding(self) -> None:
        """KubernetesApp includes 'd' binding for dashboard."""
        from system_operations_manager.tui.apps.kubernetes.app import KubernetesApp

        binding_keys = [b.key if isinstance(b, Binding) else b[0] for b in KubernetesApp.BINDINGS]
        assert "d" in binding_keys

    @pytest.mark.unit
    def test_dashboard_screen_stores_client(self, mock_client: MagicMock) -> None:
        """DashboardScreen stores the client reference."""
        screen = DashboardScreen(client=mock_client)
        assert screen._client is mock_client
