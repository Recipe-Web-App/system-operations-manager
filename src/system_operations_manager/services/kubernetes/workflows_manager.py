"""Argo Workflows resource manager.

Manages Argo Workflows, WorkflowTemplates, CronWorkflows, and workflow artifacts
through the Kubernetes ``CustomObjectsApi``.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from system_operations_manager.integrations.kubernetes.models.argo_workflows import (
    CronWorkflowSummary,
    WorkflowArtifact,
    WorkflowSummary,
    WorkflowTemplateSummary,
)
from system_operations_manager.services.kubernetes.base import K8sBaseManager

# Argo Workflows CRD coordinates
ARGO_WF_GROUP = "argoproj.io"
ARGO_WF_VERSION = "v1alpha1"
WORKFLOW_PLURAL = "workflows"
WORKFLOW_TEMPLATE_PLURAL = "workflowtemplates"
CRON_WORKFLOW_PLURAL = "cronworkflows"


class WorkflowsManager(K8sBaseManager):
    """Manager for Argo Workflows resources.

    Provides CRUD operations for Workflows, WorkflowTemplates,
    and CronWorkflows. Includes log retrieval and artifact listing.
    All CRD resources are accessed via ``CustomObjectsApi``.
    """

    _entity_name = "argo_workflows"

    # =========================================================================
    # Workflow Operations
    # =========================================================================

    def list_workflows(
        self,
        namespace: str | None = None,
        *,
        label_selector: str | None = None,
        phase: str | None = None,
    ) -> list[WorkflowSummary]:
        """List Argo Workflows in a namespace.

        Args:
            namespace: Target namespace.
            label_selector: Filter by label selector.
            phase: Filter by workflow phase.

        Returns:
            List of workflow summaries.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_workflows", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            result = self._client.custom_objects.list_namespaced_custom_object(
                ARGO_WF_GROUP,
                ARGO_WF_VERSION,
                ns,
                WORKFLOW_PLURAL,
                **kwargs,
            )
            items: list[dict[str, Any]] = result.get("items", [])
            workflows = [WorkflowSummary.from_k8s_object(item) for item in items]

            # Client-side phase filter
            if phase:
                workflows = [w for w in workflows if w.phase.lower() == phase.lower()]

            self._log.debug("listed_workflows", count=len(workflows), namespace=ns)
            return workflows
        except Exception as e:
            self._handle_api_error(e, "Workflow", None, ns)

    def get_workflow(self, name: str, namespace: str | None = None) -> WorkflowSummary:
        """Get a single Workflow by name."""
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_workflow", name=name, namespace=ns)
        try:
            result = self._client.custom_objects.get_namespaced_custom_object(
                ARGO_WF_GROUP,
                ARGO_WF_VERSION,
                ns,
                WORKFLOW_PLURAL,
                name,
            )
            return WorkflowSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Workflow", name, ns)

    def create_workflow(
        self,
        name: str,
        namespace: str | None = None,
        *,
        template_ref: str | None = None,
        arguments: dict[str, str] | None = None,
        labels: dict[str, str] | None = None,
    ) -> WorkflowSummary:
        """Create a new Workflow.

        Args:
            name: Workflow name.
            namespace: Target namespace.
            template_ref: WorkflowTemplate name to reference.
            arguments: Workflow arguments as key-value pairs.
            labels: Optional labels.

        Returns:
            Created workflow summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("creating_workflow", name=name, namespace=ns)

        body: dict[str, Any] = {
            "apiVersion": f"{ARGO_WF_GROUP}/{ARGO_WF_VERSION}",
            "kind": "Workflow",
            "metadata": {
                "name": name,
                "namespace": ns,
                "labels": labels or {},
            },
            "spec": {},
        }

        if template_ref:
            body["spec"]["workflowTemplateRef"] = {"name": template_ref}

        if arguments:
            body["spec"]["arguments"] = {
                "parameters": [{"name": k, "value": v} for k, v in arguments.items()],
            }

        try:
            result = self._client.custom_objects.create_namespaced_custom_object(
                ARGO_WF_GROUP,
                ARGO_WF_VERSION,
                ns,
                WORKFLOW_PLURAL,
                body,
            )
            self._log.info("created_workflow", name=name, namespace=ns)
            return WorkflowSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Workflow", name, ns)

    def delete_workflow(self, name: str, namespace: str | None = None) -> None:
        """Delete a Workflow."""
        ns = self._resolve_namespace(namespace)
        self._log.debug("deleting_workflow", name=name, namespace=ns)
        try:
            self._client.custom_objects.delete_namespaced_custom_object(
                ARGO_WF_GROUP,
                ARGO_WF_VERSION,
                ns,
                WORKFLOW_PLURAL,
                name,
            )
            self._log.info("deleted_workflow", name=name, namespace=ns)
        except Exception as e:
            self._handle_api_error(e, "Workflow", name, ns)

    def get_workflow_logs(
        self,
        name: str,
        namespace: str | None = None,
        *,
        container: str = "main",
        follow: bool = False,
    ) -> str | Iterator[str]:
        """Get logs for a Workflow's pods.

        Args:
            name: Workflow name.
            namespace: Target namespace.
            container: Container name within pods (default: main).
            follow: Whether to stream logs in real-time.

        Returns:
            Log text (static) or iterator of log lines (streaming).
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_workflow_logs", name=name, namespace=ns, follow=follow)
        try:
            # Get workflow to find its pods via status.nodes
            wf = self._client.custom_objects.get_namespaced_custom_object(
                ARGO_WF_GROUP,
                ARGO_WF_VERSION,
                ns,
                WORKFLOW_PLURAL,
                name,
            )
            status: dict[str, Any] = wf.get("status", {})
            nodes: dict[str, Any] = status.get("nodes", {})

            # Collect pod names from workflow nodes
            pod_names: list[str] = []
            for node_info in nodes.values():
                if node_info.get("type") == "Pod":
                    pod_name = node_info.get("id", "")
                    if pod_name:
                        pod_names.append(pod_name)

            if not pod_names:
                return "No pods found for this workflow."

            if follow:
                return self._stream_pod_logs(pod_names[-1], ns, container)

            # Collect logs from all pods
            all_logs: list[str] = []
            for pod_name in pod_names:
                try:
                    log = self._client.core_v1.read_namespaced_pod_log(
                        name=pod_name,
                        namespace=ns,
                        container=container,
                    )
                    all_logs.append(f"=== Pod: {pod_name} ===\n{log}")
                except Exception:
                    all_logs.append(f"=== Pod: {pod_name} ===\n(logs unavailable)")

            return "\n\n".join(all_logs)
        except Exception as e:
            self._handle_api_error(e, "Workflow", name, ns)

    def _stream_pod_logs(
        self,
        pod_name: str,
        namespace: str,
        container: str,
    ) -> Iterator[str]:
        """Stream logs from a pod."""
        stream = self._client.core_v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            container=container,
            follow=True,
            _preload_content=False,
        )
        for line in stream:
            if isinstance(line, bytes):
                yield line.decode("utf-8", errors="replace")
            else:
                yield str(line)

    # =========================================================================
    # WorkflowTemplate Operations
    # =========================================================================

    def list_workflow_templates(
        self,
        namespace: str | None = None,
        *,
        label_selector: str | None = None,
    ) -> list[WorkflowTemplateSummary]:
        """List WorkflowTemplates in a namespace."""
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_workflow_templates", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector
            result = self._client.custom_objects.list_namespaced_custom_object(
                ARGO_WF_GROUP,
                ARGO_WF_VERSION,
                ns,
                WORKFLOW_TEMPLATE_PLURAL,
                **kwargs,
            )
            items: list[dict[str, Any]] = result.get("items", [])
            templates = [WorkflowTemplateSummary.from_k8s_object(item) for item in items]
            self._log.debug("listed_workflow_templates", count=len(templates), namespace=ns)
            return templates
        except Exception as e:
            self._handle_api_error(e, "WorkflowTemplate", None, ns)

    def get_workflow_template(
        self, name: str, namespace: str | None = None
    ) -> WorkflowTemplateSummary:
        """Get a single WorkflowTemplate by name."""
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_workflow_template", name=name, namespace=ns)
        try:
            result = self._client.custom_objects.get_namespaced_custom_object(
                ARGO_WF_GROUP,
                ARGO_WF_VERSION,
                ns,
                WORKFLOW_TEMPLATE_PLURAL,
                name,
            )
            return WorkflowTemplateSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "WorkflowTemplate", name, ns)

    def create_workflow_template(
        self,
        name: str,
        namespace: str | None = None,
        *,
        spec: dict[str, Any],
        labels: dict[str, str] | None = None,
    ) -> WorkflowTemplateSummary:
        """Create a new WorkflowTemplate.

        Args:
            name: Template name.
            namespace: Target namespace.
            spec: Full template spec dict.
            labels: Optional labels.

        Returns:
            Created template summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("creating_workflow_template", name=name, namespace=ns)
        body: dict[str, Any] = {
            "apiVersion": f"{ARGO_WF_GROUP}/{ARGO_WF_VERSION}",
            "kind": "WorkflowTemplate",
            "metadata": {
                "name": name,
                "namespace": ns,
                "labels": labels or {},
            },
            "spec": spec,
        }
        try:
            result = self._client.custom_objects.create_namespaced_custom_object(
                ARGO_WF_GROUP,
                ARGO_WF_VERSION,
                ns,
                WORKFLOW_TEMPLATE_PLURAL,
                body,
            )
            self._log.info("created_workflow_template", name=name, namespace=ns)
            return WorkflowTemplateSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "WorkflowTemplate", name, ns)

    def delete_workflow_template(self, name: str, namespace: str | None = None) -> None:
        """Delete a WorkflowTemplate."""
        ns = self._resolve_namespace(namespace)
        self._log.debug("deleting_workflow_template", name=name, namespace=ns)
        try:
            self._client.custom_objects.delete_namespaced_custom_object(
                ARGO_WF_GROUP,
                ARGO_WF_VERSION,
                ns,
                WORKFLOW_TEMPLATE_PLURAL,
                name,
            )
            self._log.info("deleted_workflow_template", name=name, namespace=ns)
        except Exception as e:
            self._handle_api_error(e, "WorkflowTemplate", name, ns)

    # =========================================================================
    # CronWorkflow Operations
    # =========================================================================

    def list_cron_workflows(
        self,
        namespace: str | None = None,
        *,
        label_selector: str | None = None,
    ) -> list[CronWorkflowSummary]:
        """List CronWorkflows in a namespace."""
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_cron_workflows", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector
            result = self._client.custom_objects.list_namespaced_custom_object(
                ARGO_WF_GROUP,
                ARGO_WF_VERSION,
                ns,
                CRON_WORKFLOW_PLURAL,
                **kwargs,
            )
            items: list[dict[str, Any]] = result.get("items", [])
            crons = [CronWorkflowSummary.from_k8s_object(item) for item in items]
            self._log.debug("listed_cron_workflows", count=len(crons), namespace=ns)
            return crons
        except Exception as e:
            self._handle_api_error(e, "CronWorkflow", None, ns)

    def get_cron_workflow(self, name: str, namespace: str | None = None) -> CronWorkflowSummary:
        """Get a single CronWorkflow by name."""
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_cron_workflow", name=name, namespace=ns)
        try:
            result = self._client.custom_objects.get_namespaced_custom_object(
                ARGO_WF_GROUP,
                ARGO_WF_VERSION,
                ns,
                CRON_WORKFLOW_PLURAL,
                name,
            )
            return CronWorkflowSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "CronWorkflow", name, ns)

    def create_cron_workflow(
        self,
        name: str,
        namespace: str | None = None,
        *,
        schedule: str,
        template_ref: str,
        timezone: str = "",
        concurrency_policy: str = "Allow",
        labels: dict[str, str] | None = None,
    ) -> CronWorkflowSummary:
        """Create a new CronWorkflow.

        Args:
            name: CronWorkflow name.
            namespace: Target namespace.
            schedule: Cron schedule expression.
            template_ref: WorkflowTemplate name to reference.
            timezone: Timezone for schedule.
            concurrency_policy: Allow, Forbid, or Replace.
            labels: Optional labels.

        Returns:
            Created CronWorkflow summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("creating_cron_workflow", name=name, namespace=ns)
        body: dict[str, Any] = {
            "apiVersion": f"{ARGO_WF_GROUP}/{ARGO_WF_VERSION}",
            "kind": "CronWorkflow",
            "metadata": {
                "name": name,
                "namespace": ns,
                "labels": labels or {},
            },
            "spec": {
                "schedule": schedule,
                "timezone": timezone,
                "concurrencyPolicy": concurrency_policy,
                "workflowSpec": {
                    "workflowTemplateRef": {"name": template_ref},
                },
            },
        }
        try:
            result = self._client.custom_objects.create_namespaced_custom_object(
                ARGO_WF_GROUP,
                ARGO_WF_VERSION,
                ns,
                CRON_WORKFLOW_PLURAL,
                body,
            )
            self._log.info("created_cron_workflow", name=name, namespace=ns)
            return CronWorkflowSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "CronWorkflow", name, ns)

    def delete_cron_workflow(self, name: str, namespace: str | None = None) -> None:
        """Delete a CronWorkflow."""
        ns = self._resolve_namespace(namespace)
        self._log.debug("deleting_cron_workflow", name=name, namespace=ns)
        try:
            self._client.custom_objects.delete_namespaced_custom_object(
                ARGO_WF_GROUP,
                ARGO_WF_VERSION,
                ns,
                CRON_WORKFLOW_PLURAL,
                name,
            )
            self._log.info("deleted_cron_workflow", name=name, namespace=ns)
        except Exception as e:
            self._handle_api_error(e, "CronWorkflow", name, ns)

    def suspend_cron_workflow(self, name: str, namespace: str | None = None) -> CronWorkflowSummary:
        """Suspend a CronWorkflow."""
        ns = self._resolve_namespace(namespace)
        self._log.debug("suspending_cron_workflow", name=name, namespace=ns)
        try:
            patch: dict[str, Any] = {"spec": {"suspend": True}}
            result = self._client.custom_objects.patch_namespaced_custom_object(
                ARGO_WF_GROUP,
                ARGO_WF_VERSION,
                ns,
                CRON_WORKFLOW_PLURAL,
                name,
                patch,
            )
            self._log.info("suspended_cron_workflow", name=name, namespace=ns)
            return CronWorkflowSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "CronWorkflow", name, ns)

    def resume_cron_workflow(self, name: str, namespace: str | None = None) -> CronWorkflowSummary:
        """Resume a suspended CronWorkflow."""
        ns = self._resolve_namespace(namespace)
        self._log.debug("resuming_cron_workflow", name=name, namespace=ns)
        try:
            patch: dict[str, Any] = {"spec": {"suspend": False}}
            result = self._client.custom_objects.patch_namespaced_custom_object(
                ARGO_WF_GROUP,
                ARGO_WF_VERSION,
                ns,
                CRON_WORKFLOW_PLURAL,
                name,
                patch,
            )
            self._log.info("resumed_cron_workflow", name=name, namespace=ns)
            return CronWorkflowSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "CronWorkflow", name, ns)

    # =========================================================================
    # Artifact Operations
    # =========================================================================

    def list_workflow_artifacts(
        self, name: str, namespace: str | None = None
    ) -> list[WorkflowArtifact]:
        """List artifacts from a completed Workflow.

        Reads from ``.status.nodes[*].outputs.artifacts``.

        Args:
            name: Workflow name.
            namespace: Target namespace.

        Returns:
            List of workflow artifacts.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_workflow_artifacts", name=name, namespace=ns)
        try:
            result = self._client.custom_objects.get_namespaced_custom_object(
                ARGO_WF_GROUP,
                ARGO_WF_VERSION,
                ns,
                WORKFLOW_PLURAL,
                name,
            )
            status: dict[str, Any] = result.get("status", {})
            nodes: dict[str, Any] = status.get("nodes", {})

            artifacts: list[WorkflowArtifact] = []
            for node_id, node_info in nodes.items():
                outputs: dict[str, Any] = node_info.get("outputs", {})
                for artifact in outputs.get("artifacts", []):
                    artifacts.append(WorkflowArtifact.from_k8s_object(artifact, node_id=node_id))

            self._log.debug("listed_workflow_artifacts", count=len(artifacts), name=name)
            return artifacts
        except Exception as e:
            self._handle_api_error(e, "Workflow", name, ns)
