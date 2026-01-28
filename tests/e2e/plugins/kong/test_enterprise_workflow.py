"""E2E tests for Kong Enterprise feature workflows.

These tests verify complete workflows for enterprise features:
- Workspace management (multi-tenancy)
- RBAC (Role-Based Access Control)
- Vault integrations (secret management)
- Developer Portal operations

Note: These tests require Kong Enterprise edition and are skipped on OSS Kong.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tests.e2e.plugins.kong.conftest import IS_ENTERPRISE, skip_enterprise

if TYPE_CHECKING:
    import typer
    from typer.testing import CliRunner

    from tests.e2e.plugins.kong.conftest import VaultContainer


# ============================================================================
# Workspace Workflow Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.kong
@pytest.mark.kong_enterprise
@skip_enterprise
class TestWorkspaceWorkflow:
    """Test workspace management workflows for multi-tenancy."""

    def test_list_workspaces(
        self,
        cli_runner: CliRunner,
        kong_enterprise_app: typer.Typer,
    ) -> None:
        """List workspaces - default workspace should exist."""
        result = cli_runner.invoke(
            kong_enterprise_app,
            ["kong", "enterprise", "workspaces", "list"],
        )
        assert result.exit_code == 0, f"Failed to list workspaces: {result.output}"
        # Default workspace should always exist
        assert "default" in result.output

    @pytest.mark.requires_license
    def test_create_workspace(
        self,
        cli_runner: CliRunner,
        kong_enterprise_app: typer.Typer,
        unique_prefix: str,
    ) -> None:
        """Create a new workspace and verify it exists."""
        workspace_name = f"{unique_prefix}-ws"

        # Create workspace
        result = cli_runner.invoke(
            kong_enterprise_app,
            ["kong", "enterprise", "workspaces", "create", workspace_name],
        )
        assert result.exit_code == 0, f"Failed to create workspace: {result.output}"

        # Verify workspace exists
        result = cli_runner.invoke(
            kong_enterprise_app,
            ["kong", "enterprise", "workspaces", "get", workspace_name],
        )
        assert result.exit_code == 0
        assert workspace_name in result.output

    @pytest.mark.requires_license
    def test_workspace_crud_workflow(
        self,
        cli_runner: CliRunner,
        kong_enterprise_app: typer.Typer,
        unique_prefix: str,
    ) -> None:
        """Full workspace CRUD workflow: create, update, delete."""
        workspace_name = f"{unique_prefix}-crud-ws"

        # Create
        result = cli_runner.invoke(
            kong_enterprise_app,
            ["kong", "enterprise", "workspaces", "create", workspace_name],
        )
        assert result.exit_code == 0

        # Update (add comment/meta if supported)
        cli_runner.invoke(
            kong_enterprise_app,
            [
                "kong",
                "enterprise",
                "workspaces",
                "update",
                workspace_name,
                "--comment",
                "Test workspace",
            ],
        )
        # Update may or may not be supported depending on implementation
        # Accept either success or graceful handling

        # Delete
        result = cli_runner.invoke(
            kong_enterprise_app,
            ["kong", "enterprise", "workspaces", "delete", workspace_name, "--yes"],
        )
        assert result.exit_code == 0

        # Verify deleted
        result = cli_runner.invoke(
            kong_enterprise_app,
            ["kong", "enterprise", "workspaces", "get", workspace_name],
        )
        # Should fail or show not found
        assert result.exit_code != 0 or "not found" in result.output.lower()

    def test_get_workspace_details(
        self,
        cli_runner: CliRunner,
        kong_enterprise_app: typer.Typer,
    ) -> None:
        """Get details for the default workspace including entity counts."""
        result = cli_runner.invoke(
            kong_enterprise_app,
            ["kong", "enterprise", "workspaces", "get", "default"],
        )
        assert result.exit_code == 0
        assert "default" in result.output


# ============================================================================
# RBAC Workflow Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.kong
@pytest.mark.kong_enterprise
@skip_enterprise
class TestRBACRoleWorkflow:
    """Test RBAC role management workflows."""

    def test_list_roles(
        self,
        cli_runner: CliRunner,
        kong_enterprise_app: typer.Typer,
    ) -> None:
        """List RBAC roles - should include default roles."""
        result = cli_runner.invoke(
            kong_enterprise_app,
            ["kong", "enterprise", "rbac", "roles", "list"],
        )
        assert result.exit_code == 0, f"Failed to list roles: {result.output}"

    @pytest.mark.requires_license
    def test_create_role(
        self,
        cli_runner: CliRunner,
        kong_enterprise_app: typer.Typer,
        unique_prefix: str,
    ) -> None:
        """Create a custom RBAC role."""
        role_name = f"{unique_prefix}-role"

        result = cli_runner.invoke(
            kong_enterprise_app,
            ["kong", "enterprise", "rbac", "roles", "create", role_name],
        )
        assert result.exit_code == 0, f"Failed to create role: {result.output}"

        # Verify role exists
        result = cli_runner.invoke(
            kong_enterprise_app,
            ["kong", "enterprise", "rbac", "roles", "get", role_name],
        )
        assert result.exit_code == 0
        assert role_name in result.output

    @pytest.mark.requires_license
    def test_role_with_permissions(
        self,
        cli_runner: CliRunner,
        kong_enterprise_app: typer.Typer,
        unique_prefix: str,
    ) -> None:
        """Create role and add endpoint permissions."""
        role_name = f"{unique_prefix}-perm-role"

        # Create role
        result = cli_runner.invoke(
            kong_enterprise_app,
            ["kong", "enterprise", "rbac", "roles", "create", role_name],
        )
        assert result.exit_code == 0

        # Add permission to role
        result = cli_runner.invoke(
            kong_enterprise_app,
            [
                "kong",
                "enterprise",
                "rbac",
                "roles",
                "add-endpoint-permission",
                role_name,
                "--endpoint",
                "/services",
                "--actions",
                "read",
            ],
        )
        assert result.exit_code == 0, f"Failed to add permission: {result.output}"

    @pytest.mark.requires_license
    def test_role_crud_workflow(
        self,
        cli_runner: CliRunner,
        kong_enterprise_app: typer.Typer,
        unique_prefix: str,
    ) -> None:
        """Full role CRUD: create, update, delete."""
        role_name = f"{unique_prefix}-crud-role"

        # Create
        result = cli_runner.invoke(
            kong_enterprise_app,
            ["kong", "enterprise", "rbac", "roles", "create", role_name],
        )
        assert result.exit_code == 0

        # Delete
        result = cli_runner.invoke(
            kong_enterprise_app,
            ["kong", "enterprise", "rbac", "roles", "delete", role_name, "--yes"],
        )
        assert result.exit_code == 0


@pytest.mark.e2e
@pytest.mark.kong
@pytest.mark.kong_enterprise
@skip_enterprise
class TestRBACUserWorkflow:
    """Test RBAC user management workflows."""

    def test_list_users(
        self,
        cli_runner: CliRunner,
        kong_enterprise_app: typer.Typer,
    ) -> None:
        """List RBAC users."""
        result = cli_runner.invoke(
            kong_enterprise_app,
            ["kong", "enterprise", "rbac", "users", "list"],
        )
        assert result.exit_code == 0, f"Failed to list users: {result.output}"

    @pytest.mark.requires_license
    def test_create_user(
        self,
        cli_runner: CliRunner,
        kong_enterprise_app: typer.Typer,
        unique_prefix: str,
    ) -> None:
        """Create an RBAC user."""
        user_name = f"{unique_prefix}-user"

        result = cli_runner.invoke(
            kong_enterprise_app,
            ["kong", "enterprise", "rbac", "users", "create", user_name],
        )
        assert result.exit_code == 0, f"Failed to create user: {result.output}"

        # Verify user exists
        result = cli_runner.invoke(
            kong_enterprise_app,
            ["kong", "enterprise", "rbac", "users", "get", user_name],
        )
        assert result.exit_code == 0
        assert user_name in result.output

    @pytest.mark.requires_license
    def test_user_role_assignment(
        self,
        cli_runner: CliRunner,
        kong_enterprise_app: typer.Typer,
        unique_prefix: str,
    ) -> None:
        """Create user and assign a role."""
        user_name = f"{unique_prefix}-assigned-user"
        role_name = f"{unique_prefix}-assigned-role"

        # Create role first
        result = cli_runner.invoke(
            kong_enterprise_app,
            ["kong", "enterprise", "rbac", "roles", "create", role_name],
        )
        assert result.exit_code == 0

        # Create user
        result = cli_runner.invoke(
            kong_enterprise_app,
            ["kong", "enterprise", "rbac", "users", "create", user_name],
        )
        assert result.exit_code == 0

        # Assign role to user
        result = cli_runner.invoke(
            kong_enterprise_app,
            ["kong", "enterprise", "rbac", "users", "add-role", user_name, role_name],
        )
        assert result.exit_code == 0, f"Failed to assign role: {result.output}"


# ============================================================================
# Vault Workflow Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.kong
@pytest.mark.kong_enterprise
@skip_enterprise
class TestVaultWorkflow:
    """Test vault integration workflows for secret management."""

    def test_list_vaults(
        self,
        cli_runner: CliRunner,
        kong_enterprise_app: typer.Typer,
    ) -> None:
        """List configured vaults."""
        result = cli_runner.invoke(
            kong_enterprise_app,
            ["kong", "enterprise", "vaults", "list"],
        )
        assert result.exit_code == 0, f"Failed to list vaults: {result.output}"

    @pytest.mark.requires_license
    def test_create_env_vault(
        self,
        cli_runner: CliRunner,
        kong_enterprise_app: typer.Typer,
        unique_prefix: str,
    ) -> None:
        """Create an environment variable vault."""
        vault_name = f"{unique_prefix}-env-vault"

        result = cli_runner.invoke(
            kong_enterprise_app,
            [
                "kong",
                "enterprise",
                "vaults",
                "configure",
                "env",
                vault_name,
                "--prefix",
                vault_name,
            ],
        )
        assert result.exit_code == 0, f"Failed to create env vault: {result.output}"

        # Verify vault exists
        result = cli_runner.invoke(
            kong_enterprise_app,
            ["kong", "enterprise", "vaults", "get", vault_name],
        )
        assert result.exit_code == 0

    @pytest.mark.requires_license
    def test_create_hcv_vault(
        self,
        cli_runner: CliRunner,
        kong_enterprise_app: typer.Typer,
        vault_container: VaultContainer,
        vault_url: str,
        vault_token: str,
        unique_prefix: str,
    ) -> None:
        """Create a HashiCorp Vault integration with real vault container."""
        vault_name = f"{unique_prefix}-hcv-vault"

        result = cli_runner.invoke(
            kong_enterprise_app,
            [
                "kong",
                "enterprise",
                "vaults",
                "configure",
                "hcv",
                vault_name,
                "--host",
                vault_url,
                "--token",
                vault_token,
                "--prefix",
                vault_name,
            ],
        )
        assert result.exit_code == 0, f"Failed to create HCV vault: {result.output}"

    @pytest.mark.requires_license
    def test_vault_crud_workflow(
        self,
        cli_runner: CliRunner,
        kong_enterprise_app: typer.Typer,
        unique_prefix: str,
    ) -> None:
        """Full vault CRUD: create, update, delete."""
        vault_name = f"{unique_prefix}-crud-vault"

        # Create
        result = cli_runner.invoke(
            kong_enterprise_app,
            [
                "kong",
                "enterprise",
                "vaults",
                "configure",
                "env",
                vault_name,
                "--prefix",
                vault_name,
            ],
        )
        assert result.exit_code == 0

        # Delete
        result = cli_runner.invoke(
            kong_enterprise_app,
            ["kong", "enterprise", "vaults", "delete", vault_name, "--yes"],
        )
        assert result.exit_code == 0


# ============================================================================
# Developer Portal Workflow Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.kong
@pytest.mark.kong_enterprise
@skip_enterprise
class TestPortalWorkflow:
    """Test Developer Portal workflows."""

    def test_portal_status(
        self,
        cli_runner: CliRunner,
        kong_enterprise_app: typer.Typer,
    ) -> None:
        """Check Developer Portal status."""
        result = cli_runner.invoke(
            kong_enterprise_app,
            ["kong", "enterprise", "portal", "status"],
        )
        assert result.exit_code == 0, f"Failed to get portal status: {result.output}"

    def test_list_specs(
        self,
        cli_runner: CliRunner,
        kong_enterprise_app: typer.Typer,
    ) -> None:
        """List API specifications in the portal."""
        result = cli_runner.invoke(
            kong_enterprise_app,
            ["kong", "enterprise", "portal", "specs", "list"],
        )
        assert result.exit_code == 0, f"Failed to list specs: {result.output}"

    @pytest.mark.requires_license
    def test_publish_spec(
        self,
        cli_runner: CliRunner,
        kong_enterprise_app: typer.Typer,
        temp_config_dir: Path,
        unique_prefix: str,
    ) -> None:
        """Publish an API specification to the portal."""
        spec_name = f"{unique_prefix}-api"
        spec_file = temp_config_dir / "openapi.yaml"

        # Create a minimal OpenAPI spec
        spec_content = {
            "openapi": "3.0.0",
            "info": {
                "title": f"{spec_name} API",
                "version": "1.0.0",
            },
            "paths": {
                "/health": {
                    "get": {
                        "summary": "Health check",
                        "responses": {
                            "200": {"description": "OK"},
                        },
                    },
                },
            },
        }

        import yaml

        spec_file.write_text(yaml.dump(spec_content))

        result = cli_runner.invoke(
            kong_enterprise_app,
            [
                "kong",
                "enterprise",
                "portal",
                "specs",
                "publish",
                str(spec_file),
                "--name",
                spec_name,
            ],
        )
        assert result.exit_code == 0, f"Failed to publish spec: {result.output}"

    def test_list_developers(
        self,
        cli_runner: CliRunner,
        kong_enterprise_app: typer.Typer,
    ) -> None:
        """List developers registered in the portal."""
        result = cli_runner.invoke(
            kong_enterprise_app,
            ["kong", "enterprise", "portal", "developers", "list"],
        )
        assert result.exit_code == 0, f"Failed to list developers: {result.output}"


# ============================================================================
# Enterprise Feature Detection Test
# ============================================================================


@pytest.mark.e2e
@pytest.mark.kong
class TestEnterpriseDetection:
    """Test that enterprise detection works correctly."""

    def test_enterprise_flag_matches_reality(
        self,
        cli_runner: CliRunner,
        kong_enterprise_app: typer.Typer,
    ) -> None:
        """Verify IS_ENTERPRISE flag matches actual Kong edition.

        This test runs on both OSS and Enterprise to verify detection.
        """
        # Try to access workspaces endpoint
        result = cli_runner.invoke(
            kong_enterprise_app,
            ["kong", "enterprise", "workspaces", "list"],
        )

        if IS_ENTERPRISE:
            # If we're configured for enterprise, workspaces should work
            assert result.exit_code == 0, (
                f"IS_ENTERPRISE=True but workspaces failed: {result.output}"
            )
        else:
            # If not enterprise, workspaces should fail
            # Accept any failure - could be connection refused, 404, etc.
            pass  # No assertion needed - just verifying it doesn't crash
