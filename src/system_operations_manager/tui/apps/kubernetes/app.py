"""Main Textual application for Kubernetes resource browsing.

This module provides the KubernetesApp, the entry point for
interactive Kubernetes resource browsing in the TUI.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from system_operations_manager.tui.apps.kubernetes.screens import ResourceListScreen

if TYPE_CHECKING:
    from system_operations_manager.integrations.kubernetes.client import KubernetesClient


class ResourceType(Enum):
    """Kubernetes resource types available in the TUI browser."""

    # Workloads
    PODS = "Pods"
    DEPLOYMENTS = "Deployments"
    STATEFULSETS = "StatefulSets"
    DAEMONSETS = "DaemonSets"
    REPLICASETS = "ReplicaSets"

    # Networking
    SERVICES = "Services"
    INGRESSES = "Ingresses"
    NETWORK_POLICIES = "NetworkPolicies"

    # Configuration
    CONFIGMAPS = "ConfigMaps"
    SECRETS = "Secrets"

    # Cluster
    NAMESPACES = "Namespaces"
    NODES = "Nodes"
    EVENTS = "Events"


# Resource types that are cluster-scoped (not namespaced)
CLUSTER_SCOPED_TYPES = frozenset({
    ResourceType.NAMESPACES,
    ResourceType.NODES,
})

# Ordered list for cycling through types
RESOURCE_TYPE_ORDER = list(ResourceType)


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

    def action_help(self) -> None:
        """Show keyboard shortcut help."""
        self.notify(
            "j/k: navigate | Enter: select | n/N: namespace | "
            "c/C: cluster | f/F: resource type | r: refresh | q: quit"
        )

    @on(ResourceListScreen.ResourceSelected)
    def handle_resource_selected(
        self, event: ResourceListScreen.ResourceSelected
    ) -> None:
        """Handle resource selection from list.

        Currently shows a notification. The detail screen is
        implemented in a separate task (system-operations-manager-uy8).
        """
        self.notify(
            f"Selected: {event.resource_type.value} / {event.resource.name}"
        )
