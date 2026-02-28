"""Unit tests for Kong vault commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.exceptions import KongNotFoundError
from system_operations_manager.plugins.kong.commands.enterprise.vaults import (
    register_vault_commands,
)

from .conftest import create_enterprise_app


class TestVaultListCommand:
    """Tests for vault list command."""

    @pytest.fixture
    def app(self, get_vault_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with vault commands."""
        return create_enterprise_app(register_vault_commands, get_vault_manager)

    @pytest.mark.unit
    def test_list_vaults_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_vault_manager: MagicMock,
    ) -> None:
        """list should display vaults."""
        result = cli_runner.invoke(app, ["vaults", "list"])

        assert result.exit_code == 0
        assert "hcv-prod" in result.output
        mock_vault_manager.list.assert_called_once()

    @pytest.mark.unit
    def test_list_vaults_empty(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_vault_manager: MagicMock,
    ) -> None:
        """list should handle empty results."""
        mock_vault_manager.list.return_value = ([], None)

        result = cli_runner.invoke(app, ["vaults", "list"])

        assert result.exit_code == 0
        assert "No vaults configured" in result.output


class TestVaultGetCommand:
    """Tests for vault get command."""

    @pytest.fixture
    def app(self, get_vault_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with vault commands."""
        return create_enterprise_app(register_vault_commands, get_vault_manager)

    @pytest.mark.unit
    def test_get_vault_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_vault_manager: MagicMock,
    ) -> None:
        """get should display vault details."""
        result = cli_runner.invoke(app, ["vaults", "get", "hcv-prod"])

        assert result.exit_code == 0
        assert "hcv-prod" in result.output
        mock_vault_manager.get.assert_called_once_with("hcv-prod")

    @pytest.mark.unit
    def test_get_vault_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_vault_manager: MagicMock,
    ) -> None:
        """get should handle not found error."""
        mock_vault_manager.get.side_effect = KongNotFoundError(
            resource_type="vault", resource_id="nonexistent"
        )

        result = cli_runner.invoke(app, ["vaults", "get", "nonexistent"])

        assert result.exit_code == 1


class TestVaultDeleteCommand:
    """Tests for vault delete command."""

    @pytest.fixture
    def app(self, get_vault_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with vault commands."""
        return create_enterprise_app(register_vault_commands, get_vault_manager)

    @pytest.mark.unit
    def test_delete_vault_with_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_vault_manager: MagicMock,
    ) -> None:
        """delete should skip confirmation with --force."""
        result = cli_runner.invoke(app, ["vaults", "delete", "hcv-prod", "--force"])

        assert result.exit_code == 0
        assert "deleted" in result.output
        mock_vault_manager.delete.assert_called_once_with("hcv-prod")

    @pytest.mark.unit
    def test_delete_vault_cancelled(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_vault_manager: MagicMock,
    ) -> None:
        """delete should cancel when user declines."""
        result = cli_runner.invoke(app, ["vaults", "delete", "hcv-prod"], input="n\n")

        assert result.exit_code == 0
        assert "Cancelled" in result.output


class TestVaultConfigureHCVCommand:
    """Tests for vault configure hcv command."""

    @pytest.fixture
    def app(self, get_vault_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with vault commands."""
        return create_enterprise_app(register_vault_commands, get_vault_manager)

    @pytest.mark.unit
    def test_configure_hcv_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_vault_manager: MagicMock,
    ) -> None:
        """configure hcv should create HashiCorp Vault."""
        result = cli_runner.invoke(
            app, ["vaults", "configure", "hcv", "my-hcv", "--host", "vault.example.com"]
        )

        assert result.exit_code == 0
        assert "configured" in result.output
        mock_vault_manager.configure_hcv.assert_called_once()


class TestVaultConfigureAWSCommand:
    """Tests for vault configure aws command."""

    @pytest.fixture
    def app(self, get_vault_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with vault commands."""
        return create_enterprise_app(register_vault_commands, get_vault_manager)

    @pytest.mark.unit
    def test_configure_aws_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_vault_manager: MagicMock,
    ) -> None:
        """configure aws should create AWS Secrets Manager vault."""
        result = cli_runner.invoke(
            app, ["vaults", "configure", "aws", "my-aws", "--region", "us-east-1"]
        )

        assert result.exit_code == 0
        assert "configured" in result.output
        mock_vault_manager.configure_aws.assert_called_once()


class TestVaultConfigureGCPCommand:
    """Tests for vault configure gcp command."""

    @pytest.fixture
    def app(self, get_vault_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with vault commands."""
        return create_enterprise_app(register_vault_commands, get_vault_manager)

    @pytest.mark.unit
    def test_configure_gcp_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_vault_manager: MagicMock,
    ) -> None:
        """configure gcp should create GCP Secret Manager vault."""
        result = cli_runner.invoke(
            app, ["vaults", "configure", "gcp", "my-gcp", "--project-id", "my-project"]
        )

        assert result.exit_code == 0
        assert "configured" in result.output
        mock_vault_manager.configure_gcp.assert_called_once()


class TestVaultConfigureAzureCommand:
    """Tests for vault configure azure command."""

    @pytest.fixture
    def app(self, get_vault_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with vault commands."""
        return create_enterprise_app(register_vault_commands, get_vault_manager)

    @pytest.mark.unit
    def test_configure_azure_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_vault_manager: MagicMock,
    ) -> None:
        """configure azure should create Azure Key Vault."""
        result = cli_runner.invoke(
            app,
            [
                "vaults",
                "configure",
                "azure",
                "my-azure",
                "--vault-uri",
                "https://myvault.vault.azure.net",
            ],
        )

        assert result.exit_code == 0
        assert "configured" in result.output
        mock_vault_manager.configure_azure.assert_called_once()


class TestVaultConfigureEnvCommand:
    """Tests for vault configure env command."""

    @pytest.fixture
    def app(self, get_vault_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with vault commands."""
        return create_enterprise_app(register_vault_commands, get_vault_manager)

    @pytest.mark.unit
    def test_configure_env_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_vault_manager: MagicMock,
    ) -> None:
        """configure env should create environment vault."""
        result = cli_runner.invoke(app, ["vaults", "configure", "env", "my-env"])

        assert result.exit_code == 0
        assert "configured" in result.output
        mock_vault_manager.configure_env.assert_called_once()

    @pytest.mark.unit
    def test_configure_env_with_prefix(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_vault_manager: MagicMock,
    ) -> None:
        """configure env should pass prefix option."""
        result = cli_runner.invoke(
            app, ["vaults", "configure", "env", "my-env", "--env-prefix", "KONG_SECRET_"]
        )

        assert result.exit_code == 0
        mock_vault_manager.configure_env.assert_called_once()


class TestVaultListCommandError:
    """Tests for KongAPIError handling in vault list command."""

    @pytest.fixture
    def app(self, get_vault_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with vault commands."""
        return create_enterprise_app(register_vault_commands, get_vault_manager)

    @pytest.mark.unit
    def test_list_vaults_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_vault_manager: MagicMock,
    ) -> None:
        """list should handle KongAPIError gracefully."""
        from system_operations_manager.integrations.kong.exceptions import KongAPIError

        mock_vault_manager.list.side_effect = KongAPIError("Connection failed", status_code=500)

        result = cli_runner.invoke(app, ["vaults", "list"])

        assert result.exit_code == 1
        assert "error" in result.output.lower()


class TestVaultDeleteCommandError:
    """Tests for KongAPIError handling in vault delete command."""

    @pytest.fixture
    def app(self, get_vault_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with vault commands."""
        return create_enterprise_app(register_vault_commands, get_vault_manager)

    @pytest.mark.unit
    def test_delete_vault_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_vault_manager: MagicMock,
    ) -> None:
        """delete should handle KongAPIError gracefully."""
        from system_operations_manager.integrations.kong.exceptions import KongAPIError

        mock_vault_manager.get.side_effect = KongAPIError("Not found", status_code=404)

        result = cli_runner.invoke(app, ["vaults", "delete", "nonexistent", "--force"])

        assert result.exit_code == 1
        assert "error" in result.output.lower()


class TestVaultConfigureHCVCommandError:
    """Tests for KongAPIError handling in vault configure hcv command."""

    @pytest.fixture
    def app(self, get_vault_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with vault commands."""
        return create_enterprise_app(register_vault_commands, get_vault_manager)

    @pytest.mark.unit
    def test_configure_hcv_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_vault_manager: MagicMock,
    ) -> None:
        """configure hcv should handle KongAPIError gracefully."""
        from system_operations_manager.integrations.kong.exceptions import KongAPIError

        mock_vault_manager.configure_hcv.side_effect = KongAPIError("Bad request", status_code=400)

        result = cli_runner.invoke(
            app, ["vaults", "configure", "hcv", "bad-hcv", "--host", "vault.example.com"]
        )

        assert result.exit_code == 1
        assert "error" in result.output.lower()


class TestVaultConfigureAWSCommandError:
    """Tests for KongAPIError handling in vault configure aws command."""

    @pytest.fixture
    def app(self, get_vault_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with vault commands."""
        return create_enterprise_app(register_vault_commands, get_vault_manager)

    @pytest.mark.unit
    def test_configure_aws_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_vault_manager: MagicMock,
    ) -> None:
        """configure aws should handle KongAPIError gracefully."""
        from system_operations_manager.integrations.kong.exceptions import KongAPIError

        mock_vault_manager.configure_aws.side_effect = KongAPIError("Bad request", status_code=400)

        result = cli_runner.invoke(
            app, ["vaults", "configure", "aws", "bad-aws", "--region", "us-east-1"]
        )

        assert result.exit_code == 1
        assert "error" in result.output.lower()


class TestVaultConfigureGCPCommandError:
    """Tests for KongAPIError handling in vault configure gcp command."""

    @pytest.fixture
    def app(self, get_vault_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with vault commands."""
        return create_enterprise_app(register_vault_commands, get_vault_manager)

    @pytest.mark.unit
    def test_configure_gcp_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_vault_manager: MagicMock,
    ) -> None:
        """configure gcp should handle KongAPIError gracefully."""
        from system_operations_manager.integrations.kong.exceptions import KongAPIError

        mock_vault_manager.configure_gcp.side_effect = KongAPIError("Bad request", status_code=400)

        result = cli_runner.invoke(
            app, ["vaults", "configure", "gcp", "bad-gcp", "--project-id", "bad-project"]
        )

        assert result.exit_code == 1
        assert "error" in result.output.lower()


class TestVaultConfigureAzureCommandError:
    """Tests for KongAPIError handling in vault configure azure command."""

    @pytest.fixture
    def app(self, get_vault_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with vault commands."""
        return create_enterprise_app(register_vault_commands, get_vault_manager)

    @pytest.mark.unit
    def test_configure_azure_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_vault_manager: MagicMock,
    ) -> None:
        """configure azure should handle KongAPIError gracefully."""
        from system_operations_manager.integrations.kong.exceptions import KongAPIError

        mock_vault_manager.configure_azure.side_effect = KongAPIError(
            "Bad request", status_code=400
        )

        result = cli_runner.invoke(
            app,
            [
                "vaults",
                "configure",
                "azure",
                "bad-azure",
                "--vault-uri",
                "https://myvault.vault.azure.net",
            ],
        )

        assert result.exit_code == 1
        assert "error" in result.output.lower()


class TestVaultConfigureEnvCommandError:
    """Tests for KongAPIError handling in vault configure env command."""

    @pytest.fixture
    def app(self, get_vault_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create app with vault commands."""
        return create_enterprise_app(register_vault_commands, get_vault_manager)

    @pytest.mark.unit
    def test_configure_env_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_vault_manager: MagicMock,
    ) -> None:
        """configure env should handle KongAPIError gracefully."""
        from system_operations_manager.integrations.kong.exceptions import KongAPIError

        mock_vault_manager.configure_env.side_effect = KongAPIError("Bad request", status_code=400)

        result = cli_runner.invoke(app, ["vaults", "configure", "env", "bad-env"])

        assert result.exit_code == 1
        assert "error" in result.output.lower()
