"""Integration tests for KongAdminClient."""

from __future__ import annotations

import pytest

from system_operations_manager.integrations.kong.client import KongAdminClient
from system_operations_manager.integrations.kong.exceptions import KongNotFoundError


@pytest.mark.integration
@pytest.mark.kong
class TestKongClientConnection:
    """Test Kong client connection operations."""

    def test_check_connection_succeeds(
        self,
        kong_client: KongAdminClient,
    ) -> None:
        """check_connection should return True for live Kong."""
        assert kong_client.check_connection() is True

    def test_get_status_returns_valid_response(
        self,
        kong_client: KongAdminClient,
    ) -> None:
        """get_status should return status information."""
        status = kong_client.get_status()

        assert "server" in status
        # In DB-less mode, 'memory' is returned instead of 'database'
        assert "memory" in status or "database" in status

    def test_get_info_returns_version(
        self,
        kong_client: KongAdminClient,
    ) -> None:
        """get_info should return Kong version info."""
        info = kong_client.get_info()

        assert "version" in info
        assert "hostname" in info
        assert "plugins" in info


@pytest.mark.integration
@pytest.mark.kong
class TestKongClientHttpMethods:
    """Test HTTP method operations against live Kong."""

    def test_get_services_list(
        self,
        kong_client: KongAdminClient,
    ) -> None:
        """GET request should return services list."""
        response = kong_client.get("services")

        assert "data" in response
        assert isinstance(response["data"], list)

    def test_get_nonexistent_resource_raises_not_found(
        self,
        kong_client: KongAdminClient,
    ) -> None:
        """GET for nonexistent resource should raise KongNotFoundError."""
        with pytest.raises(KongNotFoundError):
            kong_client.get("services/nonexistent-service-12345")

    def test_get_routes_list(
        self,
        kong_client: KongAdminClient,
    ) -> None:
        """GET request should return routes list."""
        response = kong_client.get("routes")

        assert "data" in response
        assert isinstance(response["data"], list)

    def test_get_consumers_list(
        self,
        kong_client: KongAdminClient,
    ) -> None:
        """GET request should return consumers list."""
        response = kong_client.get("consumers")

        assert "data" in response
        assert isinstance(response["data"], list)

    def test_get_upstreams_list(
        self,
        kong_client: KongAdminClient,
    ) -> None:
        """GET request should return upstreams list."""
        response = kong_client.get("upstreams")

        assert "data" in response
        assert isinstance(response["data"], list)

    def test_get_plugins_list(
        self,
        kong_client: KongAdminClient,
    ) -> None:
        """GET request should return plugins list."""
        response = kong_client.get("plugins")

        assert "data" in response
        assert isinstance(response["data"], list)


@pytest.mark.integration
@pytest.mark.kong
class TestKongClientDBLessMode:
    """Test DB-less mode behavior."""

    def test_dbless_mode_status(
        self,
        kong_client: KongAdminClient,
    ) -> None:
        """Kong should report DB-less mode in status."""
        info = kong_client.get_info()

        # DB-less mode has database = "off"
        assert info.get("configuration", {}).get("database") == "off"

    def test_status_endpoint_returns_ok(
        self,
        kong_client: KongAdminClient,
    ) -> None:
        """Status endpoint should return healthy status."""
        status = kong_client.get_status()

        # Server section should exist
        assert "server" in status
        server = status["server"]
        assert "connections_accepted" in server or "total_requests" in server
