"""Unit tests for Kong configuration models."""

from __future__ import annotations

import pytest

from system_operations_manager.integrations.kong.models.config import (
    ApplyOperation,
    ConfigDiff,
    ConfigDiffSummary,
    ConfigValidationError,
    ConfigValidationResult,
    DeclarativeConfig,
    HealthFailure,
    PercentileMetrics,
)


class TestDeclarativeConfig:
    """Tests for DeclarativeConfig model."""

    @pytest.mark.unit
    def test_create_empty_config(self) -> None:
        """Should create empty config with defaults."""
        config = DeclarativeConfig()

        assert config.format_version == "3.0"
        assert config.transform is None
        assert config.services == []
        assert config.routes == []
        assert config.upstreams == []
        assert config.consumers == []
        assert config.plugins == []

    @pytest.mark.unit
    def test_create_config_with_services(self) -> None:
        """Should create config with services."""
        config = DeclarativeConfig(
            services=[
                {"name": "api", "host": "api.example.com"},
                {"name": "web", "host": "web.example.com"},
            ]
        )

        assert len(config.services) == 2
        assert config.services[0]["name"] == "api"

    @pytest.mark.unit
    def test_create_full_config(self) -> None:
        """Should create full config with all entity types."""
        config = DeclarativeConfig(
            _format_version="3.0",
            services=[{"name": "api", "host": "api.example.com"}],
            routes=[{"paths": ["/api"], "service": {"name": "api"}}],
            upstreams=[{"name": "api-upstream"}],
            consumers=[{"username": "user1"}],
            plugins=[{"name": "rate-limiting", "config": {"minute": 100}}],
            certificates=[{"cert": "...", "key": "..."}],
            ca_certificates=[{"cert": "..."}],
        )

        assert len(config.services) == 1
        assert len(config.routes) == 1
        assert len(config.upstreams) == 1
        assert len(config.consumers) == 1
        assert len(config.plugins) == 1

    @pytest.mark.unit
    def test_config_alias_fields(self) -> None:
        """Should support alias fields for format_version."""
        config = DeclarativeConfig(_format_version="2.1", _transform=True)

        assert config.format_version == "2.1"
        assert config.transform is True


class TestConfigDiff:
    """Tests for ConfigDiff model."""

    @pytest.mark.unit
    def test_create_diff(self) -> None:
        """Should create create diff."""
        diff = ConfigDiff(
            entity_type="service",
            operation="create",
            id_or_name="new-service",
            desired={"name": "new-service", "host": "api.example.com"},
        )

        assert diff.operation == "create"
        assert diff.current is None
        assert diff.desired is not None

    @pytest.mark.unit
    def test_update_diff(self) -> None:
        """Should create update diff with changes."""
        diff = ConfigDiff(
            entity_type="service",
            operation="update",
            id_or_name="api",
            current={"name": "api", "host": "old.example.com"},
            desired={"name": "api", "host": "new.example.com"},
            changes={"host": ("old.example.com", "new.example.com")},
        )

        assert diff.operation == "update"
        assert diff.changes is not None
        assert "host" in diff.changes

    @pytest.mark.unit
    def test_delete_diff(self) -> None:
        """Should create delete diff."""
        diff = ConfigDiff(
            entity_type="route",
            operation="delete",
            id_or_name="old-route",
            current={"paths": ["/old"]},
        )

        assert diff.operation == "delete"
        assert diff.desired is None


class TestConfigDiffSummary:
    """Tests for ConfigDiffSummary model."""

    @pytest.mark.unit
    def test_create_empty_summary(self) -> None:
        """Should create empty summary."""
        summary = ConfigDiffSummary()

        assert summary.total_changes == 0
        assert summary.creates == {}
        assert summary.updates == {}
        assert summary.deletes == {}
        assert summary.diffs == []

    @pytest.mark.unit
    def test_create_summary_with_changes(self) -> None:
        """Should create summary with change counts."""
        diffs = [
            ConfigDiff(entity_type="service", operation="create", id_or_name="new-svc"),
            ConfigDiff(entity_type="service", operation="update", id_or_name="api"),
            ConfigDiff(entity_type="route", operation="delete", id_or_name="old-route"),
        ]

        summary = ConfigDiffSummary(
            total_changes=3,
            creates={"service": 1},
            updates={"service": 1},
            deletes={"route": 1},
            diffs=diffs,
        )

        assert summary.total_changes == 3
        assert summary.creates["service"] == 1
        assert len(summary.diffs) == 3


class TestConfigValidationError:
    """Tests for ConfigValidationError model."""

    @pytest.mark.unit
    def test_create_validation_error(self) -> None:
        """Should create validation error."""
        error = ConfigValidationError(
            path="services[0].host",
            message="host is required",
            entity_type="service",
            entity_name="api",
        )

        assert error.path == "services[0].host"
        assert error.message == "host is required"
        assert error.entity_type == "service"
        assert error.entity_name == "api"

    @pytest.mark.unit
    def test_create_minimal_error(self) -> None:
        """Should create minimal validation error."""
        error = ConfigValidationError(
            path="root",
            message="Invalid format version",
        )

        assert error.entity_type is None
        assert error.entity_name is None


class TestConfigValidationResult:
    """Tests for ConfigValidationResult model."""

    @pytest.mark.unit
    def test_create_valid_result(self) -> None:
        """Should create valid result."""
        result = ConfigValidationResult(valid=True)

        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []

    @pytest.mark.unit
    def test_create_invalid_result(self) -> None:
        """Should create invalid result with errors."""
        errors = [
            ConfigValidationError(path="services[0].host", message="host is required"),
        ]
        warnings = [
            ConfigValidationError(path="plugins[0]", message="deprecated plugin"),
        ]

        result = ConfigValidationResult(
            valid=False,
            errors=errors,
            warnings=warnings,
        )

        assert result.valid is False
        assert len(result.errors) == 1
        assert len(result.warnings) == 1


class TestApplyOperation:
    """Tests for ApplyOperation model."""

    @pytest.mark.unit
    def test_create_success_operation(self) -> None:
        """Should create successful operation."""
        op = ApplyOperation(
            operation="create",
            entity_type="service",
            id_or_name="new-api",
            result="success",
        )

        assert op.result == "success"
        assert op.error is None

    @pytest.mark.unit
    def test_create_failed_operation(self) -> None:
        """Should create failed operation with error."""
        op = ApplyOperation(
            operation="update",
            entity_type="route",
            id_or_name="api-route",
            result="failed",
            error="Validation failed: paths is required",
        )

        assert op.result == "failed"
        assert op.error is not None

    @pytest.mark.unit
    def test_delete_operation(self) -> None:
        """Should create delete operation."""
        op = ApplyOperation(
            operation="delete",
            entity_type="plugin",
            id_or_name="old-plugin",
            result="success",
        )

        assert op.operation == "delete"


class TestPercentileMetrics:
    """Tests for PercentileMetrics model."""

    @pytest.mark.unit
    def test_create_percentile_metrics(self) -> None:
        """Should create percentile metrics."""
        metrics = PercentileMetrics(
            p50_ms=10.5,
            p95_ms=45.3,
            p99_ms=120.8,
            service="api",
        )

        assert metrics.p50_ms == 10.5
        assert metrics.p95_ms == 45.3
        assert metrics.p99_ms == 120.8
        assert metrics.service == "api"

    @pytest.mark.unit
    def test_default_values(self) -> None:
        """Should use default values."""
        metrics = PercentileMetrics()

        assert metrics.p50_ms is None
        assert metrics.p95_ms is None
        assert metrics.p99_ms is None
        assert metrics.service is None
        assert metrics.route is None


class TestHealthFailure:
    """Tests for HealthFailure model."""

    @pytest.mark.unit
    def test_create_health_failure(self) -> None:
        """Should create health failure."""
        failure = HealthFailure(
            target="192.168.1.1:8080",
            failure_type="tcp_error",
            failure_count=3,
            last_failure_at=1704067200,
            details="Connection refused",
        )

        assert failure.target == "192.168.1.1:8080"
        assert failure.failure_type == "tcp_error"
        assert failure.failure_count == 3
        assert failure.details == "Connection refused"

    @pytest.mark.unit
    def test_default_values(self) -> None:
        """Should use default values."""
        failure = HealthFailure(
            target="backend:8080",
            failure_type="timeout",
        )

        assert failure.failure_count == 0
        assert failure.last_failure_at is None
        assert failure.details is None
