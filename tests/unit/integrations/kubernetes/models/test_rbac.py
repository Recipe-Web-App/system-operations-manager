"""Unit tests for Kubernetes RBAC resource models."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kubernetes.models.rbac import (
    PolicyRule,
    RoleBindingSummary,
    RoleSummary,
    ServiceAccountSummary,
    Subject,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestSubject:
    """Test Subject model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with complete Subject."""
        obj = MagicMock()
        obj.kind = "ServiceAccount"
        obj.name = "default"
        obj.namespace = "kube-system"
        obj.api_group = "rbac.authorization.k8s.io"

        subject = Subject.from_k8s_object(obj)

        assert subject.kind == "ServiceAccount"
        assert subject.name == "default"
        assert subject.namespace == "kube-system"
        assert subject.api_group == "rbac.authorization.k8s.io"

    def test_from_k8s_object_user(self) -> None:
        """Test from_k8s_object with User subject."""
        obj = MagicMock()
        obj.kind = "User"
        obj.name = "admin@example.com"
        obj.namespace = None
        obj.api_group = "rbac.authorization.k8s.io"

        subject = Subject.from_k8s_object(obj)

        assert subject.kind == "User"
        assert subject.name == "admin@example.com"
        assert subject.namespace is None

    def test_from_k8s_object_group(self) -> None:
        """Test from_k8s_object with Group subject."""
        obj = MagicMock()
        obj.kind = "Group"
        obj.name = "system:authenticated"
        obj.namespace = None
        obj.api_group = None

        subject = Subject.from_k8s_object(obj)

        assert subject.kind == "Group"
        assert subject.name == "system:authenticated"

    def test_from_k8s_object_minimal(self) -> None:
        """Test from_k8s_object with minimal Subject."""
        obj = MagicMock()
        obj.kind = None
        obj.name = None
        obj.namespace = None
        obj.api_group = None

        subject = Subject.from_k8s_object(obj)

        assert subject.kind == ""
        assert subject.name == ""
        assert subject.namespace is None


@pytest.mark.unit
@pytest.mark.kubernetes
class TestPolicyRule:
    """Test PolicyRule model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with complete PolicyRule."""
        obj = MagicMock()
        obj.verbs = ["get", "list", "watch"]
        obj.api_groups = [""]
        obj.resources = ["pods", "services"]
        obj.resource_names = ["specific-pod"]

        rule = PolicyRule.from_k8s_object(obj)

        assert rule.verbs == ["get", "list", "watch"]
        assert rule.api_groups == [""]
        assert rule.resources == ["pods", "services"]
        assert rule.resource_names == ["specific-pod"]

    def test_from_k8s_object_all_verbs(self) -> None:
        """Test from_k8s_object with all verbs."""
        obj = MagicMock()
        obj.verbs = ["*"]
        obj.api_groups = ["*"]
        obj.resources = ["*"]
        obj.resource_names = []

        rule = PolicyRule.from_k8s_object(obj)

        assert rule.verbs == ["*"]
        assert rule.api_groups == ["*"]
        assert rule.resources == ["*"]

    def test_from_k8s_object_minimal(self) -> None:
        """Test from_k8s_object with minimal PolicyRule."""
        obj = MagicMock()
        obj.verbs = None
        obj.api_groups = None
        obj.resources = None
        obj.resource_names = None

        rule = PolicyRule.from_k8s_object(obj)

        assert rule.verbs == []
        assert rule.api_groups == []
        assert rule.resources == []
        assert rule.resource_names == []

    def test_from_k8s_object_apps_api_group(self) -> None:
        """Test from_k8s_object with apps API group."""
        obj = MagicMock()
        obj.verbs = ["create", "update", "delete"]
        obj.api_groups = ["apps"]
        obj.resources = ["deployments"]
        obj.resource_names = []

        rule = PolicyRule.from_k8s_object(obj)

        assert rule.api_groups == ["apps"]
        assert rule.resources == ["deployments"]


@pytest.mark.unit
@pytest.mark.kubernetes
class TestServiceAccountSummary:
    """Test ServiceAccountSummary model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with complete ServiceAccount."""
        obj = MagicMock()
        obj.metadata.name = "default"
        obj.metadata.namespace = "default"
        obj.metadata.uid = "uid-sa-123"
        obj.metadata.creation_timestamp = "2024-01-01T00:00:00Z"
        obj.metadata.labels = {"app": "test"}
        obj.metadata.annotations = {}

        secret1 = MagicMock()
        secret2 = MagicMock()
        obj.secrets = [secret1, secret2]

        sa = ServiceAccountSummary.from_k8s_object(obj)

        assert sa.name == "default"
        assert sa.namespace == "default"
        assert sa.secrets_count == 2

    def test_from_k8s_object_no_secrets(self) -> None:
        """Test from_k8s_object with no secrets."""
        obj = MagicMock()
        obj.metadata.name = "no-secrets-sa"
        obj.metadata.namespace = "kube-system"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None

        obj.secrets = []

        sa = ServiceAccountSummary.from_k8s_object(obj)

        assert sa.secrets_count == 0

    def test_from_k8s_object_none_secrets(self) -> None:
        """Test from_k8s_object with None secrets."""
        obj = MagicMock()
        obj.metadata.name = "none-secrets-sa"
        obj.metadata.namespace = "default"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None

        obj.secrets = None

        sa = ServiceAccountSummary.from_k8s_object(obj)

        assert sa.secrets_count == 0

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert ServiceAccountSummary._entity_name == "serviceaccount"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestRoleSummary:
    """Test RoleSummary model."""

    def test_from_k8s_object_role_complete(self) -> None:
        """Test from_k8s_object with complete Role."""
        obj = MagicMock()
        obj.metadata.name = "pod-reader"
        obj.metadata.namespace = "default"
        obj.metadata.uid = "uid-role-123"
        obj.metadata.creation_timestamp = "2024-01-01T00:00:00Z"
        obj.metadata.labels = {}
        obj.metadata.annotations = {}

        rule1 = MagicMock()
        rule1.verbs = ["get", "list"]
        rule1.api_groups = [""]
        rule1.resources = ["pods"]
        rule1.resource_names = []

        rule2 = MagicMock()
        rule2.verbs = ["get"]
        rule2.api_groups = [""]
        rule2.resources = ["pods/log"]
        rule2.resource_names = []

        obj.rules = [rule1, rule2]

        role = RoleSummary.from_k8s_object(obj, is_cluster_role=False)

        assert role.name == "pod-reader"
        assert role.namespace == "default"
        assert role.is_cluster_role is False
        assert role.rules_count == 2
        assert len(role.rules) == 2

    def test_from_k8s_object_cluster_role(self) -> None:
        """Test from_k8s_object with ClusterRole."""
        obj = MagicMock()
        obj.metadata.name = "cluster-admin"
        obj.metadata.namespace = None
        obj.metadata.uid = "uid-cr-456"
        obj.metadata.creation_timestamp = "2024-01-01T00:00:00Z"
        obj.metadata.labels = {}
        obj.metadata.annotations = {}

        rule = MagicMock()
        rule.verbs = ["*"]
        rule.api_groups = ["*"]
        rule.resources = ["*"]
        rule.resource_names = []

        obj.rules = [rule]

        role = RoleSummary.from_k8s_object(obj, is_cluster_role=True)

        assert role.name == "cluster-admin"
        assert role.namespace is None
        assert role.is_cluster_role is True
        assert role.rules_count == 1

    def test_from_k8s_object_no_rules(self) -> None:
        """Test from_k8s_object with no rules."""
        obj = MagicMock()
        obj.metadata.name = "empty-role"
        obj.metadata.namespace = "default"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None

        obj.rules = []

        role = RoleSummary.from_k8s_object(obj)

        assert role.rules_count == 0
        assert role.rules == []

    def test_from_k8s_object_none_rules(self) -> None:
        """Test from_k8s_object with None rules."""
        obj = MagicMock()
        obj.metadata.name = "none-rules-role"
        obj.metadata.namespace = None
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None
        obj.rules = None

        role = RoleSummary.from_k8s_object(obj)

        assert role.rules_count == 0
        assert role.rules == []

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert RoleSummary._entity_name == "role"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestRoleBindingSummary:
    """Test RoleBindingSummary model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with complete RoleBinding."""
        obj = MagicMock()
        obj.metadata.name = "read-pods"
        obj.metadata.namespace = "default"
        obj.metadata.uid = "uid-rb-123"
        obj.metadata.creation_timestamp = "2024-01-01T00:00:00Z"
        obj.metadata.labels = {}
        obj.metadata.annotations = {}

        obj.role_ref.kind = "Role"
        obj.role_ref.name = "pod-reader"

        subject1 = MagicMock()
        subject1.kind = "ServiceAccount"
        subject1.name = "default"
        subject1.namespace = "default"
        subject1.api_group = None

        subject2 = MagicMock()
        subject2.kind = "User"
        subject2.name = "jane"
        subject2.namespace = None
        subject2.api_group = "rbac.authorization.k8s.io"

        obj.subjects = [subject1, subject2]

        rb = RoleBindingSummary.from_k8s_object(obj, is_cluster_binding=False)

        assert rb.name == "read-pods"
        assert rb.namespace == "default"
        assert rb.is_cluster_binding is False
        assert rb.role_ref_kind == "Role"
        assert rb.role_ref_name == "pod-reader"
        assert len(rb.subjects) == 2

    def test_from_k8s_object_cluster_role_binding(self) -> None:
        """Test from_k8s_object with ClusterRoleBinding."""
        obj = MagicMock()
        obj.metadata.name = "cluster-admin-binding"
        obj.metadata.namespace = None
        obj.metadata.uid = "uid-crb-456"
        obj.metadata.creation_timestamp = "2024-01-01T00:00:00Z"
        obj.metadata.labels = {}
        obj.metadata.annotations = {}

        obj.role_ref.kind = "ClusterRole"
        obj.role_ref.name = "cluster-admin"

        subject = MagicMock()
        subject.kind = "User"
        subject.name = "admin"
        subject.namespace = None
        subject.api_group = "rbac.authorization.k8s.io"

        obj.subjects = [subject]

        rb = RoleBindingSummary.from_k8s_object(obj, is_cluster_binding=True)

        assert rb.name == "cluster-admin-binding"
        assert rb.namespace is None
        assert rb.is_cluster_binding is True
        assert rb.role_ref_kind == "ClusterRole"

    def test_from_k8s_object_no_subjects(self) -> None:
        """Test from_k8s_object with no subjects."""
        obj = MagicMock()
        obj.metadata.name = "no-subjects-rb"
        obj.metadata.namespace = "default"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None

        obj.role_ref.kind = "Role"
        obj.role_ref.name = "test-role"
        obj.subjects = []

        rb = RoleBindingSummary.from_k8s_object(obj)

        assert rb.subjects == []

    def test_from_k8s_object_none_subjects(self) -> None:
        """Test from_k8s_object with None subjects."""
        obj = MagicMock()
        obj.metadata.name = "none-subjects-rb"
        obj.metadata.namespace = None
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None
        obj.role_ref.kind = "Role"
        obj.role_ref.name = "test-role"
        obj.subjects = None

        rb = RoleBindingSummary.from_k8s_object(obj)

        assert rb.subjects == []

    def test_from_k8s_object_no_role_ref(self) -> None:
        """Test from_k8s_object with missing role_ref attributes."""
        obj = MagicMock()
        obj.metadata.name = "no-roleref-rb"
        obj.metadata.namespace = None
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None
        obj.role_ref = None
        obj.subjects = []

        rb = RoleBindingSummary.from_k8s_object(obj)

        assert rb.role_ref_kind is None
        assert rb.role_ref_name is None

    def test_from_k8s_object_group_subject(self) -> None:
        """Test from_k8s_object with Group subject."""
        obj = MagicMock()
        obj.metadata.name = "group-binding"
        obj.metadata.namespace = "default"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None

        obj.role_ref.kind = "Role"
        obj.role_ref.name = "viewer"

        subject = MagicMock()
        subject.kind = "Group"
        subject.name = "developers"
        subject.namespace = None
        subject.api_group = "rbac.authorization.k8s.io"

        obj.subjects = [subject]

        rb = RoleBindingSummary.from_k8s_object(obj)

        assert len(rb.subjects) == 1
        assert rb.subjects[0].kind == "Group"

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert RoleBindingSummary._entity_name == "rolebinding"
