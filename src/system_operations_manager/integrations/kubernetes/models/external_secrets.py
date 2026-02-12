"""External Secrets Operator resource display models.

External Secrets CRDs are accessed via ``CustomObjectsApi`` which returns raw
``dict`` objects rather than typed SDK classes.  The ``from_k8s_object``
classmethods therefore use ``dict.get()`` instead of ``getattr()``.
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from system_operations_manager.integrations.kubernetes.models.base import (
    K8sEntityBase,
)

# Known ESO provider keys in SecretStore spec.provider
_PROVIDER_KEYS = (
    "vault",
    "aws",
    "azurekv",
    "gcpsm",
    "kubernetes",
    "oracle",
    "ibm",
    "doppler",
    "onepassword",
    "webhook",
    "fake",
)


class SecretStoreProviderSummary(BaseModel):
    """Summary of a SecretStore provider configuration."""

    model_config = ConfigDict(extra="ignore")

    provider_type: str = Field(
        default="unknown",
        description="Provider type: vault, aws, azurekv, gcpsm, kubernetes, etc.",
    )
    server: str | None = Field(
        default=None,
        description="Provider server/endpoint URL when available",
    )

    @classmethod
    def from_k8s_object(cls, provider_dict: dict[str, Any]) -> SecretStoreProviderSummary:
        """Detect provider type from the spec.provider dict."""
        provider_type = "unknown"
        server: str | None = None
        for key in _PROVIDER_KEYS:
            if key in provider_dict:
                provider_type = key
                provider_config = provider_dict[key]
                if isinstance(provider_config, dict):
                    server = provider_config.get("server")
                break

        return cls(provider_type=provider_type, server=server)


class SecretStoreSummary(K8sEntityBase):
    """SecretStore / ClusterSecretStore display model."""

    _entity_name: ClassVar[str] = "secret_store"

    is_cluster_store: bool = Field(
        default=False,
        description="Whether this is a ClusterSecretStore",
    )
    provider_type: str = Field(default="unknown", description="Provider type")
    provider: SecretStoreProviderSummary | None = Field(
        default=None,
        description="Provider configuration summary",
    )
    ready: bool = Field(default=False, description="Whether the store is ready")
    message: str | None = Field(default=None, description="Status message")
    conditions_count: int = Field(default=0, description="Number of status conditions")

    @classmethod
    def from_k8s_object(
        cls,
        obj: dict[str, Any],
        *,
        is_cluster_store: bool = False,
    ) -> SecretStoreSummary:
        """Create from an ESO SecretStore/ClusterSecretStore CRD dict."""
        metadata: dict[str, Any] = obj.get("metadata", {})
        spec: dict[str, Any] = obj.get("spec", {})
        status: dict[str, Any] = obj.get("status", {})

        # Parse Ready condition
        ready = False
        message = None
        conditions: list[dict[str, Any]] = status.get("conditions", [])
        for condition in conditions:
            if condition.get("type") == "Ready":
                ready = condition.get("status") == "True"
                message = condition.get("message")
                break

        # Parse provider
        provider_dict: dict[str, Any] = spec.get("provider", {})
        provider = (
            SecretStoreProviderSummary.from_k8s_object(provider_dict) if provider_dict else None
        )
        provider_type = provider.provider_type if provider else "unknown"

        return cls(
            name=metadata.get("name", ""),
            namespace=metadata.get("namespace"),
            uid=metadata.get("uid"),
            creation_timestamp=metadata.get("creationTimestamp"),
            labels=metadata.get("labels") or None,
            annotations=metadata.get("annotations") or None,
            is_cluster_store=is_cluster_store,
            provider_type=provider_type,
            provider=provider,
            ready=ready,
            message=message,
            conditions_count=len(conditions),
        )


class ExternalSecretDataRef(BaseModel):
    """Individual data mapping in an ExternalSecret."""

    model_config = ConfigDict(extra="ignore")

    secret_key: str = Field(default="", description="Key in the target Kubernetes Secret")
    remote_ref_key: str = Field(default="", description="Key path in the external provider")
    remote_ref_property: str | None = Field(
        default=None,
        description="Optional property within the remote key",
    )

    @classmethod
    def from_k8s_object(cls, obj: dict[str, Any]) -> ExternalSecretDataRef:
        """Create from an ExternalSecret data entry dict."""
        remote_ref: dict[str, Any] = obj.get("remoteRef", {})
        return cls(
            secret_key=obj.get("secretKey", ""),
            remote_ref_key=remote_ref.get("key", ""),
            remote_ref_property=remote_ref.get("property"),
        )


class ExternalSecretSummary(K8sEntityBase):
    """ExternalSecret display model."""

    _entity_name: ClassVar[str] = "external_secret"

    store_name: str = Field(
        default="", description="Referenced SecretStore/ClusterSecretStore name"
    )
    store_kind: str = Field(default="SecretStore", description="Kind of referenced store")
    target_name: str | None = Field(
        default=None,
        description="Name of the K8s Secret to create (defaults to ExternalSecret name)",
    )
    target_creation_policy: str = Field(
        default="Owner",
        description="Target creation policy: Owner, Orphan, Merge, or None",
    )
    refresh_interval: str = Field(default="1h", description="Sync refresh interval")
    data_count: int = Field(default=0, description="Number of data mappings")
    data_refs: list[ExternalSecretDataRef] = Field(
        default_factory=list,
        description="Individual data reference summaries",
    )
    ready: bool = Field(default=False, description="Whether the sync is ready")
    message: str | None = Field(default=None, description="Status message")
    synced_resource_version: str | None = Field(
        default=None,
        description="Synced resource version from status",
    )
    refresh_time: str | None = Field(
        default=None,
        description="Last refresh time from status",
    )

    @classmethod
    def from_k8s_object(cls, obj: dict[str, Any]) -> ExternalSecretSummary:
        """Create from an ESO ExternalSecret CRD dict."""
        metadata: dict[str, Any] = obj.get("metadata", {})
        spec: dict[str, Any] = obj.get("spec", {})
        status: dict[str, Any] = obj.get("status", {})

        # Store reference
        store_ref: dict[str, Any] = spec.get("secretStoreRef", {})
        store_name = store_ref.get("name", "")
        store_kind = store_ref.get("kind", "SecretStore")

        # Target
        target: dict[str, Any] = spec.get("target", {})
        target_name = target.get("name")
        target_creation_policy = target.get("creationPolicy", "Owner")

        # Data mappings
        data_raw: list[dict[str, Any]] = spec.get("data", [])
        data_refs = [ExternalSecretDataRef.from_k8s_object(d) for d in data_raw]

        # Ready condition
        ready = False
        message = None
        for condition in status.get("conditions", []):
            if condition.get("type") == "Ready":
                ready = condition.get("status") == "True"
                message = condition.get("message")
                break

        return cls(
            name=metadata.get("name", ""),
            namespace=metadata.get("namespace"),
            uid=metadata.get("uid"),
            creation_timestamp=metadata.get("creationTimestamp"),
            labels=metadata.get("labels") or None,
            annotations=metadata.get("annotations") or None,
            store_name=store_name,
            store_kind=store_kind,
            target_name=target_name,
            target_creation_policy=target_creation_policy,
            refresh_interval=spec.get("refreshInterval", "1h"),
            data_count=len(data_raw),
            data_refs=data_refs,
            ready=ready,
            message=message,
            synced_resource_version=status.get("syncedResourceVersion"),
            refresh_time=status.get("refreshTime"),
        )
