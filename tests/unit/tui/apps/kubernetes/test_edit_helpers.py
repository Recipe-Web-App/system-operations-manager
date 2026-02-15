"""Unit tests for Kubernetes TUI edit helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from system_operations_manager.tui.apps.kubernetes.edit_helpers import (
    RESOURCE_API_MAP,
    _strip_server_fields,
    apply_patch,
    fetch_raw_resource,
)
from system_operations_manager.tui.apps.kubernetes.types import (
    EDITABLE_TYPES,
    ResourceType,
)


@pytest.fixture
def mock_client() -> MagicMock:
    mock = MagicMock()
    mock.default_namespace = "default"
    return mock


class TestStripServerFields:
    @pytest.mark.unit
    def test_strips_status(self) -> None:
        obj = {"metadata": {"name": "test"}, "spec": {}, "status": {"phase": "Running"}}
        result = _strip_server_fields(obj)
        assert "status" not in result

    @pytest.mark.unit
    def test_strips_managed_fields(self) -> None:
        obj = {"metadata": {"name": "test", "managedFields": [{}], "uid": "abc123"}}
        result = _strip_server_fields(obj)
        assert "managedFields" not in result["metadata"]
        assert "uid" not in result["metadata"]

    @pytest.mark.unit
    def test_preserves_user_fields(self) -> None:
        obj = {"metadata": {"name": "test", "labels": {"app": "foo"}}, "spec": {"replicas": 3}}
        result = _strip_server_fields(obj)
        assert result["metadata"]["name"] == "test"
        assert result["metadata"]["labels"] == {"app": "foo"}
        assert result["spec"]["replicas"] == 3


class TestResourceApiMap:
    @pytest.mark.unit
    def test_all_editable_types_in_map(self) -> None:
        for rt in EDITABLE_TYPES:
            assert rt in RESOURCE_API_MAP, f"{rt} missing from RESOURCE_API_MAP"


class TestFetchRawResource:
    @pytest.mark.unit
    def test_fetch_namespaced(self, mock_client: MagicMock) -> None:
        mock_raw = MagicMock()
        mock_client.apps_v1.read_namespaced_deployment.return_value = mock_raw

        with patch("kubernetes.client.ApiClient") as mock_api_client_cls:
            mock_api_client = MagicMock()
            mock_api_client.sanitize_for_serialization.return_value = {
                "metadata": {"name": "test", "managedFields": [{}]},
                "spec": {},
                "status": {},
            }
            mock_api_client_cls.return_value = mock_api_client

            result = fetch_raw_resource(mock_client, ResourceType.DEPLOYMENTS, "test", "default")

            assert "status" not in result
            assert "managedFields" not in result.get("metadata", {})

    @pytest.mark.unit
    def test_fetch_cluster_scoped(self, mock_client: MagicMock) -> None:
        mock_raw = MagicMock()
        mock_client.core_v1.read_namespace.return_value = mock_raw

        with patch("kubernetes.client.ApiClient") as mock_api_client_cls:
            mock_api_client = MagicMock()
            mock_api_client.sanitize_for_serialization.return_value = {
                "metadata": {"name": "test"},
            }
            mock_api_client_cls.return_value = mock_api_client

            result = fetch_raw_resource(mock_client, ResourceType.NAMESPACES, "test", None)

            mock_client.core_v1.read_namespace.assert_called_once_with(name="test")
            assert result["metadata"]["name"] == "test"


class TestApplyPatch:
    @pytest.mark.unit
    def test_apply_namespaced(self, mock_client: MagicMock) -> None:
        patch_body = {"spec": {"replicas": 5}}
        apply_patch(mock_client, ResourceType.DEPLOYMENTS, "test", "default", patch_body)
        mock_client.apps_v1.patch_namespaced_deployment.assert_called_once_with(
            name="test", namespace="default", body=patch_body
        )

    @pytest.mark.unit
    def test_apply_cluster_scoped(self, mock_client: MagicMock) -> None:
        patch_body = {"metadata": {"labels": {"env": "test"}}}
        apply_patch(mock_client, ResourceType.NAMESPACES, "test", None, patch_body)
        mock_client.core_v1.patch_namespace.assert_called_once_with(name="test", body=patch_body)
