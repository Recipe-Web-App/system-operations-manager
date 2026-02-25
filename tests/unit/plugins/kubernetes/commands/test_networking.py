"""Unit tests for Kubernetes networking CLI commands (gap-fill coverage)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesAuthError,
    KubernetesConnectionError,
    KubernetesError,
    KubernetesNotFoundError,
    KubernetesTimeoutError,
)
from system_operations_manager.plugins.kubernetes.commands.networking import (
    _parse_labels,
    _parse_port,
    register_networking_commands,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_networking_manager() -> MagicMock:
    """Create a mock NetworkingManager."""
    manager = MagicMock()

    manager.list_services.return_value = []
    manager.get_service.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "my-svc", "namespace": "default"}
    )
    manager.create_service.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "my-svc", "namespace": "default"}
    )
    manager.update_service.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "my-svc", "namespace": "default"}
    )
    manager.delete_service.return_value = None

    manager.list_ingresses.return_value = []
    manager.get_ingress.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "my-ingress", "namespace": "default"}
    )
    manager.create_ingress.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "my-ingress", "namespace": "default"}
    )
    manager.update_ingress.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "my-ingress", "namespace": "default"}
    )
    manager.delete_ingress.return_value = None

    manager.list_network_policies.return_value = []
    manager.get_network_policy.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "deny-all", "namespace": "default"}
    )
    manager.create_network_policy.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "deny-all", "namespace": "default"}
    )
    manager.delete_network_policy.return_value = None

    return manager


@pytest.fixture
def get_networking_manager(mock_networking_manager: MagicMock) -> Callable[[], MagicMock]:
    """Factory returning the mock NetworkingManager."""
    return lambda: mock_networking_manager


@pytest.fixture
def app(get_networking_manager: Callable[[], MagicMock]) -> typer.Typer:
    """Create a test Typer app with networking commands registered."""
    test_app = typer.Typer()
    register_networking_commands(test_app, get_networking_manager)
    return test_app


# =============================================================================
# Tests for _parse_labels helper  (line 29, 77-78)
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestParseLabels:
    """Tests for the _parse_labels helper function in networking module."""

    def test_returns_none_for_none_input(self) -> None:
        """Should return None when labels is None (line 29 TYPE_CHECKING branch)."""
        result = _parse_labels(None)
        assert result is None

    def test_returns_none_for_empty_list(self) -> None:
        """Should return None when labels is an empty list."""
        result = _parse_labels([])
        assert result is None

    def test_parses_valid_labels(self) -> None:
        """Should parse valid key=value labels into a dict."""
        result = _parse_labels(["app=nginx", "env=prod"])
        assert result == {"app": "nginx", "env": "prod"}

    def test_invalid_label_format_prints_error_and_exits(self) -> None:
        """Should print error and raise typer.Exit(1) on bad label (lines 77-78)."""
        with pytest.raises(typer.Exit) as exc_info:
            _parse_labels(["invalid-label"])
        assert exc_info.value.exit_code == 1

    def test_invalid_label_no_separator_exits(self) -> None:
        """Should exit when label string has no = separator."""
        with pytest.raises(typer.Exit):
            _parse_labels(["keyonly"])


# =============================================================================
# Tests for _parse_port helper  (line 96)
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestParsePort:
    """Tests for the _parse_port helper function."""

    def test_parse_port_with_colon_and_protocol(self) -> None:
        """Should parse port:targetPort/protocol correctly."""
        result = _parse_port("80:8080/TCP")
        assert result == {"port": 80, "target_port": 8080, "protocol": "TCP"}

    def test_parse_port_with_protocol_no_colon(self) -> None:
        """Should parse port/protocol when no colon (line 96 branch)."""
        result = _parse_port("80/UDP")
        assert result == {"port": 80, "target_port": 80, "protocol": "UDP"}

    def test_parse_port_only_number(self) -> None:
        """Should parse bare port number, defaulting targetPort and TCP."""
        result = _parse_port("8080")
        assert result == {"port": 8080, "target_port": 8080, "protocol": "TCP"}

    def test_parse_port_with_colon_default_tcp(self) -> None:
        """Should default to TCP when no protocol given."""
        result = _parse_port("443:8443")
        assert result == {"port": 443, "target_port": 8443, "protocol": "TCP"}


# =============================================================================
# Tests for Service commands  (lines 148-149, 222-223, 268-269, 285, 289-290)
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestServiceCommandErrors:
    """Tests for error-path coverage in service commands."""

    def test_list_services_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """list_services should handle KubernetesError (lines 148-149)."""
        mock_networking_manager.list_services.side_effect = KubernetesConnectionError(
            "Cannot connect"
        )

        result = cli_runner.invoke(app, ["services", "list"])

        assert result.exit_code == 1

    def test_create_service_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """create_service should handle KubernetesError (lines 222-223)."""
        mock_networking_manager.create_service.side_effect = KubernetesError(
            "Server error", status_code=500
        )

        result = cli_runner.invoke(
            app,
            ["services", "create", "my-svc", "--port", "80:8080/TCP"],
        )

        assert result.exit_code == 1

    def test_create_service_with_invalid_label(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """create_service should exit on invalid label format."""
        result = cli_runner.invoke(
            app,
            ["services", "create", "my-svc", "--label", "invalid-no-equals"],
        )

        assert result.exit_code == 1
        mock_networking_manager.create_service.assert_not_called()

    def test_update_service_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """update_service should handle KubernetesError (lines 268-269)."""
        mock_networking_manager.update_service.side_effect = KubernetesNotFoundError(
            resource_type="Service", resource_name="my-svc"
        )

        result = cli_runner.invoke(
            app,
            ["services", "update", "my-svc", "--type", "LoadBalancer"],
        )

        assert result.exit_code == 1

    def test_delete_service_user_aborts(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """delete_service should abort when user does not confirm (line 285)."""
        with patch(
            "system_operations_manager.plugins.kubernetes.commands.base.typer.confirm",
            return_value=False,
        ):
            result = cli_runner.invoke(app, ["services", "delete", "my-svc"])

        assert result.exit_code != 0
        mock_networking_manager.delete_service.assert_not_called()

    def test_delete_service_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """delete_service should handle KubernetesError (lines 289-290)."""
        mock_networking_manager.delete_service.side_effect = KubernetesNotFoundError(
            resource_type="Service", resource_name="my-svc"
        )

        result = cli_runner.invoke(app, ["services", "delete", "my-svc", "--force"])

        assert result.exit_code == 1

    def test_create_service_with_selector(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """create_service should parse selector labels."""
        result = cli_runner.invoke(
            app,
            [
                "services",
                "create",
                "my-svc",
                "--selector",
                "app=web",
                "--port",
                "80:8080/TCP",
            ],
        )

        assert result.exit_code == 0
        call_args: Any = mock_networking_manager.create_service.call_args
        assert call_args.kwargs.get("selector") == {"app": "web"}

    def test_update_service_with_invalid_selector(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """update_service should exit on invalid selector label format."""
        result = cli_runner.invoke(
            app,
            ["services", "update", "my-svc", "--selector", "invalid-no-equals"],
        )

        assert result.exit_code == 1
        mock_networking_manager.update_service.assert_not_called()


# =============================================================================
# Tests for Ingress commands  (lines 325-326, 387-391, 425-429, 444, 448-449)
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestIngressCommandErrors:
    """Tests for error-path coverage in ingress commands."""

    def test_list_ingresses_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """list_ingresses should handle KubernetesError (lines 325-326)."""
        mock_networking_manager.list_ingresses.side_effect = KubernetesAuthError(
            "Forbidden", status_code=403
        )

        result = cli_runner.invoke(app, ["ingresses", "list"])

        assert result.exit_code == 1

    def test_create_ingress_json_decode_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """create_ingress should handle JSONDecodeError (lines 387-389)."""
        result = cli_runner.invoke(
            app,
            ["ingresses", "create", "my-ingress", "--rule", "not-valid-json"],
        )

        assert result.exit_code == 1
        mock_networking_manager.create_ingress.assert_not_called()

    def test_create_ingress_handles_kubernetes_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """create_ingress should handle KubernetesError (lines 390-391)."""
        mock_networking_manager.create_ingress.side_effect = KubernetesError(
            "Server error", status_code=500
        )

        result = cli_runner.invoke(
            app,
            [
                "ingresses",
                "create",
                "my-ingress",
                "--rule",
                '{"host": "example.com"}',
            ],
        )

        assert result.exit_code == 1

    def test_create_ingress_with_invalid_label(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """create_ingress should exit on invalid label format."""
        result = cli_runner.invoke(
            app,
            ["ingresses", "create", "my-ingress", "--label", "invalid-no-equals"],
        )

        assert result.exit_code == 1
        mock_networking_manager.create_ingress.assert_not_called()

    def test_update_ingress_json_decode_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """update_ingress should handle JSONDecodeError (lines 425-427)."""
        result = cli_runner.invoke(
            app,
            ["ingresses", "update", "my-ingress", "--rule", "not-valid-json"],
        )

        assert result.exit_code == 1
        mock_networking_manager.update_ingress.assert_not_called()

    def test_update_ingress_handles_kubernetes_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """update_ingress should handle KubernetesError (lines 428-429)."""
        mock_networking_manager.update_ingress.side_effect = KubernetesNotFoundError(
            resource_type="Ingress", resource_name="my-ingress"
        )

        result = cli_runner.invoke(
            app,
            [
                "ingresses",
                "update",
                "my-ingress",
                "--rule",
                '{"host": "example.com"}',
            ],
        )

        assert result.exit_code == 1

    def test_delete_ingress_user_aborts(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """delete_ingress should abort when user does not confirm (line 444)."""
        with patch(
            "system_operations_manager.plugins.kubernetes.commands.base.typer.confirm",
            return_value=False,
        ):
            result = cli_runner.invoke(app, ["ingresses", "delete", "my-ingress"])

        assert result.exit_code != 0
        mock_networking_manager.delete_ingress.assert_not_called()

    def test_delete_ingress_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """delete_ingress should handle KubernetesError (lines 448-449)."""
        mock_networking_manager.delete_ingress.side_effect = KubernetesTimeoutError(
            "Operation timed out"
        )

        result = cli_runner.invoke(app, ["ingresses", "delete", "my-ingress", "--force"])

        assert result.exit_code == 1

    def test_create_ingress_with_tls_json_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """create_ingress should handle JSONDecodeError in TLS config."""
        result = cli_runner.invoke(
            app,
            ["ingresses", "create", "my-ingress", "--tls", "{invalid-json"],
        )

        assert result.exit_code == 1
        mock_networking_manager.create_ingress.assert_not_called()


# =============================================================================
# Tests for NetworkPolicy commands  (lines 484-485, 540-541, 556, 560-561)
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestNetworkPolicyCommandErrors:
    """Tests for error-path coverage in network policy commands."""

    def test_list_network_policies_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """list_network_policies should handle KubernetesError (lines 484-485)."""
        mock_networking_manager.list_network_policies.side_effect = KubernetesConnectionError(
            "Cannot connect"
        )

        result = cli_runner.invoke(app, ["network-policies", "list"])

        assert result.exit_code == 1

    def test_create_network_policy_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """create_network_policy should handle KubernetesError (lines 540-541)."""
        mock_networking_manager.create_network_policy.side_effect = KubernetesError(
            "Server error", status_code=500
        )

        result = cli_runner.invoke(
            app,
            [
                "network-policies",
                "create",
                "deny-all",
                "--policy-type",
                "Ingress",
            ],
        )

        assert result.exit_code == 1

    def test_create_network_policy_with_invalid_label(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """create_network_policy should exit on invalid label format."""
        result = cli_runner.invoke(
            app,
            ["network-policies", "create", "deny-all", "--label", "invalid-no-equals"],
        )

        assert result.exit_code == 1
        mock_networking_manager.create_network_policy.assert_not_called()

    def test_create_network_policy_with_invalid_pod_selector(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """create_network_policy should exit on invalid pod-selector format."""
        result = cli_runner.invoke(
            app,
            ["network-policies", "create", "deny-all", "--pod-selector", "invalid-no-equals"],
        )

        assert result.exit_code == 1
        mock_networking_manager.create_network_policy.assert_not_called()

    def test_delete_network_policy_user_aborts(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """delete_network_policy should abort when user does not confirm (line 556)."""
        with patch(
            "system_operations_manager.plugins.kubernetes.commands.base.typer.confirm",
            return_value=False,
        ):
            result = cli_runner.invoke(app, ["network-policies", "delete", "deny-all"])

        assert result.exit_code != 0
        mock_networking_manager.delete_network_policy.assert_not_called()

    def test_delete_network_policy_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """delete_network_policy should handle KubernetesError (lines 560-561)."""
        mock_networking_manager.delete_network_policy.side_effect = KubernetesNotFoundError(
            resource_type="NetworkPolicy", resource_name="deny-all"
        )

        result = cli_runner.invoke(app, ["network-policies", "delete", "deny-all", "--force"])

        assert result.exit_code == 1

    def test_create_network_policy_with_pod_selector_and_type(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """create_network_policy should parse pod-selector and policy-type."""
        result = cli_runner.invoke(
            app,
            [
                "network-policies",
                "create",
                "deny-all",
                "--pod-selector",
                "app=web",
                "--policy-type",
                "Ingress",
            ],
        )

        assert result.exit_code == 0
        call_args: Any = mock_networking_manager.create_network_policy.call_args
        assert call_args.kwargs.get("pod_selector") == {"app": "web"}


# =============================================================================
# Happy-path tests to cover the success branches
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestServiceHappyPaths:
    """Happy-path tests to cover success branches in service commands."""

    def test_list_services_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """list_services should succeed and call formatter (lines 146-147)."""
        result = cli_runner.invoke(app, ["services", "list"])

        assert result.exit_code == 0
        mock_networking_manager.list_services.assert_called_once()

    def test_get_service_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """get_service should succeed and format the resource (lines 163-169)."""
        result = cli_runner.invoke(app, ["services", "get", "my-svc"])

        assert result.exit_code == 0
        mock_networking_manager.get_service.assert_called_once_with("my-svc", namespace=None)

    def test_get_service_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """get_service should handle KubernetesError."""
        mock_networking_manager.get_service.side_effect = KubernetesNotFoundError(
            resource_type="Service", resource_name="my-svc"
        )

        result = cli_runner.invoke(app, ["services", "get", "my-svc"])

        assert result.exit_code == 1

    def test_update_service_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """update_service should succeed and format the resource (lines 266-267)."""
        result = cli_runner.invoke(
            app,
            ["services", "update", "my-svc", "--type", "LoadBalancer"],
        )

        assert result.exit_code == 0
        mock_networking_manager.update_service.assert_called_once()

    def test_delete_service_force_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """delete_service with --force should delete without confirmation (line 288)."""
        result = cli_runner.invoke(app, ["services", "delete", "my-svc", "--force"])

        assert result.exit_code == 0
        mock_networking_manager.delete_service.assert_called_once()


@pytest.mark.unit
@pytest.mark.kubernetes
class TestIngressHappyPaths:
    """Happy-path tests for ingress command success branches."""

    def test_get_ingress_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """get_ingress should succeed and format the resource (lines 339-345)."""
        result = cli_runner.invoke(app, ["ingresses", "get", "my-ingress"])

        assert result.exit_code == 0
        mock_networking_manager.get_ingress.assert_called_once_with("my-ingress", namespace=None)

    def test_get_ingress_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """get_ingress should handle KubernetesError."""
        mock_networking_manager.get_ingress.side_effect = KubernetesNotFoundError(
            resource_type="Ingress", resource_name="my-ingress"
        )

        result = cli_runner.invoke(app, ["ingresses", "get", "my-ingress"])

        assert result.exit_code == 1

    def test_list_ingresses_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """list_ingresses should succeed and call formatter (lines 323-324)."""
        result = cli_runner.invoke(app, ["ingresses", "list"])

        assert result.exit_code == 0
        mock_networking_manager.list_ingresses.assert_called_once()

    def test_create_ingress_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """create_ingress should succeed and format the resource (lines 385-386)."""
        result = cli_runner.invoke(
            app,
            [
                "ingresses",
                "create",
                "my-ingress",
                "--rule",
                '{"host": "example.com"}',
            ],
        )

        assert result.exit_code == 0
        mock_networking_manager.create_ingress.assert_called_once()

    def test_update_ingress_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """update_ingress should succeed and format the resource (lines 423-424)."""
        result = cli_runner.invoke(
            app,
            [
                "ingresses",
                "update",
                "my-ingress",
                "--rule",
                '{"host": "example.com"}',
            ],
        )

        assert result.exit_code == 0
        mock_networking_manager.update_ingress.assert_called_once()

    def test_delete_ingress_force_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """delete_ingress with --force should delete without confirmation (line 447)."""
        result = cli_runner.invoke(app, ["ingresses", "delete", "my-ingress", "--force"])

        assert result.exit_code == 0
        mock_networking_manager.delete_ingress.assert_called_once()


@pytest.mark.unit
@pytest.mark.kubernetes
class TestNetworkPolicyHappyPaths:
    """Happy-path tests for network policy command success branches."""

    def test_get_network_policy_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """get_network_policy should succeed and format the resource (lines 498-504)."""
        result = cli_runner.invoke(app, ["network-policies", "get", "deny-all"])

        assert result.exit_code == 0
        mock_networking_manager.get_network_policy.assert_called_once_with(
            "deny-all", namespace=None
        )

    def test_get_network_policy_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """get_network_policy should handle KubernetesError."""
        mock_networking_manager.get_network_policy.side_effect = KubernetesNotFoundError(
            resource_type="NetworkPolicy", resource_name="deny-all"
        )

        result = cli_runner.invoke(app, ["network-policies", "get", "deny-all"])

        assert result.exit_code == 1

    def test_list_network_policies_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """list_network_policies should succeed and call formatter (lines 482-483)."""
        result = cli_runner.invoke(app, ["network-policies", "list"])

        assert result.exit_code == 0
        mock_networking_manager.list_network_policies.assert_called_once()

    def test_delete_network_policy_force_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_networking_manager: MagicMock,
    ) -> None:
        """delete_network_policy with --force should delete without confirmation (line 559)."""
        result = cli_runner.invoke(app, ["network-policies", "delete", "deny-all", "--force"])

        assert result.exit_code == 0
        mock_networking_manager.delete_network_policy.assert_called_once()
