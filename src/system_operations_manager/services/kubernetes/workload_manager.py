"""Kubernetes workload resource manager.

Manages Pods, Deployments, StatefulSets, DaemonSets, and ReplicaSets
through the Kubernetes API, providing CRUD operations plus workload-specific
actions like scale, restart, rollout status, and rollback.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from system_operations_manager.integrations.kubernetes.models.workloads import (
    DaemonSetSummary,
    DeploymentSummary,
    PodSummary,
    ReplicaSetSummary,
    StatefulSetSummary,
)
from system_operations_manager.services.kubernetes.base import K8sBaseManager


class WorkloadManager(K8sBaseManager):
    """Manager for Kubernetes workload resources.

    Provides operations for Pods, Deployments, StatefulSets, DaemonSets,
    and ReplicaSets including scale, restart, and rollback capabilities.
    """

    _entity_name = "workload"

    # =========================================================================
    # Pod Operations
    # =========================================================================

    def list_pods(
        self,
        namespace: str | None = None,
        *,
        all_namespaces: bool = False,
        label_selector: str | None = None,
        field_selector: str | None = None,
    ) -> list[PodSummary]:
        """List pods in a namespace or across all namespaces.

        Args:
            namespace: Target namespace (uses default if None).
            all_namespaces: List pods across all namespaces.
            label_selector: Filter by label selector (e.g., 'app=nginx').
            field_selector: Filter by field selector (e.g., 'status.phase=Running').

        Returns:
            List of pod summaries.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_pods", namespace=ns, all_namespaces=all_namespaces)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector
            if field_selector:
                kwargs["field_selector"] = field_selector

            if all_namespaces:
                result = self._client.core_v1.list_pod_for_all_namespaces(**kwargs)
            else:
                result = self._client.core_v1.list_namespaced_pod(namespace=ns, **kwargs)

            pods = [PodSummary.from_k8s_object(pod) for pod in result.items]
            self._log.debug("listed_pods", count=len(pods))
            return pods
        except Exception as e:
            self._handle_api_error(e, "Pod", None, ns)

    def get_pod(self, name: str, namespace: str | None = None) -> PodSummary:
        """Get a single pod by name.

        Args:
            name: Pod name.
            namespace: Target namespace.

        Returns:
            Pod summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_pod", name=name, namespace=ns)
        try:
            result = self._client.core_v1.read_namespaced_pod(name=name, namespace=ns)
            return PodSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Pod", name, ns)

    def delete_pod(self, name: str, namespace: str | None = None) -> None:
        """Delete a pod.

        Args:
            name: Pod name.
            namespace: Target namespace.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info("deleting_pod", name=name, namespace=ns)
        try:
            self._client.core_v1.delete_namespaced_pod(name=name, namespace=ns)
            self._log.info("deleted_pod", name=name, namespace=ns)
        except Exception as e:
            self._handle_api_error(e, "Pod", name, ns)

    def get_pod_logs(
        self,
        name: str,
        namespace: str | None = None,
        *,
        container: str | None = None,
        tail_lines: int | None = None,
        previous: bool = False,
    ) -> str:
        """Get logs from a pod.

        Args:
            name: Pod name.
            namespace: Target namespace.
            container: Specific container name (required for multi-container pods).
            tail_lines: Number of lines from the end of the log.
            previous: Return logs from previous terminated container.

        Returns:
            Log content as string.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_pod_logs", name=name, namespace=ns, container=container)
        try:
            kwargs: dict[str, Any] = {"name": name, "namespace": ns}
            if container:
                kwargs["container"] = container
            if tail_lines is not None:
                kwargs["tail_lines"] = tail_lines
            if previous:
                kwargs["previous"] = previous

            logs: str = self._client.core_v1.read_namespaced_pod_log(**kwargs)
            return logs
        except Exception as e:
            self._handle_api_error(e, "Pod", name, ns)

    # =========================================================================
    # Deployment Operations
    # =========================================================================

    def list_deployments(
        self,
        namespace: str | None = None,
        *,
        all_namespaces: bool = False,
        label_selector: str | None = None,
    ) -> list[DeploymentSummary]:
        """List deployments.

        Args:
            namespace: Target namespace.
            all_namespaces: List across all namespaces.
            label_selector: Filter by label selector.

        Returns:
            List of deployment summaries.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_deployments", namespace=ns, all_namespaces=all_namespaces)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            if all_namespaces:
                result = self._client.apps_v1.list_deployment_for_all_namespaces(**kwargs)
            else:
                result = self._client.apps_v1.list_namespaced_deployment(namespace=ns, **kwargs)

            deployments = [DeploymentSummary.from_k8s_object(d) for d in result.items]
            self._log.debug("listed_deployments", count=len(deployments))
            return deployments
        except Exception as e:
            self._handle_api_error(e, "Deployment", None, ns)

    def get_deployment(self, name: str, namespace: str | None = None) -> DeploymentSummary:
        """Get a single deployment by name.

        Args:
            name: Deployment name.
            namespace: Target namespace.

        Returns:
            Deployment summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_deployment", name=name, namespace=ns)
        try:
            result = self._client.apps_v1.read_namespaced_deployment(name=name, namespace=ns)
            return DeploymentSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Deployment", name, ns)

    def create_deployment(
        self,
        name: str,
        namespace: str | None = None,
        *,
        image: str,
        replicas: int = 1,
        labels: dict[str, str] | None = None,
        port: int | None = None,
    ) -> DeploymentSummary:
        """Create a deployment.

        Args:
            name: Deployment name.
            namespace: Target namespace.
            image: Container image.
            replicas: Number of replicas.
            labels: Labels for the deployment and pod template.
            port: Container port to expose.

        Returns:
            Created deployment summary.
        """
        from kubernetes.client import (
            V1Container,
            V1ContainerPort,
            V1Deployment,
            V1DeploymentSpec,
            V1LabelSelector,
            V1ObjectMeta,
            V1PodSpec,
            V1PodTemplateSpec,
        )

        ns = self._resolve_namespace(namespace)
        pod_labels = labels or {"app": name}

        container = V1Container(
            name=name,
            image=image,
            ports=[V1ContainerPort(container_port=port)] if port else None,
        )

        body = V1Deployment(
            metadata=V1ObjectMeta(name=name, namespace=ns, labels=pod_labels),
            spec=V1DeploymentSpec(
                replicas=replicas,
                selector=V1LabelSelector(match_labels=pod_labels),
                template=V1PodTemplateSpec(
                    metadata=V1ObjectMeta(labels=pod_labels),
                    spec=V1PodSpec(containers=[container]),
                ),
            ),
        )

        self._log.info(
            "creating_deployment", name=name, namespace=ns, image=image, replicas=replicas
        )
        try:
            result = self._client.apps_v1.create_namespaced_deployment(namespace=ns, body=body)
            self._log.info("created_deployment", name=name, namespace=ns)
            return DeploymentSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Deployment", name, ns)

    def update_deployment(
        self,
        name: str,
        namespace: str | None = None,
        *,
        image: str | None = None,
        replicas: int | None = None,
    ) -> DeploymentSummary:
        """Update a deployment (patch).

        Args:
            name: Deployment name.
            namespace: Target namespace.
            image: New container image.
            replicas: New replica count.

        Returns:
            Updated deployment summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info("updating_deployment", name=name, namespace=ns)
        try:
            patch: dict[str, Any] = {"spec": {}}
            if replicas is not None:
                patch["spec"]["replicas"] = replicas
            if image is not None:
                patch["spec"]["template"] = {
                    "spec": {"containers": [{"name": name, "image": image}]}
                }

            result = self._client.apps_v1.patch_namespaced_deployment(
                name=name, namespace=ns, body=patch
            )
            self._log.info("updated_deployment", name=name, namespace=ns)
            return DeploymentSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Deployment", name, ns)

    def delete_deployment(self, name: str, namespace: str | None = None) -> None:
        """Delete a deployment.

        Args:
            name: Deployment name.
            namespace: Target namespace.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info("deleting_deployment", name=name, namespace=ns)
        try:
            self._client.apps_v1.delete_namespaced_deployment(name=name, namespace=ns)
            self._log.info("deleted_deployment", name=name, namespace=ns)
        except Exception as e:
            self._handle_api_error(e, "Deployment", name, ns)

    def scale_deployment(
        self, name: str, namespace: str | None = None, *, replicas: int
    ) -> DeploymentSummary:
        """Scale a deployment to the specified number of replicas.

        Args:
            name: Deployment name.
            namespace: Target namespace.
            replicas: Desired replica count.

        Returns:
            Updated deployment summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info("scaling_deployment", name=name, namespace=ns, replicas=replicas)
        try:
            patch = {"spec": {"replicas": replicas}}
            result = self._client.apps_v1.patch_namespaced_deployment(
                name=name, namespace=ns, body=patch
            )
            self._log.info("scaled_deployment", name=name, namespace=ns, replicas=replicas)
            return DeploymentSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Deployment", name, ns)

    def restart_deployment(self, name: str, namespace: str | None = None) -> DeploymentSummary:
        """Restart a deployment by patching the pod template annotation.

        Equivalent to ``kubectl rollout restart deployment``.

        Args:
            name: Deployment name.
            namespace: Target namespace.

        Returns:
            Updated deployment summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info("restarting_deployment", name=name, namespace=ns)
        try:
            now = datetime.now(UTC).isoformat()
            patch = {
                "spec": {
                    "template": {
                        "metadata": {"annotations": {"kubectl.kubernetes.io/restartedAt": now}}
                    }
                }
            }
            result = self._client.apps_v1.patch_namespaced_deployment(
                name=name, namespace=ns, body=patch
            )
            self._log.info("restarted_deployment", name=name, namespace=ns)
            return DeploymentSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Deployment", name, ns)

    def get_rollout_status(self, name: str, namespace: str | None = None) -> dict[str, Any]:
        """Get the rollout status of a deployment.

        Args:
            name: Deployment name.
            namespace: Target namespace.

        Returns:
            Dictionary with rollout status information.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_rollout_status", name=name, namespace=ns)
        try:
            result = self._client.apps_v1.read_namespaced_deployment(name=name, namespace=ns)
            spec_replicas = getattr(result.spec, "replicas", 0) or 0
            status = result.status
            updated = getattr(status, "updated_replicas", 0) or 0
            ready = getattr(status, "ready_replicas", 0) or 0
            available = getattr(status, "available_replicas", 0) or 0

            conditions = getattr(status, "conditions", None) or []
            condition_messages = []
            for cond in conditions:
                condition_messages.append(
                    {
                        "type": getattr(cond, "type", ""),
                        "status": getattr(cond, "status", ""),
                        "reason": getattr(cond, "reason", ""),
                        "message": getattr(cond, "message", ""),
                    }
                )

            complete = updated == spec_replicas and ready == spec_replicas

            return {
                "name": name,
                "namespace": ns,
                "desired_replicas": spec_replicas,
                "updated_replicas": updated,
                "ready_replicas": ready,
                "available_replicas": available,
                "complete": complete,
                "conditions": condition_messages,
            }
        except Exception as e:
            self._handle_api_error(e, "Deployment", name, ns)

    def rollback_deployment(
        self, name: str, namespace: str | None = None, *, revision: int | None = None
    ) -> None:
        """Rollback a deployment to a previous revision.

        If no revision is specified, rolls back to the previous revision by
        extracting the previous ReplicaSet's pod template and patching the
        deployment.

        Args:
            name: Deployment name.
            namespace: Target namespace.
            revision: Target revision number (None for previous).
        """
        ns = self._resolve_namespace(namespace)
        self._log.info("rolling_back_deployment", name=name, namespace=ns, revision=revision)
        try:
            # Get the deployment to find its selector
            deployment = self._client.apps_v1.read_namespaced_deployment(name=name, namespace=ns)
            selector = deployment.spec.selector.match_labels or {}
            label_selector = ",".join(f"{k}={v}" for k, v in selector.items())

            # Get ReplicaSets owned by this deployment
            rs_list = self._client.apps_v1.list_namespaced_replica_set(
                namespace=ns, label_selector=label_selector
            )

            # Filter to ReplicaSets owned by this deployment
            owned_rs = []
            for rs in rs_list.items:
                owners = getattr(rs.metadata, "owner_references", None) or []
                for owner in owners:
                    if (
                        getattr(owner, "kind", "") == "Deployment"
                        and getattr(owner, "name", "") == name
                    ):
                        owned_rs.append(rs)
                        break

            if len(owned_rs) < 2:
                self._log.warning("no_previous_revision", name=name, namespace=ns)
                return

            # Sort by revision annotation
            def _get_revision(rs: Any) -> int:
                annotations = getattr(rs.metadata, "annotations", None) or {}
                rev_str = annotations.get("deployment.kubernetes.io/revision", "0")
                try:
                    return int(rev_str)
                except ValueError, TypeError:
                    return 0

            owned_rs.sort(key=_get_revision, reverse=True)

            if revision is not None:
                target_rs = next((rs for rs in owned_rs if _get_revision(rs) == revision), None)
            else:
                # Previous revision is the second newest
                target_rs = owned_rs[1] if len(owned_rs) > 1 else None

            if target_rs is None:
                self._log.warning("revision_not_found", name=name, revision=revision)
                return

            # Patch deployment with the target RS's pod template
            patch = {"spec": {"template": target_rs.spec.template}}
            self._client.apps_v1.patch_namespaced_deployment(name=name, namespace=ns, body=patch)
            self._log.info(
                "rolled_back_deployment",
                name=name,
                namespace=ns,
                to_revision=_get_revision(target_rs),
            )
        except Exception as e:
            self._handle_api_error(e, "Deployment", name, ns)

    # =========================================================================
    # StatefulSet Operations
    # =========================================================================

    def list_stateful_sets(
        self,
        namespace: str | None = None,
        *,
        all_namespaces: bool = False,
        label_selector: str | None = None,
    ) -> list[StatefulSetSummary]:
        """List statefulsets.

        Args:
            namespace: Target namespace.
            all_namespaces: List across all namespaces.
            label_selector: Filter by label selector.

        Returns:
            List of statefulset summaries.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_statefulsets", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            if all_namespaces:
                result = self._client.apps_v1.list_stateful_set_for_all_namespaces(**kwargs)
            else:
                result = self._client.apps_v1.list_namespaced_stateful_set(namespace=ns, **kwargs)

            items = [StatefulSetSummary.from_k8s_object(s) for s in result.items]
            self._log.debug("listed_statefulsets", count=len(items))
            return items
        except Exception as e:
            self._handle_api_error(e, "StatefulSet", None, ns)

    def get_stateful_set(self, name: str, namespace: str | None = None) -> StatefulSetSummary:
        """Get a single statefulset by name.

        Args:
            name: StatefulSet name.
            namespace: Target namespace.

        Returns:
            StatefulSet summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_statefulset", name=name, namespace=ns)
        try:
            result = self._client.apps_v1.read_namespaced_stateful_set(name=name, namespace=ns)
            return StatefulSetSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "StatefulSet", name, ns)

    def create_stateful_set(
        self,
        name: str,
        namespace: str | None = None,
        *,
        image: str,
        replicas: int = 1,
        service_name: str,
        labels: dict[str, str] | None = None,
        port: int | None = None,
    ) -> StatefulSetSummary:
        """Create a statefulset.

        Args:
            name: StatefulSet name.
            namespace: Target namespace.
            image: Container image.
            replicas: Number of replicas.
            service_name: Headless service name.
            labels: Labels for the statefulset and pod template.
            port: Container port to expose.

        Returns:
            Created statefulset summary.
        """
        from kubernetes.client import (
            V1Container,
            V1ContainerPort,
            V1LabelSelector,
            V1ObjectMeta,
            V1PodSpec,
            V1PodTemplateSpec,
            V1StatefulSet,
            V1StatefulSetSpec,
        )

        ns = self._resolve_namespace(namespace)
        pod_labels = labels or {"app": name}

        container = V1Container(
            name=name,
            image=image,
            ports=[V1ContainerPort(container_port=port)] if port else None,
        )

        body = V1StatefulSet(
            metadata=V1ObjectMeta(name=name, namespace=ns, labels=pod_labels),
            spec=V1StatefulSetSpec(
                replicas=replicas,
                service_name=service_name,
                selector=V1LabelSelector(match_labels=pod_labels),
                template=V1PodTemplateSpec(
                    metadata=V1ObjectMeta(labels=pod_labels),
                    spec=V1PodSpec(containers=[container]),
                ),
            ),
        )

        self._log.info("creating_statefulset", name=name, namespace=ns, image=image)
        try:
            result = self._client.apps_v1.create_namespaced_stateful_set(namespace=ns, body=body)
            self._log.info("created_statefulset", name=name, namespace=ns)
            return StatefulSetSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "StatefulSet", name, ns)

    def update_stateful_set(
        self,
        name: str,
        namespace: str | None = None,
        *,
        image: str | None = None,
        replicas: int | None = None,
    ) -> StatefulSetSummary:
        """Update a statefulset (patch).

        Args:
            name: StatefulSet name.
            namespace: Target namespace.
            image: New container image.
            replicas: New replica count.

        Returns:
            Updated statefulset summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info("updating_statefulset", name=name, namespace=ns)
        try:
            patch: dict[str, Any] = {"spec": {}}
            if replicas is not None:
                patch["spec"]["replicas"] = replicas
            if image is not None:
                patch["spec"]["template"] = {
                    "spec": {"containers": [{"name": name, "image": image}]}
                }

            result = self._client.apps_v1.patch_namespaced_stateful_set(
                name=name, namespace=ns, body=patch
            )
            self._log.info("updated_statefulset", name=name, namespace=ns)
            return StatefulSetSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "StatefulSet", name, ns)

    def delete_stateful_set(self, name: str, namespace: str | None = None) -> None:
        """Delete a statefulset.

        Args:
            name: StatefulSet name.
            namespace: Target namespace.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info("deleting_statefulset", name=name, namespace=ns)
        try:
            self._client.apps_v1.delete_namespaced_stateful_set(name=name, namespace=ns)
            self._log.info("deleted_statefulset", name=name, namespace=ns)
        except Exception as e:
            self._handle_api_error(e, "StatefulSet", name, ns)

    def scale_stateful_set(
        self, name: str, namespace: str | None = None, *, replicas: int
    ) -> StatefulSetSummary:
        """Scale a statefulset.

        Args:
            name: StatefulSet name.
            namespace: Target namespace.
            replicas: Desired replica count.

        Returns:
            Updated statefulset summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info("scaling_statefulset", name=name, namespace=ns, replicas=replicas)
        try:
            patch = {"spec": {"replicas": replicas}}
            result = self._client.apps_v1.patch_namespaced_stateful_set(
                name=name, namespace=ns, body=patch
            )
            self._log.info("scaled_statefulset", name=name, namespace=ns, replicas=replicas)
            return StatefulSetSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "StatefulSet", name, ns)

    def restart_stateful_set(self, name: str, namespace: str | None = None) -> StatefulSetSummary:
        """Restart a statefulset by patching the pod template annotation.

        Args:
            name: StatefulSet name.
            namespace: Target namespace.

        Returns:
            Updated statefulset summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info("restarting_statefulset", name=name, namespace=ns)
        try:
            now = datetime.now(UTC).isoformat()
            patch = {
                "spec": {
                    "template": {
                        "metadata": {"annotations": {"kubectl.kubernetes.io/restartedAt": now}}
                    }
                }
            }
            result = self._client.apps_v1.patch_namespaced_stateful_set(
                name=name, namespace=ns, body=patch
            )
            self._log.info("restarted_statefulset", name=name, namespace=ns)
            return StatefulSetSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "StatefulSet", name, ns)

    # =========================================================================
    # DaemonSet Operations
    # =========================================================================

    def list_daemon_sets(
        self,
        namespace: str | None = None,
        *,
        all_namespaces: bool = False,
        label_selector: str | None = None,
    ) -> list[DaemonSetSummary]:
        """List daemonsets.

        Args:
            namespace: Target namespace.
            all_namespaces: List across all namespaces.
            label_selector: Filter by label selector.

        Returns:
            List of daemonset summaries.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_daemonsets", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            if all_namespaces:
                result = self._client.apps_v1.list_daemon_set_for_all_namespaces(**kwargs)
            else:
                result = self._client.apps_v1.list_namespaced_daemon_set(namespace=ns, **kwargs)

            items = [DaemonSetSummary.from_k8s_object(d) for d in result.items]
            self._log.debug("listed_daemonsets", count=len(items))
            return items
        except Exception as e:
            self._handle_api_error(e, "DaemonSet", None, ns)

    def get_daemon_set(self, name: str, namespace: str | None = None) -> DaemonSetSummary:
        """Get a single daemonset by name.

        Args:
            name: DaemonSet name.
            namespace: Target namespace.

        Returns:
            DaemonSet summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_daemonset", name=name, namespace=ns)
        try:
            result = self._client.apps_v1.read_namespaced_daemon_set(name=name, namespace=ns)
            return DaemonSetSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "DaemonSet", name, ns)

    def create_daemon_set(
        self,
        name: str,
        namespace: str | None = None,
        *,
        image: str,
        labels: dict[str, str] | None = None,
        port: int | None = None,
    ) -> DaemonSetSummary:
        """Create a daemonset.

        Args:
            name: DaemonSet name.
            namespace: Target namespace.
            image: Container image.
            labels: Labels for the daemonset and pod template.
            port: Container port to expose.

        Returns:
            Created daemonset summary.
        """
        from kubernetes.client import (
            V1Container,
            V1ContainerPort,
            V1DaemonSet,
            V1DaemonSetSpec,
            V1LabelSelector,
            V1ObjectMeta,
            V1PodSpec,
            V1PodTemplateSpec,
        )

        ns = self._resolve_namespace(namespace)
        pod_labels = labels or {"app": name}

        container = V1Container(
            name=name,
            image=image,
            ports=[V1ContainerPort(container_port=port)] if port else None,
        )

        body = V1DaemonSet(
            metadata=V1ObjectMeta(name=name, namespace=ns, labels=pod_labels),
            spec=V1DaemonSetSpec(
                selector=V1LabelSelector(match_labels=pod_labels),
                template=V1PodTemplateSpec(
                    metadata=V1ObjectMeta(labels=pod_labels),
                    spec=V1PodSpec(containers=[container]),
                ),
            ),
        )

        self._log.info("creating_daemonset", name=name, namespace=ns, image=image)
        try:
            result = self._client.apps_v1.create_namespaced_daemon_set(namespace=ns, body=body)
            self._log.info("created_daemonset", name=name, namespace=ns)
            return DaemonSetSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "DaemonSet", name, ns)

    def update_daemon_set(
        self,
        name: str,
        namespace: str | None = None,
        *,
        image: str | None = None,
    ) -> DaemonSetSummary:
        """Update a daemonset (patch).

        Args:
            name: DaemonSet name.
            namespace: Target namespace.
            image: New container image.

        Returns:
            Updated daemonset summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info("updating_daemonset", name=name, namespace=ns)
        try:
            patch: dict[str, Any] = {"spec": {}}
            if image is not None:
                patch["spec"]["template"] = {
                    "spec": {"containers": [{"name": name, "image": image}]}
                }

            result = self._client.apps_v1.patch_namespaced_daemon_set(
                name=name, namespace=ns, body=patch
            )
            self._log.info("updated_daemonset", name=name, namespace=ns)
            return DaemonSetSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "DaemonSet", name, ns)

    def delete_daemon_set(self, name: str, namespace: str | None = None) -> None:
        """Delete a daemonset.

        Args:
            name: DaemonSet name.
            namespace: Target namespace.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info("deleting_daemonset", name=name, namespace=ns)
        try:
            self._client.apps_v1.delete_namespaced_daemon_set(name=name, namespace=ns)
            self._log.info("deleted_daemonset", name=name, namespace=ns)
        except Exception as e:
            self._handle_api_error(e, "DaemonSet", name, ns)

    def restart_daemon_set(self, name: str, namespace: str | None = None) -> DaemonSetSummary:
        """Restart a daemonset by patching the pod template annotation.

        Args:
            name: DaemonSet name.
            namespace: Target namespace.

        Returns:
            Updated daemonset summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info("restarting_daemonset", name=name, namespace=ns)
        try:
            now = datetime.now(UTC).isoformat()
            patch = {
                "spec": {
                    "template": {
                        "metadata": {"annotations": {"kubectl.kubernetes.io/restartedAt": now}}
                    }
                }
            }
            result = self._client.apps_v1.patch_namespaced_daemon_set(
                name=name, namespace=ns, body=patch
            )
            self._log.info("restarted_daemonset", name=name, namespace=ns)
            return DaemonSetSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "DaemonSet", name, ns)

    # =========================================================================
    # ReplicaSet Operations
    # =========================================================================

    def list_replica_sets(
        self,
        namespace: str | None = None,
        *,
        all_namespaces: bool = False,
        label_selector: str | None = None,
    ) -> list[ReplicaSetSummary]:
        """List replicasets.

        Args:
            namespace: Target namespace.
            all_namespaces: List across all namespaces.
            label_selector: Filter by label selector.

        Returns:
            List of replicaset summaries.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_replicasets", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            if all_namespaces:
                result = self._client.apps_v1.list_replica_set_for_all_namespaces(**kwargs)
            else:
                result = self._client.apps_v1.list_namespaced_replica_set(namespace=ns, **kwargs)

            items = [ReplicaSetSummary.from_k8s_object(rs) for rs in result.items]
            self._log.debug("listed_replicasets", count=len(items))
            return items
        except Exception as e:
            self._handle_api_error(e, "ReplicaSet", None, ns)

    def get_replica_set(self, name: str, namespace: str | None = None) -> ReplicaSetSummary:
        """Get a single replicaset by name.

        Args:
            name: ReplicaSet name.
            namespace: Target namespace.

        Returns:
            ReplicaSet summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_replicaset", name=name, namespace=ns)
        try:
            result = self._client.apps_v1.read_namespaced_replica_set(name=name, namespace=ns)
            return ReplicaSetSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "ReplicaSet", name, ns)

    def delete_replica_set(self, name: str, namespace: str | None = None) -> None:
        """Delete a replicaset.

        Args:
            name: ReplicaSet name.
            namespace: Target namespace.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info("deleting_replicaset", name=name, namespace=ns)
        try:
            self._client.apps_v1.delete_namespaced_replica_set(name=name, namespace=ns)
            self._log.info("deleted_replicaset", name=name, namespace=ns)
        except Exception as e:
            self._handle_api_error(e, "ReplicaSet", name, ns)
