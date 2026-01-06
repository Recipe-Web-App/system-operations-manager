"""E2E tests for Kong traffic control workflows.

These tests verify complete workflows for traffic management plugins:
- Request size limiting
- Request transformation
- Response transformation

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


# ============================================================================
# Request Size Limiting Workflow Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.kong
class TestRequestSizeWorkflow:
    """Test request size limiting workflows."""

    def test_enable_request_size_on_service(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Enable request size limiting on a service via declarative config."""
        service_name = f"{unique_prefix}-size-svc"
        config_file = temp_config_dir / "service.yaml"

        # Create service with request-size-limiting plugin via declarative config
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
                    "name": "request-size-limiting",
                    "service": service_name,
                    "config": {
                        "allowed_payload_size": 5,
                        "size_unit": "megabytes",
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

        # Verify service exists (plugin creation validated by successful config apply)
        result = cli_runner.invoke(kong_app, ["kong", "services", "get", service_name])
        assert result.exit_code == 0
        assert service_name in result.output

    def test_enable_request_size_with_unit(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Enable request size limiting with kilobytes unit via declarative config."""
        service_name = f"{unique_prefix}-size-unit-svc"
        config_file = temp_config_dir / "service.yaml"

        # Create service with request-size-limiting plugin (kilobytes)
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
                    "name": "request-size-limiting",
                    "service": service_name,
                    "config": {
                        "allowed_payload_size": 512,
                        "size_unit": "kilobytes",
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

        # Verify service exists (plugin creation validated by successful config apply)
        result = cli_runner.invoke(kong_app, ["kong", "services", "get", service_name])
        assert result.exit_code == 0
        assert service_name in result.output

    def test_request_size_via_declarative_config(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Enable request size limiting via declarative config."""
        service_name = f"{unique_prefix}-size-decl-svc"
        config_file = temp_config_dir / "service-with-size.yaml"

        # Create service with request-size-limiting plugin in config
        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "httpbin.org",
                    "port": 80,
                    "protocol": "http",
                    "plugins": [
                        {
                            "name": "request-size-limiting",
                            "config": {
                                "allowed_payload_size": 10,
                                "size_unit": "megabytes",
                            },
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

        # Verify service exists
        result = cli_runner.invoke(kong_app, ["kong", "services", "get", service_name])
        assert result.exit_code == 0
        assert service_name in result.output


# ============================================================================
# Request Transformer Workflow Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.kong
class TestRequestTransformerWorkflow:
    """Test request transformation workflows."""

    def test_add_request_headers(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Add headers to requests via request-transformer declarative config."""
        service_name = f"{unique_prefix}-req-trans-svc"
        config_file = temp_config_dir / "service.yaml"

        # Create service with request-transformer plugin
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
                    "name": "request-transformer",
                    "service": service_name,
                    "config": {
                        "add": {
                            "headers": [
                                "X-Custom-Header:custom-value",
                                "X-Request-ID:12345",
                            ],
                        },
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

        # Verify service exists (plugin creation validated by successful config apply)
        result = cli_runner.invoke(kong_app, ["kong", "services", "get", service_name])
        assert result.exit_code == 0
        assert service_name in result.output

    def test_remove_request_headers(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Remove headers from requests via request-transformer declarative config."""
        service_name = f"{unique_prefix}-req-trans-rm-svc"
        config_file = temp_config_dir / "service.yaml"

        # Create service with request-transformer plugin (remove headers)
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
                    "name": "request-transformer",
                    "service": service_name,
                    "config": {
                        "remove": {
                            "headers": ["X-Forwarded-For", "X-Real-IP"],
                        },
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

        # Verify service exists (plugin creation validated by successful config apply)
        result = cli_runner.invoke(kong_app, ["kong", "services", "get", service_name])
        assert result.exit_code == 0
        assert service_name in result.output

    def test_add_querystring_params(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Add querystring parameters via request-transformer declarative config."""
        service_name = f"{unique_prefix}-req-trans-qs-svc"
        config_file = temp_config_dir / "service.yaml"

        # Create service with request-transformer plugin (add querystring)
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
                    "name": "request-transformer",
                    "service": service_name,
                    "config": {
                        "add": {
                            "querystring": ["api_version:v2"],
                        },
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

        # Verify service exists (plugin creation validated by successful config apply)
        result = cli_runner.invoke(kong_app, ["kong", "services", "get", service_name])
        assert result.exit_code == 0
        assert service_name in result.output

    def test_request_transformer_via_declarative_config(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Enable request transformation via declarative config."""
        service_name = f"{unique_prefix}-req-trans-decl-svc"
        config_file = temp_config_dir / "service-with-transformer.yaml"

        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "httpbin.org",
                    "port": 80,
                    "protocol": "http",
                    "plugins": [
                        {
                            "name": "request-transformer",
                            "config": {
                                "add": {
                                    "headers": ["X-Injected:true"],
                                },
                                "remove": {
                                    "headers": ["X-Unwanted"],
                                },
                            },
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


# ============================================================================
# Response Transformer Workflow Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.kong
class TestResponseTransformerWorkflow:
    """Test response transformation workflows."""

    def test_add_response_headers(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Add headers to responses via response-transformer declarative config."""
        service_name = f"{unique_prefix}-resp-trans-svc"
        config_file = temp_config_dir / "service.yaml"

        # Create service with response-transformer plugin
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
                    "name": "response-transformer",
                    "service": service_name,
                    "config": {
                        "add": {
                            "headers": [
                                "X-Powered-By:Kong",
                                "X-Cache-Status:MISS",
                            ],
                        },
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

        # Verify service exists (plugin creation validated by successful config apply)
        result = cli_runner.invoke(kong_app, ["kong", "services", "get", service_name])
        assert result.exit_code == 0
        assert service_name in result.output

    def test_remove_response_headers(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Remove headers from responses via response-transformer declarative config."""
        service_name = f"{unique_prefix}-resp-trans-rm-svc"
        config_file = temp_config_dir / "service.yaml"

        # Create service with response-transformer plugin (remove headers)
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
                    "name": "response-transformer",
                    "service": service_name,
                    "config": {
                        "remove": {
                            "headers": ["Server", "X-Kong-Upstream-Latency"],
                        },
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

        # Verify service exists (plugin creation validated by successful config apply)
        result = cli_runner.invoke(kong_app, ["kong", "services", "get", service_name])
        assert result.exit_code == 0
        assert service_name in result.output

    def test_response_transformer_via_declarative_config(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Enable response transformation via declarative config."""
        service_name = f"{unique_prefix}-resp-trans-decl-svc"
        config_file = temp_config_dir / "service-with-resp-transformer.yaml"

        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "httpbin.org",
                    "port": 80,
                    "protocol": "http",
                    "plugins": [
                        {
                            "name": "response-transformer",
                            "config": {
                                "add": {
                                    "headers": ["X-Response-Time:100ms"],
                                },
                                "remove": {
                                    "headers": ["Server"],
                                },
                            },
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


# ============================================================================
# Combined Traffic Control Workflow Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.kong
class TestCombinedTrafficWorkflow:
    """Test combined traffic control workflows."""

    def test_service_with_multiple_traffic_plugins(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Apply multiple traffic plugins to a service via declarative config."""
        service_name = f"{unique_prefix}-multi-traffic-svc"
        config_file = temp_config_dir / "service-multi-traffic.yaml"

        config = {
            "_format_version": "3.0",
            "services": [
                {
                    "name": service_name,
                    "host": "httpbin.org",
                    "port": 80,
                    "protocol": "http",
                    "plugins": [
                        {
                            "name": "request-size-limiting",
                            "config": {
                                "allowed_payload_size": 5,
                                "size_unit": "megabytes",
                            },
                        },
                        {
                            "name": "request-transformer",
                            "config": {
                                "add": {
                                    "headers": ["X-Request-Processed:true"],
                                },
                            },
                        },
                        {
                            "name": "response-transformer",
                            "config": {
                                "add": {
                                    "headers": ["X-Response-Processed:true"],
                                },
                            },
                        },
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

        # Verify service exists with plugins
        result = cli_runner.invoke(kong_app, ["kong", "services", "get", service_name])
        assert result.exit_code == 0
        assert service_name in result.output

    def test_traffic_control_on_route_level(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Apply traffic plugins at route level via declarative config."""
        service_name = f"{unique_prefix}-route-traffic-svc"
        route_name = f"{unique_prefix}-route-traffic-route"
        config_file = temp_config_dir / "route-traffic.yaml"

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
                            "paths": ["/api"],
                            "plugins": [
                                {
                                    "name": "request-size-limiting",
                                    "config": {
                                        "allowed_payload_size": 2,
                                        "size_unit": "megabytes",
                                    },
                                },
                            ],
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

        # Verify route exists
        result = cli_runner.invoke(kong_app, ["kong", "routes", "get", route_name])
        assert result.exit_code == 0
        assert route_name in result.output
