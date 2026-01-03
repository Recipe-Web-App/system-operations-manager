"""Kong Gateway service layer - business logic for Kong operations.

This package contains entity managers that implement business logic
for Kong Admin API operations. Managers use the Repository pattern
to abstract data access from command implementations.
"""

from system_operations_manager.services.kong.base import BaseEntityManager
from system_operations_manager.services.kong.consumer_manager import ConsumerManager
from system_operations_manager.services.kong.plugin_manager import KongPluginManager
from system_operations_manager.services.kong.route_manager import RouteManager
from system_operations_manager.services.kong.service_manager import ServiceManager
from system_operations_manager.services.kong.upstream_manager import UpstreamManager

__all__ = [
    "BaseEntityManager",
    "ConsumerManager",
    "KongPluginManager",
    "RouteManager",
    "ServiceManager",
    "UpstreamManager",
]
