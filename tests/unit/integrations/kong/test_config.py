"""Unit tests for Kong configuration models."""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from system_operations_manager.integrations.kong.config import (
    KongAuthConfig,
    KongConnectionConfig,
    KongEnterpriseConfig,
    KongPluginConfig,
)


class TestKongConnectionConfig:
    """Tests for KongConnectionConfig model."""

    @pytest.mark.unit
    def test_connection_config_defaults(self) -> None:
        """Config should have sensible defaults."""
        config = KongConnectionConfig()

        assert config.base_url == "http://localhost:8001"
        assert config.timeout == 30
        assert config.verify_ssl is True
        assert config.retries == 3

    @pytest.mark.unit
    def test_connection_config_base_url_http(self) -> None:
        """Config should accept http URLs."""
        config = KongConnectionConfig(base_url="http://kong.local:8001")

        assert config.base_url == "http://kong.local:8001"

    @pytest.mark.unit
    def test_connection_config_base_url_https(self) -> None:
        """Config should accept https URLs."""
        config = KongConnectionConfig(base_url="https://kong.local:8443")

        assert config.base_url == "https://kong.local:8443"

    @pytest.mark.unit
    def test_connection_config_base_url_strips_trailing_slash(self) -> None:
        """Config should strip trailing slashes from base_url."""
        config = KongConnectionConfig(base_url="http://kong.local:8001/")

        assert config.base_url == "http://kong.local:8001"

    @pytest.mark.unit
    def test_connection_config_base_url_invalid_scheme_raises(self) -> None:
        """Config should reject URLs without http/https scheme."""
        with pytest.raises(ValidationError) as exc_info:
            KongConnectionConfig(base_url="ftp://kong.local")

        assert "base_url must start with http:// or https://" in str(exc_info.value)

    @pytest.mark.unit
    def test_connection_config_base_url_no_scheme_raises(self) -> None:
        """Config should reject URLs without any scheme."""
        with pytest.raises(ValidationError) as exc_info:
            KongConnectionConfig(base_url="kong.local:8001")

        assert "base_url must start with http:// or https://" in str(exc_info.value)

    @pytest.mark.unit
    def test_connection_config_timeout_positive(self) -> None:
        """Config should accept positive timeout."""
        config = KongConnectionConfig(timeout=60)

        assert config.timeout == 60

    @pytest.mark.unit
    def test_connection_config_timeout_zero_raises(self) -> None:
        """Config should reject zero timeout."""
        with pytest.raises(ValidationError) as exc_info:
            KongConnectionConfig(timeout=0)

        assert "timeout must be positive" in str(exc_info.value)

    @pytest.mark.unit
    def test_connection_config_timeout_negative_raises(self) -> None:
        """Config should reject negative timeout."""
        with pytest.raises(ValidationError) as exc_info:
            KongConnectionConfig(timeout=-5)

        assert "timeout must be positive" in str(exc_info.value)

    @pytest.mark.unit
    def test_connection_config_retries_zero_allowed(self) -> None:
        """Config should accept zero retries."""
        config = KongConnectionConfig(retries=0)

        assert config.retries == 0

    @pytest.mark.unit
    def test_connection_config_retries_positive(self) -> None:
        """Config should accept positive retries."""
        config = KongConnectionConfig(retries=5)

        assert config.retries == 5

    @pytest.mark.unit
    def test_connection_config_retries_negative_raises(self) -> None:
        """Config should reject negative retries."""
        with pytest.raises(ValidationError) as exc_info:
            KongConnectionConfig(retries=-1)

        assert "retries must be non-negative" in str(exc_info.value)

    @pytest.mark.unit
    def test_connection_config_extra_fields_forbidden(self) -> None:
        """Config should reject unknown fields."""
        with pytest.raises(ValidationError):
            KongConnectionConfig(unknown_field="value")  # type: ignore[call-arg]


class TestKongAuthConfig:
    """Tests for KongAuthConfig model."""

    @pytest.mark.unit
    def test_auth_config_defaults(self) -> None:
        """Auth config should have sensible defaults."""
        config = KongAuthConfig()

        assert config.type == "none"
        assert config.api_key is None
        assert config.header_name == "Kong-Admin-Token"
        assert config.cert_path is None
        assert config.key_path is None
        assert config.ca_path is None

    @pytest.mark.unit
    def test_auth_config_type_none(self) -> None:
        """Auth config should accept 'none' type."""
        config = KongAuthConfig(type="none")

        assert config.type == "none"

    @pytest.mark.unit
    def test_auth_config_type_api_key(self) -> None:
        """Auth config should accept 'api_key' type."""
        config = KongAuthConfig(type="api_key", api_key="secret-key")

        assert config.type == "api_key"
        assert config.api_key == "secret-key"

    @pytest.mark.unit
    def test_auth_config_type_mtls(self) -> None:
        """Auth config should accept 'mtls' type."""
        config = KongAuthConfig(
            type="mtls",
            cert_path="/path/to/cert.pem",
            key_path="/path/to/key.pem",
        )

        assert config.type == "mtls"
        assert config.cert_path == "/path/to/cert.pem"
        assert config.key_path == "/path/to/key.pem"

    @pytest.mark.unit
    def test_auth_config_invalid_type_raises(self) -> None:
        """Auth config should reject invalid auth types."""
        with pytest.raises(ValidationError) as exc_info:
            KongAuthConfig(type="invalid")  # type: ignore[arg-type]

        # Pydantic v2 validates Literal types
        assert "type" in str(exc_info.value).lower()

    @pytest.mark.unit
    def test_auth_config_custom_header_name(self) -> None:
        """Auth config should accept custom header name."""
        config = KongAuthConfig(type="api_key", header_name="X-Custom-Token")

        assert config.header_name == "X-Custom-Token"

    @pytest.mark.unit
    def test_auth_config_extra_fields_forbidden(self) -> None:
        """Auth config should reject unknown fields."""
        with pytest.raises(ValidationError):
            KongAuthConfig(unknown_field="value")  # type: ignore[call-arg]


class TestKongEnterpriseConfig:
    """Tests for KongEnterpriseConfig model."""

    @pytest.mark.unit
    def test_enterprise_config_defaults(self) -> None:
        """Enterprise config should default to disabled."""
        config = KongEnterpriseConfig()

        assert config.enabled is False

    @pytest.mark.unit
    def test_enterprise_config_enabled(self) -> None:
        """Enterprise config should accept enabled flag."""
        config = KongEnterpriseConfig(enabled=True)

        assert config.enabled is True


class TestKongPluginConfig:
    """Tests for KongPluginConfig model."""

    @pytest.fixture(autouse=True)
    def setup_model(self) -> None:
        """Ensure KongPluginConfig is fully defined."""
        from system_operations_manager.integrations.observability.config import (
            ObservabilityStackConfig,
        )

        KongPluginConfig.model_rebuild(
            _types_namespace={"ObservabilityStackConfig": ObservabilityStackConfig}
        )

    @pytest.mark.unit
    def test_plugin_config_defaults(self) -> None:
        """Plugin config should have sensible defaults."""
        config = KongPluginConfig()

        assert config.connection.base_url == "http://localhost:8001"
        assert config.auth.type == "none"
        assert config.output_format == "table"
        assert config.default_workspace == "default"
        assert config.enterprise.enabled is False
        assert config.observability is None

    @pytest.mark.unit
    def test_plugin_config_output_format_table(self) -> None:
        """Plugin config should accept 'table' output format."""
        config = KongPluginConfig(output_format="table")

        assert config.output_format == "table"

    @pytest.mark.unit
    def test_plugin_config_output_format_json(self) -> None:
        """Plugin config should accept 'json' output format."""
        config = KongPluginConfig(output_format="json")

        assert config.output_format == "json"

    @pytest.mark.unit
    def test_plugin_config_output_format_yaml(self) -> None:
        """Plugin config should accept 'yaml' output format."""
        config = KongPluginConfig(output_format="yaml")

        assert config.output_format == "yaml"

    @pytest.mark.unit
    def test_plugin_config_invalid_output_format_raises(self) -> None:
        """Plugin config should reject invalid output formats."""
        with pytest.raises(ValidationError) as exc_info:
            KongPluginConfig(output_format="xml")  # type: ignore[arg-type]

        assert "output_format" in str(exc_info.value).lower()

    @pytest.mark.unit
    def test_plugin_config_custom_workspace(self) -> None:
        """Plugin config should accept custom workspace."""
        config = KongPluginConfig(default_workspace="production")

        assert config.default_workspace == "production"

    @pytest.mark.unit
    def test_plugin_config_with_connection(self) -> None:
        """Plugin config should accept connection config."""
        config = KongPluginConfig(
            connection=KongConnectionConfig(base_url="https://kong.prod:8443")
        )

        assert config.connection.base_url == "https://kong.prod:8443"

    @pytest.mark.unit
    def test_plugin_config_with_auth(self) -> None:
        """Plugin config should accept auth config."""
        config = KongPluginConfig(auth=KongAuthConfig(type="api_key", api_key="secret"))

        assert config.auth.type == "api_key"
        assert config.auth.api_key == "secret"


class TestKongPluginConfigFromEnv:
    """Tests for KongPluginConfig.from_env class method."""

    @pytest.mark.unit
    def test_from_env_without_env_vars(self) -> None:
        """from_env should return defaults when no env vars set."""
        with patch.dict(os.environ, {}, clear=True):
            config = KongPluginConfig.from_env()

        assert config.connection.base_url == "http://localhost:8001"
        assert config.auth.type == "none"

    @pytest.mark.unit
    def test_from_env_base_url(self) -> None:
        """from_env should read OPS_KONG_BASE_URL."""
        with patch.dict(os.environ, {"OPS_KONG_BASE_URL": "https://kong.prod:8443"}):
            config = KongPluginConfig.from_env()

        assert config.connection.base_url == "https://kong.prod:8443"

    @pytest.mark.unit
    def test_from_env_api_key(self) -> None:
        """from_env should read OPS_KONG_API_KEY."""
        with patch.dict(os.environ, {"OPS_KONG_API_KEY": "my-secret-key"}):
            config = KongPluginConfig.from_env()

        assert config.auth.api_key == "my-secret-key"

    @pytest.mark.unit
    def test_from_env_api_key_auto_sets_auth_type(self) -> None:
        """from_env should auto-set auth type to api_key when key provided."""
        with patch.dict(os.environ, {"OPS_KONG_API_KEY": "my-secret-key"}):
            config = KongPluginConfig.from_env()

        assert config.auth.type == "api_key"

    @pytest.mark.unit
    def test_from_env_explicit_auth_type(self) -> None:
        """from_env should read OPS_KONG_AUTH_TYPE."""
        with patch.dict(os.environ, {"OPS_KONG_AUTH_TYPE": "mtls"}):
            config = KongPluginConfig.from_env()

        assert config.auth.type == "mtls"

    @pytest.mark.unit
    def test_from_env_workspace(self) -> None:
        """from_env should read OPS_KONG_WORKSPACE."""
        with patch.dict(os.environ, {"OPS_KONG_WORKSPACE": "production"}):
            config = KongPluginConfig.from_env()

        assert config.default_workspace == "production"

    @pytest.mark.unit
    def test_from_env_output_format(self) -> None:
        """from_env should read OPS_KONG_OUTPUT."""
        with patch.dict(os.environ, {"OPS_KONG_OUTPUT": "json"}):
            config = KongPluginConfig.from_env()

        assert config.output_format == "json"

    @pytest.mark.unit
    def test_from_env_with_base_config(self) -> None:
        """from_env should use base_config as starting point."""
        base_config: dict[str, Any] = {
            "connection": {"base_url": "http://base:8001"},
            "default_workspace": "base-workspace",
        }

        with patch.dict(os.environ, {}):
            config = KongPluginConfig.from_env(base_config)

        assert config.connection.base_url == "http://base:8001"
        assert config.default_workspace == "base-workspace"

    @pytest.mark.unit
    def test_from_env_overrides_base_config(self) -> None:
        """from_env should override base_config with env vars."""
        base_config: dict[str, Any] = {
            "connection": {"base_url": "http://base:8001"},
        }

        with patch.dict(os.environ, {"OPS_KONG_BASE_URL": "https://env:8443"}):
            config = KongPluginConfig.from_env(base_config)

        assert config.connection.base_url == "https://env:8443"

    @pytest.mark.unit
    def test_from_env_preserves_explicit_auth_type(self) -> None:
        """from_env should not auto-set auth type if already set in base_config."""
        base_config: dict[str, Any] = {
            "auth": {"type": "mtls"},
        }

        with patch.dict(os.environ, {"OPS_KONG_API_KEY": "secret"}):
            config = KongPluginConfig.from_env(base_config)

        # API key is set but auth type remains mtls since it was explicitly set
        assert config.auth.api_key == "secret"
        assert config.auth.type == "mtls"

    @pytest.mark.unit
    def test_from_env_multiple_vars(self) -> None:
        """from_env should handle multiple env vars at once."""
        env_vars = {
            "OPS_KONG_BASE_URL": "https://kong.prod:8443",
            "OPS_KONG_API_KEY": "prod-key",
            "OPS_KONG_WORKSPACE": "production",
            "OPS_KONG_OUTPUT": "yaml",
        }

        with patch.dict(os.environ, env_vars):
            config = KongPluginConfig.from_env()

        assert config.connection.base_url == "https://kong.prod:8443"
        assert config.auth.api_key == "prod-key"
        assert config.auth.type == "api_key"
        assert config.default_workspace == "production"
        assert config.output_format == "yaml"
