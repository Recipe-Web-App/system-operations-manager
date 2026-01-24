"""Certificate-related models for Kong entities.

This module provides models for TLS certificates, SNIs (Server Name Indications),
and CA certificates used for SSL termination and mTLS in Kong.
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import Field

from system_operations_manager.integrations.kong.models.base import (
    KongEntityBase,
    KongEntityReference,
)


class Certificate(KongEntityBase):
    """TLS certificate for SSL termination.

    Certificates are used to enable HTTPS on Kong routes and services.
    They contain a public certificate and private key pair.

    Attributes:
        cert: PEM-encoded public certificate.
        key: PEM-encoded private key.
        cert_alt: Alternative certificate (e.g., ECDSA alongside RSA).
        key_alt: Alternative private key.
        snis: List of SNI hostnames associated with this certificate.

    Example:
        >>> cert = Certificate(
        ...     cert="-----BEGIN CERTIFICATE-----\\n...",
        ...     key="-----BEGIN PRIVATE KEY-----\\n...",  # pragma: allowlist secret
        ...     tags=["production"]
        ... )
    """

    _entity_name: ClassVar[str] = "certificate"

    cert: str = Field(..., description="PEM-encoded public certificate")
    key: str = Field(..., description="PEM-encoded private key")
    cert_alt: str | None = Field(
        default=None,
        description="Alternative certificate (e.g., ECDSA for dual-cert setup)",
    )
    key_alt: str | None = Field(
        default=None,
        description="Alternative private key for cert_alt",
    )
    snis: list[str] | None = Field(
        default=None,
        description="SNI hostnames associated with this certificate",
    )

    def to_create_payload(self) -> dict[str, Any]:
        """Convert model to payload for create operations.

        Excludes snis field as Kong manages them separately.
        """
        exclude_fields = {"id", "created_at", "updated_at", "snis"}
        return {k: v for k, v in self.model_dump(exclude=exclude_fields).items() if v is not None}


class CertificateSummary(KongEntityBase):
    """Lightweight certificate representation for listings.

    Used when full certificate content is not needed, such as in
    list responses or references from other entities.

    Attributes:
        cert: PEM-encoded certificate (truncated in displays).
        snis: List of SNI hostnames.
    """

    _entity_name: ClassVar[str] = "certificate"

    cert: str | None = Field(default=None, description="PEM-encoded certificate")
    snis: list[str] | None = Field(default=None, description="Associated SNI hostnames")


class SNI(KongEntityBase):
    """Server Name Indication mapping to a certificate.

    SNIs (Server Name Indications) map domain names to TLS certificates,
    allowing Kong to serve different certificates for different hostnames.

    Attributes:
        name: The SNI hostname (e.g., "api.example.com").
        certificate: Reference to the associated certificate.

    Example:
        >>> sni = SNI(
        ...     name="api.example.com",
        ...     certificate=KongEntityReference.from_id("cert-uuid-here"),
        ... )
    """

    _entity_name: ClassVar[str] = "sni"

    name: str = Field(..., description="SNI hostname")
    certificate: KongEntityReference = Field(
        ..., description="Reference to the associated certificate"
    )

    @property
    def identifier(self) -> str:
        """Human-readable identifier for this SNI."""
        return self.name


class CACertificate(KongEntityBase):
    """Certificate Authority certificate for mTLS.

    CA certificates are used to verify client certificates in mutual TLS
    (mTLS) authentication scenarios.

    Attributes:
        cert: PEM-encoded CA certificate.
        cert_digest: SHA256 digest of the certificate (computed by Kong).

    Example:
        >>> ca_cert = CACertificate(
        ...     cert="-----BEGIN CERTIFICATE-----\\n...",
        ...     tags=["mtls", "production"]
        ... )
    """

    _entity_name: ClassVar[str] = "ca_certificate"

    cert: str = Field(..., description="PEM-encoded CA certificate")
    cert_digest: str | None = Field(
        default=None,
        description="SHA256 digest of the certificate (computed by Kong)",
    )

    @property
    def identifier(self) -> str:
        """Human-readable identifier for this CA certificate.

        Uses cert_digest if available, otherwise falls back to ID.
        """
        if self.cert_digest:
            return self.cert_digest[:16] + "..."
        return self.id or "unknown"
