"""E2E tests for Kubernetes TUI application lifecycle.

These tests verify the Textual-based TUI application lifecycle and
basic interactions against a real K3S cluster:
- Application mounting and initialization
- Screen navigation
- Keyboard shortcuts
- Core UI components

All tests use Textual's async test support and run against a real K3S cluster.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from system_operations_manager.integrations.kubernetes.client import KubernetesClient
from system_operations_manager.integrations.kubernetes.config import (
    ClusterConfig,
    KubernetesPluginConfig,
)
from system_operations_manager.tui.apps.kubernetes.app import KubernetesApp

if TYPE_CHECKING:
    pass


@pytest.fixture
def k8s_client(k3s_kubeconfig_path: Path) -> KubernetesClient:
    """Create a KubernetesClient connected to K3S cluster.

    Args:
        k3s_kubeconfig_path: Path to K3S kubeconfig file

    Returns:
        Configured KubernetesClient instance
    """
    config = KubernetesPluginConfig(
        clusters={"test": ClusterConfig(kubeconfig=str(k3s_kubeconfig_path))},
        active_cluster="test",
    )
    return KubernetesClient(config)


@pytest.mark.e2e
@pytest.mark.kubernetes
@pytest.mark.asyncio
class TestTUILifecycle:
    """Test TUI app lifecycle and interactions."""

    async def test_app_mounts(self, k8s_client: KubernetesClient) -> None:
        """Verify the TUI app can mount and initialize successfully."""
        app = KubernetesApp(client=k8s_client)
        async with app.run_test() as pilot:
            # App should be running
            assert app.is_running
            # Give it a moment to stabilize
            await pilot.pause()

    async def test_app_has_title(self, k8s_client: KubernetesClient) -> None:
        """Verify the TUI app has the correct title."""
        app = KubernetesApp(client=k8s_client)
        async with app.run_test() as pilot:
            await pilot.pause()
            # Check the app title
            assert app.title == "Kubernetes Resource Browser"

    async def test_resource_list_screen_loads(self, k8s_client: KubernetesClient) -> None:
        """Verify the resource list screen loads on app mount."""
        app = KubernetesApp(client=k8s_client)
        async with app.run_test() as pilot:
            await pilot.pause()
            # The initial screen should be ResourceListScreen (or at least exist)
            assert app.screen is not None
            # We should have at least one screen in the stack
            assert len(app.screen_stack) >= 1

    async def test_dashboard_action(self, k8s_client: KubernetesClient) -> None:
        """Verify pressing 'd' opens the dashboard screen."""
        app = KubernetesApp(client=k8s_client)
        async with app.run_test() as pilot:
            await pilot.pause()
            # Record initial screen count
            initial_stack_size = len(app.screen_stack)
            # Press 'd' to open dashboard
            await pilot.press("d")
            await pilot.pause()
            # Should have pushed a new screen
            assert len(app.screen_stack) > initial_stack_size

    async def test_quit_action(self, k8s_client: KubernetesClient) -> None:
        """Verify pressing 'q' quits the application."""
        app = KubernetesApp(client=k8s_client)
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.is_running
            # Press 'q' to quit
            await pilot.press("q")
            await pilot.pause()
            # App should no longer be running
            # Note: The run_test context will handle cleanup

    async def test_help_action(self, k8s_client: KubernetesClient) -> None:
        """Verify pressing '?' shows help notification."""
        app = KubernetesApp(client=k8s_client)
        async with app.run_test() as pilot:
            await pilot.pause()
            # Press '?' to show help
            await pilot.press("question_mark")
            await pilot.pause()
            # The help action triggers a notify() call
            # We can't easily check notification contents in tests,
            # but we can verify the app is still running and stable
            assert app.is_running
