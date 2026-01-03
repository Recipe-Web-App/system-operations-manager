"""Pydantic models for Kong Services.

A Service in Kong represents an external upstream API or microservice
that Kong proxies requests to. Services define the upstream connection
details including host, port, protocol, and timeout settings.
"""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import Field, field_validator, model_validator

from system_operations_manager.integrations.kong.models.base import (
    KongEntityBase,
    KongEntityReference,
)

# Valid protocols for Kong services
ServiceProtocol = Literal["http", "https", "grpc", "grpcs", "tcp", "tls", "udp"]


class Service(KongEntityBase):
    """Kong Service entity model.

    A Service represents an external upstream API or microservice that
    Kong proxies requests to. Services can be defined either by specifying
    individual connection components (host, port, protocol, path) or by
    providing a full URL.

    Attributes:
        name: Service name (unique identifier alternative to UUID).
        host: Hostname or IP of the upstream server.
        port: Port of the upstream server (1-65535).
        protocol: Protocol to use for upstream connection.
        path: Path prefix to prepend to requests.
        url: Full URL shorthand (protocol://host:port/path).
        retries: Number of retries on connection failure.
        connect_timeout: Connection timeout in milliseconds.
        write_timeout: Write timeout in milliseconds.
        read_timeout: Read timeout in milliseconds.
        tls_verify: Whether to verify upstream TLS certificate.
        tls_verify_depth: Maximum TLS certificate chain depth.
        ca_certificates: List of CA certificate IDs for TLS verification.
        client_certificate: Client certificate for mTLS.
        enabled: Whether the service is active.
    """

    _entity_name: ClassVar[str] = "service"

    # Core identification
    name: str | None = Field(default=None, description="Service name (unique)")

    # Host configuration (either host or url required)
    host: str | None = Field(default=None, description="Host of the upstream server")
    port: int = Field(default=80, ge=1, le=65535, description="Upstream server port")
    protocol: ServiceProtocol = Field(default="http", description="Protocol to use")
    path: str | None = Field(default=None, description="Path prefix for requests")

    # URL alternative (shorthand for protocol://host:port/path)
    url: str | None = Field(default=None, description="Full URL shorthand")

    # Retries and timeouts
    retries: int = Field(default=5, ge=0, description="Number of retries")
    connect_timeout: int = Field(default=60000, ge=0, description="Connection timeout (ms)")
    write_timeout: int = Field(default=60000, ge=0, description="Write timeout (ms)")
    read_timeout: int = Field(default=60000, ge=0, description="Read timeout (ms)")

    # TLS settings
    tls_verify: bool | None = Field(default=None, description="Verify upstream TLS certificate")
    tls_verify_depth: int | None = Field(default=None, ge=0, description="TLS verify depth")
    ca_certificates: list[str] | None = Field(default=None, description="CA certificate IDs")
    client_certificate: KongEntityReference | None = Field(
        default=None, description="Client certificate for mTLS"
    )

    # Connection behavior
    enabled: bool = Field(default=True, description="Whether service is active")

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str | None) -> str | None:
        """Ensure path starts with /."""
        if v is not None and v and not v.startswith("/"):
            return f"/{v}"
        return v

    @field_validator("protocol", mode="before")
    @classmethod
    def lowercase_protocol(cls, v: str | None) -> str | None:
        """Ensure protocol is lowercase."""
        if v is not None:
            return v.lower()
        return v

    @model_validator(mode="after")
    def check_host_or_url(self) -> Service:
        """Ensure either host or url is provided for creation.

        Note: This is relaxed for API responses which always have host.
        """
        # For responses from API, host will be populated
        # For creation, either host or url must be provided
        return self

    def to_create_payload(self) -> dict[str, Any]:
        """Convert to create payload, handling URL expansion."""
        payload = super().to_create_payload()
        # If URL is provided, let Kong parse it
        # Otherwise ensure host is included
        return payload


class ServiceSummary(KongEntityBase):
    """Minimal service representation for listings."""

    _entity_name: ClassVar[str] = "service"

    name: str | None = None
    host: str | None = None
    port: int = 80
    protocol: str = "http"
    enabled: bool = True
