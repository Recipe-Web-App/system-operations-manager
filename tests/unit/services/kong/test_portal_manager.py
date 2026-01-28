"""Unit tests for Kong PortalManager."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kong.exceptions import KongNotFoundError
from system_operations_manager.services.kong.portal_manager import PortalManager


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock Kong Admin client."""
    return MagicMock()


@pytest.fixture
def manager(mock_client: MagicMock) -> PortalManager:
    """Create a PortalManager with mocked client."""
    return PortalManager(mock_client)


class TestPortalManagerInit:
    """Tests for PortalManager initialization."""

    @pytest.mark.unit
    def test_portal_manager_initialization(self, mock_client: MagicMock) -> None:
        """Manager should initialize with client."""
        manager = PortalManager(mock_client)

        assert manager._client is mock_client


class TestPortalManagerGetStatus:
    """Tests for get_status method."""

    @pytest.mark.unit
    def test_get_status_enabled(self, manager: PortalManager, mock_client: MagicMock) -> None:
        """get_status should return portal status when enabled."""
        mock_client.get.return_value = {
            "name": "default",
            "config": {
                "portal": True,
                "portal_gui_host": "portal.example.com",
                "portal_api_uri": "https://api.example.com",
                "portal_auth": "basic-auth",
                "portal_auto_approve": True,
            },
        }

        status = manager.get_status()

        assert status.enabled is True
        assert status.portal_gui_host == "portal.example.com"
        assert status.portal_api_uri == "https://api.example.com"
        assert status.portal_auth == "basic-auth"
        assert status.portal_auto_approve is True
        mock_client.get.assert_called_once_with("workspaces/default")

    @pytest.mark.unit
    def test_get_status_disabled(self, manager: PortalManager, mock_client: MagicMock) -> None:
        """get_status should return disabled status."""
        mock_client.get.return_value = {
            "name": "default",
            "config": {"portal": False},
        }

        status = manager.get_status()

        assert status.enabled is False

    @pytest.mark.unit
    def test_get_status_no_config(self, manager: PortalManager, mock_client: MagicMock) -> None:
        """get_status should handle missing config gracefully."""
        mock_client.get.return_value = {"name": "default"}

        status = manager.get_status()

        assert status.enabled is False

    @pytest.mark.unit
    def test_get_status_error(self, manager: PortalManager, mock_client: MagicMock) -> None:
        """get_status should return disabled on error."""
        mock_client.get.side_effect = Exception("Connection error")

        status = manager.get_status()

        assert status.enabled is False


class TestPortalManagerIsEnabled:
    """Tests for is_enabled method."""

    @pytest.mark.unit
    def test_is_enabled_true(self, manager: PortalManager, mock_client: MagicMock) -> None:
        """is_enabled should return True when portal is enabled."""
        mock_client.get.return_value = {"config": {"portal": True}}

        result = manager.is_enabled()

        assert result is True

    @pytest.mark.unit
    def test_is_enabled_false(self, manager: PortalManager, mock_client: MagicMock) -> None:
        """is_enabled should return False when portal is disabled."""
        mock_client.get.return_value = {"config": {"portal": False}}

        result = manager.is_enabled()

        assert result is False


class TestPortalManagerListSpecs:
    """Tests for list_specs method."""

    @pytest.mark.unit
    def test_list_specs_success(self, manager: PortalManager, mock_client: MagicMock) -> None:
        """list_specs should return API specifications."""
        mock_client.get.return_value = {
            "data": [
                {"id": "spec-1", "name": "users-api", "path": "specs/users.yaml", "type": "spec"},
                {"id": "spec-2", "name": "orders-api", "path": "specs/orders.yaml", "type": "spec"},
                {
                    "id": "file-1",
                    "name": "header",
                    "path": "partials/header.html",
                    "type": "partial",
                },
            ]
        }

        specs, offset = manager.list_specs()

        # Should filter to only spec files
        assert len(specs) == 2
        assert specs[0].name == "users-api"
        assert specs[1].name == "orders-api"
        assert offset is None

    @pytest.mark.unit
    def test_list_specs_with_pagination(
        self, manager: PortalManager, mock_client: MagicMock
    ) -> None:
        """list_specs should pass pagination params."""
        mock_client.get.return_value = {
            "data": [{"id": "spec-1", "name": "api", "path": "specs/api.yaml", "type": "spec"}],
            "offset": "next-page",
        }

        specs, offset = manager.list_specs(limit=10, offset="current")

        assert len(specs) == 1
        assert offset == "next-page"
        mock_client.get.assert_called_once_with("files", params={"size": 10, "offset": "current"})

    @pytest.mark.unit
    def test_list_specs_empty(self, manager: PortalManager, mock_client: MagicMock) -> None:
        """list_specs should return empty list when no specs exist."""
        mock_client.get.return_value = {"data": []}

        specs, _offset = manager.list_specs()

        assert len(specs) == 0

    @pytest.mark.unit
    def test_list_specs_error(self, manager: PortalManager, mock_client: MagicMock) -> None:
        """list_specs should return empty list on error."""
        mock_client.get.side_effect = Exception("Connection error")

        specs, offset = manager.list_specs()

        assert len(specs) == 0
        assert offset is None


class TestPortalManagerGetSpec:
    """Tests for get_spec method."""

    @pytest.mark.unit
    def test_get_spec_success(self, manager: PortalManager, mock_client: MagicMock) -> None:
        """get_spec should return specification by path."""
        mock_client.get.return_value = {
            "id": "spec-1",
            "name": "users-api",
            "path": "specs/users.yaml",
            "type": "spec",
            "contents": "openapi: 3.0.0",
        }

        spec = manager.get_spec("specs/users.yaml")

        assert spec.name == "users-api"
        assert spec.path == "specs/users.yaml"
        mock_client.get.assert_called_once_with("files/specs/users.yaml")

    @pytest.mark.unit
    def test_get_spec_not_found(self, manager: PortalManager, mock_client: MagicMock) -> None:
        """get_spec should raise error for non-existent spec."""
        mock_client.get.side_effect = KongNotFoundError(
            resource_type="file", resource_id="specs/nonexistent.yaml"
        )

        with pytest.raises(KongNotFoundError):
            manager.get_spec("specs/nonexistent.yaml")


class TestPortalManagerPublishSpec:
    """Tests for publish_spec method."""

    @pytest.mark.unit
    def test_publish_spec_success(self, manager: PortalManager, mock_client: MagicMock) -> None:
        """publish_spec should publish new specification."""
        mock_client.post.return_value = {
            "id": "spec-new",
            "name": "new-api",
            "path": "specs/new-api.yaml",
            "type": "spec",
        }

        spec = manager.publish_spec("new-api", "openapi: 3.0.0")

        assert spec.name == "new-api"
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "files"
        assert call_args[1]["json"]["name"] == "new-api"
        assert call_args[1]["json"]["path"] == "specs/new-api.yaml"
        assert call_args[1]["json"]["type"] == "spec"

    @pytest.mark.unit
    def test_publish_spec_custom_path(self, manager: PortalManager, mock_client: MagicMock) -> None:
        """publish_spec should use custom path when provided."""
        mock_client.post.return_value = {
            "id": "spec-new",
            "name": "custom-api",
            "path": "custom/path/api.yaml",
            "type": "spec",
        }

        _spec = manager.publish_spec("custom-api", "openapi: 3.0.0", path="custom/path/api.yaml")

        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["path"] == "custom/path/api.yaml"

    @pytest.mark.unit
    def test_publish_spec_update_existing(
        self, manager: PortalManager, mock_client: MagicMock
    ) -> None:
        """publish_spec should update if spec already exists."""
        mock_client.post.side_effect = Exception("Already exists")
        mock_client.patch.return_value = {
            "id": "spec-existing",
            "name": "existing-api",
            "path": "specs/existing-api.yaml",
            "type": "spec",
        }

        spec = manager.publish_spec("existing-api", "openapi: 3.0.0")

        assert spec.name == "existing-api"
        mock_client.patch.assert_called_once()


class TestPortalManagerUpdateSpec:
    """Tests for update_spec method."""

    @pytest.mark.unit
    def test_update_spec_success(self, manager: PortalManager, mock_client: MagicMock) -> None:
        """update_spec should update specification contents."""
        mock_client.patch.return_value = {
            "id": "spec-1",
            "name": "users-api",
            "path": "specs/users.yaml",
            "type": "spec",
            "contents": "openapi: 3.1.0",
        }

        spec = manager.update_spec("specs/users.yaml", "openapi: 3.1.0")

        assert spec.path == "specs/users.yaml"
        mock_client.patch.assert_called_once_with(
            "files/specs/users.yaml", json={"contents": "openapi: 3.1.0"}
        )


class TestPortalManagerDeleteSpec:
    """Tests for delete_spec method."""

    @pytest.mark.unit
    def test_delete_spec_success(self, manager: PortalManager, mock_client: MagicMock) -> None:
        """delete_spec should delete specification."""
        manager.delete_spec("specs/users.yaml")

        mock_client.delete.assert_called_once_with("files/specs/users.yaml")

    @pytest.mark.unit
    def test_delete_spec_not_found(self, manager: PortalManager, mock_client: MagicMock) -> None:
        """delete_spec should raise error for non-existent spec."""
        mock_client.delete.side_effect = KongNotFoundError(
            resource_type="file", resource_id="specs/nonexistent.yaml"
        )

        with pytest.raises(KongNotFoundError):
            manager.delete_spec("specs/nonexistent.yaml")


class TestPortalManagerListFiles:
    """Tests for list_files method."""

    @pytest.mark.unit
    def test_list_files_success(self, manager: PortalManager, mock_client: MagicMock) -> None:
        """list_files should return all portal files."""
        mock_client.get.return_value = {
            "data": [
                {"id": "file-1", "name": "api", "path": "specs/api.yaml", "type": "spec"},
                {
                    "id": "file-2",
                    "name": "header",
                    "path": "partials/header.html",
                    "type": "partial",
                },
                {"id": "file-3", "name": "home", "path": "pages/home.html", "type": "page"},
            ]
        }

        files, offset = manager.list_files()

        assert len(files) == 3
        assert offset is None

    @pytest.mark.unit
    def test_list_files_filter_by_type(
        self, manager: PortalManager, mock_client: MagicMock
    ) -> None:
        """list_files should filter by file type."""
        mock_client.get.return_value = {
            "data": [
                {"id": "file-1", "name": "api", "path": "specs/api.yaml", "type": "spec"},
                {
                    "id": "file-2",
                    "name": "header",
                    "path": "partials/header.html",
                    "type": "partial",
                },
            ]
        }

        files, _offset = manager.list_files(file_type="partial")

        # Only partial files should be returned
        assert len(files) == 1
        assert files[0].type == "partial"

    @pytest.mark.unit
    def test_list_files_error(self, manager: PortalManager, mock_client: MagicMock) -> None:
        """list_files should return empty list on error."""
        mock_client.get.side_effect = Exception("Connection error")

        files, offset = manager.list_files()

        assert len(files) == 0
        assert offset is None


class TestPortalManagerListDevelopers:
    """Tests for list_developers method."""

    @pytest.mark.unit
    def test_list_developers_success(self, manager: PortalManager, mock_client: MagicMock) -> None:
        """list_developers should return registered developers."""
        mock_client.get.return_value = {
            "data": [
                {"id": "dev-1", "email": "alice@example.com", "status": "approved"},
                {"id": "dev-2", "email": "bob@example.com", "status": "pending"},
            ]
        }

        developers, _offset = manager.list_developers()

        assert len(developers) == 2
        assert developers[0].email == "alice@example.com"
        assert developers[1].email == "bob@example.com"
        mock_client.get.assert_called_once_with("developers", params={})

    @pytest.mark.unit
    def test_list_developers_filter_by_status(
        self, manager: PortalManager, mock_client: MagicMock
    ) -> None:
        """list_developers should filter by status."""
        mock_client.get.return_value = {
            "data": [{"id": "dev-1", "email": "alice@example.com", "status": "pending"}]
        }

        _developers, _offset = manager.list_developers(status="pending")

        mock_client.get.assert_called_once_with("developers", params={"status": "pending"})

    @pytest.mark.unit
    def test_list_developers_with_pagination(
        self, manager: PortalManager, mock_client: MagicMock
    ) -> None:
        """list_developers should pass pagination params."""
        mock_client.get.return_value = {
            "data": [{"id": "dev-1", "email": "alice@example.com", "status": "approved"}],
            "offset": "next-page",
        }

        _developers, offset = manager.list_developers(limit=10, offset="current")

        assert offset == "next-page"
        mock_client.get.assert_called_once_with(
            "developers", params={"size": 10, "offset": "current"}
        )

    @pytest.mark.unit
    def test_list_developers_error(self, manager: PortalManager, mock_client: MagicMock) -> None:
        """list_developers should return empty list on error."""
        mock_client.get.side_effect = Exception("Connection error")

        developers, _offset = manager.list_developers()

        assert len(developers) == 0


class TestPortalManagerGetDeveloper:
    """Tests for get_developer method."""

    @pytest.mark.unit
    def test_get_developer_by_email(self, manager: PortalManager, mock_client: MagicMock) -> None:
        """get_developer should return developer by email."""
        mock_client.get.return_value = {
            "id": "dev-1",
            "email": "alice@example.com",
            "status": "approved",
        }

        developer = manager.get_developer("alice@example.com")

        assert developer.email == "alice@example.com"
        mock_client.get.assert_called_once_with("developers/alice@example.com")

    @pytest.mark.unit
    def test_get_developer_not_found(self, manager: PortalManager, mock_client: MagicMock) -> None:
        """get_developer should raise error for non-existent developer."""
        mock_client.get.side_effect = KongNotFoundError(
            resource_type="developer", resource_id="nonexistent@example.com"
        )

        with pytest.raises(KongNotFoundError):
            manager.get_developer("nonexistent@example.com")


class TestPortalManagerApproveDeveloper:
    """Tests for approve_developer method."""

    @pytest.mark.unit
    def test_approve_developer_success(
        self, manager: PortalManager, mock_client: MagicMock
    ) -> None:
        """approve_developer should approve pending developer."""
        mock_client.patch.return_value = {
            "id": "dev-1",
            "email": "alice@example.com",
            "status": "approved",
        }

        developer = manager.approve_developer("alice@example.com")

        assert developer.status == "approved"
        mock_client.patch.assert_called_once_with(
            "developers/alice@example.com", json={"status": "approved"}
        )


class TestPortalManagerRejectDeveloper:
    """Tests for reject_developer method."""

    @pytest.mark.unit
    def test_reject_developer_success(self, manager: PortalManager, mock_client: MagicMock) -> None:
        """reject_developer should reject pending developer."""
        mock_client.patch.return_value = {
            "id": "dev-1",
            "email": "bob@example.com",
            "status": "rejected",
        }

        developer = manager.reject_developer("bob@example.com")

        assert developer.status == "rejected"
        mock_client.patch.assert_called_once_with(
            "developers/bob@example.com", json={"status": "rejected"}
        )


class TestPortalManagerRevokeDeveloper:
    """Tests for revoke_developer method."""

    @pytest.mark.unit
    def test_revoke_developer_success(self, manager: PortalManager, mock_client: MagicMock) -> None:
        """revoke_developer should revoke approved developer."""
        mock_client.patch.return_value = {
            "id": "dev-1",
            "email": "charlie@example.com",
            "status": "revoked",
        }

        developer = manager.revoke_developer("charlie@example.com")

        assert developer.status == "revoked"
        mock_client.patch.assert_called_once_with(
            "developers/charlie@example.com", json={"status": "revoked"}
        )


class TestPortalManagerDeleteDeveloper:
    """Tests for delete_developer method."""

    @pytest.mark.unit
    def test_delete_developer_success(self, manager: PortalManager, mock_client: MagicMock) -> None:
        """delete_developer should delete developer."""
        manager.delete_developer("alice@example.com")

        mock_client.delete.assert_called_once_with("developers/alice@example.com")

    @pytest.mark.unit
    def test_delete_developer_not_found(
        self, manager: PortalManager, mock_client: MagicMock
    ) -> None:
        """delete_developer should raise error for non-existent developer."""
        mock_client.delete.side_effect = KongNotFoundError(
            resource_type="developer", resource_id="nonexistent@example.com"
        )

        with pytest.raises(KongNotFoundError):
            manager.delete_developer("nonexistent@example.com")
