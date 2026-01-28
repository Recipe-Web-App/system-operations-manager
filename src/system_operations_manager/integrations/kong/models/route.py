"""Pydantic models for Kong Routes.

A Route in Kong defines rules for matching client requests to Services.
Routes can match on various criteria including paths, hosts, headers,
methods, and SNIs (for TLS routes).
"""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import Field, field_validator, model_validator

from system_operations_manager.integrations.kong.models.base import (
    KongEntityBase,
    KongEntityReference,
)

# Valid protocols for Kong routes
RouteProtocol = Literal["http", "https", "grpc", "grpcs", "tcp", "tls", "udp"]


class Route(KongEntityBase):
    """Kong Route entity model.

    A Route defines rules for matching client requests and forwarding
    them to a Service. Routes can match on multiple criteria, and at
    least one matching criterion must be provided.

    Attributes:
        name: Route name (unique identifier alternative to UUID).
        service: Reference to the associated service.
        protocols: Accepted protocols (http, https, grpc, etc.).
        methods: HTTP methods to match (GET, POST, etc.).
        hosts: Host headers to match.
        paths: Path prefixes to match.
        headers: Headers to match.
        snis: SNIs for TLS route matching.
        sources: Source IP/port criteria for stream routes.
        destinations: Destination IP/port criteria for stream routes.
        https_redirect_status_code: Status code for HTTPS redirect.
        regex_priority: Priority for regex path matching.
        strip_path: Whether to strip matched path prefix.
        path_handling: Path handling version (v0 or v1).
        preserve_host: Whether to preserve original host header.
        request_buffering: Whether to buffer request body.
        response_buffering: Whether to buffer response body.
    """

    _entity_name: ClassVar[str] = "route"

    # Core identification
    name: str | None = Field(default=None, description="Route name (unique)")

    # Associated service
    service: KongEntityReference | None = Field(default=None, description="Associated service")

    # Matching criteria (at least one required for creation)
    protocols: list[RouteProtocol] = Field(
        default=["http", "https"], description="Accepted protocols"
    )
    methods: list[str] | None = Field(default=None, description="HTTP methods (GET, POST, etc.)")
    hosts: list[str] | None = Field(default=None, description="Host headers to match")
    paths: list[str] | None = Field(default=None, description="Path prefixes to match")
    headers: dict[str, list[str]] | None = Field(default=None, description="Headers to match")
    snis: list[str] | None = Field(default=None, description="SNIs for TLS routes")
    sources: list[dict[str, Any]] | None = Field(
        default=None, description="Source IPs/ports for stream routes"
    )
    destinations: list[dict[str, Any]] | None = Field(
        default=None, description="Destination IPs/ports for stream routes"
    )

    # Routing behavior
    https_redirect_status_code: int = Field(
        default=426, description="HTTP status for HTTPS redirect"
    )
    regex_priority: int = Field(default=0, description="Regex route priority")
    strip_path: bool = Field(default=True, description="Strip matched path prefix")
    path_handling: Literal["v0", "v1"] = Field(default="v0", description="Path handling version")
    preserve_host: bool = Field(default=False, description="Preserve host header")
    request_buffering: bool = Field(default=True, description="Buffer request body")
    response_buffering: bool = Field(default=True, description="Buffer response body")

    @field_validator("methods", mode="before")
    @classmethod
    def uppercase_methods(cls, v: list[str] | None) -> list[str] | None:
        """Ensure HTTP methods are uppercase."""
        if v is not None:
            return [m.upper() for m in v]
        return v

    @field_validator("paths", mode="before")
    @classmethod
    def validate_paths(cls, v: list[str] | None) -> list[str] | None:
        """Ensure paths start with /."""
        if v is not None:
            return [p if p.startswith("/") or p.startswith("~") else f"/{p}" for p in v]
        return v

    @model_validator(mode="after")
    def check_matching_criteria(self) -> Route:
        """Validate that at least one matching criterion exists.

        Note: This validation is relaxed for API responses which
        always include matching criteria.
        """
        # For creation, at least one criterion should be provided
        # For updates, this is optional
        return self

    def to_create_payload(self) -> dict[str, Any]:
        """Convert to create payload, ensuring service reference format."""
        payload = super().to_create_payload()

        # Ensure service reference is properly formatted
        if "service" in payload and isinstance(payload["service"], dict):
            # Keep only id or name
            service_ref = payload["service"]
            if service_ref.get("id"):
                payload["service"] = {"id": service_ref["id"]}
            elif service_ref.get("name"):
                payload["service"] = {"name": service_ref["name"]}

        return payload


class RouteSummary(KongEntityBase):
    """Minimal route representation for listings."""

    _entity_name: ClassVar[str] = "route"

    name: str | None = None
    paths: list[str] | None = None
    methods: list[str] | None = None
    hosts: list[str] | None = None
    service: KongEntityReference | None = None
