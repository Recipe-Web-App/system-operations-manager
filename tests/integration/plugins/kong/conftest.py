"""Kong integration test fixtures using testcontainers."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

from system_operations_manager.integrations.kong.client import KongAdminClient
from system_operations_manager.integrations.kong.config import (
    KongAuthConfig,
    KongConnectionConfig,
)
from system_operations_manager.services.kong.consumer_manager import ConsumerManager
from system_operations_manager.services.kong.plugin_manager import KongPluginManager
from system_operations_manager.services.kong.route_manager import RouteManager
from system_operations_manager.services.kong.service_manager import ServiceManager
from system_operations_manager.services.kong.upstream_manager import UpstreamManager

if TYPE_CHECKING:
    pass


# ============================================================================
# Configuration Constants
# ============================================================================

# Image selection: Use env var or default to OSS
KONG_IMAGE = os.environ.get("KONG_TEST_IMAGE", "kong:latest")
KONG_ENTERPRISE_IMAGE = "kong/kong-gateway:latest"

# Test data directory
TEST_DATA_DIR = Path(__file__).parent


def is_enterprise_image(image: str) -> bool:
    """Check if the image is Kong Enterprise."""
    return "kong-gateway" in image or "enterprise" in image.lower()


IS_ENTERPRISE = is_enterprise_image(KONG_IMAGE)

# Skip marker for enterprise-only tests
skip_enterprise = pytest.mark.skipif(
    not IS_ENTERPRISE,
    reason="Kong Enterprise required",
)


# ============================================================================
# Kong Container Class
# ============================================================================


class KongContainer(DockerContainer):
    """Custom Kong container for testing.

    Runs Kong in DB-less mode with declarative configuration.
    """

    ADMIN_PORT = 8001
    PROXY_PORT = 8000

    def __init__(
        self,
        image: str = KONG_IMAGE,
        kong_config_path: Path | None = None,
    ) -> None:
        super().__init__(image)

        self.kong_config_path = kong_config_path or TEST_DATA_DIR / "kong.yml"

        # DB-less mode configuration
        self.with_env("KONG_DATABASE", "off")
        self.with_env("KONG_PROXY_ACCESS_LOG", "/dev/stdout")
        self.with_env("KONG_ADMIN_ACCESS_LOG", "/dev/stdout")
        self.with_env("KONG_PROXY_ERROR_LOG", "/dev/stderr")
        self.with_env("KONG_ADMIN_ERROR_LOG", "/dev/stderr")
        self.with_env("KONG_ADMIN_LISTEN", "0.0.0.0:8001")

        # Mount declarative config if exists
        if self.kong_config_path.exists():
            self.with_env("KONG_DECLARATIVE_CONFIG", "/kong/kong.yml")
            self.with_volume_mapping(
                str(self.kong_config_path),
                "/kong/kong.yml",
                mode="ro",
            )

        # Expose ports
        self.with_exposed_ports(self.ADMIN_PORT, self.PROXY_PORT)

    def get_admin_url(self) -> str:
        """Get the Admin API URL with mapped port."""
        host = self.get_container_host_ip()
        port = self.get_exposed_port(self.ADMIN_PORT)
        return f"http://{host}:{port}"

    def get_proxy_url(self) -> str:
        """Get the Proxy URL with mapped port."""
        host = self.get_container_host_ip()
        port = self.get_exposed_port(self.PROXY_PORT)
        return f"http://{host}:{port}"


# ============================================================================
# Pytest Fixtures
# ============================================================================


@pytest.fixture(scope="module")
def kong_container() -> Generator[KongContainer]:
    """Start Kong container for integration tests.

    Module-scoped to avoid slow startup for each test.
    Uses DB-less mode with declarative configuration.
    """
    container = KongContainer(image=KONG_IMAGE)

    # Configure wait strategy for Kong readiness
    container.waiting_for(LogMessageWaitStrategy("start worker processes").with_startup_timeout(60))

    with container:
        yield container


@pytest.fixture(scope="module")
def kong_admin_url(kong_container: KongContainer) -> str:
    """Get Kong Admin API URL."""
    return kong_container.get_admin_url()


@pytest.fixture(scope="module")
def kong_proxy_url(kong_container: KongContainer) -> str:
    """Get Kong Proxy URL."""
    return kong_container.get_proxy_url()


@pytest.fixture(scope="module")
def connection_config(kong_admin_url: str) -> KongConnectionConfig:
    """Create connection config for the test Kong instance."""
    return KongConnectionConfig(
        base_url=kong_admin_url,
        timeout=30,
        verify_ssl=False,
        retries=1,
    )


@pytest.fixture(scope="module")
def auth_config() -> KongAuthConfig:
    """Create auth config (no auth for test container)."""
    return KongAuthConfig(type="none")


@pytest.fixture(scope="module")
def kong_client(
    connection_config: KongConnectionConfig,
    auth_config: KongAuthConfig,
) -> Generator[KongAdminClient]:
    """Create Kong Admin API client for tests.

    Module-scoped to reuse connection across tests.
    """
    with KongAdminClient(connection_config, auth_config) as client:
        yield client


# ============================================================================
# Service Manager Fixtures
# ============================================================================


@pytest.fixture
def service_manager(kong_client: KongAdminClient) -> ServiceManager:
    """Create ServiceManager instance."""
    return ServiceManager(kong_client)


@pytest.fixture
def route_manager(kong_client: KongAdminClient) -> RouteManager:
    """Create RouteManager instance."""
    return RouteManager(kong_client)


@pytest.fixture
def consumer_manager(kong_client: KongAdminClient) -> ConsumerManager:
    """Create ConsumerManager instance."""
    return ConsumerManager(kong_client)


@pytest.fixture
def upstream_manager(kong_client: KongAdminClient) -> UpstreamManager:
    """Create UpstreamManager instance."""
    return UpstreamManager(kong_client)


@pytest.fixture
def plugin_manager(kong_client: KongAdminClient) -> KongPluginManager:
    """Create KongPluginManager instance."""
    return KongPluginManager(kong_client)


# ============================================================================
# Enterprise Detection
# ============================================================================


@pytest.fixture(scope="module")
def is_enterprise(kong_client: KongAdminClient) -> bool:
    """Detect if Kong instance is Enterprise edition.

    Checks for presence of workspaces endpoint.
    """
    try:
        kong_client.get("workspaces")
        return True
    except Exception:
        return False
