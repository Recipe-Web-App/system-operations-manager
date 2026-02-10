"""Kubernetes integration configuration models."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator


class ClusterConfig(BaseModel):
    """Configuration for a single Kubernetes cluster."""

    model_config = ConfigDict(extra="forbid")

    context: str = ""
    kubeconfig: str = "~/.kube/config"
    namespace: str = "default"
    timeout: int = 300

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout is positive."""
        if v <= 0:
            raise ValueError("timeout must be positive")
        return v

    @field_validator("kubeconfig")
    @classmethod
    def validate_kubeconfig(cls, v: str) -> str:
        """Expand ~ in kubeconfig path."""
        return str(Path(v).expanduser())


class KubernetesAuthConfig(BaseModel):
    """Kubernetes authentication configuration."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["kubeconfig", "token", "service_account", "certificate"] = "kubeconfig"
    token: str | None = None
    cert_path: str | None = None
    key_path: str | None = None
    ca_path: str | None = None

    @field_validator("type")
    @classmethod
    def validate_auth_type(cls, v: str) -> str:
        """Validate authentication type."""
        valid_types = {"kubeconfig", "token", "service_account", "certificate"}
        if v not in valid_types:
            raise ValueError(f"auth type must be one of: {', '.join(sorted(valid_types))}")
        return v


class KubernetesDefaultsConfig(BaseModel):
    """Default settings for Kubernetes operations."""

    model_config = ConfigDict(extra="forbid")

    timeout: int = 300
    retry_attempts: int = 3
    dry_run_strategy: Literal["none", "client", "server"] = "none"

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout is positive."""
        if v <= 0:
            raise ValueError("timeout must be positive")
        return v

    @field_validator("retry_attempts")
    @classmethod
    def validate_retry_attempts(cls, v: int) -> int:
        """Validate retry_attempts is non-negative."""
        if v < 0:
            raise ValueError("retry_attempts must be non-negative")
        return v


class KubernetesPluginConfig(BaseModel):
    """Complete Kubernetes plugin configuration."""

    model_config = ConfigDict(extra="forbid")

    clusters: dict[str, ClusterConfig] = {}
    active_cluster: str | None = None
    defaults: KubernetesDefaultsConfig = KubernetesDefaultsConfig()
    auth: KubernetesAuthConfig = KubernetesAuthConfig()
    output_format: Literal["table", "json", "yaml"] = "table"

    @field_validator("output_format")
    @classmethod
    def validate_output_format(cls, v: str) -> str:
        """Validate output format."""
        valid_formats = {"table", "json", "yaml"}
        if v not in valid_formats:
            raise ValueError(f"output_format must be one of: {', '.join(sorted(valid_formats))}")
        return v

    @classmethod
    def from_env(cls, base_config: dict[str, Any] | None = None) -> KubernetesPluginConfig:
        """Create configuration with environment variable overrides.

        Environment variables take precedence over base_config values.

        Supported environment variables:
            OPS_K8S_CONTEXT: Override active Kubernetes context
            OPS_K8S_NAMESPACE: Override default namespace
            OPS_K8S_KUBECONFIG: Override kubeconfig path
            OPS_K8S_TOKEN: Bearer token for authentication
            OPS_K8S_TIMEOUT: Default timeout in seconds
            OPS_K8S_OUTPUT: Output format (table, json, yaml)
            OPS_K8S_DRY_RUN: Dry run strategy (none, client, server)
        """
        config_dict = base_config.copy() if base_config else {}

        # Ensure nested dicts exist
        if "defaults" not in config_dict:
            config_dict["defaults"] = {}
        if "auth" not in config_dict:
            config_dict["auth"] = {}
        if "clusters" not in config_dict:
            config_dict["clusters"] = {}

        # Kubeconfig path override
        if kubeconfig := os.environ.get("OPS_K8S_KUBECONFIG"):
            # Apply to default cluster or all clusters without explicit kubeconfig
            config_dict.setdefault("_kubeconfig_override", kubeconfig)

        # Context override -> set as active_cluster
        if context := os.environ.get("OPS_K8S_CONTEXT"):
            config_dict["active_cluster"] = context

        # Namespace override -> apply to default cluster config
        if namespace := os.environ.get("OPS_K8S_NAMESPACE"):
            config_dict.setdefault("_namespace_override", namespace)

        # Token auth override
        if token := os.environ.get("OPS_K8S_TOKEN"):
            config_dict["auth"]["token"] = token
            if config_dict["auth"].get("type", "kubeconfig") == "kubeconfig":
                config_dict["auth"]["type"] = "token"

        # Timeout override
        if timeout := os.environ.get("OPS_K8S_TIMEOUT"):
            config_dict["defaults"]["timeout"] = int(timeout)

        # Output format override
        if output_format := os.environ.get("OPS_K8S_OUTPUT"):
            config_dict["output_format"] = output_format

        # Dry run override
        if dry_run := os.environ.get("OPS_K8S_DRY_RUN"):
            config_dict["defaults"]["dry_run_strategy"] = dry_run

        # Extract internal override keys before validation
        kubeconfig_override = config_dict.pop("_kubeconfig_override", None)
        namespace_override = config_dict.pop("_namespace_override", None)

        instance = cls.model_validate(config_dict)

        # Apply overrides to the resolved config
        if kubeconfig_override:
            for cluster_cfg in instance.clusters.values():
                cluster_cfg.kubeconfig = str(Path(kubeconfig_override).expanduser())

        if namespace_override:
            for cluster_cfg in instance.clusters.values():
                cluster_cfg.namespace = namespace_override

        return instance

    def get_active_context(self) -> str | None:
        """Get the active cluster context name.

        Returns the active_cluster if set, or the context from the first
        configured cluster, or None if no clusters are configured.
        """
        if self.active_cluster:
            # If active_cluster matches a named cluster, return its context
            if cluster := self.clusters.get(self.active_cluster):
                return cluster.context
            # Otherwise treat it as a raw context name
            return self.active_cluster
        # Fall back to first cluster's context
        if self.clusters:
            first = next(iter(self.clusters.values()))
            return first.context
        return None

    def get_active_namespace(self) -> str:
        """Get the default namespace for the active cluster.

        Returns the namespace from the active cluster config,
        or 'default' if no cluster is configured.
        """
        if self.active_cluster and self.active_cluster in self.clusters:
            return self.clusters[self.active_cluster].namespace
        if self.clusters:
            first = next(iter(self.clusters.values()))
            return first.namespace
        return "default"

    def get_active_timeout(self) -> int:
        """Get the timeout for the active cluster.

        Returns the timeout from the active cluster config,
        or the default timeout.
        """
        if self.active_cluster and self.active_cluster in self.clusters:
            return self.clusters[self.active_cluster].timeout
        return self.defaults.timeout
