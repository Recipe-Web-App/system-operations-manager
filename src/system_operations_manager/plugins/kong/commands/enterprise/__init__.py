"""Kong Enterprise commands.

Provides CLI commands for Kong Enterprise features:
- Workspaces (multi-tenancy)
- RBAC (Role-Based Access Control)
- Vaults (secret management)
- Developer Portal
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import typer

from system_operations_manager.plugins.kong.commands.enterprise.portal import (
    register_portal_commands,
)
from system_operations_manager.plugins.kong.commands.enterprise.rbac import (
    register_rbac_commands,
)
from system_operations_manager.plugins.kong.commands.enterprise.vaults import (
    register_vault_commands,
)
from system_operations_manager.plugins.kong.commands.enterprise.workspaces import (
    register_workspace_commands,
)

if TYPE_CHECKING:
    from system_operations_manager.services.kong.portal_manager import PortalManager
    from system_operations_manager.services.kong.rbac_manager import RBACManager
    from system_operations_manager.services.kong.vault_manager import VaultManager
    from system_operations_manager.services.kong.workspace_manager import WorkspaceManager


__all__ = [
    "register_enterprise_commands",
    "register_portal_commands",
    "register_rbac_commands",
    "register_vault_commands",
    "register_workspace_commands",
]


def register_enterprise_commands(
    app: typer.Typer,
    get_workspace_manager: Callable[[], WorkspaceManager],
    get_rbac_manager: Callable[[], RBACManager],
    get_vault_manager: Callable[[], VaultManager],
    get_portal_manager: Callable[[], PortalManager],
) -> None:
    """Register all enterprise commands with the main app.

    Args:
        app: Main Typer app to register enterprise commands on.
        get_workspace_manager: Factory function for WorkspaceManager.
        get_rbac_manager: Factory function for RBACManager.
        get_vault_manager: Factory function for VaultManager.
        get_portal_manager: Factory function for PortalManager.
    """
    enterprise_app = typer.Typer(
        name="enterprise",
        help="Kong Enterprise features (workspaces, RBAC, vaults, portal)",
        no_args_is_help=True,
    )

    # Register sub-command groups
    register_workspace_commands(enterprise_app, get_workspace_manager)
    register_rbac_commands(enterprise_app, get_rbac_manager)
    register_vault_commands(enterprise_app, get_vault_manager)
    register_portal_commands(enterprise_app, get_portal_manager)

    app.add_typer(enterprise_app, name="enterprise")
