"""Integration tests for RouteManager."""

from __future__ import annotations

import pytest

from system_operations_manager.integrations.kong.exceptions import KongNotFoundError
from system_operations_manager.services.kong.route_manager import RouteManager


@pytest.mark.integration
@pytest.mark.kong
class TestRouteManagerList:
    """Test route listing operations."""

    def test_list_all_routes(
        self,
        route_manager: RouteManager,
    ) -> None:
        """list should return routes from declarative config."""
        routes, _offset = route_manager.list()

        assert len(routes) >= 1  # At least test-route
        assert any(r.name == "test-route" for r in routes)

    def test_list_with_pagination(
        self,
        route_manager: RouteManager,
    ) -> None:
        """list should support pagination."""
        routes, _ = route_manager.list(limit=1)

        assert len(routes) <= 1

    def test_list_returns_expected_routes(
        self,
        route_manager: RouteManager,
    ) -> None:
        """list should return both configured routes."""
        routes, _ = route_manager.list()

        route_names = [r.name for r in routes]
        assert "test-route" in route_names
        assert "mock-route" in route_names


@pytest.mark.integration
@pytest.mark.kong
class TestRouteManagerGet:
    """Test route retrieval operations."""

    def test_get_route_by_name(
        self,
        route_manager: RouteManager,
    ) -> None:
        """get should retrieve route by name."""
        route = route_manager.get("test-route")

        assert route.name == "test-route"
        assert "/test" in (route.paths or [])
        assert route.strip_path is True

    def test_get_mock_route(
        self,
        route_manager: RouteManager,
    ) -> None:
        """get should retrieve mock-route."""
        route = route_manager.get("mock-route")

        assert route.name == "mock-route"
        assert "/mock" in (route.paths or [])
        assert "GET" in (route.methods or [])
        assert "POST" in (route.methods or [])

    def test_get_nonexistent_route_raises(
        self,
        route_manager: RouteManager,
    ) -> None:
        """get should raise KongNotFoundError for missing route."""
        with pytest.raises(KongNotFoundError):
            route_manager.get("nonexistent-route")

    def test_exists_returns_true_for_existing(
        self,
        route_manager: RouteManager,
    ) -> None:
        """exists should return True for existing route."""
        assert route_manager.exists("test-route") is True

    def test_exists_returns_false_for_missing(
        self,
        route_manager: RouteManager,
    ) -> None:
        """exists should return False for missing route."""
        assert route_manager.exists("nonexistent") is False


@pytest.mark.integration
@pytest.mark.kong
class TestRouteManagerByService:
    """Test service-scoped route operations."""

    def test_list_by_service(
        self,
        route_manager: RouteManager,
    ) -> None:
        """list_by_service should return routes for specific service."""
        routes, _ = route_manager.list_by_service("test-service")

        assert len(routes) >= 1
        assert any(r.name == "test-route" for r in routes)

    def test_list_by_service_mock_api(
        self,
        route_manager: RouteManager,
    ) -> None:
        """list_by_service should return routes for mock-api."""
        routes, _ = route_manager.list_by_service("mock-api")

        assert len(routes) >= 1
        assert any(r.name == "mock-route" for r in routes)

    def test_list_by_nonexistent_service(
        self,
        route_manager: RouteManager,
    ) -> None:
        """list_by_service for nonexistent service should raise error."""
        with pytest.raises(KongNotFoundError):
            route_manager.list_by_service("nonexistent-service")


@pytest.mark.integration
@pytest.mark.kong
class TestRouteManagerPlugins:
    """Test route plugin operations."""

    def test_get_plugins_for_route(
        self,
        route_manager: RouteManager,
    ) -> None:
        """get_plugins should return plugins for route."""
        plugins = route_manager.get_plugins("test-route")

        # May be empty if no plugins configured on route
        assert isinstance(plugins, list)

    def test_count_routes(
        self,
        route_manager: RouteManager,
    ) -> None:
        """count should return total number of routes."""
        count = route_manager.count()

        assert count >= 2  # test-route and mock-route
