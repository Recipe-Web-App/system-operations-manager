"""Unit tests for External Secrets Operator Kubernetes resource models."""

from __future__ import annotations

import pytest

from system_operations_manager.integrations.kubernetes.models.external_secrets import (
    ExternalSecretDataRef,
    ExternalSecretSummary,
    SecretStoreProviderSummary,
    SecretStoreSummary,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestSecretStoreProviderSummary:
    """Test SecretStoreProviderSummary model."""

    def test_from_k8s_object_vault_provider(self) -> None:
        """Test provider detection for HashiCorp Vault."""
        provider_dict = {
            "vault": {
                "server": "https://vault.example.com",
                "path": "secret",
                "version": "v2",
            }
        }

        provider = SecretStoreProviderSummary.from_k8s_object(provider_dict)

        assert provider.provider_type == "vault"
        assert provider.server == "https://vault.example.com"

    def test_from_k8s_object_aws_provider(self) -> None:
        """Test provider detection for AWS Secrets Manager."""
        provider_dict = {
            "aws": {
                "service": "SecretsManager",
                "region": "us-east-1",
            }
        }

        provider = SecretStoreProviderSummary.from_k8s_object(provider_dict)

        assert provider.provider_type == "aws"
        assert provider.server is None

    def test_from_k8s_object_azurekv_provider(self) -> None:
        """Test provider detection for Azure Key Vault."""
        provider_dict = {
            "azurekv": {
                "vaultUrl": "https://myvault.vault.azure.net/",
                "tenantId": "tenant-uuid",
            }
        }

        provider = SecretStoreProviderSummary.from_k8s_object(provider_dict)

        assert provider.provider_type == "azurekv"
        assert provider.server is None

    def test_from_k8s_object_gcpsm_provider(self) -> None:
        """Test provider detection for Google Cloud Secret Manager."""
        provider_dict = {
            "gcpsm": {
                "projectID": "my-gcp-project",
            }
        }

        provider = SecretStoreProviderSummary.from_k8s_object(provider_dict)

        assert provider.provider_type == "gcpsm"
        assert provider.server is None

    def test_from_k8s_object_kubernetes_provider(self) -> None:
        """Test provider detection for Kubernetes native provider.

        The Kubernetes ESO provider uses a nested auth block rather than a top-level
        'server' string, so server resolves to None after detection.
        """
        provider_dict = {
            "kubernetes": {
                "remoteNamespace": "cross-cluster-ns",
                "auth": {"serviceAccount": {"name": "eso-sa"}},
            }
        }

        provider = SecretStoreProviderSummary.from_k8s_object(provider_dict)

        assert provider.provider_type == "kubernetes"
        assert provider.server is None

    def test_from_k8s_object_vault_with_server(self) -> None:
        """Test that vault server URL is extracted correctly."""
        provider_dict = {
            "vault": {
                "server": "https://vault.internal:8200",
            }
        }

        provider = SecretStoreProviderSummary.from_k8s_object(provider_dict)

        assert provider.server == "https://vault.internal:8200"

    def test_from_k8s_object_unknown_provider(self) -> None:
        """Test that an unrecognised provider key yields 'unknown'."""
        provider_dict = {
            "customProvider": {
                "endpoint": "https://custom.example.com",
            }
        }

        provider = SecretStoreProviderSummary.from_k8s_object(provider_dict)

        assert provider.provider_type == "unknown"
        assert provider.server is None

    def test_from_k8s_object_empty_dict(self) -> None:
        """Test from_k8s_object with an empty provider dict."""
        provider = SecretStoreProviderSummary.from_k8s_object({})

        assert provider.provider_type == "unknown"
        assert provider.server is None

    def test_from_k8s_object_doppler_provider(self) -> None:
        """Test provider detection for Doppler."""
        provider_dict = {
            "doppler": {
                "project": "my-project",
                "config": "production",
            }
        }

        provider = SecretStoreProviderSummary.from_k8s_object(provider_dict)

        assert provider.provider_type == "doppler"

    def test_from_k8s_object_fake_provider(self) -> None:
        """Test provider detection for the fake/test provider."""
        provider_dict = {
            "fake": {
                "data": [{"key": "test-key", "value": "test-value"}],
            }
        }

        provider = SecretStoreProviderSummary.from_k8s_object(provider_dict)

        assert provider.provider_type == "fake"

    def test_from_k8s_object_oracle_provider(self) -> None:
        """Test provider detection for Oracle Vault."""
        provider_dict = {
            "oracle": {
                "region": "us-ashburn-1",
                "vault": "ocid1.vault.oc1...",
            }
        }

        provider = SecretStoreProviderSummary.from_k8s_object(provider_dict)

        assert provider.provider_type == "oracle"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestSecretStoreSummary:
    """Test SecretStoreSummary model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with all fields present."""
        obj = {
            "metadata": {
                "name": "vault-store",
                "namespace": "external-secrets",
                "uid": "uid-ss-001",
                "creationTimestamp": "2026-01-01T00:00:00Z",
                "labels": {"environment": "production"},
                "annotations": {"owner": "platform-team"},
            },
            "spec": {
                "provider": {
                    "vault": {
                        "server": "https://vault.example.com",
                        "path": "secret",
                        "version": "v2",
                    }
                }
            },
            "status": {
                "conditions": [
                    {
                        "type": "Ready",
                        "status": "True",
                        "message": "store validated",
                    }
                ]
            },
        }

        ss = SecretStoreSummary.from_k8s_object(obj)

        assert ss.name == "vault-store"
        assert ss.namespace == "external-secrets"
        assert ss.uid == "uid-ss-001"
        assert ss.labels == {"environment": "production"}
        assert ss.is_cluster_store is False
        assert ss.provider_type == "vault"
        assert ss.provider is not None
        assert ss.provider.server == "https://vault.example.com"
        assert ss.ready is True
        assert ss.message == "store validated"
        assert ss.conditions_count == 1

    def test_from_k8s_object_minimal(self) -> None:
        """Test from_k8s_object with only a name."""
        obj = {
            "metadata": {"name": "bare-store"},
        }

        ss = SecretStoreSummary.from_k8s_object(obj)

        assert ss.name == "bare-store"
        assert ss.namespace is None
        assert ss.is_cluster_store is False
        assert ss.provider_type == "unknown"
        assert ss.provider is None
        assert ss.ready is False
        assert ss.message is None
        assert ss.conditions_count == 0

    def test_from_k8s_object_no_status(self) -> None:
        """Test from_k8s_object with provider but no status section."""
        obj = {
            "metadata": {
                "name": "no-status-store",
                "namespace": "default",
            },
            "spec": {"provider": {"aws": {"service": "SecretsManager", "region": "eu-west-1"}}},
        }

        ss = SecretStoreSummary.from_k8s_object(obj)

        assert ss.provider_type == "aws"
        assert ss.ready is False
        assert ss.conditions_count == 0

    def test_from_k8s_object_cluster_store_flag(self) -> None:
        """Test that is_cluster_store flag is propagated correctly."""
        obj = {
            "metadata": {
                "name": "cluster-vault-store",
                "uid": "uid-css-001",
            },
            "spec": {"provider": {"vault": {"server": "https://vault.cluster.internal"}}},
            "status": {},
        }

        css = SecretStoreSummary.from_k8s_object(obj, is_cluster_store=True)

        assert css.is_cluster_store is True
        assert css.name == "cluster-vault-store"

    def test_from_k8s_object_not_ready(self) -> None:
        """Test from_k8s_object when the store is not ready."""
        obj = {
            "metadata": {"name": "unhealthy-store", "namespace": "eso"},
            "spec": {"provider": {"vault": {"server": "https://vault.down"}}},
            "status": {
                "conditions": [
                    {
                        "type": "Ready",
                        "status": "False",
                        "message": "connection refused",
                    }
                ]
            },
        }

        ss = SecretStoreSummary.from_k8s_object(obj)

        assert ss.ready is False
        assert ss.message == "connection refused"
        assert ss.conditions_count == 1

    def test_from_k8s_object_multiple_conditions_uses_ready(self) -> None:
        """Test that the Ready condition is selected from multiple conditions."""
        obj = {
            "metadata": {"name": "multi-cond-store", "namespace": "eso"},
            "spec": {"provider": {"vault": {"server": "https://vault.example.com"}}},
            "status": {
                "conditions": [
                    {"type": "Configured", "status": "True", "message": "configured"},
                    {"type": "Ready", "status": "True", "message": "all good"},
                    {"type": "Deprecated", "status": "False", "message": "old api"},
                ]
            },
        }

        ss = SecretStoreSummary.from_k8s_object(obj)

        assert ss.ready is True
        assert ss.message == "all good"
        assert ss.conditions_count == 3

    def test_from_k8s_object_no_ready_condition(self) -> None:
        """Test from_k8s_object when conditions exist but none is type 'Ready'."""
        obj = {
            "metadata": {"name": "no-ready-cond-store"},
            "spec": {"provider": {"fake": {}}},
            "status": {"conditions": [{"type": "Configured", "status": "True", "message": "ok"}]},
        }

        ss = SecretStoreSummary.from_k8s_object(obj)

        assert ss.ready is False
        assert ss.message is None
        assert ss.conditions_count == 1

    def test_from_k8s_object_empty_provider_dict(self) -> None:
        """Test from_k8s_object when spec.provider is present but empty."""
        obj = {
            "metadata": {"name": "empty-provider-store"},
            "spec": {"provider": {}},
        }

        ss = SecretStoreSummary.from_k8s_object(obj)

        assert ss.provider is None
        assert ss.provider_type == "unknown"

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert SecretStoreSummary._entity_name == "secret_store"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestExternalSecretDataRef:
    """Test ExternalSecretDataRef model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with all fields present."""
        obj = {
            "secretKey": "db-password",
            "remoteRef": {
                "key": "myapp/production/database",
                "property": "password",
            },
        }

        ref = ExternalSecretDataRef.from_k8s_object(obj)

        assert ref.secret_key == "db-password"
        assert ref.remote_ref_key == "myapp/production/database"
        assert ref.remote_ref_property == "password"

    def test_from_k8s_object_no_property(self) -> None:
        """Test from_k8s_object when remoteRef has no property field."""
        obj = {
            "secretKey": "api-key",
            "remoteRef": {
                "key": "myapp/api-key",
            },
        }

        ref = ExternalSecretDataRef.from_k8s_object(obj)

        assert ref.secret_key == "api-key"
        assert ref.remote_ref_key == "myapp/api-key"
        assert ref.remote_ref_property is None

    def test_from_k8s_object_minimal(self) -> None:
        """Test from_k8s_object with an empty dict."""
        ref = ExternalSecretDataRef.from_k8s_object({})

        assert ref.secret_key == ""
        assert ref.remote_ref_key == ""
        assert ref.remote_ref_property is None

    def test_from_k8s_object_no_remote_ref(self) -> None:
        """Test from_k8s_object when remoteRef section is missing."""
        obj = {
            "secretKey": "orphaned-key",
        }

        ref = ExternalSecretDataRef.from_k8s_object(obj)

        assert ref.secret_key == "orphaned-key"
        assert ref.remote_ref_key == ""
        assert ref.remote_ref_property is None

    def test_from_k8s_object_property_explicitly_none(self) -> None:
        """Test that a missing property field resolves to None."""
        obj = {
            "secretKey": "session-key",
            "remoteRef": {
                "key": "auth/session",
            },
        }

        ref = ExternalSecretDataRef.from_k8s_object(obj)

        assert ref.remote_ref_property is None


@pytest.mark.unit
@pytest.mark.kubernetes
class TestExternalSecretSummary:
    """Test ExternalSecretSummary model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with all fields present."""
        obj = {
            "metadata": {
                "name": "app-secrets",
                "namespace": "production",
                "uid": "uid-es-001",
                "creationTimestamp": "2026-01-01T00:00:00Z",
                "labels": {"app": "myapp"},
                "annotations": {"managed-by": "platform"},
            },
            "spec": {
                "secretStoreRef": {
                    "name": "vault-store",
                    "kind": "ClusterSecretStore",
                },
                "target": {
                    "name": "myapp-secrets",
                    "creationPolicy": "Owner",
                },
                "refreshInterval": "15m",
                "data": [
                    {
                        "secretKey": "db-password",
                        "remoteRef": {
                            "key": "myapp/prod/db",
                            "property": "password",
                        },
                    },
                    {
                        "secretKey": "api-key",
                        "remoteRef": {
                            "key": "myapp/prod/api",
                        },
                    },
                ],
            },
            "status": {
                "conditions": [
                    {
                        "type": "Ready",
                        "status": "True",
                        "message": "Secret synced successfully",
                    }
                ],
                "syncedResourceVersion": "v1-abc123",
                "refreshTime": "2026-01-15T10:00:00Z",
            },
        }

        es = ExternalSecretSummary.from_k8s_object(obj)

        assert es.name == "app-secrets"
        assert es.namespace == "production"
        assert es.uid == "uid-es-001"
        assert es.labels == {"app": "myapp"}
        assert es.store_name == "vault-store"
        assert es.store_kind == "ClusterSecretStore"
        assert es.target_name == "myapp-secrets"
        assert es.target_creation_policy == "Owner"
        assert es.refresh_interval == "15m"
        assert es.data_count == 2
        assert len(es.data_refs) == 2
        assert es.data_refs[0].secret_key == "db-password"
        assert es.data_refs[0].remote_ref_property == "password"
        assert es.data_refs[1].secret_key == "api-key"
        assert es.data_refs[1].remote_ref_property is None
        assert es.ready is True
        assert es.message == "Secret synced successfully"
        assert es.synced_resource_version == "v1-abc123"
        assert es.refresh_time == "2026-01-15T10:00:00Z"

    def test_from_k8s_object_minimal(self) -> None:
        """Test from_k8s_object with only a name."""
        obj = {
            "metadata": {"name": "bare-external-secret"},
        }

        es = ExternalSecretSummary.from_k8s_object(obj)

        assert es.name == "bare-external-secret"
        assert es.namespace is None
        assert es.store_name == ""
        assert es.store_kind == "SecretStore"
        assert es.target_name is None
        assert es.target_creation_policy == "Owner"
        assert es.refresh_interval == "1h"
        assert es.data_count == 0
        assert es.data_refs == []
        assert es.ready is False
        assert es.message is None
        assert es.synced_resource_version is None
        assert es.refresh_time is None

    def test_from_k8s_object_no_status(self) -> None:
        """Test from_k8s_object with no status section."""
        obj = {
            "metadata": {
                "name": "no-status-es",
                "namespace": "default",
            },
            "spec": {
                "secretStoreRef": {"name": "my-store", "kind": "SecretStore"},
                "data": [{"secretKey": "key", "remoteRef": {"key": "path/key"}}],
            },
        }

        es = ExternalSecretSummary.from_k8s_object(obj)

        assert es.ready is False
        assert es.message is None
        assert es.data_count == 1
        assert es.synced_resource_version is None

    def test_from_k8s_object_not_ready(self) -> None:
        """Test from_k8s_object when the sync has failed."""
        obj = {
            "metadata": {"name": "failing-es", "namespace": "staging"},
            "spec": {
                "secretStoreRef": {"name": "vault-store"},
                "data": [],
            },
            "status": {
                "conditions": [
                    {
                        "type": "Ready",
                        "status": "False",
                        "message": "secret not found in vault",
                    }
                ]
            },
        }

        es = ExternalSecretSummary.from_k8s_object(obj)

        assert es.ready is False
        assert es.message == "secret not found in vault"

    def test_from_k8s_object_store_kind_defaults_to_secret_store(self) -> None:
        """Test that store kind defaults to SecretStore when not specified."""
        obj = {
            "metadata": {"name": "default-kind-es"},
            "spec": {
                "secretStoreRef": {"name": "my-store"},
            },
        }

        es = ExternalSecretSummary.from_k8s_object(obj)

        assert es.store_kind == "SecretStore"

    def test_from_k8s_object_data_refs_parsed_correctly(self) -> None:
        """Test that multiple data entries are all parsed into ExternalSecretDataRef."""
        obj = {
            "metadata": {"name": "multi-data-es", "namespace": "apps"},
            "spec": {
                "secretStoreRef": {"name": "store"},
                "data": [
                    {
                        "secretKey": "key-a",
                        "remoteRef": {"key": "path/a", "property": "value"},
                    },
                    {
                        "secretKey": "key-b",
                        "remoteRef": {"key": "path/b"},
                    },
                    {
                        "secretKey": "key-c",
                        "remoteRef": {"key": "path/c", "property": "sub-key"},
                    },
                ],
            },
        }

        es = ExternalSecretSummary.from_k8s_object(obj)

        assert es.data_count == 3
        assert len(es.data_refs) == 3
        assert es.data_refs[0].secret_key == "key-a"
        assert es.data_refs[0].remote_ref_property == "value"
        assert es.data_refs[1].remote_ref_property is None
        assert es.data_refs[2].remote_ref_key == "path/c"

    def test_from_k8s_object_cluster_secret_store_kind(self) -> None:
        """Test from_k8s_object referencing a ClusterSecretStore."""
        obj = {
            "metadata": {"name": "cluster-ref-es", "namespace": "team-ns"},
            "spec": {
                "secretStoreRef": {
                    "name": "global-vault-store",
                    "kind": "ClusterSecretStore",
                },
                "refreshInterval": "5m",
            },
        }

        es = ExternalSecretSummary.from_k8s_object(obj)

        assert es.store_kind == "ClusterSecretStore"
        assert es.refresh_interval == "5m"

    def test_from_k8s_object_empty_labels_and_annotations_become_none(self) -> None:
        """Test that empty labels/annotations are coerced to None."""
        obj = {
            "metadata": {
                "name": "clean-es",
                "labels": {},
                "annotations": {},
            },
        }

        es = ExternalSecretSummary.from_k8s_object(obj)

        assert es.labels is None
        assert es.annotations is None

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert ExternalSecretSummary._entity_name == "external_secret"
