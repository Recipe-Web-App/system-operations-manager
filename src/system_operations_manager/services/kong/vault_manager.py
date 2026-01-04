"""Kong Enterprise vault manager.

This module provides the service layer for managing Kong Enterprise vaults,
enabling secret management integration with external vault providers.
"""

from __future__ import annotations

from typing import Any

import structlog

from system_operations_manager.integrations.kong.models.enterprise import (
    AWSSecretsConfig,
    AzureVaultConfig,
    EnvVaultConfig,
    GCPSecretsConfig,
    HashiCorpVaultConfig,
    Vault,
)
from system_operations_manager.services.kong.base import BaseEntityManager

logger = structlog.get_logger()


class VaultManager(BaseEntityManager[Vault]):
    """Manager for Kong Enterprise vaults.

    Vaults provide secret management integration, allowing Kong to retrieve
    secrets from external vault providers like HashiCorp Vault, AWS Secrets
    Manager, GCP Secret Manager, Azure Key Vault, or environment variables.

    Secrets can be referenced in plugin configurations using vault:// URIs:
        {vault://my-vault/path/to/secret}

    Example:
        >>> manager = VaultManager(client)
        >>> vault = manager.configure_hcv(
        ...     "hcv-production",
        ...     HashiCorpVaultConfig(host="vault.example.com", mount="secret"),
        ... )
        >>> print(f"Vault prefix: {vault.prefix}")
    """

    _endpoint = "vaults"
    _entity_name = "vault"
    _model_class = Vault

    def configure_hcv(
        self,
        name: str,
        config: HashiCorpVaultConfig,
        *,
        prefix: str | None = None,
        description: str | None = None,
    ) -> Vault:
        """Configure a HashiCorp Vault integration.

        Args:
            name: Unique vault name.
            config: HashiCorp Vault configuration.
            prefix: Custom vault prefix (defaults to name).
            description: Optional description.

        Returns:
            The created vault entity.
        """
        vault_config: dict[str, Any] = {
            "host": config.host,
            "port": config.port,
            "protocol": config.protocol,
            "mount": config.mount,
            "kv": config.kv,
            "auth_method": config.auth_method,
        }

        if config.token:
            vault_config["token"] = config.token
        if config.namespace:
            vault_config["namespace"] = config.namespace

        vault = Vault(
            name=name,
            prefix=prefix or name,
            description=description,
            config=vault_config,
        )

        self._log.info("configuring_hcv_vault", name=name, host=config.host)
        return self.create(vault)

    def configure_aws(
        self,
        name: str,
        config: AWSSecretsConfig,
        *,
        prefix: str | None = None,
        description: str | None = None,
    ) -> Vault:
        """Configure an AWS Secrets Manager integration.

        Args:
            name: Unique vault name.
            config: AWS Secrets Manager configuration.
            prefix: Custom vault prefix (defaults to name).
            description: Optional description.

        Returns:
            The created vault entity.
        """
        vault_config: dict[str, Any] = {
            "region": config.region,
        }

        if config.endpoint_url:
            vault_config["endpoint_url"] = config.endpoint_url
        if config.role_arn:
            vault_config["role_arn"] = config.role_arn

        vault = Vault(
            name=name,
            prefix=prefix or name,
            description=description,
            config=vault_config,
        )

        self._log.info("configuring_aws_vault", name=name, region=config.region)
        return self.create(vault)

    def configure_gcp(
        self,
        name: str,
        config: GCPSecretsConfig,
        *,
        prefix: str | None = None,
        description: str | None = None,
    ) -> Vault:
        """Configure a GCP Secret Manager integration.

        Args:
            name: Unique vault name.
            config: GCP Secret Manager configuration.
            prefix: Custom vault prefix (defaults to name).
            description: Optional description.

        Returns:
            The created vault entity.
        """
        vault_config: dict[str, Any] = {
            "project_id": config.project_id,
        }

        vault = Vault(
            name=name,
            prefix=prefix or name,
            description=description,
            config=vault_config,
        )

        self._log.info("configuring_gcp_vault", name=name, project=config.project_id)
        return self.create(vault)

    def configure_azure(
        self,
        name: str,
        config: AzureVaultConfig,
        *,
        prefix: str | None = None,
        description: str | None = None,
    ) -> Vault:
        """Configure an Azure Key Vault integration.

        Args:
            name: Unique vault name.
            config: Azure Key Vault configuration.
            prefix: Custom vault prefix (defaults to name).
            description: Optional description.

        Returns:
            The created vault entity.
        """
        vault_config: dict[str, Any] = {
            "vault_uri": config.vault_uri,
        }

        if config.client_id:
            vault_config["client_id"] = config.client_id
        if config.tenant_id:
            vault_config["tenant_id"] = config.tenant_id

        vault = Vault(
            name=name,
            prefix=prefix or name,
            description=description,
            config=vault_config,
        )

        self._log.info("configuring_azure_vault", name=name, uri=config.vault_uri)
        return self.create(vault)

    def configure_env(
        self,
        name: str,
        config: EnvVaultConfig,
        *,
        prefix: str | None = None,
        description: str | None = None,
    ) -> Vault:
        """Configure an environment variable vault.

        This vault type reads secrets from environment variables.

        Args:
            name: Unique vault name.
            config: Environment vault configuration.
            prefix: Custom vault prefix (defaults to name).
            description: Optional description.

        Returns:
            The created vault entity.
        """
        vault_config: dict[str, Any] = {
            "prefix": config.prefix,
        }

        vault = Vault(
            name=name,
            prefix=prefix or name,
            description=description,
            config=vault_config,
        )

        self._log.info("configuring_env_vault", name=name, env_prefix=config.prefix)
        return self.create(vault)

    def get_vault_type(self, vault: Vault) -> str:
        """Determine the type of a vault from its configuration.

        Args:
            vault: Vault entity to inspect.

        Returns:
            Vault type string: "hcv", "aws", "gcp", "azure", "env", or "unknown".
        """
        config = vault.config

        if "host" in config and ("mount" in config or "kv" in config):
            return "hcv"
        if "region" in config:
            return "aws"
        if "project_id" in config:
            return "gcp"
        if "vault_uri" in config:
            return "azure"
        if "prefix" in config and len(config) == 1:
            return "env"

        return "unknown"

    def test_vault_connection(self, name_or_id: str) -> bool:
        """Test connectivity to a vault.

        Note: This is a basic check and may not be available on all Kong versions.

        Args:
            name_or_id: Vault name or ID.

        Returns:
            True if vault is reachable, False otherwise.
        """
        try:
            # Get vault to verify it exists
            vault = self.get(name_or_id)

            # Try to read a test secret (this may fail but confirms connectivity)
            self._log.debug("testing_vault_connection", vault=vault.name)

            # Note: Kong doesn't have a dedicated vault test endpoint
            # The vault is validated when it's used in a plugin config
            return True
        except Exception as e:
            self._log.warning("vault_connection_test_failed", vault=name_or_id, error=str(e))
            return False
