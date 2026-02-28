"""Unit tests for OptimizationManager."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kubernetes.models.optimization import (
    OptimizationSummary,
    OrphanPod,
    ResourceMetrics,
    RightsizingRecommendation,
    StaleJob,
    WorkloadResourceAnalysis,
)
from system_operations_manager.services.kubernetes.optimization_manager import (
    IDLE_CPU_MILLICORES,
    IDLE_MEMORY_BYTES,
    OptimizationManager,
    _get_replicas,
    _parse_cpu,
    _parse_memory,
    _safe_nested_get,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_k8s_client() -> MagicMock:
    """Create a mock Kubernetes client."""
    mock_client = MagicMock()
    mock_client.default_namespace = "default"
    return mock_client


@pytest.fixture
def manager(mock_k8s_client: MagicMock) -> OptimizationManager:
    """Create an OptimizationManager with a mocked client."""
    return OptimizationManager(mock_k8s_client)


# =============================================================================
# Helpers
# =============================================================================


def _make_workload(
    name: str = "my-deploy",
    namespace: str = "default",
    replicas: int = 2,
    match_labels: dict[str, str] | None = None,
    cpu_request: str = "100m",
    cpu_limit: str = "200m",
    mem_request: str = "128Mi",
    mem_limit: str = "256Mi",
    creation_timestamp: datetime | str | None = None,
) -> MagicMock:
    """Build a minimal workload MagicMock with attribute-based access."""
    workload = MagicMock()
    workload.metadata.name = name
    workload.metadata.namespace = namespace
    workload.metadata.creation_timestamp = creation_timestamp
    workload.spec.replicas = replicas

    # selector
    if match_labels is not None:
        workload.spec.selector.match_labels = match_labels
    else:
        workload.spec.selector.match_labels = {"app": name}

    # single container in the pod template
    container = MagicMock()
    container.resources.requests = {"cpu": cpu_request, "memory": mem_request}
    container.resources.limits = {"cpu": cpu_limit, "memory": mem_limit}
    workload.spec.template.spec.containers = [container]

    return workload


def _make_pod_metrics_dict(
    namespace: str,
    pod_name: str,
    cpu: str = "50m",
    memory: str = "64Mi",
) -> dict[str, object]:
    """Build a raw metrics-server dict item (dict access, not attr)."""
    return {
        "metadata": {"name": pod_name, "namespace": namespace},
        "containers": [{"usage": {"cpu": cpu, "memory": memory}}],
    }


# =============================================================================
# Tests: _parse_cpu
# =============================================================================


class TestParseCpu:
    """Tests for the _parse_cpu module-level helper."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_zero_string(self) -> None:
        """'0' should parse to 0 millicores."""
        assert _parse_cpu("0") == 0

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_empty_string(self) -> None:
        """Empty string should parse to 0 millicores."""
        assert _parse_cpu("") == 0

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_nanocores(self) -> None:
        """Nanocores suffix 'n' divides by 1_000_000."""
        # 2_000_000n -> 2m
        assert _parse_cpu("2000000n") == 2
        # 500_000n -> 0m (integer truncation)
        assert _parse_cpu("500000n") == 0

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_microcores(self) -> None:
        """Microcores suffix 'u' divides by 1_000."""
        assert _parse_cpu("500u") == 0
        assert _parse_cpu("2000u") == 2

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_millicores(self) -> None:
        """Millicores suffix 'm' strips suffix and returns integer."""
        assert _parse_cpu("250m") == 250
        assert _parse_cpu("1000m") == 1000

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_full_cores(self) -> None:
        """Plain float cores are converted to millicores."""
        assert _parse_cpu("1") == 1000
        assert _parse_cpu("1.5") == 1500
        assert _parse_cpu("2") == 2000


# =============================================================================
# Tests: _parse_memory
# =============================================================================


class TestParseMemory:
    """Tests for the _parse_memory module-level helper."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_zero_string(self) -> None:
        """'0' should parse to 0 bytes."""
        assert _parse_memory("0") == 0

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_empty_string(self) -> None:
        """Empty string should parse to 0 bytes."""
        assert _parse_memory("") == 0

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_kibibytes(self) -> None:
        """'Ki' suffix uses 1024 as multiplier."""
        assert _parse_memory("4Ki") == 4 * 1024

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_mebibytes(self) -> None:
        """'Mi' suffix uses 1024**2 as multiplier."""
        assert _parse_memory("128Mi") == 128 * 1024**2

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_gibibytes(self) -> None:
        """'Gi' suffix uses 1024**3 as multiplier."""
        assert _parse_memory("1Gi") == 1024**3

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_tebibytes(self) -> None:
        """'Ti' suffix uses 1024**4 as multiplier."""
        assert _parse_memory("1Ti") == 1024**4

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_kilobytes(self) -> None:
        """'k' suffix uses 1000 as multiplier."""
        assert _parse_memory("4k") == 4000

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_megabytes(self) -> None:
        """'M' suffix uses 1_000_000 as multiplier."""
        assert _parse_memory("10M") == 10_000_000

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_gigabytes(self) -> None:
        """'G' suffix uses 1_000_000_000 as multiplier."""
        assert _parse_memory("2G") == 2_000_000_000

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_terabytes(self) -> None:
        """'T' suffix uses 1_000_000_000_000 as multiplier."""
        assert _parse_memory("1T") == 1_000_000_000_000

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_bare_bytes(self) -> None:
        """Plain integer string is treated as bytes."""
        assert _parse_memory("1024") == 1024


# =============================================================================
# Tests: _safe_nested_get
# =============================================================================


class TestSafeNestedGet:
    """Tests for the _safe_nested_get module-level helper."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_existing_nested_attrs(self) -> None:
        """Returns correct value when all attrs exist."""
        obj = MagicMock()
        obj.metadata.name = "hello"
        assert _safe_nested_get(obj, "metadata", "name") == "hello"

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_partial_path_returns_default(self) -> None:
        """Returns default when an intermediate attr is None."""
        obj = MagicMock()
        obj.metadata = None
        assert _safe_nested_get(obj, "metadata", "name", default="fallback") == "fallback"

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_none_root_object(self) -> None:
        """Returns default immediately when obj is None."""
        assert _safe_nested_get(None, "x", "y", default="d") == "d"

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_default_value_when_attr_missing(self) -> None:
        """Returns default when the final attr is absent."""
        obj = MagicMock(spec=[])  # no dynamic attributes
        result = _safe_nested_get(obj, "nonexistent", default=42)
        assert result == 42

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_single_attr(self) -> None:
        """Works correctly with a single attribute."""
        obj = MagicMock()
        obj.phase = "Running"
        assert _safe_nested_get(obj, "phase") == "Running"


# =============================================================================
# Tests: _get_replicas
# =============================================================================


class TestGetReplicas:
    """Tests for the _get_replicas module-level helper."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_deployment_uses_spec_replicas(self) -> None:
        """Deployment reads spec.replicas."""
        workload = MagicMock()
        workload.spec.replicas = 5
        assert _get_replicas(workload, "Deployment") == 5

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_statefulset_uses_spec_replicas(self) -> None:
        """StatefulSet reads spec.replicas."""
        workload = MagicMock()
        workload.spec.replicas = 3
        assert _get_replicas(workload, "StatefulSet") == 3

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_daemonset_uses_desired_number_scheduled(self) -> None:
        """DaemonSet reads status.desired_number_scheduled."""
        workload = MagicMock()
        workload.status.desired_number_scheduled = 7
        assert _get_replicas(workload, "DaemonSet") == 7

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_defaults_to_one_when_missing(self) -> None:
        """Returns 1 when the relevant attribute is None."""
        workload = MagicMock()
        workload.spec.replicas = None  # _safe_nested_get returns default=1
        # Simulate attribute present but None -> default=1 in _safe_nested_get
        result = _get_replicas(workload, "Deployment")
        assert result == 1

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_daemonset_defaults_to_one_when_missing(self) -> None:
        """DaemonSet returns 1 when desired_number_scheduled is None."""
        workload = MagicMock()
        workload.status.desired_number_scheduled = None
        result = _get_replicas(workload, "DaemonSet")
        assert result == 1


# =============================================================================
# Tests: _fetch_pod_metrics
# =============================================================================


class TestFetchPodMetrics:
    """Tests for OptimizationManager._fetch_pod_metrics."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_single_namespace_calls_correct_api(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Single-namespace mode uses list_namespaced_custom_object."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

        result = manager._fetch_pod_metrics(namespace="staging")

        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            group="metrics.k8s.io",
            version="v1beta1",
            namespace="staging",
            plural="pods",
        )
        assert result == {}

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_all_namespaces_calls_cluster_api(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """all_namespaces mode uses list_cluster_custom_object."""
        mock_k8s_client.custom_objects.list_cluster_custom_object.return_value = {"items": []}

        result = manager._fetch_pod_metrics(all_namespaces=True)

        mock_k8s_client.custom_objects.list_cluster_custom_object.assert_called_once_with(
            group="metrics.k8s.io",
            version="v1beta1",
            plural="pods",
        )
        assert result == {}

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_parses_container_usage_and_aggregates(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Aggregates CPU and memory across multiple containers per pod."""
        items = [
            {
                "metadata": {"name": "pod-1", "namespace": "default"},
                "containers": [
                    {"usage": {"cpu": "100m", "memory": "128Mi"}},
                    {"usage": {"cpu": "50m", "memory": "64Mi"}},
                ],
            }
        ]
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": items}

        result = manager._fetch_pod_metrics(namespace="default")

        key = "default/pod-1"
        assert key in result
        assert result[key].cpu_millicores == 150
        assert result[key].memory_bytes == (128 + 64) * 1024**2

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_empty_items_returns_empty_dict(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Empty items list produces an empty metrics dict."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

        result = manager._fetch_pod_metrics(namespace="default")

        assert result == {}

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_api_error_calls_handle_api_error(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """API exception is forwarded through _handle_api_error."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.side_effect = Exception(
            "metrics unavailable"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            manager._fetch_pod_metrics(namespace="default")

        mock_k8s_client.translate_api_exception.assert_called_once()


# =============================================================================
# Tests: _get_workload_pod_selector
# =============================================================================


class TestGetWorkloadPodSelector:
    """Tests for OptimizationManager._get_workload_pod_selector."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_with_match_labels_returns_selector_string(self, manager: OptimizationManager) -> None:
        """Returns 'key=value,...' string when match_labels are present."""
        workload = MagicMock()
        workload.spec.selector.match_labels = {"app": "nginx", "env": "prod"}
        result = manager._get_workload_pod_selector(workload)
        assert result is not None
        # Order-independent check
        parts = result.split(",")
        assert "app=nginx" in parts
        assert "env=prod" in parts

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_without_match_labels_returns_none(self, manager: OptimizationManager) -> None:
        """Returns None when match_labels are absent/falsy."""
        workload = MagicMock()
        workload.spec.selector.match_labels = {}
        assert manager._get_workload_pod_selector(workload) is None

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_none_selector_returns_none(self, manager: OptimizationManager) -> None:
        """Returns None when spec.selector.match_labels resolves to None."""
        workload = MagicMock()
        workload.spec.selector = None
        assert manager._get_workload_pod_selector(workload) is None


# =============================================================================
# Tests: _aggregate_resource_spec
# =============================================================================


class TestAggregateResourceSpec:
    """Tests for OptimizationManager._aggregate_resource_spec."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_single_container_resources(self, manager: OptimizationManager) -> None:
        """Parses resources from a single container correctly."""
        container = MagicMock()
        container.resources.requests = {"cpu": "250m", "memory": "128Mi"}
        container.resources.limits = {"cpu": "500m", "memory": "256Mi"}

        pod_template = MagicMock()
        pod_template.spec.containers = [container]

        spec = manager._aggregate_resource_spec(pod_template, replicas=1)

        assert spec.cpu_request_millicores == 250
        assert spec.cpu_limit_millicores == 500
        assert spec.memory_request_bytes == 128 * 1024**2
        assert spec.memory_limit_bytes == 256 * 1024**2

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_multiple_containers_sums_resources(self, manager: OptimizationManager) -> None:
        """Sums CPU and memory across all containers."""
        c1 = MagicMock()
        c1.resources.requests = {"cpu": "100m", "memory": "64Mi"}
        c1.resources.limits = {"cpu": "200m", "memory": "128Mi"}

        c2 = MagicMock()
        c2.resources.requests = {"cpu": "150m", "memory": "32Mi"}
        c2.resources.limits = {"cpu": "300m", "memory": "64Mi"}

        pod_template = MagicMock()
        pod_template.spec.containers = [c1, c2]

        spec = manager._aggregate_resource_spec(pod_template, replicas=1)

        assert spec.cpu_request_millicores == 250
        assert spec.cpu_limit_millicores == 500
        assert spec.memory_request_bytes == 96 * 1024**2
        assert spec.memory_limit_bytes == 192 * 1024**2

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_no_resources_attr_returns_zeros(self, manager: OptimizationManager) -> None:
        """Container with no resources attribute contributes zero."""
        container = MagicMock()
        container.resources = None

        pod_template = MagicMock()
        pod_template.spec.containers = [container]

        spec = manager._aggregate_resource_spec(pod_template, replicas=1)

        assert spec.cpu_request_millicores == 0
        assert spec.memory_request_bytes == 0

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_replicas_multiplier_applied(self, manager: OptimizationManager) -> None:
        """Resource totals are multiplied by the replica count."""
        container = MagicMock()
        container.resources.requests = {"cpu": "100m", "memory": "64Mi"}
        container.resources.limits = {"cpu": "200m", "memory": "128Mi"}

        pod_template = MagicMock()
        pod_template.spec.containers = [container]

        spec = manager._aggregate_resource_spec(pod_template, replicas=3)

        assert spec.cpu_request_millicores == 300
        assert spec.cpu_limit_millicores == 600
        assert spec.memory_request_bytes == 3 * 64 * 1024**2


# =============================================================================
# Tests: analyze_workloads
# =============================================================================


class TestAnalyzeWorkloads:
    """Tests for OptimizationManager.analyze_workloads."""

    def _setup_empty_lists(self, mock_k8s_client: MagicMock) -> None:
        """Configure mocks to return empty workload lists and no metrics."""
        empty_list = MagicMock()
        empty_list.items = []
        mock_k8s_client.apps_v1.list_namespaced_deployment.return_value = empty_list
        mock_k8s_client.apps_v1.list_namespaced_stateful_set.return_value = empty_list
        mock_k8s_client.apps_v1.list_namespaced_daemon_set.return_value = empty_list
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_returns_list_of_analyses(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Returns a list; empty when there are no workloads."""
        self._setup_empty_lists(mock_k8s_client)

        result = manager.analyze_workloads(namespace="default")

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_skips_workloads_with_no_name_or_namespace(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Workloads missing name or namespace are skipped."""
        nameless = MagicMock()
        nameless.metadata.name = None
        nameless.metadata.namespace = "default"

        deploy_list = MagicMock()
        deploy_list.items = [nameless]
        empty_list = MagicMock()
        empty_list.items = []

        mock_k8s_client.apps_v1.list_namespaced_deployment.return_value = deploy_list
        mock_k8s_client.apps_v1.list_namespaced_stateful_set.return_value = empty_list
        mock_k8s_client.apps_v1.list_namespaced_daemon_set.return_value = empty_list
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

        result = manager.analyze_workloads(namespace="default")

        assert len(result) == 0

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_processes_all_three_workload_types(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Deployments, StatefulSets, and DaemonSets are all queried."""
        deploy = _make_workload(name="my-deploy", namespace="default")
        ss = _make_workload(name="my-ss", namespace="default")
        ds = _make_workload(name="my-ds", namespace="default")
        ds.status.desired_number_scheduled = 3

        deploy_list = MagicMock()
        deploy_list.items = [deploy]
        ss_list = MagicMock()
        ss_list.items = [ss]
        ds_list = MagicMock()
        ds_list.items = [ds]

        mock_k8s_client.apps_v1.list_namespaced_deployment.return_value = deploy_list
        mock_k8s_client.apps_v1.list_namespaced_stateful_set.return_value = ss_list
        mock_k8s_client.apps_v1.list_namespaced_daemon_set.return_value = ds_list
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}
        # pod listing for _sum_pod_usage: return empty pods
        mock_k8s_client.core_v1.list_namespaced_pod.return_value = MagicMock(items=[])

        result = manager.analyze_workloads(namespace="default")

        assert len(result) == 3
        kinds = {a.workload_type for a in result}
        assert kinds == {"Deployment", "StatefulSet", "DaemonSet"}

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_passes_label_selector_to_list_calls(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """label_selector is forwarded to K8s API list calls."""
        empty_list = MagicMock()
        empty_list.items = []
        mock_k8s_client.apps_v1.list_namespaced_deployment.return_value = empty_list
        mock_k8s_client.apps_v1.list_namespaced_stateful_set.return_value = empty_list
        mock_k8s_client.apps_v1.list_namespaced_daemon_set.return_value = empty_list
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

        manager.analyze_workloads(namespace="default", label_selector="tier=backend")

        call_kwargs = mock_k8s_client.apps_v1.list_namespaced_deployment.call_args.kwargs
        assert call_kwargs.get("label_selector") == "tier=backend"

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_all_namespaces_uses_all_namespace_list_fns(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """all_namespaces mode calls the *_for_all_namespaces API variants."""
        empty_list = MagicMock()
        empty_list.items = []
        mock_k8s_client.apps_v1.list_deployment_for_all_namespaces.return_value = empty_list
        mock_k8s_client.apps_v1.list_stateful_set_for_all_namespaces.return_value = empty_list
        mock_k8s_client.apps_v1.list_daemon_set_for_all_namespaces.return_value = empty_list
        mock_k8s_client.custom_objects.list_cluster_custom_object.return_value = {"items": []}

        manager.analyze_workloads(all_namespaces=True)

        mock_k8s_client.apps_v1.list_deployment_for_all_namespaces.assert_called_once()
        mock_k8s_client.apps_v1.list_stateful_set_for_all_namespaces.assert_called_once()
        mock_k8s_client.apps_v1.list_daemon_set_for_all_namespaces.assert_called_once()


# =============================================================================
# Tests: recommend
# =============================================================================


class TestRecommend:
    """Tests for OptimizationManager.recommend."""

    def _configure_deployment(self, mock_k8s_client: MagicMock, workload: MagicMock) -> None:
        """Wire up mock client to serve a Deployment."""
        mock_k8s_client.apps_v1.read_namespaced_deployment.return_value = workload
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}
        mock_k8s_client.core_v1.list_namespaced_pod.return_value = MagicMock(items=[])

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_generates_recommendation_with_correct_values(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """RightsizingRecommendation is built with expected recommended values."""
        workload = _make_workload(
            name="api", namespace="default", replicas=1, cpu_request="500m", mem_request="512Mi"
        )
        self._configure_deployment(mock_k8s_client, workload)

        rec = manager.recommend("api", namespace="default", workload_type="Deployment")

        assert isinstance(rec, RightsizingRecommendation)
        assert rec.name == "api"
        assert rec.namespace == "default"
        assert rec.workload_type == "Deployment"
        # With zero actual usage, recommended CPU >= 1 and memory >= 1Mi
        assert rec.recommended_cpu_request_millicores >= 1
        assert rec.recommended_memory_request_bytes >= 1048576
        # CPU limit is 2x the request
        assert rec.recommended_cpu_limit_millicores == rec.recommended_cpu_request_millicores * 2

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_recommend_statefulset(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Fetches a StatefulSet when workload_type='StatefulSet'."""
        workload = _make_workload(name="db", namespace="default", replicas=3)
        mock_k8s_client.apps_v1.read_namespaced_stateful_set.return_value = workload
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}
        mock_k8s_client.core_v1.list_namespaced_pod.return_value = MagicMock(items=[])

        rec = manager.recommend("db", namespace="default", workload_type="StatefulSet")

        assert rec.workload_type == "StatefulSet"
        mock_k8s_client.apps_v1.read_namespaced_stateful_set.assert_called_once_with(
            "db", "default"
        )

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_recommend_daemonset(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Fetches a DaemonSet when workload_type='DaemonSet'."""
        workload = _make_workload(name="monitor", namespace="default")
        workload.status.desired_number_scheduled = 5
        mock_k8s_client.apps_v1.read_namespaced_daemon_set.return_value = workload
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}
        mock_k8s_client.core_v1.list_namespaced_pod.return_value = MagicMock(items=[])

        rec = manager.recommend("monitor", namespace="default", workload_type="DaemonSet")

        assert rec.workload_type == "DaemonSet"
        mock_k8s_client.apps_v1.read_namespaced_daemon_set.assert_called_once_with(
            "monitor", "default"
        )

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_unknown_workload_type_raises_value_error(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Unknown workload_type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown workload type"):
            manager.recommend("foo", namespace="default", workload_type="CronJob")


# =============================================================================
# Tests: find_unused
# =============================================================================


class TestFindUnused:
    """Tests for OptimizationManager.find_unused."""

    def _setup_empty_unused(self, mock_k8s_client: MagicMock) -> None:
        """Return empty state for all sub-queries."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}
        mock_k8s_client.core_v1.list_namespaced_pod.return_value = MagicMock(items=[])
        mock_k8s_client.batch_v1.list_namespaced_job.return_value = MagicMock(items=[])

        empty_list = MagicMock()
        empty_list.items = []
        mock_k8s_client.apps_v1.list_namespaced_deployment.return_value = empty_list
        mock_k8s_client.apps_v1.list_namespaced_stateful_set.return_value = empty_list
        mock_k8s_client.apps_v1.list_namespaced_daemon_set.return_value = empty_list

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_returns_dict_with_expected_keys(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Result dict has orphan_pods, stale_jobs, idle_workloads keys."""
        self._setup_empty_unused(mock_k8s_client)

        result = manager.find_unused(namespace="default")

        assert "orphan_pods" in result
        assert "stale_jobs" in result
        assert "idle_workloads" in result

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_returns_empty_lists_when_nothing_unused(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """All lists are empty when cluster is clean."""
        self._setup_empty_unused(mock_k8s_client)

        result = manager.find_unused(namespace="default")

        assert result["orphan_pods"] == []
        assert result["stale_jobs"] == []
        assert result["idle_workloads"] == []


# =============================================================================
# Tests: get_summary
# =============================================================================


class TestGetSummary:
    """Tests for OptimizationManager.get_summary."""

    def _setup_empty_cluster(self, mock_k8s_client: MagicMock) -> None:
        """Configure mocks so the cluster appears completely empty."""
        empty_list = MagicMock()
        empty_list.items = []
        for method in (
            "list_namespaced_deployment",
            "list_namespaced_stateful_set",
            "list_namespaced_daemon_set",
        ):
            getattr(mock_k8s_client.apps_v1, method).return_value = empty_list

        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}
        mock_k8s_client.core_v1.list_namespaced_pod.return_value = MagicMock(items=[])
        mock_k8s_client.batch_v1.list_namespaced_job.return_value = MagicMock(items=[])

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_returns_optimization_summary_instance(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Returns an OptimizationSummary object."""
        self._setup_empty_cluster(mock_k8s_client)

        result = manager.get_summary(namespace="default")

        assert isinstance(result, OptimizationSummary)

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_summary_counts_correct_for_empty_cluster(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """All counts are zero for an empty cluster."""
        self._setup_empty_cluster(mock_k8s_client)

        summary = manager.get_summary(namespace="default")

        assert summary.total_workloads_analyzed == 0
        assert summary.overprovisioned_count == 0
        assert summary.underutilized_count == 0
        assert summary.ok_count == 0
        assert summary.orphan_pod_count == 0
        assert summary.stale_job_count == 0
        assert summary.total_cpu_waste_millicores == 0
        assert summary.total_memory_waste_bytes == 0

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_summary_calculates_waste_from_overprovisioned(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """CPU and memory waste are derived from overprovisioned workloads."""
        workload = _make_workload(
            name="fat-deploy",
            namespace="default",
            replicas=1,
            cpu_request="1000m",
            mem_request="1Gi",
        )
        deploy_list = MagicMock()
        deploy_list.items = [workload]
        empty_list = MagicMock()
        empty_list.items = []

        mock_k8s_client.apps_v1.list_namespaced_deployment.return_value = deploy_list
        mock_k8s_client.apps_v1.list_namespaced_stateful_set.return_value = empty_list
        mock_k8s_client.apps_v1.list_namespaced_daemon_set.return_value = empty_list
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}
        # No matching pods -> usage=0, so workload is underutilized or overprovisioned
        mock_k8s_client.core_v1.list_namespaced_pod.return_value = MagicMock(items=[])
        mock_k8s_client.batch_v1.list_namespaced_job.return_value = MagicMock(items=[])

        summary = manager.get_summary(namespace="default")

        # Workload with zero usage and non-zero spec should be overprovisioned or underutilized
        assert summary.total_workloads_analyzed == 1
        # waste should be non-negative
        assert summary.total_cpu_waste_millicores >= 0
        assert summary.total_memory_waste_bytes >= 0


# =============================================================================
# Tests: _sum_pod_usage
# =============================================================================


class TestSumPodUsage:
    """Tests for OptimizationManager._sum_pod_usage."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_no_selector_returns_empty_metrics(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """None selector immediately returns zero ResourceMetrics."""
        pod_metrics = {"default/pod-1": ResourceMetrics(cpu_millicores=100, memory_bytes=1024)}

        result = manager._sum_pod_usage(pod_metrics, "default", label_selector=None)

        assert result.cpu_millicores == 0
        assert result.memory_bytes == 0

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_sums_matching_pod_metrics(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Metrics for pods matching the selector are summed."""
        pod1 = MagicMock()
        pod1.metadata.name = "pod-a"
        pod2 = MagicMock()
        pod2.metadata.name = "pod-b"

        mock_k8s_client.core_v1.list_namespaced_pod.return_value = MagicMock(items=[pod1, pod2])

        pod_metrics = {
            "default/pod-a": ResourceMetrics(cpu_millicores=50, memory_bytes=512),
            "default/pod-b": ResourceMetrics(cpu_millicores=75, memory_bytes=256),
            "default/pod-c": ResourceMetrics(cpu_millicores=200, memory_bytes=999),
        }

        result = manager._sum_pod_usage(pod_metrics, "default", label_selector="app=test")

        assert result.cpu_millicores == 125
        assert result.memory_bytes == 768

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_exception_in_pod_listing_returns_empty(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Pod listing exceptions are silently swallowed; returns empty metrics."""
        mock_k8s_client.core_v1.list_namespaced_pod.side_effect = Exception("permission denied")

        pod_metrics = {"default/pod-a": ResourceMetrics(cpu_millicores=50, memory_bytes=512)}

        result = manager._sum_pod_usage(pod_metrics, "default", label_selector="app=x")

        assert result.cpu_millicores == 0
        assert result.memory_bytes == 0


# =============================================================================
# Tests: _get_workload
# =============================================================================


class TestGetWorkload:
    """Tests for OptimizationManager._get_workload."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_fetches_deployment(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Calls read_namespaced_deployment for Deployment kind."""
        workload = MagicMock()
        mock_k8s_client.apps_v1.read_namespaced_deployment.return_value = workload

        result = manager._get_workload("my-deploy", "default", "Deployment")

        assert result is workload
        mock_k8s_client.apps_v1.read_namespaced_deployment.assert_called_once_with(
            "my-deploy", "default"
        )

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_fetches_statefulset(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Calls read_namespaced_stateful_set for StatefulSet kind."""
        workload = MagicMock()
        mock_k8s_client.apps_v1.read_namespaced_stateful_set.return_value = workload

        result = manager._get_workload("my-ss", "default", "StatefulSet")

        assert result is workload
        mock_k8s_client.apps_v1.read_namespaced_stateful_set.assert_called_once_with(
            "my-ss", "default"
        )

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_fetches_daemonset(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Calls read_namespaced_daemon_set for DaemonSet kind."""
        workload = MagicMock()
        mock_k8s_client.apps_v1.read_namespaced_daemon_set.return_value = workload

        result = manager._get_workload("my-ds", "default", "DaemonSet")

        assert result is workload
        mock_k8s_client.apps_v1.read_namespaced_daemon_set.assert_called_once_with(
            "my-ds", "default"
        )

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_unknown_kind_raises_value_error(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Unknown kind raises ValueError without calling _handle_api_error."""
        with pytest.raises(ValueError, match="Unknown workload type"):
            manager._get_workload("x", "default", "CronJob")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_api_error_calls_handle_api_error(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Non-ValueError API exceptions are routed through _handle_api_error."""
        mock_k8s_client.apps_v1.read_namespaced_deployment.side_effect = Exception("not found")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            manager._get_workload("x", "default", "Deployment")

        mock_k8s_client.translate_api_exception.assert_called_once()


# =============================================================================
# Tests: _find_orphan_pods
# =============================================================================


class TestFindOrphanPods:
    """Tests for OptimizationManager._find_orphan_pods."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_pods_without_owner_refs_are_orphans(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Pods with no owner_references are identified as orphans."""
        orphan = MagicMock()
        orphan.metadata.name = "lone-pod"
        orphan.metadata.namespace = "default"
        # owner_references=None -> _safe_nested_get returns None -> `or []` -> empty list
        orphan.metadata.owner_references = None
        # Fields consumed by OrphanPod.from_k8s_object must be proper types or None
        orphan.metadata.uid = "uid-orphan"
        orphan.metadata.creation_timestamp = None
        orphan.metadata.labels = None
        orphan.status.phase = "Running"
        orphan.spec.node_name = "node-1"

        mock_k8s_client.core_v1.list_namespaced_pod.return_value = MagicMock(items=[orphan])

        result = manager._find_orphan_pods("default", False, {})

        assert len(result) == 1
        assert isinstance(result[0], OrphanPod)

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_pods_with_owner_refs_are_not_orphans(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Pods with non-empty owner_references are not orphans."""
        owner = MagicMock()
        owner.kind = "ReplicaSet"

        managed_pod = MagicMock()
        managed_pod.metadata.name = "managed-pod"
        managed_pod.metadata.namespace = "default"
        managed_pod.metadata.owner_references = [owner]

        mock_k8s_client.core_v1.list_namespaced_pod.return_value = MagicMock(items=[managed_pod])

        result = manager._find_orphan_pods("default", False, {})

        assert len(result) == 0

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_all_namespaces_calls_list_pod_for_all_namespaces(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """all_namespaces=True uses the cross-namespace pod list API."""
        mock_k8s_client.core_v1.list_pod_for_all_namespaces.return_value = MagicMock(items=[])

        result = manager._find_orphan_pods("default", True, {})

        mock_k8s_client.core_v1.list_pod_for_all_namespaces.assert_called_once()
        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_api_error_calls_handle_api_error(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Pod listing exceptions are forwarded to _handle_api_error."""
        mock_k8s_client.core_v1.list_namespaced_pod.side_effect = Exception("connection timeout")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            manager._find_orphan_pods("default", False, {})


# =============================================================================
# Tests: _find_stale_jobs
# =============================================================================


class TestFindStaleJobs:
    """Tests for OptimizationManager._find_stale_jobs."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_completed_job_older_than_threshold_is_stale(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """A completed job with completion_time older than stale_job_hours is stale."""
        old_time = datetime.now(UTC) - timedelta(hours=48)

        job = MagicMock()
        job.metadata.name = "old-job"
        job.metadata.namespace = "default"
        job.metadata.uid = "uid-1"
        job.metadata.creation_timestamp = None
        job.metadata.labels = None
        job.status.completion_time = old_time
        job.status.conditions = []

        mock_k8s_client.batch_v1.list_namespaced_job.return_value = MagicMock(items=[job])

        result = manager._find_stale_jobs("default", False, stale_job_hours=24)

        assert len(result) == 1
        assert isinstance(result[0], StaleJob)

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_failed_job_with_condition_is_stale(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """A failed job (no completion_time but has Failed condition) is stale when old enough."""
        old_time = datetime.now(UTC) - timedelta(hours=30)

        failed_cond = MagicMock()
        failed_cond.type = "Failed"
        failed_cond.status = "True"
        failed_cond.last_transition_time = old_time

        job = MagicMock()
        job.metadata.name = "failed-job"
        job.metadata.namespace = "default"
        job.metadata.uid = "uid-2"
        job.metadata.creation_timestamp = None
        job.metadata.labels = None
        job.status.completion_time = None
        job.status.conditions = [failed_cond]

        mock_k8s_client.batch_v1.list_namespaced_job.return_value = MagicMock(items=[job])

        result = manager._find_stale_jobs("default", False, stale_job_hours=24)

        assert len(result) == 1

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_recent_completed_job_not_stale(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """A job completed less than stale_job_hours ago is not stale."""
        recent_time = datetime.now(UTC) - timedelta(hours=1)

        job = MagicMock()
        job.metadata.name = "recent-job"
        job.metadata.namespace = "default"
        job.metadata.uid = "uid-3"
        job.metadata.creation_timestamp = None
        job.metadata.labels = None
        job.status.completion_time = recent_time
        job.status.conditions = []

        mock_k8s_client.batch_v1.list_namespaced_job.return_value = MagicMock(items=[job])

        result = manager._find_stale_jobs("default", False, stale_job_hours=24)

        assert len(result) == 0

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_running_job_is_skipped(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """A running job (no completion_time, no Failed condition) is not stale."""
        job = MagicMock()
        job.metadata.name = "running-job"
        job.metadata.namespace = "default"
        job.metadata.uid = "uid-4"
        job.metadata.creation_timestamp = None
        job.metadata.labels = None
        job.status.completion_time = None
        job.status.conditions = []

        mock_k8s_client.batch_v1.list_namespaced_job.return_value = MagicMock(items=[job])

        result = manager._find_stale_jobs("default", False, stale_job_hours=24)

        assert len(result) == 0

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_string_timestamp_is_parsed(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """ISO string timestamps for completion_time are parsed correctly."""
        old_time = datetime.now(UTC) - timedelta(hours=48)
        time_str = old_time.strftime("%Y-%m-%dT%H:%M:%S") + "Z"

        job = MagicMock()
        job.metadata.name = "string-ts-job"
        job.metadata.namespace = "default"
        job.metadata.uid = "uid-5"
        job.metadata.creation_timestamp = None
        job.metadata.labels = None
        job.status.completion_time = time_str
        job.status.conditions = []

        mock_k8s_client.batch_v1.list_namespaced_job.return_value = MagicMock(items=[job])

        result = manager._find_stale_jobs("default", False, stale_job_hours=24)

        assert len(result) == 1

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_all_namespaces_uses_cluster_list_api(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """all_namespaces=True uses list_job_for_all_namespaces."""
        mock_k8s_client.batch_v1.list_job_for_all_namespaces.return_value = MagicMock(items=[])

        result = manager._find_stale_jobs("default", True, stale_job_hours=24)

        mock_k8s_client.batch_v1.list_job_for_all_namespaces.assert_called_once()
        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_api_error_calls_handle_api_error(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Job listing exceptions are forwarded to _handle_api_error."""
        mock_k8s_client.batch_v1.list_namespaced_job.side_effect = Exception("connection refused")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            manager._find_stale_jobs("default", False, stale_job_hours=24)

        mock_k8s_client.translate_api_exception.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_failed_job_with_no_last_transition_time_is_skipped(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Failed job whose condition has no last_transition_time is skipped (ref_time=None)."""
        failed_cond = MagicMock()
        failed_cond.type = "Failed"
        failed_cond.status = "True"
        # getattr(cond, "last_transition_time", None) returns None
        failed_cond.last_transition_time = None

        job = MagicMock()
        job.metadata.name = "no-ts-job"
        job.metadata.namespace = "default"
        job.metadata.uid = "uid-notime"
        job.metadata.creation_timestamp = None
        job.metadata.labels = None
        job.status.completion_time = None
        job.status.conditions = [failed_cond]

        mock_k8s_client.batch_v1.list_namespaced_job.return_value = MagicMock(items=[job])

        result = manager._find_stale_jobs("default", False, stale_job_hours=24)

        # ref_time ends up None -> job is skipped
        assert len(result) == 0


# =============================================================================
# Tests: _find_idle_workloads
# =============================================================================


class TestFindIdleWorkloads:
    """Tests for OptimizationManager._find_idle_workloads."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_returns_workloads_with_negligible_usage(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Workloads with usage at or below thresholds and non-zero spec are idle."""
        # A workload with 1000m request but zero actual usage -> idle
        workload = _make_workload(
            name="idle-deploy",
            namespace="default",
            replicas=1,
            cpu_request="1000m",
            mem_request="512Mi",
        )
        deploy_list = MagicMock()
        deploy_list.items = [workload]
        empty_list = MagicMock()
        empty_list.items = []

        mock_k8s_client.apps_v1.list_namespaced_deployment.return_value = deploy_list
        mock_k8s_client.apps_v1.list_namespaced_stateful_set.return_value = empty_list
        mock_k8s_client.apps_v1.list_namespaced_daemon_set.return_value = empty_list
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}
        # No matching pods -> zero usage
        mock_k8s_client.core_v1.list_namespaced_pod.return_value = MagicMock(items=[])

        pod_metrics: dict[str, ResourceMetrics] = {}
        result = manager._find_idle_workloads(
            "default",
            False,
            pod_metrics,
            idle_cpu=IDLE_CPU_MILLICORES,
            idle_memory=IDLE_MEMORY_BYTES,
        )

        # The workload has zero usage <= thresholds and non-zero spec -> idle
        assert len(result) >= 1
        assert all(isinstance(a, WorkloadResourceAnalysis) for a in result)


# =============================================================================
# Tests: _analyze_single_workload
# =============================================================================


class TestAnalyzeSingleWorkload:
    """Tests for OptimizationManager._analyze_single_workload."""

    def _replica_fn(self, w: MagicMock) -> int:
        return _get_replicas(w, "Deployment")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_overprovisioned_status(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Status is 'overprovisioned' when usage is low but above idle thresholds."""
        workload = _make_workload(
            name="deploy",
            namespace="default",
            replicas=1,
            cpu_request="1000m",
            mem_request="1Gi",
        )
        # usage: 50m CPU, 128Mi memory -> below 20% threshold, above idle thresholds
        pod_metrics = {
            "default/pod-x": ResourceMetrics(cpu_millicores=50, memory_bytes=128 * 1024**2)
        }

        mock_pod = MagicMock()
        mock_pod.metadata.name = "pod-x"
        mock_k8s_client.core_v1.list_namespaced_pod.return_value = MagicMock(items=[mock_pod])

        analysis = manager._analyze_single_workload(
            workload, "Deployment", pod_metrics, self._replica_fn, threshold=0.20
        )

        assert analysis is not None
        assert analysis.status == "overprovisioned"
        assert analysis.name == "deploy"
        assert analysis.namespace == "default"

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_underutilized_status(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Status is 'underutilized' when usage is at or below idle thresholds."""
        workload = _make_workload(
            name="idle-deploy",
            namespace="default",
            replicas=1,
            cpu_request="500m",
            mem_request="256Mi",
        )
        # usage: 0 CPU, 0 memory -> at idle thresholds
        pod_metrics: dict[str, ResourceMetrics] = {}
        mock_k8s_client.core_v1.list_namespaced_pod.return_value = MagicMock(items=[])

        analysis = manager._analyze_single_workload(
            workload, "Deployment", pod_metrics, self._replica_fn, threshold=0.20
        )

        assert analysis is not None
        assert analysis.status == "underutilized"

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_ok_status(self, manager: OptimizationManager, mock_k8s_client: MagicMock) -> None:
        """Status is 'ok' when usage meets or exceeds the threshold ratio."""
        workload = _make_workload(
            name="busy-deploy",
            namespace="default",
            replicas=1,
            cpu_request="100m",
            mem_request="64Mi",
        )
        # usage: 90m CPU, 60Mi memory -> 90% CPU util, above threshold
        pod_metrics = {
            "default/pod-y": ResourceMetrics(cpu_millicores=90, memory_bytes=60 * 1024**2)
        }

        mock_pod = MagicMock()
        mock_pod.metadata.name = "pod-y"
        mock_k8s_client.core_v1.list_namespaced_pod.return_value = MagicMock(items=[mock_pod])

        analysis = manager._analyze_single_workload(
            workload, "Deployment", pod_metrics, self._replica_fn, threshold=0.20
        )

        assert analysis is not None
        assert analysis.status == "ok"

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_missing_name_returns_none(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Returns None when workload has no name."""
        workload = MagicMock()
        workload.metadata.name = None
        workload.metadata.namespace = "default"

        result = manager._analyze_single_workload(
            workload, "Deployment", {}, self._replica_fn, threshold=0.20
        )

        assert result is None

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_missing_namespace_returns_none(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Returns None when workload has no namespace."""
        workload = MagicMock()
        workload.metadata.name = "some-deploy"
        workload.metadata.namespace = None

        result = manager._analyze_single_workload(
            workload, "Deployment", {}, self._replica_fn, threshold=0.20
        )

        assert result is None

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_datetime_creation_timestamp_is_iso_string(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """datetime creation_timestamp is serialized to ISO string."""
        ts = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)
        workload = _make_workload(
            name="ts-deploy",
            namespace="default",
            replicas=1,
            creation_timestamp=ts,
        )
        mock_k8s_client.core_v1.list_namespaced_pod.return_value = MagicMock(items=[])

        analysis = manager._analyze_single_workload(
            workload, "Deployment", {}, self._replica_fn, threshold=0.20
        )

        assert analysis is not None
        assert analysis.creation_timestamp == ts.isoformat()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_string_creation_timestamp_is_passed_through(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """String creation_timestamp is passed through unchanged."""
        ts_str = "2025-06-01T10:00:00+00:00"
        workload = _make_workload(
            name="str-ts-deploy",
            namespace="default",
            replicas=1,
            creation_timestamp=ts_str,
        )
        mock_k8s_client.core_v1.list_namespaced_pod.return_value = MagicMock(items=[])

        analysis = manager._analyze_single_workload(
            workload, "Deployment", {}, self._replica_fn, threshold=0.20
        )

        assert analysis is not None
        assert analysis.creation_timestamp == ts_str

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_other_creation_timestamp_type_uses_str(
        self, manager: OptimizationManager, mock_k8s_client: MagicMock
    ) -> None:
        """Non-datetime, non-string creation_timestamp is cast via str()."""
        workload = _make_workload(
            name="int-ts-deploy",
            namespace="default",
            replicas=1,
            creation_timestamp="12345",  # non-datetime string exercises the str() branch
        )
        mock_k8s_client.core_v1.list_namespaced_pod.return_value = MagicMock(items=[])

        analysis = manager._analyze_single_workload(
            workload, "Deployment", {}, self._replica_fn, threshold=0.20
        )

        assert analysis is not None
        assert analysis.creation_timestamp == "12345"
