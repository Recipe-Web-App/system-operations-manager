"""Kubernetes job resource manager.

Manages Jobs and CronJobs through the Kubernetes API,
including suspend/resume operations for CronJobs.
"""

from __future__ import annotations

from typing import Any

from system_operations_manager.integrations.kubernetes.models.jobs import (
    CronJobSummary,
    JobSummary,
)
from system_operations_manager.services.kubernetes.base import K8sBaseManager


class JobManager(K8sBaseManager):
    """Manager for Kubernetes job resources.

    Provides CRUD operations for Jobs and CronJobs,
    plus suspend/resume for CronJobs.
    """

    _entity_name = "job"

    # =========================================================================
    # Job Operations
    # =========================================================================

    def list_jobs(
        self,
        namespace: str | None = None,
        *,
        all_namespaces: bool = False,
        label_selector: str | None = None,
    ) -> list[JobSummary]:
        """List jobs.

        Args:
            namespace: Target namespace.
            all_namespaces: List across all namespaces.
            label_selector: Filter by label selector.

        Returns:
            List of job summaries.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_jobs", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            if all_namespaces:
                result = self._client.batch_v1.list_job_for_all_namespaces(**kwargs)
            else:
                result = self._client.batch_v1.list_namespaced_job(namespace=ns, **kwargs)

            items = [JobSummary.from_k8s_object(j) for j in result.items]
            self._log.debug("listed_jobs", count=len(items))
            return items
        except Exception as e:
            self._handle_api_error(e, "Job", None, ns)

    def get_job(self, name: str, namespace: str | None = None) -> JobSummary:
        """Get a single job by name.

        Args:
            name: Job name.
            namespace: Target namespace.

        Returns:
            Job summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_job", name=name, namespace=ns)
        try:
            result = self._client.batch_v1.read_namespaced_job(name=name, namespace=ns)
            return JobSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Job", name, ns)

    def create_job(
        self,
        name: str,
        namespace: str | None = None,
        *,
        image: str,
        command: list[str] | None = None,
        completions: int = 1,
        parallelism: int = 1,
        labels: dict[str, str] | None = None,
    ) -> JobSummary:
        """Create a job.

        Args:
            name: Job name.
            namespace: Target namespace.
            image: Container image.
            command: Container command.
            completions: Number of successful completions needed.
            parallelism: Number of pods to run in parallel.
            labels: Job labels.

        Returns:
            Created job summary.
        """
        from kubernetes.client import (
            V1Container,
            V1Job,
            V1JobSpec,
            V1ObjectMeta,
            V1PodSpec,
            V1PodTemplateSpec,
        )

        ns = self._resolve_namespace(namespace)
        pod_labels = labels or {"job-name": name}

        container = V1Container(
            name=name,
            image=image,
            command=command,
        )

        body = V1Job(
            metadata=V1ObjectMeta(name=name, namespace=ns, labels=pod_labels),
            spec=V1JobSpec(
                completions=completions,
                parallelism=parallelism,
                template=V1PodTemplateSpec(
                    metadata=V1ObjectMeta(labels=pod_labels),
                    spec=V1PodSpec(
                        containers=[container],
                        restart_policy="Never",
                    ),
                ),
            ),
        )

        self._log.info("creating_job", name=name, namespace=ns, image=image)
        try:
            result = self._client.batch_v1.create_namespaced_job(namespace=ns, body=body)
            self._log.info("created_job", name=name, namespace=ns)
            return JobSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Job", name, ns)

    def delete_job(
        self,
        name: str,
        namespace: str | None = None,
        *,
        propagation_policy: str = "Background",
    ) -> None:
        """Delete a job.

        Args:
            name: Job name.
            namespace: Target namespace.
            propagation_policy: Deletion propagation (Background, Foreground, Orphan).
        """
        from kubernetes.client import V1DeleteOptions

        ns = self._resolve_namespace(namespace)
        self._log.info("deleting_job", name=name, namespace=ns)
        try:
            self._client.batch_v1.delete_namespaced_job(
                name=name,
                namespace=ns,
                body=V1DeleteOptions(propagation_policy=propagation_policy),
            )
            self._log.info("deleted_job", name=name, namespace=ns)
        except Exception as e:
            self._handle_api_error(e, "Job", name, ns)

    # =========================================================================
    # CronJob Operations
    # =========================================================================

    def list_cron_jobs(
        self,
        namespace: str | None = None,
        *,
        all_namespaces: bool = False,
        label_selector: str | None = None,
    ) -> list[CronJobSummary]:
        """List cronjobs.

        Args:
            namespace: Target namespace.
            all_namespaces: List across all namespaces.
            label_selector: Filter by label selector.

        Returns:
            List of cronjob summaries.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_cronjobs", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            if all_namespaces:
                result = self._client.batch_v1.list_cron_job_for_all_namespaces(**kwargs)
            else:
                result = self._client.batch_v1.list_namespaced_cron_job(namespace=ns, **kwargs)

            items = [CronJobSummary.from_k8s_object(cj) for cj in result.items]
            self._log.debug("listed_cronjobs", count=len(items))
            return items
        except Exception as e:
            self._handle_api_error(e, "CronJob", None, ns)

    def get_cron_job(self, name: str, namespace: str | None = None) -> CronJobSummary:
        """Get a single cronjob by name.

        Args:
            name: CronJob name.
            namespace: Target namespace.

        Returns:
            CronJob summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_cronjob", name=name, namespace=ns)
        try:
            result = self._client.batch_v1.read_namespaced_cron_job(name=name, namespace=ns)
            return CronJobSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "CronJob", name, ns)

    def create_cron_job(
        self,
        name: str,
        namespace: str | None = None,
        *,
        image: str,
        command: list[str] | None = None,
        schedule: str,
        labels: dict[str, str] | None = None,
    ) -> CronJobSummary:
        """Create a cronjob.

        Args:
            name: CronJob name.
            namespace: Target namespace.
            image: Container image.
            command: Container command.
            schedule: Cron schedule expression (e.g., '*/5 * * * *').
            labels: CronJob labels.

        Returns:
            Created cronjob summary.
        """
        from kubernetes.client import (
            V1Container,
            V1CronJob,
            V1CronJobSpec,
            V1JobSpec,
            V1JobTemplateSpec,
            V1ObjectMeta,
            V1PodSpec,
            V1PodTemplateSpec,
        )

        ns = self._resolve_namespace(namespace)
        pod_labels = labels or {"cronjob-name": name}

        container = V1Container(
            name=name,
            image=image,
            command=command,
        )

        body = V1CronJob(
            metadata=V1ObjectMeta(name=name, namespace=ns, labels=pod_labels),
            spec=V1CronJobSpec(
                schedule=schedule,
                job_template=V1JobTemplateSpec(
                    spec=V1JobSpec(
                        template=V1PodTemplateSpec(
                            metadata=V1ObjectMeta(labels=pod_labels),
                            spec=V1PodSpec(
                                containers=[container],
                                restart_policy="Never",
                            ),
                        ),
                    ),
                ),
            ),
        )

        self._log.info("creating_cronjob", name=name, namespace=ns, schedule=schedule)
        try:
            result = self._client.batch_v1.create_namespaced_cron_job(namespace=ns, body=body)
            self._log.info("created_cronjob", name=name, namespace=ns)
            return CronJobSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "CronJob", name, ns)

    def update_cron_job(
        self,
        name: str,
        namespace: str | None = None,
        *,
        schedule: str | None = None,
        suspend: bool | None = None,
    ) -> CronJobSummary:
        """Update a cronjob (patch).

        Args:
            name: CronJob name.
            namespace: Target namespace.
            schedule: New cron schedule.
            suspend: Whether to suspend the cronjob.

        Returns:
            Updated cronjob summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info("updating_cronjob", name=name, namespace=ns)
        try:
            patch: dict[str, Any] = {"spec": {}}
            if schedule is not None:
                patch["spec"]["schedule"] = schedule
            if suspend is not None:
                patch["spec"]["suspend"] = suspend

            result = self._client.batch_v1.patch_namespaced_cron_job(
                name=name, namespace=ns, body=patch
            )
            self._log.info("updated_cronjob", name=name, namespace=ns)
            return CronJobSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "CronJob", name, ns)

    def delete_cron_job(self, name: str, namespace: str | None = None) -> None:
        """Delete a cronjob.

        Args:
            name: CronJob name.
            namespace: Target namespace.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info("deleting_cronjob", name=name, namespace=ns)
        try:
            self._client.batch_v1.delete_namespaced_cron_job(name=name, namespace=ns)
            self._log.info("deleted_cronjob", name=name, namespace=ns)
        except Exception as e:
            self._handle_api_error(e, "CronJob", name, ns)

    def suspend_cron_job(self, name: str, namespace: str | None = None) -> CronJobSummary:
        """Suspend a cronjob.

        Args:
            name: CronJob name.
            namespace: Target namespace.

        Returns:
            Updated cronjob summary.
        """
        self._log.info("suspending_cronjob", name=name)
        return self.update_cron_job(name, namespace, suspend=True)

    def resume_cron_job(self, name: str, namespace: str | None = None) -> CronJobSummary:
        """Resume a suspended cronjob.

        Args:
            name: CronJob name.
            namespace: Target namespace.

        Returns:
            Updated cronjob summary.
        """
        self._log.info("resuming_cronjob", name=name)
        return self.update_cron_job(name, namespace, suspend=False)
