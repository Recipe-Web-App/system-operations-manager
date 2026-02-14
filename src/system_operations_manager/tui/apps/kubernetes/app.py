"""Main Textual application for Kubernetes resource browsing.

This module provides the KubernetesApp, the entry point for
interactive Kubernetes resource browsing in the TUI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from system_operations_manager.tui.apps.kubernetes.screens import (
    DashboardScreen,
    ResourceListScreen,
)
from system_operations_manager.tui.apps.kubernetes.types import (
    CLUSTER_SCOPED_TYPES,
    RESOURCE_TYPE_ORDER,
    ResourceType,
)

if TYPE_CHECKING:
    from system_operations_manager.integrations.kubernetes.client import KubernetesClient

# Re-export for backward compatibility
__all__ = [
    "CLUSTER_SCOPED_TYPES",
    "RESOURCE_TYPE_ORDER",
    "DashboardScreen",
    "KubernetesApp",
    "ResourceType",
]


class KubernetesApp(App[None]):
    """TUI application for browsing Kubernetes cluster resources.

    Presents a navigable table of resources with namespace/cluster
    switching and resource type filtering.

    Args:
        client: Kubernetes API client instance.
    """

    TITLE = "Kubernetes Resource Browser"
    CSS_PATH = "styles.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("escape", "back", "Back", show=True),
        Binding("d", "dashboard", "Dashboard", show=True),
        Binding("question_mark", "help", "Help", show=True),
    ]

    def __init__(self, client: KubernetesClient) -> None:
        """Initialize the Kubernetes resource browser app.

        Args:
            client: Kubernetes API client for cluster communication.
        """
        super().__init__()
        self._client = client

    def compose(self) -> ComposeResult:
        """Compose the app layout."""
        yield Header()
        yield Footer()

    def on_mount(self) -> None:
        """Push the initial resource list screen on mount."""
        self.push_screen(ResourceListScreen(client=self._client))

    async def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

    async def action_back(self) -> None:
        """Navigate back to previous screen."""
        if len(self.screen_stack) > 1:
            self.pop_screen()

    def action_dashboard(self) -> None:
        """Open the cluster status dashboard."""
        self.push_screen(DashboardScreen(client=self._client))

    def action_help(self) -> None:
        """Show keyboard shortcut help."""
        self.notify(
            "j/k: navigate | Enter: select | n/N: namespace | "
            "c/C: cluster | f/F: resource type | r: refresh | d: dashboard | q: quit"
        )

    @on(ResourceListScreen.ResourceSelected)
    def handle_resource_selected(self, event: ResourceListScreen.ResourceSelected) -> None:
        """Handle resource selection from list.

        Currently shows a notification. The detail screen is
        implemented in a separate task (system-operations-manager-uy8).
        """
        self.notify(f"Selected: {event.resource_type.value} / {event.resource.name}")
