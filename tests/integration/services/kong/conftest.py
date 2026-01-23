"""Kong services integration test fixtures.

Re-uses the Kong container and client fixtures from the plugins integration tests.
"""

from __future__ import annotations

# Import all fixtures from the plugins/kong conftest
from tests.integration.plugins.kong.conftest import (
    KongContainer,
    auth_config,
    connection_config,
    consumer_manager,
    is_enterprise,
    kong_admin_url,
    kong_client,
    kong_container,
    kong_proxy_url,
    openapi_sync_manager,
    plugin_manager,
    route_manager,
    service_manager,
    upstream_manager,
)

__all__ = [
    "KongContainer",
    "auth_config",
    "connection_config",
    "consumer_manager",
    "is_enterprise",
    "kong_admin_url",
    "kong_client",
    "kong_container",
    "kong_proxy_url",
    "openapi_sync_manager",
    "plugin_manager",
    "route_manager",
    "service_manager",
    "upstream_manager",
]
