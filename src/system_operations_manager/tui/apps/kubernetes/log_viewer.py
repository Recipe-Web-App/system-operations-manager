"""Log viewer screen for Kubernetes pod log streaming.

Provides a TUI screen with real-time log streaming via RichLog,
container selection for multi-container pods, and follow/pause controls.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from textual import work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Label, RichLog

from system_operations_manager.tui.apps.kubernetes.widgets import SelectorPopup
from system_operations_manager.tui.base import BaseScreen

if TYPE_CHECKING:
    from textual.worker import Worker

    from system_operations_manager.integrations.kubernetes.client import KubernetesClient
    from system_operations_manager.integrations.kubernetes.models.workloads import PodSummary
    from system_operations_manager.services.kubernetes.streaming_manager import (
        StreamingManager,
    )

logger = structlog.get_logger()

TAIL_LINES_FOLLOW = 200
TAIL_LINES_STATIC = 500


class LogViewerScreen(BaseScreen[None]):
    """Screen for viewing pod logs with streaming support.

    Displays logs from a selected container using Textual's RichLog
    widget. Supports follow mode for real-time streaming, container
    switching, and timestamp toggling.

    Args:
        resource: Pod to view logs for.
        client: Kubernetes API client.
        initial_container: Container name to start with (defaults to first).
    """

    BINDINGS = [
        ("escape", "back", "Back"),
        ("c", "select_container", "Container"),
        ("f", "toggle_follow", "Follow"),
        ("space", "toggle_follow", "Pause/Resume"),
        ("t", "toggle_timestamps", "Timestamps"),
        ("ctrl+l", "clear_logs", "Clear"),
        ("g", "scroll_top", "Top"),
        ("G", "scroll_bottom", "Bottom"),
    ]

    def __init__(
        self,
        resource: PodSummary,
        client: KubernetesClient,
        initial_container: str | None = None,
    ) -> None:
        """Initialize the log viewer screen.

        Args:
            resource: The pod resource to stream logs from.
            client: Kubernetes API client for streaming.
            initial_container: Container name to view (defaults to first).
        """
        super().__init__()
        self._resource = resource
        self._client = client
        self._container = initial_container
        self._following = True
        self._show_timestamps = False
        self.__streaming_mgr: StreamingManager | None = None
        self._log_worker: Worker[None] | None = None

    @property
    def _streaming_mgr(self) -> StreamingManager:
        """Lazy-loaded streaming manager instance."""
        if self.__streaming_mgr is None:
            from system_operations_manager.services.kubernetes.streaming_manager import (
                StreamingManager,
            )

            self.__streaming_mgr = StreamingManager(self._client)
        return self.__streaming_mgr

    # =========================================================================
    # Layout
    # =========================================================================

    def compose(self) -> ComposeResult:
        """Compose the log viewer layout."""
        yield Container(
            Label(self._build_header(), id="log-header"),
            Horizontal(
                Label(self._build_container_label(), id="log-container-label"),
                Label("[bold green]FOLLOWING[/bold green]", id="log-status"),
                id="log-toolbar",
            ),
            RichLog(
                highlight=True,
                markup=True,
                auto_scroll=True,
                id="log-output",
            ),
            id="log-container",
        )

    def on_mount(self) -> None:
        """Set default container and start streaming."""
        if not self._container and self._resource.containers:
            self._container = self._resource.containers[0].name
            self.query_one("#log-container-label", Label).update(self._build_container_label())
        self._start_log_stream()

    # =========================================================================
    # Text Builders
    # =========================================================================

    def _build_header(self) -> str:
        """Build the header text with pod name and namespace.

        Returns:
            Rich-markup formatted header string.
        """
        name = self._resource.name
        ns = self._resource.namespace
        parts = [f"[bold]Pod Logs[/bold] / [bold cyan]{name}[/bold cyan]"]
        if ns:
            parts.append(f"  [dim]ns:[/dim] {ns}")
        return "".join(parts)

    def _build_container_label(self) -> str:
        """Build the container label text.

        Returns:
            Formatted container label string.
        """
        display = self._container or "N/A"
        return f"Container: [bold]{display}[/bold]"

    # =========================================================================
    # Log Streaming
    # =========================================================================

    def _start_log_stream(self) -> None:
        """Cancel existing worker and start a new log stream."""
        self._cancel_log_worker()
        if self._following:
            self._log_worker = self._stream_follow_logs()
        else:
            self._log_worker = self._load_static_logs()

    @work(thread=True)
    def _stream_follow_logs(self) -> None:
        """Stream logs in follow mode using a background thread.

        Uses ``StreamingManager.stream_logs(follow=True)`` which returns
        a blocking iterator. Lines are posted to the UI thread via
        ``call_from_thread``.
        """
        log_widget = self.query_one("#log-output", RichLog)
        try:
            iterator = self._streaming_mgr.stream_logs(
                self._resource.name,
                self._resource.namespace,
                container=self._container,
                follow=True,
                tail_lines=TAIL_LINES_FOLLOW,
                timestamps=self._show_timestamps,
            )
            if isinstance(iterator, str):
                # Shouldn't happen with follow=True but handle gracefully
                for line in iterator.splitlines():
                    self.app.call_from_thread(log_widget.write, line)
                return

            for line in iterator:
                self.app.call_from_thread(log_widget.write, line.rstrip("\n"))
        except Exception as e:
            logger.warning("log_stream_error", pod=self._resource.name, error=str(e))
            self.app.call_from_thread(
                log_widget.write,
                f"[red]Error streaming logs: {e}[/red]",
            )

    @work(thread=True)
    def _load_static_logs(self) -> None:
        """Load logs in non-follow mode (snapshot).

        Fetches all available log lines and writes them to the RichLog.
        """
        log_widget = self.query_one("#log-output", RichLog)
        try:
            result = self._streaming_mgr.stream_logs(
                self._resource.name,
                self._resource.namespace,
                container=self._container,
                follow=False,
                tail_lines=TAIL_LINES_STATIC,
                timestamps=self._show_timestamps,
            )
            if isinstance(result, str):
                for line in result.splitlines():
                    self.app.call_from_thread(log_widget.write, line)
            else:
                for line in result:
                    self.app.call_from_thread(log_widget.write, line.rstrip("\n"))
        except Exception as e:
            logger.warning("log_load_error", pod=self._resource.name, error=str(e))
            self.app.call_from_thread(
                log_widget.write,
                f"[red]Error loading logs: {e}[/red]",
            )

    def _cancel_log_worker(self) -> None:
        """Cancel the active log streaming worker if running."""
        if self._log_worker is not None and self._log_worker.is_running:
            self._log_worker.cancel()
            self._log_worker = None

    # =========================================================================
    # Keyboard Actions
    # =========================================================================

    def action_back(self) -> None:
        """Cancel streaming and navigate back."""
        self._cancel_log_worker()
        self.go_back()

    def action_select_container(self) -> None:
        """Open container selector popup."""
        containers = [c.name for c in self._resource.containers if c.name]
        if not containers:
            self.notify_user("No containers found", severity="warning")
            return
        self.app.push_screen(
            SelectorPopup("Select Container", containers, self._container),
            callback=self._handle_container_selected,
        )

    def _handle_container_selected(self, result: str | None) -> None:
        """Handle container selection from popup.

        Args:
            result: Selected container name or None if dismissed.
        """
        if result and result != self._container:
            self._container = result
            self.query_one("#log-container-label", Label).update(self._build_container_label())
            log_widget = self.query_one("#log-output", RichLog)
            log_widget.clear()
            self._start_log_stream()

    def action_toggle_follow(self) -> None:
        """Toggle between follow and paused mode."""
        self._following = not self._following
        status = self.query_one("#log-status", Label)
        if self._following:
            status.update("[bold green]FOLLOWING[/bold green]")
            self._start_log_stream()
        else:
            status.update("[bold yellow]PAUSED[/bold yellow]")
            self._cancel_log_worker()

    def action_toggle_timestamps(self) -> None:
        """Toggle timestamp display and restart stream."""
        self._show_timestamps = not self._show_timestamps
        state = "on" if self._show_timestamps else "off"
        self.notify_user(f"Timestamps {state}")
        log_widget = self.query_one("#log-output", RichLog)
        log_widget.clear()
        self._start_log_stream()

    def action_clear_logs(self) -> None:
        """Clear the log output."""
        log_widget = self.query_one("#log-output", RichLog)
        log_widget.clear()

    def action_scroll_top(self) -> None:
        """Scroll to the top of the log output."""
        log_widget = self.query_one("#log-output", RichLog)
        log_widget.scroll_home()

    def action_scroll_bottom(self) -> None:
        """Scroll to the bottom of the log output."""
        log_widget = self.query_one("#log-output", RichLog)
        log_widget.scroll_end()
