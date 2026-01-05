"""Unit tests for Kong VaultManager."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kong.exceptions import KongNotFoundError
from system_operations_manager.integrations.kong.models.enterprise import (
    AWSSecretsConfig,
    AzureVaultConfig,
    EnvVaultConfig,
    GCPSecretsConfig,
    HashiCorpVaultConfig,
    Vault,
)
from system_operations_manager.services.kong.vault_manager import VaultManager


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock Kong Admin client."""
    return MagicMock()


@pytest.fixture
def manager(mock_client: MagicMock) -> VaultManager:
    """Create a VaultManager with mocked client."""
    return VaultManager(mock_client)


class TestVaultManagerInit:
    """Tests for VaultManager initialization."""

    @pytest.mark.unit
    def test_vault_manager_initialization(self, mock_client: MagicMock) -> None:
        """Manager should initialize with client."""
        manager = VaultManager(mock_client)

        assert manager._client is mock_client
        assert manager._endpoint == "vaults"
        assert manager._entity_name == "vault"


class TestVaultManagerConfigureHCV:
    """Tests for configure_hcv method."""

    @pytest.mark.unit
    def test_configure_hcv_basic(self, manager: VaultManager, mock_client: MagicMock) -> None:
        """configure_hcv should create HashiCorp Vault."""
        mock_client.post.return_value = {
            "id": "vault-1",
            "name": "hcv-prod",
            "prefix": "hcv-prod",
            "config": {
                "host": "vault.example.com",
                "port": 8200,
                "protocol": "https",
                "mount": "secret",
                "kv": "v2",
                "auth_method": "token",
            },
        }

        config = HashiCorpVaultConfig(
            host="vault.example.com",
            mount="secret",
        )
        vault = manager.configure_hcv("hcv-prod", config)

        assert vault.name == "hcv-prod"
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "vaults"
        assert call_args[1]["json"]["name"] == "hcv-prod"

    @pytest.mark.unit
    def test_configure_hcv_with_token(self, manager: VaultManager, mock_client: MagicMock) -> None:
        """configure_hcv should include token when provided."""
        mock_client.post.return_value = {
            "id": "vault-1",
            "name": "hcv-prod",
            "prefix": "hcv-prod",
            "config": {"host": "vault.example.com", "mount": "secret", "token": "s.xxx"},
        }

        config = HashiCorpVaultConfig(
            host="vault.example.com",
            mount="secret",
            token="s.xxx",
        )
        manager.configure_hcv("hcv-prod", config)

        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["config"]["token"] == "s.xxx"

    @pytest.mark.unit
    def test_configure_hcv_with_namespace(
        self, manager: VaultManager, mock_client: MagicMock
    ) -> None:
        """configure_hcv should include namespace when provided."""
        mock_client.post.return_value = {
            "id": "vault-1",
            "name": "hcv-prod",
            "prefix": "hcv-prod",
            "config": {"host": "vault.example.com", "mount": "secret", "namespace": "admin"},
        }

        config = HashiCorpVaultConfig(
            host="vault.example.com",
            mount="secret",
            namespace="admin",
        )
        manager.configure_hcv("hcv-prod", config)

        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["config"]["namespace"] == "admin"

    @pytest.mark.unit
    def test_configure_hcv_custom_prefix(
        self, manager: VaultManager, mock_client: MagicMock
    ) -> None:
        """configure_hcv should use custom prefix when provided."""
        mock_client.post.return_value = {
            "id": "vault-1",
            "name": "hcv-prod",
            "prefix": "custom-prefix",
            "config": {"host": "vault.example.com", "mount": "secret"},
        }

        config = HashiCorpVaultConfig(host="vault.example.com", mount="secret")
        manager.configure_hcv("hcv-prod", config, prefix="custom-prefix")

        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["prefix"] == "custom-prefix"


class TestVaultManagerConfigureAWS:
    """Tests for configure_aws method."""

    @pytest.mark.unit
    def test_configure_aws_basic(self, manager: VaultManager, mock_client: MagicMock) -> None:
        """configure_aws should create AWS Secrets Manager vault."""
        mock_client.post.return_value = {
            "id": "vault-1",
            "name": "aws-secrets",
            "prefix": "aws-secrets",
            "config": {"region": "us-east-1"},
        }

        config = AWSSecretsConfig(region="us-east-1")
        vault = manager.configure_aws("aws-secrets", config)

        assert vault.name == "aws-secrets"
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["config"]["region"] == "us-east-1"

    @pytest.mark.unit
    def test_configure_aws_with_role_arn(
        self, manager: VaultManager, mock_client: MagicMock
    ) -> None:
        """configure_aws should include role_arn when provided."""
        mock_client.post.return_value = {
            "id": "vault-1",
            "name": "aws-secrets",
            "prefix": "aws-secrets",
            "config": {"region": "us-east-1", "role_arn": "arn:aws:iam::123456789:role/vault"},
        }

        config = AWSSecretsConfig(
            region="us-east-1",
            role_arn="arn:aws:iam::123456789:role/vault",
        )
        manager.configure_aws("aws-secrets", config)

        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["config"]["role_arn"] == "arn:aws:iam::123456789:role/vault"

    @pytest.mark.unit
    def test_configure_aws_with_endpoint(
        self, manager: VaultManager, mock_client: MagicMock
    ) -> None:
        """configure_aws should include endpoint_url when provided."""
        mock_client.post.return_value = {
            "id": "vault-1",
            "name": "aws-secrets",
            "prefix": "aws-secrets",
            "config": {"region": "us-east-1", "endpoint_url": "http://localhost:4566"},
        }

        config = AWSSecretsConfig(
            region="us-east-1",
            endpoint_url="http://localhost:4566",
        )
        manager.configure_aws("aws-secrets", config)

        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["config"]["endpoint_url"] == "http://localhost:4566"


class TestVaultManagerConfigureGCP:
    """Tests for configure_gcp method."""

    @pytest.mark.unit
    def test_configure_gcp_basic(self, manager: VaultManager, mock_client: MagicMock) -> None:
        """configure_gcp should create GCP Secret Manager vault."""
        mock_client.post.return_value = {
            "id": "vault-1",
            "name": "gcp-secrets",
            "prefix": "gcp-secrets",
            "config": {"project_id": "my-project"},
        }

        config = GCPSecretsConfig(project_id="my-project")
        vault = manager.configure_gcp("gcp-secrets", config)

        assert vault.name == "gcp-secrets"
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["config"]["project_id"] == "my-project"

    @pytest.mark.unit
    def test_configure_gcp_with_description(
        self, manager: VaultManager, mock_client: MagicMock
    ) -> None:
        """configure_gcp should include description when provided."""
        mock_client.post.return_value = {
            "id": "vault-1",
            "name": "gcp-secrets",
            "prefix": "gcp-secrets",
            "description": "Production GCP secrets",
            "config": {"project_id": "my-project"},
        }

        config = GCPSecretsConfig(project_id="my-project")
        manager.configure_gcp("gcp-secrets", config, description="Production GCP secrets")

        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["description"] == "Production GCP secrets"


class TestVaultManagerConfigureAzure:
    """Tests for configure_azure method."""

    @pytest.mark.unit
    def test_configure_azure_basic(self, manager: VaultManager, mock_client: MagicMock) -> None:
        """configure_azure should create Azure Key Vault."""
        mock_client.post.return_value = {
            "id": "vault-1",
            "name": "azure-kv",
            "prefix": "azure-kv",
            "config": {"vault_uri": "https://myvault.vault.azure.net"},
        }

        config = AzureVaultConfig(vault_uri="https://myvault.vault.azure.net")
        vault = manager.configure_azure("azure-kv", config)

        assert vault.name == "azure-kv"
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["config"]["vault_uri"] == "https://myvault.vault.azure.net"

    @pytest.mark.unit
    def test_configure_azure_with_client_id(
        self, manager: VaultManager, mock_client: MagicMock
    ) -> None:
        """configure_azure should include client_id when provided."""
        mock_client.post.return_value = {
            "id": "vault-1",
            "name": "azure-kv",
            "prefix": "azure-kv",
            "config": {
                "vault_uri": "https://myvault.vault.azure.net",
                "client_id": "client-123",
            },
        }

        config = AzureVaultConfig(
            vault_uri="https://myvault.vault.azure.net",
            client_id="client-123",
        )
        manager.configure_azure("azure-kv", config)

        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["config"]["client_id"] == "client-123"

    @pytest.mark.unit
    def test_configure_azure_with_tenant_id(
        self, manager: VaultManager, mock_client: MagicMock
    ) -> None:
        """configure_azure should include tenant_id when provided."""
        mock_client.post.return_value = {
            "id": "vault-1",
            "name": "azure-kv",
            "prefix": "azure-kv",
            "config": {
                "vault_uri": "https://myvault.vault.azure.net",
                "tenant_id": "tenant-456",
            },
        }

        config = AzureVaultConfig(
            vault_uri="https://myvault.vault.azure.net",
            tenant_id="tenant-456",
        )
        manager.configure_azure("azure-kv", config)

        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["config"]["tenant_id"] == "tenant-456"


class TestVaultManagerConfigureEnv:
    """Tests for configure_env method."""

    @pytest.mark.unit
    def test_configure_env_basic(self, manager: VaultManager, mock_client: MagicMock) -> None:
        """configure_env should create environment variable vault."""
        mock_client.post.return_value = {
            "id": "vault-1",
            "name": "env-secrets",
            "prefix": "env-secrets",
            "config": {"prefix": "KONG_SECRET_"},
        }

        config = EnvVaultConfig(prefix="KONG_SECRET_")
        vault = manager.configure_env("env-secrets", config)

        assert vault.name == "env-secrets"
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["config"]["prefix"] == "KONG_SECRET_"


class TestVaultManagerGetVaultType:
    """Tests for get_vault_type method."""

    @pytest.mark.unit
    def test_get_vault_type_hcv(self, manager: VaultManager) -> None:
        """get_vault_type should identify HashiCorp Vault."""
        vault = Vault(
            name="hcv",
            prefix="hcv",
            config={"host": "vault.example.com", "mount": "secret"},
        )

        result = manager.get_vault_type(vault)

        assert result == "hcv"

    @pytest.mark.unit
    def test_get_vault_type_hcv_with_kv(self, manager: VaultManager) -> None:
        """get_vault_type should identify HCV with kv field."""
        vault = Vault(
            name="hcv",
            prefix="hcv",
            config={"host": "vault.example.com", "kv": "v2"},
        )

        result = manager.get_vault_type(vault)

        assert result == "hcv"

    @pytest.mark.unit
    def test_get_vault_type_aws(self, manager: VaultManager) -> None:
        """get_vault_type should identify AWS Secrets Manager."""
        vault = Vault(
            name="aws",
            prefix="aws",
            config={"region": "us-east-1"},
        )

        result = manager.get_vault_type(vault)

        assert result == "aws"

    @pytest.mark.unit
    def test_get_vault_type_gcp(self, manager: VaultManager) -> None:
        """get_vault_type should identify GCP Secret Manager."""
        vault = Vault(
            name="gcp",
            prefix="gcp",
            config={"project_id": "my-project"},
        )

        result = manager.get_vault_type(vault)

        assert result == "gcp"

    @pytest.mark.unit
    def test_get_vault_type_azure(self, manager: VaultManager) -> None:
        """get_vault_type should identify Azure Key Vault."""
        vault = Vault(
            name="azure",
            prefix="azure",
            config={"vault_uri": "https://myvault.vault.azure.net"},
        )

        result = manager.get_vault_type(vault)

        assert result == "azure"

    @pytest.mark.unit
    def test_get_vault_type_env(self, manager: VaultManager) -> None:
        """get_vault_type should identify environment vault."""
        vault = Vault(
            name="env",
            prefix="env",
            config={"prefix": "KONG_SECRET_"},
        )

        result = manager.get_vault_type(vault)

        assert result == "env"

    @pytest.mark.unit
    def test_get_vault_type_unknown(self, manager: VaultManager) -> None:
        """get_vault_type should return unknown for unrecognized config."""
        vault = Vault(
            name="custom",
            prefix="custom",
            config={"some_key": "some_value", "another_key": "another_value"},
        )

        result = manager.get_vault_type(vault)

        assert result == "unknown"


class TestVaultManagerTestConnection:
    """Tests for test_vault_connection method."""

    @pytest.mark.unit
    def test_vault_connection_success(self, manager: VaultManager, mock_client: MagicMock) -> None:
        """test_vault_connection should return True when vault exists."""
        mock_client.get.return_value = {
            "id": "vault-1",
            "name": "hcv-prod",
            "prefix": "hcv-prod",
            "config": {"host": "vault.example.com"},
        }

        result = manager.test_vault_connection("hcv-prod")

        assert result is True
        mock_client.get.assert_called_once_with("vaults/hcv-prod")

    @pytest.mark.unit
    def test_vault_connection_not_found(
        self, manager: VaultManager, mock_client: MagicMock
    ) -> None:
        """test_vault_connection should return False when vault not found."""
        mock_client.get.side_effect = KongNotFoundError(
            resource_type="vault", resource_id="nonexistent"
        )

        result = manager.test_vault_connection("nonexistent")

        assert result is False

    @pytest.mark.unit
    def test_vault_connection_error(self, manager: VaultManager, mock_client: MagicMock) -> None:
        """test_vault_connection should return False on any error."""
        mock_client.get.side_effect = Exception("Connection error")

        result = manager.test_vault_connection("hcv-prod")

        assert result is False


class TestVaultManagerCRUD:
    """Tests for CRUD operations inherited from BaseEntityManager."""

    @pytest.mark.unit
    def test_list_vaults(self, manager: VaultManager, mock_client: MagicMock) -> None:
        """list should return vaults."""
        mock_client.get.return_value = {
            "data": [
                {"id": "vault-1", "name": "hcv-prod", "prefix": "hcv", "config": {}},
                {"id": "vault-2", "name": "aws-secrets", "prefix": "aws", "config": {}},
            ]
        }

        vaults, _offset = manager.list()

        assert len(vaults) == 2
        assert vaults[0].name == "hcv-prod"
        assert vaults[1].name == "aws-secrets"

    @pytest.mark.unit
    def test_get_vault(self, manager: VaultManager, mock_client: MagicMock) -> None:
        """get should return vault by name."""
        mock_client.get.return_value = {
            "id": "vault-1",
            "name": "hcv-prod",
            "prefix": "hcv-prod",
            "config": {"host": "vault.example.com"},
        }

        vault = manager.get("hcv-prod")

        assert vault.name == "hcv-prod"
        mock_client.get.assert_called_once_with("vaults/hcv-prod")

    @pytest.mark.unit
    def test_delete_vault(self, manager: VaultManager, mock_client: MagicMock) -> None:
        """delete should remove vault."""
        manager.delete("hcv-prod")

        mock_client.delete.assert_called_once_with("vaults/hcv-prod")
