"""Unit tests for KonnectRouteManager."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kong.models.route import Route
from system_operations_manager.integrations.konnect.exceptions import KonnectNotFoundError
from system_operations_manager.services.konnect.route_manager import KonnectRouteManager


@pytest.fixture
def mock_konnect_client() -> MagicMock:
    """Create a mock Konnect client."""
    return MagicMock()


@pytest.fixture
def route_manager(mock_konnect_client: MagicMock) -> KonnectRouteManager:
    """Create a KonnectRouteManager with mock client."""
    return KonnectRouteManager(mock_konnect_client, "cp-123")


class TestKonnectRouteManagerInit:
    """Tests for KonnectRouteManager initialization."""

    @pytest.mark.unit
    def test_initialization(self, mock_konnect_client: MagicMock) -> None:
        """Manager should initialize with client and control plane ID."""
        manager = KonnectRouteManager(mock_konnect_client, "cp-123")
        assert manager.control_plane_id == "cp-123"


class TestKonnectRouteManagerList:
    """Tests for list operations."""

    @pytest.mark.unit
    def test_list_routes(
        self,
        route_manager: KonnectRouteManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """list should return routes from client."""
        expected_routes = [
            Route(name="route-1", paths=["/api"]),
            Route(name="route-2", paths=["/health"]),
        ]
        mock_konnect_client.list_routes.return_value = (expected_routes, None)

        routes, _next_offset = route_manager.list()

        assert len(routes) == 2
        assert routes[0].name == "route-1"
        mock_konnect_client.list_routes.assert_called_once_with(
            "cp-123", tags=None, limit=None, offset=None
        )

    @pytest.mark.unit
    def test_list_by_service(
        self,
        route_manager: KonnectRouteManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """list_by_service should filter by service."""
        expected_routes = [Route(name="svc-route", paths=["/api"])]
        mock_konnect_client.list_routes.return_value = (expected_routes, None)

        routes, _ = route_manager.list_by_service("test-service")

        assert len(routes) == 1
        mock_konnect_client.list_routes.assert_called_once_with(
            "cp-123",
            service_name_or_id="test-service",
            tags=None,
            limit=None,
            offset=None,
        )


class TestKonnectRouteManagerGet:
    """Tests for get operations."""

    @pytest.mark.unit
    def test_get_route(
        self,
        route_manager: KonnectRouteManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """get should return route from client."""
        expected = Route(name="test-route", paths=["/api"])
        mock_konnect_client.get_route.return_value = expected

        result = route_manager.get("test-route")

        assert result.name == "test-route"
        mock_konnect_client.get_route.assert_called_once_with("cp-123", "test-route")

    @pytest.mark.unit
    def test_get_route_not_found(
        self,
        route_manager: KonnectRouteManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """get should raise NotFoundError when route doesn't exist."""
        mock_konnect_client.get_route.side_effect = KonnectNotFoundError(
            "Route not found", status_code=404
        )

        with pytest.raises(KonnectNotFoundError):
            route_manager.get("nonexistent")


class TestKonnectRouteManagerExists:
    """Tests for exists operations."""

    @pytest.mark.unit
    def test_exists_returns_true(
        self,
        route_manager: KonnectRouteManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """exists should return True when route exists."""
        mock_konnect_client.get_route.return_value = Route(name="test", paths=["/api"])

        assert route_manager.exists("test") is True

    @pytest.mark.unit
    def test_exists_returns_false(
        self,
        route_manager: KonnectRouteManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """exists should return False when route doesn't exist."""
        mock_konnect_client.get_route.side_effect = KonnectNotFoundError(
            "Route not found", status_code=404
        )

        assert route_manager.exists("nonexistent") is False


class TestKonnectRouteManagerCreate:
    """Tests for create operations."""

    @pytest.mark.unit
    def test_create_route(
        self,
        route_manager: KonnectRouteManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """create should create route via client."""
        route = Route(name="new-route", paths=["/new"])
        created = Route(id="route-new", name="new-route", paths=["/new"])
        mock_konnect_client.create_route.return_value = created

        result = route_manager.create(route)

        assert result.id == "route-new"
        mock_konnect_client.create_route.assert_called_once_with(
            "cp-123", route, service_name_or_id=None
        )

    @pytest.mark.unit
    def test_create_route_for_service(
        self,
        route_manager: KonnectRouteManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """create should pass service_name_or_id to client."""
        route = Route(name="new-route", paths=["/new"])
        created = Route(id="route-new", name="new-route", paths=["/new"])
        mock_konnect_client.create_route.return_value = created

        route_manager.create(route, service_name_or_id="test-service")

        mock_konnect_client.create_route.assert_called_once_with(
            "cp-123", route, service_name_or_id="test-service"
        )


class TestKonnectRouteManagerUpdate:
    """Tests for update operations."""

    @pytest.mark.unit
    def test_update_route(
        self,
        route_manager: KonnectRouteManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """update should update route via client."""
        route = Route(name="test-route", paths=["/updated"])
        updated = Route(id="route-1", name="test-route", paths=["/updated"])
        mock_konnect_client.update_route.return_value = updated

        result = route_manager.update("route-1", route)

        assert result.paths == ["/updated"]
        mock_konnect_client.update_route.assert_called_once_with("cp-123", "route-1", route)


class TestKonnectRouteManagerDelete:
    """Tests for delete operations."""

    @pytest.mark.unit
    def test_delete_route(
        self,
        route_manager: KonnectRouteManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """delete should delete route via client."""
        route_manager.delete("route-1")

        mock_konnect_client.delete_route.assert_called_once_with("cp-123", "route-1")
