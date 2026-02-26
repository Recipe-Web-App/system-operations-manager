"""Unit tests for Kubernetes resource optimization display models."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kubernetes.models.optimization import (
    OptimizationSummary,
    OrphanPod,
    ResourceMetrics,
    ResourceSpec,
    RightsizingRecommendation,
    StaleJob,
    WorkloadResourceAnalysis,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestResourceMetrics:
    """Test ResourceMetrics model."""

    def test_defaults(self) -> None:
        """Test ResourceMetrics with default values."""
        m = ResourceMetrics()
        assert m.cpu_millicores == 0
        assert m.memory_bytes == 0

    def test_cpu_display_millicores(self) -> None:
        """Test cpu_display returns 'm' suffix for values under 1000."""
        m = ResourceMetrics(cpu_millicores=500, memory_bytes=0)
        assert m.cpu_display == "500m"

    def test_cpu_display_millicores_zero(self) -> None:
        """Test cpu_display returns '0m' for zero millicores."""
        m = ResourceMetrics(cpu_millicores=0, memory_bytes=0)
        assert m.cpu_display == "0m"

    def test_cpu_display_cores_exactly_1000(self) -> None:
        """Test cpu_display returns cores format when cpu_millicores equals 1000."""
        m = ResourceMetrics(cpu_millicores=1000, memory_bytes=0)
        assert m.cpu_display == "1.0"

    def test_cpu_display_cores_above_1000(self) -> None:
        """Test cpu_display returns cores format when cpu_millicores exceeds 1000."""
        m = ResourceMetrics(cpu_millicores=1500, memory_bytes=0)
        assert m.cpu_display == "1.5"

    def test_cpu_display_cores_large(self) -> None:
        """Test cpu_display with a large core value."""
        m = ResourceMetrics(cpu_millicores=8000, memory_bytes=0)
        assert m.cpu_display == "8.0"

    def test_memory_display_bytes(self) -> None:
        """Test memory_display returns raw bytes when under 1 KiB."""
        m = ResourceMetrics(cpu_millicores=0, memory_bytes=512)
        assert m.memory_display == "512B"

    def test_memory_display_zero_bytes(self) -> None:
        """Test memory_display returns '0B' for zero bytes."""
        m = ResourceMetrics(cpu_millicores=0, memory_bytes=0)
        assert m.memory_display == "0B"

    def test_memory_display_kibibytes(self) -> None:
        """Test memory_display returns KiB suffix for values in [1024, 1024*1024)."""
        m = ResourceMetrics(cpu_millicores=0, memory_bytes=2048)
        assert m.memory_display == "2Ki"

    def test_memory_display_kibibytes_exactly_1024(self) -> None:
        """Test memory_display returns KiB suffix at exactly 1024 bytes."""
        m = ResourceMetrics(cpu_millicores=0, memory_bytes=1024)
        assert m.memory_display == "1Ki"

    def test_memory_display_mebibytes(self) -> None:
        """Test memory_display returns MiB suffix for values in [1 MiB, 1 GiB)."""
        m = ResourceMetrics(cpu_millicores=0, memory_bytes=1024 * 1024 * 128)
        assert m.memory_display == "128Mi"

    def test_memory_display_mebibytes_exactly_1_mib(self) -> None:
        """Test memory_display returns MiB suffix at exactly 1 MiB."""
        m = ResourceMetrics(cpu_millicores=0, memory_bytes=1024 * 1024)
        assert m.memory_display == "1Mi"

    def test_memory_display_gibibytes(self) -> None:
        """Test memory_display returns GiB suffix for values >= 1 GiB."""
        m = ResourceMetrics(cpu_millicores=0, memory_bytes=1024 * 1024 * 1024 * 2)
        assert m.memory_display == "2.0Gi"

    def test_memory_display_gibibytes_exactly_1_gib(self) -> None:
        """Test memory_display returns GiB suffix at exactly 1 GiB."""
        m = ResourceMetrics(cpu_millicores=0, memory_bytes=1024 * 1024 * 1024)
        assert m.memory_display == "1.0Gi"

    def test_memory_display_fractional_gib(self) -> None:
        """Test memory_display rounds GiB correctly for non-round values."""
        m = ResourceMetrics(cpu_millicores=0, memory_bytes=int(1.5 * 1024 * 1024 * 1024))
        assert m.memory_display == "1.5Gi"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestResourceSpec:
    """Test ResourceSpec model."""

    def test_defaults(self) -> None:
        """Test ResourceSpec with default values."""
        s = ResourceSpec()
        assert s.cpu_request_millicores == 0
        assert s.cpu_limit_millicores == 0
        assert s.memory_request_bytes == 0
        assert s.memory_limit_bytes == 0

    def test_explicit_values(self) -> None:
        """Test ResourceSpec with explicit values."""
        s = ResourceSpec(
            cpu_request_millicores=250,
            cpu_limit_millicores=500,
            memory_request_bytes=128 * 1024 * 1024,
            memory_limit_bytes=256 * 1024 * 1024,
        )
        assert s.cpu_request_millicores == 250
        assert s.cpu_limit_millicores == 500
        assert s.memory_request_bytes == 128 * 1024 * 1024
        assert s.memory_limit_bytes == 256 * 1024 * 1024


@pytest.mark.unit
@pytest.mark.kubernetes
class TestWorkloadResourceAnalysis:
    """Test WorkloadResourceAnalysis model."""

    def _make_analysis(
        self,
        cpu_millicores: int = 200,
        memory_bytes: int = 64 * 1024 * 1024,
        cpu_request_millicores: int = 500,
        memory_request_bytes: int = 128 * 1024 * 1024,
    ) -> WorkloadResourceAnalysis:
        return WorkloadResourceAnalysis(
            name="web-app",
            workload_type="Deployment",
            total_usage=ResourceMetrics(
                cpu_millicores=cpu_millicores,
                memory_bytes=memory_bytes,
            ),
            total_spec=ResourceSpec(
                cpu_request_millicores=cpu_request_millicores,
                memory_request_bytes=memory_request_bytes,
            ),
        )

    def test_defaults(self) -> None:
        """Test WorkloadResourceAnalysis default field values."""
        a = WorkloadResourceAnalysis(name="app", workload_type="Deployment")
        assert a.replicas == 1
        assert a.cpu_utilization_pct == 0.0
        assert a.memory_utilization_pct == 0.0
        assert a.status == "ok"

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert WorkloadResourceAnalysis._entity_name == "workload_analysis"

    def test_cpu_usage_display_millicores(self) -> None:
        """Test cpu_usage_display formats correctly with millicores usage."""
        a = self._make_analysis(cpu_millicores=200, cpu_request_millicores=500)
        assert a.cpu_usage_display == "200m/500m"

    def test_cpu_usage_display_cores(self) -> None:
        """Test cpu_usage_display formats correctly when usage exceeds 1000m."""
        a = self._make_analysis(cpu_millicores=1500, cpu_request_millicores=2000)
        assert a.cpu_usage_display == "1.5/2000m"

    def test_cpu_usage_display_zero_request(self) -> None:
        """Test cpu_usage_display when request is zero."""
        a = self._make_analysis(cpu_millicores=0, cpu_request_millicores=0)
        assert a.cpu_usage_display == "0m/0m"

    def test_memory_usage_display(self) -> None:
        """Test memory_usage_display formats usage and request correctly."""
        a = self._make_analysis(
            memory_bytes=64 * 1024 * 1024,
            memory_request_bytes=128 * 1024 * 1024,
        )
        assert a.memory_usage_display == "64Mi/128Mi"

    def test_memory_usage_display_gib_usage(self) -> None:
        """Test memory_usage_display with GiB-scale usage."""
        a = self._make_analysis(
            memory_bytes=2 * 1024 * 1024 * 1024,
            memory_request_bytes=4 * 1024 * 1024 * 1024,
        )
        assert a.memory_usage_display == "2.0Gi/4096Mi"

    def test_memory_usage_display_zero_request(self) -> None:
        """Test memory_usage_display when request is zero bytes."""
        a = self._make_analysis(memory_bytes=0, memory_request_bytes=0)
        assert a.memory_usage_display == "0B/0Mi"

    def test_status_overprovisioned(self) -> None:
        """Test WorkloadResourceAnalysis with overprovisioned status."""
        a = WorkloadResourceAnalysis(
            name="overprovisioned-app",
            workload_type="Deployment",
            status="overprovisioned",
        )
        assert a.status == "overprovisioned"

    def test_status_underutilized(self) -> None:
        """Test WorkloadResourceAnalysis with underutilized status."""
        a = WorkloadResourceAnalysis(
            name="underutilized-app",
            workload_type="StatefulSet",
            status="underutilized",
        )
        assert a.status == "underutilized"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestRightsizingRecommendation:
    """Test RightsizingRecommendation model."""

    def _make_recommendation(self) -> RightsizingRecommendation:
        return RightsizingRecommendation(
            name="web-app",
            workload_type="Deployment",
            current_spec=ResourceSpec(
                cpu_request_millicores=1000,
                cpu_limit_millicores=2000,
                memory_request_bytes=512 * 1024 * 1024,
                memory_limit_bytes=1024 * 1024 * 1024,
            ),
            current_usage=ResourceMetrics(
                cpu_millicores=200,
                memory_bytes=128 * 1024 * 1024,
            ),
            recommended_cpu_request_millicores=250,
            recommended_memory_request_bytes=160 * 1024 * 1024,
            recommended_cpu_limit_millicores=500,
            recommended_memory_limit_bytes=320 * 1024 * 1024,
            cpu_savings_millicores=750,
            memory_savings_bytes=352 * 1024 * 1024,
        )

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert RightsizingRecommendation._entity_name == "recommendation"

    def test_fields(self) -> None:
        """Test RightsizingRecommendation fields are stored correctly."""
        rec = self._make_recommendation()
        assert rec.name == "web-app"
        assert rec.workload_type == "Deployment"
        assert rec.recommended_cpu_request_millicores == 250
        assert rec.recommended_memory_request_bytes == 160 * 1024 * 1024
        assert rec.recommended_cpu_limit_millicores == 500
        assert rec.recommended_memory_limit_bytes == 320 * 1024 * 1024
        assert rec.cpu_savings_millicores == 750
        assert rec.memory_savings_bytes == 352 * 1024 * 1024

    def test_default_savings(self) -> None:
        """Test RightsizingRecommendation default savings values."""
        rec = RightsizingRecommendation(
            name="app",
            workload_type="DaemonSet",
            current_spec=ResourceSpec(),
            current_usage=ResourceMetrics(),
            recommended_cpu_request_millicores=100,
            recommended_memory_request_bytes=64 * 1024 * 1024,
            recommended_cpu_limit_millicores=200,
            recommended_memory_limit_bytes=128 * 1024 * 1024,
        )
        assert rec.cpu_savings_millicores == 0
        assert rec.memory_savings_bytes == 0


@pytest.mark.unit
@pytest.mark.kubernetes
class TestOrphanPod:
    """Test OrphanPod model."""

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert OrphanPod._entity_name == "orphan_pod"

    def test_from_k8s_object_with_metrics(self) -> None:
        """Test from_k8s_object populates fields including metrics."""
        obj = MagicMock()
        obj.metadata.name = "orphan-pod-abc"
        obj.metadata.namespace = "default"
        obj.metadata.uid = "uid-orphan-1"
        obj.metadata.creation_timestamp = "2024-01-01T00:00:00Z"
        obj.metadata.labels = {"app": "orphan"}
        obj.status.phase = "Running"
        obj.spec.node_name = "node-1"

        metrics = ResourceMetrics(cpu_millicores=150, memory_bytes=32 * 1024 * 1024)

        pod = OrphanPod.from_k8s_object(obj, metrics=metrics)

        assert pod.name == "orphan-pod-abc"
        assert pod.namespace == "default"
        assert pod.uid == "uid-orphan-1"
        assert pod.phase == "Running"
        assert pod.node_name == "node-1"
        assert pod.cpu_usage == "150m"
        assert pod.memory_usage == "32Mi"

    def test_from_k8s_object_without_metrics(self) -> None:
        """Test from_k8s_object without metrics uses dash placeholders."""
        obj = MagicMock()
        obj.metadata.name = "orphan-pod-xyz"
        obj.metadata.namespace = "kube-system"
        obj.metadata.uid = "uid-orphan-2"
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.status.phase = "Pending"
        obj.spec.node_name = None

        pod = OrphanPod.from_k8s_object(obj, metrics=None)

        assert pod.cpu_usage == "-"
        assert pod.memory_usage == "-"

    def test_from_k8s_object_minimal(self) -> None:
        """Test from_k8s_object with minimal pod data."""
        obj = MagicMock()
        obj.metadata.name = "minimal-orphan"
        obj.metadata.namespace = None
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.status.phase = None
        obj.spec.node_name = None

        pod = OrphanPod.from_k8s_object(obj)

        assert pod.name == "minimal-orphan"
        assert pod.phase == "Unknown"
        assert pod.node_name is None
        assert pod.cpu_usage == "-"
        assert pod.memory_usage == "-"

    def test_from_k8s_object_metrics_cpu_cores(self) -> None:
        """Test from_k8s_object with metrics showing CPU usage in cores format."""
        obj = MagicMock()
        obj.metadata.name = "heavy-pod"
        obj.metadata.namespace = "production"
        obj.metadata.uid = "uid-heavy"
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.status.phase = "Running"
        obj.spec.node_name = "node-heavy"

        metrics = ResourceMetrics(cpu_millicores=2500, memory_bytes=2 * 1024 * 1024 * 1024)

        pod = OrphanPod.from_k8s_object(obj, metrics=metrics)

        assert pod.cpu_usage == "2.5"
        assert pod.memory_usage == "2.0Gi"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestStaleJob:
    """Test StaleJob model."""

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert StaleJob._entity_name == "stale_job"

    def test_from_k8s_object_complete_status(self) -> None:
        """Test from_k8s_object identifies a Complete job condition."""
        obj = MagicMock()
        obj.metadata.name = "done-job"
        obj.metadata.namespace = "default"
        obj.metadata.uid = "uid-done-1"
        obj.metadata.creation_timestamp = "2024-01-01T00:00:00Z"
        obj.metadata.labels = {"app": "batch"}

        cond = MagicMock()
        cond.type = "Complete"
        cond.status = "True"
        obj.status.conditions = [cond]
        obj.status.completion_time = "2024-01-01T01:00:00Z"

        job = StaleJob.from_k8s_object(obj, age_hours=2.5)

        assert job.name == "done-job"
        assert job.namespace == "default"
        assert job.status == "Complete"
        assert job.age_hours == 2.5

    def test_from_k8s_object_failed_status(self) -> None:
        """Test from_k8s_object identifies a Failed job condition."""
        obj = MagicMock()
        obj.metadata.name = "failed-job"
        obj.metadata.namespace = "default"
        obj.metadata.uid = "uid-failed-1"
        obj.metadata.creation_timestamp = "2024-01-01T00:00:00Z"
        obj.metadata.labels = None

        cond = MagicMock()
        cond.type = "Failed"
        cond.status = "True"
        obj.status.conditions = [cond]
        obj.status.completion_time = None

        job = StaleJob.from_k8s_object(obj, age_hours=10.0)

        assert job.status == "Failed"
        assert job.age_hours == 10.0

    def test_from_k8s_object_failed_condition_not_true(self) -> None:
        """Test from_k8s_object does not set Failed when condition status is not True."""
        obj = MagicMock()
        obj.metadata.name = "running-job"
        obj.metadata.namespace = "default"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None

        cond = MagicMock()
        cond.type = "Failed"
        cond.status = "False"
        obj.status.conditions = [cond]
        obj.status.completion_time = None

        job = StaleJob.from_k8s_object(obj, age_hours=0.0)

        assert job.status == "Unknown"

    def test_from_k8s_object_no_conditions(self) -> None:
        """Test from_k8s_object with no conditions returns Unknown status."""
        obj = MagicMock()
        obj.metadata.name = "no-cond-job"
        obj.metadata.namespace = "default"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.status.conditions = []
        obj.status.completion_time = None

        job = StaleJob.from_k8s_object(obj)

        assert job.status == "Unknown"
        assert job.age_hours == 0.0

    def test_from_k8s_object_none_conditions(self) -> None:
        """Test from_k8s_object with None conditions returns Unknown status."""
        obj = MagicMock()
        obj.metadata.name = "none-cond-job"
        obj.metadata.namespace = "default"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.status.conditions = None
        obj.status.completion_time = None

        job = StaleJob.from_k8s_object(obj)

        assert job.status == "Unknown"

    def test_from_k8s_object_complete_not_true(self) -> None:
        """Test from_k8s_object does not set Complete when condition status is not True."""
        obj = MagicMock()
        obj.metadata.name = "not-complete-job"
        obj.metadata.namespace = "default"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None

        cond = MagicMock()
        cond.type = "Complete"
        cond.status = "False"
        obj.status.conditions = [cond]
        obj.status.completion_time = None

        job = StaleJob.from_k8s_object(obj)

        assert job.status == "Unknown"

    def test_from_k8s_object_multiple_conditions_complete_first(self) -> None:
        """Test from_k8s_object stops at first matching Complete condition."""
        obj = MagicMock()
        obj.metadata.name = "multi-cond-job"
        obj.metadata.namespace = "default"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None

        cond_complete = MagicMock()
        cond_complete.type = "Complete"
        cond_complete.status = "True"

        cond_failed = MagicMock()
        cond_failed.type = "Failed"
        cond_failed.status = "True"

        obj.status.conditions = [cond_complete, cond_failed]
        obj.status.completion_time = "2024-01-01T02:00:00Z"

        job = StaleJob.from_k8s_object(obj, age_hours=5.0)

        assert job.status == "Complete"

    def test_from_k8s_object_minimal(self) -> None:
        """Test from_k8s_object with minimal job data."""
        obj = MagicMock()
        obj.metadata.name = "minimal-job"
        obj.metadata.namespace = None
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.status.conditions = []
        obj.status.completion_time = None

        job = StaleJob.from_k8s_object(obj)

        assert job.name == "minimal-job"
        assert job.completion_time is None
        assert job.age_hours == 0.0


@pytest.mark.unit
@pytest.mark.kubernetes
class TestOptimizationSummary:
    """Test OptimizationSummary model."""

    def test_defaults(self) -> None:
        """Test OptimizationSummary with default values."""
        s = OptimizationSummary()
        assert s.total_workloads_analyzed == 0
        assert s.overprovisioned_count == 0
        assert s.underutilized_count == 0
        assert s.ok_count == 0
        assert s.orphan_pod_count == 0
        assert s.stale_job_count == 0
        assert s.total_cpu_waste_millicores == 0
        assert s.total_memory_waste_bytes == 0

    def test_cpu_waste_display_millicores(self) -> None:
        """Test cpu_waste_display returns 'm' suffix when under 1000m."""
        s = OptimizationSummary(total_cpu_waste_millicores=750)
        assert s.cpu_waste_display == "750m"

    def test_cpu_waste_display_zero(self) -> None:
        """Test cpu_waste_display returns '0m' for zero waste."""
        s = OptimizationSummary(total_cpu_waste_millicores=0)
        assert s.cpu_waste_display == "0m"

    def test_cpu_waste_display_cores(self) -> None:
        """Test cpu_waste_display returns cores format when >= 1000m."""
        s = OptimizationSummary(total_cpu_waste_millicores=1000)
        assert s.cpu_waste_display == "1.0 cores"

    def test_cpu_waste_display_many_cores(self) -> None:
        """Test cpu_waste_display with multiple cores of waste."""
        s = OptimizationSummary(total_cpu_waste_millicores=3500)
        assert s.cpu_waste_display == "3.5 cores"

    def test_memory_waste_display_bytes(self) -> None:
        """Test memory_waste_display returns raw bytes when under 1 KiB."""
        s = OptimizationSummary(total_memory_waste_bytes=512)
        assert s.memory_waste_display == "512B"

    def test_memory_waste_display_zero(self) -> None:
        """Test memory_waste_display returns '0B' for zero waste."""
        s = OptimizationSummary(total_memory_waste_bytes=0)
        assert s.memory_waste_display == "0B"

    def test_memory_waste_display_mebibytes(self) -> None:
        """Test memory_waste_display returns MiB suffix for values in [1 MiB, 1 GiB)."""
        s = OptimizationSummary(total_memory_waste_bytes=256 * 1024 * 1024)
        assert s.memory_waste_display == "256Mi"

    def test_memory_waste_display_mebibytes_exactly_1_mib(self) -> None:
        """Test memory_waste_display at exactly 1 MiB boundary."""
        s = OptimizationSummary(total_memory_waste_bytes=1024 * 1024)
        assert s.memory_waste_display == "1Mi"

    def test_memory_waste_display_gibibytes(self) -> None:
        """Test memory_waste_display returns GiB suffix for values >= 1 GiB."""
        s = OptimizationSummary(total_memory_waste_bytes=4 * 1024 * 1024 * 1024)
        assert s.memory_waste_display == "4.0Gi"

    def test_memory_waste_display_gibibytes_fractional(self) -> None:
        """Test memory_waste_display for a fractional GiB value."""
        s = OptimizationSummary(total_memory_waste_bytes=int(1.5 * 1024 * 1024 * 1024))
        assert s.memory_waste_display == "1.5Gi"

    def test_populated_summary(self) -> None:
        """Test OptimizationSummary with fully populated fields."""
        s = OptimizationSummary(
            total_workloads_analyzed=20,
            overprovisioned_count=5,
            underutilized_count=3,
            ok_count=12,
            orphan_pod_count=2,
            stale_job_count=4,
            total_cpu_waste_millicores=2000,
            total_memory_waste_bytes=512 * 1024 * 1024,
        )
        assert s.total_workloads_analyzed == 20
        assert s.overprovisioned_count == 5
        assert s.underutilized_count == 3
        assert s.ok_count == 12
        assert s.orphan_pod_count == 2
        assert s.stale_job_count == 4
        assert s.cpu_waste_display == "2.0 cores"
        assert s.memory_waste_display == "512Mi"
