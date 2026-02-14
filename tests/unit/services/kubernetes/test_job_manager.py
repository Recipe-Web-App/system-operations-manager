"""Unit tests for JobManager."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from system_operations_manager.services.kubernetes.job_manager import JobManager


@pytest.fixture
def mock_k8s_client() -> MagicMock:
    """Create a mock Kubernetes client."""
    mock_client = MagicMock()
    mock_client.default_namespace = "default"
    return mock_client


@pytest.fixture
def job_manager(mock_k8s_client: MagicMock) -> JobManager:
    """Create a JobManager instance with mocked client."""
    return JobManager(mock_k8s_client)


class TestJobOperations:
    """Tests for Job operations."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_jobs_success(self, job_manager: JobManager, mock_k8s_client: MagicMock) -> None:
        """Should list jobs successfully."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.batch_v1.list_namespaced_job.return_value = mock_response

        result = job_manager.list_jobs()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_jobs_empty(self, job_manager: JobManager, mock_k8s_client: MagicMock) -> None:
        """Should return empty list when no jobs exist."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.batch_v1.list_namespaced_job.return_value = mock_response

        result = job_manager.list_jobs()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_jobs_all_namespaces(
        self, job_manager: JobManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list jobs across all namespaces."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.batch_v1.list_job_for_all_namespaces.return_value = mock_response

        result = job_manager.list_jobs(all_namespaces=True)

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_jobs_error(self, job_manager: JobManager, mock_k8s_client: MagicMock) -> None:
        """Should handle API error when listing jobs."""
        mock_k8s_client.batch_v1.list_namespaced_job.side_effect = Exception("API error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            job_manager.list_jobs()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_job_success(self, job_manager: JobManager, mock_k8s_client: MagicMock) -> None:
        """Should get job successfully."""
        mock_job = MagicMock()
        mock_k8s_client.batch_v1.read_namespaced_job.return_value = mock_job

        with patch(
            "system_operations_manager.services.kubernetes.job_manager.JobSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = job_manager.get_job("test-job")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_job_error(self, job_manager: JobManager, mock_k8s_client: MagicMock) -> None:
        """Should handle API error when getting job."""
        mock_k8s_client.batch_v1.read_namespaced_job.side_effect = Exception("Not found")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            job_manager.get_job("test-job")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_job_success(self, job_manager: JobManager, mock_k8s_client: MagicMock) -> None:
        """Should create job successfully."""
        mock_job = MagicMock()
        mock_k8s_client.batch_v1.create_namespaced_job.return_value = mock_job

        with patch(
            "system_operations_manager.services.kubernetes.job_manager.JobSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = job_manager.create_job("test-job", image="busybox:latest")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_job_error(self, job_manager: JobManager, mock_k8s_client: MagicMock) -> None:
        """Should handle API error when creating job."""
        mock_k8s_client.batch_v1.create_namespaced_job.side_effect = Exception("Create error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            job_manager.create_job("test-job", image="busybox:latest")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_job_success(self, job_manager: JobManager, mock_k8s_client: MagicMock) -> None:
        """Should delete job successfully."""
        job_manager.delete_job("test-job")

        mock_k8s_client.batch_v1.delete_namespaced_job.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_job_error(self, job_manager: JobManager, mock_k8s_client: MagicMock) -> None:
        """Should handle API error when deleting job."""
        mock_k8s_client.batch_v1.delete_namespaced_job.side_effect = Exception("Delete error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            job_manager.delete_job("test-job")


class TestCronJobOperations:
    """Tests for CronJob operations."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_cron_jobs_success(
        self, job_manager: JobManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list cronjobs successfully."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.batch_v1.list_namespaced_cron_job.return_value = mock_response

        result = job_manager.list_cron_jobs()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_cron_jobs_empty(
        self, job_manager: JobManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should return empty list when no cronjobs exist."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.batch_v1.list_namespaced_cron_job.return_value = mock_response

        result = job_manager.list_cron_jobs()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_cron_jobs_error(
        self, job_manager: JobManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when listing cronjobs."""
        mock_k8s_client.batch_v1.list_namespaced_cron_job.side_effect = Exception("API error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            job_manager.list_cron_jobs()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_cron_job_success(
        self, job_manager: JobManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should get cronjob successfully."""
        mock_cronjob = MagicMock()
        mock_k8s_client.batch_v1.read_namespaced_cron_job.return_value = mock_cronjob

        with patch(
            "system_operations_manager.services.kubernetes.job_manager.CronJobSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = job_manager.get_cron_job("test-cronjob")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_cron_job_error(self, job_manager: JobManager, mock_k8s_client: MagicMock) -> None:
        """Should handle API error when getting cronjob."""
        mock_k8s_client.batch_v1.read_namespaced_cron_job.side_effect = Exception("Not found")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            job_manager.get_cron_job("test-cronjob")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_cron_job_success(
        self, job_manager: JobManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should create cronjob successfully."""
        mock_cronjob = MagicMock()
        mock_k8s_client.batch_v1.create_namespaced_cron_job.return_value = mock_cronjob

        with patch(
            "system_operations_manager.services.kubernetes.job_manager.CronJobSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = job_manager.create_cron_job(
                "test-cronjob", image="busybox:latest", schedule="*/5 * * * *"
            )

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_cron_job_error(
        self, job_manager: JobManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when creating cronjob."""
        mock_k8s_client.batch_v1.create_namespaced_cron_job.side_effect = Exception("Create error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            job_manager.create_cron_job("test-cronjob", image="busybox", schedule="*/5 * * * *")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_update_cron_job_success(
        self, job_manager: JobManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should update cronjob successfully."""
        mock_cronjob = MagicMock()
        mock_k8s_client.batch_v1.patch_namespaced_cron_job.return_value = mock_cronjob

        with patch(
            "system_operations_manager.services.kubernetes.job_manager.CronJobSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = job_manager.update_cron_job("test-cronjob", schedule="0 * * * *")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_update_cron_job_error(
        self, job_manager: JobManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when updating cronjob."""
        mock_k8s_client.batch_v1.patch_namespaced_cron_job.side_effect = Exception("Update error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            job_manager.update_cron_job("test-cronjob", schedule="0 * * * *")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_cron_job_success(
        self, job_manager: JobManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should delete cronjob successfully."""
        job_manager.delete_cron_job("test-cronjob")

        mock_k8s_client.batch_v1.delete_namespaced_cron_job.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_cron_job_error(
        self, job_manager: JobManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when deleting cronjob."""
        mock_k8s_client.batch_v1.delete_namespaced_cron_job.side_effect = Exception("Delete error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            job_manager.delete_cron_job("test-cronjob")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_suspend_cron_job_success(
        self, job_manager: JobManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should suspend cronjob successfully."""
        mock_cronjob = MagicMock()
        mock_k8s_client.batch_v1.patch_namespaced_cron_job.return_value = mock_cronjob

        with patch(
            "system_operations_manager.services.kubernetes.job_manager.CronJobSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = job_manager.suspend_cron_job("test-cronjob")

            assert result == mock_summary
            # Verify suspend=True was passed in the patch
            call_kwargs = mock_k8s_client.batch_v1.patch_namespaced_cron_job.call_args[1]
            assert call_kwargs["body"]["spec"]["suspend"] is True

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_suspend_cron_job_error(
        self, job_manager: JobManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when suspending cronjob."""
        mock_k8s_client.batch_v1.patch_namespaced_cron_job.side_effect = Exception("Suspend error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            job_manager.suspend_cron_job("test-cronjob")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_resume_cron_job_success(
        self, job_manager: JobManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should resume cronjob successfully."""
        mock_cronjob = MagicMock()
        mock_k8s_client.batch_v1.patch_namespaced_cron_job.return_value = mock_cronjob

        with patch(
            "system_operations_manager.services.kubernetes.job_manager.CronJobSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = job_manager.resume_cron_job("test-cronjob")

            assert result == mock_summary
            # Verify suspend=False was passed in the patch
            call_kwargs = mock_k8s_client.batch_v1.patch_namespaced_cron_job.call_args[1]
            assert call_kwargs["body"]["spec"]["suspend"] is False

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_resume_cron_job_error(
        self, job_manager: JobManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when resuming cronjob."""
        mock_k8s_client.batch_v1.patch_namespaced_cron_job.side_effect = Exception("Resume error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            job_manager.resume_cron_job("test-cronjob")
