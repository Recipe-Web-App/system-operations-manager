"""Configuration manager for Kong declarative configuration.

This module provides the ConfigManager class for handling export, validation,
diff, and apply operations for Kong's declarative configuration format.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from system_operations_manager.integrations.kong.client import KongAdminClient

from system_operations_manager.integrations.kong.models.config import (
    ApplyOperation,
    ConfigDiff,
    ConfigDiffSummary,
    ConfigValidationError,
    ConfigValidationResult,
    DeclarativeConfig,
)

logger = structlog.get_logger()


class ConfigManager:
    """Manager for Kong declarative configuration operations.

    Provides methods to:
    - Export current Kong state to declarative config
    - Validate config files against Kong schemas
    - Diff current state with desired config
    - Apply declarative config with dependency ordering

    Example:
        >>> manager = ConfigManager(client)
        >>> config = manager.export_state()
        >>> diff = manager.diff_config(desired_config)
        >>> manager.apply_config(desired_config)
    """

    # Entity types in dependency order for apply
    ENTITY_ORDER = [
        "services",
        "upstreams",
        "routes",
        "consumers",
        "plugins",
    ]

    # Entity types in reverse order for delete
    DELETE_ORDER = [
        "plugins",
        "consumers",
        "routes",
        "upstreams",
        "services",
    ]

    def __init__(self, client: KongAdminClient) -> None:
        """Initialize the config manager.

        Args:
            client: Kong Admin API client instance.
        """
        self._client = client
        self._log = logger.bind(service="config_manager")

    # =========================================================================
    # Export Methods
    # =========================================================================

    def export_state(
        self,
        *,
        only: list[str] | None = None,
        include_credentials: bool = False,
    ) -> DeclarativeConfig:
        """Export current Kong state to declarative config.

        Fetches all entities from Kong and assembles them into a
        declarative configuration format.

        Args:
            only: Filter to specific entity types (e.g., ['services', 'routes']).
            include_credentials: Whether to include consumer credentials.

        Returns:
            DeclarativeConfig with current state.
        """
        self._log.info(
            "exporting_kong_state",
            only=only,
            include_credentials=include_credentials,
        )

        config = DeclarativeConfig()

        entity_types = only if only else self.ENTITY_ORDER

        for entity_type in entity_types:
            if entity_type == "services":
                config.services = self._export_services()
            elif entity_type == "routes":
                config.routes = self._export_routes()
            elif entity_type == "upstreams":
                config.upstreams = self._export_upstreams()
            elif entity_type == "consumers":
                config.consumers = self._export_consumers(include_credentials)
            elif entity_type == "plugins":
                config.plugins = self._export_plugins()

        self._log.info(
            "export_complete",
            services=len(config.services),
            routes=len(config.routes),
            upstreams=len(config.upstreams),
            consumers=len(config.consumers),
            plugins=len(config.plugins),
        )

        return config

    def _export_services(self) -> list[dict[str, Any]]:
        """Export all services."""
        self._log.debug("exporting_services")
        response = self._client.get("services")
        return self._clean_entities(response.get("data", []))

    def _export_routes(self) -> list[dict[str, Any]]:
        """Export all routes."""
        self._log.debug("exporting_routes")
        response = self._client.get("routes")
        return self._clean_entities(response.get("data", []))

    def _export_upstreams(self) -> list[dict[str, Any]]:
        """Export all upstreams with embedded targets."""
        self._log.debug("exporting_upstreams")
        response = self._client.get("upstreams")
        upstreams = response.get("data", [])

        # For each upstream, fetch and embed targets
        for upstream in upstreams:
            name = upstream.get("name") or upstream.get("id")
            if name:
                try:
                    targets_response = self._client.get(f"upstreams/{name}/targets")
                    targets = self._clean_entities(targets_response.get("data", []))
                    if targets:
                        upstream["targets"] = targets
                except Exception as e:
                    self._log.warning(
                        "failed_to_export_targets",
                        upstream=name,
                        error=str(e),
                    )

        return self._clean_entities(upstreams)

    def _export_consumers(self, include_credentials: bool) -> list[dict[str, Any]]:
        """Export all consumers, optionally with credentials."""
        self._log.debug("exporting_consumers", include_credentials=include_credentials)
        response = self._client.get("consumers")
        consumers = response.get("data", [])

        if include_credentials:
            credential_types = ["key-auth", "basic-auth", "jwt", "oauth2", "acls"]
            for consumer in consumers:
                consumer_id = consumer.get("id") or consumer.get("username")
                if not consumer_id:
                    continue

                for cred_type in credential_types:
                    try:
                        creds_response = self._client.get(f"consumers/{consumer_id}/{cred_type}")
                        creds = creds_response.get("data", [])
                        if creds:
                            # Store with underscored key for declarative format
                            key = cred_type.replace("-", "_")
                            consumer[key] = self._clean_entities(creds)
                    except Exception:
                        # Credential type not enabled or no credentials
                        pass

        return self._clean_entities(consumers)

    def _export_plugins(self) -> list[dict[str, Any]]:
        """Export all plugins."""
        self._log.debug("exporting_plugins")
        response = self._client.get("plugins")
        return self._clean_entities(response.get("data", []))

    def _clean_entities(self, entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove server-assigned fields from entities.

        Removes created_at, updated_at, and None values to produce
        clean declarative configuration.

        Args:
            entities: List of entity dictionaries.

        Returns:
            Cleaned entity list.
        """
        cleaned = []
        for entity in entities:
            clean = {
                k: v
                for k, v in entity.items()
                if k not in ("created_at", "updated_at") and v is not None
            }
            cleaned.append(clean)
        return cleaned

    # =========================================================================
    # Validation Methods
    # =========================================================================

    def validate_config(self, config: DeclarativeConfig) -> ConfigValidationResult:
        """Validate a declarative config.

        Checks:
        - Schema validation (Pydantic already handles this)
        - Reference integrity (routes reference valid services, etc.)

        Args:
            config: Configuration to validate.

        Returns:
            ConfigValidationResult with errors and warnings.
        """
        self._log.info("validating_config")

        errors: list[ConfigValidationError] = []
        warnings: list[ConfigValidationError] = []

        # Collect entity names/IDs for reference validation
        service_ids = self._collect_identifiers(config.services)
        consumer_ids = self._collect_identifiers(config.consumers)
        route_ids = self._collect_identifiers(config.routes)

        # Validate routes reference valid services
        for i, route in enumerate(config.routes):
            service_ref = route.get("service")
            if service_ref:
                ref_id = service_ref.get("id") or service_ref.get("name")
                if ref_id and ref_id not in service_ids:
                    errors.append(
                        ConfigValidationError(
                            path=f"routes[{i}].service",
                            message=f"Route references unknown service: {ref_id}",
                            entity_type="route",
                            entity_name=route.get("name"),
                        )
                    )

        # Validate plugins reference valid entities
        for i, plugin in enumerate(config.plugins):
            # Check service reference
            svc_ref = plugin.get("service")
            if isinstance(svc_ref, dict):
                ref_id = svc_ref.get("id") or svc_ref.get("name")
                if ref_id and ref_id not in service_ids:
                    errors.append(
                        ConfigValidationError(
                            path=f"plugins[{i}].service",
                            message=f"Plugin references unknown service: {ref_id}",
                            entity_type="plugin",
                            entity_name=plugin.get("name"),
                        )
                    )

            # Check route reference
            route_ref = plugin.get("route")
            if isinstance(route_ref, dict):
                ref_id = route_ref.get("id") or route_ref.get("name")
                if ref_id and ref_id not in route_ids:
                    errors.append(
                        ConfigValidationError(
                            path=f"plugins[{i}].route",
                            message=f"Plugin references unknown route: {ref_id}",
                            entity_type="plugin",
                            entity_name=plugin.get("name"),
                        )
                    )

            # Check consumer reference
            consumer_ref = plugin.get("consumer")
            if isinstance(consumer_ref, dict):
                ref_id = consumer_ref.get("id") or consumer_ref.get("username")
                if ref_id and ref_id not in consumer_ids:
                    errors.append(
                        ConfigValidationError(
                            path=f"plugins[{i}].consumer",
                            message=f"Plugin references unknown consumer: {ref_id}",
                            entity_type="plugin",
                            entity_name=plugin.get("name"),
                        )
                    )

        # Warn about plugins without scope
        for i, plugin in enumerate(config.plugins):
            if not any(plugin.get(scope) for scope in ("service", "route", "consumer")):
                warnings.append(
                    ConfigValidationError(
                        path=f"plugins[{i}]",
                        message="Plugin has no scope (service, route, or consumer) - will be global",
                        entity_type="plugin",
                        entity_name=plugin.get("name"),
                    )
                )

        result = ConfigValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

        self._log.info(
            "validation_complete",
            valid=result.valid,
            errors=len(errors),
            warnings=len(warnings),
        )

        return result

    def _collect_identifiers(self, entities: list[dict[str, Any]]) -> set[str]:
        """Collect all IDs and names from entities.

        Args:
            entities: List of entity dictionaries.

        Returns:
            Set of all entity identifiers (IDs and names).
        """
        ids = set()
        for entity in entities:
            if entity.get("id"):
                ids.add(entity["id"])
            if entity.get("name"):
                ids.add(entity["name"])
            if entity.get("username"):
                ids.add(entity["username"])
        return ids

    # =========================================================================
    # Diff Methods
    # =========================================================================

    def diff_config(self, desired: DeclarativeConfig) -> ConfigDiffSummary:
        """Calculate diff between current state and desired config.

        Compares entity by entity to determine what operations are needed.

        Args:
            desired: The desired configuration state.

        Returns:
            ConfigDiffSummary with all required changes.
        """
        self._log.info("diffing_config")

        current = self.export_state()
        diffs: list[ConfigDiff] = []

        for entity_type in self.ENTITY_ORDER:
            current_entities = getattr(current, entity_type, [])
            desired_entities = getattr(desired, entity_type, [])

            entity_diffs = self._diff_entity_list(
                entity_type,
                current_entities,
                desired_entities,
            )
            diffs.extend(entity_diffs)

        # Build summary
        summary = ConfigDiffSummary(total_changes=len(diffs), diffs=diffs)
        for diff in diffs:
            if diff.operation == "create":
                summary.creates[diff.entity_type] = summary.creates.get(diff.entity_type, 0) + 1
            elif diff.operation == "update":
                summary.updates[diff.entity_type] = summary.updates.get(diff.entity_type, 0) + 1
            elif diff.operation == "delete":
                summary.deletes[diff.entity_type] = summary.deletes.get(diff.entity_type, 0) + 1

        self._log.info(
            "diff_complete",
            total=summary.total_changes,
            creates=sum(summary.creates.values()),
            updates=sum(summary.updates.values()),
            deletes=sum(summary.deletes.values()),
        )

        return summary

    def _diff_entity_list(
        self,
        entity_type: str,
        current: list[dict[str, Any]],
        desired: list[dict[str, Any]],
    ) -> list[ConfigDiff]:
        """Diff two lists of entities.

        Args:
            entity_type: Type of entity being compared.
            current: Current entities from Kong.
            desired: Desired entities from config.

        Returns:
            List of ConfigDiff objects describing changes.
        """
        diffs = []

        # Index by name or ID
        current_map = {self._entity_key(e): e for e in current}
        desired_map = {self._entity_key(e): e for e in desired}

        # Find creates and updates
        for key, desired_entity in desired_map.items():
            if key not in current_map:
                diffs.append(
                    ConfigDiff(
                        entity_type=entity_type,
                        operation="create",
                        id_or_name=key,
                        desired=desired_entity,
                    )
                )
            else:
                changes = self._diff_entity(current_map[key], desired_entity)
                if changes:
                    diffs.append(
                        ConfigDiff(
                            entity_type=entity_type,
                            operation="update",
                            id_or_name=key,
                            current=current_map[key],
                            desired=desired_entity,
                            changes=changes,
                        )
                    )

        # Find deletes
        for key, current_entity in current_map.items():
            if key not in desired_map:
                diffs.append(
                    ConfigDiff(
                        entity_type=entity_type,
                        operation="delete",
                        id_or_name=key,
                        current=current_entity,
                    )
                )

        return diffs

    def _entity_key(self, entity: dict[str, Any]) -> str:
        """Get unique key for an entity (name, username, or ID).

        Args:
            entity: Entity dictionary.

        Returns:
            String key for indexing.
        """
        return (
            entity.get("name")
            or entity.get("username")
            or entity.get("id")
            or str(hash(frozenset(entity.items())))
        )

    def _diff_entity(
        self,
        current: dict[str, Any],
        desired: dict[str, Any],
    ) -> dict[str, tuple[Any, Any]] | None:
        """Compare two entities and return field-level changes.

        Args:
            current: Current entity state.
            desired: Desired entity state.

        Returns:
            Dictionary of changed fields with (old, new) values, or None if identical.
        """
        changes: dict[str, tuple[Any, Any]] = {}
        ignore_keys = {"id", "created_at", "updated_at"}

        all_keys = set(current.keys()) | set(desired.keys())

        for key in all_keys - ignore_keys:
            curr_val = current.get(key)
            desired_val = desired.get(key)
            if curr_val != desired_val:
                changes[key] = (curr_val, desired_val)

        return changes if changes else None

    # =========================================================================
    # Apply Methods
    # =========================================================================

    def apply_config(
        self,
        config: DeclarativeConfig,
        *,
        dry_run: bool = False,
    ) -> list[ApplyOperation]:
        """Apply declarative config to Kong.

        Applies changes in dependency order:
        1. Services, Upstreams (no dependencies)
        2. Routes (depend on services)
        3. Consumers (no dependencies)
        4. Plugins (depend on services, routes, consumers)

        Deletes are performed in reverse dependency order.

        Args:
            config: The desired configuration.
            dry_run: If True, only calculate changes without applying.

        Returns:
            List of operations performed.
        """
        self._log.info("applying_config", dry_run=dry_run)

        diff = self.diff_config(config)
        operations: list[ApplyOperation] = []

        if dry_run:
            # Return what would be done
            for d in diff.diffs:
                operations.append(
                    ApplyOperation(
                        operation=d.operation,
                        entity_type=d.entity_type,
                        id_or_name=d.id_or_name,
                        result="success",
                    )
                )
            return operations

        # Apply creates and updates in dependency order
        for entity_type in self.ENTITY_ORDER:
            type_diffs = [d for d in diff.diffs if d.entity_type == entity_type]

            # Creates first, then updates
            for operation in ["create", "update"]:
                for diff_item in type_diffs:
                    if diff_item.operation == operation and diff_item.desired:
                        result = self._apply_entity(entity_type, diff_item)
                        operations.append(result)

        # Deletes in reverse dependency order
        for entity_type in self.DELETE_ORDER:
            type_diffs = [
                d for d in diff.diffs if d.entity_type == entity_type and d.operation == "delete"
            ]
            for diff_item in type_diffs:
                result = self._delete_entity(entity_type, diff_item)
                operations.append(result)

        self._log.info(
            "apply_complete",
            total_operations=len(operations),
            successful=len([o for o in operations if o.result == "success"]),
            failed=len([o for o in operations if o.result == "failed"]),
        )

        return operations

    def _apply_entity(
        self,
        entity_type: str,
        diff_item: ConfigDiff,
    ) -> ApplyOperation:
        """Apply a single entity create/update.

        Args:
            entity_type: Type of entity.
            diff_item: Diff describing the change.

        Returns:
            ApplyOperation result.
        """
        endpoint = entity_type

        try:
            if diff_item.operation == "create":
                self._client.post(endpoint, json=diff_item.desired)
            else:
                self._client.patch(
                    f"{endpoint}/{diff_item.id_or_name}",
                    json=diff_item.desired,
                )

            self._log.debug(
                "entity_applied",
                operation=diff_item.operation,
                entity_type=entity_type,
                id_or_name=diff_item.id_or_name,
            )

            return ApplyOperation(
                operation=diff_item.operation,
                entity_type=entity_type,
                id_or_name=diff_item.id_or_name,
                result="success",
            )

        except Exception as e:
            self._log.error(
                "entity_apply_failed",
                operation=diff_item.operation,
                entity_type=entity_type,
                id_or_name=diff_item.id_or_name,
                error=str(e),
            )

            return ApplyOperation(
                operation=diff_item.operation,
                entity_type=entity_type,
                id_or_name=diff_item.id_or_name,
                result="failed",
                error=str(e),
            )

    def _delete_entity(
        self,
        entity_type: str,
        diff_item: ConfigDiff,
    ) -> ApplyOperation:
        """Delete a single entity.

        Args:
            entity_type: Type of entity.
            diff_item: Diff describing the deletion.

        Returns:
            ApplyOperation result.
        """
        try:
            self._client.delete(f"{entity_type}/{diff_item.id_or_name}")

            self._log.debug(
                "entity_deleted",
                entity_type=entity_type,
                id_or_name=diff_item.id_or_name,
            )

            return ApplyOperation(
                operation="delete",
                entity_type=entity_type,
                id_or_name=diff_item.id_or_name,
                result="success",
            )

        except Exception as e:
            self._log.error(
                "entity_delete_failed",
                entity_type=entity_type,
                id_or_name=diff_item.id_or_name,
                error=str(e),
            )

            return ApplyOperation(
                operation="delete",
                entity_type=entity_type,
                id_or_name=diff_item.id_or_name,
                result="failed",
                error=str(e),
            )

    # =========================================================================
    # DB-less Mode Methods
    # =========================================================================

    def sync_config(
        self,
        config: DeclarativeConfig,
    ) -> dict[str, Any]:
        """Sync declarative config to Kong using the /config endpoint.

        This method is specifically for Kong DB-less mode. It pushes the entire
        declarative configuration to Kong using the /config endpoint, which
        completely replaces the current configuration.

        Unlike apply_config which uses individual entity endpoints, this method
        is the proper way to apply configuration in DB-less mode.

        Args:
            config: The complete desired configuration.

        Returns:
            Dict containing the response from Kong.

        Raises:
            KongAPIError: If the sync fails.
        """
        self._log.info("syncing_config_dbless")

        # Convert config to dict for API
        config_data = config.model_dump(exclude_none=True, by_alias=True)

        # Remove internal metadata fields that Kong doesn't recognize
        # These are added by the export function for tracking purposes
        internal_fields = ["_metadata", "_info", "_comment"]
        for field in internal_fields:
            config_data.pop(field, None)

        # POST to /config endpoint
        response = self._client.post("config", json=config_data)

        self._log.info(
            "sync_complete",
            services=len(config.services) if config.services else 0,
            routes=len(config.routes) if config.routes else 0,
            consumers=len(config.consumers) if config.consumers else 0,
            plugins=len(config.plugins) if config.plugins else 0,
        )

        return response

    def is_dbless_mode(self) -> bool:
        """Check if Kong is running in DB-less mode.

        Returns:
            True if Kong is in DB-less mode, False otherwise.
        """
        try:
            response = self._client.get("")
            config = response.get("configuration", {})
            database = config.get("database", "postgres")
            return str(database) == "off"
        except Exception:
            # If we can't determine, assume DB mode (safer default)
            return False
