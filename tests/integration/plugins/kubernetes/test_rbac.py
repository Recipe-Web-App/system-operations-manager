"""Integration tests for Kubernetes RBACManager against real K3S cluster."""

import pytest

from system_operations_manager.services.kubernetes import RBACManager


@pytest.mark.integration
@pytest.mark.kubernetes
class TestServiceAccountCRUD:
    """Test CRUD operations for Kubernetes service accounts."""

    def test_create_service_account(
        self, rbac_manager: RBACManager, test_namespace: str, unique_name: str
    ) -> None:
        """Test creating a service account."""
        sa_name = f"sa-{unique_name}"

        sa = rbac_manager.create_service_account(
            name=sa_name,
            namespace=test_namespace,
            labels={"test": "integration"},
        )

        assert sa.name == sa_name
        assert sa.namespace == test_namespace

    def test_list_service_accounts(
        self, rbac_manager: RBACManager, test_namespace: str, unique_name: str
    ) -> None:
        """Test listing service accounts (default SA should exist)."""
        sa_name = f"sa-{unique_name}"

        # Create a service account
        rbac_manager.create_service_account(
            name=sa_name,
            namespace=test_namespace,
            labels={"test": "list-test"},
        )

        # List service accounts
        sas = rbac_manager.list_service_accounts(namespace=test_namespace)

        # K8s creates a default service account in each namespace
        assert len(sas) >= 2  # At least default + our created SA
        sa_names = [sa.name for sa in sas]
        assert "default" in sa_names
        assert sa_name in sa_names

    def test_get_service_account(
        self, rbac_manager: RBACManager, test_namespace: str, unique_name: str
    ) -> None:
        """Test getting a specific service account."""
        sa_name = f"sa-{unique_name}"

        # Create a service account
        created_sa = rbac_manager.create_service_account(
            name=sa_name,
            namespace=test_namespace,
        )

        # Get the service account
        sa = rbac_manager.get_service_account(name=sa_name, namespace=test_namespace)

        assert sa.name == created_sa.name
        assert sa.namespace == created_sa.namespace

    def test_delete_service_account(
        self, rbac_manager: RBACManager, test_namespace: str, unique_name: str
    ) -> None:
        """Test deleting a service account."""
        sa_name = f"sa-{unique_name}"

        # Create a service account
        rbac_manager.create_service_account(
            name=sa_name,
            namespace=test_namespace,
        )

        # Delete the service account
        rbac_manager.delete_service_account(name=sa_name, namespace=test_namespace)

        # Verify it's deleted by checking list
        sas = rbac_manager.list_service_accounts(namespace=test_namespace)
        sa_names = [sa.name for sa in sas]
        assert sa_name not in sa_names


@pytest.mark.integration
@pytest.mark.kubernetes
class TestRoleCRUD:
    """Test CRUD operations for Kubernetes roles and role bindings."""

    def test_create_role(
        self, rbac_manager: RBACManager, test_namespace: str, unique_name: str
    ) -> None:
        """Test creating a role."""
        role_name = f"role-{unique_name}"

        rules = [
            {
                "apiGroups": [""],
                "resources": ["pods"],
                "verbs": ["get", "list"],
            }
        ]

        role = rbac_manager.create_role(
            name=role_name,
            namespace=test_namespace,
            rules=rules,
            labels={"test": "integration"},
        )

        assert role.name == role_name
        assert role.namespace == test_namespace

    def test_list_roles(
        self, rbac_manager: RBACManager, test_namespace: str, unique_name: str
    ) -> None:
        """Test listing roles in a namespace."""
        role_name = f"role-{unique_name}"

        # Create a role
        rules = [
            {
                "apiGroups": [""],
                "resources": ["pods"],
                "verbs": ["get", "list"],
            }
        ]

        rbac_manager.create_role(
            name=role_name,
            namespace=test_namespace,
            rules=rules,
        )

        # List roles
        roles = rbac_manager.list_roles(namespace=test_namespace)

        assert len(roles) > 0
        role_names = [r.name for r in roles]
        assert role_name in role_names

    def test_create_role_binding(
        self, rbac_manager: RBACManager, test_namespace: str, unique_name: str
    ) -> None:
        """Test creating a role binding."""
        role_name = f"role-{unique_name}"
        sa_name = f"sa-{unique_name}"
        rb_name = f"rb-{unique_name}"

        # Create service account
        rbac_manager.create_service_account(
            name=sa_name,
            namespace=test_namespace,
        )

        # Create role
        rules = [
            {
                "apiGroups": [""],
                "resources": ["pods"],
                "verbs": ["get", "list"],
            }
        ]

        rbac_manager.create_role(
            name=role_name,
            namespace=test_namespace,
            rules=rules,
        )

        # Create role binding
        role_ref = {
            "apiGroup": "rbac.authorization.k8s.io",
            "kind": "Role",
            "name": role_name,
        }

        subjects = [
            {
                "kind": "ServiceAccount",
                "name": sa_name,
                "namespace": test_namespace,
            }
        ]

        rb = rbac_manager.create_role_binding(
            name=rb_name,
            namespace=test_namespace,
            role_ref=role_ref,
            subjects=subjects,
            labels={"test": "integration"},
        )

        assert rb.name == rb_name
        assert rb.namespace == test_namespace

    def test_list_role_bindings(
        self, rbac_manager: RBACManager, test_namespace: str, unique_name: str
    ) -> None:
        """Test listing role bindings in a namespace."""
        role_name = f"role-{unique_name}"
        sa_name = f"sa-{unique_name}"
        rb_name = f"rb-{unique_name}"

        # Create service account
        rbac_manager.create_service_account(
            name=sa_name,
            namespace=test_namespace,
        )

        # Create role
        rules = [
            {
                "apiGroups": [""],
                "resources": ["pods"],
                "verbs": ["get", "list"],
            }
        ]

        rbac_manager.create_role(
            name=role_name,
            namespace=test_namespace,
            rules=rules,
        )

        # Create role binding
        role_ref = {
            "apiGroup": "rbac.authorization.k8s.io",
            "kind": "Role",
            "name": role_name,
        }

        subjects = [
            {
                "kind": "ServiceAccount",
                "name": sa_name,
                "namespace": test_namespace,
            }
        ]

        rbac_manager.create_role_binding(
            name=rb_name,
            namespace=test_namespace,
            role_ref=role_ref,
            subjects=subjects,
        )

        # List role bindings
        rbs = rbac_manager.list_role_bindings(namespace=test_namespace)

        assert len(rbs) > 0
        rb_names = [rb.name for rb in rbs]
        assert rb_name in rb_names
