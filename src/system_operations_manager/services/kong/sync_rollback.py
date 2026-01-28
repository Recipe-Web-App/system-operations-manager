"""Sync rollback service for reverting Kong sync operations.

This module provides the ability to rollback sync operations between Kong Gateway
and Konnect control plane. It uses the audit log to determine what changes were
made and reverses them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from system_operations_manager.services.kong.sync_audit import (
    SyncAuditEntry,
    SyncAuditService,
)

if TYPE_CHECKING:
    pass


class RollbackAction(BaseModel):
    """A single rollback action to perform.

    Represents one operation that will be executed during rollback,
    derived from a corresponding sync audit entry.
    """

    entity_type: str = Field(description="Entity type: services, routes, etc.")
    entity_id: str | None = Field(default=None, description="Entity ID to operate on")
    entity_name: str = Field(description="Human-readable entity identifier")
    original_action: str = Field(description="Original sync action: 'create' or 'update'")
    rollback_action: str = Field(description="Rollback action: 'delete' or 'restore'")
    before_state: dict[str, Any] | None = Field(
        default=None, description="State to restore for 'restore' action"
    )
    after_state: dict[str, Any] | None = Field(
        default=None, description="State that was created (for finding entity to delete)"
    )
    target: str = Field(description="Target system: 'gateway' or 'konnect'")


class RollbackPreview(BaseModel):
    """Preview of a rollback operation.

    Contains all the actions that would be performed during rollback,
    along with any warnings about potential issues.
    """

    sync_id: str = Field(description="ID of the sync being rolled back")
    operation: str = Field(description="Original operation: 'push' or 'pull'")
    timestamp: str = Field(description="Timestamp of the original sync")
    actions: list[RollbackAction] = Field(default_factory=list, description="Actions to perform")
    warnings: list[str] = Field(default_factory=list, description="Warnings about the rollback")
    can_rollback: bool = Field(default=True, description="Whether rollback is possible")


class RollbackResult(BaseModel):
    """Result of a rollback operation.

    Tracks success/failure counts and any errors that occurred.
    """

    sync_id: str = Field(description="ID of the sync that was rolled back")
    success: bool = Field(description="Whether rollback completed without errors")
    rolled_back: int = Field(default=0, description="Number of entities rolled back")
    failed: int = Field(default=0, description="Number of failed rollback operations")
    skipped: int = Field(default=0, description="Number of skipped operations")
    errors: list[str] = Field(default_factory=list, description="Error messages")


class RollbackService:
    """Service for rolling back sync operations.

    Uses the audit log to determine what changes were made during a sync
    and reverses them by:
    - Deleting entities that were created
    - Restoring entities to their before_state for updates
    """

    def __init__(
        self,
        audit_service: SyncAuditService,
        gateway_managers: dict[str, Any],
        konnect_managers: dict[str, Any],
    ) -> None:
        """Initialize the rollback service.

        Args:
            audit_service: Service for accessing audit logs
            gateway_managers: Dict mapping entity type to Gateway manager
            konnect_managers: Dict mapping entity type to Konnect manager
        """
        self._audit_service = audit_service
        self._gateway_managers = gateway_managers
        self._konnect_managers = konnect_managers

    def preview_rollback(
        self,
        sync_id: str,
        entity_types: list[str] | None = None,
    ) -> RollbackPreview:
        """Preview what would be rolled back without making changes.

        Args:
            sync_id: The sync operation ID to preview rollback for
            entity_types: Optional list of entity types to filter

        Returns:
            RollbackPreview with actions and warnings
        """
        entries = self._audit_service.get_sync_details(sync_id)

        if not entries:
            return RollbackPreview(
                sync_id=sync_id,
                operation="unknown",
                timestamp="",
                actions=[],
                warnings=["Sync operation not found"],
                can_rollback=False,
            )

        first_entry = entries[0]

        # Check if this was a dry-run
        if first_entry.dry_run:
            return RollbackPreview(
                sync_id=sync_id,
                operation=first_entry.operation,
                timestamp=first_entry.timestamp,
                actions=[],
                warnings=["Cannot rollback a dry-run sync (no changes were made)"],
                can_rollback=False,
            )

        actions, warnings = self._build_rollback_actions(entries, entity_types)

        return RollbackPreview(
            sync_id=sync_id,
            operation=first_entry.operation,
            timestamp=first_entry.timestamp,
            actions=actions,
            warnings=warnings,
            can_rollback=len(actions) > 0,
        )

    def rollback(
        self,
        sync_id: str,
        entity_types: list[str] | None = None,
        force: bool = False,
    ) -> RollbackResult:
        """Execute rollback of a sync operation.

        Args:
            sync_id: The sync operation ID to rollback
            entity_types: Optional list of entity types to filter
            force: If True, continue on errors

        Returns:
            RollbackResult with success/failure counts
        """
        preview = self.preview_rollback(sync_id, entity_types)

        if not preview.can_rollback:
            return RollbackResult(
                sync_id=sync_id,
                success=False,
                errors=preview.warnings,
            )

        rolled_back = 0
        failed = 0
        skipped = 0
        errors: list[str] = []

        # Process actions in reverse order (last action first)
        for action in reversed(preview.actions):
            try:
                success = self._execute_rollback_action(action)
                if success:
                    rolled_back += 1
                else:
                    skipped += 1
            except Exception as e:
                error_msg = f"Failed to rollback {action.entity_type}/{action.entity_name}: {e}"
                errors.append(error_msg)
                failed += 1
                if not force:
                    break

        return RollbackResult(
            sync_id=sync_id,
            success=failed == 0,
            rolled_back=rolled_back,
            failed=failed,
            skipped=skipped,
            errors=errors,
        )

    def _build_rollback_actions(
        self,
        entries: list[SyncAuditEntry],
        entity_types: list[str] | None,
    ) -> tuple[list[RollbackAction], list[str]]:
        """Build list of rollback actions from audit entries.

        Args:
            entries: Audit entries from the sync operation
            entity_types: Optional filter for entity types

        Returns:
            Tuple of (actions, warnings)
        """
        actions: list[RollbackAction] = []
        warnings: list[str] = []

        for entry in entries:
            # Skip entries that weren't successful
            if entry.status not in ("success",):
                continue

            # Skip entries that don't match entity type filter
            if entity_types and entry.entity_type not in entity_types:
                continue

            # Skip entries that are 'skip' actions
            if entry.action == "skip":
                continue

            # Determine target system (opposite of source)
            target = entry.target

            if entry.action == "create":
                # To rollback a create, we delete the entity
                if entry.after_state is None:
                    warnings.append(
                        f"Cannot rollback create of {entry.entity_type}/{entry.entity_name}: "
                        "missing after_state (entity ID unknown)"
                    )
                    continue

                # Get entity ID from after_state
                entity_id = entry.after_state.get("id")
                if not entity_id:
                    warnings.append(
                        f"Cannot rollback create of {entry.entity_type}/{entry.entity_name}: "
                        "no ID in after_state"
                    )
                    continue

                actions.append(
                    RollbackAction(
                        entity_type=entry.entity_type,
                        entity_id=entity_id,
                        entity_name=entry.entity_name,
                        original_action="create",
                        rollback_action="delete",
                        after_state=entry.after_state,
                        target=target,
                    )
                )

            elif entry.action == "update":
                # To rollback an update, we restore the before_state
                if entry.before_state is None:
                    warnings.append(
                        f"Cannot rollback update of {entry.entity_type}/{entry.entity_name}: "
                        "missing before_state"
                    )
                    continue

                # Get entity ID from before_state or after_state
                entity_id = entry.before_state.get("id") or (
                    entry.after_state.get("id") if entry.after_state else None
                )
                if not entity_id:
                    warnings.append(
                        f"Cannot rollback update of {entry.entity_type}/{entry.entity_name}: "
                        "no ID found"
                    )
                    continue

                actions.append(
                    RollbackAction(
                        entity_type=entry.entity_type,
                        entity_id=entity_id,
                        entity_name=entry.entity_name,
                        original_action="update",
                        rollback_action="restore",
                        before_state=entry.before_state,
                        after_state=entry.after_state,
                        target=target,
                    )
                )

        return actions, warnings

    def _execute_rollback_action(self, action: RollbackAction) -> bool:
        """Execute a single rollback action.

        Args:
            action: The rollback action to execute

        Returns:
            True if successful, False if skipped

        Raises:
            Exception: If the operation fails
        """
        # Select the appropriate manager based on target
        managers = self._konnect_managers if action.target == "konnect" else self._gateway_managers

        manager = managers.get(action.entity_type)
        if manager is None:
            raise ValueError(f"No manager available for {action.entity_type} in {action.target}")

        if action.rollback_action == "delete":
            # Delete the entity
            if action.entity_id is None:
                return False
            manager.delete(action.entity_id)
            return True

        elif action.rollback_action == "restore":
            # Restore the before_state
            if action.entity_id is None or action.before_state is None:
                return False

            # Reconstruct the entity from before_state
            # The manager's update method expects an entity object
            model_class = getattr(manager, "_model_class", None)
            if model_class is None:
                raise ValueError(f"Manager for {action.entity_type} has no _model_class")

            # Create entity from before_state
            entity = model_class.model_validate(action.before_state)
            manager.update(action.entity_id, entity)
            return True

        return False
