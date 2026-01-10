"""Kubernetes service module.

Provides centralized Kubernetes integration for the system operations manager.
"""

from system_operations_manager.services.kubernetes.client import KubernetesService

__all__ = ["KubernetesService"]
