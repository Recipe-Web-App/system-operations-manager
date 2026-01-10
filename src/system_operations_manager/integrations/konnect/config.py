"""Konnect configuration management."""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, SecretStr

from system_operations_manager.integrations.konnect.exceptions import (
    KonnectConfigError,
)


class KonnectRegion(str, Enum):
    """Konnect API regions."""

    US = "us"
    EU = "eu"
    AU = "au"

    @property
    def api_url(self) -> str:
        """Get the API URL for this region."""
        return f"https://{self.value}.api.konghq.com"


class KonnectConfig(BaseModel):
    """Konnect configuration."""

    token: SecretStr = Field(..., description="Konnect Personal Access Token")
    region: KonnectRegion = Field(default=KonnectRegion.US, description="Konnect region")
    default_control_plane: str | None = Field(
        default=None, description="Default control plane name or ID"
    )

    model_config = {"use_enum_values": False}

    @property
    def api_url(self) -> str:
        """Get the API URL based on region."""
        return self.region.api_url

    @classmethod
    def get_config_path(cls) -> Path:
        """Get the config file path.

        Returns:
            Path to the config file (~/.config/ops/konnect.yaml).
        """
        config_dir = Path.home() / ".config" / "ops"
        return config_dir / "konnect.yaml"

    @classmethod
    def load(cls) -> KonnectConfig:
        """Load configuration from file or environment.

        Priority:
        1. Environment variables (KONG_KONNECT_TOKEN, KONG_KONNECT_REGION)
        2. Config file (~/.config/ops/konnect.yaml)

        Returns:
            Loaded configuration.

        Raises:
            KonnectConfigError: If configuration is missing or invalid.
        """
        # Check environment variables first
        env_token = os.environ.get("KONG_KONNECT_TOKEN")
        env_region = os.environ.get("KONG_KONNECT_REGION", "us")

        if env_token:
            try:
                region = KonnectRegion(env_region.lower())
            except ValueError:
                region = KonnectRegion.US
            return cls(token=SecretStr(env_token), region=region)

        # Load from config file
        config_path = cls.get_config_path()
        if not config_path.exists():
            raise KonnectConfigError(
                "Konnect not configured. Run 'ops kong konnect login' first.",
                details=f"Config file not found: {config_path}",
            )

        try:
            with config_path.open() as f:
                data = yaml.safe_load(f)

            if not data or "token" not in data:
                raise KonnectConfigError(
                    "Invalid config file. Run 'ops kong konnect login' to reconfigure.",
                    details="Missing 'token' in config file",
                )

            return cls(
                token=SecretStr(data["token"]),
                region=KonnectRegion(data.get("region", "us")),
                default_control_plane=data.get("default_control_plane"),
            )
        except yaml.YAMLError as e:
            raise KonnectConfigError(
                "Invalid config file format",
                details=str(e),
            ) from e

    def save(self) -> None:
        """Save configuration to file.

        Creates the config directory if it doesn't exist.
        Sets file permissions to 600 (owner read/write only).
        """
        config_path = self.get_config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)

        data: dict[str, Any] = {
            "token": self.token.get_secret_value(),
            "region": self.region.value,
        }
        if self.default_control_plane:
            data["default_control_plane"] = self.default_control_plane

        with config_path.open("w") as f:
            yaml.safe_dump(data, f, default_flow_style=False)

        # Set restrictive permissions (owner read/write only)
        config_path.chmod(0o600)

    @classmethod
    def exists(cls) -> bool:
        """Check if configuration exists.

        Returns:
            True if config file exists or environment variables are set.
        """
        if os.environ.get("KONG_KONNECT_TOKEN"):
            return True
        return cls.get_config_path().exists()
