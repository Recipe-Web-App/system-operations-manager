"""E2E tests for Kong security plugin workflows.

These tests verify complete workflows for setting up security:
- Key authentication (key-auth)
- Rate limiting
- Other security plugins

Note: Kong runs in DB-less mode, so entities are created via declarative config apply.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import yaml

if TYPE_CHECKING:
    import typer
    from typer.testing import CliRunner


@pytest.mark.e2e
@pytest.mark.kong
class TestKeyAuthWorkflow:
    """Test key authentication workflows via declarative config."""

    def test_enable_key_auth_on_service(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Enable key-auth plugin on a service via config."""
        service_name = f"{unique_prefix}-keyauth-svc"
        config_file = temp_config_dir / "keyauth.yaml"

        # Create declarative config with service and key-auth plugin
        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "httpbin.org",
                    "port": 80,
                    "protocol": "http",
                }
            ],
            "plugins": [
                {
                    "name": "key-auth",
                    "service": service_name,
                    "config": {"key_names": ["apikey"]},
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        # Apply config
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0, f"Failed to apply config: {result.output}"

        # Verify plugin is enabled
        result = cli_runner.invoke(kong_app, ["kong", "plugins", "list", "--service", service_name])
        assert result.exit_code == 0
        assert "key-auth" in result.output

    def test_consumer_with_api_key(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Create a consumer with an API key via declarative config."""
        username = f"{unique_prefix}-keyauth-user"
        api_key = f"test-key-{unique_prefix}"
        config_file = temp_config_dir / "consumer-key.yaml"

        # Create declarative config with consumer and key-auth credential
        config = {
            "_format_version": "3.0",
            "consumers": [
                {
                    "username": username,
                    "keyauth_credentials": [{"key": api_key}],
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        # Apply config
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0, f"Failed to apply config: {result.output}"

        # Verify consumer exists
        result = cli_runner.invoke(kong_app, ["kong", "consumers", "get", username])
        assert result.exit_code == 0
        assert username in result.output

    def test_key_auth_full_flow(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Complete key-auth flow via declarative config."""
        service_name = f"{unique_prefix}-keyauth-api"
        route_name = f"{unique_prefix}-keyauth-route"
        username = f"{unique_prefix}-api-consumer"
        api_key = f"api-key-{unique_prefix}"
        config_file = temp_config_dir / "full-keyauth.yaml"

        # Create comprehensive declarative config
        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "httpbin.org",
                    "port": 80,
                    "protocol": "http",
                    "routes": [
                        {
                            "name": route_name,
                            "paths": [f"/api/{unique_prefix}"],
                        }
                    ],
                }
            ],
            "plugins": [
                {
                    "name": "key-auth",
                    "service": service_name,
                    "config": {"hide_credentials": True},
                }
            ],
            "consumers": [
                {
                    "username": username,
                    "keyauth_credentials": [{"key": api_key}],
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        # Apply config
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0, f"Failed to apply config: {result.output}"

        # Verify complete setup
        # Check plugin is enabled
        result = cli_runner.invoke(kong_app, ["kong", "plugins", "list", "--service", service_name])
        assert result.exit_code == 0
        assert "key-auth" in result.output

        # Check consumer exists
        result = cli_runner.invoke(kong_app, ["kong", "consumers", "get", username])
        assert result.exit_code == 0
        assert username in result.output


@pytest.mark.e2e
@pytest.mark.kong
class TestRateLimitWorkflow:
    """Test rate limiting workflows via declarative config."""

    def test_enable_rate_limiting(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Enable rate limiting on a service via declarative config."""
        service_name = f"{unique_prefix}-ratelimit-svc"
        config_file = temp_config_dir / "ratelimit.yaml"

        # Create declarative config with service and rate-limiting plugin
        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "httpbin.org",
                    "port": 80,
                    "protocol": "http",
                }
            ],
            "plugins": [
                {
                    "name": "rate-limiting",
                    "service": service_name,
                    "config": {
                        "minute": 100,
                        "policy": "local",
                    },
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        # Apply config
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0, f"Failed to apply config: {result.output}"

        # Verify plugin
        result = cli_runner.invoke(kong_app, ["kong", "plugins", "list", "--service", service_name])
        assert result.exit_code == 0
        assert "rate-limiting" in result.output

    def test_rate_limit_multiple_windows(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Enable rate limiting with multiple time windows."""
        service_name = f"{unique_prefix}-ratelimit-multi"
        config_file = temp_config_dir / "ratelimit-multi.yaml"

        # Create declarative config with service and rate-limiting with multiple windows
        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "example.com",
                    "port": 80,
                    "protocol": "http",
                }
            ],
            "plugins": [
                {
                    "name": "rate-limiting",
                    "service": service_name,
                    "config": {
                        "second": 10,
                        "minute": 100,
                        "hour": 1000,
                        "policy": "local",
                    },
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        # Apply config
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0

        # Verify plugin
        result = cli_runner.invoke(kong_app, ["kong", "plugins", "list", "--service", service_name])
        assert result.exit_code == 0
        assert "rate-limiting" in result.output


@pytest.mark.e2e
@pytest.mark.kong
class TestSecurityCombinedWorkflow:
    """Test combined security plugin workflows via declarative config."""

    def test_service_with_key_auth_and_rate_limit(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Set up a service with both key-auth and rate limiting."""
        service_name = f"{unique_prefix}-secure-api"
        username = f"{unique_prefix}-secure-user"
        config_file = temp_config_dir / "secure-api.yaml"

        # Create comprehensive security config
        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "httpbin.org",
                    "port": 80,
                    "protocol": "http",
                }
            ],
            "plugins": [
                {
                    "name": "key-auth",
                    "service": service_name,
                    "config": {"key_names": ["apikey"]},
                },
                {
                    "name": "rate-limiting",
                    "service": service_name,
                    "config": {
                        "minute": 60,
                        "limit_by": "consumer",
                        "policy": "local",
                    },
                },
            ],
            "consumers": [
                {
                    "username": username,
                    "keyauth_credentials": [{"key": f"key-{unique_prefix}"}],
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        # Apply config
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0, f"Failed to apply config: {result.output}"

        # Verify both plugins are enabled
        result = cli_runner.invoke(kong_app, ["kong", "plugins", "list", "--service", service_name])
        assert result.exit_code == 0
        assert "key-auth" in result.output
        assert "rate-limiting" in result.output


@pytest.mark.e2e
@pytest.mark.kong
class TestCORSWorkflow:
    """Test CORS plugin workflows via declarative config."""

    def test_enable_cors(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Enable CORS on a service via declarative config."""
        service_name = f"{unique_prefix}-cors-svc"
        config_file = temp_config_dir / "cors.yaml"

        # Create declarative config with service and CORS plugin
        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "httpbin.org",
                    "port": 80,
                    "protocol": "http",
                }
            ],
            "plugins": [
                {
                    "name": "cors",
                    "service": service_name,
                    "config": {
                        "origins": ["https://example.com"],
                        "methods": ["GET", "POST"],
                        "headers": ["Content-Type", "Authorization"],
                        "credentials": True,
                    },
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        # Apply config
        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0, f"Failed to apply config: {result.output}"

        # Verify plugin
        result = cli_runner.invoke(kong_app, ["kong", "plugins", "list", "--service", service_name])
        assert result.exit_code == 0
        assert "cors" in result.output


# ============================================================================
# JWT Workflow Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.kong
class TestJWTWorkflow:
    """Test JWT authentication workflows via declarative config."""

    def test_enable_jwt_on_service(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Enable JWT authentication on a service."""
        service_name = f"{unique_prefix}-jwt-svc"
        config_file = temp_config_dir / "jwt.yaml"

        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "httpbin.org",
                    "port": 80,
                    "protocol": "http",
                }
            ],
            "plugins": [
                {
                    "name": "jwt",
                    "service": service_name,
                    "config": {
                        "claims_to_verify": ["exp"],
                    },
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0, f"Failed to apply config: {result.output}"

        # Verify plugin
        result = cli_runner.invoke(kong_app, ["kong", "plugins", "list", "--service", service_name])
        assert result.exit_code == 0
        assert "jwt" in result.output

    def test_consumer_with_jwt_credentials(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Create a consumer with JWT credentials."""
        username = f"{unique_prefix}-jwt-user"
        config_file = temp_config_dir / "consumer-jwt.yaml"

        config = {
            "_format_version": "3.0",
            "consumers": [
                {
                    "username": username,
                    "jwt_secrets": [
                        {
                            "key": f"jwt-key-{unique_prefix}",
                            "algorithm": "HS256",
                            "secret": "my-jwt-secret-key-1234567890",
                        }
                    ],
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0, f"Failed to apply config: {result.output}"

        # Verify consumer exists
        result = cli_runner.invoke(kong_app, ["kong", "consumers", "get", username])
        assert result.exit_code == 0
        assert username in result.output

    def test_jwt_full_flow(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Complete JWT authentication flow."""
        service_name = f"{unique_prefix}-jwt-api"
        username = f"{unique_prefix}-jwt-consumer"
        config_file = temp_config_dir / "full-jwt.yaml"

        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "httpbin.org",
                    "port": 80,
                    "protocol": "http",
                    "routes": [
                        {
                            "name": f"{unique_prefix}-jwt-route",
                            "paths": [f"/jwt/{unique_prefix}"],
                        }
                    ],
                }
            ],
            "plugins": [
                {
                    "name": "jwt",
                    "service": service_name,
                    "config": {
                        "claims_to_verify": ["exp", "nbf"],
                        "header_names": ["Authorization"],
                    },
                }
            ],
            "consumers": [
                {
                    "username": username,
                    "jwt_secrets": [
                        {
                            "key": f"key-{unique_prefix}",
                            "algorithm": "HS256",
                            "secret": "secret-for-testing-12345",
                        }
                    ],
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0, f"Failed to apply config: {result.output}"

        # Verify setup
        result = cli_runner.invoke(kong_app, ["kong", "plugins", "list", "--service", service_name])
        assert result.exit_code == 0
        assert "jwt" in result.output


# ============================================================================
# OAuth2 Workflow Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.kong
class TestOAuth2Workflow:
    """Test OAuth2 authentication workflows via declarative config."""

    def test_enable_oauth2_on_service(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Enable OAuth2 on a service."""
        service_name = f"{unique_prefix}-oauth2-svc"
        config_file = temp_config_dir / "oauth2.yaml"

        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "httpbin.org",
                    "port": 80,
                    "protocol": "http",
                }
            ],
            "plugins": [
                {
                    "name": "oauth2",
                    "service": service_name,
                    "config": {
                        "scopes": ["read", "write"],
                        "mandatory_scope": True,
                        "enable_authorization_code": True,
                        "enable_client_credentials": True,
                    },
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0, f"Failed to apply config: {result.output}"

        # Verify plugin
        result = cli_runner.invoke(kong_app, ["kong", "plugins", "list", "--service", service_name])
        assert result.exit_code == 0
        assert "oauth2" in result.output

    def test_consumer_with_oauth2_credentials(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Create a consumer with OAuth2 credentials."""
        username = f"{unique_prefix}-oauth2-user"
        config_file = temp_config_dir / "consumer-oauth2.yaml"

        config = {
            "_format_version": "3.0",
            "consumers": [
                {
                    "username": username,
                    "oauth2_credentials": [
                        {
                            "name": f"OAuth2 App {unique_prefix}",
                            "client_id": f"client-{unique_prefix}",
                            "client_secret": "secret-12345",
                            "redirect_uris": ["https://example.com/callback"],
                        }
                    ],
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0, f"Failed to apply config: {result.output}"

        # Verify consumer exists
        result = cli_runner.invoke(kong_app, ["kong", "consumers", "get", username])
        assert result.exit_code == 0
        assert username in result.output

    def test_oauth2_with_client_credentials_grant(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """OAuth2 with client credentials grant type only."""
        service_name = f"{unique_prefix}-oauth2-cc-svc"
        config_file = temp_config_dir / "oauth2-cc.yaml"

        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "httpbin.org",
                    "port": 80,
                    "protocol": "http",
                }
            ],
            "plugins": [
                {
                    "name": "oauth2",
                    "service": service_name,
                    "config": {
                        "enable_client_credentials": True,
                        "enable_authorization_code": False,
                        "enable_implicit_grant": False,
                        "enable_password_grant": False,
                    },
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0, f"Failed to apply config: {result.output}"


# ============================================================================
# ACL Workflow Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.kong
class TestACLWorkflow:
    """Test ACL (Access Control List) workflows via declarative config."""

    def test_enable_acl_on_service(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Enable ACL with allowed groups on a service."""
        service_name = f"{unique_prefix}-acl-svc"
        config_file = temp_config_dir / "acl.yaml"

        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "httpbin.org",
                    "port": 80,
                    "protocol": "http",
                }
            ],
            "plugins": [
                {
                    "name": "acl",
                    "service": service_name,
                    "config": {
                        "allow": ["admin", "premium"],
                    },
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0, f"Failed to apply config: {result.output}"

        # Verify plugin
        result = cli_runner.invoke(kong_app, ["kong", "plugins", "list", "--service", service_name])
        assert result.exit_code == 0
        assert "acl" in result.output

    def test_consumer_with_acl_groups(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Create a consumer with ACL group memberships."""
        username = f"{unique_prefix}-acl-user"
        config_file = temp_config_dir / "consumer-acl.yaml"

        config = {
            "_format_version": "3.0",
            "consumers": [
                {
                    "username": username,
                    "acls": [
                        {"group": "admin"},
                        {"group": "premium"},
                    ],
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0, f"Failed to apply config: {result.output}"

        # Verify consumer exists
        result = cli_runner.invoke(kong_app, ["kong", "consumers", "get", username])
        assert result.exit_code == 0
        assert username in result.output

    def test_acl_with_deny_groups(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Enable ACL with denied groups."""
        service_name = f"{unique_prefix}-acl-deny-svc"
        config_file = temp_config_dir / "acl-deny.yaml"

        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "httpbin.org",
                    "port": 80,
                    "protocol": "http",
                }
            ],
            "plugins": [
                {
                    "name": "acl",
                    "service": service_name,
                    "config": {
                        "deny": ["blocked", "suspended"],
                    },
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0, f"Failed to apply config: {result.output}"

    def test_acl_full_flow_with_auth(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Complete ACL flow with key-auth for consumer identification."""
        service_name = f"{unique_prefix}-acl-auth-svc"
        username = f"{unique_prefix}-acl-auth-user"
        config_file = temp_config_dir / "acl-full.yaml"

        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "httpbin.org",
                    "port": 80,
                    "protocol": "http",
                }
            ],
            "plugins": [
                {
                    "name": "key-auth",
                    "service": service_name,
                },
                {
                    "name": "acl",
                    "service": service_name,
                    "config": {
                        "allow": ["premium"],
                    },
                },
            ],
            "consumers": [
                {
                    "username": username,
                    "keyauth_credentials": [{"key": f"key-{unique_prefix}"}],
                    "acls": [{"group": "premium"}],
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0, f"Failed to apply config: {result.output}"

        # Verify plugins
        result = cli_runner.invoke(kong_app, ["kong", "plugins", "list", "--service", service_name])
        assert result.exit_code == 0
        assert "key-auth" in result.output
        assert "acl" in result.output


# ============================================================================
# IP Restriction Workflow Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.kong
class TestIPRestrictionWorkflow:
    """Test IP restriction workflows via declarative config."""

    def test_enable_ip_allow_list(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Enable IP restriction with allowed IPs."""
        service_name = f"{unique_prefix}-ip-allow-svc"
        config_file = temp_config_dir / "ip-allow.yaml"

        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "httpbin.org",
                    "port": 80,
                    "protocol": "http",
                }
            ],
            "plugins": [
                {
                    "name": "ip-restriction",
                    "service": service_name,
                    "config": {
                        "allow": ["192.168.1.0/24", "10.0.0.0/8"],
                    },
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0, f"Failed to apply config: {result.output}"

        # Verify plugin
        result = cli_runner.invoke(kong_app, ["kong", "plugins", "list", "--service", service_name])
        assert result.exit_code == 0
        assert "ip-restriction" in result.output

    def test_enable_ip_deny_list(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Enable IP restriction with denied IPs."""
        service_name = f"{unique_prefix}-ip-deny-svc"
        config_file = temp_config_dir / "ip-deny.yaml"

        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "httpbin.org",
                    "port": 80,
                    "protocol": "http",
                }
            ],
            "plugins": [
                {
                    "name": "ip-restriction",
                    "service": service_name,
                    "config": {
                        "deny": ["192.168.100.0/24", "10.10.10.10"],
                    },
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0, f"Failed to apply config: {result.output}"

        # Verify plugin
        result = cli_runner.invoke(kong_app, ["kong", "plugins", "list", "--service", service_name])
        assert result.exit_code == 0
        assert "ip-restriction" in result.output

    def test_ip_restriction_on_route(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Enable IP restriction at route level."""
        service_name = f"{unique_prefix}-ip-route-svc"
        route_name = f"{unique_prefix}-ip-route"
        config_file = temp_config_dir / "ip-route.yaml"

        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "httpbin.org",
                    "port": 80,
                    "protocol": "http",
                    "routes": [
                        {
                            "name": route_name,
                            "paths": [f"/admin/{unique_prefix}"],
                        }
                    ],
                }
            ],
            "plugins": [
                {
                    "name": "ip-restriction",
                    "route": route_name,
                    "config": {
                        "allow": ["127.0.0.1", "::1"],
                    },
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0, f"Failed to apply config: {result.output}"

        # Verify route exists
        result = cli_runner.invoke(kong_app, ["kong", "routes", "get", route_name])
        assert result.exit_code == 0
