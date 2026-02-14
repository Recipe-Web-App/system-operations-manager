"""Argo Rollouts resource manager.

Manages Argo Rollouts, AnalysisTemplates, and AnalysisRuns
through the Kubernetes ``CustomObjectsApi``.
"""

from __future__ import annotations

import json
from typing import Any

from system_operations_manager.integrations.kubernetes.models.argo_rollouts import (
    AnalysisRunSummary,
    AnalysisTemplateSummary,
    RolloutSummary,
)
from system_operations_manager.services.kubernetes.base import K8sBaseManager

# Argo Rollouts CRD coordinates
ARGO_ROLLOUTS_GROUP = "argoproj.io"
ARGO_ROLLOUTS_VERSION = "v1alpha1"
ROLLOUT_PLURAL = "rollouts"
ANALYSIS_TEMPLATE_PLURAL = "analysistemplates"
ANALYSIS_RUN_PLURAL = "analysisruns"


class RolloutsManager(K8sBaseManager):
    """Manager for Argo Rollouts resources.

    Provides CRUD operations for Rollouts, AnalysisTemplates,
    and AnalysisRuns. Includes promote, abort, and retry operations.
    All CRD resources are accessed via ``CustomObjectsApi``.
    """

    _entity_name = "argo_rollouts"

    # =========================================================================
    # Rollout Operations
    # =========================================================================

    def list_rollouts(
        self,
        namespace: str | None = None,
        *,
        label_selector: str | None = None,
    ) -> list[RolloutSummary]:
        """List Argo Rollouts in a namespace.

        Args:
            namespace: Target namespace.
            label_selector: Filter by label selector.

        Returns:
            List of rollout summaries.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_rollouts", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector
            result = self._client.custom_objects.list_namespaced_custom_object(
                ARGO_ROLLOUTS_GROUP,
                ARGO_ROLLOUTS_VERSION,
                ns,
                ROLLOUT_PLURAL,
                **kwargs,
            )
            items: list[dict[str, Any]] = result.get("items", [])
            rollouts = [RolloutSummary.from_k8s_object(item) for item in items]
            self._log.debug("listed_rollouts", count=len(rollouts), namespace=ns)
            return rollouts
        except Exception as e:
            self._handle_api_error(e, "Rollout", None, ns)

    def get_rollout(self, name: str, namespace: str | None = None) -> RolloutSummary:
        """Get a single Rollout by name.

        Args:
            name: Rollout name.
            namespace: Target namespace.

        Returns:
            Rollout summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_rollout", name=name, namespace=ns)
        try:
            result = self._client.custom_objects.get_namespaced_custom_object(
                ARGO_ROLLOUTS_GROUP,
                ARGO_ROLLOUTS_VERSION,
                ns,
                ROLLOUT_PLURAL,
                name,
            )
            return RolloutSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Rollout", name, ns)

    def create_rollout(
        self,
        name: str,
        namespace: str | None = None,
        *,
        image: str,
        replicas: int = 1,
        strategy: str = "canary",
        canary_steps: list[dict[str, Any]] | None = None,
        labels: dict[str, str] | None = None,
    ) -> RolloutSummary:
        """Create a new Argo Rollout.

        Args:
            name: Rollout name.
            namespace: Target namespace.
            image: Container image.
            replicas: Number of replicas.
            strategy: Deployment strategy (canary or blueGreen).
            canary_steps: List of canary step configurations.
            labels: Optional labels.

        Returns:
            Created rollout summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("creating_rollout", name=name, namespace=ns)

        strategy_spec: dict[str, Any] = {}
        if strategy == "canary":
            canary_config: dict[str, Any] = {}
            if canary_steps:
                canary_config["steps"] = canary_steps
            strategy_spec["canary"] = canary_config
        elif strategy == "blueGreen":
            strategy_spec["blueGreen"] = {
                "activeService": f"{name}-active",
                "previewService": f"{name}-preview",
            }

        app_labels = {"app": name}
        if labels:
            app_labels.update(labels)

        body: dict[str, Any] = {
            "apiVersion": f"{ARGO_ROLLOUTS_GROUP}/{ARGO_ROLLOUTS_VERSION}",
            "kind": "Rollout",
            "metadata": {
                "name": name,
                "namespace": ns,
                "labels": app_labels,
            },
            "spec": {
                "replicas": replicas,
                "strategy": strategy_spec,
                "selector": {"matchLabels": {"app": name}},
                "template": {
                    "metadata": {"labels": {"app": name}},
                    "spec": {
                        "containers": [{"name": name, "image": image}],
                    },
                },
            },
        }
        try:
            result = self._client.custom_objects.create_namespaced_custom_object(
                ARGO_ROLLOUTS_GROUP,
                ARGO_ROLLOUTS_VERSION,
                ns,
                ROLLOUT_PLURAL,
                body,
            )
            self._log.info("created_rollout", name=name, namespace=ns)
            return RolloutSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Rollout", name, ns)

    def delete_rollout(self, name: str, namespace: str | None = None) -> None:
        """Delete a Rollout.

        Args:
            name: Rollout name to delete.
            namespace: Target namespace.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("deleting_rollout", name=name, namespace=ns)
        try:
            self._client.custom_objects.delete_namespaced_custom_object(
                ARGO_ROLLOUTS_GROUP,
                ARGO_ROLLOUTS_VERSION,
                ns,
                ROLLOUT_PLURAL,
                name,
            )
            self._log.info("deleted_rollout", name=name, namespace=ns)
        except Exception as e:
            self._handle_api_error(e, "Rollout", name, ns)

    def get_rollout_status(self, name: str, namespace: str | None = None) -> dict[str, Any]:
        """Get detailed status for a Rollout.

        Returns more detailed status information than the summary model,
        including steps and conditions.

        Args:
            name: Rollout name.
            namespace: Target namespace.

        Returns:
            Dict with detailed status information.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_rollout_status", name=name, namespace=ns)
        try:
            result = self._client.custom_objects.get_namespaced_custom_object(
                ARGO_ROLLOUTS_GROUP,
                ARGO_ROLLOUTS_VERSION,
                ns,
                ROLLOUT_PLURAL,
                name,
            )
            spec: dict[str, Any] = result.get("spec", {})
            status: dict[str, Any] = result.get("status", {})
            canary: dict[str, Any] = status.get("canary", {})

            # Extract steps from canary strategy
            strategy_spec: dict[str, Any] = spec.get("strategy", {})
            steps: list[dict[str, Any]] = strategy_spec.get("canary", {}).get("steps", [])

            return {
                "name": name,
                "namespace": ns,
                "phase": status.get("phase", "Unknown"),
                "message": status.get("message"),
                "replicas": spec.get("replicas", 0),
                "ready_replicas": status.get("readyReplicas", 0),
                "current_step_index": status.get("currentStepIndex"),
                "total_steps": len(steps),
                "canary_weight": canary.get("weight", 0),
                "stable_rs": status.get("stableRS", ""),
                "canary_rs": status.get("currentPodHash", ""),
                "conditions": status.get("conditions", []),
            }
        except Exception as e:
            self._handle_api_error(e, "Rollout", name, ns)

    def promote_rollout(
        self,
        name: str,
        namespace: str | None = None,
        *,
        full: bool = False,
    ) -> RolloutSummary:
        """Promote a Rollout (advance canary or activate blue-green).

        Patches the Rollout with the promote annotation.

        Args:
            name: Rollout name.
            namespace: Target namespace.
            full: Whether to do a full promotion (skip remaining steps).

        Returns:
            Updated rollout summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("promoting_rollout", name=name, namespace=ns, full=full)
        try:
            promote_value = "full" if full else "true"
            patch: dict[str, Any] = {
                "metadata": {
                    "annotations": {
                        "rollout.argoproj.io/promote": promote_value,
                    },
                },
            }
            result = self._client.custom_objects.patch_namespaced_custom_object(
                ARGO_ROLLOUTS_GROUP,
                ARGO_ROLLOUTS_VERSION,
                ns,
                ROLLOUT_PLURAL,
                name,
                patch,
            )
            self._log.info("promoted_rollout", name=name, namespace=ns, full=full)
            return RolloutSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Rollout", name, ns)

    def abort_rollout(self, name: str, namespace: str | None = None) -> RolloutSummary:
        """Abort a Rollout in progress.

        Patches the Rollout with the abort annotation.

        Args:
            name: Rollout name.
            namespace: Target namespace.

        Returns:
            Updated rollout summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("aborting_rollout", name=name, namespace=ns)
        try:
            patch: dict[str, Any] = {
                "metadata": {
                    "annotations": {
                        "rollout.argoproj.io/abort": "true",
                    },
                },
            }
            result = self._client.custom_objects.patch_namespaced_custom_object(
                ARGO_ROLLOUTS_GROUP,
                ARGO_ROLLOUTS_VERSION,
                ns,
                ROLLOUT_PLURAL,
                name,
                patch,
            )
            self._log.info("aborted_rollout", name=name, namespace=ns)
            return RolloutSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Rollout", name, ns)

    def retry_rollout(self, name: str, namespace: str | None = None) -> RolloutSummary:
        """Retry a failed/aborted Rollout.

        Removes the abort annotation and restarts.

        Args:
            name: Rollout name.
            namespace: Target namespace.

        Returns:
            Updated rollout summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("retrying_rollout", name=name, namespace=ns)
        try:
            # Remove abort annotation by setting to null via JSON merge patch
            patch = json.dumps(
                {
                    "metadata": {
                        "annotations": {
                            "rollout.argoproj.io/abort": None,
                        },
                    },
                    "status": {
                        "abort": False,
                    },
                }
            )
            result = self._client.custom_objects.patch_namespaced_custom_object(
                ARGO_ROLLOUTS_GROUP,
                ARGO_ROLLOUTS_VERSION,
                ns,
                ROLLOUT_PLURAL,
                name,
                json.loads(patch),
            )
            self._log.info("retried_rollout", name=name, namespace=ns)
            return RolloutSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Rollout", name, ns)

    # =========================================================================
    # AnalysisTemplate Operations
    # =========================================================================

    def list_analysis_templates(
        self,
        namespace: str | None = None,
        *,
        label_selector: str | None = None,
    ) -> list[AnalysisTemplateSummary]:
        """List AnalysisTemplates in a namespace.

        Args:
            namespace: Target namespace.
            label_selector: Filter by label selector.

        Returns:
            List of analysis template summaries.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_analysis_templates", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector
            result = self._client.custom_objects.list_namespaced_custom_object(
                ARGO_ROLLOUTS_GROUP,
                ARGO_ROLLOUTS_VERSION,
                ns,
                ANALYSIS_TEMPLATE_PLURAL,
                **kwargs,
            )
            items: list[dict[str, Any]] = result.get("items", [])
            templates = [AnalysisTemplateSummary.from_k8s_object(item) for item in items]
            self._log.debug("listed_analysis_templates", count=len(templates), namespace=ns)
            return templates
        except Exception as e:
            self._handle_api_error(e, "AnalysisTemplate", None, ns)

    def get_analysis_template(
        self, name: str, namespace: str | None = None
    ) -> AnalysisTemplateSummary:
        """Get a single AnalysisTemplate by name.

        Args:
            name: AnalysisTemplate name.
            namespace: Target namespace.

        Returns:
            Analysis template summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_analysis_template", name=name, namespace=ns)
        try:
            result = self._client.custom_objects.get_namespaced_custom_object(
                ARGO_ROLLOUTS_GROUP,
                ARGO_ROLLOUTS_VERSION,
                ns,
                ANALYSIS_TEMPLATE_PLURAL,
                name,
            )
            return AnalysisTemplateSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "AnalysisTemplate", name, ns)

    # =========================================================================
    # AnalysisRun Operations
    # =========================================================================

    def list_analysis_runs(
        self,
        namespace: str | None = None,
        *,
        label_selector: str | None = None,
    ) -> list[AnalysisRunSummary]:
        """List AnalysisRuns in a namespace.

        Args:
            namespace: Target namespace.
            label_selector: Filter by label selector.

        Returns:
            List of analysis run summaries.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_analysis_runs", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector
            result = self._client.custom_objects.list_namespaced_custom_object(
                ARGO_ROLLOUTS_GROUP,
                ARGO_ROLLOUTS_VERSION,
                ns,
                ANALYSIS_RUN_PLURAL,
                **kwargs,
            )
            items: list[dict[str, Any]] = result.get("items", [])
            runs = [AnalysisRunSummary.from_k8s_object(item) for item in items]
            self._log.debug("listed_analysis_runs", count=len(runs), namespace=ns)
            return runs
        except Exception as e:
            self._handle_api_error(e, "AnalysisRun", None, ns)

    def get_analysis_run(self, name: str, namespace: str | None = None) -> AnalysisRunSummary:
        """Get a single AnalysisRun by name.

        Args:
            name: AnalysisRun name.
            namespace: Target namespace.

        Returns:
            Analysis run summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_analysis_run", name=name, namespace=ns)
        try:
            result = self._client.custom_objects.get_namespaced_custom_object(
                ARGO_ROLLOUTS_GROUP,
                ARGO_ROLLOUTS_VERSION,
                ns,
                ANALYSIS_RUN_PLURAL,
                name,
            )
            return AnalysisRunSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "AnalysisRun", name, ns)
