"""OpenAPI to Kong route synchronization manager.

This module provides the OpenAPISyncManager class for parsing OpenAPI
specifications and synchronizing them with Kong routes.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog
import yaml

from system_operations_manager.integrations.kong.exceptions import (
    KongAPIError,
    KongNotFoundError,
)
from system_operations_manager.integrations.kong.models.base import KongEntityReference
from system_operations_manager.integrations.kong.models.openapi import (
    OpenAPIOperation,
    OpenAPISpec,
    RouteMapping,
    SyncApplyResult,
    SyncChange,
    SyncOperationResult,
    SyncResult,
)
from system_operations_manager.integrations.kong.models.route import Route

if TYPE_CHECKING:
    from system_operations_manager.integrations.kong.client import KongAdminClient
    from system_operations_manager.services.kong.route_manager import RouteManager
    from system_operations_manager.services.kong.service_manager import ServiceManager

logger = structlog.get_logger()

# HTTP methods recognized in OpenAPI specs
HTTP_METHODS = {"get", "post", "put", "delete", "patch", "head", "options", "trace"}


class OpenAPIParseError(KongAPIError):
    """Exception raised when OpenAPI spec parsing fails."""

    def __init__(
        self,
        message: str,
        file_path: Path | None = None,
        parse_error: str | None = None,
    ) -> None:
        """Initialize the parse error.

        Args:
            message: Error message.
            file_path: Path to the file that failed to parse.
            parse_error: Underlying parse error details.
        """
        super().__init__(message)
        self.file_path = file_path
        self.parse_error = parse_error


class BreakingChangeError(KongAPIError):
    """Exception raised when breaking changes require --force."""

    def __init__(self, breaking_changes: list[SyncChange]) -> None:
        """Initialize the breaking change error.

        Args:
            breaking_changes: List of breaking changes detected.
        """
        count = len(breaking_changes)
        super().__init__(f"{count} breaking change(s) detected. Use --force to apply.")
        self.breaking_changes = breaking_changes


class OpenAPISyncManager:
    """Manages OpenAPI to Kong route synchronization.

    This manager handles:
    - Parsing OpenAPI 3.x specifications (YAML/JSON)
    - Generating Kong route mappings from OpenAPI paths
    - Calculating diffs between spec and current Kong state
    - Detecting breaking changes
    - Applying sync operations to Kong

    Example:
        >>> manager = OpenAPISyncManager(client, route_manager, service_manager)
        >>> spec = manager.parse_openapi(Path("api-spec.yaml"))
        >>> mappings = manager.generate_route_mappings(spec, "my-service")
        >>> result = manager.calculate_diff("my-service", mappings)
        >>> if not result.has_breaking_changes:
        ...     manager.apply_sync(result)
    """

    def __init__(
        self,
        client: KongAdminClient,
        route_manager: RouteManager,
        service_manager: ServiceManager,
    ) -> None:
        """Initialize the sync manager.

        Args:
            client: Kong Admin API client.
            route_manager: Route entity manager.
            service_manager: Service entity manager.
        """
        self._client = client
        self._route_manager = route_manager
        self._service_manager = service_manager
        self._log = logger.bind(component="openapi_sync")

    def parse_openapi(self, spec_path: Path) -> OpenAPISpec:
        """Parse an OpenAPI 3.x specification file.

        Supports both YAML and JSON formats. Extracts paths, methods,
        operation IDs, and tags from the specification.

        Args:
            spec_path: Path to the OpenAPI specification file.

        Returns:
            Parsed OpenAPISpec object.

        Raises:
            OpenAPIParseError: If parsing fails.
            FileNotFoundError: If file doesn't exist.
        """
        self._log.debug("parsing_openapi_spec", path=str(spec_path))

        if not spec_path.exists():
            raise FileNotFoundError(f"OpenAPI spec not found: {spec_path}")

        try:
            content = spec_path.read_text()

            # Determine format and parse
            if spec_path.suffix.lower() in (".yaml", ".yml"):
                data = yaml.safe_load(content)
            elif spec_path.suffix.lower() == ".json":
                data = json.loads(content)
            else:
                # Try YAML first (more permissive), then JSON
                try:
                    data = yaml.safe_load(content)
                except yaml.YAMLError:
                    data = json.loads(content)

        except (yaml.YAMLError, json.JSONDecodeError) as e:
            raise OpenAPIParseError(
                f"Failed to parse {spec_path.name}",
                file_path=spec_path,
                parse_error=str(e),
            ) from e

        return self._parse_spec_data(data, spec_path)

    def _parse_spec_data(self, data: dict[str, Any], spec_path: Path) -> OpenAPISpec:
        """Parse OpenAPI spec data structure.

        Args:
            data: Parsed YAML/JSON data.
            spec_path: Path to spec file (for error messages).

        Returns:
            Parsed OpenAPISpec object.

        Raises:
            OpenAPIParseError: If spec is invalid.
        """
        # Validate OpenAPI version
        openapi_version = data.get("openapi", "")
        if not openapi_version.startswith("3."):
            swagger_version = data.get("swagger", "")
            if swagger_version:
                raise OpenAPIParseError(
                    f"Swagger {swagger_version} not supported. Please use OpenAPI 3.x.",
                    file_path=spec_path,
                )
            raise OpenAPIParseError(
                "Invalid OpenAPI spec: missing 'openapi' version field",
                file_path=spec_path,
            )

        # Extract info
        info = data.get("info", {})
        title = info.get("title", "Untitled API")
        version = info.get("version", "1.0.0")

        # Extract base path from servers
        base_path = self._extract_base_path(data.get("servers", []))

        # Parse paths and operations
        operations: list[OpenAPIOperation] = []
        all_tags: set[str] = set()
        paths = data.get("paths", {})

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            for method in HTTP_METHODS:
                if method not in path_item:
                    continue

                operation_data = path_item[method]
                if not isinstance(operation_data, dict):
                    continue

                operation_id = operation_data.get("operationId")
                tags = operation_data.get("tags", [])
                summary = operation_data.get("summary")
                deprecated = operation_data.get("deprecated", False)

                operations.append(
                    OpenAPIOperation(
                        path=path,
                        method=method.upper(),
                        operation_id=operation_id,
                        tags=tags,
                        summary=summary,
                        deprecated=deprecated,
                    )
                )

                all_tags.update(tags)

        self._log.info(
            "parsed_openapi_spec",
            title=title,
            version=version,
            operations=len(operations),
            tags=len(all_tags),
        )

        return OpenAPISpec(
            title=title,
            version=version,
            base_path=base_path,
            operations=operations,
            all_tags=sorted(all_tags),
        )

    def _extract_base_path(self, servers: list[dict[str, Any]]) -> str | None:
        """Extract base path from servers section.

        Args:
            servers: OpenAPI servers array.

        Returns:
            Base path if found, None otherwise.
        """
        if not servers:
            return None

        # Use first server URL
        url = servers[0].get("url", "")

        # Extract path portion from URL
        # Handle both absolute URLs and relative paths
        if url.startswith(("http://", "https://")):
            # Parse path from full URL
            from urllib.parse import urlparse

            parsed = urlparse(url)
            path = parsed.path
        else:
            path = url

        # Remove trailing slash
        if path and path != "/" and path.endswith("/"):
            path = path.rstrip("/")

        return path if path and path != "/" else None

    def generate_route_mappings(
        self,
        spec: OpenAPISpec,
        service_name: str,
        *,
        path_prefix: str | None = None,
        strip_path: bool = True,
    ) -> list[RouteMapping]:
        """Generate Kong route mappings from OpenAPI spec.

        Groups operations by path (one route per path with multiple methods).
        Route naming follows the pattern: {service_name}-{operationId}

        Args:
            spec: Parsed OpenAPI specification.
            service_name: Kong service name (used for route naming and tagging).
            path_prefix: Optional prefix to add to all paths.
            strip_path: Whether routes should strip the matched path.

        Returns:
            List of route mappings.
        """
        self._log.debug(
            "generating_route_mappings",
            service=service_name,
            operations=len(spec.operations),
        )

        # Group operations by path
        path_operations: dict[str, list[OpenAPIOperation]] = {}
        for op in spec.operations:
            if op.path not in path_operations:
                path_operations[op.path] = []
            path_operations[op.path].append(op)

        mappings: list[RouteMapping] = []
        used_names: set[str] = set()

        for path, operations in path_operations.items():
            # Generate route name
            route_name = self._generate_route_name(service_name, path, operations)

            # Handle name collisions
            base_name = route_name
            counter = 1
            while route_name in used_names:
                route_name = f"{base_name}-{counter}"
                counter += 1
            used_names.add(route_name)

            # Collect methods and tags
            methods = sorted({op.method for op in operations})
            operation_tags: set[str] = set()
            operation_ids: list[str] = []

            for op in operations:
                operation_tags.update(op.tags)
                if op.operation_id:
                    operation_ids.append(op.operation_id)

            # Build tags list: service name + OpenAPI tags
            tags = [f"service:{service_name}"]
            tags.extend(sorted(operation_tags))

            # Apply path prefix: explicit override > spec base_path
            effective_prefix = path_prefix if path_prefix else spec.base_path
            final_path = path
            if effective_prefix:
                final_path = f"{effective_prefix.rstrip('/')}{path}"

            mappings.append(
                RouteMapping(
                    route_name=route_name,
                    path=final_path,
                    methods=methods,
                    tags=tags,
                    operation_ids=operation_ids,
                    strip_path=strip_path,
                )
            )

        self._log.info(
            "generated_route_mappings",
            service=service_name,
            routes=len(mappings),
        )

        return mappings

    def _generate_route_name(
        self,
        service_name: str,
        path: str,
        operations: list[OpenAPIOperation],
    ) -> str:
        """Generate a route name from service and operations.

        Priority:
        1. First non-None operationId: {service}-{operationId}
        2. Path-based fallback: {service}-{sanitized-path}

        Args:
            service_name: Kong service name.
            path: OpenAPI path.
            operations: Operations for this path.

        Returns:
            Generated route name.
        """
        # Try to use first operationId
        for op in operations:
            if op.operation_id:
                return f"{service_name}-{op.operation_id}"

        # Fallback to path-based name
        sanitized_path = self._sanitize_path_for_name(path)
        return f"{service_name}-{sanitized_path}"

    def _sanitize_path_for_name(self, path: str) -> str:
        """Sanitize an OpenAPI path for use in a route name.

        Args:
            path: OpenAPI path (e.g., "/users/{userId}/profile").

        Returns:
            Sanitized name (e.g., "users-userId-profile").
        """
        # Remove path parameters braces
        sanitized = re.sub(r"\{([^}]+)\}", r"\1", path)
        # Replace slashes and other non-alphanumeric chars with hyphens
        sanitized = re.sub(r"[^a-zA-Z0-9]+", "-", sanitized)
        # Remove leading/trailing hyphens
        sanitized = sanitized.strip("-")
        # Collapse multiple hyphens
        sanitized = re.sub(r"-+", "-", sanitized)
        return sanitized.lower()

    def calculate_diff(
        self,
        service_name: str,
        mappings: list[RouteMapping],
    ) -> SyncResult:
        """Calculate changes needed to sync Kong routes with mappings.

        Compares the desired route mappings against current Kong routes
        for the service and identifies creates, updates, and deletes.

        Args:
            service_name: Kong service name.
            mappings: Desired route mappings from OpenAPI spec.

        Returns:
            SyncResult with creates, updates, and deletes.

        Raises:
            KongNotFoundError: If service doesn't exist.
        """
        self._log.debug("calculating_diff", service=service_name)

        # Verify service exists
        self._service_manager.get(service_name)

        # Get current routes for service
        current_routes = self._get_all_routes_for_service(service_name)
        current_by_name: dict[str, Route] = {r.name: r for r in current_routes if r.name}

        # Build desired state
        desired_by_name: dict[str, RouteMapping] = {m.route_name: m for m in mappings}

        creates: list[SyncChange] = []
        updates: list[SyncChange] = []
        deletes: list[SyncChange] = []

        # Find creates and updates
        for name, mapping in desired_by_name.items():
            if name not in current_by_name:
                # New route
                creates.append(
                    SyncChange(
                        operation="create",
                        route_name=name,
                        path=mapping.path,
                        methods=mapping.methods,
                        tags=mapping.tags,
                        strip_path=mapping.strip_path,
                        is_breaking=False,
                    )
                )
            else:
                # Check for updates
                current = current_by_name[name]
                changes = self._compare_route(current, mapping)
                if changes:
                    is_breaking, breaking_reason = self._is_breaking_update(current, mapping)
                    updates.append(
                        SyncChange(
                            operation="update",
                            route_name=name,
                            path=mapping.path,
                            methods=mapping.methods,
                            tags=mapping.tags,
                            strip_path=mapping.strip_path,
                            is_breaking=is_breaking,
                            breaking_reason=breaking_reason,
                            field_changes=changes,
                        )
                    )

        # Find deletes (routes in Kong not in spec)
        # Only consider routes that match our naming convention
        for name, current in current_by_name.items():
            if name.startswith(f"{service_name}-") and name not in desired_by_name:
                deletes.append(
                    SyncChange(
                        operation="delete",
                        route_name=name,
                        path=current.paths[0] if current.paths else "",
                        methods=current.methods or [],
                        tags=current.tags or [],
                        is_breaking=True,
                        breaking_reason="Route will be deleted, removing API endpoint",
                    )
                )

        result = SyncResult(
            creates=creates,
            updates=updates,
            deletes=deletes,
            service_name=service_name,
        )

        self._log.info(
            "calculated_diff",
            service=service_name,
            creates=len(creates),
            updates=len(updates),
            deletes=len(deletes),
            breaking=len(result.breaking_changes),
        )

        return result

    def _get_all_routes_for_service(self, service_name: str) -> list[Route]:
        """Get all routes for a service (handling pagination).

        Args:
            service_name: Kong service name.

        Returns:
            List of all routes for the service.
        """
        all_routes: list[Route] = []
        offset: str | None = None

        while True:
            routes, offset = self._route_manager.list_by_service(service_name, offset=offset)
            all_routes.extend(routes)
            if not offset:
                break

        return all_routes

    def _compare_route(
        self,
        current: Route,
        desired: RouteMapping,
    ) -> dict[str, tuple[Any, Any]] | None:
        """Compare current route with desired mapping.

        Args:
            current: Current Kong route.
            desired: Desired route mapping.

        Returns:
            Dictionary of changed fields {field: (old_value, new_value)},
            or None if no changes.
        """
        changes: dict[str, tuple[Any, Any]] = {}

        # Compare paths
        current_paths = set(current.paths or [])
        desired_paths = {desired.path}
        if current_paths != desired_paths:
            changes["paths"] = (sorted(current_paths), sorted(desired_paths))

        # Compare methods
        current_methods = set(current.methods or [])
        desired_methods = set(desired.methods)
        if current_methods != desired_methods:
            changes["methods"] = (sorted(current_methods), sorted(desired_methods))

        # Compare tags
        current_tags = set(current.tags or [])
        desired_tags = set(desired.tags)
        if current_tags != desired_tags:
            changes["tags"] = (sorted(current_tags), sorted(desired_tags))

        # Compare strip_path
        if current.strip_path != desired.strip_path:
            changes["strip_path"] = (current.strip_path, desired.strip_path)

        return changes if changes else None

    def _is_breaking_update(
        self,
        current: Route,
        desired: RouteMapping,
    ) -> tuple[bool, str | None]:
        """Determine if an update is a breaking change.

        Breaking changes:
        - Removing paths
        - Removing HTTP methods
        - Path structure changes that affect matching

        Args:
            current: Current Kong route.
            desired: Desired route mapping.

        Returns:
            Tuple of (is_breaking, reason).
        """
        # Check for removed paths
        current_paths = set(current.paths or [])
        desired_paths = {desired.path}
        removed_paths = current_paths - desired_paths
        if removed_paths:
            return True, f"Paths will be removed: {sorted(removed_paths)}"

        # Check for removed methods
        current_methods = set(current.methods or [])
        desired_methods = set(desired.methods)
        removed_methods = current_methods - desired_methods
        if removed_methods:
            return True, f"Methods will be removed: {sorted(removed_methods)}"

        return False, None

    def apply_sync(
        self,
        sync_result: SyncResult,
        *,
        force: bool = False,
        dry_run: bool = False,
    ) -> SyncApplyResult:
        """Apply sync changes to Kong.

        Args:
            sync_result: Calculated diff from calculate_diff().
            force: Apply breaking changes without confirmation.
            dry_run: Preview changes without applying.

        Returns:
            SyncApplyResult with operation outcomes.

        Raises:
            BreakingChangeError: If breaking changes exist and force=False.
        """
        self._log.debug(
            "applying_sync",
            service=sync_result.service_name,
            dry_run=dry_run,
            force=force,
        )

        # Check for breaking changes
        if sync_result.has_breaking_changes and not force:
            raise BreakingChangeError(sync_result.breaking_changes)

        if dry_run:
            self._log.info("dry_run_complete", changes=sync_result.total_changes)
            return SyncApplyResult(
                operations=[],
                service_name=sync_result.service_name,
            )

        operations: list[SyncOperationResult] = []

        # Apply creates
        for change in sync_result.creates:
            result = self._apply_create(sync_result.service_name, change)
            operations.append(result)

        # Apply updates
        for change in sync_result.updates:
            result = self._apply_update(change)
            operations.append(result)

        # Apply deletes
        for change in sync_result.deletes:
            result = self._apply_delete(change)
            operations.append(result)

        apply_result = SyncApplyResult(
            operations=operations,
            service_name=sync_result.service_name,
        )

        self._log.info(
            "sync_applied",
            service=sync_result.service_name,
            succeeded=len(apply_result.succeeded),
            failed=len(apply_result.failed),
        )

        return apply_result

    def _apply_create(
        self,
        service_name: str,
        change: SyncChange,
    ) -> SyncOperationResult:
        """Apply a create operation.

        Args:
            service_name: Kong service name.
            change: Create change to apply.

        Returns:
            Operation result.
        """
        try:
            route = Route(
                name=change.route_name,
                paths=[change.path],
                methods=change.methods,
                tags=change.tags,
                strip_path=change.strip_path,
                service=KongEntityReference.from_name(service_name),
            )
            self._route_manager.create_for_service(service_name, route)
            self._log.info("created_route", name=change.route_name)
            return SyncOperationResult(
                operation="create",
                route_name=change.route_name,
                result="success",
            )
        except KongAPIError as e:
            self._log.error("create_failed", name=change.route_name, error=str(e))
            return SyncOperationResult(
                operation="create",
                route_name=change.route_name,
                result="failed",
                error=str(e),
            )

    def _apply_update(self, change: SyncChange) -> SyncOperationResult:
        """Apply an update operation.

        Args:
            change: Update change to apply.

        Returns:
            Operation result.
        """
        try:
            route = Route(
                paths=[change.path],
                methods=change.methods,
                tags=change.tags,
                strip_path=change.strip_path,
            )
            self._route_manager.update(change.route_name, route)
            self._log.info("updated_route", name=change.route_name)
            return SyncOperationResult(
                operation="update",
                route_name=change.route_name,
                result="success",
            )
        except KongAPIError as e:
            self._log.error("update_failed", name=change.route_name, error=str(e))
            return SyncOperationResult(
                operation="update",
                route_name=change.route_name,
                result="failed",
                error=str(e),
            )

    def _apply_delete(self, change: SyncChange) -> SyncOperationResult:
        """Apply a delete operation.

        Args:
            change: Delete change to apply.

        Returns:
            Operation result.
        """
        try:
            self._route_manager.delete(change.route_name)
            self._log.info("deleted_route", name=change.route_name)
            return SyncOperationResult(
                operation="delete",
                route_name=change.route_name,
                result="success",
            )
        except KongNotFoundError:
            # Route already deleted, consider success
            self._log.warning("route_already_deleted", name=change.route_name)
            return SyncOperationResult(
                operation="delete",
                route_name=change.route_name,
                result="success",
            )
        except KongAPIError as e:
            self._log.error("delete_failed", name=change.route_name, error=str(e))
            return SyncOperationResult(
                operation="delete",
                route_name=change.route_name,
                result="failed",
                error=str(e),
            )
