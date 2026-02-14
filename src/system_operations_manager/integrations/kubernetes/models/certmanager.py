"""Cert-manager resource display models.

Cert-manager CRDs are accessed via ``CustomObjectsApi`` which returns raw
``dict`` objects rather than typed SDK classes.  The ``from_k8s_object``
classmethods therefore use ``dict.get()`` instead of ``getattr()``.
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from system_operations_manager.integrations.kubernetes.models.base import (
    K8sEntityBase,
)

# Known issuer spec keys for detecting issuer type
_ISSUER_TYPE_KEYS = ("acme", "ca", "vault", "selfSigned", "venafi")


class CertManagerCondition(BaseModel):
    """Cert-manager status condition from ``.status.conditions[]``."""

    model_config = ConfigDict(extra="ignore")

    type: str = Field(default="", description="Condition type (Ready, Issuing, etc.)")
    status: str = Field(default="Unknown", description="Condition status (True, False, Unknown)")
    reason: str = Field(default="", description="Machine-readable reason")
    message: str | None = Field(default=None, description="Human-readable message")
    last_transition_time: str | None = Field(default=None, description="Last transition timestamp")

    @classmethod
    def from_k8s_object(cls, obj: dict[str, Any]) -> CertManagerCondition:
        """Create from a condition dict."""
        return cls(
            type=obj.get("type", ""),
            status=obj.get("status", "Unknown"),
            reason=obj.get("reason", ""),
            message=obj.get("message"),
            last_transition_time=obj.get("lastTransitionTime"),
        )


def _is_ready(conditions: list[CertManagerCondition]) -> bool:
    """Determine readiness from a list of cert-manager conditions."""
    for c in conditions:
        if c.type == "Ready":
            return c.status == "True"
    return False


def _parse_conditions(status: dict[str, Any]) -> list[CertManagerCondition]:
    """Parse ``.status.conditions`` into a list of CertManagerCondition."""
    raw: list[dict[str, Any]] = status.get("conditions", [])
    return [CertManagerCondition.from_k8s_object(c) for c in raw]


def _detect_issuer_type(spec: dict[str, Any]) -> str:
    """Detect issuer type from the spec dict."""
    for key in _ISSUER_TYPE_KEYS:
        if key in spec:
            return key
    return "unknown"


# =============================================================================
# Certificate
# =============================================================================


class CertificateSummary(K8sEntityBase):
    """Cert-manager Certificate display model."""

    _entity_name: ClassVar[str] = "certificate"

    secret_name: str = Field(default="", description="Target Secret name for the certificate")
    issuer_name: str = Field(default="", description="Issuer reference name")
    issuer_kind: str = Field(default="Issuer", description="Issuer kind (Issuer or ClusterIssuer)")
    issuer_group: str = Field(default="cert-manager.io", description="Issuer API group")
    dns_names: list[str] = Field(default_factory=list, description="Subject Alternative Names")
    common_name: str | None = Field(default=None, description="Certificate Common Name")
    duration: str | None = Field(default=None, description="Certificate validity duration")
    renew_before: str | None = Field(default=None, description="Renewal window before expiry")
    ready: bool = Field(default=False, description="Whether the certificate is ready")
    not_after: str | None = Field(default=None, description="Certificate expiration timestamp")
    not_before: str | None = Field(default=None, description="Certificate valid-from timestamp")
    renewal_time: str | None = Field(default=None, description="Next renewal time")
    revision: int | None = Field(default=None, description="Current certificate revision")
    conditions: list[CertManagerCondition] = Field(
        default_factory=list, description="Status conditions"
    )

    @classmethod
    def from_k8s_object(cls, obj: dict[str, Any]) -> CertificateSummary:
        """Create from a cert-manager Certificate CRD dict."""
        metadata: dict[str, Any] = obj.get("metadata", {})
        spec: dict[str, Any] = obj.get("spec", {})
        status: dict[str, Any] = obj.get("status", {})

        issuer_ref: dict[str, Any] = spec.get("issuerRef", {})
        conditions = _parse_conditions(status)

        return cls(
            name=metadata.get("name", ""),
            namespace=metadata.get("namespace"),
            uid=metadata.get("uid"),
            creation_timestamp=metadata.get("creationTimestamp"),
            labels=metadata.get("labels") or None,
            annotations=metadata.get("annotations") or None,
            secret_name=spec.get("secretName", ""),
            issuer_name=issuer_ref.get("name", ""),
            issuer_kind=issuer_ref.get("kind", "Issuer"),
            issuer_group=issuer_ref.get("group", "cert-manager.io"),
            dns_names=spec.get("dnsNames", []),
            common_name=spec.get("commonName"),
            duration=spec.get("duration"),
            renew_before=spec.get("renewBefore"),
            ready=_is_ready(conditions),
            not_after=status.get("notAfter"),
            not_before=status.get("notBefore"),
            renewal_time=status.get("renewalTime"),
            revision=status.get("revision"),
            conditions=conditions,
        )


# =============================================================================
# Issuer / ClusterIssuer
# =============================================================================


class IssuerSummary(K8sEntityBase):
    """Cert-manager Issuer / ClusterIssuer display model."""

    _entity_name: ClassVar[str] = "issuer"

    is_cluster_issuer: bool = Field(
        default=False,
        description="Whether this is a ClusterIssuer",
    )
    issuer_type: str = Field(
        default="unknown", description="Issuer type (acme, ca, selfSigned, etc.)"
    )
    acme_server: str | None = Field(default=None, description="ACME server URL")
    acme_email: str | None = Field(default=None, description="ACME registration email")
    ready: bool = Field(default=False, description="Whether the issuer is ready")
    conditions: list[CertManagerCondition] = Field(
        default_factory=list, description="Status conditions"
    )

    @classmethod
    def from_k8s_object(
        cls,
        obj: dict[str, Any],
        *,
        is_cluster_issuer: bool = False,
    ) -> IssuerSummary:
        """Create from a cert-manager Issuer/ClusterIssuer CRD dict."""
        metadata: dict[str, Any] = obj.get("metadata", {})
        spec: dict[str, Any] = obj.get("spec", {})
        status: dict[str, Any] = obj.get("status", {})

        issuer_type = _detect_issuer_type(spec)
        acme_config: dict[str, Any] = spec.get("acme", {})
        conditions = _parse_conditions(status)

        return cls(
            name=metadata.get("name", ""),
            namespace=metadata.get("namespace"),
            uid=metadata.get("uid"),
            creation_timestamp=metadata.get("creationTimestamp"),
            labels=metadata.get("labels") or None,
            annotations=metadata.get("annotations") or None,
            is_cluster_issuer=is_cluster_issuer,
            issuer_type=issuer_type,
            acme_server=acme_config.get("server") if acme_config else None,
            acme_email=acme_config.get("email") if acme_config else None,
            ready=_is_ready(conditions),
            conditions=conditions,
        )


# =============================================================================
# CertificateRequest
# =============================================================================


class CertificateRequestSummary(K8sEntityBase):
    """Cert-manager CertificateRequest display model."""

    _entity_name: ClassVar[str] = "certificate_request"

    issuer_name: str = Field(default="", description="Issuer reference name")
    issuer_kind: str = Field(default="Issuer", description="Issuer kind")
    issuer_group: str = Field(default="cert-manager.io", description="Issuer API group")
    ready: bool = Field(default=False, description="Whether the request is ready")
    approved: bool = Field(default=False, description="Whether the request is approved")
    denied: bool = Field(default=False, description="Whether the request is denied")
    conditions: list[CertManagerCondition] = Field(
        default_factory=list, description="Status conditions"
    )

    @classmethod
    def from_k8s_object(cls, obj: dict[str, Any]) -> CertificateRequestSummary:
        """Create from a cert-manager CertificateRequest CRD dict."""
        metadata: dict[str, Any] = obj.get("metadata", {})
        spec: dict[str, Any] = obj.get("spec", {})
        status: dict[str, Any] = obj.get("status", {})

        issuer_ref: dict[str, Any] = spec.get("issuerRef", {})
        conditions = _parse_conditions(status)

        # Determine approved/denied from conditions
        approved = False
        denied = False
        for c in conditions:
            if c.type == "Approved":
                approved = c.status == "True"
            elif c.type == "Denied":
                denied = c.status == "True"

        return cls(
            name=metadata.get("name", ""),
            namespace=metadata.get("namespace"),
            uid=metadata.get("uid"),
            creation_timestamp=metadata.get("creationTimestamp"),
            labels=metadata.get("labels") or None,
            annotations=metadata.get("annotations") or None,
            issuer_name=issuer_ref.get("name", ""),
            issuer_kind=issuer_ref.get("kind", "Issuer"),
            issuer_group=issuer_ref.get("group", "cert-manager.io"),
            ready=_is_ready(conditions),
            approved=approved,
            denied=denied,
            conditions=conditions,
        )


# =============================================================================
# Order (ACME)
# =============================================================================


class OrderSummary(K8sEntityBase):
    """Cert-manager ACME Order display model."""

    _entity_name: ClassVar[str] = "order"

    state: str = Field(default="", description="Order state (pending, ready, valid, invalid)")
    url: str | None = Field(default=None, description="ACME order URL")
    reason: str | None = Field(default=None, description="Failure reason")
    dns_names: list[str] = Field(default_factory=list, description="DNS names in the order")
    conditions: list[CertManagerCondition] = Field(
        default_factory=list, description="Status conditions"
    )

    @classmethod
    def from_k8s_object(cls, obj: dict[str, Any]) -> OrderSummary:
        """Create from a cert-manager ACME Order CRD dict."""
        metadata: dict[str, Any] = obj.get("metadata", {})
        spec: dict[str, Any] = obj.get("spec", {})
        status: dict[str, Any] = obj.get("status", {})

        conditions = _parse_conditions(status)

        return cls(
            name=metadata.get("name", ""),
            namespace=metadata.get("namespace"),
            uid=metadata.get("uid"),
            creation_timestamp=metadata.get("creationTimestamp"),
            labels=metadata.get("labels") or None,
            annotations=metadata.get("annotations") or None,
            state=status.get("state", ""),
            url=status.get("url"),
            reason=status.get("reason"),
            dns_names=spec.get("dnsNames", []),
            conditions=conditions,
        )


# =============================================================================
# Challenge (ACME)
# =============================================================================


class ChallengeSummary(K8sEntityBase):
    """Cert-manager ACME Challenge display model."""

    _entity_name: ClassVar[str] = "challenge"

    challenge_type: str = Field(default="", description="Challenge type (http-01, dns-01)")
    dns_name: str = Field(default="", description="Domain being validated")
    state: str = Field(
        default="", description="Challenge state (pending, processing, valid, invalid)"
    )
    presented: bool = Field(default=False, description="Whether the challenge is presented")
    processing: bool = Field(default=False, description="Whether the challenge is being processed")
    reason: str | None = Field(default=None, description="Failure reason")
    issuer_name: str = Field(default="", description="Issuer reference name")
    issuer_kind: str = Field(default="Issuer", description="Issuer kind")
    conditions: list[CertManagerCondition] = Field(
        default_factory=list, description="Status conditions"
    )

    @classmethod
    def from_k8s_object(cls, obj: dict[str, Any]) -> ChallengeSummary:
        """Create from a cert-manager ACME Challenge CRD dict."""
        metadata: dict[str, Any] = obj.get("metadata", {})
        spec: dict[str, Any] = obj.get("spec", {})
        status: dict[str, Any] = obj.get("status", {})

        issuer_ref: dict[str, Any] = spec.get("issuerRef", {})

        # Determine challenge type from spec
        challenge_type = ""
        if "solver" in spec:
            solver: dict[str, Any] = spec["solver"]
            if "http01" in solver:
                challenge_type = "http-01"
            elif "dns01" in solver:
                challenge_type = "dns-01"
        elif spec.get("type"):
            challenge_type = spec["type"]

        conditions = _parse_conditions(status)

        return cls(
            name=metadata.get("name", ""),
            namespace=metadata.get("namespace"),
            uid=metadata.get("uid"),
            creation_timestamp=metadata.get("creationTimestamp"),
            labels=metadata.get("labels") or None,
            annotations=metadata.get("annotations") or None,
            challenge_type=challenge_type,
            dns_name=spec.get("dnsName", ""),
            state=status.get("state", spec.get("state", "")),
            presented=status.get("presented", False),
            processing=status.get("processing", False),
            reason=status.get("reason"),
            issuer_name=issuer_ref.get("name", ""),
            issuer_kind=issuer_ref.get("kind", "Issuer"),
            conditions=conditions,
        )
