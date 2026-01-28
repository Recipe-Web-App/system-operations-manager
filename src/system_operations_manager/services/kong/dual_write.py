"""Dual-write service for Kong Gateway and Konnect operations.

This service orchestrates write operations to both Kong Gateway (data plane)
and Konnect (control plane), providing consistent dual-write behavior with
best-effort Konnect synchronization.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class DualWriteResult[T]:
    """Result from a dual-write operation.

    Contains the results from both Gateway and Konnect writes,
    along with any errors that occurred during Konnect synchronization.

    Attributes:
        gateway_result: The entity returned from Gateway (always present on success).
        konnect_result: The entity returned from Konnect (None if skipped or failed).
        konnect_error: Exception if Konnect write failed (None on success).
        konnect_skipped: True if Konnect write was intentionally skipped.
    """

    gateway_result: T
    konnect_result: T | None = None
    konnect_error: Exception | None = None
    konnect_skipped: bool = False
    konnect_not_configured: bool = False

    @property
    def is_fully_synced(self) -> bool:
        """True if both writes succeeded."""
        return (
            self.konnect_result is not None
            and self.konnect_error is None
            and not self.konnect_skipped
        )

    @property
    def partial_success(self) -> bool:
        """True if Gateway succeeded but Konnect failed."""
        return self.konnect_error is not None


@dataclass
class DualDeleteResult:
    """Result from a dual-delete operation.

    Similar to DualWriteResult but for delete operations which don't return entities.
    """

    gateway_deleted: bool = True
    konnect_deleted: bool = False
    konnect_error: Exception | None = None
    konnect_skipped: bool = False
    konnect_not_configured: bool = False

    @property
    def is_fully_synced(self) -> bool:
        """True if both deletes succeeded."""
        return self.konnect_deleted and self.konnect_error is None and not self.konnect_skipped

    @property
    def partial_success(self) -> bool:
        """True if Gateway succeeded but Konnect failed."""
        return self.konnect_error is not None


class DualWriteService[T]:
    """Orchestrates write operations to Gateway and optionally Konnect.

    This service implements a Gateway-first, Konnect-best-effort write strategy:
    1. Always write to Gateway first (must succeed)
    2. Attempt Konnect write if configured and not skipped
    3. Log warning on Konnect failure but don't rollback Gateway

    Args:
        gateway_manager: Manager for Gateway operations (required).
        konnect_manager: Manager for Konnect operations (None if not configured).
        entity_name: Name of the entity type for logging (e.g., "service").
    """

    def __init__(
        self,
        gateway_manager: Any,
        konnect_manager: Any | None,
        entity_name: str,
    ) -> None:
        self._gateway = gateway_manager
        self._konnect = konnect_manager
        self._entity_name = entity_name
        self._log = logger.bind(entity_type=entity_name)

    @property
    def konnect_configured(self) -> bool:
        """Check if Konnect is configured."""
        return self._konnect is not None

    def create(
        self,
        entity: T,
        *,
        data_plane_only: bool = False,
        **kwargs: Any,
    ) -> DualWriteResult[T]:
        """Create entity on Gateway and optionally Konnect.

        Args:
            entity: The entity to create.
            data_plane_only: If True, skip Konnect synchronization.
            **kwargs: Additional arguments passed to manager create methods.

        Returns:
            DualWriteResult containing results from both systems.

        Raises:
            KongAPIError: If Gateway write fails.
        """
        self._log.info("creating_entity", data_plane_only=data_plane_only)

        # 1. Always write to Gateway first
        gateway_result = self._gateway.create(entity, **kwargs)
        self._log.info("gateway_create_success", id=getattr(gateway_result, "id", None))

        # 2. Skip Konnect if flag set
        if data_plane_only:
            self._log.debug("konnect_skipped", reason="data_plane_only flag")
            return DualWriteResult(
                gateway_result=gateway_result,
                konnect_skipped=True,
            )

        # 3. Skip Konnect if not configured
        if self._konnect is None:
            self._log.debug("konnect_skipped", reason="not configured")
            return DualWriteResult(
                gateway_result=gateway_result,
                konnect_not_configured=True,
            )

        # 4. Attempt Konnect write (best-effort)
        try:
            konnect_result = self._konnect.create(entity, **kwargs)
            self._log.info("konnect_create_success", id=getattr(konnect_result, "id", None))
            return DualWriteResult(
                gateway_result=gateway_result,
                konnect_result=konnect_result,
            )
        except Exception as e:
            self._log.warning(
                "konnect_create_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return DualWriteResult(
                gateway_result=gateway_result,
                konnect_error=e,
            )

    def update(
        self,
        id_or_name: str,
        entity: T,
        *,
        data_plane_only: bool = False,
        **kwargs: Any,
    ) -> DualWriteResult[T]:
        """Update entity on Gateway and optionally Konnect.

        Args:
            id_or_name: Entity identifier.
            entity: The updated entity data.
            data_plane_only: If True, skip Konnect synchronization.
            **kwargs: Additional arguments passed to manager update methods.

        Returns:
            DualWriteResult containing results from both systems.

        Raises:
            KongAPIError: If Gateway write fails.
        """
        self._log.info("updating_entity", id_or_name=id_or_name, data_plane_only=data_plane_only)

        # 1. Always update Gateway first
        gateway_result = self._gateway.update(id_or_name, entity, **kwargs)
        self._log.info("gateway_update_success", id=getattr(gateway_result, "id", None))

        # 2. Skip Konnect if flag set
        if data_plane_only:
            self._log.debug("konnect_skipped", reason="data_plane_only flag")
            return DualWriteResult(
                gateway_result=gateway_result,
                konnect_skipped=True,
            )

        # 3. Skip Konnect if not configured
        if self._konnect is None:
            self._log.debug("konnect_skipped", reason="not configured")
            return DualWriteResult(
                gateway_result=gateway_result,
                konnect_not_configured=True,
            )

        # 4. Attempt Konnect update (best-effort)
        try:
            konnect_result = self._konnect.update(id_or_name, entity, **kwargs)
            self._log.info("konnect_update_success", id=getattr(konnect_result, "id", None))
            return DualWriteResult(
                gateway_result=gateway_result,
                konnect_result=konnect_result,
            )
        except Exception as e:
            self._log.warning(
                "konnect_update_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return DualWriteResult(
                gateway_result=gateway_result,
                konnect_error=e,
            )

    def delete(
        self,
        id_or_name: str,
        *,
        data_plane_only: bool = False,
    ) -> DualDeleteResult:
        """Delete entity from Gateway and optionally Konnect.

        Args:
            id_or_name: Entity identifier.
            data_plane_only: If True, skip Konnect synchronization.

        Returns:
            DualDeleteResult indicating success/failure for both systems.

        Raises:
            KongAPIError: If Gateway delete fails.
        """
        self._log.info("deleting_entity", id_or_name=id_or_name, data_plane_only=data_plane_only)

        # 1. Always delete from Gateway first
        self._gateway.delete(id_or_name)
        self._log.info("gateway_delete_success")

        # 2. Skip Konnect if flag set
        if data_plane_only:
            self._log.debug("konnect_skipped", reason="data_plane_only flag")
            return DualDeleteResult(
                gateway_deleted=True,
                konnect_skipped=True,
            )

        # 3. Skip Konnect if not configured
        if self._konnect is None:
            self._log.debug("konnect_skipped", reason="not configured")
            return DualDeleteResult(
                gateway_deleted=True,
                konnect_not_configured=True,
            )

        # 4. Attempt Konnect delete (best-effort)
        try:
            self._konnect.delete(id_or_name)
            self._log.info("konnect_delete_success")
            return DualDeleteResult(
                gateway_deleted=True,
                konnect_deleted=True,
            )
        except Exception as e:
            self._log.warning(
                "konnect_delete_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return DualDeleteResult(
                gateway_deleted=True,
                konnect_error=e,
            )
