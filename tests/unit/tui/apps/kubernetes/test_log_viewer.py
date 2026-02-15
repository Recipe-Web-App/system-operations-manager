"""Unit tests for Kubernetes TUI log viewer screen.

Tests LogViewerScreen bindings, constructor, header building,
and default state.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from textual.binding import Binding

from system_operations_manager.integrations.kubernetes.models.workloads import (
    ContainerStatus,
    PodSummary,
)
from system_operations_manager.tui.apps.kubernetes.log_viewer import (
    TAIL_LINES_FOLLOW,
    TAIL_LINES_STATIC,
    LogViewerScreen,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture()
def sample_pod_with_containers() -> PodSummary:
    """Create a sample pod with multiple containers."""
    return PodSummary(
        name="nginx-abc123",
        namespace="default",
        phase="Running",
        ready_count=2,
        total_count=2,
        restarts=0,
        containers=[
            ContainerStatus(name="nginx", image="nginx:1.25", ready=True, state="running"),
            ContainerStatus(name="sidecar", image="envoy:latest", ready=True, state="running"),
        ],
    )


@pytest.fixture()
def sample_pod_single_container() -> PodSummary:
    """Create a sample pod with one container."""
    return PodSummary(
        name="simple-pod",
        namespace="default",
        phase="Running",
        ready_count=1,
        total_count=1,
        restarts=0,
        containers=[
            ContainerStatus(name="app", image="myapp:1.0", ready=True, state="running"),
        ],
    )


# ============================================================================
# Binding Tests
# ============================================================================


def _binding_keys() -> list[str]:
    """Extract binding key strings from LogViewerScreen."""
    return [b.key if isinstance(b, Binding) else b[0] for b in LogViewerScreen.BINDINGS]


class TestLogViewerBindings:
    """Tests for LogViewerScreen key bindings."""

    @pytest.mark.unit
    def test_has_bindings(self) -> None:
        """Screen defines bindings."""
        assert len(LogViewerScreen.BINDINGS) > 0

    @pytest.mark.unit
    def test_escape_binding(self) -> None:
        """Escape navigates back."""
        assert "escape" in _binding_keys()

    @pytest.mark.unit
    def test_container_select_binding(self) -> None:
        """'c' opens container selector."""
        assert "c" in _binding_keys()

    @pytest.mark.unit
    def test_follow_toggle_binding(self) -> None:
        """'f' toggles follow mode."""
        assert "f" in _binding_keys()

    @pytest.mark.unit
    def test_space_toggle_binding(self) -> None:
        """Space toggles follow mode."""
        assert "space" in _binding_keys()

    @pytest.mark.unit
    def test_timestamps_binding(self) -> None:
        """'t' toggles timestamps."""
        assert "t" in _binding_keys()

    @pytest.mark.unit
    def test_clear_binding(self) -> None:
        """Ctrl+L clears log output."""
        assert "ctrl+l" in _binding_keys()

    @pytest.mark.unit
    def test_scroll_top_binding(self) -> None:
        """'g' scrolls to top."""
        assert "g" in _binding_keys()

    @pytest.mark.unit
    def test_scroll_bottom_binding(self) -> None:
        """'G' scrolls to bottom."""
        assert "G" in _binding_keys()


# ============================================================================
# Constructor Tests
# ============================================================================


class TestLogViewerConstructor:
    """Tests for LogViewerScreen initialization."""

    @pytest.mark.unit
    def test_stores_resource(self, sample_pod_with_containers: PodSummary) -> None:
        """Constructor stores the pod resource."""
        client = MagicMock()
        screen = LogViewerScreen(resource=sample_pod_with_containers, client=client)
        assert screen._resource.name == "nginx-abc123"

    @pytest.mark.unit
    def test_stores_client(self, sample_pod_with_containers: PodSummary) -> None:
        """Constructor stores the K8s client."""
        client = MagicMock()
        screen = LogViewerScreen(resource=sample_pod_with_containers, client=client)
        assert screen._client is client

    @pytest.mark.unit
    def test_container_defaults_to_none(self, sample_pod_with_containers: PodSummary) -> None:
        """Container is None before mount (set during on_mount)."""
        client = MagicMock()
        screen = LogViewerScreen(resource=sample_pod_with_containers, client=client)
        assert screen._container is None

    @pytest.mark.unit
    def test_initial_container_parameter(self, sample_pod_with_containers: PodSummary) -> None:
        """initial_container parameter sets starting container."""
        client = MagicMock()
        screen = LogViewerScreen(
            resource=sample_pod_with_containers,
            client=client,
            initial_container="sidecar",
        )
        assert screen._container == "sidecar"

    @pytest.mark.unit
    def test_following_defaults_true(self, sample_pod_with_containers: PodSummary) -> None:
        """Follow mode is enabled by default."""
        client = MagicMock()
        screen = LogViewerScreen(resource=sample_pod_with_containers, client=client)
        assert screen._following is True

    @pytest.mark.unit
    def test_timestamps_defaults_false(self, sample_pod_with_containers: PodSummary) -> None:
        """Timestamp display is disabled by default."""
        client = MagicMock()
        screen = LogViewerScreen(resource=sample_pod_with_containers, client=client)
        assert screen._show_timestamps is False


# ============================================================================
# Header Builder Tests
# ============================================================================


class TestLogViewerHeader:
    """Tests for _build_header text generation."""

    @pytest.mark.unit
    def test_header_includes_pod_name(self, sample_pod_with_containers: PodSummary) -> None:
        """Header contains the pod name."""
        screen = LogViewerScreen.__new__(LogViewerScreen)
        screen._resource = sample_pod_with_containers
        header = screen._build_header()
        assert "nginx-abc123" in header

    @pytest.mark.unit
    def test_header_includes_namespace(self, sample_pod_with_containers: PodSummary) -> None:
        """Header contains the namespace."""
        screen = LogViewerScreen.__new__(LogViewerScreen)
        screen._resource = sample_pod_with_containers
        header = screen._build_header()
        assert "default" in header
        assert "ns:" in header

    @pytest.mark.unit
    def test_header_no_namespace(self) -> None:
        """Header omits namespace section when None."""
        pod = PodSummary(
            name="orphan-pod",
            namespace=None,
            phase="Running",
            ready_count=1,
            total_count=1,
            restarts=0,
        )
        screen = LogViewerScreen.__new__(LogViewerScreen)
        screen._resource = pod
        header = screen._build_header()
        assert "orphan-pod" in header
        assert "ns:" not in header

    @pytest.mark.unit
    def test_header_includes_label(self, sample_pod_with_containers: PodSummary) -> None:
        """Header includes 'Pod Logs' label."""
        screen = LogViewerScreen.__new__(LogViewerScreen)
        screen._resource = sample_pod_with_containers
        header = screen._build_header()
        assert "Pod Logs" in header


# ============================================================================
# Container Label Tests
# ============================================================================


class TestLogViewerContainerLabel:
    """Tests for _build_container_label text generation."""

    @pytest.mark.unit
    def test_label_with_container(self) -> None:
        """Label shows container name."""
        screen = LogViewerScreen.__new__(LogViewerScreen)
        screen._container = "nginx"
        label = screen._build_container_label()
        assert "nginx" in label
        assert "Container:" in label

    @pytest.mark.unit
    def test_label_without_container(self) -> None:
        """Label shows N/A when no container set."""
        screen = LogViewerScreen.__new__(LogViewerScreen)
        screen._container = None
        label = screen._build_container_label()
        assert "N/A" in label


# ============================================================================
# Constants Tests
# ============================================================================


class TestLogViewerConstants:
    """Tests for log viewer constants."""

    @pytest.mark.unit
    def test_tail_lines_follow_is_positive(self) -> None:
        """Follow tail lines is a positive integer."""
        assert TAIL_LINES_FOLLOW > 0

    @pytest.mark.unit
    def test_tail_lines_static_is_positive(self) -> None:
        """Static tail lines is a positive integer."""
        assert TAIL_LINES_STATIC > 0

    @pytest.mark.unit
    def test_static_tail_greater_than_follow(self) -> None:
        """Static mode fetches more lines than follow mode."""
        assert TAIL_LINES_STATIC >= TAIL_LINES_FOLLOW
