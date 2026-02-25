"""Unit tests for Kubernetes workload CLI commands (gap-fill coverage)."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesAuthError,
    KubernetesConnectionError,
    KubernetesError,
    KubernetesNotFoundError,
    KubernetesTimeoutError,
)
from system_operations_manager.plugins.kubernetes.commands.workloads import (
    _parse_labels,
    register_workload_commands,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_workload_manager() -> MagicMock:
    """Create a mock WorkloadManager."""
    manager = MagicMock()

    manager.list_pods.return_value = []
    manager.get_pod.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "my-pod", "namespace": "default"}
    )
    manager.delete_pod.return_value = None
    manager.get_pod_logs.return_value = "pod logs here"

    manager.list_deployments.return_value = []
    manager.get_deployment.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "my-app", "namespace": "default", "replicas": 1}
    )
    manager.create_deployment.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "my-app", "namespace": "default", "replicas": 1}
    )
    manager.update_deployment.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "my-app", "namespace": "default", "replicas": 2}
    )
    manager.delete_deployment.return_value = None
    manager.scale_deployment.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "my-app", "namespace": "default", "replicas": 5}
    )
    manager.restart_deployment.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "my-app", "namespace": "default"}
    )
    manager.get_rollout_status.return_value = {"complete": True, "message": "done"}
    manager.rollback_deployment.return_value = None

    manager.list_stateful_sets.return_value = []
    manager.get_stateful_set.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "my-db", "namespace": "default", "replicas": 1}
    )
    manager.create_stateful_set.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "my-db", "namespace": "default"}
    )
    manager.update_stateful_set.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "my-db", "namespace": "default"}
    )
    manager.delete_stateful_set.return_value = None
    manager.scale_stateful_set.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "my-db", "namespace": "default", "replicas": 3}
    )
    manager.restart_stateful_set.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "my-db", "namespace": "default"}
    )

    manager.list_daemon_sets.return_value = []
    manager.get_daemon_set.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "my-logger", "namespace": "default"}
    )
    manager.create_daemon_set.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "my-logger", "namespace": "default"}
    )
    manager.update_daemon_set.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "my-logger", "namespace": "default"}
    )
    manager.delete_daemon_set.return_value = None
    manager.restart_daemon_set.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "my-logger", "namespace": "default"}
    )

    manager.list_replica_sets.return_value = []
    manager.get_replica_set.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "my-rs", "namespace": "default"}
    )
    manager.delete_replica_set.return_value = None

    return manager


@pytest.fixture
def get_workload_manager_fn(mock_workload_manager: MagicMock) -> Callable[[], MagicMock]:
    """Factory returning the mock WorkloadManager."""
    return lambda: mock_workload_manager


@pytest.fixture
def app(get_workload_manager_fn: Callable[[], MagicMock]) -> typer.Typer:
    """Create a test Typer app with workload commands registered."""
    test_app = typer.Typer()
    register_workload_commands(test_app, get_workload_manager_fn)
    return test_app


# =============================================================================
# Tests for _parse_labels helper  (lines 29, 96-97)
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestParseLabels:
    """Tests for the _parse_labels helper function in workloads module."""

    def test_returns_none_for_none_input(self) -> None:
        """Should return None when labels is None (line 29 TYPE_CHECKING branch)."""
        result = _parse_labels(None)
        assert result is None

    def test_returns_none_for_empty_list(self) -> None:
        """Should return None when labels is an empty list."""
        result = _parse_labels([])
        assert result is None

    def test_parses_valid_labels(self) -> None:
        """Should parse valid key=value labels into a dict."""
        result = _parse_labels(["app=nginx", "env=prod"])
        assert result == {"app": "nginx", "env": "prod"}

    def test_invalid_label_format_prints_error_and_exits(self) -> None:
        """Should print error and raise typer.Exit(1) on bad label (lines 96-97)."""
        with pytest.raises(typer.Exit) as exc_info:
            _parse_labels(["invalid-label"])
        assert exc_info.value.exit_code == 1

    def test_invalid_label_no_separator_exits(self) -> None:
        """Should exit when label string has no = separator."""
        with pytest.raises(typer.Exit):
            _parse_labels(["keyonly"])


# =============================================================================
# Tests for Pod commands  (lines 198, 231-232)
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestPodCommandErrors:
    """Tests for error-path coverage in pod commands."""

    def test_list_pods_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """list_pods should handle KubernetesError."""
        mock_workload_manager.list_pods.side_effect = KubernetesConnectionError("Cannot connect")

        result = cli_runner.invoke(app, ["pods", "list"])

        assert result.exit_code == 1

    def test_get_pod_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """get_pod should handle KubernetesError."""
        mock_workload_manager.get_pod.side_effect = KubernetesNotFoundError(
            resource_type="Pod", resource_name="my-pod"
        )

        result = cli_runner.invoke(app, ["pods", "get", "my-pod"])

        assert result.exit_code == 1

    def test_delete_pod_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """delete_pod should handle KubernetesError (line 198)."""
        mock_workload_manager.delete_pod.side_effect = KubernetesError(
            "Server error", status_code=500
        )

        result = cli_runner.invoke(app, ["pods", "delete", "my-pod", "--force"])

        assert result.exit_code == 1

    def test_delete_pod_user_cancels(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """delete_pod should cancel when user does not confirm."""
        with patch(
            "system_operations_manager.plugins.kubernetes.commands.base.typer.confirm",
            return_value=False,
        ):
            result = cli_runner.invoke(app, ["pods", "delete", "my-pod"])

        assert result.exit_code == 0
        mock_workload_manager.delete_pod.assert_not_called()

    def test_pod_logs_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """pod_logs should handle KubernetesError (lines 231-232)."""
        mock_workload_manager.get_pod_logs.side_effect = KubernetesTimeoutError("Timed out")

        result = cli_runner.invoke(app, ["pods", "logs", "my-pod"])

        assert result.exit_code == 1


# =============================================================================
# Tests for Deployment commands  (lines 267-268, 323-324, 351-352, 369-370,
#   374-375, 397-398, 418-419, 438-439, 462-463)
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestDeploymentCommandErrors:
    """Tests for error-path coverage in deployment commands."""

    def test_list_deployments_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """list_deployments should handle KubernetesError (lines 267-268)."""
        mock_workload_manager.list_deployments.side_effect = KubernetesConnectionError(
            "Cannot connect"
        )

        result = cli_runner.invoke(app, ["deployments", "list"])

        assert result.exit_code == 1

    def test_create_deployment_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """create_deployment should handle KubernetesError (lines 323-324)."""
        mock_workload_manager.create_deployment.side_effect = KubernetesError(
            "Server error", status_code=500
        )

        result = cli_runner.invoke(
            app,
            ["deployments", "create", "my-app", "--image", "nginx:1.21"],
        )

        assert result.exit_code == 1

    def test_create_deployment_with_invalid_label(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """create_deployment should exit on invalid label format."""
        result = cli_runner.invoke(
            app,
            [
                "deployments",
                "create",
                "my-app",
                "--image",
                "nginx:1.21",
                "--label",
                "invalid-no-equals",
            ],
        )

        assert result.exit_code == 1
        mock_workload_manager.create_deployment.assert_not_called()

    def test_update_deployment_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """update_deployment should handle KubernetesError (lines 351-352)."""
        mock_workload_manager.update_deployment.side_effect = KubernetesNotFoundError(
            resource_type="Deployment", resource_name="my-app"
        )

        result = cli_runner.invoke(
            app,
            ["deployments", "update", "my-app", "--image", "nginx:1.22"],
        )

        assert result.exit_code == 1

    def test_delete_deployment_user_cancels(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """delete_deployment should cancel when user does not confirm (lines 369-370)."""
        with patch(
            "system_operations_manager.plugins.kubernetes.commands.base.typer.confirm",
            return_value=False,
        ):
            result = cli_runner.invoke(app, ["deployments", "delete", "my-app"])

        assert result.exit_code == 0
        mock_workload_manager.delete_deployment.assert_not_called()

    def test_delete_deployment_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """delete_deployment should handle KubernetesError (lines 374-375)."""
        mock_workload_manager.delete_deployment.side_effect = KubernetesNotFoundError(
            resource_type="Deployment", resource_name="my-app"
        )

        result = cli_runner.invoke(app, ["deployments", "delete", "my-app", "--force"])

        assert result.exit_code == 1

    def test_scale_deployment_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """scale_deployment should handle KubernetesError (lines 397-398)."""
        mock_workload_manager.scale_deployment.side_effect = KubernetesError(
            "Server error", status_code=500
        )

        result = cli_runner.invoke(app, ["deployments", "scale", "my-app", "--replicas", "5"])

        assert result.exit_code == 1

    def test_restart_deployment_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """restart_deployment should handle KubernetesError (lines 418-419)."""
        mock_workload_manager.restart_deployment.side_effect = KubernetesTimeoutError("Timed out")

        result = cli_runner.invoke(app, ["deployments", "restart", "my-app"])

        assert result.exit_code == 1

    def test_rollout_status_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """rollout_status should handle KubernetesError (lines 438-439)."""
        mock_workload_manager.get_rollout_status.side_effect = KubernetesNotFoundError(
            resource_type="Deployment", resource_name="my-app"
        )

        result = cli_runner.invoke(app, ["deployments", "rollout-status", "my-app"])

        assert result.exit_code == 1

    def test_rollback_deployment_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """rollback_deployment should handle KubernetesError (lines 462-463)."""
        mock_workload_manager.rollback_deployment.side_effect = KubernetesError(
            "Server error", status_code=500
        )

        result = cli_runner.invoke(app, ["deployments", "rollback", "my-app", "--revision", "2"])

        assert result.exit_code == 1

    def test_rollback_deployment_no_revision_text(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """rollback_deployment should say 'previous revision' when no revision given."""
        result = cli_runner.invoke(app, ["deployments", "rollback", "my-app"])

        assert result.exit_code == 0
        assert "previous revision" in result.stdout

    def test_rollback_deployment_with_revision_text(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """rollback_deployment should say 'revision N' when revision is specified."""
        result = cli_runner.invoke(app, ["deployments", "rollback", "my-app", "--revision", "3"])

        assert result.exit_code == 0
        assert "revision 3" in result.stdout


# =============================================================================
# Tests for StatefulSet commands  (lines 495-496, 515-516, 553-554, 580-581,
#   597-598, 602-603, 623-624, 643-644)
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestStatefulSetCommandErrors:
    """Tests for error-path coverage in statefulset commands."""

    def test_list_statefulsets_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """list_statefulsets should handle KubernetesError (lines 495-496)."""
        mock_workload_manager.list_stateful_sets.side_effect = KubernetesConnectionError(
            "Cannot connect"
        )

        result = cli_runner.invoke(app, ["statefulsets", "list"])

        assert result.exit_code == 1

    def test_get_statefulset_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """get_statefulset should handle KubernetesError (lines 515-516)."""
        mock_workload_manager.get_stateful_set.side_effect = KubernetesNotFoundError(
            resource_type="StatefulSet", resource_name="my-db"
        )

        result = cli_runner.invoke(app, ["statefulsets", "get", "my-db"])

        assert result.exit_code == 1

    def test_create_statefulset_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """create_statefulset should handle KubernetesError (lines 553-554)."""
        mock_workload_manager.create_stateful_set.side_effect = KubernetesError(
            "Server error", status_code=500
        )

        result = cli_runner.invoke(
            app,
            [
                "statefulsets",
                "create",
                "my-db",
                "--image",
                "postgres:15",
                "--service-name",
                "my-db-svc",
            ],
        )

        assert result.exit_code == 1

    def test_create_statefulset_with_invalid_label(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """create_statefulset should exit on invalid label format."""
        result = cli_runner.invoke(
            app,
            [
                "statefulsets",
                "create",
                "my-db",
                "--image",
                "postgres:15",
                "--service-name",
                "my-db-svc",
                "--label",
                "invalid-no-equals",
            ],
        )

        assert result.exit_code == 1
        mock_workload_manager.create_stateful_set.assert_not_called()

    def test_update_statefulset_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """update_statefulset should handle KubernetesError (lines 580-581)."""
        mock_workload_manager.update_stateful_set.side_effect = KubernetesNotFoundError(
            resource_type="StatefulSet", resource_name="my-db"
        )

        result = cli_runner.invoke(
            app, ["statefulsets", "update", "my-db", "--image", "postgres:16"]
        )

        assert result.exit_code == 1

    def test_delete_statefulset_user_cancels(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """delete_statefulset should cancel when user does not confirm (lines 597-598)."""
        with patch(
            "system_operations_manager.plugins.kubernetes.commands.base.typer.confirm",
            return_value=False,
        ):
            result = cli_runner.invoke(app, ["statefulsets", "delete", "my-db"])

        assert result.exit_code == 0
        mock_workload_manager.delete_stateful_set.assert_not_called()

    def test_delete_statefulset_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """delete_statefulset should handle KubernetesError (lines 602-603)."""
        mock_workload_manager.delete_stateful_set.side_effect = KubernetesNotFoundError(
            resource_type="StatefulSet", resource_name="my-db"
        )

        result = cli_runner.invoke(app, ["statefulsets", "delete", "my-db", "--force"])

        assert result.exit_code == 1

    def test_scale_statefulset_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """scale_statefulset should handle KubernetesError (lines 623-624)."""
        mock_workload_manager.scale_stateful_set.side_effect = KubernetesError(
            "Server error", status_code=500
        )

        result = cli_runner.invoke(app, ["statefulsets", "scale", "my-db", "--replicas", "3"])

        assert result.exit_code == 1

    def test_restart_statefulset_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """restart_statefulset should handle KubernetesError (lines 643-644)."""
        mock_workload_manager.restart_stateful_set.side_effect = KubernetesTimeoutError("Timed out")

        result = cli_runner.invoke(app, ["statefulsets", "restart", "my-db"])

        assert result.exit_code == 1


# =============================================================================
# Tests for DaemonSet commands  (lines 676-677, 696-697, 726-727, 749-750,
#   766-767, 771-772, 791-792)
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestDaemonSetCommandErrors:
    """Tests for error-path coverage in daemonset commands."""

    def test_list_daemonsets_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """list_daemonsets should handle KubernetesError (lines 676-677)."""
        mock_workload_manager.list_daemon_sets.side_effect = KubernetesConnectionError(
            "Cannot connect"
        )

        result = cli_runner.invoke(app, ["daemonsets", "list"])

        assert result.exit_code == 1

    def test_get_daemonset_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """get_daemonset should handle KubernetesError (lines 696-697)."""
        mock_workload_manager.get_daemon_set.side_effect = KubernetesNotFoundError(
            resource_type="DaemonSet", resource_name="my-logger"
        )

        result = cli_runner.invoke(app, ["daemonsets", "get", "my-logger"])

        assert result.exit_code == 1

    def test_create_daemonset_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """create_daemonset should handle KubernetesError (lines 726-727)."""
        mock_workload_manager.create_daemon_set.side_effect = KubernetesError(
            "Server error", status_code=500
        )

        result = cli_runner.invoke(
            app,
            ["daemonsets", "create", "my-logger", "--image", "fluentd:latest"],
        )

        assert result.exit_code == 1

    def test_create_daemonset_with_invalid_label(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """create_daemonset should exit on invalid label format."""
        result = cli_runner.invoke(
            app,
            [
                "daemonsets",
                "create",
                "my-logger",
                "--image",
                "fluentd:latest",
                "--label",
                "invalid-no-equals",
            ],
        )

        assert result.exit_code == 1
        mock_workload_manager.create_daemon_set.assert_not_called()

    def test_update_daemonset_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """update_daemonset should handle KubernetesError (lines 749-750)."""
        mock_workload_manager.update_daemon_set.side_effect = KubernetesNotFoundError(
            resource_type="DaemonSet", resource_name="my-logger"
        )

        result = cli_runner.invoke(
            app, ["daemonsets", "update", "my-logger", "--image", "fluentd:v2"]
        )

        assert result.exit_code == 1

    def test_delete_daemonset_user_cancels(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """delete_daemonset should cancel when user does not confirm (lines 766-767)."""
        with patch(
            "system_operations_manager.plugins.kubernetes.commands.base.typer.confirm",
            return_value=False,
        ):
            result = cli_runner.invoke(app, ["daemonsets", "delete", "my-logger"])

        assert result.exit_code == 0
        mock_workload_manager.delete_daemon_set.assert_not_called()

    def test_delete_daemonset_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """delete_daemonset should handle KubernetesError (lines 771-772)."""
        mock_workload_manager.delete_daemon_set.side_effect = KubernetesNotFoundError(
            resource_type="DaemonSet", resource_name="my-logger"
        )

        result = cli_runner.invoke(app, ["daemonsets", "delete", "my-logger", "--force"])

        assert result.exit_code == 1

    def test_restart_daemonset_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """restart_daemonset should handle KubernetesError (lines 791-792)."""
        mock_workload_manager.restart_daemon_set.side_effect = KubernetesTimeoutError("Timed out")

        result = cli_runner.invoke(app, ["daemonsets", "restart", "my-logger"])

        assert result.exit_code == 1


# =============================================================================
# Tests for ReplicaSet commands  (lines 823-824, 843-844, 866)
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestReplicaSetCommandErrors:
    """Tests for error-path coverage in replicaset commands."""

    def test_list_replicasets_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """list_replicasets should handle KubernetesError (lines 823-824)."""
        mock_workload_manager.list_replica_sets.side_effect = KubernetesAuthError(
            "Forbidden", status_code=403
        )

        result = cli_runner.invoke(app, ["replicasets", "list"])

        assert result.exit_code == 1

    def test_get_replicaset_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """get_replicaset should handle KubernetesError (lines 843-844)."""
        mock_workload_manager.get_replica_set.side_effect = KubernetesNotFoundError(
            resource_type="ReplicaSet", resource_name="my-rs"
        )

        result = cli_runner.invoke(app, ["replicasets", "get", "my-rs"])

        assert result.exit_code == 1

    def test_delete_replicaset_user_cancels(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """delete_replicaset should cancel when user does not confirm."""
        with patch(
            "system_operations_manager.plugins.kubernetes.commands.base.typer.confirm",
            return_value=False,
        ):
            result = cli_runner.invoke(app, ["replicasets", "delete", "my-rs"])

        assert result.exit_code == 0
        mock_workload_manager.delete_replica_set.assert_not_called()

    def test_delete_replicaset_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """delete_replicaset should handle KubernetesError (line 866)."""
        mock_workload_manager.delete_replica_set.side_effect = KubernetesNotFoundError(
            resource_type="ReplicaSet", resource_name="my-rs"
        )

        result = cli_runner.invoke(app, ["replicasets", "delete", "my-rs", "--force"])

        assert result.exit_code == 1

    def test_delete_replicaset_force_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """delete_replicaset with --force should delete without confirmation."""
        result = cli_runner.invoke(app, ["replicasets", "delete", "my-rs", "--force"])

        assert result.exit_code == 0
        mock_workload_manager.delete_replica_set.assert_called_once()


# =============================================================================
# Happy-path tests to cover success branches
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestPodHappyPaths:
    """Happy-path tests for Pod command success branches."""

    def test_list_pods_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """list_pods should succeed and call formatter (lines 151-152)."""
        result = cli_runner.invoke(app, ["pods", "list"])

        assert result.exit_code == 0
        mock_workload_manager.list_pods.assert_called_once()

    def test_get_pod_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """get_pod should succeed and format the resource (lines 172-173)."""
        result = cli_runner.invoke(app, ["pods", "get", "my-pod"])

        assert result.exit_code == 0
        mock_workload_manager.get_pod.assert_called_once_with("my-pod", None)

    def test_delete_pod_force_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """delete_pod with --force should succeed without confirmation (line 196)."""
        result = cli_runner.invoke(app, ["pods", "delete", "my-pod", "--force"])

        assert result.exit_code == 0
        mock_workload_manager.delete_pod.assert_called_once_with("my-pod", None)

    def test_pod_logs_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """pod_logs should print logs on success (line 230)."""
        result = cli_runner.invoke(app, ["pods", "logs", "my-pod"])

        assert result.exit_code == 0
        assert "pod logs here" in result.stdout


@pytest.mark.unit
@pytest.mark.kubernetes
class TestDeploymentHappyPaths:
    """Happy-path tests for Deployment command success branches."""

    def test_list_deployments_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """list_deployments should succeed and call formatter (lines 265-266)."""
        result = cli_runner.invoke(app, ["deployments", "list"])

        assert result.exit_code == 0
        mock_workload_manager.list_deployments.assert_called_once()

    def test_get_deployment_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """get_deployment should succeed and format the resource (lines 283-289)."""
        result = cli_runner.invoke(app, ["deployments", "get", "my-app"])

        assert result.exit_code == 0
        mock_workload_manager.get_deployment.assert_called_once_with("my-app", None)

    def test_get_deployment_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """get_deployment should handle KubernetesError."""
        mock_workload_manager.get_deployment.side_effect = KubernetesNotFoundError(
            resource_type="Deployment", resource_name="my-app"
        )

        result = cli_runner.invoke(app, ["deployments", "get", "my-app"])

        assert result.exit_code == 1

    def test_create_deployment_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """create_deployment should succeed and format the resource (lines 320-322)."""
        result = cli_runner.invoke(
            app, ["deployments", "create", "my-app", "--image", "nginx:1.21"]
        )

        assert result.exit_code == 0
        mock_workload_manager.create_deployment.assert_called_once()

    def test_update_deployment_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """update_deployment should succeed and format the resource (lines 348-350)."""
        result = cli_runner.invoke(
            app, ["deployments", "update", "my-app", "--image", "nginx:1.22"]
        )

        assert result.exit_code == 0
        mock_workload_manager.update_deployment.assert_called_once()

    def test_delete_deployment_force_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """delete_deployment with --force should delete without confirmation (line 373)."""
        result = cli_runner.invoke(app, ["deployments", "delete", "my-app", "--force"])

        assert result.exit_code == 0
        mock_workload_manager.delete_deployment.assert_called_once()

    def test_scale_deployment_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """scale_deployment should succeed and format the resource (lines 394-396)."""
        result = cli_runner.invoke(app, ["deployments", "scale", "my-app", "--replicas", "5"])

        assert result.exit_code == 0
        mock_workload_manager.scale_deployment.assert_called_once()

    def test_restart_deployment_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """restart_deployment should succeed and format the resource (lines 415-417)."""
        result = cli_runner.invoke(app, ["deployments", "restart", "my-app"])

        assert result.exit_code == 0
        mock_workload_manager.restart_deployment.assert_called_once()

    def test_rollout_status_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """rollout_status should succeed and format the dict (lines 436-437)."""
        result = cli_runner.invoke(app, ["deployments", "rollout-status", "my-app"])

        assert result.exit_code == 0
        mock_workload_manager.get_rollout_status.assert_called_once()


@pytest.mark.unit
@pytest.mark.kubernetes
class TestStatefulSetHappyPaths:
    """Happy-path tests for StatefulSet command success branches."""

    def test_list_statefulsets_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """list_statefulsets should succeed and call formatter (lines 493-494)."""
        result = cli_runner.invoke(app, ["statefulsets", "list"])

        assert result.exit_code == 0
        mock_workload_manager.list_stateful_sets.assert_called_once()

    def test_get_statefulset_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """get_statefulset should succeed and format the resource (lines 513-514)."""
        result = cli_runner.invoke(app, ["statefulsets", "get", "my-db"])

        assert result.exit_code == 0
        mock_workload_manager.get_stateful_set.assert_called_once_with("my-db", None)

    def test_create_statefulset_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """create_statefulset should succeed and format the resource (lines 550-552)."""
        result = cli_runner.invoke(
            app,
            [
                "statefulsets",
                "create",
                "my-db",
                "--image",
                "postgres:15",
                "--service-name",
                "my-db-svc",
            ],
        )

        assert result.exit_code == 0
        mock_workload_manager.create_stateful_set.assert_called_once()

    def test_update_statefulset_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """update_statefulset should succeed and format the resource (lines 577-579)."""
        result = cli_runner.invoke(
            app, ["statefulsets", "update", "my-db", "--image", "postgres:16"]
        )

        assert result.exit_code == 0
        mock_workload_manager.update_stateful_set.assert_called_once()

    def test_delete_statefulset_force_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """delete_statefulset with --force should delete without confirmation (line 601)."""
        result = cli_runner.invoke(app, ["statefulsets", "delete", "my-db", "--force"])

        assert result.exit_code == 0
        mock_workload_manager.delete_stateful_set.assert_called_once()

    def test_scale_statefulset_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """scale_statefulset should succeed and format the resource (lines 620-622)."""
        result = cli_runner.invoke(app, ["statefulsets", "scale", "my-db", "--replicas", "3"])

        assert result.exit_code == 0
        mock_workload_manager.scale_stateful_set.assert_called_once()

    def test_restart_statefulset_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """restart_statefulset should succeed and format the resource (lines 640-642)."""
        result = cli_runner.invoke(app, ["statefulsets", "restart", "my-db"])

        assert result.exit_code == 0
        mock_workload_manager.restart_stateful_set.assert_called_once()


@pytest.mark.unit
@pytest.mark.kubernetes
class TestDaemonSetHappyPaths:
    """Happy-path tests for DaemonSet command success branches."""

    def test_list_daemonsets_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """list_daemonsets should succeed and call formatter (lines 674-675)."""
        result = cli_runner.invoke(app, ["daemonsets", "list"])

        assert result.exit_code == 0
        mock_workload_manager.list_daemon_sets.assert_called_once()

    def test_get_daemonset_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """get_daemonset should succeed and format the resource (lines 694-695)."""
        result = cli_runner.invoke(app, ["daemonsets", "get", "my-logger"])

        assert result.exit_code == 0
        mock_workload_manager.get_daemon_set.assert_called_once_with("my-logger", None)

    def test_create_daemonset_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """create_daemonset should succeed and format the resource (lines 723-725)."""
        result = cli_runner.invoke(
            app,
            ["daemonsets", "create", "my-logger", "--image", "fluentd:latest"],
        )

        assert result.exit_code == 0
        mock_workload_manager.create_daemon_set.assert_called_once()

    def test_update_daemonset_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """update_daemonset should succeed and format the resource (lines 746-748)."""
        result = cli_runner.invoke(
            app, ["daemonsets", "update", "my-logger", "--image", "fluentd:v2"]
        )

        assert result.exit_code == 0
        mock_workload_manager.update_daemon_set.assert_called_once()

    def test_delete_daemonset_force_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """delete_daemonset with --force should delete without confirmation (line 770)."""
        result = cli_runner.invoke(app, ["daemonsets", "delete", "my-logger", "--force"])

        assert result.exit_code == 0
        mock_workload_manager.delete_daemon_set.assert_called_once()

    def test_restart_daemonset_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """restart_daemonset should succeed and format the resource (lines 788-790)."""
        result = cli_runner.invoke(app, ["daemonsets", "restart", "my-logger"])

        assert result.exit_code == 0
        mock_workload_manager.restart_daemon_set.assert_called_once()


@pytest.mark.unit
@pytest.mark.kubernetes
class TestReplicaSetHappyPaths:
    """Happy-path tests for ReplicaSet command success branches."""

    def test_list_replicasets_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """list_replicasets should succeed and call formatter (lines 821-822)."""
        result = cli_runner.invoke(app, ["replicasets", "list"])

        assert result.exit_code == 0
        mock_workload_manager.list_replica_sets.assert_called_once()

    def test_get_replicaset_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workload_manager: MagicMock,
    ) -> None:
        """get_replicaset should succeed and format the resource (lines 841-842)."""
        result = cli_runner.invoke(app, ["replicasets", "get", "my-rs"])

        assert result.exit_code == 0
        mock_workload_manager.get_replica_set.assert_called_once_with("my-rs", None)
