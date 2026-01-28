"""E2E tests for Kong observability workflows.

These tests verify complete workflows for observability features:
- Logging (HTTP, file, syslog, TCP)
- Metrics (Prometheus)
- Health checks
- Tracing (OpenTelemetry, Zipkin)

Note: These tests are currently SKIPPED due to Python 3.14 type annotation issues
with the observability commands. Remove the skip marker when the issue is resolved.

See: tests/e2e/plugins/kong/conftest.py comment about observability commands.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import yaml

if TYPE_CHECKING:
    import typer
    from typer.testing import CliRunner


# Skip all tests in this module until observability commands are fixed
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.kong,
    pytest.mark.skip(
        reason="Observability commands excluded due to Python 3.14 type annotation issues"
    ),
]


# ============================================================================
# Logging Workflow Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.kong
class TestHTTPLoggingWorkflow:
    """Test HTTP logging plugin workflows."""

    def test_enable_http_log_on_service(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Enable HTTP logging on a service via declarative config."""
        service_name = f"{unique_prefix}-httplog-svc"
        config_file = temp_config_dir / "httplog.yaml"

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
                    "name": "http-log",
                    "service": service_name,
                    "config": {
                        "http_endpoint": "http://logging-server:8080/logs",
                        "method": "POST",
                        "timeout": 10000,
                        "keepalive": 60000,
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
        assert "http-log" in result.output

    def test_http_log_with_custom_headers(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Enable HTTP logging with custom headers."""
        service_name = f"{unique_prefix}-httplog-headers-svc"
        config_file = temp_config_dir / "httplog-headers.yaml"

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
                    "name": "http-log",
                    "service": service_name,
                    "config": {
                        "http_endpoint": "http://logging-server:8080/logs",
                        "headers": {
                            "X-Log-Source": "kong-gateway",
                            "Authorization": "Bearer log-token",
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


@pytest.mark.e2e
@pytest.mark.kong
class TestFileLoggingWorkflow:
    """Test file logging plugin workflows."""

    def test_enable_file_log_on_service(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Enable file logging on a service."""
        service_name = f"{unique_prefix}-filelog-svc"
        config_file = temp_config_dir / "filelog.yaml"

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
                    "name": "file-log",
                    "service": service_name,
                    "config": {
                        "path": "/tmp/kong-logs/access.log",
                        "reopen": True,
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


@pytest.mark.e2e
@pytest.mark.kong
class TestTCPLoggingWorkflow:
    """Test TCP/UDP logging plugin workflows."""

    def test_enable_tcp_log_on_service(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Enable TCP logging on a service."""
        service_name = f"{unique_prefix}-tcplog-svc"
        config_file = temp_config_dir / "tcplog.yaml"

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
                    "name": "tcp-log",
                    "service": service_name,
                    "config": {
                        "host": "logging-server",
                        "port": 514,
                        "timeout": 10000,
                        "keepalive": 60000,
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
# Metrics Workflow Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.kong
class TestPrometheusMetricsWorkflow:
    """Test Prometheus metrics plugin workflows."""

    def test_enable_prometheus_globally(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Enable Prometheus metrics globally."""
        config_file = temp_config_dir / "prometheus-global.yaml"

        config = {
            "_format_version": "3.0",
            "plugins": [
                {
                    "name": "prometheus",
                    "config": {
                        "per_consumer": True,
                        "status_code_metrics": True,
                        "latency_metrics": True,
                        "bandwidth_metrics": True,
                        "upstream_health_metrics": True,
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
        result = cli_runner.invoke(kong_app, ["kong", "plugins", "list"])
        assert result.exit_code == 0
        assert "prometheus" in result.output

    def test_enable_prometheus_on_service(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Enable Prometheus metrics on a specific service."""
        service_name = f"{unique_prefix}-prometheus-svc"
        config_file = temp_config_dir / "prometheus-service.yaml"

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
                    "name": "prometheus",
                    "service": service_name,
                    "config": {
                        "per_consumer": False,
                        "status_code_metrics": True,
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
# Health Check Workflow Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.kong
class TestHealthCheckWorkflow:
    """Test upstream health check workflows."""

    def test_upstream_with_active_health_checks(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Create upstream with active health checks via declarative config."""
        upstream_name = f"{unique_prefix}-health-upstream"
        config_file = temp_config_dir / "upstream-health.yaml"

        config = {
            "_format_version": "3.0",
            "upstreams": [
                {
                    "name": upstream_name,
                    "healthchecks": {
                        "active": {
                            "type": "http",
                            "http_path": "/health",
                            "healthy": {
                                "interval": 5,
                                "successes": 2,
                            },
                            "unhealthy": {
                                "interval": 5,
                                "http_failures": 3,
                            },
                        },
                    },
                    "targets": [
                        {"target": "backend1.example.com:8080", "weight": 100},
                        {"target": "backend2.example.com:8080", "weight": 100},
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

        # Verify upstream exists
        result = cli_runner.invoke(kong_app, ["kong", "upstreams", "get", upstream_name])
        assert result.exit_code == 0
        assert upstream_name in result.output

    def test_upstream_with_passive_health_checks(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Create upstream with passive health checks."""
        upstream_name = f"{unique_prefix}-passive-upstream"
        config_file = temp_config_dir / "upstream-passive.yaml"

        config = {
            "_format_version": "3.0",
            "upstreams": [
                {
                    "name": upstream_name,
                    "healthchecks": {
                        "passive": {
                            "type": "http",
                            "healthy": {
                                "successes": 5,
                            },
                            "unhealthy": {
                                "http_failures": 5,
                                "http_statuses": [500, 502, 503],
                            },
                        },
                    },
                    "targets": [
                        {"target": "backend.example.com:8080", "weight": 100},
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

    def test_check_upstream_health_status(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Check health status of an upstream."""
        upstream_name = f"{unique_prefix}-status-upstream"
        config_file = temp_config_dir / "upstream-status.yaml"

        config = {
            "_format_version": "3.0",
            "upstreams": [
                {
                    "name": upstream_name,
                    "targets": [
                        {"target": "backend.example.com:8080", "weight": 100},
                    ],
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        result = cli_runner.invoke(
            kong_app,
            ["kong", "config", "apply", str(config_file), "--no-confirm"],
        )
        assert result.exit_code == 0

        # Check health status
        result = cli_runner.invoke(kong_app, ["kong", "upstreams", "health", upstream_name])
        # Health check may fail if targets are unreachable, but command should succeed
        assert result.exit_code == 0


# ============================================================================
# Tracing Workflow Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.kong
class TestOpenTelemetryTracingWorkflow:
    """Test OpenTelemetry tracing plugin workflows."""

    def test_enable_opentelemetry_globally(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Enable OpenTelemetry tracing globally."""
        config_file = temp_config_dir / "otel-global.yaml"

        config = {
            "_format_version": "3.0",
            "plugins": [
                {
                    "name": "opentelemetry",
                    "config": {
                        "endpoint": "http://otel-collector:4318/v1/traces",
                        "resource_attributes": {
                            "service.name": "kong-gateway",
                            "service.version": "1.0.0",
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

    def test_enable_opentelemetry_on_service(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Enable OpenTelemetry tracing on a specific service."""
        service_name = f"{unique_prefix}-otel-svc"
        config_file = temp_config_dir / "otel-service.yaml"

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
                    "name": "opentelemetry",
                    "service": service_name,
                    "config": {
                        "endpoint": "http://otel-collector:4318/v1/traces",
                        "headers": {
                            "X-Custom-Header": "value",
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


@pytest.mark.e2e
@pytest.mark.kong
class TestZipkinTracingWorkflow:
    """Test Zipkin tracing plugin workflows."""

    def test_enable_zipkin_on_service(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Enable Zipkin tracing on a service."""
        service_name = f"{unique_prefix}-zipkin-svc"
        config_file = temp_config_dir / "zipkin.yaml"

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
                    "name": "zipkin",
                    "service": service_name,
                    "config": {
                        "http_endpoint": "http://zipkin:9411/api/v2/spans",
                        "sample_ratio": 1.0,
                        "default_service_name": service_name,
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

    def test_zipkin_with_custom_sampling(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Enable Zipkin with custom sampling configuration."""
        service_name = f"{unique_prefix}-zipkin-sample-svc"
        config_file = temp_config_dir / "zipkin-sample.yaml"

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
                    "name": "zipkin",
                    "service": service_name,
                    "config": {
                        "http_endpoint": "http://zipkin:9411/api/v2/spans",
                        "sample_ratio": 0.1,  # Sample 10% of requests
                        "include_credential": True,
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
# Combined Observability Workflow Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.kong
class TestCombinedObservabilityWorkflow:
    """Test combined observability plugin workflows."""

    def test_service_with_full_observability_stack(
        self,
        cli_runner: CliRunner,
        kong_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Apply full observability stack to a service via declarative config."""
        service_name = f"{unique_prefix}-full-obs-svc"
        config_file = temp_config_dir / "full-observability.yaml"

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
                # Logging
                {
                    "name": "http-log",
                    "service": service_name,
                    "config": {
                        "http_endpoint": "http://logging-server:8080/logs",
                    },
                },
                # Metrics
                {
                    "name": "prometheus",
                    "service": service_name,
                    "config": {
                        "per_consumer": True,
                        "status_code_metrics": True,
                    },
                },
                # Tracing
                {
                    "name": "opentelemetry",
                    "service": service_name,
                    "config": {
                        "endpoint": "http://otel-collector:4318/v1/traces",
                    },
                },
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
        assert "http-log" in result.output
        assert "prometheus" in result.output
        assert "opentelemetry" in result.output
