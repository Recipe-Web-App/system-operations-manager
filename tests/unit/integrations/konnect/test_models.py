"""Unit tests for Konnect API models."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from system_operations_manager.integrations.konnect.models import (
    ControlPlane,
    ControlPlaneListResponse,
    DataPlaneCertificate,
)


class TestControlPlane:
    """Tests for ControlPlane model."""

    @pytest.mark.unit
    def test_control_plane_creation(self) -> None:
        """ControlPlane should be created with required fields."""
        cp = ControlPlane(
            id="cp-123",
            name="test-cp",
        )

        assert cp.id == "cp-123"
        assert cp.name == "test-cp"
        assert cp.description is None
        assert cp.cluster_type is None

    @pytest.mark.unit
    def test_control_plane_with_all_fields(self) -> None:
        """ControlPlane should accept all optional fields."""
        cp = ControlPlane(
            id="cp-123",
            name="test-cp",
            description="Test control plane",
            cluster_type="CLUSTER_TYPE_K8S_INGRESS_CONTROLLER",
            control_plane_endpoint="https://test.cp0.konghq.com",
            telemetry_endpoint="https://test.tp0.konghq.com",
            created_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
            updated_at=datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC),
        )

        assert cp.description == "Test control plane"
        assert cp.cluster_type == "CLUSTER_TYPE_K8S_INGRESS_CONTROLLER"
        assert cp.control_plane_endpoint == "https://test.cp0.konghq.com"
        assert cp.telemetry_endpoint == "https://test.tp0.konghq.com"

    @pytest.mark.unit
    def test_control_plane_from_api_response(self) -> None:
        """ControlPlane.from_api_response should parse API data."""
        api_data = {
            "id": "cp-456",
            "name": "api-cp",
            "description": "From API",
            "config": {
                "cluster_type": "CLUSTER_TYPE_CONTROL_PLANE",
                "control_plane_endpoint": "https://api.cp0.konghq.com",
                "telemetry_endpoint": "https://api.tp0.konghq.com",
            },
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
        }

        cp = ControlPlane.from_api_response(api_data)

        assert cp.id == "cp-456"
        assert cp.name == "api-cp"
        assert cp.description == "From API"
        assert cp.cluster_type == "CLUSTER_TYPE_CONTROL_PLANE"
        assert cp.control_plane_endpoint == "https://api.cp0.konghq.com"

    @pytest.mark.unit
    def test_control_plane_from_api_response_minimal(self) -> None:
        """ControlPlane.from_api_response should handle minimal data."""
        api_data = {
            "id": "cp-789",
            "name": "minimal-cp",
        }

        cp = ControlPlane.from_api_response(api_data)

        assert cp.id == "cp-789"
        assert cp.name == "minimal-cp"
        assert cp.cluster_type is None
        assert cp.control_plane_endpoint is None


class TestDataPlaneCertificate:
    """Tests for DataPlaneCertificate model."""

    @pytest.mark.unit
    def test_certificate_creation(self) -> None:
        """DataPlaneCertificate should be created with required fields."""
        cert = DataPlaneCertificate(
            id="cert-123",
            cert="-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
        )

        assert cert.id == "cert-123"
        assert "CERTIFICATE" in cert.cert
        assert cert.key is None

    @pytest.mark.unit
    def test_certificate_with_key(self) -> None:
        """DataPlaneCertificate should accept private key."""
        cert = DataPlaneCertificate(
            id="cert-123",
            cert="-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
            key="-----BEGIN TEST KEY-----\nkey\n-----END TEST KEY-----",
        )

        assert cert.key is not None
        assert "TEST KEY" in cert.key

    @pytest.mark.unit
    def test_certificate_from_api_response(self) -> None:
        """DataPlaneCertificate.from_api_response should parse API data."""
        api_data = {
            "id": "cert-456",
            "cert": "-----BEGIN CERTIFICATE-----\napi-cert\n-----END CERTIFICATE-----",
            "created_at": 1704067200,  # Unix timestamp
            "updated_at": 1704153600,
        }

        cert = DataPlaneCertificate.from_api_response(api_data)

        assert cert.id == "cert-456"
        assert "api-cert" in cert.cert

    @pytest.mark.unit
    def test_certificate_from_api_response_with_item_wrapper(self) -> None:
        """DataPlaneCertificate.from_api_response should handle item wrapper."""
        api_data = {
            "item": {
                "id": "cert-789",
                "cert": "-----BEGIN CERTIFICATE-----\nwrapped\n-----END CERTIFICATE-----",
                "created_at": 1704067200,
                "updated_at": 1704153600,
            }
        }

        cert = DataPlaneCertificate.from_api_response(api_data)

        assert cert.id == "cert-789"
        assert "wrapped" in cert.cert


class TestControlPlaneListResponse:
    """Tests for ControlPlaneListResponse model."""

    @pytest.mark.unit
    def test_list_response_creation(self) -> None:
        """ControlPlaneListResponse should be created with defaults."""
        response = ControlPlaneListResponse()

        assert response.data == []
        assert response.meta == {}

    @pytest.mark.unit
    def test_list_response_from_api(self) -> None:
        """ControlPlaneListResponse.from_api_response should parse list."""
        api_data = {
            "data": [
                {"id": "cp-1", "name": "first-cp", "config": {}},
                {"id": "cp-2", "name": "second-cp", "config": {}},
            ],
            "meta": {"page": {"total": 2}},
        }

        response = ControlPlaneListResponse.from_api_response(api_data)

        assert len(response.data) == 2
        assert response.data[0].id == "cp-1"
        assert response.data[1].name == "second-cp"
        assert response.meta["page"]["total"] == 2

    @pytest.mark.unit
    def test_list_response_from_empty_api(self) -> None:
        """ControlPlaneListResponse.from_api_response should handle empty list."""
        api_data: dict[str, list[dict[str, str]] | dict[str, int]] = {"data": [], "meta": {}}

        response = ControlPlaneListResponse.from_api_response(api_data)

        assert response.data == []
