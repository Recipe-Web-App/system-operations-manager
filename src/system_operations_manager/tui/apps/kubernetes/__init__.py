"""Kubernetes Resource Browser TUI application.

This module provides an interactive terminal interface for browsing
and managing Kubernetes cluster resources.

Usage:
    from system_operations_manager.tui.apps.kubernetes import KubernetesApp

    app = KubernetesApp(client=client)
    app.run()
"""

from system_operations_manager.tui.apps.kubernetes.app import KubernetesApp

__all__ = ["KubernetesApp"]
