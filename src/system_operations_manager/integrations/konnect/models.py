"""Konnect API data models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ControlPlane(BaseModel):
    """Kong Konnect Control Plane."""

    id: str = Field(..., description="Control plane ID")
    name: str = Field(..., description="Control plane name")
    description: str | None = Field(default=None, description="Description")
    cluster_type: str | None = Field(default=None, description="Cluster type")
    control_plane_endpoint: str | None = Field(
        default=None, description="Control plane endpoint URL"
    )
    telemetry_endpoint: str | None = Field(default=None, description="Telemetry endpoint URL")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    updated_at: datetime | None = Field(default=None, description="Update timestamp")

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> ControlPlane:
        """Create from Konnect API response.

        Args:
            data: API response data.

        Returns:
            ControlPlane instance.
        """
        config = data.get("config", {})
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description"),
            cluster_type=config.get("cluster_type"),
            control_plane_endpoint=config.get("control_plane_endpoint"),
            telemetry_endpoint=config.get("telemetry_endpoint"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


class DataPlaneCertificate(BaseModel):
    """Data Plane client certificate."""

    id: str = Field(..., description="Certificate ID")
    cert: str = Field(..., description="Certificate PEM")
    key: str | None = Field(default=None, description="Private key PEM")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    updated_at: datetime | None = Field(default=None, description="Update timestamp")

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> DataPlaneCertificate:
        """Create from Konnect API response.

        Args:
            data: API response data. May be wrapped in an "item" key.

        Returns:
            DataPlaneCertificate instance.
        """
        # Handle response wrapped in "item" key
        if "item" in data:
            data = data["item"]

        return cls(
            id=data["id"],
            cert=data["cert"],
            key=data.get("key"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


class ControlPlaneListResponse(BaseModel):
    """Response for listing control planes."""

    data: list[ControlPlane] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> ControlPlaneListResponse:
        """Create from Konnect API response.

        Args:
            data: API response data.

        Returns:
            ControlPlaneListResponse instance.
        """
        control_planes = [ControlPlane.from_api_response(cp) for cp in data.get("data", [])]
        return cls(
            data=control_planes,
            meta=data.get("meta", {}),
        )
