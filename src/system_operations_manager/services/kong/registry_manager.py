"""Registry manager for Kong Service Registry.

This module provides the RegistryManager class for managing the local
service registry file and deploying services to Kong.

Config location: ~/.config/ops/kong/services.yaml
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog
import yaml

from system_operations_manager.integrations.kong.exceptions import KongNotFoundError
from system_operations_manager.integrations.kong.models.service import Service
from system_operations_manager.integrations.kong.models.service_registry import (
    ServiceAlreadyExistsError,
    ServiceDeployDiff,
    ServiceDeployResult,
    ServiceDeploySummary,
    ServiceNotFoundError,
    ServiceRegistry,
    ServiceRegistryEntry,
)

if TYPE_CHECKING:
    from system_operations_manager.services.kong.openapi_sync_manager import OpenAPISyncManager
    from system_operations_manager.services.kong.service_manager import ServiceManager

logger = structlog.get_logger()

# Default config directory following XDG conventions
DEFAULT_CONFIG_DIR = Path.home() / ".config" / "ops" / "kong"
DEFAULT_REGISTRY_FILE = "services.yaml"


class RegistryManager:
    """Manager for Kong Service Registry operations.

    Handles loading, saving, and modifying the local service registry,
    as well as deploying services to Kong.

    Attributes:
        config_path: Path to the registry YAML file.

    Example:
        >>> manager = RegistryManager()
        >>> manager.add_service(ServiceRegistryEntry(name="api", host="api.local"))
        >>> registry = manager.load()
        >>> print(len(registry.services))
        1
    """

    # Fields to compare for detecting service changes
    COMPARE_FIELDS = [
        "host",
        "port",
        "protocol",
        "path",
        "retries",
        "connect_timeout",
        "write_timeout",
        "read_timeout",
        "tags",
        "enabled",
    ]

    def __init__(self, config_dir: Path | None = None) -> None:
        """Initialize the registry manager.

        Args:
            config_dir: Directory for config files. Defaults to ~/.config/ops/kong/
        """
        if config_dir is None:
            config_dir = DEFAULT_CONFIG_DIR
        self.config_dir = config_dir
        self.config_path = config_dir / DEFAULT_REGISTRY_FILE
        self._log = logger.bind(service="registry_manager")

    def _ensure_config_dir(self) -> None:
        """Ensure the config directory exists."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> ServiceRegistry:
        """Load the service registry from disk.

        Returns:
            ServiceRegistry containing all configured services.

        Raises:
            RegistryNotFoundError: If the registry file doesn't exist.
        """
        self._log.debug("loading_registry", path=str(self.config_path))

        if not self.config_path.exists():
            # Return empty registry if file doesn't exist
            self._log.debug("registry_not_found_returning_empty", path=str(self.config_path))
            return ServiceRegistry(services=[])

        content = self.config_path.read_text()
        if not content.strip():
            return ServiceRegistry(services=[])

        data = yaml.safe_load(content)
        if data is None:
            return ServiceRegistry(services=[])

        registry = ServiceRegistry.model_validate(data)
        self._log.debug("registry_loaded", count=len(registry.services))
        return registry

    def save(self, registry: ServiceRegistry) -> None:
        """Save the service registry to disk.

        Creates the config directory if it doesn't exist.

        Args:
            registry: ServiceRegistry to save.
        """
        self._ensure_config_dir()
        self._log.debug("saving_registry", path=str(self.config_path), count=len(registry.services))

        # Convert to dict, excluding None values for cleaner YAML
        data = registry.model_dump(exclude_none=True)

        with self.config_path.open("w") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

        self._log.info("registry_saved", path=str(self.config_path), count=len(registry.services))

    def add_service(self, entry: ServiceRegistryEntry) -> None:
        """Add a service to the registry.

        Args:
            entry: Service entry to add.

        Raises:
            ServiceAlreadyExistsError: If a service with the same name exists.
        """
        registry = self.load()

        if registry.get_service(entry.name) is not None:
            raise ServiceAlreadyExistsError(entry.name)

        registry.services.append(entry)
        self.save(registry)
        self._log.info("service_added", name=entry.name)

    def update_service(self, entry: ServiceRegistryEntry) -> None:
        """Update an existing service in the registry.

        Args:
            entry: Service entry with updated values.

        Raises:
            ServiceNotFoundError: If the service doesn't exist.
        """
        registry = self.load()

        for i, service in enumerate(registry.services):
            if service.name == entry.name:
                registry.services[i] = entry
                self.save(registry)
                self._log.info("service_updated", name=entry.name)
                return

        raise ServiceNotFoundError(entry.name)

    def remove_service(self, name: str) -> None:
        """Remove a service from the registry.

        Args:
            name: Name of the service to remove.

        Raises:
            ServiceNotFoundError: If the service doesn't exist.
        """
        registry = self.load()
        original_count = len(registry.services)

        registry.services = [s for s in registry.services if s.name != name]

        if len(registry.services) == original_count:
            raise ServiceNotFoundError(name)

        self.save(registry)
        self._log.info("service_removed", name=name)

    def get_service(self, name: str) -> ServiceRegistryEntry | None:
        """Get a service by name.

        Args:
            name: Service name to find.

        Returns:
            ServiceRegistryEntry if found, None otherwise.
        """
        registry = self.load()
        return registry.get_service(name)

    def import_from_file(self, file_path: Path) -> int:
        """Import services from a YAML file.

        Merges services from the file into the existing registry.
        Services with existing names are updated, new services are added.

        Args:
            file_path: Path to YAML file to import.

        Returns:
            Number of services imported/updated.
        """
        self._log.debug("importing_from_file", path=str(file_path))

        content = file_path.read_text()
        data = yaml.safe_load(content)
        imported = ServiceRegistry.model_validate(data)

        registry = self.load()
        count = 0

        for entry in imported.services:
            existing = registry.get_service(entry.name)
            if existing:
                # Update existing
                for i, s in enumerate(registry.services):
                    if s.name == entry.name:
                        registry.services[i] = entry
                        break
            else:
                # Add new
                registry.services.append(entry)
            count += 1

        self.save(registry)
        self._log.info("import_completed", count=count)
        return count

    def calculate_diff(
        self,
        service_manager: ServiceManager,
        service_names: list[str] | None = None,
    ) -> ServiceDeploySummary:
        """Calculate diff between registry and current Kong state.

        Args:
            service_manager: ServiceManager for Kong API calls.
            service_names: Optional list of specific services to check.
                          If None, checks all services in registry.

        Returns:
            ServiceDeploySummary with diffs for each service.
        """
        registry = self.load()
        diffs: list[ServiceDeployDiff] = []
        creates = updates = unchanged = 0

        services_to_check = registry.services
        if service_names:
            services_to_check = [s for s in registry.services if s.name in service_names]

        for entry in services_to_check:
            try:
                current_service = service_manager.get(entry.name)
                changes = self._compare_service(current_service, entry)

                if changes:
                    diffs.append(
                        ServiceDeployDiff(
                            service_name=entry.name,
                            operation="update",
                            current=current_service.model_dump(exclude_none=True),
                            desired=entry.to_kong_service_dict(),
                            changes=changes,
                        )
                    )
                    updates += 1
                else:
                    diffs.append(
                        ServiceDeployDiff(
                            service_name=entry.name,
                            operation="unchanged",
                        )
                    )
                    unchanged += 1

            except KongNotFoundError:
                diffs.append(
                    ServiceDeployDiff(
                        service_name=entry.name,
                        operation="create",
                        desired=entry.to_kong_service_dict(),
                    )
                )
                creates += 1

        return ServiceDeploySummary(
            total_services=len(services_to_check),
            creates=creates,
            updates=updates,
            unchanged=unchanged,
            diffs=diffs,
        )

    def _compare_service(
        self,
        current: Service,
        desired: ServiceRegistryEntry,
    ) -> dict[str, tuple[Any, Any]] | None:
        """Compare current service with desired state.

        Args:
            current: Current service state from Kong.
            desired: Desired service state from registry.

        Returns:
            Dictionary of field changes, or None if no changes.
        """
        changes: dict[str, tuple[Any, Any]] = {}
        current_dict = current.model_dump()
        desired_dict = desired.to_kong_service_dict()

        for field in self.COMPARE_FIELDS:
            curr_val = current_dict.get(field)
            des_val = desired_dict.get(field)

            # Only compare if desired specifies the field
            if field in desired_dict and curr_val != des_val:
                changes[field] = (curr_val, des_val)

        return changes if changes else None

    def deploy(
        self,
        service_manager: ServiceManager,
        openapi_sync_manager: OpenAPISyncManager | None = None,
        *,
        skip_routes: bool = False,
        service_names: list[str] | None = None,
    ) -> list[ServiceDeployResult]:
        """Deploy services from registry to Kong.

        Creates or updates services based on the calculated diff,
        and optionally syncs routes from OpenAPI specs.

        Args:
            service_manager: ServiceManager for Kong API calls.
            openapi_sync_manager: Optional manager for OpenAPI route sync.
            skip_routes: If True, skip OpenAPI route synchronization.
            service_names: Optional list of specific services to deploy.

        Returns:
            List of ServiceDeployResult for each service.
        """
        summary = self.calculate_diff(service_manager, service_names)
        registry = self.load()
        results: list[ServiceDeployResult] = []

        for diff in summary.diffs:
            entry = registry.get_service(diff.service_name)
            if entry is None:
                continue

            result = self._deploy_single_service(
                diff,
                entry,
                service_manager,
                openapi_sync_manager,
                skip_routes=skip_routes,
            )
            results.append(result)

        return results

    def _deploy_single_service(
        self,
        diff: ServiceDeployDiff,
        entry: ServiceRegistryEntry,
        service_manager: ServiceManager,
        openapi_sync_manager: OpenAPISyncManager | None,
        *,
        skip_routes: bool,
    ) -> ServiceDeployResult:
        """Deploy a single service to Kong.

        Args:
            diff: The diff for this service.
            entry: The registry entry for this service.
            service_manager: ServiceManager for Kong API calls.
            openapi_sync_manager: Optional manager for OpenAPI route sync.
            skip_routes: If True, skip OpenAPI route synchronization.

        Returns:
            ServiceDeployResult for this service.
        """
        service_status: str = "unchanged"
        routes_synced = 0
        routes_status: str = "no_spec"
        error: str | None = None

        # Handle service creation/update
        if diff.operation == "unchanged":
            service_status = "unchanged"
        elif diff.operation == "create":
            try:
                service = Service(**entry.to_kong_service_dict())
                service_manager.create(service)
                service_status = "created"
                self._log.info("service_created", name=entry.name)
            except Exception as e:
                self._log.error("service_create_failed", name=entry.name, error=str(e))
                return ServiceDeployResult(
                    service_name=entry.name,
                    service_status="failed",
                    error=str(e),
                )
        elif diff.operation == "update":
            try:
                service = Service(**entry.to_kong_service_dict())
                service_manager.update(entry.name, service)
                service_status = "updated"
                self._log.info("service_updated", name=entry.name)
            except Exception as e:
                self._log.error("service_update_failed", name=entry.name, error=str(e))
                return ServiceDeployResult(
                    service_name=entry.name,
                    service_status="failed",
                    error=str(e),
                )

        # Handle OpenAPI route sync
        if skip_routes:
            routes_status = "skipped"
        elif not entry.has_openapi_spec:
            routes_status = "no_spec"
        elif openapi_sync_manager is not None:
            try:
                routes_synced, routes_status = self._sync_routes(entry, openapi_sync_manager)
            except Exception as e:
                self._log.error("route_sync_failed", name=entry.name, error=str(e))
                routes_status = "failed"
                error = f"Route sync failed: {e}"

        return ServiceDeployResult(
            service_name=entry.name,
            service_status=service_status,  # type: ignore[arg-type]
            routes_synced=routes_synced,
            routes_status=routes_status,  # type: ignore[arg-type]
            error=error,
        )

    def _sync_routes(
        self,
        entry: ServiceRegistryEntry,
        openapi_sync_manager: OpenAPISyncManager,
    ) -> tuple[int, str]:
        """Sync routes from OpenAPI spec for a service.

        Args:
            entry: Service registry entry with OpenAPI spec path.
            openapi_sync_manager: Manager for OpenAPI route sync.

        Returns:
            Tuple of (routes_synced_count, status_string).
        """
        spec_path = entry.openapi_spec_path
        if spec_path is None or not spec_path.exists():
            self._log.warning(
                "openapi_spec_not_found",
                name=entry.name,
                path=str(entry.openapi_spec),
            )
            return 0, "failed"

        # Parse and sync
        spec = openapi_sync_manager.parse_openapi(spec_path)
        mappings = openapi_sync_manager.generate_route_mappings(
            spec,
            entry.name,
            path_prefix=entry.path_prefix,
            strip_path=entry.strip_path,
        )

        # Calculate diff and apply
        sync_result = openapi_sync_manager.calculate_diff(entry.name, mappings)

        if not sync_result.has_changes:
            return 0, "synced"

        apply_result = openapi_sync_manager.apply_sync(sync_result, force=True)

        routes_count = len(apply_result.succeeded)
        self._log.info(
            "routes_synced",
            name=entry.name,
            count=routes_count,
        )

        return routes_count, "synced"
