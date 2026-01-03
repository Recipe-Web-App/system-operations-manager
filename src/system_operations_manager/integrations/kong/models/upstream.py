"""Pydantic models for Kong Upstreams and Targets.

Upstreams in Kong represent virtual hostnames for load balancing across
multiple target backends. Targets are the actual backend servers that
receive traffic through an upstream.
"""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import Field

from system_operations_manager.integrations.kong.models.base import KongEntityBase

# Load balancing algorithms
LoadBalancingAlgorithm = Literal[
    "round-robin",
    "consistent-hashing",
    "least-connections",
    "latency",
]

# Hash input sources
HashOnSource = Literal[
    "none",
    "consumer",
    "ip",
    "header",
    "cookie",
    "path",
    "query_arg",
    "uri_capture",
]


class HealthCheckConfig(KongEntityBase):
    """Health check configuration for upstreams.

    Configures active and passive health checking for upstream targets.
    """

    model_config = {"extra": "allow"}  # Health checks have many fields

    active: dict[str, Any] | None = Field(
        default=None, description="Active health check configuration"
    )
    passive: dict[str, Any] | None = Field(
        default=None, description="Passive health check configuration"
    )
    threshold: int | None = Field(default=None, description="Health threshold percentage")


class Upstream(KongEntityBase):
    """Kong Upstream entity model.

    An Upstream represents a virtual hostname for load balancing across
    multiple backend targets. Upstreams support various load balancing
    algorithms and health checking configurations.

    Attributes:
        name: Upstream name (virtual hostname).
        algorithm: Load balancing algorithm.
        slots: Number of slots in the hash ring (for consistent-hashing).
        hash_on: Input for consistent-hashing.
        hash_fallback: Fallback hash input.
        hash_on_header: Header name for header-based hashing.
        hash_fallback_header: Fallback header name.
        hash_on_cookie: Cookie name for cookie-based hashing.
        hash_on_cookie_path: Cookie path.
        hash_on_query_arg: Query argument for hashing.
        hash_on_uri_capture: URI capture group for hashing.
        healthchecks: Health check configuration.
        host_header: Override host header sent to targets.
        client_certificate: Client certificate for mTLS to targets.
        use_srv_name: Use SRV record name for TLS SNI.
    """

    _entity_name: ClassVar[str] = "upstream"

    # Core identification
    name: str = Field(description="Upstream name (virtual hostname)")

    # Load balancing
    algorithm: LoadBalancingAlgorithm = Field(
        default="round-robin", description="Load balancing algorithm"
    )
    slots: int = Field(default=10000, ge=10, le=65536, description="Hash ring slots")

    # Hashing configuration
    hash_on: HashOnSource = Field(default="none", description="Hash input for consistent-hashing")
    hash_fallback: HashOnSource | None = Field(default=None, description="Fallback hash input")
    hash_on_header: str | None = Field(
        default=None, description="Header name for header-based hashing"
    )
    hash_fallback_header: str | None = Field(default=None, description="Fallback header name")
    hash_on_cookie: str | None = Field(
        default=None, description="Cookie name for cookie-based hashing"
    )
    hash_on_cookie_path: str = Field(default="/", description="Cookie path")
    hash_on_query_arg: str | None = Field(default=None, description="Query argument for hashing")
    hash_on_uri_capture: str | None = Field(
        default=None, description="URI capture group for hashing"
    )

    # Health checks
    healthchecks: HealthCheckConfig | dict[str, Any] | None = Field(
        default=None, description="Health check configuration"
    )

    # Connection behavior
    host_header: str | None = Field(
        default=None, description="Override host header sent to targets"
    )
    client_certificate: dict[str, str] | None = Field(
        default=None, description="Client certificate for mTLS to targets"
    )
    use_srv_name: bool = Field(default=False, description="Use SRV record name for TLS SNI")


class Target(KongEntityBase):
    """Kong Target entity model.

    A Target represents a backend server in an upstream's load balancing
    pool. Targets have a weight that determines their share of traffic.

    Attributes:
        target: Target address (host:port or just host).
        weight: Load balancing weight (0-65535). Weight 0 disables target.
        upstream: Reference to parent upstream.
    """

    _entity_name: ClassVar[str] = "target"

    target: str = Field(description="Target address (host:port or host)")
    weight: int = Field(default=100, ge=0, le=65535, description="Load balancing weight")
    upstream: dict[str, str] | None = Field(default=None, description="Parent upstream reference")


class TargetHealth(KongEntityBase):
    """Health status for an individual target.

    Attributes:
        address: Target address.
        health: Health status (HEALTHY, UNHEALTHY, DNS_ERROR, HEALTHCHECKS_OFF).
        weight: Current weight.
    """

    _entity_name: ClassVar[str] = "target_health"

    address: str | None = Field(default=None, description="Target address")
    health: str | None = Field(default=None, description="Health status")
    weight: int | None = Field(default=None, description="Target weight")


class UpstreamHealth(KongEntityBase):
    """Upstream health status.

    Contains overall upstream health and individual target health data.

    Attributes:
        id: Upstream ID.
        health: Overall health status (HEALTHY, UNHEALTHY, HEALTHCHECKS_OFF).
        data: Detailed health information including target states.
    """

    _entity_name: ClassVar[str] = "upstream_health"

    health: Literal["HEALTHY", "UNHEALTHY", "HEALTHCHECKS_OFF"] | str | None = Field(
        default=None, description="Overall health status"
    )
    data: dict[str, Any] | None = Field(default=None, description="Detailed health data")
