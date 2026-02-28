"""Tests for cert-manager command error paths and helper functions.

Covers:
- _parse_labels valid and invalid input
- _parse_issuer_config invalid JSON and non-dict JSON
- KubernetesError handling in every command
- delete abort paths (confirm_delete returns False)
- renew_certificate "not renewed" path
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import click
import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesError,
    KubernetesNotFoundError,
)
from system_operations_manager.plugins.kubernetes.commands.certs import (
    _parse_labels,
    register_certs_commands,
)

# =============================================================================
# Helper function tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestParseLabels:
    """Tests for the _parse_labels helper function."""

    def test_returns_none_for_none_input(self) -> None:
        """_parse_labels should return None when given None."""
        result = _parse_labels(None)
        assert result is None

    def test_returns_none_for_empty_list(self) -> None:
        """_parse_labels should return None when given an empty list."""
        result = _parse_labels([])
        assert result is None

    def test_parses_single_label(self) -> None:
        """_parse_labels should parse a single key=value label."""
        result = _parse_labels(["app=myapp"])
        assert result == {"app": "myapp"}

    def test_parses_multiple_labels(self) -> None:
        """_parse_labels should parse multiple key=value labels."""
        result = _parse_labels(["app=myapp", "env=production"])
        assert result == {"app": "myapp", "env": "production"}

    def test_parses_label_with_empty_value(self) -> None:
        """_parse_labels should parse a label with an empty value."""
        result = _parse_labels(["key="])
        assert result == {"key": ""}

    def test_invalid_label_raises_exit(self) -> None:
        """_parse_labels should raise click.exceptions.Exit for labels without '='."""
        with pytest.raises(click.exceptions.Exit):
            _parse_labels(["invalid-label"])

    def test_invalid_label_exits_with_code_1(self) -> None:
        """_parse_labels exit code should be 1 for invalid label format."""
        with pytest.raises(click.exceptions.Exit) as exc_info:
            _parse_labels(["noequalssign"])
        assert exc_info.value.exit_code == 1


@pytest.mark.unit
@pytest.mark.kubernetes
class TestParseIssuerConfig:
    """Tests for _parse_issuer_config via CLI commands."""

    @pytest.fixture
    def app(self, get_certmanager_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with certs commands."""
        app = typer.Typer()
        register_certs_commands(app, get_certmanager_manager)
        return app

    def test_invalid_json_exits(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """create issuer with invalid JSON config should exit with error."""
        result = cli_runner.invoke(
            app,
            [
                "certs",
                "issuer",
                "create",
                "my-issuer",
                "--type",
                "ca",
                "--config",
                "not-valid-json",
            ],
        )
        assert result.exit_code != 0

    def test_non_dict_json_exits(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """create issuer with JSON array config should exit with error."""
        result = cli_runner.invoke(
            app,
            [
                "certs",
                "issuer",
                "create",
                "my-issuer",
                "--type",
                "ca",
                "--config",
                '["not", "a", "dict"]',
            ],
        )
        assert result.exit_code != 0

    def test_invalid_json_clusterissuer_exits(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """create clusterissuer with invalid JSON config should exit with error."""
        result = cli_runner.invoke(
            app,
            [
                "certs",
                "clusterissuer",
                "create",
                "my-ci",
                "--type",
                "ca",
                "--config",
                "{bad json}",
            ],
        )
        assert result.exit_code != 0

    def test_non_dict_json_clusterissuer_exits(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """create clusterissuer with JSON array config should exit with error."""
        result = cli_runner.invoke(
            app,
            [
                "certs",
                "clusterissuer",
                "create",
                "my-ci",
                "--type",
                "ca",
                "--config",
                "[1, 2, 3]",
            ],
        )
        assert result.exit_code != 0


# =============================================================================
# KubernetesError handling for Certificate commands
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestCertificateCommandErrors:
    """Tests for KubernetesError handling in Certificate commands."""

    @pytest.fixture
    def app(self, get_certmanager_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with certs commands."""
        app = typer.Typer()
        register_certs_commands(app, get_certmanager_manager)
        return app

    def test_list_certificates_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """list certificates should handle KubernetesError."""
        mock_certmanager_manager.list_certificates.side_effect = KubernetesError("failed to list")
        result = cli_runner.invoke(app, ["certs", "cert", "list"])
        assert result.exit_code == 1

    def test_get_certificate_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """get certificate should handle KubernetesError."""
        mock_certmanager_manager.get_certificate.side_effect = KubernetesNotFoundError(
            resource_type="Certificate", resource_name="missing"
        )
        result = cli_runner.invoke(app, ["certs", "cert", "get", "missing"])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_create_certificate_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """create certificate should handle KubernetesError."""
        mock_certmanager_manager.create_certificate.side_effect = KubernetesError("create failed")
        result = cli_runner.invoke(
            app,
            [
                "certs",
                "cert",
                "create",
                "my-tls",
                "--secret-name",
                "secret",
                "--issuer-name",
                "issuer",
                "--dns-name",
                "example.com",
            ],
        )
        assert result.exit_code == 1

    def test_delete_certificate_abort_when_not_confirmed(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """delete certificate should abort when user does not confirm."""
        cli_runner.invoke(app, ["certs", "cert", "delete", "my-tls"], input="n\n")
        mock_certmanager_manager.delete_certificate.assert_not_called()

    def test_delete_certificate_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """delete certificate should handle KubernetesError."""
        mock_certmanager_manager.delete_certificate.side_effect = KubernetesError("delete failed")
        result = cli_runner.invoke(app, ["certs", "cert", "delete", "my-tls", "--force"])
        assert result.exit_code == 1

    def test_certificate_status_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """status should handle KubernetesError."""
        mock_certmanager_manager.get_certificate_status.side_effect = KubernetesError(
            "status failed"
        )
        result = cli_runner.invoke(app, ["certs", "cert", "status", "my-tls"])
        assert result.exit_code == 1

    def test_renew_certificate_not_renewed_message(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """renew should show 'may not have been triggered' when renewed is False."""
        mock_certmanager_manager.renew_certificate.return_value = {
            "name": "my-tls",
            "namespace": "default",
            "renewed": False,
        }
        result = cli_runner.invoke(app, ["certs", "cert", "renew", "my-tls"])
        assert result.exit_code == 0
        assert "may not have been triggered" in result.stdout.lower()

    def test_renew_certificate_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """renew should handle KubernetesError."""
        mock_certmanager_manager.renew_certificate.side_effect = KubernetesError("renew failed")
        result = cli_runner.invoke(app, ["certs", "cert", "renew", "my-tls"])
        assert result.exit_code == 1


# =============================================================================
# KubernetesError handling for Issuer commands
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestIssuerCommandErrors:
    """Tests for KubernetesError handling in Issuer commands."""

    @pytest.fixture
    def app(self, get_certmanager_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with certs commands."""
        app = typer.Typer()
        register_certs_commands(app, get_certmanager_manager)
        return app

    def test_list_issuers_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """list issuers should handle KubernetesError."""
        mock_certmanager_manager.list_issuers.side_effect = KubernetesError("list failed")
        result = cli_runner.invoke(app, ["certs", "issuer", "list"])
        assert result.exit_code == 1

    def test_get_issuer_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """get issuer should handle KubernetesError."""
        mock_certmanager_manager.get_issuer.side_effect = KubernetesNotFoundError(
            resource_type="Issuer", resource_name="missing"
        )
        result = cli_runner.invoke(app, ["certs", "issuer", "get", "missing"])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_create_issuer_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """create issuer should handle KubernetesError."""
        mock_certmanager_manager.create_issuer.side_effect = KubernetesError("create failed")
        result = cli_runner.invoke(
            app,
            [
                "certs",
                "issuer",
                "create",
                "my-issuer",
                "--type",
                "selfSigned",
                "--config",
                "{}",
            ],
        )
        assert result.exit_code == 1

    def test_delete_issuer_abort_when_not_confirmed(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """delete issuer should abort when user does not confirm."""
        cli_runner.invoke(app, ["certs", "issuer", "delete", "letsencrypt-staging"], input="n\n")
        mock_certmanager_manager.delete_issuer.assert_not_called()

    def test_delete_issuer_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """delete issuer should handle KubernetesError."""
        mock_certmanager_manager.delete_issuer.side_effect = KubernetesError("delete failed")
        result = cli_runner.invoke(
            app, ["certs", "issuer", "delete", "letsencrypt-staging", "--force"]
        )
        assert result.exit_code == 1

    def test_issuer_status_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """issuer status should handle KubernetesError."""
        mock_certmanager_manager.get_issuer_status.side_effect = KubernetesError("status failed")
        result = cli_runner.invoke(app, ["certs", "issuer", "status", "letsencrypt-staging"])
        assert result.exit_code == 1


# =============================================================================
# KubernetesError handling for ClusterIssuer commands
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestClusterIssuerCommandErrors:
    """Tests for KubernetesError handling in ClusterIssuer commands."""

    @pytest.fixture
    def app(self, get_certmanager_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with certs commands."""
        app = typer.Typer()
        register_certs_commands(app, get_certmanager_manager)
        return app

    def test_list_cluster_issuers_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """list cluster issuers should handle KubernetesError."""
        mock_certmanager_manager.list_cluster_issuers.side_effect = KubernetesError("list failed")
        result = cli_runner.invoke(app, ["certs", "clusterissuer", "list"])
        assert result.exit_code == 1

    def test_get_cluster_issuer_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """get cluster issuer should handle KubernetesError."""
        mock_certmanager_manager.get_cluster_issuer.side_effect = KubernetesNotFoundError(
            resource_type="ClusterIssuer", resource_name="missing"
        )
        result = cli_runner.invoke(app, ["certs", "clusterissuer", "get", "missing"])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_create_cluster_issuer_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """create cluster issuer should handle KubernetesError."""
        mock_certmanager_manager.create_cluster_issuer.side_effect = KubernetesError(
            "create failed"
        )
        result = cli_runner.invoke(
            app,
            [
                "certs",
                "clusterissuer",
                "create",
                "my-ci",
                "--type",
                "selfSigned",
                "--config",
                "{}",
            ],
        )
        assert result.exit_code == 1

    def test_delete_cluster_issuer_abort_when_not_confirmed(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """delete cluster issuer should abort when user does not confirm."""
        cli_runner.invoke(
            app, ["certs", "clusterissuer", "delete", "letsencrypt-prod"], input="n\n"
        )
        mock_certmanager_manager.delete_cluster_issuer.assert_not_called()

    def test_delete_cluster_issuer_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """delete cluster issuer should handle KubernetesError."""
        mock_certmanager_manager.delete_cluster_issuer.side_effect = KubernetesError(
            "delete failed"
        )
        result = cli_runner.invoke(
            app, ["certs", "clusterissuer", "delete", "letsencrypt-prod", "--force"]
        )
        assert result.exit_code == 1

    def test_cluster_issuer_status_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """cluster issuer status should handle KubernetesError."""
        mock_certmanager_manager.get_cluster_issuer_status.side_effect = KubernetesError(
            "status failed"
        )
        result = cli_runner.invoke(app, ["certs", "clusterissuer", "status", "letsencrypt-prod"])
        assert result.exit_code == 1


# =============================================================================
# KubernetesError handling for ACME commands
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestACMECommandErrors:
    """Tests for KubernetesError handling in ACME commands."""

    @pytest.fixture
    def app(self, get_certmanager_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with certs commands."""
        app = typer.Typer()
        register_certs_commands(app, get_certmanager_manager)
        return app

    def test_create_acme_issuer_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """create-issuer should handle KubernetesError."""
        mock_certmanager_manager.create_acme_issuer.side_effect = KubernetesError("create failed")
        result = cli_runner.invoke(
            app,
            [
                "certs",
                "acme",
                "create-issuer",
                "letsencrypt-staging",
                "--email",
                "admin@example.com",
            ],
        )
        assert result.exit_code == 1

    def test_create_acme_cluster_issuer_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """create-clusterissuer should handle KubernetesError."""
        mock_certmanager_manager.create_acme_cluster_issuer.side_effect = KubernetesError(
            "create failed"
        )
        result = cli_runner.invoke(
            app,
            [
                "certs",
                "acme",
                "create-clusterissuer",
                "letsencrypt-prod",
                "--email",
                "admin@example.com",
                "--production",
            ],
        )
        assert result.exit_code == 1


# =============================================================================
# KubernetesError handling for CertificateRequest commands
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestCertificateRequestCommandErrors:
    """Tests for KubernetesError handling in CertificateRequest commands."""

    @pytest.fixture
    def app(self, get_certmanager_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with certs commands."""
        app = typer.Typer()
        register_certs_commands(app, get_certmanager_manager)
        return app

    def test_list_certificate_requests_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """list certificate requests should handle KubernetesError."""
        mock_certmanager_manager.list_certificate_requests.side_effect = KubernetesError(
            "list failed"
        )
        result = cli_runner.invoke(app, ["certs", "request", "list"])
        assert result.exit_code == 1

    def test_get_certificate_request_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """get certificate request should handle KubernetesError."""
        mock_certmanager_manager.get_certificate_request.side_effect = KubernetesNotFoundError(
            resource_type="CertificateRequest", resource_name="missing"
        )
        result = cli_runner.invoke(app, ["certs", "request", "get", "missing"])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()


# =============================================================================
# KubernetesError handling for Challenge commands
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestChallengeCommandErrors:
    """Tests for KubernetesError handling in Challenge commands."""

    @pytest.fixture
    def app(self, get_certmanager_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with certs commands."""
        app = typer.Typer()
        register_certs_commands(app, get_certmanager_manager)
        return app

    def test_list_challenges_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """list challenges should handle KubernetesError."""
        mock_certmanager_manager.list_challenges.side_effect = KubernetesError("list failed")
        result = cli_runner.invoke(app, ["certs", "challenge", "list"])
        assert result.exit_code == 1

    def test_get_challenge_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """get challenge should handle KubernetesError."""
        mock_certmanager_manager.get_challenge.side_effect = KubernetesNotFoundError(
            resource_type="Challenge", resource_name="missing"
        )
        result = cli_runner.invoke(app, ["certs", "challenge", "get", "missing"])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_troubleshoot_challenge_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """troubleshoot challenge should handle KubernetesError."""
        mock_certmanager_manager.troubleshoot_challenge.side_effect = KubernetesError(
            "troubleshoot failed"
        )
        result = cli_runner.invoke(app, ["certs", "challenge", "troubleshoot", "my-challenge"])
        assert result.exit_code == 1


# =============================================================================
# Label parsing via CLI commands (exercises _parse_labels success path)
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestLabelParsingViaCLI:
    """Tests for _parse_labels success path invoked through CLI commands."""

    @pytest.fixture
    def app(self, get_certmanager_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with certs commands."""
        app = typer.Typer()
        register_certs_commands(app, get_certmanager_manager)
        return app

    def test_create_certificate_with_labels(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """create certificate with --label should pass parsed labels."""
        result = cli_runner.invoke(
            app,
            [
                "certs",
                "cert",
                "create",
                "my-tls",
                "--secret-name",
                "secret",
                "--issuer-name",
                "issuer",
                "--dns-name",
                "example.com",
                "--label",
                "app=myapp",
                "--label",
                "env=production",
            ],
        )
        assert result.exit_code == 0
        call_kwargs: Any = mock_certmanager_manager.create_certificate.call_args
        assert call_kwargs.kwargs["labels"] == {"app": "myapp", "env": "production"}

    def test_create_issuer_with_labels(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """create issuer with --label should pass parsed labels."""
        result = cli_runner.invoke(
            app,
            [
                "certs",
                "issuer",
                "create",
                "my-issuer",
                "--type",
                "selfSigned",
                "--config",
                "{}",
                "--label",
                "tier=infra",
            ],
        )
        assert result.exit_code == 0
        call_kwargs: Any = mock_certmanager_manager.create_issuer.call_args
        assert call_kwargs.kwargs["labels"] == {"tier": "infra"}

    def test_create_cluster_issuer_with_labels(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """create clusterissuer with --label should pass parsed labels."""
        result = cli_runner.invoke(
            app,
            [
                "certs",
                "clusterissuer",
                "create",
                "my-ci",
                "--type",
                "selfSigned",
                "--config",
                "{}",
                "--label",
                "managed=true",
            ],
        )
        assert result.exit_code == 0
        call_kwargs: Any = mock_certmanager_manager.create_cluster_issuer.call_args
        assert call_kwargs.kwargs["labels"] == {"managed": "true"}

    def test_create_acme_issuer_with_labels(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """create-issuer with --label should pass parsed labels."""
        result = cli_runner.invoke(
            app,
            [
                "certs",
                "acme",
                "create-issuer",
                "le-staging",
                "--email",
                "admin@example.com",
                "--label",
                "env=staging",
            ],
        )
        assert result.exit_code == 0
        call_kwargs: Any = mock_certmanager_manager.create_acme_issuer.call_args
        assert call_kwargs.kwargs["labels"] == {"env": "staging"}

    def test_create_acme_cluster_issuer_with_labels(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_certmanager_manager: MagicMock,
    ) -> None:
        """create-clusterissuer with --label should pass parsed labels."""
        result = cli_runner.invoke(
            app,
            [
                "certs",
                "acme",
                "create-clusterissuer",
                "le-prod",
                "--email",
                "admin@example.com",
                "--production",
                "--label",
                "env=prod",
            ],
        )
        assert result.exit_code == 0
        call_kwargs: Any = mock_certmanager_manager.create_acme_cluster_issuer.call_args
        assert call_kwargs.kwargs["labels"] == {"env": "prod"}
