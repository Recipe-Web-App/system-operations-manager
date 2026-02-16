"""Unit tests for Kubernetes configuration models."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from system_operations_manager.integrations.kubernetes.config import (
    ClusterConfig,
    KubernetesAuthConfig,
    KubernetesDefaultsConfig,
    KubernetesPluginConfig,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestClusterConfig:
    """Test ClusterConfig Pydantic model."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = ClusterConfig()
        assert config.context == ""
        assert config.kubeconfig == "~/.kube/config"
        assert config.namespace == "default"
        assert config.timeout == 300

    def test_custom_values(self) -> None:
        """Test initialization with custom values."""
        config = ClusterConfig(
            context="minikube",
            kubeconfig="/custom/kubeconfig",
            namespace="production",
            timeout=600,
        )
        assert config.context == "minikube"
        assert config.kubeconfig == "/custom/kubeconfig"
        assert config.namespace == "production"
        assert config.timeout == 600

    def test_kubeconfig_path_expansion(self) -> None:
        """Test that tilde in kubeconfig path is expanded."""
        config = ClusterConfig(kubeconfig="~/custom/config")
        assert "~" not in config.kubeconfig
        assert config.kubeconfig == str(Path("~/custom/config").expanduser())

    def test_timeout_validation_positive(self) -> None:
        """Test that positive timeout is valid."""
        config = ClusterConfig(timeout=1)
        assert config.timeout == 1

    def test_timeout_validation_zero(self) -> None:
        """Test that zero timeout raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ClusterConfig(timeout=0)
        assert "timeout must be positive" in str(exc_info.value)

    def test_timeout_validation_negative(self) -> None:
        """Test that negative timeout raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ClusterConfig(timeout=-100)
        assert "timeout must be positive" in str(exc_info.value)

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ClusterConfig(unknown_field="value")  # type: ignore[call-arg]
        assert "extra" in str(exc_info.value).lower()


@pytest.mark.unit
@pytest.mark.kubernetes
class TestKubernetesAuthConfig:
    """Test KubernetesAuthConfig Pydantic model."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = KubernetesAuthConfig()
        assert config.type == "kubeconfig"
        assert config.token is None
        assert config.cert_path is None
        assert config.key_path is None
        assert config.ca_path is None

    def test_kubeconfig_auth(self) -> None:
        """Test kubeconfig authentication type."""
        config = KubernetesAuthConfig(type="kubeconfig")
        assert config.type == "kubeconfig"

    def test_token_auth(self) -> None:
        """Test token authentication type."""
        config = KubernetesAuthConfig(type="token", token="eyJhbGciOiJSUzI1...")
        assert config.type == "token"
        assert config.token == "eyJhbGciOiJSUzI1..."

    def test_certificate_auth(self) -> None:
        """Test certificate authentication type."""
        config = KubernetesAuthConfig(
            type="certificate",
            cert_path="/path/to/cert.pem",
            key_path="/path/to/key.pem",
            ca_path="/path/to/ca.pem",
        )
        assert config.type == "certificate"
        assert config.cert_path == "/path/to/cert.pem"
        assert config.key_path == "/path/to/key.pem"
        assert config.ca_path == "/path/to/ca.pem"

    def test_service_account_auth(self) -> None:
        """Test service account authentication type."""
        config = KubernetesAuthConfig(type="service_account")
        assert config.type == "service_account"

    def test_invalid_auth_type(self) -> None:
        """Test that invalid auth type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            KubernetesAuthConfig(type="invalid")  # type: ignore[arg-type]
        assert "Input should be" in str(exc_info.value) or "literal_error" in str(exc_info.value)

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            KubernetesAuthConfig(unknown="value")  # type: ignore[call-arg]
        assert "extra" in str(exc_info.value).lower()


@pytest.mark.unit
@pytest.mark.kubernetes
class TestKubernetesDefaultsConfig:
    """Test KubernetesDefaultsConfig Pydantic model."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = KubernetesDefaultsConfig()
        assert config.timeout == 300
        assert config.retry_attempts == 3
        assert config.dry_run_strategy == "none"

    def test_custom_values(self) -> None:
        """Test initialization with custom values."""
        config = KubernetesDefaultsConfig(
            timeout=600,
            retry_attempts=5,
            dry_run_strategy="server",
        )
        assert config.timeout == 600
        assert config.retry_attempts == 5
        assert config.dry_run_strategy == "server"

    def test_timeout_validation_positive(self) -> None:
        """Test that positive timeout is valid."""
        config = KubernetesDefaultsConfig(timeout=100)
        assert config.timeout == 100

    def test_timeout_validation_zero(self) -> None:
        """Test that zero timeout raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            KubernetesDefaultsConfig(timeout=0)
        assert "timeout must be positive" in str(exc_info.value)

    def test_timeout_validation_negative(self) -> None:
        """Test that negative timeout raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            KubernetesDefaultsConfig(timeout=-1)
        assert "timeout must be positive" in str(exc_info.value)

    def test_retry_attempts_zero(self) -> None:
        """Test that zero retry attempts is valid."""
        config = KubernetesDefaultsConfig(retry_attempts=0)
        assert config.retry_attempts == 0

    def test_retry_attempts_negative(self) -> None:
        """Test that negative retry attempts raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            KubernetesDefaultsConfig(retry_attempts=-1)
        assert "retry_attempts must be non-negative" in str(exc_info.value)

    def test_dry_run_strategy_none(self) -> None:
        """Test dry_run_strategy='none'."""
        config = KubernetesDefaultsConfig(dry_run_strategy="none")
        assert config.dry_run_strategy == "none"

    def test_dry_run_strategy_client(self) -> None:
        """Test dry_run_strategy='client'."""
        config = KubernetesDefaultsConfig(dry_run_strategy="client")
        assert config.dry_run_strategy == "client"

    def test_dry_run_strategy_server(self) -> None:
        """Test dry_run_strategy='server'."""
        config = KubernetesDefaultsConfig(dry_run_strategy="server")
        assert config.dry_run_strategy == "server"

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            KubernetesDefaultsConfig(extra_field="value")  # type: ignore[call-arg]
        assert "extra" in str(exc_info.value).lower()


@pytest.mark.unit
@pytest.mark.kubernetes
class TestKubernetesPluginConfig:
    """Test KubernetesPluginConfig Pydantic model."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = KubernetesPluginConfig()
        assert config.clusters == {}
        assert config.active_cluster is None
        assert isinstance(config.defaults, KubernetesDefaultsConfig)
        assert isinstance(config.auth, KubernetesAuthConfig)
        assert config.output_format == "table"

    def test_custom_values(self) -> None:
        """Test initialization with custom values."""
        cluster_config = ClusterConfig(context="prod", namespace="production")
        config = KubernetesPluginConfig(
            clusters={"production": cluster_config},
            active_cluster="production",
            output_format="json",
        )
        assert "production" in config.clusters
        assert config.active_cluster == "production"
        assert config.output_format == "json"

    def test_output_format_table(self) -> None:
        """Test output_format='table'."""
        config = KubernetesPluginConfig(output_format="table")
        assert config.output_format == "table"

    def test_output_format_json(self) -> None:
        """Test output_format='json'."""
        config = KubernetesPluginConfig(output_format="json")
        assert config.output_format == "json"

    def test_output_format_yaml(self) -> None:
        """Test output_format='yaml'."""
        config = KubernetesPluginConfig(output_format="yaml")
        assert config.output_format == "yaml"

    def test_invalid_output_format(self) -> None:
        """Test that invalid output format raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            KubernetesPluginConfig(output_format="xml")  # type: ignore[arg-type]
        assert "Input should be" in str(exc_info.value) or "literal_error" in str(exc_info.value)

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            KubernetesPluginConfig(unknown="value")  # type: ignore[call-arg]
        assert "extra" in str(exc_info.value).lower()

    def test_get_active_context_no_clusters(self) -> None:
        """Test get_active_context with no clusters."""
        config = KubernetesPluginConfig()
        assert config.get_active_context() is None

    def test_get_active_context_with_active_cluster_name(self) -> None:
        """Test get_active_context with named cluster."""
        cluster_config = ClusterConfig(context="prod-context")
        config = KubernetesPluginConfig(
            clusters={"production": cluster_config},
            active_cluster="production",
        )
        assert config.get_active_context() == "prod-context"

    def test_get_active_context_with_raw_context(self) -> None:
        """Test get_active_context with raw context name."""
        config = KubernetesPluginConfig(active_cluster="minikube")
        assert config.get_active_context() == "minikube"

    def test_get_active_context_first_cluster(self) -> None:
        """Test get_active_context falls back to first cluster."""
        cluster_config = ClusterConfig(context="first-context")
        config = KubernetesPluginConfig(clusters={"first": cluster_config})
        assert config.get_active_context() == "first-context"

    def test_get_active_namespace_no_clusters(self) -> None:
        """Test get_active_namespace with no clusters."""
        config = KubernetesPluginConfig()
        assert config.get_active_namespace() == "default"

    def test_get_active_namespace_with_active_cluster(self) -> None:
        """Test get_active_namespace with active cluster."""
        cluster_config = ClusterConfig(namespace="production")
        config = KubernetesPluginConfig(
            clusters={"prod": cluster_config},
            active_cluster="prod",
        )
        assert config.get_active_namespace() == "production"

    def test_get_active_namespace_first_cluster(self) -> None:
        """Test get_active_namespace falls back to first cluster."""
        cluster_config = ClusterConfig(namespace="staging")
        config = KubernetesPluginConfig(clusters={"first": cluster_config})
        assert config.get_active_namespace() == "staging"

    def test_get_active_timeout_no_clusters(self) -> None:
        """Test get_active_timeout with no clusters."""
        config = KubernetesPluginConfig()
        assert config.get_active_timeout() == 300

    def test_get_active_timeout_with_active_cluster(self) -> None:
        """Test get_active_timeout with active cluster."""
        cluster_config = ClusterConfig(timeout=600)
        config = KubernetesPluginConfig(
            clusters={"prod": cluster_config},
            active_cluster="prod",
        )
        assert config.get_active_timeout() == 600

    def test_get_active_timeout_default(self) -> None:
        """Test get_active_timeout uses default when cluster has default timeout."""
        config = KubernetesPluginConfig(defaults=KubernetesDefaultsConfig(timeout=450))
        assert config.get_active_timeout() == 450

    def test_from_env_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test from_env with no environment variables."""
        # Clear any K8s env vars
        for key in list(os.environ.keys()):
            if key.startswith("OPS_K8S_"):
                monkeypatch.delenv(key, raising=False)

        config = KubernetesPluginConfig.from_env()
        assert isinstance(config, KubernetesPluginConfig)
        assert config.clusters == {}
        assert config.active_cluster is None

    def test_from_env_context_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test from_env with OPS_K8S_CONTEXT."""
        monkeypatch.setenv("OPS_K8S_CONTEXT", "test-context")
        config = KubernetesPluginConfig.from_env()
        assert config.active_cluster == "test-context"

    def test_from_env_namespace_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test from_env with OPS_K8S_NAMESPACE."""
        monkeypatch.setenv("OPS_K8S_NAMESPACE", "custom-ns")
        base = {"clusters": {"test": {"context": "test"}}}
        config = KubernetesPluginConfig.from_env(base)
        assert config.clusters["test"].namespace == "custom-ns"

    def test_from_env_kubeconfig_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test from_env with OPS_K8S_KUBECONFIG."""
        monkeypatch.setenv("OPS_K8S_KUBECONFIG", "/custom/config")
        base = {"clusters": {"test": {"context": "test"}}}
        config = KubernetesPluginConfig.from_env(base)
        assert config.clusters["test"].kubeconfig == "/custom/config"

    def test_from_env_token_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test from_env with OPS_K8S_TOKEN."""
        monkeypatch.setenv("OPS_K8S_TOKEN", "test-token-123")
        config = KubernetesPluginConfig.from_env()
        assert config.auth.token == "test-token-123"
        assert config.auth.type == "token"

    def test_from_env_timeout_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test from_env with OPS_K8S_TIMEOUT."""
        monkeypatch.setenv("OPS_K8S_TIMEOUT", "600")
        config = KubernetesPluginConfig.from_env()
        assert config.defaults.timeout == 600

    def test_from_env_output_format_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test from_env with OPS_K8S_OUTPUT."""
        monkeypatch.setenv("OPS_K8S_OUTPUT", "yaml")
        config = KubernetesPluginConfig.from_env()
        assert config.output_format == "yaml"

    def test_from_env_dry_run_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test from_env with OPS_K8S_DRY_RUN."""
        monkeypatch.setenv("OPS_K8S_DRY_RUN", "server")
        config = KubernetesPluginConfig.from_env()
        assert config.defaults.dry_run_strategy == "server"

    def test_from_env_with_base_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test from_env merges with base config."""
        base = {
            "clusters": {"prod": {"context": "production", "namespace": "prod-ns"}},
            "active_cluster": "prod",
        }
        monkeypatch.setenv("OPS_K8S_TIMEOUT", "900")
        config = KubernetesPluginConfig.from_env(base)
        assert config.active_cluster == "prod"
        assert config.clusters["prod"].namespace == "prod-ns"
        assert config.defaults.timeout == 900
