"""Integration tests for ServiceManager."""

from __future__ import annotations

import pytest

from system_operations_manager.integrations.kong.exceptions import KongNotFoundError
from system_operations_manager.services.kong.service_manager import ServiceManager


@pytest.mark.integration
@pytest.mark.kong
class TestServiceManagerList:
    """Test service listing operations."""

    def test_list_all_services(
        self,
        service_manager: ServiceManager,
    ) -> None:
        """list should return services from declarative config."""
        services, _offset = service_manager.list()

        assert len(services) >= 1  # At least test-service
        assert any(s.name == "test-service" for s in services)

    def test_list_with_tags_filter(
        self,
        service_manager: ServiceManager,
    ) -> None:
        """list should filter by tags."""
        services, _ = service_manager.list(tags=["test"])

        # All returned services should have the tag
        for service in services:
            assert "test" in (service.tags or [])

    def test_list_with_pagination(
        self,
        service_manager: ServiceManager,
    ) -> None:
        """list should support pagination."""
        services, _ = service_manager.list(limit=1)

        assert len(services) <= 1

    def test_list_returns_expected_services(
        self,
        service_manager: ServiceManager,
    ) -> None:
        """list should return both configured services."""
        services, _ = service_manager.list()

        service_names = [s.name for s in services]
        assert "test-service" in service_names
        assert "mock-api" in service_names


@pytest.mark.integration
@pytest.mark.kong
class TestServiceManagerGet:
    """Test service retrieval operations."""

    def test_get_service_by_name(
        self,
        service_manager: ServiceManager,
    ) -> None:
        """get should retrieve service by name."""
        service = service_manager.get("test-service")

        assert service.name == "test-service"
        assert service.host == "httpbin.org"

    def test_get_mock_api_service(
        self,
        service_manager: ServiceManager,
    ) -> None:
        """get should retrieve mock-api service."""
        service = service_manager.get("mock-api")

        assert service.name == "mock-api"
        assert service.host == "mockbin.org"
        assert service.port == 80
        assert service.protocol == "http"

    def test_get_nonexistent_service_raises(
        self,
        service_manager: ServiceManager,
    ) -> None:
        """get should raise KongNotFoundError for missing service."""
        with pytest.raises(KongNotFoundError):
            service_manager.get("nonexistent-service")

    def test_exists_returns_true_for_existing(
        self,
        service_manager: ServiceManager,
    ) -> None:
        """exists should return True for existing service."""
        assert service_manager.exists("test-service") is True

    def test_exists_returns_false_for_missing(
        self,
        service_manager: ServiceManager,
    ) -> None:
        """exists should return False for missing service."""
        assert service_manager.exists("nonexistent") is False


@pytest.mark.integration
@pytest.mark.kong
class TestServiceManagerRelated:
    """Test service-related operations."""

    def test_get_routes_for_service(
        self,
        service_manager: ServiceManager,
    ) -> None:
        """get_routes should return associated routes."""
        routes = service_manager.get_routes("test-service")

        assert len(routes) >= 1
        assert any(r.name == "test-route" for r in routes)

    def test_get_routes_for_mock_api(
        self,
        service_manager: ServiceManager,
    ) -> None:
        """get_routes should return mock-api routes."""
        routes = service_manager.get_routes("mock-api")

        assert len(routes) >= 1
        assert any(r.name == "mock-route" for r in routes)

    def test_get_plugins_for_service(
        self,
        service_manager: ServiceManager,
    ) -> None:
        """get_plugins should return associated plugins."""
        plugins = service_manager.get_plugins("test-service")

        # May be empty if no plugins configured on service
        assert isinstance(plugins, list)

    def test_count_services(
        self,
        service_manager: ServiceManager,
    ) -> None:
        """count should return total number of services."""
        count = service_manager.count()

        assert count >= 2  # test-service and mock-api
