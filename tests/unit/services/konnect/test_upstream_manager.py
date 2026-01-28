"""Unit tests for KonnectUpstreamManager."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kong.models.upstream import Target, Upstream
from system_operations_manager.integrations.konnect.exceptions import KonnectNotFoundError
from system_operations_manager.services.konnect.upstream_manager import KonnectUpstreamManager


@pytest.fixture
def mock_konnect_client() -> MagicMock:
    """Create a mock Konnect client."""
    return MagicMock()


@pytest.fixture
def upstream_manager(mock_konnect_client: MagicMock) -> KonnectUpstreamManager:
    """Create a KonnectUpstreamManager with mock client."""
    return KonnectUpstreamManager(mock_konnect_client, "cp-123")


class TestKonnectUpstreamManagerInit:
    """Tests for KonnectUpstreamManager initialization."""

    @pytest.mark.unit
    def test_initialization(self, mock_konnect_client: MagicMock) -> None:
        """Manager should initialize with client and control plane ID."""
        manager = KonnectUpstreamManager(mock_konnect_client, "cp-123")
        assert manager.control_plane_id == "cp-123"

    @pytest.mark.unit
    def test_control_plane_id_property(self, upstream_manager: KonnectUpstreamManager) -> None:
        """control_plane_id property should return the ID."""
        assert upstream_manager.control_plane_id == "cp-123"


class TestKonnectUpstreamManagerList:
    """Tests for list operations."""

    @pytest.mark.unit
    def test_list_upstreams(
        self,
        upstream_manager: KonnectUpstreamManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """list should return upstreams from client."""
        expected_upstreams = [
            Upstream(name="upstream-1"),
            Upstream(name="upstream-2"),
        ]
        mock_konnect_client.list_upstreams.return_value = (expected_upstreams, None)

        upstreams, _next_offset = upstream_manager.list()

        assert len(upstreams) == 2
        assert upstreams[0].name == "upstream-1"
        mock_konnect_client.list_upstreams.assert_called_once_with(
            "cp-123", tags=None, limit=None, offset=None
        )

    @pytest.mark.unit
    def test_list_with_filters(
        self,
        upstream_manager: KonnectUpstreamManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """list should pass filters to client."""
        mock_konnect_client.list_upstreams.return_value = ([], None)

        upstream_manager.list(tags=["prod"], limit=10, offset="abc")

        mock_konnect_client.list_upstreams.assert_called_once_with(
            "cp-123", tags=["prod"], limit=10, offset="abc"
        )


class TestKonnectUpstreamManagerGet:
    """Tests for get operations."""

    @pytest.mark.unit
    def test_get_upstream(
        self,
        upstream_manager: KonnectUpstreamManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """get should return upstream from client."""
        expected = Upstream(name="test-upstream")
        mock_konnect_client.get_upstream.return_value = expected

        result = upstream_manager.get("test-upstream")

        assert result.name == "test-upstream"
        mock_konnect_client.get_upstream.assert_called_once_with("cp-123", "test-upstream")

    @pytest.mark.unit
    def test_get_upstream_not_found(
        self,
        upstream_manager: KonnectUpstreamManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """get should raise NotFoundError when upstream doesn't exist."""
        mock_konnect_client.get_upstream.side_effect = KonnectNotFoundError(
            "Upstream not found", status_code=404
        )

        with pytest.raises(KonnectNotFoundError):
            upstream_manager.get("nonexistent")


class TestKonnectUpstreamManagerExists:
    """Tests for exists operations."""

    @pytest.mark.unit
    def test_exists_returns_true(
        self,
        upstream_manager: KonnectUpstreamManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """exists should return True when upstream exists."""
        mock_konnect_client.get_upstream.return_value = Upstream(name="test")

        assert upstream_manager.exists("test") is True

    @pytest.mark.unit
    def test_exists_returns_false(
        self,
        upstream_manager: KonnectUpstreamManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """exists should return False when upstream doesn't exist."""
        mock_konnect_client.get_upstream.side_effect = KonnectNotFoundError(
            "Upstream not found", status_code=404
        )

        assert upstream_manager.exists("nonexistent") is False


class TestKonnectUpstreamManagerCreate:
    """Tests for create operations."""

    @pytest.mark.unit
    def test_create_upstream(
        self,
        upstream_manager: KonnectUpstreamManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """create should create upstream via client."""
        upstream = Upstream(name="new-upstream")
        created = Upstream(id="upstream-new", name="new-upstream")
        mock_konnect_client.create_upstream.return_value = created

        result = upstream_manager.create(upstream)

        assert result.id == "upstream-new"
        mock_konnect_client.create_upstream.assert_called_once_with("cp-123", upstream)


class TestKonnectUpstreamManagerUpdate:
    """Tests for update operations."""

    @pytest.mark.unit
    def test_update_upstream(
        self,
        upstream_manager: KonnectUpstreamManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """update should update upstream via client."""
        upstream = Upstream(name="test-upstream", slots=1000)
        updated = Upstream(id="upstream-1", name="test-upstream", slots=1000)
        mock_konnect_client.update_upstream.return_value = updated

        result = upstream_manager.update("test-upstream", upstream)

        assert result.slots == 1000
        mock_konnect_client.update_upstream.assert_called_once_with(
            "cp-123", "test-upstream", upstream
        )


class TestKonnectUpstreamManagerDelete:
    """Tests for delete operations."""

    @pytest.mark.unit
    def test_delete_upstream(
        self,
        upstream_manager: KonnectUpstreamManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """delete should delete upstream via client."""
        upstream_manager.delete("test-upstream")

        mock_konnect_client.delete_upstream.assert_called_once_with("cp-123", "test-upstream")


class TestKonnectUpstreamManagerTargets:
    """Tests for target operations."""

    @pytest.mark.unit
    def test_list_targets(
        self,
        upstream_manager: KonnectUpstreamManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """list_targets should return targets from client."""
        expected_targets = [
            Target(target="192.168.1.1:8000", weight=100),
            Target(target="192.168.1.2:8000", weight=100),
        ]
        mock_konnect_client.list_targets.return_value = (expected_targets, None)

        targets, _next_offset = upstream_manager.list_targets("my-upstream")

        assert len(targets) == 2
        assert targets[0].target == "192.168.1.1:8000"
        mock_konnect_client.list_targets.assert_called_once_with(
            "cp-123", "my-upstream", limit=None, offset=None
        )

    @pytest.mark.unit
    def test_add_target(
        self,
        upstream_manager: KonnectUpstreamManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """add_target should add target via client."""
        target = Target(target="192.168.1.3:8000", weight=100)
        created = Target(id="target-new", target="192.168.1.3:8000", weight=100)
        mock_konnect_client.create_target.return_value = created

        result = upstream_manager.add_target("my-upstream", target)

        assert result.id == "target-new"
        mock_konnect_client.create_target.assert_called_once_with("cp-123", "my-upstream", target)

    @pytest.mark.unit
    def test_delete_target(
        self,
        upstream_manager: KonnectUpstreamManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """delete_target should delete target via client."""
        upstream_manager.delete_target("my-upstream", "target-123")

        mock_konnect_client.delete_target.assert_called_once_with(
            "cp-123", "my-upstream", "target-123"
        )
