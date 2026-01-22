"""Integration tests for Konnect client with mocked HTTP responses.

These tests verify the full request/response cycle using respx to mock
the Konnect API without making real HTTP calls.
"""

from __future__ import annotations

import pytest
import respx
from httpx import Response
from pydantic import SecretStr

from system_operations_manager.integrations.kong.models.route import Route
from system_operations_manager.integrations.kong.models.service import Service
from system_operations_manager.integrations.konnect.client import KonnectClient
from system_operations_manager.integrations.konnect.config import (
    KonnectConfig,
    KonnectRegion,
)
from system_operations_manager.integrations.konnect.exceptions import (
    KonnectAuthError,
    KonnectNotFoundError,
)


@pytest.fixture
def konnect_config() -> KonnectConfig:
    """Create test Konnect config."""
    return KonnectConfig(
        token=SecretStr("test-token-12345"),
        region=KonnectRegion.US,
        default_control_plane="test-cp",
    )


@pytest.fixture
def base_url() -> str:
    """Base URL for Konnect API."""
    return "https://us.api.konghq.com"


class TestKonnectClientServiceIntegration:
    """Integration tests for service CRUD operations."""

    @pytest.mark.integration
    @respx.mock
    def test_list_services_full_flow(
        self,
        konnect_config: KonnectConfig,
        base_url: str,
    ) -> None:
        """Test listing services with full HTTP mock."""
        # Setup mock
        respx.get(f"{base_url}/v2/control-planes/cp-123/core-entities/services").mock(
            return_value=Response(
                200,
                json={
                    "data": [
                        {
                            "id": "svc-001",
                            "name": "auth-service",
                            "host": "auth.internal",
                            "port": 8080,
                            "protocol": "http",
                            "enabled": True,
                            "tags": ["production"],
                        },
                        {
                            "id": "svc-002",
                            "name": "user-service",
                            "host": "users.internal",
                            "port": 8081,
                            "protocol": "http",
                            "enabled": True,
                            "tags": ["production"],
                        },
                    ],
                    "offset": None,
                },
            )
        )

        # Execute
        with KonnectClient(konnect_config) as client:
            services, next_offset = client.list_services("cp-123")

        # Verify
        assert len(services) == 2
        assert services[0].name == "auth-service"
        assert services[0].host == "auth.internal"
        assert services[1].name == "user-service"
        assert next_offset is None

    @pytest.mark.integration
    @respx.mock
    def test_create_service_full_flow(
        self,
        konnect_config: KonnectConfig,
        base_url: str,
    ) -> None:
        """Test creating a service with full HTTP mock."""
        # Setup mock
        respx.post(f"{base_url}/v2/control-planes/cp-123/core-entities/services").mock(
            return_value=Response(
                201,
                json={
                    "id": "svc-new-001",
                    "name": "new-service",
                    "host": "new.internal",
                    "port": 8080,
                    "protocol": "http",
                    "enabled": True,
                    "created_at": 1704067200,
                    "updated_at": 1704067200,
                },
            )
        )

        # Execute
        service = Service(name="new-service", host="new.internal", port=8080)
        with KonnectClient(konnect_config) as client:
            result = client.create_service("cp-123", service)

        # Verify
        assert result.id == "svc-new-001"
        assert result.name == "new-service"
        assert result.host == "new.internal"

    @pytest.mark.integration
    @respx.mock
    def test_get_service_not_found(
        self,
        konnect_config: KonnectConfig,
        base_url: str,
    ) -> None:
        """Test getting non-existent service returns proper error."""
        # Setup mock
        respx.get(f"{base_url}/v2/control-planes/cp-123/core-entities/services/nonexistent").mock(
            return_value=Response(
                404,
                json={"message": "Service not found"},
            )
        )

        # Execute & Verify
        with KonnectClient(konnect_config) as client, pytest.raises(KonnectNotFoundError):
            client.get_service("cp-123", "nonexistent")

    @pytest.mark.integration
    @respx.mock
    def test_update_service_full_flow(
        self,
        konnect_config: KonnectConfig,
        base_url: str,
    ) -> None:
        """Test updating a service with full HTTP mock."""
        # Setup mock
        respx.patch(f"{base_url}/v2/control-planes/cp-123/core-entities/services/svc-001").mock(
            return_value=Response(
                200,
                json={
                    "id": "svc-001",
                    "name": "auth-service",
                    "host": "auth-v2.internal",
                    "port": 9090,
                    "protocol": "http",
                    "enabled": True,
                },
            )
        )

        # Execute
        service = Service(name="auth-service", host="auth-v2.internal", port=9090)
        with KonnectClient(konnect_config) as client:
            result = client.update_service("cp-123", "svc-001", service)

        # Verify
        assert result.host == "auth-v2.internal"
        assert result.port == 9090

    @pytest.mark.integration
    @respx.mock
    def test_delete_service_full_flow(
        self,
        konnect_config: KonnectConfig,
        base_url: str,
    ) -> None:
        """Test deleting a service with full HTTP mock."""
        # Setup mock
        respx.delete(f"{base_url}/v2/control-planes/cp-123/core-entities/services/svc-001").mock(
            return_value=Response(204)
        )

        # Execute - should not raise
        with KonnectClient(konnect_config) as client:
            client.delete_service("cp-123", "svc-001")


class TestKonnectClientRouteIntegration:
    """Integration tests for route CRUD operations."""

    @pytest.mark.integration
    @respx.mock
    def test_list_routes_for_service(
        self,
        konnect_config: KonnectConfig,
        base_url: str,
    ) -> None:
        """Test listing routes for a service with full HTTP mock."""
        # Setup mock
        respx.get(
            f"{base_url}/v2/control-planes/cp-123/core-entities/services/auth-service/routes"
        ).mock(
            return_value=Response(
                200,
                json={
                    "data": [
                        {
                            "id": "route-001",
                            "name": "auth-login",
                            "paths": ["/auth/login"],
                            "methods": ["POST"],
                            "tags": ["auth"],
                        },
                        {
                            "id": "route-002",
                            "name": "auth-logout",
                            "paths": ["/auth/logout"],
                            "methods": ["POST"],
                            "tags": ["auth"],
                        },
                    ],
                    "offset": None,
                },
            )
        )

        # Execute
        with KonnectClient(konnect_config) as client:
            routes, _ = client.list_routes("cp-123", service_name_or_id="auth-service")

        # Verify
        assert len(routes) == 2
        assert routes[0].name == "auth-login"
        assert routes[0].paths == ["/auth/login"]
        assert routes[1].name == "auth-logout"

    @pytest.mark.integration
    @respx.mock
    def test_create_route_for_service(
        self,
        konnect_config: KonnectConfig,
        base_url: str,
    ) -> None:
        """Test creating a route for a service with full HTTP mock."""
        # Setup mock
        respx.post(
            f"{base_url}/v2/control-planes/cp-123/core-entities/services/auth-service/routes"
        ).mock(
            return_value=Response(
                201,
                json={
                    "id": "route-new-001",
                    "name": "auth-refresh",
                    "paths": ["/auth/refresh"],
                    "methods": ["POST"],
                    "strip_path": True,
                },
            )
        )

        # Execute
        route = Route(name="auth-refresh", paths=["/auth/refresh"], methods=["POST"])
        with KonnectClient(konnect_config) as client:
            result = client.create_route("cp-123", route, service_name_or_id="auth-service")

        # Verify
        assert result.id == "route-new-001"
        assert result.name == "auth-refresh"

    @pytest.mark.integration
    @respx.mock
    def test_update_route_full_flow(
        self,
        konnect_config: KonnectConfig,
        base_url: str,
    ) -> None:
        """Test updating a route with full HTTP mock."""
        # Setup mock
        respx.patch(f"{base_url}/v2/control-planes/cp-123/core-entities/routes/route-001").mock(
            return_value=Response(
                200,
                json={
                    "id": "route-001",
                    "name": "auth-login",
                    "paths": ["/api/v2/auth/login"],
                    "methods": ["POST", "OPTIONS"],
                    "strip_path": True,
                },
            )
        )

        # Execute
        route = Route(
            name="auth-login",
            paths=["/api/v2/auth/login"],
            methods=["POST", "OPTIONS"],
        )
        with KonnectClient(konnect_config) as client:
            result = client.update_route("cp-123", "route-001", route)

        # Verify
        assert result.paths == ["/api/v2/auth/login"]
        assert result.methods is not None
        assert "OPTIONS" in result.methods


class TestKonnectClientAuthIntegration:
    """Integration tests for authentication handling."""

    @pytest.mark.integration
    @respx.mock
    def test_invalid_token_returns_auth_error(
        self,
        konnect_config: KonnectConfig,
        base_url: str,
    ) -> None:
        """Test that invalid token returns proper auth error."""
        # Setup mock
        respx.get(f"{base_url}/v2/control-planes").mock(
            return_value=Response(
                401,
                json={"message": "Invalid token"},
            )
        )

        # Execute & Verify
        with KonnectClient(konnect_config) as client, pytest.raises(KonnectAuthError):
            client.list_control_planes()

    @pytest.mark.integration
    @respx.mock
    def test_authorization_header_is_sent(
        self,
        konnect_config: KonnectConfig,
        base_url: str,
    ) -> None:
        """Test that Authorization header is properly sent."""
        # Setup mock that captures request
        route = respx.get(f"{base_url}/v2/control-planes/cp-123/core-entities/services")
        route.mock(return_value=Response(200, json={"data": []}))

        # Execute
        with KonnectClient(konnect_config) as client:
            client.list_services("cp-123")

        # Verify authorization header was sent
        assert route.called
        request = route.calls[0].request
        assert "Authorization" in request.headers
        assert request.headers["Authorization"] == "Bearer test-token-12345"
