"""Unit tests for RolloutsManager."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.services.kubernetes.rollouts_manager import (
    ANALYSIS_RUN_PLURAL,
    ANALYSIS_TEMPLATE_PLURAL,
    ARGO_ROLLOUTS_GROUP,
    ARGO_ROLLOUTS_VERSION,
    ROLLOUT_PLURAL,
    RolloutsManager,
)


@pytest.fixture
def mock_k8s_client() -> MagicMock:
    """Create a mock Kubernetes client."""
    mock_client = MagicMock()
    mock_client.default_namespace = "default"
    return mock_client


@pytest.fixture
def rollouts_manager(mock_k8s_client: MagicMock) -> RolloutsManager:
    """Create a RolloutsManager with mocked client."""
    return RolloutsManager(mock_k8s_client)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestRolloutsManager:
    """Tests for RolloutsManager."""

    # =========================================================================
    # Rollout Tests
    # =========================================================================

    def test_list_rollouts(
        self,
        rollouts_manager: RolloutsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_rollouts should call custom_objects API."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {
            "items": [
                {
                    "metadata": {"name": "my-rollout", "namespace": "default"},
                    "spec": {
                        "replicas": 3,
                        "strategy": {"canary": {}},
                        "template": {"spec": {"containers": [{"image": "nginx:1.21"}]}},
                    },
                    "status": {
                        "phase": "Healthy",
                        "readyReplicas": 3,
                        "availableReplicas": 3,
                        "canary": {"weight": 0},
                    },
                }
            ]
        }

        rollouts = rollouts_manager.list_rollouts()

        assert len(rollouts) == 1
        assert rollouts[0].name == "my-rollout"
        assert rollouts[0].strategy == "canary"
        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            ARGO_ROLLOUTS_GROUP,
            ARGO_ROLLOUTS_VERSION,
            "default",
            ROLLOUT_PLURAL,
        )

    def test_list_rollouts_with_namespace(
        self,
        rollouts_manager: RolloutsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_rollouts should use provided namespace."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

        rollouts_manager.list_rollouts(namespace="production")

        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            ARGO_ROLLOUTS_GROUP,
            ARGO_ROLLOUTS_VERSION,
            "production",
            ROLLOUT_PLURAL,
        )

    def test_list_rollouts_with_label_selector(
        self,
        rollouts_manager: RolloutsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_rollouts should pass label selector."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

        rollouts_manager.list_rollouts(label_selector="app=myapp")

        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            ARGO_ROLLOUTS_GROUP,
            ARGO_ROLLOUTS_VERSION,
            "default",
            ROLLOUT_PLURAL,
            label_selector="app=myapp",
        )

    def test_get_rollout(
        self,
        rollouts_manager: RolloutsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_rollout should retrieve rollout by name."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {
            "metadata": {"name": "my-rollout", "namespace": "default"},
            "spec": {
                "replicas": 3,
                "strategy": {"canary": {}},
                "template": {"spec": {"containers": [{"image": "nginx:1.21"}]}},
            },
            "status": {
                "phase": "Healthy",
                "readyReplicas": 3,
                "availableReplicas": 3,
                "canary": {"weight": 0},
            },
        }

        rollout = rollouts_manager.get_rollout("my-rollout")

        assert rollout.name == "my-rollout"
        assert rollout.image == "nginx:1.21"
        mock_k8s_client.custom_objects.get_namespaced_custom_object.assert_called_once_with(
            ARGO_ROLLOUTS_GROUP,
            ARGO_ROLLOUTS_VERSION,
            "default",
            ROLLOUT_PLURAL,
            "my-rollout",
        )

    def test_create_rollout(
        self,
        rollouts_manager: RolloutsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_rollout should create new rollout."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = {
            "metadata": {"name": "my-rollout", "namespace": "default"},
            "spec": {
                "replicas": 3,
                "strategy": {"canary": {}},
                "template": {"spec": {"containers": [{"image": "nginx:1.21"}]}},
            },
            "status": {},
        }

        rollout = rollouts_manager.create_rollout(
            "my-rollout",
            image="nginx:1.21",
            replicas=3,
        )

        assert rollout.name == "my-rollout"
        mock_k8s_client.custom_objects.create_namespaced_custom_object.assert_called_once()
        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        assert call_args.args[0] == ARGO_ROLLOUTS_GROUP
        assert call_args.args[1] == ARGO_ROLLOUTS_VERSION
        assert call_args.args[2] == "default"
        assert call_args.args[3] == ROLLOUT_PLURAL
        body = call_args.args[4]
        assert body["metadata"]["name"] == "my-rollout"
        assert body["spec"]["replicas"] == 3

    def test_create_rollout_with_bluegreen_strategy(
        self,
        rollouts_manager: RolloutsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_rollout should include blueGreen strategy when specified."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = {
            "metadata": {"name": "my-rollout", "namespace": "default"},
            "spec": {
                "replicas": 3,
                "strategy": {
                    "blueGreen": {
                        "activeService": "my-rollout-active",
                        "previewService": "my-rollout-preview",
                    }
                },
            },
            "status": {},
        }

        rollouts_manager.create_rollout(
            "my-rollout",
            image="nginx:1.21",
            strategy="blueGreen",
        )

        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args.args[4]
        assert "blueGreen" in body["spec"]["strategy"]
        assert body["spec"]["strategy"]["blueGreen"]["activeService"] == "my-rollout-active"

    def test_delete_rollout(
        self,
        rollouts_manager: RolloutsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """delete_rollout should delete rollout."""
        rollouts_manager.delete_rollout("my-rollout")

        mock_k8s_client.custom_objects.delete_namespaced_custom_object.assert_called_once_with(
            ARGO_ROLLOUTS_GROUP,
            ARGO_ROLLOUTS_VERSION,
            "default",
            ROLLOUT_PLURAL,
            "my-rollout",
        )

    def test_get_rollout_status(
        self,
        rollouts_manager: RolloutsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_rollout_status should return detailed status."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {
            "metadata": {"name": "my-rollout", "namespace": "default"},
            "spec": {
                "replicas": 3,
                "strategy": {"canary": {"steps": [{"setWeight": 20}, {"pause": {}}]}},
            },
            "status": {
                "phase": "Progressing",
                "message": "Rolling out",
                "readyReplicas": 2,
                "currentStepIndex": 0,
                "canary": {"weight": 20},
                "stableRS": "abc123",
                "currentPodHash": "def456",
                "conditions": [],
            },
        }

        status = rollouts_manager.get_rollout_status("my-rollout")

        assert status["name"] == "my-rollout"
        assert status["phase"] == "Progressing"
        assert status["current_step_index"] == 0
        assert status["total_steps"] == 2
        assert status["canary_weight"] == 20

    def test_promote_rollout(
        self,
        rollouts_manager: RolloutsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """promote_rollout should patch rollout with promote annotation."""
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.return_value = {
            "metadata": {
                "name": "my-rollout",
                "namespace": "default",
                "annotations": {"rollout.argoproj.io/promote": "true"},
            },
            "spec": {},
            "status": {},
        }

        rollouts_manager.promote_rollout("my-rollout")

        call_args = mock_k8s_client.custom_objects.patch_namespaced_custom_object.call_args
        assert call_args.args[0] == ARGO_ROLLOUTS_GROUP
        assert call_args.args[4] == "my-rollout"
        patch = call_args.args[5]
        assert patch["metadata"]["annotations"]["rollout.argoproj.io/promote"] == "true"

    def test_promote_rollout_full(
        self,
        rollouts_manager: RolloutsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """promote_rollout with full should use 'full' annotation value."""
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.return_value = {
            "metadata": {"name": "my-rollout", "namespace": "default"},
            "spec": {},
            "status": {},
        }

        rollouts_manager.promote_rollout("my-rollout", full=True)

        call_args = mock_k8s_client.custom_objects.patch_namespaced_custom_object.call_args
        patch = call_args.args[5]
        assert patch["metadata"]["annotations"]["rollout.argoproj.io/promote"] == "full"

    def test_abort_rollout(
        self,
        rollouts_manager: RolloutsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """abort_rollout should patch rollout with abort annotation."""
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.return_value = {
            "metadata": {
                "name": "my-rollout",
                "namespace": "default",
                "annotations": {"rollout.argoproj.io/abort": "true"},
            },
            "spec": {},
            "status": {},
        }

        rollouts_manager.abort_rollout("my-rollout")

        call_args = mock_k8s_client.custom_objects.patch_namespaced_custom_object.call_args
        patch = call_args.args[5]
        assert patch["metadata"]["annotations"]["rollout.argoproj.io/abort"] == "true"

    def test_retry_rollout(
        self,
        rollouts_manager: RolloutsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """retry_rollout should patch rollout to remove abort annotation."""
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.return_value = {
            "metadata": {"name": "my-rollout", "namespace": "default"},
            "spec": {},
            "status": {},
        }

        rollouts_manager.retry_rollout("my-rollout")

        call_args = mock_k8s_client.custom_objects.patch_namespaced_custom_object.call_args
        patch = call_args.args[5]
        assert patch["metadata"]["annotations"]["rollout.argoproj.io/abort"] is None
        assert patch["status"]["abort"] is False

    # =========================================================================
    # AnalysisTemplate Tests
    # =========================================================================

    def test_list_analysis_templates(
        self,
        rollouts_manager: RolloutsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_analysis_templates should call custom_objects API."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {
            "items": [
                {
                    "metadata": {"name": "success-rate", "namespace": "default"},
                    "spec": {
                        "metrics": [{"name": "success-rate"}, {"name": "error-rate"}],
                        "args": [{"name": "service-name"}],
                    },
                }
            ]
        }

        templates = rollouts_manager.list_analysis_templates()

        assert len(templates) == 1
        assert templates[0].name == "success-rate"
        assert templates[0].metrics_count == 2
        assert templates[0].args == ["service-name"]
        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            ARGO_ROLLOUTS_GROUP,
            ARGO_ROLLOUTS_VERSION,
            "default",
            ANALYSIS_TEMPLATE_PLURAL,
        )

    def test_get_analysis_template(
        self,
        rollouts_manager: RolloutsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_analysis_template should retrieve template by name."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {
            "metadata": {"name": "success-rate", "namespace": "default"},
            "spec": {
                "metrics": [{"name": "success-rate"}],
                "args": [{"name": "service-name"}],
            },
        }

        template = rollouts_manager.get_analysis_template("success-rate")

        assert template.name == "success-rate"
        assert template.metrics_count == 1
        mock_k8s_client.custom_objects.get_namespaced_custom_object.assert_called_once_with(
            ARGO_ROLLOUTS_GROUP,
            ARGO_ROLLOUTS_VERSION,
            "default",
            ANALYSIS_TEMPLATE_PLURAL,
            "success-rate",
        )

    # =========================================================================
    # AnalysisRun Tests
    # =========================================================================

    def test_list_analysis_runs(
        self,
        rollouts_manager: RolloutsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_analysis_runs should call custom_objects API."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {
            "items": [
                {
                    "metadata": {
                        "name": "my-rollout-abc123",
                        "namespace": "default",
                        "ownerReferences": [{"kind": "Rollout", "name": "my-rollout"}],
                    },
                    "spec": {},
                    "status": {
                        "phase": "Successful",
                        "metricResults": [{"name": "success-rate"}, {"name": "error-rate"}],
                    },
                }
            ]
        }

        runs = rollouts_manager.list_analysis_runs()

        assert len(runs) == 1
        assert runs[0].name == "my-rollout-abc123"
        assert runs[0].phase == "Successful"
        assert runs[0].metrics_count == 2
        assert runs[0].rollout_ref == "my-rollout"
        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            ARGO_ROLLOUTS_GROUP,
            ARGO_ROLLOUTS_VERSION,
            "default",
            ANALYSIS_RUN_PLURAL,
        )

    def test_get_analysis_run(
        self,
        rollouts_manager: RolloutsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_analysis_run should retrieve run by name."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {
            "metadata": {
                "name": "my-rollout-abc123",
                "namespace": "default",
                "ownerReferences": [{"kind": "Rollout", "name": "my-rollout"}],
            },
            "spec": {},
            "status": {
                "phase": "Successful",
                "metricResults": [{"name": "success-rate"}],
            },
        }

        run = rollouts_manager.get_analysis_run("my-rollout-abc123")

        assert run.name == "my-rollout-abc123"
        assert run.phase == "Successful"
        assert run.rollout_ref == "my-rollout"
        mock_k8s_client.custom_objects.get_namespaced_custom_object.assert_called_once_with(
            ARGO_ROLLOUTS_GROUP,
            ARGO_ROLLOUTS_VERSION,
            "default",
            ANALYSIS_RUN_PLURAL,
            "my-rollout-abc123",
        )


@pytest.mark.unit
@pytest.mark.kubernetes
class TestRolloutsManagerErrorPaths:
    """Tests for RolloutsManager API error handling (exception branches)."""

    def test_list_rollouts_api_error(
        self,
        rollouts_manager: RolloutsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_rollouts should propagate translated API errors."""
        sentinel = RuntimeError("list rollouts failed")
        mock_k8s_client.custom_objects.list_namespaced_custom_object.side_effect = RuntimeError(
            "raw"
        )
        mock_k8s_client.translate_api_exception.side_effect = sentinel

        with pytest.raises(RuntimeError, match="list rollouts failed"):
            rollouts_manager.list_rollouts()

    def test_get_rollout_api_error(
        self,
        rollouts_manager: RolloutsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_rollout should propagate translated API errors."""
        sentinel = RuntimeError("get rollout failed")
        mock_k8s_client.custom_objects.get_namespaced_custom_object.side_effect = RuntimeError(
            "raw"
        )
        mock_k8s_client.translate_api_exception.side_effect = sentinel

        with pytest.raises(RuntimeError, match="get rollout failed"):
            rollouts_manager.get_rollout("my-rollout")

    def test_create_rollout_api_error(
        self,
        rollouts_manager: RolloutsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_rollout should propagate translated API errors."""
        sentinel = RuntimeError("create rollout failed")
        mock_k8s_client.custom_objects.create_namespaced_custom_object.side_effect = RuntimeError(
            "raw"
        )
        mock_k8s_client.translate_api_exception.side_effect = sentinel

        with pytest.raises(RuntimeError, match="create rollout failed"):
            rollouts_manager.create_rollout("my-rollout", image="nginx:latest")

    def test_delete_rollout_api_error(
        self,
        rollouts_manager: RolloutsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """delete_rollout should propagate translated API errors."""
        sentinel = RuntimeError("delete rollout failed")
        mock_k8s_client.custom_objects.delete_namespaced_custom_object.side_effect = RuntimeError(
            "raw"
        )
        mock_k8s_client.translate_api_exception.side_effect = sentinel

        with pytest.raises(RuntimeError, match="delete rollout failed"):
            rollouts_manager.delete_rollout("my-rollout")

    def test_get_rollout_status_api_error(
        self,
        rollouts_manager: RolloutsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_rollout_status should propagate translated API errors."""
        sentinel = RuntimeError("get status failed")
        mock_k8s_client.custom_objects.get_namespaced_custom_object.side_effect = RuntimeError(
            "raw"
        )
        mock_k8s_client.translate_api_exception.side_effect = sentinel

        with pytest.raises(RuntimeError, match="get status failed"):
            rollouts_manager.get_rollout_status("my-rollout")

    def test_promote_rollout_api_error(
        self,
        rollouts_manager: RolloutsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """promote_rollout should propagate translated API errors."""
        sentinel = RuntimeError("promote rollout failed")
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.side_effect = RuntimeError(
            "raw"
        )
        mock_k8s_client.translate_api_exception.side_effect = sentinel

        with pytest.raises(RuntimeError, match="promote rollout failed"):
            rollouts_manager.promote_rollout("my-rollout")

    def test_abort_rollout_api_error(
        self,
        rollouts_manager: RolloutsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """abort_rollout should propagate translated API errors."""
        sentinel = RuntimeError("abort rollout failed")
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.side_effect = RuntimeError(
            "raw"
        )
        mock_k8s_client.translate_api_exception.side_effect = sentinel

        with pytest.raises(RuntimeError, match="abort rollout failed"):
            rollouts_manager.abort_rollout("my-rollout")

    def test_retry_rollout_api_error(
        self,
        rollouts_manager: RolloutsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """retry_rollout should propagate translated API errors."""
        sentinel = RuntimeError("retry rollout failed")
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.side_effect = RuntimeError(
            "raw"
        )
        mock_k8s_client.translate_api_exception.side_effect = sentinel

        with pytest.raises(RuntimeError, match="retry rollout failed"):
            rollouts_manager.retry_rollout("my-rollout")

    def test_list_analysis_templates_api_error(
        self,
        rollouts_manager: RolloutsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_analysis_templates should propagate translated API errors."""
        sentinel = RuntimeError("list templates failed")
        mock_k8s_client.custom_objects.list_namespaced_custom_object.side_effect = RuntimeError(
            "raw"
        )
        mock_k8s_client.translate_api_exception.side_effect = sentinel

        with pytest.raises(RuntimeError, match="list templates failed"):
            rollouts_manager.list_analysis_templates()

    def test_get_analysis_template_api_error(
        self,
        rollouts_manager: RolloutsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_analysis_template should propagate translated API errors."""
        sentinel = RuntimeError("get template failed")
        mock_k8s_client.custom_objects.get_namespaced_custom_object.side_effect = RuntimeError(
            "raw"
        )
        mock_k8s_client.translate_api_exception.side_effect = sentinel

        with pytest.raises(RuntimeError, match="get template failed"):
            rollouts_manager.get_analysis_template("success-rate")

    def test_list_analysis_runs_api_error(
        self,
        rollouts_manager: RolloutsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_analysis_runs should propagate translated API errors."""
        sentinel = RuntimeError("list runs failed")
        mock_k8s_client.custom_objects.list_namespaced_custom_object.side_effect = RuntimeError(
            "raw"
        )
        mock_k8s_client.translate_api_exception.side_effect = sentinel

        with pytest.raises(RuntimeError, match="list runs failed"):
            rollouts_manager.list_analysis_runs()

    def test_get_analysis_run_api_error(
        self,
        rollouts_manager: RolloutsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_analysis_run should propagate translated API errors."""
        sentinel = RuntimeError("get run failed")
        mock_k8s_client.custom_objects.get_namespaced_custom_object.side_effect = RuntimeError(
            "raw"
        )
        mock_k8s_client.translate_api_exception.side_effect = sentinel

        with pytest.raises(RuntimeError, match="get run failed"):
            rollouts_manager.get_analysis_run("my-rollout-abc123")


@pytest.mark.unit
@pytest.mark.kubernetes
class TestRolloutsManagerEdgeCases:
    """Tests for RolloutsManager edge cases and alternate branches."""

    def test_create_rollout_with_canary_steps(
        self,
        rollouts_manager: RolloutsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_rollout should include canary steps in strategy spec."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = {
            "metadata": {"name": "my-rollout", "namespace": "default"},
            "spec": {
                "replicas": 1,
                "strategy": {
                    "canary": {"steps": [{"setWeight": 20}, {"pause": {"duration": "10m"}}]}
                },
                "template": {"spec": {"containers": [{"image": "nginx:latest"}]}},
            },
            "status": {},
        }
        canary_steps = [{"setWeight": 20}, {"pause": {"duration": "10m"}}]

        rollouts_manager.create_rollout(
            "my-rollout",
            image="nginx:latest",
            canary_steps=canary_steps,
        )

        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args.args[4]
        assert body["spec"]["strategy"]["canary"]["steps"] == canary_steps

    def test_create_rollout_with_labels(
        self,
        rollouts_manager: RolloutsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_rollout should merge provided labels into app_labels."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = {
            "metadata": {"name": "my-rollout", "namespace": "default"},
            "spec": {
                "replicas": 1,
                "strategy": {"canary": {}},
                "template": {"spec": {"containers": [{"image": "nginx:latest"}]}},
            },
            "status": {},
        }
        extra_labels = {"env": "prod", "team": "platform"}

        rollouts_manager.create_rollout(
            "my-rollout",
            image="nginx:latest",
            labels=extra_labels,
        )

        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args.args[4]
        assert body["metadata"]["labels"]["app"] == "my-rollout"
        assert body["metadata"]["labels"]["env"] == "prod"
        assert body["metadata"]["labels"]["team"] == "platform"

    def test_list_analysis_templates_with_label_selector(
        self,
        rollouts_manager: RolloutsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_analysis_templates should pass label_selector when provided."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

        rollouts_manager.list_analysis_templates(label_selector="team=platform")

        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            ARGO_ROLLOUTS_GROUP,
            ARGO_ROLLOUTS_VERSION,
            "default",
            ANALYSIS_TEMPLATE_PLURAL,
            label_selector="team=platform",
        )

    def test_list_analysis_runs_with_label_selector(
        self,
        rollouts_manager: RolloutsManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_analysis_runs should pass label_selector when provided."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

        rollouts_manager.list_analysis_runs(label_selector="rollout=my-rollout")

        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            ARGO_ROLLOUTS_GROUP,
            ARGO_ROLLOUTS_VERSION,
            "default",
            ANALYSIS_RUN_PLURAL,
            label_selector="rollout=my-rollout",
        )
