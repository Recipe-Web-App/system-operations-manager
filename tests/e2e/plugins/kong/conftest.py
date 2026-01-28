"""Kong E2E test fixtures using testcontainers.

This module provides fixtures that bridge the testcontainers infrastructure
from integration tests with CLI testing via CliRunner.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Callable, Generator
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
import typer
from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network
from testcontainers.core.wait_strategies import LogMessageWaitStrategy
from testcontainers.postgres import PostgresContainer
from typer.testing import CliRunner

if TYPE_CHECKING:
    from contextlib import AbstractContextManager
    from unittest.mock import MagicMock

    from system_operations_manager.services.kong.conflict_resolver import Resolution


# ============================================================================
# Configuration Constants
# ============================================================================

# Image selection: Use env var or default to OSS
KONG_IMAGE = os.environ.get("KONG_TEST_IMAGE", "kong:latest")
KONG_ENTERPRISE_IMAGE = "kong/kong-gateway:latest"


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
# Kong Container Class (duplicated from integration tests for isolation)
# ============================================================================


class KongContainer(DockerContainer):  # type: ignore[misc]
    """Custom Kong container for E2E testing.

    Runs Kong in DB-less mode without pre-loaded configuration.
    E2E tests create their own entities via CLI commands.
    """

    ADMIN_PORT = 8001
    PROXY_PORT = 8000

    def __init__(
        self,
        image: str = KONG_IMAGE,
    ) -> None:
        super().__init__(image)

        # DB-less mode configuration
        self.with_env("KONG_DATABASE", "off")
        self.with_env("KONG_PROXY_ACCESS_LOG", "/dev/stdout")
        self.with_env("KONG_ADMIN_ACCESS_LOG", "/dev/stdout")
        self.with_env("KONG_PROXY_ERROR_LOG", "/dev/stderr")
        self.with_env("KONG_ADMIN_ERROR_LOG", "/dev/stderr")
        self.with_env("KONG_ADMIN_LISTEN", "0.0.0.0:8001")

        # Enable declarative config updates via Admin API
        # This is needed for E2E tests that create entities via CLI
        self.with_env("KONG_DECLARATIVE_CONFIG_STRING", '{"_format_version": "3.0"}')

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
# Kong Container with Database Support (OSS)
# ============================================================================


class KongDbContainer(DockerContainer):  # type: ignore[misc]
    """Kong container with PostgreSQL database support.

    Runs Kong in database mode, enabling full CRUD operations on entities.
    Works with both OSS and Enterprise images.
    """

    ADMIN_PORT = 8001
    PROXY_PORT = 8000

    def __init__(
        self,
        pg_host: str,
        pg_port: int,
        pg_user: str = "kong",
        pg_password: str = "kong",
        pg_database: str = "kong",
        image: str = KONG_IMAGE,
    ) -> None:
        super().__init__(image)

        # Database mode configuration
        self.with_env("KONG_DATABASE", "postgres")
        self.with_env("KONG_PG_HOST", pg_host)
        self.with_env("KONG_PG_PORT", str(pg_port))
        self.with_env("KONG_PG_USER", pg_user)
        self.with_env("KONG_PG_PASSWORD", pg_password)
        self.with_env("KONG_PG_DATABASE", pg_database)

        # Admin API configuration
        self.with_env("KONG_ADMIN_LISTEN", "0.0.0.0:8001")
        self.with_env("KONG_PROXY_LISTEN", "0.0.0.0:8000")

        # Logging
        self.with_env("KONG_PROXY_ACCESS_LOG", "/dev/stdout")
        self.with_env("KONG_ADMIN_ACCESS_LOG", "/dev/stdout")
        self.with_env("KONG_PROXY_ERROR_LOG", "/dev/stderr")
        self.with_env("KONG_ADMIN_ERROR_LOG", "/dev/stderr")

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
# Kong Enterprise Container with Database Support
# ============================================================================


class KongEnterpriseDbContainer(DockerContainer):  # type: ignore[misc]
    """Kong Enterprise container with PostgreSQL database support.

    Runs Kong in database mode, which is required for enterprise features
    like workspaces, RBAC, vaults, and developer portal.
    """

    ADMIN_PORT = 8001
    PROXY_PORT = 8000

    def __init__(
        self,
        pg_host: str,
        pg_port: int,
        pg_user: str = "kong",
        pg_password: str = "kong",
        pg_database: str = "kong",
        image: str = KONG_ENTERPRISE_IMAGE,
    ) -> None:
        super().__init__(image)

        # Database mode configuration
        self.with_env("KONG_DATABASE", "postgres")
        self.with_env("KONG_PG_HOST", pg_host)
        self.with_env("KONG_PG_PORT", str(pg_port))
        self.with_env("KONG_PG_USER", pg_user)
        self.with_env("KONG_PG_PASSWORD", pg_password)
        self.with_env("KONG_PG_DATABASE", pg_database)

        # Admin API configuration
        self.with_env("KONG_ADMIN_LISTEN", "0.0.0.0:8001")
        self.with_env("KONG_PROXY_LISTEN", "0.0.0.0:8000")

        # Logging
        self.with_env("KONG_PROXY_ACCESS_LOG", "/dev/stdout")
        self.with_env("KONG_ADMIN_ACCESS_LOG", "/dev/stdout")
        self.with_env("KONG_PROXY_ERROR_LOG", "/dev/stderr")
        self.with_env("KONG_ADMIN_ERROR_LOG", "/dev/stderr")

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


@pytest.fixture(scope="session")
def docker_network() -> Generator[Network]:
    """Create a Docker network for container communication.

    Required for Kong to communicate with PostgreSQL.
    """
    network = Network()
    network.create()
    try:
        yield network
    finally:
        network.remove()


@pytest.fixture(scope="session")
def postgres_container(docker_network: Network) -> Generator[PostgresContainer]:
    """PostgreSQL container for Kong tests.

    Provides database backend for Kong to enable full CRUD operations.
    Configured with higher max_connections to support many concurrent tests.
    """
    container = PostgresContainer(
        image="postgres:15-alpine",
        username="kong",
        password="kong",
        dbname="kong",
    )
    container.with_network(docker_network)
    container.with_network_aliases("kong-postgres")
    # Increase max connections to handle many concurrent tests
    container.with_command("-c max_connections=200")

    with container:
        yield container


@pytest.fixture(scope="session")
def kong_container(
    postgres_container: PostgresContainer,
    docker_network: Network,
) -> Generator[KongDbContainer]:
    """Session-scoped Kong container with PostgreSQL for E2E tests.

    Runs Kong in database mode to enable full CRUD operations on entities.
    Using session scope to share the container across all E2E tests.
    """
    # Use network alias for PostgreSQL host (internal Docker network)
    container = KongDbContainer(
        pg_host="kong-postgres",  # Network alias
        pg_port=5432,  # Internal port
        pg_user="kong",
        pg_password="kong",
        pg_database="kong",
        image=KONG_IMAGE,
    )
    container.with_network(docker_network)

    # Run migrations before starting Kong
    container.with_command("sh -c 'kong migrations bootstrap && kong start'")

    # Configure wait strategy for Kong readiness (longer timeout for migrations)
    container.waiting_for(
        LogMessageWaitStrategy("start worker processes").with_startup_timeout(120)
    )

    with container:
        yield container


@pytest.fixture(scope="session")
def kong_dbless_container() -> Generator[KongContainer]:
    """Kong container in DB-less mode (for tests that don't need database).

    Faster startup but limited to declarative config operations.
    """
    container = KongContainer(image=KONG_IMAGE)
    container.waiting_for(LogMessageWaitStrategy("start worker processes").with_startup_timeout(60))

    with container:
        yield container


@pytest.fixture(scope="session")
def kong_admin_url(kong_container: KongDbContainer) -> str:
    """Get Kong Admin API URL."""
    return kong_container.get_admin_url()


@pytest.fixture(scope="session")
def kong_proxy_url(kong_container: KongDbContainer) -> str:
    """Get Kong Proxy URL."""
    return kong_container.get_proxy_url()


# ============================================================================
# Enterprise Database Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def enterprise_postgres_container(docker_network: Network) -> Generator[PostgresContainer]:
    """PostgreSQL container for Kong Enterprise tests.

    Separate from main postgres_container to allow independent lifecycle.
    Configured with higher max_connections to support many concurrent tests.
    """
    if not IS_ENTERPRISE:
        pytest.skip("Kong Enterprise required")

    container = PostgresContainer(
        image="postgres:15-alpine",
        username="kong",
        password="kong",
        dbname="kong_enterprise",
    )
    container.with_network(docker_network)
    container.with_network_aliases("kong-enterprise-postgres")
    # Increase max connections to handle many concurrent tests
    container.with_command("-c max_connections=200")

    with container:
        yield container


@pytest.fixture(scope="session")
def kong_enterprise_db_container(
    postgres_container: PostgresContainer,
    docker_network: Network,
) -> Generator[KongEnterpriseDbContainer]:
    """Kong Enterprise container with database for e2e tests.

    Runs Kong in database mode with PostgreSQL, enabling enterprise features
    like workspaces, RBAC, vaults, and developer portal.
    """
    if not IS_ENTERPRISE:
        pytest.skip("Kong Enterprise required")

    # Use network alias for PostgreSQL host (internal Docker network)
    container = KongEnterpriseDbContainer(
        pg_host="kong-postgres",  # Network alias
        pg_port=5432,  # Internal port
        pg_user="kong",
        pg_password="kong",
        pg_database="kong",
        image=KONG_IMAGE,  # Use the configured enterprise image
    )
    container.with_network(docker_network)

    # Run migrations before starting Kong
    container.with_command("sh -c 'kong migrations bootstrap && kong start'")

    # Wait for Kong to be ready (longer timeout for migrations)
    container.waiting_for(
        LogMessageWaitStrategy("start worker processes").with_startup_timeout(180)
    )

    with container:
        yield container


@pytest.fixture(scope="session")
def kong_enterprise_admin_url(kong_enterprise_db_container: KongEnterpriseDbContainer) -> str:
    """Get Kong Enterprise Admin API URL (database-backed)."""
    return kong_enterprise_db_container.get_admin_url()


@pytest.fixture(scope="session")
def has_enterprise_license(kong_enterprise_admin_url: str) -> bool:
    """Check if Kong Enterprise has a valid license for write operations.

    The free Kong Gateway image allows read operations on enterprise endpoints
    but requires a license for create/update/delete operations.

    Returns True if license is available, False otherwise.
    """
    import httpx

    try:
        # Try to create a test workspace
        response = httpx.post(
            f"{kong_enterprise_admin_url}/workspaces",
            json={"name": "license-test-workspace"},
            timeout=10,
        )

        if response.status_code == 201:
            # Success - delete the test workspace
            httpx.delete(
                f"{kong_enterprise_admin_url}/workspaces/license-test-workspace",
                timeout=10,
            )
            return True
        elif response.status_code == 403:
            # License required
            return False
        else:
            # Other error - assume no license
            return False
    except Exception:
        return False


@pytest.fixture(autouse=True)
def skip_if_no_license(request: pytest.FixtureRequest) -> None:
    """Skip tests marked with 'requires_license' if no enterprise license.

    This fixture auto-runs for all tests but only acts on tests with
    the @pytest.mark.requires_license marker.
    """
    if request.node.get_closest_marker("requires_license") and IS_ENTERPRISE:
        has_license = request.getfixturevalue("has_enterprise_license")
        if not has_license:
            pytest.skip("Kong Enterprise license required for write operations")


@pytest.fixture(scope="session")
def is_dbless_mode(kong_admin_url: str) -> bool:
    """Detect if Kong is running in DB-less mode.

    In DB-less mode, Kong doesn't support individual entity CRUD operations -
    only declarative config updates via /config endpoint work.
    """
    import httpx

    try:
        # Try to create a route directly - this fails in DB-less mode
        response = httpx.post(
            f"{kong_admin_url}/routes",
            json={"name": "dbless-test-route", "paths": ["/dbless-test"]},
            timeout=10,
        )
        if response.status_code == 201:
            # Success - delete the test route
            httpx.delete(
                f"{kong_admin_url}/routes/dbless-test-route",
                timeout=10,
            )
            return False
        elif response.status_code == 405:
            # Method not allowed - DB-less mode
            return True
        else:
            # Other error - assume DB-less
            return True
    except Exception:
        return True


@pytest.fixture(autouse=True)
def skip_if_dbless(request: pytest.FixtureRequest) -> None:
    """Skip tests marked with 'requires_db' if Kong is in DB-less mode.

    This fixture auto-runs for all tests but only acts on tests with
    the @pytest.mark.requires_db marker.
    """
    if request.node.get_closest_marker("requires_db"):
        is_dbless = request.getfixturevalue("is_dbless_mode")
        if is_dbless:
            pytest.skip("Kong database mode required for this test")


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI runner for invoking commands.

    Function-scoped to ensure clean state between tests.
    """
    return CliRunner()


@pytest.fixture(autouse=True)
def kong_env(kong_admin_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Configure environment for Kong plugin.

    Auto-used to ensure all tests have the correct Kong URL configured.
    """
    monkeypatch.setenv("OPS_KONG_BASE_URL", kong_admin_url)


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Path:
    """Temporary directory for config files.

    Useful for export/import tests.
    """
    return tmp_path


@pytest.fixture
def unique_prefix() -> str:
    """Generate a unique prefix for test entities.

    Helps avoid name conflicts when tests run in parallel or
    don't clean up properly.
    """
    return f"e2e-{uuid.uuid4().hex[:8]}"


# ============================================================================
# Test Application with Kong Plugin
# ============================================================================


def create_kong_app(kong_url: str) -> typer.Typer:
    """Create a Typer app with the Kong plugin commands for E2E testing.

    Args:
        kong_url: The Kong Admin API URL.

    Returns:
        A Typer app with Kong commands registered.

    Note:
        This manually registers only the commands needed for E2E testing,
        avoiding some commands with Python 3.14 type annotation issues.
    """
    from system_operations_manager.integrations.kong.client import KongAdminClient
    from system_operations_manager.integrations.kong.config import (
        KongAuthConfig,
        KongConnectionConfig,
    )
    from system_operations_manager.plugins.kong.commands.config import (
        register_config_commands,
    )
    from system_operations_manager.plugins.kong.commands.consumers import (
        register_consumer_commands,
    )
    from system_operations_manager.plugins.kong.commands.openapi import (
        register_openapi_commands,
    )
    from system_operations_manager.plugins.kong.commands.plugins import (
        register_plugin_commands,
    )
    from system_operations_manager.plugins.kong.commands.registry import (
        register_registry_commands,
    )
    from system_operations_manager.plugins.kong.commands.routes import (
        register_route_commands,
    )
    from system_operations_manager.plugins.kong.commands.security import (
        register_security_commands,
    )
    from system_operations_manager.plugins.kong.commands.services import (
        register_service_commands,
    )
    from system_operations_manager.plugins.kong.commands.traffic import (
        register_traffic_commands,
    )
    from system_operations_manager.plugins.kong.commands.upstreams import (
        register_upstream_commands,
    )
    from system_operations_manager.services.kong import (
        ConfigManager,
        ConsumerManager,
        KongPluginManager,
        OpenAPISyncManager,
        RouteManager,
        ServiceManager,
        UpstreamManager,
    )
    from system_operations_manager.services.kong.dual_write import DualWriteService
    from system_operations_manager.services.kong.registry_manager import RegistryManager

    # Create the Kong Admin client
    connection_config = KongConnectionConfig(
        base_url=kong_url,
        timeout=30,
        verify_ssl=False,
        retries=1,
    )
    auth_config = KongAuthConfig(type="none")
    client = KongAdminClient(connection_config, auth_config)

    # Create manager factory functions
    def get_service_manager() -> ServiceManager:
        return ServiceManager(client)

    def get_route_manager() -> RouteManager:
        return RouteManager(client)

    def get_consumer_manager() -> ConsumerManager:
        return ConsumerManager(client)

    def get_upstream_manager() -> UpstreamManager:
        return UpstreamManager(client)

    def get_plugin_manager() -> KongPluginManager:
        return KongPluginManager(client)

    def get_config_manager() -> ConfigManager:
        return ConfigManager(client)

    def get_openapi_sync_manager() -> OpenAPISyncManager:
        return OpenAPISyncManager(
            client,
            get_route_manager(),
            get_service_manager(),
        )

    def get_registry_manager() -> RegistryManager:
        # Dynamically compute config_dir based on current HOME env var
        # This allows tests to override HOME and get a fresh registry
        home = Path(os.environ.get("HOME", str(Path.home())))
        config_dir = home / ".config" / "ops" / "kong"
        return RegistryManager(config_dir=config_dir)

    # Create dual-write service factories (with Konnect=None since not available in CI)
    def get_dual_write_service_manager() -> DualWriteService[Any]:
        return DualWriteService(
            gateway_manager=get_service_manager(),
            konnect_manager=None,  # No Konnect in CI
            entity_name="service",
        )

    def get_dual_write_route_manager() -> DualWriteService[Any]:
        return DualWriteService(
            gateway_manager=get_route_manager(),
            konnect_manager=None,
            entity_name="route",
        )

    def get_dual_write_consumer_manager() -> DualWriteService[Any]:
        return DualWriteService(
            gateway_manager=get_consumer_manager(),
            konnect_manager=None,
            entity_name="consumer",
        )

    def get_dual_write_upstream_manager() -> DualWriteService[Any]:
        return DualWriteService(
            gateway_manager=get_upstream_manager(),
            konnect_manager=None,
            entity_name="upstream",
        )

    def get_dual_write_plugin_manager() -> DualWriteService[Any]:
        return DualWriteService(
            gateway_manager=get_plugin_manager(),
            konnect_manager=None,
            entity_name="plugin",
        )

    # Create the main app
    app = typer.Typer(
        name="ops",
        help="System Control CLI for E2E testing.",
        add_completion=False,
    )

    # Create Kong sub-app
    kong_app = typer.Typer(
        name="kong",
        help="Kong Gateway management commands",
        no_args_is_help=True,
    )

    # Register entity commands (avoiding observability due to Python 3.14 type annotation issues)
    # Pass dual-write factories for commands that support the --data-plane-only flag
    register_service_commands(
        kong_app,
        get_service_manager,
        get_dual_write_service=get_dual_write_service_manager,
    )
    register_route_commands(
        kong_app,
        get_route_manager,
        get_dual_write_service=get_dual_write_route_manager,
    )
    register_consumer_commands(
        kong_app,
        get_consumer_manager,
        get_dual_write_service=get_dual_write_consumer_manager,
    )
    register_upstream_commands(
        kong_app,
        get_upstream_manager,
        get_dual_write_service=get_dual_write_upstream_manager,
    )
    register_plugin_commands(
        kong_app,
        get_plugin_manager,
        get_dual_write_service=get_dual_write_plugin_manager,
    )
    register_security_commands(kong_app, get_plugin_manager, get_consumer_manager)
    register_traffic_commands(kong_app, get_plugin_manager)
    register_config_commands(kong_app, get_config_manager)
    register_openapi_commands(
        kong_app,
        get_openapi_sync_manager,
        get_service_manager,
        get_route_manager,
    )
    register_registry_commands(
        kong_app,
        get_registry_manager,
        get_service_manager,
        get_openapi_sync_manager,
    )

    # Add Kong sub-app to main app
    app.add_typer(kong_app, name="kong")

    return app


@pytest.fixture(scope="session")
def kong_app(kong_admin_url: str) -> typer.Typer:
    """Session-scoped Typer app with Kong plugin initialized.

    This app has the Kong plugin properly configured to talk to
    the test container.
    """
    return create_kong_app(kong_admin_url)


# ============================================================================
# Helper Fixtures for Common Test Patterns
# ============================================================================


@pytest.fixture
def invoke_kong(cli_runner: CliRunner, kong_app: typer.Typer) -> Callable[..., object]:
    """Helper to invoke Kong CLI commands.

    Returns a function that invokes commands on the kong_app.

    Example:
        result = invoke_kong("services", "list")
        result = invoke_kong("services", "create", "--name", "test")
    """

    def _invoke(*args: str, input: str | None = None) -> object:
        cmd = ["kong", *args]
        return cli_runner.invoke(kong_app, cmd, input=input)

    return _invoke


# ============================================================================
# Enterprise App Factory
# ============================================================================


def create_kong_enterprise_app(kong_url: str) -> typer.Typer:
    """Create a Typer app with Kong plugin commands including enterprise features.

    Args:
        kong_url: The Kong Admin API URL.

    Returns:
        A Typer app with Kong commands (including enterprise) registered.
    """
    from system_operations_manager.integrations.kong.client import KongAdminClient
    from system_operations_manager.integrations.kong.config import (
        KongAuthConfig,
        KongConnectionConfig,
    )
    from system_operations_manager.plugins.kong.commands.config import (
        register_config_commands,
    )
    from system_operations_manager.plugins.kong.commands.consumers import (
        register_consumer_commands,
    )
    from system_operations_manager.plugins.kong.commands.enterprise import (
        register_enterprise_commands,
    )
    from system_operations_manager.plugins.kong.commands.plugins import (
        register_plugin_commands,
    )
    from system_operations_manager.plugins.kong.commands.routes import (
        register_route_commands,
    )
    from system_operations_manager.plugins.kong.commands.security import (
        register_security_commands,
    )
    from system_operations_manager.plugins.kong.commands.services import (
        register_service_commands,
    )
    from system_operations_manager.plugins.kong.commands.traffic import (
        register_traffic_commands,
    )
    from system_operations_manager.plugins.kong.commands.upstreams import (
        register_upstream_commands,
    )
    from system_operations_manager.services.kong import (
        ConfigManager,
        ConsumerManager,
        KongPluginManager,
        PortalManager,
        RBACManager,
        RouteManager,
        ServiceManager,
        UpstreamManager,
        VaultManager,
        WorkspaceManager,
    )

    # Create the Kong Admin client
    connection_config = KongConnectionConfig(
        base_url=kong_url,
        timeout=30,
        verify_ssl=False,
        retries=1,
    )
    auth_config = KongAuthConfig(type="none")
    client = KongAdminClient(connection_config, auth_config)

    # Create manager factory functions
    def get_service_manager() -> ServiceManager:
        return ServiceManager(client)

    def get_route_manager() -> RouteManager:
        return RouteManager(client)

    def get_consumer_manager() -> ConsumerManager:
        return ConsumerManager(client)

    def get_upstream_manager() -> UpstreamManager:
        return UpstreamManager(client)

    def get_plugin_manager() -> KongPluginManager:
        return KongPluginManager(client)

    def get_config_manager() -> ConfigManager:
        return ConfigManager(client)

    # Enterprise managers
    def get_workspace_manager() -> WorkspaceManager:
        return WorkspaceManager(client)

    def get_rbac_manager() -> RBACManager:
        return RBACManager(client)

    def get_vault_manager() -> VaultManager:
        return VaultManager(client)

    def get_portal_manager() -> PortalManager:
        return PortalManager(client)

    # Create the main app
    app = typer.Typer(
        name="ops",
        help="System Control CLI for E2E testing (with Enterprise).",
        add_completion=False,
    )

    # Create Kong sub-app
    kong_app = typer.Typer(
        name="kong",
        help="Kong Gateway management commands",
        no_args_is_help=True,
    )

    # Register entity commands
    register_service_commands(kong_app, get_service_manager)
    register_route_commands(kong_app, get_route_manager)
    register_consumer_commands(kong_app, get_consumer_manager)
    register_upstream_commands(kong_app, get_upstream_manager)
    register_plugin_commands(kong_app, get_plugin_manager)
    register_security_commands(kong_app, get_plugin_manager, get_consumer_manager)
    register_traffic_commands(kong_app, get_plugin_manager)
    register_config_commands(kong_app, get_config_manager)

    # Register enterprise commands
    register_enterprise_commands(
        kong_app,
        get_workspace_manager,
        get_rbac_manager,
        get_vault_manager,
        get_portal_manager,
    )

    # Add Kong sub-app to main app
    app.add_typer(kong_app, name="kong")

    return app


@pytest.fixture(scope="session")
def kong_enterprise_app(kong_enterprise_admin_url: str) -> typer.Typer:
    """Session-scoped Typer app with Kong plugin including enterprise features.

    This app has the Kong plugin properly configured to talk to
    the database-backed test container, with enterprise commands registered.

    Note: This uses kong_enterprise_admin_url (database mode) instead of
    kong_admin_url (DB-less mode) because enterprise features require a database.
    """
    return create_kong_enterprise_app(kong_enterprise_admin_url)


@pytest.fixture
def invoke_kong_enterprise(
    cli_runner: CliRunner, kong_enterprise_app: typer.Typer
) -> Callable[..., object]:
    """Helper to invoke Kong CLI commands including enterprise features.

    Returns a function that invokes commands on the kong_enterprise_app.

    Example:
        result = invoke_kong_enterprise("enterprise", "workspaces", "list")
        result = invoke_kong_enterprise("enterprise", "rbac", "roles", "list")
    """

    def _invoke(*args: str, input: str | None = None) -> object:
        cmd = ["kong", *args]
        return cli_runner.invoke(kong_enterprise_app, cmd, input=input)

    return _invoke


# ============================================================================
# Vault Container for E2E Tests
# ============================================================================


class VaultContainer(DockerContainer):  # type: ignore[misc]
    """HashiCorp Vault container for E2E testing.

    Runs Vault in dev mode for testing Kong vault integrations.
    """

    VAULT_PORT = 8200
    DEV_ROOT_TOKEN = "e2e-test-token"

    def __init__(
        self,
        image: str = "hashicorp/vault:latest",
    ) -> None:
        super().__init__(image)

        # Dev mode configuration
        self.with_env("VAULT_DEV_ROOT_TOKEN_ID", self.DEV_ROOT_TOKEN)
        self.with_env("VAULT_DEV_LISTEN_ADDRESS", "0.0.0.0:8200")

        # Expose port
        self.with_exposed_ports(self.VAULT_PORT)

    def get_vault_url(self) -> str:
        """Get the Vault API URL with mapped port."""
        host = self.get_container_host_ip()
        port = self.get_exposed_port(self.VAULT_PORT)
        return f"http://{host}:{port}"

    def get_root_token(self) -> str:
        """Get the root token for authentication."""
        return self.DEV_ROOT_TOKEN


@pytest.fixture(scope="session")
def vault_container() -> Generator[VaultContainer]:
    """Session-scoped HashiCorp Vault container for E2E tests.

    Used for testing Kong vault integrations with a real vault backend.
    """
    container = VaultContainer()

    # Wait for Vault to be ready
    container.waiting_for(LogMessageWaitStrategy("Development mode").with_startup_timeout(30))

    with container:
        yield container


@pytest.fixture(scope="session")
def vault_url(vault_container: VaultContainer) -> str:
    """Get Vault API URL."""
    return vault_container.get_vault_url()


@pytest.fixture(scope="session")
def vault_token(vault_container: VaultContainer) -> str:
    """Get Vault root token."""
    return vault_container.get_root_token()


# ============================================================================
# Konnect Configuration Detection
# ============================================================================


@pytest.fixture(scope="session")
def is_konnect_configured() -> bool:
    """Detect if Konnect is configured in the environment.

    Checks for KONNECT_API_KEY or ops.yaml configuration.
    Returns True if Konnect appears to be configured, False otherwise.
    """
    import os

    # Check environment variable
    if os.environ.get("KONNECT_API_KEY"):
        return True

    # Check for ops.yaml with konnect config
    config_locations = [
        Path.cwd() / "ops.yaml",
        Path.home() / ".config" / "ops" / "ops.yaml",
    ]

    for config_path in config_locations:
        if config_path.exists():
            try:
                import yaml

                with config_path.open() as f:
                    config = yaml.safe_load(f)
                    if config and config.get("konnect", {}).get("api_key"):
                        return True
            except Exception:
                continue

    return False


@pytest.fixture(autouse=True)
def skip_if_no_konnect(request: pytest.FixtureRequest) -> None:
    """Skip tests marked with 'requires_konnect' if Konnect is not configured.

    This fixture auto-runs for all tests but only acts on tests with
    the @pytest.mark.requires_konnect marker.
    """
    if request.node.get_closest_marker("requires_konnect"):
        is_configured = request.getfixturevalue("is_konnect_configured")
        if not is_configured:
            pytest.skip("Konnect not configured - set KONNECT_API_KEY or configure ops.yaml")


# ============================================================================
# Sync Interactive Mode Fixtures
# ============================================================================


@pytest.fixture
def mock_tui_resolutions() -> Callable[[list[Resolution]], AbstractContextManager[MagicMock]]:
    """Factory to mock _launch_conflict_resolution_tui with specific resolutions.

    Usage:
        def test_example(mock_tui_resolutions):
            resolutions = [Resolution(...)]
            with mock_tui_resolutions(resolutions) as mock_tui:
                result = cli_runner.invoke(app, ["kong", "sync", "push", "--interactive"])
                mock_tui.assert_called_once()
    """
    from contextlib import contextmanager
    from unittest.mock import patch

    @contextmanager
    def _mock(resolutions: list[Resolution]) -> Generator[MagicMock]:
        with patch(
            "system_operations_manager.plugins.kong.commands.sync._launch_conflict_resolution_tui"
        ) as mock:
            mock.return_value = resolutions
            yield mock

    return _mock
