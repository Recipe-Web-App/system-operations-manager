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

    # Nested entity mappings - fields that contain child entities
    # These are valid in declarative config but need special handling for REST API
    NESTED_ENTITIES = {
        "services": {
            "routes": "service",  # routes nested in services, use 'service' as parent ref
            "plugins": "service",  # plugins nested in services
        },
        "routes": {
            "plugins": "route",  # plugins nested in routes
        },
        "upstreams": {
            "targets": "upstream",  # targets nested in upstreams
        },
        "consumers": {
            "plugins": "consumer",  # plugins nested in consumers
            # Credential types - declarative config field names
            "keyauth_credentials": "key-auth",  # API endpoint suffix
            "basicauth_credentials": "basic-auth",
            "jwt_secrets": "jwt",
            "oauth2_credentials": "oauth2",
            "acls": "acls",
            "hmacauth_credentials": "hmac-auth",
        },
    }

    def __init__(self, client: KongAdminClient) -> None:
        """Initialize the config manager.

        Args:
            client: Kong Admin API client instance.
        """
        self._client = client
        self._log = logger.bind(service="config_manager")

    # =========================================================================
    # Config Flattening (for DB mode)
    # =========================================================================

    def _flatten_config(self, config: DeclarativeConfig) -> DeclarativeConfig:
        """Flatten nested entities in declarative config for DB mode.

        Kong's declarative config format allows nesting entities (e.g., routes
        inside services). This is supported by the /config endpoint (DB-less mode)
        but NOT by individual entity endpoints (DB mode).

        This method extracts nested entities and adds proper parent references
        so they can be created via the REST API.

        Args:
            config: Configuration with potentially nested entities.

        Returns:
            Flattened configuration with all entities at top level.
        """
        # Start with copies of top-level entities
        flat_services = []
        flat_routes = list(config.routes)
        flat_upstreams = []
        flat_consumers = list(config.consumers)
        flat_plugins = list(config.plugins)

        # Process services - extract nested routes and plugins
        for service in config.services:
            service_copy = dict(service)
            service_name = service.get("name") or service.get("id")

            # Extract nested routes
            if "routes" in service_copy:
                for route in service_copy.pop("routes"):
                    route_copy = dict(route)
                    # Add service reference if not already present
                    if "service" not in route_copy and service_name:
                        route_copy["service"] = {"name": service_name}
                    flat_routes.append(route_copy)

            # Extract nested plugins
            if "plugins" in service_copy:
                for plugin in service_copy.pop("plugins"):
                    plugin_copy = dict(plugin)
                    # Add service reference if not already present
                    if "service" not in plugin_copy and service_name:
                        plugin_copy["service"] = {"name": service_name}
                    flat_plugins.append(plugin_copy)

            flat_services.append(service_copy)

        # Process upstreams - keep targets nested (handled specially in _apply_entity)
        for upstream in config.upstreams:
            upstream_copy = dict(upstream)
            # Targets are handled specially - they're created via /upstreams/{name}/targets
            # We keep them nested for now and handle in _apply_entity
            flat_upstreams.append(upstream_copy)

        # Process routes - extract nested plugins
        processed_routes = []
        for route in flat_routes:
            route_copy = dict(route)
            route_name = route.get("name") or route.get("id")

            if "plugins" in route_copy:
                for plugin in route_copy.pop("plugins"):
                    plugin_copy = dict(plugin)
                    if "route" not in plugin_copy and route_name:
                        plugin_copy["route"] = {"name": route_name}
                    flat_plugins.append(plugin_copy)

            processed_routes.append(route_copy)

        # Process consumers - extract nested plugins and credentials
        processed_consumers = []
        for consumer in flat_consumers:
            consumer_copy = dict(consumer)
            consumer_id = consumer.get("username") or consumer.get("id")

            if "plugins" in consumer_copy:
                for plugin in consumer_copy.pop("plugins"):
                    plugin_copy = dict(plugin)
                    if "consumer" not in plugin_copy and consumer_id:
                        plugin_copy["consumer"] = {"username": consumer_id}
                    flat_plugins.append(plugin_copy)

            # Credentials stay nested - handled specially in _apply_entity
            processed_consumers.append(consumer_copy)

        # Create flattened config using model_validate to avoid mypy alias issues
        flattened = DeclarativeConfig.model_validate(
            {
                "_format_version": config.format_version,
                "_transform": config.transform,
                "services": flat_services,
                "routes": processed_routes,
                "upstreams": flat_upstreams,
                "consumers": processed_consumers,
                "plugins": flat_plugins,
                "certificates": config.certificates,
                "ca_certificates": config.ca_certificates,
            }
        )

        self._log.debug(
            "config_flattened",
            services=len(flat_services),
            routes=len(processed_routes),
            upstreams=len(flat_upstreams),
            consumers=len(processed_consumers),
            plugins=len(flat_plugins),
        )

        return flattened

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
        In DB mode, flattens nested entities before comparing.

        Args:
            desired: The desired configuration state.

        Returns:
            ConfigDiffSummary with all required changes.
        """
        self._log.info("diffing_config")

        # Flatten nested entities for DB mode comparison
        if not self.is_dbless_mode():
            desired = self._flatten_config(desired)

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

        # Index by name or ID (pass entity_type for proper plugin keying)
        current_map = {self._entity_key(e, entity_type): e for e in current}
        desired_map = {self._entity_key(e, entity_type): e for e in desired}

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

    def _entity_key(self, entity: dict[str, Any], entity_type: str = "") -> str:
        """Get unique key for an entity.

        For most entities, uses name, username, or ID.
        For plugins, includes the scope (service/route/consumer) to ensure uniqueness
        since multiple plugins with the same name can exist on different parents.

        Args:
            entity: Entity dictionary.
            entity_type: Type of entity (used for special handling of plugins).

        Returns:
            String key for indexing.
        """
        # For plugins, create compound key with scope
        if entity_type == "plugins" or entity.get("name") in (
            "key-auth",
            "basic-auth",
            "jwt",
            "oauth2",
            "acl",
            "rate-limiting",
            "request-size-limiting",
            "request-transformer",
            "response-transformer",
            "cors",
            "ip-restriction",
            "bot-detection",
            "aws-lambda",
            "http-log",
            "file-log",
            "tcp-log",
            "udp-log",
            "syslog",
            "prometheus",
            "datadog",
            "zipkin",
            "opentelemetry",
            "proxy-cache",
            "response-ratelimiting",
        ):
            plugin_name = entity.get("name", "")
            scope_parts = []

            # Check for service scope
            service_ref = entity.get("service")
            if service_ref:
                svc_name = self._extract_ref_name(service_ref)
                if svc_name:
                    scope_parts.append(f"service:{svc_name}")

            # Check for route scope
            route_ref = entity.get("route")
            if route_ref:
                route_name = self._extract_ref_name(route_ref)
                if route_name:
                    scope_parts.append(f"route:{route_name}")

            # Check for consumer scope
            consumer_ref = entity.get("consumer")
            if consumer_ref:
                consumer_name = self._extract_ref_name(consumer_ref, prefer_username=True)
                if consumer_name:
                    scope_parts.append(f"consumer:{consumer_name}")

            if scope_parts:
                return f"{plugin_name}@{','.join(sorted(scope_parts))}"
            else:
                # Global plugin - use ID if available to ensure uniqueness
                return entity.get("id") or f"{plugin_name}@global"

        # Standard entity key
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

        Handles special cases:
        - Plugins with parent refs: uses nested endpoints (/services/{name}/plugins)
        - Upstreams with nested targets: creates targets via /upstreams/{name}/targets
        - Strips any nested entity fields before sending to API

        Args:
            entity_type: Type of entity.
            diff_item: Diff describing the change.

        Returns:
            ApplyOperation result.
        """
        try:
            # Prepare entity data - strip nested fields that Kong API doesn't accept
            entity_data = self._prepare_entity_for_api(entity_type, diff_item.desired)

            # Determine the correct endpoint - plugins use nested endpoints
            endpoint = self._get_entity_endpoint(entity_type, entity_data)

            if diff_item.operation == "create":
                self._client.post(endpoint, json=entity_data)
            else:
                # For updates, use the ID from current state if available
                # This is important for plugins where id_or_name may be a compound key
                update_id = diff_item.id_or_name
                if diff_item.current:
                    update_id = (
                        diff_item.current.get("id")
                        or diff_item.current.get("name")
                        or diff_item.id_or_name
                    )
                self._client.patch(
                    f"{entity_type}/{update_id}",
                    json=entity_data,
                )

            # Handle nested targets for upstreams
            if entity_type == "upstreams" and diff_item.desired:
                self._apply_nested_targets(diff_item.id_or_name, diff_item.desired)

            # Handle nested credentials for consumers
            if entity_type == "consumers" and diff_item.desired:
                self._apply_consumer_credentials(diff_item.id_or_name, diff_item.desired)

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

    def _get_entity_endpoint(
        self,
        entity_type: str,
        entity_data: dict[str, Any],
    ) -> str:
        """Get the correct API endpoint for an entity.

        For plugins, routes, and other entities that can be scoped to a parent,
        uses nested endpoints when a parent reference is present.

        Examples:
        - Plugin with service ref -> /services/{name}/plugins
        - Plugin with route ref -> /routes/{name}/plugins
        - Route with service ref -> /services/{name}/routes
        - Regular entity -> /{entity_type}

        Args:
            entity_type: Type of entity.
            entity_data: Entity data (may contain parent references).

        Returns:
            API endpoint path.
        """
        if entity_type == "plugins":
            # Plugins can be scoped to service, route, or consumer
            # Check for parent references and use nested endpoint
            if "service" in entity_data:
                service_name = self._extract_ref_name(entity_data.get("service"))
                if service_name:
                    # Remove the service ref from entity_data since we're using nested endpoint
                    entity_data.pop("service", None)
                    return f"services/{service_name}/plugins"

            if "route" in entity_data:
                route_name = self._extract_ref_name(entity_data.get("route"))
                if route_name:
                    entity_data.pop("route", None)
                    return f"routes/{route_name}/plugins"

            if "consumer" in entity_data:
                consumer_ref = entity_data.get("consumer")
                consumer_name = self._extract_ref_name(consumer_ref, prefer_username=True)
                if consumer_name:
                    entity_data.pop("consumer", None)
                    return f"consumers/{consumer_name}/plugins"

        elif entity_type == "routes":
            # Routes can be scoped to a service
            if "service" in entity_data:
                service_name = self._extract_ref_name(entity_data.get("service"))
                if service_name:
                    entity_data.pop("service", None)
                    return f"services/{service_name}/routes"

        # Default: use the entity type as endpoint
        return entity_type

    def _extract_ref_name(
        self,
        ref: str | dict[str, Any] | None,
        prefer_username: bool = False,
    ) -> str | None:
        """Extract entity name/id from a reference.

        References can be:
        - A string (the name/id directly)
        - A dict with 'name', 'id', or 'username' key

        Args:
            ref: Reference value (string or dict).
            prefer_username: If True, check 'username' before 'name' (for consumers).

        Returns:
            The extracted name/id, or None if not found.
        """
        if ref is None:
            return None

        if isinstance(ref, str):
            return ref

        if isinstance(ref, dict):
            if prefer_username:
                return ref.get("username") or ref.get("name") or ref.get("id")
            return ref.get("name") or ref.get("id")

        return None

    def _prepare_entity_for_api(
        self,
        entity_type: str,
        entity: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Prepare entity data for Kong Admin API.

        Removes nested entity fields that aren't accepted by the REST API.
        These nested fields are valid in declarative config but must be
        handled separately when using individual entity endpoints.

        Args:
            entity_type: Type of entity.
            entity: Entity data to prepare.

        Returns:
            Cleaned entity data suitable for REST API.
        """
        if entity is None:
            return {}

        # Fields to strip based on entity type
        nested_fields = self.NESTED_ENTITIES.get(entity_type, {})

        # Create a copy without nested fields
        cleaned = {k: v for k, v in entity.items() if k not in nested_fields}

        return cleaned

    def _apply_nested_targets(
        self,
        upstream_name: str,
        upstream_data: dict[str, Any],
    ) -> None:
        """Apply nested targets to an upstream.

        Targets in declarative config are nested under upstreams but must
        be created via the /upstreams/{name}/targets endpoint.

        Args:
            upstream_name: Name of the upstream.
            upstream_data: Upstream data that may contain nested targets.
        """
        targets = upstream_data.get("targets", [])
        if not targets:
            return

        for target in targets:
            target_data = {k: v for k, v in target.items() if k not in ("id", "created_at")}
            try:
                self._client.post(f"upstreams/{upstream_name}/targets", json=target_data)
                self._log.debug(
                    "target_applied",
                    upstream=upstream_name,
                    target=target_data.get("target"),
                )
            except Exception as e:
                self._log.warning(
                    "target_apply_failed",
                    upstream=upstream_name,
                    target=target_data.get("target"),
                    error=str(e),
                )

    def _apply_consumer_credentials(
        self,
        consumer_name: str,
        consumer_data: dict[str, Any],
    ) -> None:
        """Apply nested credentials to a consumer.

        Credentials in declarative config are nested under consumers but must
        be created via specific endpoints like /consumers/{name}/key-auth.

        Args:
            consumer_name: Username or ID of the consumer.
            consumer_data: Consumer data that may contain nested credentials.
        """
        # Map of declarative config field names to API endpoint suffixes
        credential_endpoints = {
            "keyauth_credentials": "key-auth",
            "basicauth_credentials": "basic-auth",
            "jwt_secrets": "jwt",
            "oauth2_credentials": "oauth2",
            "acls": "acls",
            "hmacauth_credentials": "hmac-auth",
        }

        for field_name, endpoint_suffix in credential_endpoints.items():
            credentials = consumer_data.get(field_name, [])
            if not credentials:
                continue

            for credential in credentials:
                cred_data = {
                    k: v for k, v in credential.items() if k not in ("id", "created_at", "consumer")
                }
                try:
                    self._client.post(
                        f"consumers/{consumer_name}/{endpoint_suffix}",
                        json=cred_data,
                    )
                    self._log.debug(
                        "credential_applied",
                        consumer=consumer_name,
                        credential_type=endpoint_suffix,
                    )
                except Exception as e:
                    self._log.warning(
                        "credential_apply_failed",
                        consumer=consumer_name,
                        credential_type=endpoint_suffix,
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
            # Use ID from current state if available (for plugins with compound keys)
            delete_id = diff_item.id_or_name
            if diff_item.current:
                delete_id = (
                    diff_item.current.get("id")
                    or diff_item.current.get("name")
                    or diff_item.id_or_name
                )
            self._client.delete(f"{entity_type}/{delete_id}")

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
