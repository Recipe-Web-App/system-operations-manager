"""Pydantic models for Kong Service Registry configuration.

The service registry is a local configuration file that defines services
to be deployed to Kong. It supports batch deployment and optional OpenAPI
route synchronization.

Config location: ~/.config/ops/kong/services.yaml
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Valid protocols for Kong services
ServiceProtocol = Literal["http", "https", "grpc", "grpcs", "tcp", "tls"]


class ServiceRegistryEntry(BaseModel):
    """Single service definition in the registry.

    Defines all the configuration needed to create a Kong service,
    plus optional OpenAPI spec path for route synchronization.

    Attributes:
        name: Service name (unique identifier in Kong).
        host: Upstream host or DNS name.
        port: Upstream port (1-65535).
        protocol: Protocol for upstream connection.
        path: Path prefix to prepend to requests.
        tags: Tags for filtering and organization.
        retries: Number of retries on connection failure.
        connect_timeout: Connection timeout in milliseconds.
        write_timeout: Write timeout in milliseconds.
        read_timeout: Read timeout in milliseconds.
        enabled: Whether the service is active.
        openapi_spec: Path to OpenAPI specification file.
        path_prefix: Prefix to add to all route paths.
        strip_path: Whether to strip matched path when proxying.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_default=True,
    )

    # Required fields
    name: str = Field(description="Service name (unique identifier)")
    host: str = Field(description="Upstream host or DNS name")

    # Connection settings with sensible defaults
    port: int = Field(default=80, ge=1, le=65535, description="Upstream port")
    protocol: ServiceProtocol = Field(default="http", description="Protocol")
    path: str | None = Field(default=None, description="Path prefix for requests")

    # Optional Kong service settings
    tags: list[str] | None = Field(default=None, description="Tags for filtering")
    retries: int | None = Field(default=None, ge=0, description="Number of retries")
    connect_timeout: int | None = Field(default=None, ge=0, description="Connection timeout (ms)")
    write_timeout: int | None = Field(default=None, ge=0, description="Write timeout (ms)")
    read_timeout: int | None = Field(default=None, ge=0, description="Read timeout (ms)")
    enabled: bool = Field(default=True, description="Whether service is active")

    # OpenAPI integration (optional)
    openapi_spec: str | None = Field(
        default=None,
        description="Path to OpenAPI specification file for route sync",
    )
    path_prefix: str | None = Field(
        default=None,
        description="Prefix to add to all route paths during sync",
    )
    strip_path: bool = Field(
        default=False,
        description="Strip matched path when proxying",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure name is not empty and contains valid characters."""
        if not v or not v.strip():
            raise ValueError("Service name cannot be empty")
        # Kong service names must be alphanumeric with - _ . ~
        import re

        if not re.match(r"^[a-zA-Z0-9._~-]+$", v):
            raise ValueError(
                "Service name must contain only alphanumeric characters, "
                "hyphens, underscores, periods, or tildes"
            )
        return v

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        """Ensure host is not empty."""
        if not v or not v.strip():
            raise ValueError("Host cannot be empty")
        return v

    @field_validator("protocol", mode="before")
    @classmethod
    def lowercase_protocol(cls, v: str | None) -> str | None:
        """Ensure protocol is lowercase."""
        if v is not None:
            return v.lower()
        return v

    @field_validator("path", "path_prefix")
    @classmethod
    def validate_path(cls, v: str | None) -> str | None:
        """Ensure path starts with / if provided."""
        if v is not None and v and not v.startswith("/"):
            return f"/{v}"
        return v

    @field_validator("openapi_spec")
    @classmethod
    def expand_openapi_path(cls, v: str | None) -> str | None:
        """Expand ~ in OpenAPI spec path."""
        if v is not None:
            return str(Path(v).expanduser())
        return v

    def to_kong_service_dict(self) -> dict[str, Any]:
        """Convert to dictionary suitable for Kong service creation.

        Returns:
            Dictionary with Kong service fields only (excludes OpenAPI settings).
        """
        kong_fields = {
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "protocol": self.protocol,
            "enabled": self.enabled,
        }
        # Add optional fields if set
        if self.path is not None:
            kong_fields["path"] = self.path
        if self.tags is not None:
            kong_fields["tags"] = self.tags
        if self.retries is not None:
            kong_fields["retries"] = self.retries
        if self.connect_timeout is not None:
            kong_fields["connect_timeout"] = self.connect_timeout
        if self.write_timeout is not None:
            kong_fields["write_timeout"] = self.write_timeout
        if self.read_timeout is not None:
            kong_fields["read_timeout"] = self.read_timeout
        return kong_fields

    @property
    def has_openapi_spec(self) -> bool:
        """Check if this service has an OpenAPI spec configured."""
        return self.openapi_spec is not None

    @property
    def openapi_spec_path(self) -> Path | None:
        """Get the OpenAPI spec as a Path object."""
        if self.openapi_spec is not None:
            return Path(self.openapi_spec)
        return None


class ServiceRegistry(BaseModel):
    """Complete service registry configuration.

    Contains a list of service definitions to be deployed to Kong.
    Validates that all service names are unique.

    Attributes:
        services: List of service definitions.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    services: list[ServiceRegistryEntry] = Field(
        default_factory=list,
        description="List of service definitions",
    )

    @field_validator("services")
    @classmethod
    def validate_unique_names(cls, v: list[ServiceRegistryEntry]) -> list[ServiceRegistryEntry]:
        """Ensure all service names are unique."""
        names = [s.name for s in v]
        if len(names) != len(set(names)):
            duplicates = sorted({n for n in names if names.count(n) > 1})
            raise ValueError(f"Duplicate service names: {', '.join(duplicates)}")
        return v

    def get_service(self, name: str) -> ServiceRegistryEntry | None:
        """Get a service by name.

        Args:
            name: Service name to find.

        Returns:
            ServiceRegistryEntry if found, None otherwise.
        """
        for service in self.services:
            if service.name == name:
                return service
        return None

    def __len__(self) -> int:
        """Return number of services in registry."""
        return len(self.services)

    def __iter__(self) -> Iterator[ServiceRegistryEntry]:  # type: ignore[override]
        """Iterate over services."""
        return iter(self.services)


class ServiceDeployDiff(BaseModel):
    """Represents the difference for a single service.

    Used to show what would change when deploying a service.

    Attributes:
        service_name: Name of the service.
        operation: Type of operation (create, update, unchanged).
        current: Current service state in Kong (if exists).
        desired: Desired service state from registry.
        changes: Field-level changes for updates.
    """

    service_name: str
    operation: Literal["create", "update", "unchanged"]
    current: dict[str, Any] | None = None
    desired: dict[str, Any] | None = None
    changes: dict[str, tuple[Any, Any]] | None = None  # field: (old_value, new_value)


class ServiceDeploySummary(BaseModel):
    """Summary of a batch deploy operation.

    Aggregates all the diffs for preview before applying.

    Attributes:
        total_services: Total number of services in registry.
        creates: Number of services to create.
        updates: Number of services to update.
        unchanged: Number of services already in sync.
        diffs: Individual diff for each service.
    """

    total_services: int = 0
    creates: int = 0
    updates: int = 0
    unchanged: int = 0
    diffs: list[ServiceDeployDiff] = Field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes to apply."""
        return self.creates > 0 or self.updates > 0


class ServiceDeployResult(BaseModel):
    """Result of deploying a single service.

    Returned after applying changes to Kong.

    Attributes:
        service_name: Name of the service.
        service_status: Result of service creation/update.
        routes_synced: Number of routes synced from OpenAPI.
        routes_status: Result of route synchronization.
        error: Error message if operation failed.
    """

    service_name: str
    service_status: Literal["created", "updated", "unchanged", "failed"]
    routes_synced: int = 0
    routes_status: Literal["synced", "skipped", "failed", "no_spec"] = "no_spec"
    error: str | None = None

    @property
    def success(self) -> bool:
        """Check if the deployment was successful."""
        return self.service_status in ("created", "updated", "unchanged")


class RegistryNotFoundError(Exception):
    """Raised when the registry file does not exist."""

    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__(f"Registry file not found: {path}")


class ServiceNotFoundError(Exception):
    """Raised when a service is not found in the registry."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Service not found in registry: {name}")


class ServiceAlreadyExistsError(Exception):
    """Raised when trying to add a service that already exists."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Service already exists in registry: {name}")
