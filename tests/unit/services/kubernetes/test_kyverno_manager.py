"""Unit tests for KyvernoManager."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from system_operations_manager.integrations.kubernetes.models.kyverno import (
    KyvernoPolicySummary,
    PolicyReportSummary,
)
from system_operations_manager.services.kubernetes.kyverno_manager import (
    CLUSTER_POLICY_PLURAL,
    CLUSTER_POLICY_REPORT_PLURAL,
    KYVERNO_GROUP,
    KYVERNO_VERSION,
    POLICY_PLURAL,
    POLICY_REPORT_GROUP,
    POLICY_REPORT_PLURAL,
    POLICY_REPORT_VERSION,
    KyvernoManager,
)


@pytest.fixture
def mock_k8s_client() -> MagicMock:
    """Create a mock Kubernetes client with default namespace."""
    mock_client = MagicMock()
    mock_client.default_namespace = "default"
    return mock_client


@pytest.fixture
def manager(mock_k8s_client: MagicMock) -> KyvernoManager:
    """Create a KyvernoManager with a mocked client."""
    return KyvernoManager(mock_k8s_client)


# =============================================================================
# ClusterPolicy Operations
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestClusterPolicyOperations:
    """Tests for cluster-scoped ClusterPolicy CRUD operations."""

    def test_list_cluster_policies_success(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_cluster_policies should return one summary per item in the API response."""
        mock_k8s_client.custom_objects.list_cluster_custom_object.return_value = {"items": [{}, {}]}

        with patch.object(KyvernoPolicySummary, "from_k8s_object") as mock_from:
            mock_from.return_value = MagicMock()
            result = manager.list_cluster_policies()

        assert len(result) == 2
        assert mock_from.call_count == 2
        mock_k8s_client.custom_objects.list_cluster_custom_object.assert_called_once_with(
            KYVERNO_GROUP,
            KYVERNO_VERSION,
            CLUSTER_POLICY_PLURAL,
        )

    def test_list_cluster_policies_with_label_selector(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_cluster_policies should forward label_selector to the API call."""
        mock_k8s_client.custom_objects.list_cluster_custom_object.return_value = {"items": []}

        manager.list_cluster_policies(label_selector="env=prod")

        mock_k8s_client.custom_objects.list_cluster_custom_object.assert_called_once_with(
            KYVERNO_GROUP,
            KYVERNO_VERSION,
            CLUSTER_POLICY_PLURAL,
            label_selector="env=prod",
        )

    def test_list_cluster_policies_api_error(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_cluster_policies should propagate exceptions via _handle_api_error."""
        mock_k8s_client.custom_objects.list_cluster_custom_object.side_effect = Exception(
            "connection refused"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("api error")

        with pytest.raises(RuntimeError, match="api error"):
            manager.list_cluster_policies()

        mock_k8s_client.translate_api_exception.assert_called_once()

    def test_get_cluster_policy_success(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_cluster_policy should call get_cluster_custom_object and parse the result."""
        mock_k8s_client.custom_objects.get_cluster_custom_object.return_value = {}

        with patch.object(KyvernoPolicySummary, "from_k8s_object") as mock_from:
            mock_summary = MagicMock()
            mock_from.return_value = mock_summary
            result = manager.get_cluster_policy("require-labels")

        assert result is mock_summary
        mock_from.assert_called_once_with({}, is_cluster_policy=True)
        mock_k8s_client.custom_objects.get_cluster_custom_object.assert_called_once_with(
            KYVERNO_GROUP,
            KYVERNO_VERSION,
            CLUSTER_POLICY_PLURAL,
            "require-labels",
        )

    def test_get_cluster_policy_api_error(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_cluster_policy should propagate exceptions via _handle_api_error."""
        mock_k8s_client.custom_objects.get_cluster_custom_object.side_effect = Exception(
            "not found"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("api error")

        with pytest.raises(RuntimeError, match="api error"):
            manager.get_cluster_policy("missing-policy")

        mock_k8s_client.translate_api_exception.assert_called_once()

    def test_create_cluster_policy_success_default_params(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_cluster_policy should build the correct body using default params."""
        mock_k8s_client.custom_objects.create_cluster_custom_object.return_value = {}

        with patch.object(KyvernoPolicySummary, "from_k8s_object") as mock_from:
            mock_summary = MagicMock()
            mock_from.return_value = mock_summary
            result = manager.create_cluster_policy("require-labels")

        assert result is mock_summary
        call_args = mock_k8s_client.custom_objects.create_cluster_custom_object.call_args
        group, version, plural, body = call_args[0]
        assert group == KYVERNO_GROUP
        assert version == KYVERNO_VERSION
        assert plural == CLUSTER_POLICY_PLURAL
        assert body["apiVersion"] == f"{KYVERNO_GROUP}/{KYVERNO_VERSION}"
        assert body["kind"] == "ClusterPolicy"
        assert body["metadata"]["name"] == "require-labels"
        assert body["metadata"]["labels"] == {}
        assert body["spec"]["background"] is True
        assert body["spec"]["validationFailureAction"] == "Audit"
        assert body["spec"]["rules"] == []

    def test_create_cluster_policy_with_all_params(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_cluster_policy should embed all optional parameters correctly."""
        rules = [{"name": "check-labels", "match": {"any": []}, "validate": {}}]
        labels = {"team": "platform", "env": "prod"}
        mock_k8s_client.custom_objects.create_cluster_custom_object.return_value = {}

        with patch.object(KyvernoPolicySummary, "from_k8s_object"):
            manager.create_cluster_policy(
                "enforce-labels",
                rules=rules,
                background=False,
                validation_failure_action="Enforce",
                labels=labels,
            )

        call_args = mock_k8s_client.custom_objects.create_cluster_custom_object.call_args
        body = call_args[0][3]
        assert body["metadata"]["name"] == "enforce-labels"
        assert body["metadata"]["labels"] == labels
        assert body["spec"]["background"] is False
        assert body["spec"]["validationFailureAction"] == "Enforce"
        assert body["spec"]["rules"] == rules

    def test_create_cluster_policy_api_error(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_cluster_policy should propagate exceptions via _handle_api_error."""
        mock_k8s_client.custom_objects.create_cluster_custom_object.side_effect = Exception(
            "already exists"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("api error")

        with pytest.raises(RuntimeError, match="api error"):
            manager.create_cluster_policy("require-labels")

        mock_k8s_client.translate_api_exception.assert_called_once()

    def test_delete_cluster_policy_success(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """delete_cluster_policy should call delete_cluster_custom_object."""
        manager.delete_cluster_policy("require-labels")

        mock_k8s_client.custom_objects.delete_cluster_custom_object.assert_called_once_with(
            KYVERNO_GROUP,
            KYVERNO_VERSION,
            CLUSTER_POLICY_PLURAL,
            "require-labels",
        )

    def test_delete_cluster_policy_api_error(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """delete_cluster_policy should propagate exceptions via _handle_api_error."""
        mock_k8s_client.custom_objects.delete_cluster_custom_object.side_effect = Exception(
            "forbidden"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("api error")

        with pytest.raises(RuntimeError, match="api error"):
            manager.delete_cluster_policy("require-labels")

        mock_k8s_client.translate_api_exception.assert_called_once()


# =============================================================================
# Namespaced Policy Operations
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestNamespacedPolicyOperations:
    """Tests for namespaced Policy CRUD operations."""

    def test_list_policies_success(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_policies should return one summary per item in the API response."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {
            "items": [{}, {}, {}]
        }

        with patch.object(KyvernoPolicySummary, "from_k8s_object") as mock_from:
            mock_from.return_value = MagicMock()
            result = manager.list_policies()

        assert len(result) == 3
        assert mock_from.call_count == 3
        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            KYVERNO_GROUP,
            KYVERNO_VERSION,
            "default",
            POLICY_PLURAL,
        )

    def test_list_policies_with_label_selector(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_policies should forward label_selector to the API call."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

        manager.list_policies(label_selector="app=backend")

        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            KYVERNO_GROUP,
            KYVERNO_VERSION,
            "default",
            POLICY_PLURAL,
            label_selector="app=backend",
        )

    def test_list_policies_api_error(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_policies should propagate exceptions via _handle_api_error."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.side_effect = Exception(
            "timeout"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("api error")

        with pytest.raises(RuntimeError, match="api error"):
            manager.list_policies()

        mock_k8s_client.translate_api_exception.assert_called_once()

    def test_get_policy_success(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_policy should call get_namespaced_custom_object and parse the result."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {}

        with patch.object(KyvernoPolicySummary, "from_k8s_object") as mock_from:
            mock_summary = MagicMock()
            mock_from.return_value = mock_summary
            result = manager.get_policy("restrict-images")

        assert result is mock_summary
        mock_from.assert_called_once_with({})
        mock_k8s_client.custom_objects.get_namespaced_custom_object.assert_called_once_with(
            KYVERNO_GROUP,
            KYVERNO_VERSION,
            "default",
            POLICY_PLURAL,
            "restrict-images",
        )

    def test_get_policy_api_error(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_policy should propagate exceptions via _handle_api_error."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.side_effect = Exception(
            "not found"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("api error")

        with pytest.raises(RuntimeError, match="api error"):
            manager.get_policy("missing-policy")

        mock_k8s_client.translate_api_exception.assert_called_once()

    def test_create_policy_success_includes_namespace_in_body(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_policy body must include the resolved namespace in metadata."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = {}

        with patch.object(KyvernoPolicySummary, "from_k8s_object") as mock_from:
            mock_summary = MagicMock()
            mock_from.return_value = mock_summary
            result = manager.create_policy("restrict-images")

        assert result is mock_summary
        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        group, version, ns, plural, body = call_args[0]
        assert group == KYVERNO_GROUP
        assert version == KYVERNO_VERSION
        assert ns == "default"
        assert plural == POLICY_PLURAL
        assert body["apiVersion"] == f"{KYVERNO_GROUP}/{KYVERNO_VERSION}"
        assert body["kind"] == "Policy"
        assert body["metadata"]["name"] == "restrict-images"
        assert body["metadata"]["namespace"] == "default"
        assert body["metadata"]["labels"] == {}
        assert body["spec"]["background"] is True
        assert body["spec"]["validationFailureAction"] == "Audit"
        assert body["spec"]["rules"] == []

    def test_create_policy_with_all_params(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_policy should embed all optional parameters in the body."""
        rules = [{"name": "check-image-registry", "match": {"any": []}, "validate": {}}]
        labels = {"managed-by": "ops-cli"}
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = {}

        with patch.object(KyvernoPolicySummary, "from_k8s_object"):
            manager.create_policy(
                "restrict-images",
                "production",
                rules=rules,
                background=False,
                validation_failure_action="Enforce",
                labels=labels,
            )

        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args[0][4]
        assert body["metadata"]["name"] == "restrict-images"
        assert body["metadata"]["namespace"] == "production"
        assert body["metadata"]["labels"] == labels
        assert body["spec"]["background"] is False
        assert body["spec"]["validationFailureAction"] == "Enforce"
        assert body["spec"]["rules"] == rules

    def test_create_policy_api_error(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_policy should propagate exceptions via _handle_api_error."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.side_effect = Exception(
            "conflict"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("api error")

        with pytest.raises(RuntimeError, match="api error"):
            manager.create_policy("restrict-images")

        mock_k8s_client.translate_api_exception.assert_called_once()

    def test_delete_policy_success(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """delete_policy should call delete_namespaced_custom_object."""
        manager.delete_policy("restrict-images")

        mock_k8s_client.custom_objects.delete_namespaced_custom_object.assert_called_once_with(
            KYVERNO_GROUP,
            KYVERNO_VERSION,
            "default",
            POLICY_PLURAL,
            "restrict-images",
        )

    def test_delete_policy_api_error(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """delete_policy should propagate exceptions via _handle_api_error."""
        mock_k8s_client.custom_objects.delete_namespaced_custom_object.side_effect = Exception(
            "forbidden"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("api error")

        with pytest.raises(RuntimeError, match="api error"):
            manager.delete_policy("restrict-images")

        mock_k8s_client.translate_api_exception.assert_called_once()


# =============================================================================
# ClusterPolicyReport Operations
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestClusterPolicyReportOperations:
    """Tests for cluster-scoped ClusterPolicyReport read operations."""

    def test_list_cluster_policy_reports_success(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_cluster_policy_reports should return one summary per item."""
        mock_k8s_client.custom_objects.list_cluster_custom_object.return_value = {"items": [{}, {}]}

        with patch.object(PolicyReportSummary, "from_k8s_object") as mock_from:
            mock_from.return_value = MagicMock()
            result = manager.list_cluster_policy_reports()

        assert len(result) == 2
        assert mock_from.call_count == 2
        mock_from.assert_any_call({}, is_cluster_report=True)
        mock_k8s_client.custom_objects.list_cluster_custom_object.assert_called_once_with(
            POLICY_REPORT_GROUP,
            POLICY_REPORT_VERSION,
            CLUSTER_POLICY_REPORT_PLURAL,
        )

    def test_list_cluster_policy_reports_api_error(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_cluster_policy_reports should propagate exceptions via _handle_api_error."""
        mock_k8s_client.custom_objects.list_cluster_custom_object.side_effect = Exception(
            "connection refused"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("api error")

        with pytest.raises(RuntimeError, match="api error"):
            manager.list_cluster_policy_reports()

        mock_k8s_client.translate_api_exception.assert_called_once()

    def test_get_cluster_policy_report_success(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_cluster_policy_report should call get_cluster_custom_object with correct args."""
        mock_k8s_client.custom_objects.get_cluster_custom_object.return_value = {}

        with patch.object(PolicyReportSummary, "from_k8s_object") as mock_from:
            mock_summary = MagicMock()
            mock_from.return_value = mock_summary
            result = manager.get_cluster_policy_report("cluster-report-1")

        assert result is mock_summary
        mock_from.assert_called_once_with({}, is_cluster_report=True)
        mock_k8s_client.custom_objects.get_cluster_custom_object.assert_called_once_with(
            POLICY_REPORT_GROUP,
            POLICY_REPORT_VERSION,
            CLUSTER_POLICY_REPORT_PLURAL,
            "cluster-report-1",
        )

    def test_get_cluster_policy_report_api_error(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_cluster_policy_report should propagate exceptions via _handle_api_error."""
        mock_k8s_client.custom_objects.get_cluster_custom_object.side_effect = Exception(
            "not found"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("api error")

        with pytest.raises(RuntimeError, match="api error"):
            manager.get_cluster_policy_report("missing-report")

        mock_k8s_client.translate_api_exception.assert_called_once()


# =============================================================================
# PolicyReport Operations
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestPolicyReportOperations:
    """Tests for namespaced PolicyReport read operations."""

    def test_list_policy_reports_success(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_policy_reports should return one summary per item in the API response."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": [{}]}

        with patch.object(PolicyReportSummary, "from_k8s_object") as mock_from:
            mock_from.return_value = MagicMock()
            result = manager.list_policy_reports()

        assert len(result) == 1
        mock_from.assert_called_once_with({})
        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            POLICY_REPORT_GROUP,
            POLICY_REPORT_VERSION,
            "default",
            POLICY_REPORT_PLURAL,
        )

    def test_list_policy_reports_api_error(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_policy_reports should propagate exceptions via _handle_api_error."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.side_effect = Exception(
            "timeout"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("api error")

        with pytest.raises(RuntimeError, match="api error"):
            manager.list_policy_reports()

        mock_k8s_client.translate_api_exception.assert_called_once()

    def test_get_policy_report_success(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_policy_report should call get_namespaced_custom_object and parse the result."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {}

        with patch.object(PolicyReportSummary, "from_k8s_object") as mock_from:
            mock_summary = MagicMock()
            mock_from.return_value = mock_summary
            result = manager.get_policy_report("ns-report-1")

        assert result is mock_summary
        mock_from.assert_called_once_with({})
        mock_k8s_client.custom_objects.get_namespaced_custom_object.assert_called_once_with(
            POLICY_REPORT_GROUP,
            POLICY_REPORT_VERSION,
            "default",
            POLICY_REPORT_PLURAL,
            "ns-report-1",
        )

    def test_get_policy_report_api_error(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_policy_report should propagate exceptions via _handle_api_error."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.side_effect = Exception(
            "forbidden"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("api error")

        with pytest.raises(RuntimeError, match="api error"):
            manager.get_policy_report("ns-report-1")

        mock_k8s_client.translate_api_exception.assert_called_once()


# =============================================================================
# Admission Controller Status
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestAdmissionControllerStatus:
    """Tests for get_admission_status."""

    def test_get_admission_status_running_pods(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_admission_status should return running=True when all pods are Running."""
        mock_pod = MagicMock()
        mock_pod.metadata.name = "kyverno-admission-abc12"
        mock_pod.status.phase = "Running"
        mock_pod.spec.containers = [MagicMock(image="ghcr.io/kyverno/kyverno:v1.11.0")]
        mock_k8s_client.core_v1.list_namespaced_pod.return_value.items = [mock_pod]

        result = manager.get_admission_status()

        assert result["running"] is True
        assert len(result["pods"]) == 1
        assert result["pods"][0]["name"] == "kyverno-admission-abc12"
        assert result["pods"][0]["status"] == "Running"
        mock_k8s_client.core_v1.list_namespaced_pod.assert_called_once_with(
            namespace="kyverno",
            label_selector="app.kubernetes.io/component=admission-controller",
        )

    def test_get_admission_status_no_pods(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_admission_status should return running=False when no pods are found."""
        mock_k8s_client.core_v1.list_namespaced_pod.return_value.items = []

        result = manager.get_admission_status()

        assert result["running"] is False
        assert result["pods"] == []

    def test_get_admission_status_pod_not_in_running_state(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_admission_status should return running=False when any pod is not Running."""
        mock_pod_running = MagicMock()
        mock_pod_running.metadata.name = "kyverno-admission-pod-1"
        mock_pod_running.status.phase = "Running"
        mock_pod_running.spec.containers = [MagicMock(image="ghcr.io/kyverno/kyverno:v1.11.0")]

        mock_pod_pending = MagicMock()
        mock_pod_pending.metadata.name = "kyverno-admission-pod-2"
        mock_pod_pending.status.phase = "Pending"
        mock_pod_pending.spec.containers = [MagicMock(image="ghcr.io/kyverno/kyverno:v1.11.0")]

        mock_k8s_client.core_v1.list_namespaced_pod.return_value.items = [
            mock_pod_running,
            mock_pod_pending,
        ]

        result = manager.get_admission_status()

        assert result["running"] is False
        assert len(result["pods"]) == 2

    def test_get_admission_status_extracts_version_from_image_tag(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_admission_status should extract version from the first container image tag."""
        mock_pod = MagicMock()
        mock_pod.metadata.name = "kyverno-admission-xyz"
        mock_pod.status.phase = "Running"
        mock_pod.spec.containers = [MagicMock(image="ghcr.io/kyverno/kyverno:v1.11.4")]
        mock_k8s_client.core_v1.list_namespaced_pod.return_value.items = [mock_pod]

        result = manager.get_admission_status()

        assert result.get("version") == "v1.11.4"

    def test_get_admission_status_api_error_returns_error_dict(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_admission_status should return an error dict when the API call fails."""
        mock_k8s_client.core_v1.list_namespaced_pod.side_effect = Exception("unreachable")

        result = manager.get_admission_status()

        assert result["running"] is False
        assert result["pods"] == []
        assert "error" in result
        assert result["error"] == "Could not reach kyverno namespace"


# =============================================================================
# Policy Validation (dry-run)
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestPolicyValidation:
    """Tests for validate_policy dry-run logic."""

    def test_validate_cluster_policy_valid(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """validate_policy for a ClusterPolicy should call create_cluster_custom_object with dry_run=All."""
        policy_dict = {
            "kind": "ClusterPolicy",
            "metadata": {"name": "require-labels"},
            "spec": {"rules": []},
        }
        mock_k8s_client.custom_objects.create_cluster_custom_object.return_value = {}

        with patch.object(KyvernoPolicySummary, "from_k8s_object") as mock_from:
            mock_summary = MagicMock()
            mock_from.return_value = mock_summary
            result = manager.validate_policy(policy_dict)

        assert result["valid"] is True
        assert result["policy"] is mock_summary
        mock_k8s_client.custom_objects.create_cluster_custom_object.assert_called_once_with(
            KYVERNO_GROUP,
            KYVERNO_VERSION,
            CLUSTER_POLICY_PLURAL,
            policy_dict,
            dry_run="All",
        )

    def test_validate_namespaced_policy_valid(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """validate_policy for a Policy should call create_namespaced_custom_object with dry_run=All."""
        policy_dict = {
            "kind": "Policy",
            "metadata": {"name": "restrict-images", "namespace": "staging"},
            "spec": {"rules": []},
        }
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = {}

        with patch.object(KyvernoPolicySummary, "from_k8s_object") as mock_from:
            mock_summary = MagicMock()
            mock_from.return_value = mock_summary
            result = manager.validate_policy(policy_dict)

        assert result["valid"] is True
        assert result["policy"] is mock_summary
        mock_k8s_client.custom_objects.create_namespaced_custom_object.assert_called_once_with(
            KYVERNO_GROUP,
            KYVERNO_VERSION,
            "staging",
            POLICY_PLURAL,
            policy_dict,
            dry_run="All",
        )

    def test_validate_namespaced_policy_falls_back_to_default_namespace(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """validate_policy for a Policy with no namespace in metadata should use the client default."""
        policy_dict = {
            "kind": "Policy",
            "metadata": {"name": "restrict-images"},
            "spec": {"rules": []},
        }
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = {}

        with patch.object(KyvernoPolicySummary, "from_k8s_object"):
            result = manager.validate_policy(policy_dict)

        assert result["valid"] is True
        # verify the namespace passed to the API was the client default
        actual_ns = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args[0][2]
        assert actual_ns == "default"

    def test_validate_namespaced_policy_invalid_returns_error_dict(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """validate_policy should return valid=False and the error message on failure."""
        policy_dict = {
            "kind": "Policy",
            "metadata": {"name": "bad-policy", "namespace": "default"},
            "spec": {},
        }
        mock_k8s_client.custom_objects.create_namespaced_custom_object.side_effect = Exception(
            "schema validation failed"
        )

        result = manager.validate_policy(policy_dict)

        assert result["valid"] is False
        assert "schema validation failed" in result["error"]

    def test_validate_cluster_policy_invalid_returns_error_dict(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """validate_policy should return valid=False and the error message on ClusterPolicy failure."""
        policy_dict = {
            "kind": "ClusterPolicy",
            "metadata": {"name": "bad-cluster-policy"},
            "spec": {},
        }
        mock_k8s_client.custom_objects.create_cluster_custom_object.side_effect = Exception(
            "invalid spec"
        )

        result = manager.validate_policy(policy_dict)

        assert result["valid"] is False
        assert "invalid spec" in result["error"]


# =============================================================================
# Namespace Resolution
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestNamespaceResolution:
    """Tests verifying namespace fall-through to client default."""

    def test_list_policies_uses_explicit_namespace(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """When a namespace is given, list_policies should forward it to the API."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

        manager.list_policies("kube-system")

        call_args = mock_k8s_client.custom_objects.list_namespaced_custom_object.call_args
        assert call_args[0][2] == "kube-system"

    def test_get_policy_uses_explicit_namespace(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """When a namespace is given, get_policy should forward it to the API."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {}

        with patch.object(KyvernoPolicySummary, "from_k8s_object"):
            manager.get_policy("my-policy", "production")

        call_args = mock_k8s_client.custom_objects.get_namespaced_custom_object.call_args
        assert call_args[0][2] == "production"

    def test_delete_policy_uses_explicit_namespace(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """When a namespace is given, delete_policy should forward it to the API."""
        manager.delete_policy("my-policy", "staging")

        call_args = mock_k8s_client.custom_objects.delete_namespaced_custom_object.call_args
        assert call_args[0][2] == "staging"

    def test_list_policy_reports_uses_explicit_namespace(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """When a namespace is given, list_policy_reports should forward it to the API."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

        manager.list_policy_reports("monitoring")

        call_args = mock_k8s_client.custom_objects.list_namespaced_custom_object.call_args
        assert call_args[0][2] == "monitoring"

    def test_get_policy_report_uses_explicit_namespace(
        self,
        manager: KyvernoManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """When a namespace is given, get_policy_report should forward it to the API."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {}

        with patch.object(PolicyReportSummary, "from_k8s_object"):
            manager.get_policy_report("report-1", "monitoring")

        call_args = mock_k8s_client.custom_objects.get_namespaced_custom_object.call_args
        assert call_args[0][2] == "monitoring"


# =============================================================================
# Constants
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestConstants:
    """Tests verifying that module-level Kyverno constants are correct."""

    def test_kyverno_group_constant(self) -> None:
        """KYVERNO_GROUP should be the kyverno.io API group."""
        assert KYVERNO_GROUP == "kyverno.io"

    def test_kyverno_version_constant(self) -> None:
        """KYVERNO_VERSION should be v1."""
        assert KYVERNO_VERSION == "v1"

    def test_cluster_policy_plural_constant(self) -> None:
        """CLUSTER_POLICY_PLURAL should be clusterpolicies."""
        assert CLUSTER_POLICY_PLURAL == "clusterpolicies"

    def test_policy_plural_constant(self) -> None:
        """POLICY_PLURAL should be policies."""
        assert POLICY_PLURAL == "policies"

    def test_policy_report_group_constant(self) -> None:
        """POLICY_REPORT_GROUP should be wgpolicyk8s.io."""
        assert POLICY_REPORT_GROUP == "wgpolicyk8s.io"

    def test_policy_report_version_constant(self) -> None:
        """POLICY_REPORT_VERSION should be v1alpha2."""
        assert POLICY_REPORT_VERSION == "v1alpha2"

    def test_cluster_policy_report_plural_constant(self) -> None:
        """CLUSTER_POLICY_REPORT_PLURAL should be clusterpolicyreports."""
        assert CLUSTER_POLICY_REPORT_PLURAL == "clusterpolicyreports"

    def test_policy_report_plural_constant(self) -> None:
        """POLICY_REPORT_PLURAL should be policyreports."""
        assert POLICY_REPORT_PLURAL == "policyreports"
