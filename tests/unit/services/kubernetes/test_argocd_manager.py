"""Unit tests for ArgoCDManager."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.services.kubernetes.argocd_manager import (
    APP_PROJECT_PLURAL,
    APPLICATION_PLURAL,
    ARGOCD_GROUP,
    ARGOCD_NAMESPACE,
    ARGOCD_VERSION,
    ArgoCDManager,
)


@pytest.fixture
def mock_k8s_client() -> MagicMock:
    """Create a mock Kubernetes client."""
    mock_client = MagicMock()
    mock_client.default_namespace = "default"
    return mock_client


@pytest.fixture
def argocd_manager(mock_k8s_client: MagicMock) -> ArgoCDManager:
    """Create an ArgoCDManager with mocked client."""
    return ArgoCDManager(mock_k8s_client)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestArgoCDManager:
    """Tests for ArgoCDManager."""

    # =========================================================================
    # Application Tests
    # =========================================================================

    def test_list_applications(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_applications should call custom_objects API."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {
            "items": [
                {
                    "metadata": {"name": "app1", "namespace": "argocd"},
                    "spec": {
                        "project": "default",
                        "source": {"repoURL": "https://github.com/org/repo", "path": "k8s"},
                        "destination": {
                            "server": "https://kubernetes.default.svc",
                            "namespace": "default",
                        },
                    },
                    "status": {
                        "sync": {"status": "Synced"},
                        "health": {"status": "Healthy"},
                    },
                }
            ]
        }

        apps = argocd_manager.list_applications()

        assert len(apps) == 1
        assert apps[0].name == "app1"
        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            ARGOCD_GROUP,
            ARGOCD_VERSION,
            ARGOCD_NAMESPACE,
            APPLICATION_PLURAL,
        )

    def test_list_applications_with_namespace(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_applications should use provided namespace."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

        argocd_manager.list_applications(namespace="production")

        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            ARGOCD_GROUP,
            ARGOCD_VERSION,
            "production",
            APPLICATION_PLURAL,
        )

    def test_list_applications_with_label_selector(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_applications should pass label selector."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

        argocd_manager.list_applications(label_selector="env=prod")

        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            ARGOCD_GROUP,
            ARGOCD_VERSION,
            ARGOCD_NAMESPACE,
            APPLICATION_PLURAL,
            label_selector="env=prod",
        )

    def test_get_application(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_application should retrieve application by name."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {
            "metadata": {"name": "my-app", "namespace": "argocd"},
            "spec": {
                "project": "default",
                "source": {"repoURL": "https://github.com/org/repo", "path": "k8s"},
                "destination": {"server": "https://kubernetes.default.svc", "namespace": "default"},
            },
            "status": {
                "sync": {"status": "Synced"},
                "health": {"status": "Healthy"},
            },
        }

        app = argocd_manager.get_application("my-app")

        assert app.name == "my-app"
        assert app.repo_url == "https://github.com/org/repo"
        mock_k8s_client.custom_objects.get_namespaced_custom_object.assert_called_once_with(
            ARGOCD_GROUP,
            ARGOCD_VERSION,
            ARGOCD_NAMESPACE,
            APPLICATION_PLURAL,
            "my-app",
        )

    def test_create_application(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_application should create new application."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = {
            "metadata": {"name": "my-app", "namespace": "argocd"},
            "spec": {
                "project": "default",
                "source": {
                    "repoURL": "https://github.com/org/repo",
                    "path": "k8s",
                    "targetRevision": "HEAD",
                },
                "destination": {"server": "https://kubernetes.default.svc", "namespace": "default"},
            },
            "status": {},
        }

        app = argocd_manager.create_application(
            "my-app",
            repo_url="https://github.com/org/repo",
            path="k8s",
        )

        assert app.name == "my-app"
        mock_k8s_client.custom_objects.create_namespaced_custom_object.assert_called_once()
        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        assert call_args.args[0] == ARGOCD_GROUP
        assert call_args.args[1] == ARGOCD_VERSION
        assert call_args.args[2] == ARGOCD_NAMESPACE
        assert call_args.args[3] == APPLICATION_PLURAL
        body = call_args.args[4]
        assert body["metadata"]["name"] == "my-app"
        assert body["spec"]["source"]["repoURL"] == "https://github.com/org/repo"

    def test_create_application_with_auto_sync(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_application should include auto-sync policy when enabled."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = {
            "metadata": {"name": "my-app", "namespace": "argocd"},
            "spec": {},
            "status": {},
        }

        argocd_manager.create_application(
            "my-app",
            repo_url="https://github.com/org/repo",
            path="k8s",
            auto_sync=True,
        )

        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args.args[4]
        assert "automated" in body["spec"]["syncPolicy"]
        assert body["spec"]["syncPolicy"]["automated"]["prune"] is True
        assert body["spec"]["syncPolicy"]["automated"]["selfHeal"] is True

    def test_delete_application(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """delete_application should delete application."""
        argocd_manager.delete_application("my-app")

        mock_k8s_client.custom_objects.delete_namespaced_custom_object.assert_called_once_with(
            ARGOCD_GROUP,
            ARGOCD_VERSION,
            ARGOCD_NAMESPACE,
            APPLICATION_PLURAL,
            "my-app",
        )

    def test_sync_application(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """sync_application should trigger sync operation."""
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.return_value = {
            "operation": {
                "sync": {"prune": False, "dryRun": False},
                "initiatedBy": {"username": "ops-cli"},
            }
        }

        result = argocd_manager.sync_application("my-app")

        assert result["name"] == "my-app"
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.assert_called_once()
        call_args = mock_k8s_client.custom_objects.patch_namespaced_custom_object.call_args
        assert call_args.args[4] == "my-app"
        patch = call_args.args[5]
        assert "operation" in patch
        assert "sync" in patch["operation"]

    def test_sync_application_with_revision(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """sync_application should include revision when specified."""
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.return_value = {
            "operation": {"sync": {}}
        }

        argocd_manager.sync_application("my-app", revision="v1.2.3")

        call_args = mock_k8s_client.custom_objects.patch_namespaced_custom_object.call_args
        patch = call_args.args[5]
        assert patch["operation"]["sync"]["revision"] == "v1.2.3"

    def test_rollback_application(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """rollback_application should rollback to previous revision."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {
            "status": {
                "history": [
                    {"revision": "abc123"},
                    {"revision": "def456"},
                ]
            }
        }
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.return_value = {}

        result = argocd_manager.rollback_application("my-app")

        assert result["target_revision"] == "abc123"
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.assert_called_once()

    def test_rollback_application_with_revision_id(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """rollback_application should rollback to specific revision."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {
            "status": {
                "history": [
                    {"revision": "abc123"},
                    {"revision": "def456"},
                    {"revision": "ghi789"},
                ]
            }
        }
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.return_value = {}

        result = argocd_manager.rollback_application("my-app", revision_id=2)

        assert result["target_revision"] == "def456"

    def test_get_application_health(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_application_health should return health status."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {
            "status": {
                "health": {"status": "Healthy", "message": "All good"},
                "resources": [
                    {
                        "kind": "Deployment",
                        "name": "my-deploy",
                        "namespace": "default",
                        "status": "Synced",
                        "health": {"status": "Healthy"},
                    }
                ],
                "conditions": [],
            }
        }

        result = argocd_manager.get_application_health("my-app")

        assert result["health_status"] == "Healthy"
        assert result["message"] == "All good"
        assert len(result["resources"]) == 1

    def test_diff_application(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """diff_application should return sync diff."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {
            "status": {
                "sync": {
                    "status": "Synced",
                    "revision": "abc123",
                    "comparedTo": {
                        "source": {"repoURL": "https://github.com/org/repo"},
                        "destination": {"namespace": "default"},
                    },
                },
                "resources": [
                    {"kind": "Deployment", "name": "deploy1", "status": "Synced"},
                    {"kind": "Service", "name": "svc1", "status": "OutOfSync"},
                ],
            }
        }

        result = argocd_manager.diff_application("my-app")

        assert result["sync_status"] == "Synced"
        assert result["total_resources"] == 2
        assert result["synced_resources"] == 1
        assert len(result["out_of_sync_resources"]) == 1

    # =========================================================================
    # Project Tests
    # =========================================================================

    def test_list_projects(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_projects should call custom_objects API."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {
            "items": [
                {
                    "metadata": {"name": "project1", "namespace": "argocd"},
                    "spec": {
                        "description": "Test project",
                        "sourceRepos": ["*"],
                        "destinations": [],
                    },
                }
            ]
        }

        projects = argocd_manager.list_projects()

        assert len(projects) == 1
        assert projects[0].name == "project1"
        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            ARGOCD_GROUP,
            ARGOCD_VERSION,
            ARGOCD_NAMESPACE,
            APP_PROJECT_PLURAL,
        )

    def test_get_project(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_project should retrieve project by name."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {
            "metadata": {"name": "my-project", "namespace": "argocd"},
            "spec": {
                "description": "My project",
                "sourceRepos": ["https://github.com/org/repo"],
                "destinations": [{"server": "*", "namespace": "*"}],
            },
        }

        project = argocd_manager.get_project("my-project")

        assert project.name == "my-project"
        assert project.description == "My project"
        mock_k8s_client.custom_objects.get_namespaced_custom_object.assert_called_once_with(
            ARGOCD_GROUP,
            ARGOCD_VERSION,
            ARGOCD_NAMESPACE,
            APP_PROJECT_PLURAL,
            "my-project",
        )

    def test_create_project(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_project should create new project."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = {
            "metadata": {"name": "my-project", "namespace": "argocd"},
            "spec": {
                "description": "Test project",
                "sourceRepos": ["*"],
                "destinations": [{"server": "*", "namespace": "*"}],
            },
        }

        project = argocd_manager.create_project(
            "my-project",
            description="Test project",
        )

        assert project.name == "my-project"
        mock_k8s_client.custom_objects.create_namespaced_custom_object.assert_called_once()
        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args.args[4]
        assert body["metadata"]["name"] == "my-project"
        assert body["spec"]["description"] == "Test project"

    def test_create_project_with_source_repos(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_project should include source repos when specified."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = {
            "metadata": {"name": "my-project", "namespace": "argocd"},
            "spec": {},
        }

        argocd_manager.create_project(
            "my-project",
            source_repos=["https://github.com/org/repo1", "https://github.com/org/repo2"],
        )

        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args.args[4]
        assert len(body["spec"]["sourceRepos"]) == 2
        assert "https://github.com/org/repo1" in body["spec"]["sourceRepos"]

    def test_delete_project(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """delete_project should delete project."""
        argocd_manager.delete_project("my-project")

        mock_k8s_client.custom_objects.delete_namespaced_custom_object.assert_called_once_with(
            ARGOCD_GROUP,
            ARGOCD_VERSION,
            ARGOCD_NAMESPACE,
            APP_PROJECT_PLURAL,
            "my-project",
        )


@pytest.mark.unit
@pytest.mark.kubernetes
class TestArgoCDManagerListProjectsLabelSelector:
    """Tests for list_projects label selector branch."""

    def test_list_projects_with_label_selector(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_projects should pass label selector to the custom_objects API."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

        argocd_manager.list_projects(label_selector="team=platform")

        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            ARGOCD_GROUP,
            ARGOCD_VERSION,
            ARGOCD_NAMESPACE,
            APP_PROJECT_PLURAL,
            label_selector="team=platform",
        )


@pytest.mark.unit
@pytest.mark.kubernetes
class TestArgoCDManagerApplicationErrors:
    """Tests for error handling in application operations."""

    def test_list_applications_propagates_api_error(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_applications should invoke _handle_api_error on exception."""
        api_error = RuntimeError("connection refused")
        mock_k8s_client.custom_objects.list_namespaced_custom_object.side_effect = api_error
        sentinel = RuntimeError("translated")
        mock_k8s_client.translate_api_exception.side_effect = sentinel

        with pytest.raises(RuntimeError, match="translated"):
            argocd_manager.list_applications()

        mock_k8s_client.translate_api_exception.assert_called_once_with(
            api_error,
            resource_type="Application",
            resource_name=None,
            namespace=ARGOCD_NAMESPACE,
        )

    def test_get_application_propagates_api_error(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_application should invoke _handle_api_error on exception."""
        api_error = RuntimeError("not found")
        mock_k8s_client.custom_objects.get_namespaced_custom_object.side_effect = api_error
        sentinel = RuntimeError("translated")
        mock_k8s_client.translate_api_exception.side_effect = sentinel

        with pytest.raises(RuntimeError, match="translated"):
            argocd_manager.get_application("missing-app")

        mock_k8s_client.translate_api_exception.assert_called_once_with(
            api_error,
            resource_type="Application",
            resource_name="missing-app",
            namespace=ARGOCD_NAMESPACE,
        )

    def test_create_application_propagates_api_error(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_application should invoke _handle_api_error on exception."""
        api_error = RuntimeError("already exists")
        mock_k8s_client.custom_objects.create_namespaced_custom_object.side_effect = api_error
        sentinel = RuntimeError("translated")
        mock_k8s_client.translate_api_exception.side_effect = sentinel

        with pytest.raises(RuntimeError, match="translated"):
            argocd_manager.create_application(
                "my-app",
                repo_url="https://github.com/org/repo",
                path="k8s",
            )

        mock_k8s_client.translate_api_exception.assert_called_once_with(
            api_error,
            resource_type="Application",
            resource_name="my-app",
            namespace=ARGOCD_NAMESPACE,
        )

    def test_delete_application_propagates_api_error(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """delete_application should invoke _handle_api_error on exception."""
        api_error = RuntimeError("forbidden")
        mock_k8s_client.custom_objects.delete_namespaced_custom_object.side_effect = api_error
        sentinel = RuntimeError("translated")
        mock_k8s_client.translate_api_exception.side_effect = sentinel

        with pytest.raises(RuntimeError, match="translated"):
            argocd_manager.delete_application("my-app")

        mock_k8s_client.translate_api_exception.assert_called_once_with(
            api_error,
            resource_type="Application",
            resource_name="my-app",
            namespace=ARGOCD_NAMESPACE,
        )

    def test_sync_application_propagates_api_error(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """sync_application should invoke _handle_api_error on exception."""
        api_error = RuntimeError("timeout")
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.side_effect = api_error
        sentinel = RuntimeError("translated")
        mock_k8s_client.translate_api_exception.side_effect = sentinel

        with pytest.raises(RuntimeError, match="translated"):
            argocd_manager.sync_application("my-app")

        mock_k8s_client.translate_api_exception.assert_called_once_with(
            api_error,
            resource_type="Application",
            resource_name="my-app",
            namespace=ARGOCD_NAMESPACE,
        )

    def test_get_application_health_propagates_api_error(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_application_health should invoke _handle_api_error on exception."""
        api_error = RuntimeError("server error")
        mock_k8s_client.custom_objects.get_namespaced_custom_object.side_effect = api_error
        sentinel = RuntimeError("translated")
        mock_k8s_client.translate_api_exception.side_effect = sentinel

        with pytest.raises(RuntimeError, match="translated"):
            argocd_manager.get_application_health("my-app")

        mock_k8s_client.translate_api_exception.assert_called_once_with(
            api_error,
            resource_type="Application",
            resource_name="my-app",
            namespace=ARGOCD_NAMESPACE,
        )

    def test_diff_application_propagates_api_error(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """diff_application should invoke _handle_api_error on exception."""
        api_error = RuntimeError("unauthorized")
        mock_k8s_client.custom_objects.get_namespaced_custom_object.side_effect = api_error
        sentinel = RuntimeError("translated")
        mock_k8s_client.translate_api_exception.side_effect = sentinel

        with pytest.raises(RuntimeError, match="translated"):
            argocd_manager.diff_application("my-app")

        mock_k8s_client.translate_api_exception.assert_called_once_with(
            api_error,
            resource_type="Application",
            resource_name="my-app",
            namespace=ARGOCD_NAMESPACE,
        )


@pytest.mark.unit
@pytest.mark.kubernetes
class TestArgoCDManagerRollbackEdgeCases:
    """Tests for rollback_application edge cases and error handling."""

    def test_rollback_application_no_history_returns_error_dict(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """rollback_application should return error dict when no history exists."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {"status": {}}
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.return_value = {}

        result = argocd_manager.rollback_application("my-app")

        assert result["name"] == "my-app"
        assert result["namespace"] == ARGOCD_NAMESPACE
        assert "error" in result
        assert result["error"] == "No deployment history available"
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.assert_not_called()

    def test_rollback_application_empty_history_list_returns_error_dict(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """rollback_application should return error dict when history list is empty."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {
            "status": {"history": []}
        }
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.return_value = {}

        result = argocd_manager.rollback_application("my-app")

        assert result["error"] == "No deployment history available"
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.assert_not_called()

    def test_rollback_application_single_history_entry_uses_last(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """rollback_application with single history entry falls back to history[-1]."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {
            "status": {
                "history": [
                    {"revision": "only123"},
                ]
            }
        }
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.return_value = {}

        result = argocd_manager.rollback_application("my-app")

        assert result["target_revision"] == "only123"

    def test_rollback_application_propagates_api_error(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """rollback_application should invoke _handle_api_error on exception."""
        api_error = RuntimeError("api failure")
        mock_k8s_client.custom_objects.get_namespaced_custom_object.side_effect = api_error
        sentinel = RuntimeError("translated")
        mock_k8s_client.translate_api_exception.side_effect = sentinel

        with pytest.raises(RuntimeError, match="translated"):
            argocd_manager.rollback_application("my-app")

        mock_k8s_client.translate_api_exception.assert_called_once_with(
            api_error,
            resource_type="Application",
            resource_name="my-app",
            namespace=ARGOCD_NAMESPACE,
        )


@pytest.mark.unit
@pytest.mark.kubernetes
class TestArgoCDManagerProjectErrors:
    """Tests for error handling in AppProject operations."""

    def test_list_projects_propagates_api_error(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_projects should invoke _handle_api_error on exception."""
        api_error = RuntimeError("connection refused")
        mock_k8s_client.custom_objects.list_namespaced_custom_object.side_effect = api_error
        sentinel = RuntimeError("translated")
        mock_k8s_client.translate_api_exception.side_effect = sentinel

        with pytest.raises(RuntimeError, match="translated"):
            argocd_manager.list_projects()

        mock_k8s_client.translate_api_exception.assert_called_once_with(
            api_error,
            resource_type="AppProject",
            resource_name=None,
            namespace=ARGOCD_NAMESPACE,
        )

    def test_get_project_propagates_api_error(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_project should invoke _handle_api_error on exception."""
        api_error = RuntimeError("not found")
        mock_k8s_client.custom_objects.get_namespaced_custom_object.side_effect = api_error
        sentinel = RuntimeError("translated")
        mock_k8s_client.translate_api_exception.side_effect = sentinel

        with pytest.raises(RuntimeError, match="translated"):
            argocd_manager.get_project("missing-project")

        mock_k8s_client.translate_api_exception.assert_called_once_with(
            api_error,
            resource_type="AppProject",
            resource_name="missing-project",
            namespace=ARGOCD_NAMESPACE,
        )

    def test_create_project_propagates_api_error(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_project should invoke _handle_api_error on exception."""
        api_error = RuntimeError("conflict")
        mock_k8s_client.custom_objects.create_namespaced_custom_object.side_effect = api_error
        sentinel = RuntimeError("translated")
        mock_k8s_client.translate_api_exception.side_effect = sentinel

        with pytest.raises(RuntimeError, match="translated"):
            argocd_manager.create_project("my-project")

        mock_k8s_client.translate_api_exception.assert_called_once_with(
            api_error,
            resource_type="AppProject",
            resource_name="my-project",
            namespace=ARGOCD_NAMESPACE,
        )

    def test_delete_project_propagates_api_error(
        self,
        argocd_manager: ArgoCDManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """delete_project should invoke _handle_api_error on exception."""
        api_error = RuntimeError("forbidden")
        mock_k8s_client.custom_objects.delete_namespaced_custom_object.side_effect = api_error
        sentinel = RuntimeError("translated")
        mock_k8s_client.translate_api_exception.side_effect = sentinel

        with pytest.raises(RuntimeError, match="translated"):
            argocd_manager.delete_project("my-project")

        mock_k8s_client.translate_api_exception.assert_called_once_with(
            api_error,
            resource_type="AppProject",
            resource_name="my-project",
            namespace=ARGOCD_NAMESPACE,
        )
