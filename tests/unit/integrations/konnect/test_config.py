"""Unit tests for Konnect configuration."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import SecretStr

from system_operations_manager.integrations.konnect.config import (
    KonnectConfig,
    KonnectRegion,
)
from system_operations_manager.integrations.konnect.exceptions import (
    KonnectConfigError,
)


class TestKonnectRegion:
    """Tests for KonnectRegion enum."""

    @pytest.mark.unit
    def test_region_values(self) -> None:
        """Region enum should have expected values."""
        assert KonnectRegion.US.value == "us"
        assert KonnectRegion.EU.value == "eu"
        assert KonnectRegion.AU.value == "au"

    @pytest.mark.unit
    def test_region_api_urls(self) -> None:
        """Region should return correct API URLs."""
        assert KonnectRegion.US.api_url == "https://us.api.konghq.com"
        assert KonnectRegion.EU.api_url == "https://eu.api.konghq.com"
        assert KonnectRegion.AU.api_url == "https://au.api.konghq.com"


class TestKonnectConfig:
    """Tests for KonnectConfig."""

    @pytest.mark.unit
    def test_config_creation(self) -> None:
        """Config should be created with required fields."""
        config = KonnectConfig(
            token=SecretStr("test-token"),
            region=KonnectRegion.US,
        )

        assert config.token.get_secret_value() == "test-token"
        assert config.region == KonnectRegion.US
        assert config.default_control_plane is None

    @pytest.mark.unit
    def test_config_with_default_control_plane(self) -> None:
        """Config should accept default_control_plane."""
        config = KonnectConfig(
            token=SecretStr("test-token"),
            region=KonnectRegion.EU,
            default_control_plane="my-cp",
        )

        assert config.default_control_plane == "my-cp"

    @pytest.mark.unit
    def test_api_url_property(self) -> None:
        """api_url property should return region's API URL."""
        config = KonnectConfig(
            token=SecretStr("test-token"),
            region=KonnectRegion.AU,
        )

        assert config.api_url == "https://au.api.konghq.com"

    @pytest.mark.unit
    def test_get_config_path(self) -> None:
        """get_config_path should return ~/.config/ops/konnect.yaml."""
        path = KonnectConfig.get_config_path()

        assert path == Path.home() / ".config" / "ops" / "konnect.yaml"


class TestKonnectConfigLoad:
    """Tests for KonnectConfig.load()."""

    @pytest.mark.unit
    def test_load_from_env_vars(self) -> None:
        """load() should use environment variables when set."""
        with patch.dict(
            os.environ,
            {"KONG_KONNECT_TOKEN": "env-token", "KONG_KONNECT_REGION": "eu"},
        ):
            config = KonnectConfig.load()

            assert config.token.get_secret_value() == "env-token"
            assert config.region == KonnectRegion.EU

    @pytest.mark.unit
    def test_load_from_env_default_region(self) -> None:
        """load() should default to US region when not specified."""
        with patch.dict(
            os.environ,
            {"KONG_KONNECT_TOKEN": "env-token"},
            clear=False,
        ):
            # Remove region var if present
            os.environ.pop("KONG_KONNECT_REGION", None)
            config = KonnectConfig.load()

            assert config.region == KonnectRegion.US

    @pytest.mark.unit
    def test_load_missing_config_raises_error(self, tmp_path: Path) -> None:
        """load() should raise error when config file doesn't exist."""
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(
                KonnectConfig, "get_config_path", return_value=tmp_path / "nonexistent.yaml"
            ),
        ):
            # Clear env vars
            os.environ.pop("KONG_KONNECT_TOKEN", None)

            with pytest.raises(KonnectConfigError) as exc_info:
                KonnectConfig.load()

            assert "not configured" in str(exc_info.value)

    @pytest.mark.unit
    def test_load_from_file(self, tmp_path: Path) -> None:
        """load() should read from config file."""
        config_file = tmp_path / "konnect.yaml"
        config_file.write_text("token: file-token\nregion: au\ndefault_control_plane: my-cp\n")

        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(KonnectConfig, "get_config_path", return_value=config_file),
        ):
            os.environ.pop("KONG_KONNECT_TOKEN", None)
            config = KonnectConfig.load()

            assert config.token.get_secret_value() == "file-token"
            assert config.region == KonnectRegion.AU
            assert config.default_control_plane == "my-cp"

    @pytest.mark.unit
    def test_load_invalid_yaml_raises_error(self, tmp_path: Path) -> None:
        """load() should raise error for invalid YAML."""
        config_file = tmp_path / "konnect.yaml"
        config_file.write_text("invalid: [yaml: content")

        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(KonnectConfig, "get_config_path", return_value=config_file),
        ):
            os.environ.pop("KONG_KONNECT_TOKEN", None)

            with pytest.raises(KonnectConfigError) as exc_info:
                KonnectConfig.load()

            assert "Invalid config file" in str(exc_info.value)

    @pytest.mark.unit
    def test_load_missing_token_raises_error(self, tmp_path: Path) -> None:
        """load() should raise error when token is missing from file."""
        config_file = tmp_path / "konnect.yaml"
        config_file.write_text("region: us\n")

        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(KonnectConfig, "get_config_path", return_value=config_file),
        ):
            os.environ.pop("KONG_KONNECT_TOKEN", None)

            with pytest.raises(KonnectConfigError) as exc_info:
                KonnectConfig.load()

            assert "Invalid config file" in str(exc_info.value)


class TestKonnectConfigSave:
    """Tests for KonnectConfig.save()."""

    @pytest.mark.unit
    def test_save_creates_file(self, tmp_path: Path) -> None:
        """save() should create config file."""
        config_file = tmp_path / "ops" / "konnect.yaml"

        config = KonnectConfig(
            token=SecretStr("save-token"),
            region=KonnectRegion.EU,
        )

        with patch.object(KonnectConfig, "get_config_path", return_value=config_file):
            config.save()

        assert config_file.exists()
        content = config_file.read_text()
        assert "save-token" in content
        assert "eu" in content

    @pytest.mark.unit
    def test_save_sets_permissions(self, tmp_path: Path) -> None:
        """save() should set 600 permissions on config file."""
        config_file = tmp_path / "konnect.yaml"

        config = KonnectConfig(
            token=SecretStr("secure-token"),
            region=KonnectRegion.US,
        )

        with patch.object(KonnectConfig, "get_config_path", return_value=config_file):
            config.save()

        # Check permissions (0o600 = owner read/write only)
        assert (config_file.stat().st_mode & 0o777) == 0o600

    @pytest.mark.unit
    def test_save_includes_default_control_plane(self, tmp_path: Path) -> None:
        """save() should include default_control_plane if set."""
        config_file = tmp_path / "konnect.yaml"

        config = KonnectConfig(
            token=SecretStr("token"),
            region=KonnectRegion.US,
            default_control_plane="my-default-cp",
        )

        with patch.object(KonnectConfig, "get_config_path", return_value=config_file):
            config.save()

        content = config_file.read_text()
        assert "my-default-cp" in content


class TestKonnectConfigExists:
    """Tests for KonnectConfig.exists()."""

    @pytest.mark.unit
    def test_exists_with_env_var(self) -> None:
        """exists() should return True when env var is set."""
        with patch.dict(os.environ, {"KONG_KONNECT_TOKEN": "token"}):
            assert KonnectConfig.exists() is True

    @pytest.mark.unit
    def test_exists_with_file(self, tmp_path: Path) -> None:
        """exists() should return True when config file exists."""
        config_file = tmp_path / "konnect.yaml"
        config_file.write_text("token: test\n")

        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(KonnectConfig, "get_config_path", return_value=config_file),
        ):
            os.environ.pop("KONG_KONNECT_TOKEN", None)
            assert KonnectConfig.exists() is True

    @pytest.mark.unit
    def test_exists_without_config(self, tmp_path: Path) -> None:
        """exists() should return False when no config exists."""
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(
                KonnectConfig, "get_config_path", return_value=tmp_path / "nonexistent.yaml"
            ),
        ):
            os.environ.pop("KONG_KONNECT_TOKEN", None)
            assert KonnectConfig.exists() is False
