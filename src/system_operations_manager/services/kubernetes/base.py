"""Base manager for Kubernetes service managers.

Provides shared infrastructure for all Kubernetes resource managers,
including client access, namespace resolution, and error translation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NoReturn

import structlog

if TYPE_CHECKING:
    from system_operations_manager.integrations.kubernetes.client import KubernetesClient

logger = structlog.get_logger()


class K8sBaseManager:
    """Base class for Kubernetes service managers.

    Provides shared concerns for all managers:
    - Client reference and API group access
    - Structured logging with entity binding
    - Namespace resolution with config fallback
    - Consistent API error translation

    Subclasses set ``_entity_name`` for structured log context.

    Example:
        >>> class WorkloadManager(K8sBaseManager):
        ...     _entity_name = "workload"
    """

    _entity_name: str = ""

    def __init__(self, client: KubernetesClient) -> None:
        """Initialize the manager.

        Args:
            client: Kubernetes API client instance.
        """
        self._client = client
        self._log = logger.bind(entity=self._entity_name)

    def _resolve_namespace(self, namespace: str | None) -> str:
        """Resolve namespace, falling back to the client default.

        Args:
            namespace: Explicit namespace or None for default.

        Returns:
            The resolved namespace string.
        """
        return namespace or self._client.default_namespace

    def _handle_api_error(
        self,
        e: Exception,
        resource_type: str | None = None,
        resource_name: str | None = None,
        namespace: str | None = None,
    ) -> NoReturn:
        """Translate a Kubernetes API exception and re-raise.

        Args:
            e: The original exception (typically ApiException).
            resource_type: Type of resource being operated on.
            resource_name: Name of the resource.
            namespace: Namespace of the resource.

        Raises:
            KubernetesError: Always raises an appropriate subclass.
        """
        raise self._client.translate_api_exception(
            e,
            resource_type=resource_type,
            resource_name=resource_name,
            namespace=namespace,
        )
