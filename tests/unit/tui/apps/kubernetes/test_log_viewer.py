"""Unit tests for Kubernetes TUI log viewer screen.

Tests LogViewerScreen bindings, constructor, header building,
and default state.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, PropertyMock, patch

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


# ============================================================================
# Helpers
# ============================================================================


def _make_log_viewer() -> LogViewerScreen:
    """Create a LogViewerScreen bypassing __init__ for unit testing."""
    screen = LogViewerScreen.__new__(LogViewerScreen)
    screen._resource = PodSummary(
        name="nginx-abc123",
        namespace="default",
        phase="Running",
        ready_count=1,
        total_count=1,
        restarts=0,
        containers=[
            ContainerStatus(name="nginx", image="nginx:1.25", ready=True, state="running"),
            ContainerStatus(name="sidecar", image="envoy:latest", ready=True, state="running"),
        ],
    )
    screen._client = MagicMock()
    screen._container = "nginx"
    screen._following = True
    screen._show_timestamps = False
    screen._LogViewerScreen__streaming_mgr = None
    screen._log_worker = None
    screen.go_back = MagicMock()
    screen.notify_user = MagicMock()
    screen.query_one = MagicMock()
    return screen


# ============================================================================
# Streaming Manager Property Tests
# ============================================================================


@pytest.mark.unit
class TestStreamingMgrProperty:
    """Tests for the lazy _streaming_mgr property."""

    def test_second_access_returns_cached_instance(self) -> None:
        """Subsequent access to _streaming_mgr returns the cached instance."""
        screen = _make_log_viewer()
        cached = MagicMock()
        screen._LogViewerScreen__streaming_mgr = cached
        assert screen._streaming_mgr is cached

    def test_first_access_creates_and_caches(self) -> None:
        """First access creates a StreamingManager and caches it."""
        import unittest.mock as _um

        screen = _make_log_viewer()
        screen._LogViewerScreen__streaming_mgr = None
        fake_mgr = MagicMock()
        mock_cls = MagicMock(return_value=fake_mgr)

        with _um.patch.dict(
            "sys.modules",
            {
                "system_operations_manager.services.kubernetes.streaming_manager": MagicMock(
                    StreamingManager=mock_cls
                )
            },
        ):
            result = screen._streaming_mgr

        assert result is fake_mgr
        assert screen._LogViewerScreen__streaming_mgr is fake_mgr


# ============================================================================
# Start / Cancel Log Stream Tests
# ============================================================================


@pytest.mark.unit
class TestStartLogStream:
    """Tests for _start_log_stream dispatch logic."""

    def test_calls_stream_follow_when_following(self) -> None:
        """_start_log_stream dispatches to _stream_follow_logs when following."""
        screen = _make_log_viewer()
        screen._following = True
        fake_worker = MagicMock()
        screen._stream_follow_logs = MagicMock(return_value=fake_worker)
        screen._load_static_logs = MagicMock()
        screen._cancel_log_worker = MagicMock()

        screen._start_log_stream()

        screen._stream_follow_logs.assert_called_once()
        screen._load_static_logs.assert_not_called()
        assert screen._log_worker is fake_worker

    def test_calls_load_static_when_not_following(self) -> None:
        """_start_log_stream dispatches to _load_static_logs when paused."""
        screen = _make_log_viewer()
        screen._following = False
        fake_worker = MagicMock()
        screen._stream_follow_logs = MagicMock()
        screen._load_static_logs = MagicMock(return_value=fake_worker)
        screen._cancel_log_worker = MagicMock()

        screen._start_log_stream()

        screen._load_static_logs.assert_called_once()
        assert screen._log_worker is fake_worker


@pytest.mark.unit
class TestCancelLogWorker:
    """Tests for _cancel_log_worker."""

    def test_noop_when_no_worker(self) -> None:
        """No error when _log_worker is None."""
        screen = _make_log_viewer()
        screen._log_worker = None
        screen._cancel_log_worker()
        assert screen._log_worker is None

    def test_cancels_running_worker(self) -> None:
        """Cancels running worker and clears reference."""
        screen = _make_log_viewer()
        worker = MagicMock()
        worker.is_running = True
        screen._log_worker = worker
        screen._cancel_log_worker()
        worker.cancel.assert_called_once()
        assert screen._log_worker is None

    def test_skips_stopped_worker(self) -> None:
        """Does not cancel a stopped worker."""
        screen = _make_log_viewer()
        worker = MagicMock()
        worker.is_running = False
        screen._log_worker = worker
        screen._cancel_log_worker()
        worker.cancel.assert_not_called()


# ============================================================================
# Action Method Tests
# ============================================================================


@pytest.mark.unit
class TestLogViewerActions:
    """Tests for LogViewerScreen keyboard action methods."""

    def test_action_back(self) -> None:
        """action_back cancels worker then navigates back."""
        screen = _make_log_viewer()
        screen._cancel_log_worker = MagicMock()
        screen.action_back()
        screen._cancel_log_worker.assert_called_once()
        screen.go_back.assert_called_once()

    def test_action_select_container_opens_popup(self) -> None:
        """action_select_container pushes SelectorPopup."""
        screen = _make_log_viewer()
        mock_app = MagicMock()
        with patch.object(type(screen), "app", new_callable=PropertyMock, return_value=mock_app):
            screen.action_select_container()
        mock_app.push_screen.assert_called_once()

    def test_action_select_container_warns_when_no_containers(self) -> None:
        """action_select_container warns when pod has no containers."""
        screen = _make_log_viewer()
        screen._resource = PodSummary(
            name="empty",
            namespace="default",
            phase="Pending",
            ready_count=0,
            total_count=0,
            restarts=0,
            containers=[],
        )
        mock_app = MagicMock()
        with patch.object(type(screen), "app", new_callable=PropertyMock, return_value=mock_app):
            screen.action_select_container()
        screen.notify_user.assert_called_once()
        mock_app.push_screen.assert_not_called()

    def test_action_toggle_follow_enables(self) -> None:
        """Toggling from not-following to following starts stream."""
        screen = _make_log_viewer()
        screen._following = False
        screen._start_log_stream = MagicMock()
        screen._cancel_log_worker = MagicMock()
        screen.action_toggle_follow()
        assert screen._following is True
        screen._start_log_stream.assert_called_once()

    def test_action_toggle_follow_disables(self) -> None:
        """Toggling from following to paused cancels stream."""
        screen = _make_log_viewer()
        screen._following = True
        screen._start_log_stream = MagicMock()
        screen._cancel_log_worker = MagicMock()
        screen.action_toggle_follow()
        assert screen._following is False
        screen._cancel_log_worker.assert_called_once()

    def test_action_toggle_timestamps(self) -> None:
        """Toggling timestamps flips flag and restarts stream."""
        screen = _make_log_viewer()
        screen._show_timestamps = False
        screen._start_log_stream = MagicMock()
        screen.action_toggle_timestamps()
        assert screen._show_timestamps is True
        screen.notify_user.assert_called_once()
        screen._start_log_stream.assert_called_once()

    def test_action_clear_logs(self) -> None:
        """action_clear_logs clears the log widget."""
        screen = _make_log_viewer()
        mock_log = MagicMock()
        screen.query_one = MagicMock(return_value=mock_log)
        screen.action_clear_logs()
        mock_log.clear.assert_called_once()

    def test_action_scroll_top(self) -> None:
        """action_scroll_top calls scroll_home."""
        screen = _make_log_viewer()
        mock_log = MagicMock()
        screen.query_one = MagicMock(return_value=mock_log)
        screen.action_scroll_top()
        mock_log.scroll_home.assert_called_once()

    def test_action_scroll_bottom(self) -> None:
        """action_scroll_bottom calls scroll_end."""
        screen = _make_log_viewer()
        mock_log = MagicMock()
        screen.query_one = MagicMock(return_value=mock_log)
        screen.action_scroll_bottom()
        mock_log.scroll_end.assert_called_once()


# ============================================================================
# Handle Container Selected Tests
# ============================================================================


@pytest.mark.unit
class TestHandleContainerSelected:
    """Tests for _handle_container_selected callback."""

    def test_none_result_is_noop(self) -> None:
        """None result does not change container."""
        screen = _make_log_viewer()
        screen._start_log_stream = MagicMock()
        screen._handle_container_selected(None)
        screen._start_log_stream.assert_not_called()

    def test_same_container_is_noop(self) -> None:
        """Selecting the same container does nothing."""
        screen = _make_log_viewer()
        screen._container = "nginx"
        screen._start_log_stream = MagicMock()
        screen._handle_container_selected("nginx")
        screen._start_log_stream.assert_not_called()

    def test_different_container_updates_and_restarts(self) -> None:
        """Selecting a different container updates and restarts stream."""
        screen = _make_log_viewer()
        screen._container = "nginx"
        mock_label = MagicMock()
        mock_log = MagicMock()

        def _query(selector: str, *a: Any, **kw: Any) -> MagicMock:
            if "container-label" in str(selector):
                return mock_label
            return mock_log

        screen.query_one = MagicMock(side_effect=_query)
        screen._start_log_stream = MagicMock()
        screen._handle_container_selected("sidecar")
        assert screen._container == "sidecar"
        mock_label.update.assert_called_once()
        mock_log.clear.assert_called_once()
        screen._start_log_stream.assert_called_once()


# ============================================================================
# on_mount Tests
# ============================================================================


@pytest.mark.unit
class TestOnMount:
    """Tests for the on_mount lifecycle method."""

    def test_on_mount_sets_first_container_when_none(self) -> None:
        """on_mount assigns the first container name when _container is None."""
        screen = _make_log_viewer()
        screen._container = None
        mock_label = MagicMock()
        screen.query_one = MagicMock(return_value=mock_label)
        screen._start_log_stream = MagicMock()

        screen.on_mount()

        assert screen._container == "nginx"
        mock_label.update.assert_called_once()
        screen._start_log_stream.assert_called_once()

    def test_on_mount_skips_container_update_when_already_set(self) -> None:
        """on_mount does not overwrite an already-assigned container."""
        screen = _make_log_viewer()
        screen._container = "sidecar"
        mock_label = MagicMock()
        screen.query_one = MagicMock(return_value=mock_label)
        screen._start_log_stream = MagicMock()

        screen.on_mount()

        assert screen._container == "sidecar"
        mock_label.update.assert_not_called()
        screen._start_log_stream.assert_called_once()

    def test_on_mount_skips_container_update_when_no_containers(self) -> None:
        """on_mount does not set container when pod has no containers."""
        screen = _make_log_viewer()
        screen._container = None
        screen._resource = PodSummary(
            name="empty-pod",
            namespace="default",
            phase="Pending",
            ready_count=0,
            total_count=0,
            restarts=0,
            containers=[],
        )
        mock_label = MagicMock()
        screen.query_one = MagicMock(return_value=mock_label)
        screen._start_log_stream = MagicMock()

        screen.on_mount()

        assert screen._container is None
        mock_label.update.assert_not_called()
        screen._start_log_stream.assert_called_once()


# ============================================================================
# _stream_follow_logs Tests
# ============================================================================


@pytest.mark.unit
class TestStreamFollowLogs:
    """Tests for the _stream_follow_logs background worker (via __wrapped__)."""

    def test_stream_follow_logs_iterator(self) -> None:
        """Each line from the iterator is written to the log widget."""
        screen = _make_log_viewer()
        mock_log = MagicMock()
        screen.query_one = MagicMock(return_value=mock_log)
        mock_mgr = MagicMock()
        mock_mgr.stream_logs.return_value = ["line1\n", "line2\n"]
        screen._LogViewerScreen__streaming_mgr = mock_mgr
        mock_app = MagicMock()
        mock_app.call_from_thread = lambda fn, *a, **kw: fn(*a, **kw)

        with patch.object(type(screen), "app", new_callable=PropertyMock, return_value=mock_app):
            LogViewerScreen._stream_follow_logs.__wrapped__(screen)

        assert mock_log.write.call_count == 2

    def test_stream_follow_logs_string_result(self) -> None:
        """A string result is split by lines and each line written individually."""
        screen = _make_log_viewer()
        mock_log = MagicMock()
        screen.query_one = MagicMock(return_value=mock_log)
        mock_mgr = MagicMock()
        mock_mgr.stream_logs.return_value = "line1\nline2"
        screen._LogViewerScreen__streaming_mgr = mock_mgr
        mock_app = MagicMock()
        mock_app.call_from_thread = lambda fn, *a, **kw: fn(*a, **kw)

        with patch.object(type(screen), "app", new_callable=PropertyMock, return_value=mock_app):
            LogViewerScreen._stream_follow_logs.__wrapped__(screen)

        assert mock_log.write.call_count == 2

    def test_stream_follow_logs_error(self) -> None:
        """An exception from stream_logs writes an error message to the widget."""
        screen = _make_log_viewer()
        mock_log = MagicMock()
        screen.query_one = MagicMock(return_value=mock_log)
        mock_mgr = MagicMock()
        mock_mgr.stream_logs.side_effect = RuntimeError("connection lost")
        screen._LogViewerScreen__streaming_mgr = mock_mgr
        mock_app = MagicMock()
        mock_app.call_from_thread = lambda fn, *a, **kw: fn(*a, **kw)

        with patch.object(type(screen), "app", new_callable=PropertyMock, return_value=mock_app):
            LogViewerScreen._stream_follow_logs.__wrapped__(screen)

        mock_log.write.assert_called_once()
        assert "Error" in mock_log.write.call_args[0][0]

    def test_stream_follow_logs_strips_trailing_newline(self) -> None:
        """Trailing newlines are stripped from each line before writing."""
        screen = _make_log_viewer()
        mock_log = MagicMock()
        screen.query_one = MagicMock(return_value=mock_log)
        mock_mgr = MagicMock()
        mock_mgr.stream_logs.return_value = ["hello\n"]
        screen._LogViewerScreen__streaming_mgr = mock_mgr
        mock_app = MagicMock()
        mock_app.call_from_thread = lambda fn, *a, **kw: fn(*a, **kw)

        with patch.object(type(screen), "app", new_callable=PropertyMock, return_value=mock_app):
            LogViewerScreen._stream_follow_logs.__wrapped__(screen)

        mock_log.write.assert_called_once_with("hello")

    def test_stream_follow_logs_calls_stream_logs_with_correct_args(self) -> None:
        """stream_logs is called with the correct pod, namespace, and options."""
        screen = _make_log_viewer()
        mock_log = MagicMock()
        screen.query_one = MagicMock(return_value=mock_log)
        mock_mgr = MagicMock()
        mock_mgr.stream_logs.return_value = []
        screen._LogViewerScreen__streaming_mgr = mock_mgr
        mock_app = MagicMock()
        mock_app.call_from_thread = lambda fn, *a, **kw: fn(*a, **kw)

        with patch.object(type(screen), "app", new_callable=PropertyMock, return_value=mock_app):
            LogViewerScreen._stream_follow_logs.__wrapped__(screen)

        mock_mgr.stream_logs.assert_called_once_with(
            "nginx-abc123",
            "default",
            container="nginx",
            follow=True,
            tail_lines=TAIL_LINES_FOLLOW,
            timestamps=False,
        )


# ============================================================================
# _load_static_logs Tests
# ============================================================================


@pytest.mark.unit
class TestLoadStaticLogs:
    """Tests for the _load_static_logs background worker (via __wrapped__)."""

    def test_load_static_logs_string_result(self) -> None:
        """A string result is split into lines and each line written."""
        screen = _make_log_viewer()
        mock_log = MagicMock()
        screen.query_one = MagicMock(return_value=mock_log)
        mock_mgr = MagicMock()
        mock_mgr.stream_logs.return_value = "alpha\nbeta\ngamma"
        screen._LogViewerScreen__streaming_mgr = mock_mgr
        mock_app = MagicMock()
        mock_app.call_from_thread = lambda fn, *a, **kw: fn(*a, **kw)

        with patch.object(type(screen), "app", new_callable=PropertyMock, return_value=mock_app):
            LogViewerScreen._load_static_logs.__wrapped__(screen)

        assert mock_log.write.call_count == 3

    def test_load_static_logs_iterator_result(self) -> None:
        """An iterable result writes each line (stripped) to the log widget."""
        screen = _make_log_viewer()
        mock_log = MagicMock()
        screen.query_one = MagicMock(return_value=mock_log)
        mock_mgr = MagicMock()
        mock_mgr.stream_logs.return_value = ["alpha\n", "beta\n", "gamma\n"]
        screen._LogViewerScreen__streaming_mgr = mock_mgr
        mock_app = MagicMock()
        mock_app.call_from_thread = lambda fn, *a, **kw: fn(*a, **kw)

        with patch.object(type(screen), "app", new_callable=PropertyMock, return_value=mock_app):
            LogViewerScreen._load_static_logs.__wrapped__(screen)

        assert mock_log.write.call_count == 3

    def test_load_static_logs_error(self) -> None:
        """An exception from stream_logs writes an error message to the widget."""
        screen = _make_log_viewer()
        mock_log = MagicMock()
        screen.query_one = MagicMock(return_value=mock_log)
        mock_mgr = MagicMock()
        mock_mgr.stream_logs.side_effect = ValueError("timeout")
        screen._LogViewerScreen__streaming_mgr = mock_mgr
        mock_app = MagicMock()
        mock_app.call_from_thread = lambda fn, *a, **kw: fn(*a, **kw)

        with patch.object(type(screen), "app", new_callable=PropertyMock, return_value=mock_app):
            LogViewerScreen._load_static_logs.__wrapped__(screen)

        mock_log.write.assert_called_once()
        assert "Error" in mock_log.write.call_args[0][0]

    def test_load_static_logs_strips_trailing_newline(self) -> None:
        """Trailing newlines are stripped from each iterator line before writing."""
        screen = _make_log_viewer()
        mock_log = MagicMock()
        screen.query_one = MagicMock(return_value=mock_log)
        mock_mgr = MagicMock()
        mock_mgr.stream_logs.return_value = ["only-line\n"]
        screen._LogViewerScreen__streaming_mgr = mock_mgr
        mock_app = MagicMock()
        mock_app.call_from_thread = lambda fn, *a, **kw: fn(*a, **kw)

        with patch.object(type(screen), "app", new_callable=PropertyMock, return_value=mock_app):
            LogViewerScreen._load_static_logs.__wrapped__(screen)

        mock_log.write.assert_called_once_with("only-line")

    def test_load_static_logs_calls_stream_logs_with_correct_args(self) -> None:
        """stream_logs is called with follow=False and TAIL_LINES_STATIC."""
        screen = _make_log_viewer()
        mock_log = MagicMock()
        screen.query_one = MagicMock(return_value=mock_log)
        mock_mgr = MagicMock()
        mock_mgr.stream_logs.return_value = []
        screen._LogViewerScreen__streaming_mgr = mock_mgr
        mock_app = MagicMock()
        mock_app.call_from_thread = lambda fn, *a, **kw: fn(*a, **kw)

        with patch.object(type(screen), "app", new_callable=PropertyMock, return_value=mock_app):
            LogViewerScreen._load_static_logs.__wrapped__(screen)

        mock_mgr.stream_logs.assert_called_once_with(
            "nginx-abc123",
            "default",
            container="nginx",
            follow=False,
            tail_lines=TAIL_LINES_STATIC,
            timestamps=False,
        )
