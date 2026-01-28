"""Unit tests for observability configuration models."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from system_operations_manager.integrations.observability.config import (
    ElasticsearchConfig,
    JaegerConfig,
    LokiConfig,
    ObservabilityStackConfig,
    PrometheusConfig,
    ZipkinConfig,
)


class TestPrometheusConfig:
    """Tests for PrometheusConfig."""

    @pytest.mark.unit
    def test_default_values(self) -> None:
        """Config should have sensible defaults."""
        config = PrometheusConfig()

        assert config.url == "http://localhost:9090"
        assert config.timeout == 30
        assert config.auth_type == "none"
        assert config.username is None
        assert config.password is None
        assert config.token is None

    @pytest.mark.unit
    def test_custom_url(self) -> None:
        """Config should accept custom URL."""
        config = PrometheusConfig(url="https://prometheus.example.com:9090")

        assert config.url == "https://prometheus.example.com:9090"

    @pytest.mark.unit
    def test_url_validation_strips_trailing_slash(self) -> None:
        """URL should have trailing slash stripped."""
        config = PrometheusConfig(url="http://localhost:9090/")

        assert config.url == "http://localhost:9090"

    @pytest.mark.unit
    def test_url_validation_rejects_invalid_scheme(self) -> None:
        """URL must start with http:// or https://."""
        with pytest.raises(ValidationError):
            PrometheusConfig(url="ftp://localhost:9090")

    @pytest.mark.unit
    def test_timeout_validation(self) -> None:
        """Timeout must be positive."""
        with pytest.raises(ValidationError):
            PrometheusConfig(timeout=0)

        with pytest.raises(ValidationError):
            PrometheusConfig(timeout=-1)

    @pytest.mark.unit
    def test_basic_auth_config(self) -> None:
        """Config should support basic auth."""
        config = PrometheusConfig(
            auth_type="basic",
            username="admin",
            password="secret",
        )

        assert config.auth_type == "basic"
        assert config.username == "admin"
        assert config.password == "secret"

    @pytest.mark.unit
    def test_bearer_auth_config(self) -> None:
        """Config should support bearer token auth."""
        config = PrometheusConfig(
            auth_type="bearer",
            token="my-token",
        )

        assert config.auth_type == "bearer"
        assert config.token == "my-token"


class TestElasticsearchConfig:
    """Tests for ElasticsearchConfig."""

    @pytest.mark.unit
    def test_default_values(self) -> None:
        """Config should have sensible defaults."""
        config = ElasticsearchConfig()

        assert config.hosts == ["http://localhost:9200"]
        assert config.index_pattern == "kong-*"
        assert config.verify_certs is True
        assert config.timeout == 30

    @pytest.mark.unit
    def test_multiple_hosts(self) -> None:
        """Config should accept multiple hosts."""
        config = ElasticsearchConfig(
            hosts=["http://es1:9200", "http://es2:9200"],
        )

        assert len(config.hosts) == 2

    @pytest.mark.unit
    def test_hosts_validation_strips_trailing_slash(self) -> None:
        """Hosts should have trailing slashes stripped."""
        config = ElasticsearchConfig(
            hosts=["http://localhost:9200/"],
        )

        assert config.hosts == ["http://localhost:9200"]

    @pytest.mark.unit
    def test_hosts_validation_rejects_invalid_scheme(self) -> None:
        """Hosts must start with http:// or https://."""
        with pytest.raises(ValidationError):
            ElasticsearchConfig(hosts=["localhost:9200"])

    @pytest.mark.unit
    def test_cloud_id_config(self) -> None:
        """Config should support Elastic Cloud."""
        config = ElasticsearchConfig(
            cloud_id="my-deployment:xyz",
            api_key="my-api-key",
        )

        assert config.cloud_id == "my-deployment:xyz"
        assert config.api_key == "my-api-key"


class TestLokiConfig:
    """Tests for LokiConfig."""

    @pytest.mark.unit
    def test_default_values(self) -> None:
        """Config should have sensible defaults."""
        config = LokiConfig()

        assert config.url == "http://localhost:3100"
        assert config.timeout == 30
        assert config.org_id is None

    @pytest.mark.unit
    def test_multi_tenant_config(self) -> None:
        """Config should support multi-tenant Loki."""
        config = LokiConfig(
            url="https://loki.example.com",
            org_id="tenant-1",
        )

        assert config.org_id == "tenant-1"

    @pytest.mark.unit
    def test_auth_config(self) -> None:
        """Config should support authentication."""
        config = LokiConfig(
            username="user",
            password="pass",
        )

        assert config.username == "user"
        assert config.password == "pass"


class TestJaegerConfig:
    """Tests for JaegerConfig."""

    @pytest.mark.unit
    def test_default_values(self) -> None:
        """Config should have sensible defaults."""
        config = JaegerConfig()

        assert config.query_url == "http://localhost:16686"
        assert config.timeout == 30

    @pytest.mark.unit
    def test_custom_url(self) -> None:
        """Config should accept custom query URL."""
        config = JaegerConfig(query_url="https://jaeger.example.com")

        assert config.query_url == "https://jaeger.example.com"

    @pytest.mark.unit
    def test_auth_config(self) -> None:
        """Config should support authentication."""
        config = JaegerConfig(
            username="admin",
            password="secret",
        )

        assert config.username == "admin"
        assert config.password == "secret"


class TestZipkinConfig:
    """Tests for ZipkinConfig."""

    @pytest.mark.unit
    def test_default_values(self) -> None:
        """Config should have sensible defaults."""
        config = ZipkinConfig()

        assert config.url == "http://localhost:9411"
        assert config.timeout == 30

    @pytest.mark.unit
    def test_custom_url(self) -> None:
        """Config should accept custom URL."""
        config = ZipkinConfig(url="https://zipkin.example.com")

        assert config.url == "https://zipkin.example.com"


class TestObservabilityStackConfig:
    """Tests for ObservabilityStackConfig."""

    @pytest.mark.unit
    def test_empty_config(self) -> None:
        """Empty config should be valid."""
        config = ObservabilityStackConfig()

        assert config.prometheus is None
        assert config.elasticsearch is None
        assert config.loki is None
        assert config.jaeger is None
        assert config.zipkin is None

    @pytest.mark.unit
    def test_has_metrics_backend(self) -> None:
        """Should detect when Prometheus is configured."""
        config = ObservabilityStackConfig(
            prometheus=PrometheusConfig(),
        )

        assert config.has_metrics_backend is True

        empty_config = ObservabilityStackConfig()
        assert empty_config.has_metrics_backend is False

    @pytest.mark.unit
    def test_has_logs_backend(self) -> None:
        """Should detect when ES or Loki is configured."""
        es_config = ObservabilityStackConfig(
            elasticsearch=ElasticsearchConfig(),
        )
        assert es_config.has_logs_backend is True

        loki_config = ObservabilityStackConfig(
            loki=LokiConfig(),
        )
        assert loki_config.has_logs_backend is True

        empty_config = ObservabilityStackConfig()
        assert empty_config.has_logs_backend is False

    @pytest.mark.unit
    def test_has_tracing_backend(self) -> None:
        """Should detect when Jaeger or Zipkin is configured."""
        jaeger_config = ObservabilityStackConfig(
            jaeger=JaegerConfig(),
        )
        assert jaeger_config.has_tracing_backend is True

        zipkin_config = ObservabilityStackConfig(
            zipkin=ZipkinConfig(),
        )
        assert zipkin_config.has_tracing_backend is True

        empty_config = ObservabilityStackConfig()
        assert empty_config.has_tracing_backend is False

    @pytest.mark.unit
    def test_configured_backends(self) -> None:
        """Should list all configured backends."""
        config = ObservabilityStackConfig(
            prometheus=PrometheusConfig(),
            elasticsearch=ElasticsearchConfig(),
            jaeger=JaegerConfig(),
        )

        backends = config.configured_backends
        assert "prometheus" in backends
        assert "elasticsearch" in backends
        assert "jaeger" in backends
        assert "loki" not in backends
        assert "zipkin" not in backends

    @pytest.mark.unit
    def test_from_env_prometheus(self) -> None:
        """Should read Prometheus config from environment."""
        with patch.dict(os.environ, {"OPS_PROMETHEUS_URL": "http://prom:9090"}):
            config = ObservabilityStackConfig.from_env()

            assert config.prometheus is not None
            assert config.prometheus.url == "http://prom:9090"

    @pytest.mark.unit
    def test_from_env_elasticsearch(self) -> None:
        """Should read Elasticsearch config from environment."""
        with patch.dict(
            os.environ,
            {
                "OPS_ELASTICSEARCH_HOSTS": "http://es1:9200,http://es2:9200",
                "OPS_ELASTICSEARCH_INDEX": "my-kong-*",
            },
        ):
            config = ObservabilityStackConfig.from_env()

            assert config.elasticsearch is not None
            assert len(config.elasticsearch.hosts) == 2
            assert config.elasticsearch.index_pattern == "my-kong-*"

    @pytest.mark.unit
    def test_from_env_loki(self) -> None:
        """Should read Loki config from environment."""
        with patch.dict(os.environ, {"OPS_LOKI_URL": "http://loki:3100"}):
            config = ObservabilityStackConfig.from_env()

            assert config.loki is not None
            assert config.loki.url == "http://loki:3100"

    @pytest.mark.unit
    def test_from_env_jaeger(self) -> None:
        """Should read Jaeger config from environment."""
        with patch.dict(os.environ, {"OPS_JAEGER_URL": "http://jaeger:16686"}):
            config = ObservabilityStackConfig.from_env()

            assert config.jaeger is not None
            assert config.jaeger.query_url == "http://jaeger:16686"

    @pytest.mark.unit
    def test_from_env_zipkin(self) -> None:
        """Should read Zipkin config from environment."""
        with patch.dict(os.environ, {"OPS_ZIPKIN_URL": "http://zipkin:9411"}):
            config = ObservabilityStackConfig.from_env()

            assert config.zipkin is not None
            assert config.zipkin.url == "http://zipkin:9411"

    @pytest.mark.unit
    def test_from_env_overrides_base_config(self) -> None:
        """Environment variables should override base config."""
        base = {"prometheus": {"url": "http://old:9090"}}

        with patch.dict(os.environ, {"OPS_PROMETHEUS_URL": "http://new:9090"}):
            config = ObservabilityStackConfig.from_env(base)

            assert config.prometheus is not None
            assert config.prometheus.url == "http://new:9090"
