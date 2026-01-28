"""Enterprise-specific test fixtures."""

from __future__ import annotations

import pytest

from system_operations_manager.integrations.kong.client import KongAdminClient
from system_operations_manager.services.kong.portal_manager import PortalManager
from system_operations_manager.services.kong.rbac_manager import RBACManager
from system_operations_manager.services.kong.vault_manager import VaultManager
from system_operations_manager.services.kong.workspace_manager import WorkspaceManager

# Import skip marker from parent
from tests.integration.plugins.kong.conftest import IS_ENTERPRISE, skip_enterprise

# Skip entire module if not enterprise
pytestmark = [
    pytest.mark.kong_enterprise,
    skip_enterprise,
]


@pytest.fixture
def workspace_manager(kong_client: KongAdminClient) -> WorkspaceManager:
    """Create WorkspaceManager instance."""
    return WorkspaceManager(kong_client)


@pytest.fixture
def rbac_manager(kong_client: KongAdminClient) -> RBACManager:
    """Create RBACManager instance."""
    return RBACManager(kong_client)


@pytest.fixture
def vault_manager(kong_client: KongAdminClient) -> VaultManager:
    """Create VaultManager instance."""
    return VaultManager(kong_client)


@pytest.fixture
def portal_manager(kong_client: KongAdminClient) -> PortalManager:
    """Create PortalManager instance."""
    return PortalManager(kong_client)


# Re-export for convenience
__all__ = [
    "IS_ENTERPRISE",
    "portal_manager",
    "rbac_manager",
    "skip_enterprise",
    "vault_manager",
    "workspace_manager",
]
