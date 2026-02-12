"""Kubernetes resource optimization manager.

Provides resource usage analysis, right-sizing recommendations,
orphan pod detection, and stale job identification using the
metrics-server API.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from system_operations_manager.integrations.kubernetes.models.optimization import (
    OptimizationSummary,
    OrphanPod,
    ResourceMetrics,
    ResourceSpec,
    RightsizingRecommendation,
    StaleJob,
    WorkloadResourceAnalysis,
)
from system_operations_manager.services.kubernetes.base import K8sBaseManager

# =============================================================================
# Constants
# =============================================================================

UNDERUTILIZED_CPU_THRESHOLD = 0.2
UNDERUTILIZED_MEMORY_THRESHOLD = 0.2
OVERPROVISIONED_BUFFER = 1.3
DEFAULT_STALE_JOB_HOURS = 24
IDLE_CPU_MILLICORES = 1
IDLE_MEMORY_BYTES = 1048576  # 1Mi

METRICS_API_GROUP = "metrics.k8s.io"
METRICS_API_VERSION = "v1beta1"


class OptimizationManager(K8sBaseManager):
    """Manager for Kubernetes resource optimization analysis.

    Uses the metrics-server API to fetch actual resource consumption
    and compare it against workload resource requests/limits.
    """

    _entity_name = "optimization"

    # -------------------------------------------------------------------------
    # Metrics-server helpers
    # -------------------------------------------------------------------------

    def _fetch_pod_metrics(
        self,
        namespace: str | None = None,
        *,
        all_namespaces: bool = False,
    ) -> dict[str, ResourceMetrics]:
        """Fetch pod metrics from metrics-server.

        Returns:
            Mapping of ``namespace/pod-name`` to ResourceMetrics.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("fetching_pod_metrics", namespace=ns, all_namespaces=all_namespaces)

        try:
            if all_namespaces:
                result = self._client.custom_objects.list_cluster_custom_object(
                    group=METRICS_API_GROUP,
                    version=METRICS_API_VERSION,
                    plural="pods",
                )
            else:
                result = self._client.custom_objects.list_namespaced_custom_object(
                    group=METRICS_API_GROUP,
                    version=METRICS_API_VERSION,
                    namespace=ns,
                    plural="pods",
                )

            metrics: dict[str, ResourceMetrics] = {}
            for item in result.get("items", []):
                pod_name = item["metadata"]["name"]
                pod_ns = item["metadata"]["namespace"]
                key = f"{pod_ns}/{pod_name}"

                total_cpu = 0
                total_mem = 0
                for container in item.get("containers", []):
                    total_cpu += _parse_cpu(container.get("usage", {}).get("cpu", "0"))
                    total_mem += _parse_memory(container.get("usage", {}).get("memory", "0"))

                metrics[key] = ResourceMetrics(
                    cpu_millicores=total_cpu,
                    memory_bytes=total_mem,
                )

            self._log.debug("fetched_pod_metrics", count=len(metrics))
            return metrics
        except Exception as e:
            self._handle_api_error(e, "PodMetrics", None, ns)

    def _get_workload_pod_selector(
        self,
        workload: Any,
    ) -> str | None:
        """Extract the label selector string from a workload's spec."""
        match_labels = _safe_nested_get(workload, "spec", "selector", "match_labels")
        if not match_labels:
            return None
        return ",".join(f"{k}={v}" for k, v in match_labels.items())

    def _aggregate_resource_spec(self, pod_template: Any, replicas: int) -> ResourceSpec:
        """Sum resource requests/limits across all containers in a pod template."""
        containers = _safe_nested_get(pod_template, "spec", "containers") or []
        total_cpu_req = 0
        total_cpu_lim = 0
        total_mem_req = 0
        total_mem_lim = 0

        for container in containers:
            resources = getattr(container, "resources", None)
            if resources:
                requests = getattr(resources, "requests", None) or {}
                limits = getattr(resources, "limits", None) or {}
                total_cpu_req += _parse_cpu(requests.get("cpu", "0"))
                total_cpu_lim += _parse_cpu(limits.get("cpu", "0"))
                total_mem_req += _parse_memory(requests.get("memory", "0"))
                total_mem_lim += _parse_memory(limits.get("memory", "0"))

        return ResourceSpec(
            cpu_request_millicores=total_cpu_req * replicas,
            cpu_limit_millicores=total_cpu_lim * replicas,
            memory_request_bytes=total_mem_req * replicas,
            memory_limit_bytes=total_mem_lim * replicas,
        )

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def analyze_workloads(
        self,
        namespace: str | None = None,
        *,
        all_namespaces: bool = False,
        label_selector: str | None = None,
        threshold: float = UNDERUTILIZED_CPU_THRESHOLD,
    ) -> list[WorkloadResourceAnalysis]:
        """Analyze resource usage vs requests for controller-managed workloads.

        Covers Deployments, StatefulSets, and DaemonSets.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info("analyzing_workloads", namespace=ns, all_namespaces=all_namespaces)

        pod_metrics = self._fetch_pod_metrics(namespace=namespace, all_namespaces=all_namespaces)
        analyses: list[WorkloadResourceAnalysis] = []

        for kind, list_fn, replica_fn in self._workload_list_fns(
            ns, all_namespaces, label_selector
        ):
            for workload in list_fn():
                analysis = self._analyze_single_workload(
                    workload, kind, pod_metrics, replica_fn, threshold
                )
                if analysis:
                    analyses.append(analysis)

        self._log.info("analysis_complete", count=len(analyses))
        return analyses

    def recommend(
        self,
        name: str,
        namespace: str | None = None,
        *,
        workload_type: str = "Deployment",
    ) -> RightsizingRecommendation:
        """Get a right-sizing recommendation for a specific workload."""
        ns = self._resolve_namespace(namespace)
        self._log.info("generating_recommendation", name=name, namespace=ns, kind=workload_type)

        workload = self._get_workload(name, ns, workload_type)
        replicas = _get_replicas(workload, workload_type)
        pod_template = _safe_nested_get(workload, "spec", "template")
        current_spec = self._aggregate_resource_spec(pod_template, replicas)

        pod_metrics = self._fetch_pod_metrics(namespace=ns)
        selector = self._get_workload_pod_selector(workload)
        total_usage = self._sum_pod_usage(pod_metrics, ns, selector)

        rec_cpu_req = max(1, int(total_usage.cpu_millicores * OVERPROVISIONED_BUFFER))
        rec_mem_req = max(1048576, int(total_usage.memory_bytes * OVERPROVISIONED_BUFFER))
        rec_cpu_lim = max(rec_cpu_req, int(rec_cpu_req * 2))
        rec_mem_lim = max(rec_mem_req, int(rec_mem_req * 1.5))

        return RightsizingRecommendation(
            name=name,
            namespace=ns,
            workload_type=workload_type,
            current_spec=current_spec,
            current_usage=total_usage,
            recommended_cpu_request_millicores=rec_cpu_req,
            recommended_memory_request_bytes=rec_mem_req,
            recommended_cpu_limit_millicores=rec_cpu_lim,
            recommended_memory_limit_bytes=rec_mem_lim,
            cpu_savings_millicores=max(0, current_spec.cpu_request_millicores - rec_cpu_req),
            memory_savings_bytes=max(0, current_spec.memory_request_bytes - rec_mem_req),
        )

    def find_unused(
        self,
        namespace: str | None = None,
        *,
        all_namespaces: bool = False,
        stale_job_hours: float = DEFAULT_STALE_JOB_HOURS,
        idle_threshold_cpu: int = IDLE_CPU_MILLICORES,
        idle_threshold_memory: int = IDLE_MEMORY_BYTES,
    ) -> dict[str, Any]:
        """Find orphan pods, stale jobs, and idle workloads.

        Returns:
            Dictionary with keys: orphan_pods, stale_jobs, idle_workloads.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info("finding_unused", namespace=ns, all_namespaces=all_namespaces)

        pod_metrics = self._fetch_pod_metrics(namespace=namespace, all_namespaces=all_namespaces)

        orphan_pods = self._find_orphan_pods(ns, all_namespaces, pod_metrics)
        stale_jobs = self._find_stale_jobs(ns, all_namespaces, stale_job_hours)
        idle_workloads = self._find_idle_workloads(
            ns, all_namespaces, pod_metrics, idle_threshold_cpu, idle_threshold_memory
        )

        return {
            "orphan_pods": orphan_pods,
            "stale_jobs": stale_jobs,
            "idle_workloads": idle_workloads,
        }

    def get_summary(
        self,
        namespace: str | None = None,
        *,
        all_namespaces: bool = False,
    ) -> OptimizationSummary:
        """Get a high-level optimization summary."""
        ns = self._resolve_namespace(namespace)
        self._log.info("generating_summary", namespace=ns, all_namespaces=all_namespaces)

        analyses = self.analyze_workloads(namespace=namespace, all_namespaces=all_namespaces)
        unused = self.find_unused(namespace=namespace, all_namespaces=all_namespaces)

        overprovisioned = [a for a in analyses if a.status == "overprovisioned"]
        underutilized = [a for a in analyses if a.status == "underutilized"]
        ok = [a for a in analyses if a.status == "ok"]

        total_cpu_waste = sum(
            max(0, a.total_spec.cpu_request_millicores - a.total_usage.cpu_millicores)
            for a in overprovisioned
        )
        total_mem_waste = sum(
            max(0, a.total_spec.memory_request_bytes - a.total_usage.memory_bytes)
            for a in overprovisioned
        )

        return OptimizationSummary(
            total_workloads_analyzed=len(analyses),
            overprovisioned_count=len(overprovisioned),
            underutilized_count=len(underutilized),
            ok_count=len(ok),
            orphan_pod_count=len(unused["orphan_pods"]),
            stale_job_count=len(unused["stale_jobs"]),
            total_cpu_waste_millicores=total_cpu_waste,
            total_memory_waste_bytes=total_mem_waste,
        )

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _workload_list_fns(
        self,
        namespace: str,
        all_namespaces: bool,
        label_selector: str | None,
    ) -> list[tuple[str, Any, Any]]:
        """Return (kind, list_function, replica_extractor) triples."""
        kwargs: dict[str, Any] = {}
        if label_selector:
            kwargs["label_selector"] = label_selector

        def _list_deployments() -> list[Any]:
            if all_namespaces:
                r = self._client.apps_v1.list_deployment_for_all_namespaces(**kwargs)
            else:
                r = self._client.apps_v1.list_namespaced_deployment(namespace=namespace, **kwargs)
            items: list[Any] = r.items
            return items

        def _list_statefulsets() -> list[Any]:
            if all_namespaces:
                r = self._client.apps_v1.list_stateful_set_for_all_namespaces(**kwargs)
            else:
                r = self._client.apps_v1.list_namespaced_stateful_set(namespace=namespace, **kwargs)
            items: list[Any] = r.items
            return items

        def _list_daemonsets() -> list[Any]:
            if all_namespaces:
                r = self._client.apps_v1.list_daemon_set_for_all_namespaces(**kwargs)
            else:
                r = self._client.apps_v1.list_namespaced_daemon_set(namespace=namespace, **kwargs)
            items: list[Any] = r.items
            return items

        return [
            ("Deployment", _list_deployments, lambda w: _get_replicas(w, "Deployment")),
            ("StatefulSet", _list_statefulsets, lambda w: _get_replicas(w, "StatefulSet")),
            ("DaemonSet", _list_daemonsets, lambda w: _get_replicas(w, "DaemonSet")),
        ]

    def _analyze_single_workload(
        self,
        workload: Any,
        kind: str,
        pod_metrics: dict[str, ResourceMetrics],
        replica_fn: Any,
        threshold: float,
    ) -> WorkloadResourceAnalysis | None:
        """Analyze a single workload against its pod metrics."""
        name = _safe_nested_get(workload, "metadata", "name")
        ns = _safe_nested_get(workload, "metadata", "namespace")
        if not name or not ns:
            return None

        replicas = replica_fn(workload)
        pod_template = _safe_nested_get(workload, "spec", "template")
        spec = self._aggregate_resource_spec(pod_template, replicas)

        selector = self._get_workload_pod_selector(workload)
        usage = self._sum_pod_usage(pod_metrics, ns, selector)

        cpu_util = (
            (usage.cpu_millicores / spec.cpu_request_millicores)
            if spec.cpu_request_millicores > 0
            else 0.0
        )
        mem_util = (
            (usage.memory_bytes / spec.memory_request_bytes)
            if spec.memory_request_bytes > 0
            else 0.0
        )

        if (
            cpu_util < threshold
            and mem_util < threshold
            and (spec.cpu_request_millicores > 0 or spec.memory_request_bytes > 0)
        ):
            if (
                usage.cpu_millicores <= IDLE_CPU_MILLICORES
                and usage.memory_bytes <= IDLE_MEMORY_BYTES
            ):
                status = "underutilized"
            else:
                status = "overprovisioned"
        else:
            status = "ok"

        creation_ts = _safe_nested_get(workload, "metadata", "creation_timestamp")
        ts_str: str | None = None
        if creation_ts is not None:
            if isinstance(creation_ts, datetime):
                ts_str = creation_ts.isoformat()
            elif isinstance(creation_ts, str):
                ts_str = creation_ts
            else:
                ts_str = str(creation_ts)

        return WorkloadResourceAnalysis(
            name=name,
            namespace=ns,
            creation_timestamp=ts_str,
            workload_type=kind,
            replicas=replicas,
            total_usage=usage,
            total_spec=spec,
            cpu_utilization_pct=round(cpu_util * 100, 1),
            memory_utilization_pct=round(mem_util * 100, 1),
            status=status,
        )

    def _sum_pod_usage(
        self,
        pod_metrics: dict[str, ResourceMetrics],
        namespace: str,
        label_selector: str | None,
    ) -> ResourceMetrics:
        """Sum metrics for pods matching a workload's selector.

        Falls back to namespace prefix matching when metrics don't have labels.
        """
        if not label_selector:
            return ResourceMetrics()

        # Fetch pods matching the selector to get their names
        try:
            pods = self._client.core_v1.list_namespaced_pod(
                namespace=namespace,
                label_selector=label_selector,
            )
            pod_names = {f"{namespace}/{p.metadata.name}" for p in (pods.items or [])}
        except Exception:
            pod_names = set()

        total_cpu = 0
        total_mem = 0
        for key, m in pod_metrics.items():
            if key in pod_names:
                total_cpu += m.cpu_millicores
                total_mem += m.memory_bytes

        return ResourceMetrics(cpu_millicores=total_cpu, memory_bytes=total_mem)

    def _get_workload(self, name: str, namespace: str, kind: str) -> Any:
        """Fetch a single workload by name and kind."""
        try:
            if kind == "Deployment":
                return self._client.apps_v1.read_namespaced_deployment(name, namespace)
            elif kind == "StatefulSet":
                return self._client.apps_v1.read_namespaced_stateful_set(name, namespace)
            elif kind == "DaemonSet":
                return self._client.apps_v1.read_namespaced_daemon_set(name, namespace)
            else:
                self._log.error("unknown_workload_type", kind=kind)
                msg = f"Unknown workload type: {kind}"
                raise ValueError(msg)
        except ValueError:
            raise
        except Exception as e:
            self._handle_api_error(e, kind, name, namespace)

    def _find_orphan_pods(
        self,
        namespace: str,
        all_namespaces: bool,
        pod_metrics: dict[str, ResourceMetrics],
    ) -> list[OrphanPod]:
        """Find pods with no owner controller."""
        try:
            if all_namespaces:
                result = self._client.core_v1.list_pod_for_all_namespaces()
            else:
                result = self._client.core_v1.list_namespaced_pod(namespace=namespace)
        except Exception as e:
            self._handle_api_error(e, "Pod", None, namespace)

        orphans: list[OrphanPod] = []
        for pod in result.items or []:
            owner_refs = _safe_nested_get(pod, "metadata", "owner_references") or []
            if not owner_refs:
                pod_name = _safe_nested_get(pod, "metadata", "name") or ""
                pod_ns = _safe_nested_get(pod, "metadata", "namespace") or namespace
                key = f"{pod_ns}/{pod_name}"
                metrics = pod_metrics.get(key)
                orphans.append(OrphanPod.from_k8s_object(pod, metrics))

        return orphans

    def _find_stale_jobs(
        self,
        namespace: str,
        all_namespaces: bool,
        stale_job_hours: float,
    ) -> list[StaleJob]:
        """Find completed/failed jobs older than the threshold."""
        try:
            if all_namespaces:
                result = self._client.batch_v1.list_job_for_all_namespaces()
            else:
                result = self._client.batch_v1.list_namespaced_job(namespace=namespace)
        except Exception as e:
            self._handle_api_error(e, "Job", None, namespace)

        now = datetime.now(UTC)
        stale: list[StaleJob] = []
        for job in result.items or []:
            completion_time = _safe_nested_get(job, "status", "completion_time")
            conditions = _safe_nested_get(job, "status", "conditions") or []

            is_finished = False
            if completion_time:
                is_finished = True
            else:
                for cond in conditions:
                    cond_type = getattr(cond, "type", None)
                    cond_status = getattr(cond, "status", None)
                    if cond_type == "Failed" and cond_status == "True":
                        is_finished = True
                        break

            if not is_finished:
                continue

            ref_time = completion_time
            if ref_time is None:
                # Use the failed condition's last transition time
                for cond in conditions:
                    if getattr(cond, "type", None) == "Failed":
                        ref_time = getattr(cond, "last_transition_time", None)
                        break

            if ref_time is None:
                continue

            if isinstance(ref_time, str):
                ref_time = datetime.fromisoformat(ref_time.replace("Z", "+00:00"))

            age_hours = (now - ref_time).total_seconds() / 3600
            if age_hours >= stale_job_hours:
                stale.append(StaleJob.from_k8s_object(job, age_hours=age_hours))

        return stale

    def _find_idle_workloads(
        self,
        namespace: str,
        all_namespaces: bool,
        pod_metrics: dict[str, ResourceMetrics],
        idle_cpu: int,
        idle_memory: int,
    ) -> list[WorkloadResourceAnalysis]:
        """Find controller-managed workloads with negligible usage."""
        analyses = self.analyze_workloads(
            namespace=namespace if not all_namespaces else None,
            all_namespaces=all_namespaces,
        )
        return [
            a
            for a in analyses
            if a.total_usage.cpu_millicores <= idle_cpu
            and a.total_usage.memory_bytes <= idle_memory
            and (a.total_spec.cpu_request_millicores > 0 or a.total_spec.memory_request_bytes > 0)
        ]


# =============================================================================
# Module-level helpers
# =============================================================================


def _parse_cpu(value: str) -> int:
    """Parse a Kubernetes CPU value to millicores."""
    if not value or value == "0":
        return 0
    value = str(value)
    if value.endswith("n"):
        return int(int(value[:-1]) / 1_000_000)
    if value.endswith("u"):
        return int(int(value[:-1]) / 1_000)
    if value.endswith("m"):
        return int(value[:-1])
    # Assume cores
    return int(float(value) * 1000)


def _parse_memory(value: str) -> int:
    """Parse a Kubernetes memory value to bytes."""
    if not value or value == "0":
        return 0
    value = str(value)
    suffixes = {
        "Ki": 1024,
        "Mi": 1024**2,
        "Gi": 1024**3,
        "Ti": 1024**4,
        "k": 1000,
        "M": 1000**2,
        "G": 1000**3,
        "T": 1000**4,
    }
    for suffix, multiplier in suffixes.items():
        if value.endswith(suffix):
            return int(float(value[: -len(suffix)]) * multiplier)
    return int(value)


def _safe_nested_get(obj: Any, *attrs: str, default: Any = None) -> Any:
    """Safely traverse nested attributes on kubernetes SDK objects."""
    current = obj
    for attr in attrs:
        if current is None:
            return default
        current = getattr(current, attr, None)
    return current if current is not None else default


def _get_replicas(workload: Any, kind: str) -> int:
    """Extract the effective replica count from a workload."""
    if kind == "DaemonSet":
        result: int = _safe_nested_get(workload, "status", "desired_number_scheduled", default=1)
        return result
    count: int = _safe_nested_get(workload, "spec", "replicas", default=1)
    return count
