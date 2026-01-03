"""Pydantic models for Kong Plugins.

Plugins in Kong add functionality to Services, Routes, Consumers, or globally.
They can implement authentication, rate limiting, transformations, logging,
and many other features.
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import Field

from system_operations_manager.integrations.kong.models.base import (
    KongEntityBase,
    KongEntityReference,
)


class KongPluginEntity(KongEntityBase):
    """Kong Plugin entity model.

    A Plugin adds functionality to Kong and can be scoped to:
    - Global (no service, route, or consumer)
    - Service-level
    - Route-level
    - Consumer-level
    - Or combinations thereof

    Note: Named KongPluginEntity to avoid confusion with the CLI Plugin class.

    Attributes:
        name: Plugin name (e.g., 'rate-limiting', 'key-auth').
        service: Service scope (optional).
        route: Route scope (optional).
        consumer: Consumer scope (optional).
        config: Plugin-specific configuration.
        protocols: Protocols to apply plugin on.
        enabled: Whether plugin is active.
        ordering: Plugin execution ordering (Kong 3.0+).
        instance_name: Unique instance name for same-type plugins.
    """

    _entity_name: ClassVar[str] = "plugin"

    # Plugin identification
    name: str = Field(description="Plugin name (e.g., 'rate-limiting', 'key-auth')")
    instance_name: str | None = Field(
        default=None, description="Unique instance name for same-type plugins"
    )

    # Scope (all optional = global plugin)
    service: KongEntityReference | None = Field(default=None, description="Service scope")
    route: KongEntityReference | None = Field(default=None, description="Route scope")
    consumer: KongEntityReference | None = Field(default=None, description="Consumer scope")

    # Configuration
    config: dict[str, Any] = Field(default_factory=dict, description="Plugin configuration")
    protocols: list[str] = Field(
        default_factory=lambda: ["grpc", "grpcs", "http", "https"],
        description="Protocols to apply plugin on",
    )
    enabled: bool = Field(default=True, description="Whether plugin is active")

    # Ordering (Kong 3.0+)
    ordering: dict[str, Any] | None = Field(default=None, description="Plugin execution ordering")

    def to_create_payload(self) -> dict[str, Any]:
        """Convert to create payload, ensuring proper scope references."""
        payload = super().to_create_payload()

        # Ensure scope references are properly formatted
        for scope in ("service", "route", "consumer"):
            if scope in payload and isinstance(payload[scope], dict):
                ref = payload[scope]
                if ref.get("id"):
                    payload[scope] = {"id": ref["id"]}
                elif ref.get("name"):
                    payload[scope] = {"name": ref["name"]}

        return payload


class AvailablePlugin(KongEntityBase):
    """Information about an available plugin type.

    Represents a plugin that is available for use in the Kong cluster.

    Attributes:
        name: Plugin name.
        version: Plugin version.
        priority: Execution priority.
        phases: Phases where plugin runs (e.g., 'access', 'response').
    """

    _entity_name: ClassVar[str] = "available_plugin"

    name: str = Field(description="Plugin name")
    version: str | None = Field(default=None, description="Plugin version")
    priority: int | None = Field(default=None, description="Execution priority")
    phases: list[str] | None = Field(default=None, description="Execution phases")


class PluginSchema(KongEntityBase):
    """Plugin configuration schema.

    Contains the JSON schema for a plugin's configuration options.

    Attributes:
        name: Plugin name.
        fields: Schema field definitions.
    """

    _entity_name: ClassVar[str] = "plugin_schema"

    name: str | None = Field(default=None, description="Plugin name")
    fields: list[dict[str, Any]] | None = Field(default=None, description="Schema fields")
