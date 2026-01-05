"""Integration tests for UpstreamManager."""

from __future__ import annotations

import pytest

from system_operations_manager.integrations.kong.exceptions import KongNotFoundError
from system_operations_manager.services.kong.upstream_manager import UpstreamManager


@pytest.mark.integration
@pytest.mark.kong
class TestUpstreamManagerList:
    """Test upstream listing operations."""

    def test_list_all_upstreams(
        self,
        upstream_manager: UpstreamManager,
    ) -> None:
        """list should return upstreams from declarative config."""
        upstreams, _ = upstream_manager.list()

        assert len(upstreams) >= 1
        assert any(u.name == "test-upstream" for u in upstreams)

    def test_list_with_pagination(
        self,
        upstream_manager: UpstreamManager,
    ) -> None:
        """list should support pagination."""
        upstreams, _ = upstream_manager.list(limit=1)

        assert len(upstreams) <= 1


@pytest.mark.integration
@pytest.mark.kong
class TestUpstreamManagerGet:
    """Test upstream retrieval operations."""

    def test_get_upstream_by_name(
        self,
        upstream_manager: UpstreamManager,
    ) -> None:
        """get should retrieve upstream by name."""
        upstream = upstream_manager.get("test-upstream")

        assert upstream.name == "test-upstream"
        assert upstream.algorithm == "round-robin"

    def test_get_nonexistent_upstream_raises(
        self,
        upstream_manager: UpstreamManager,
    ) -> None:
        """get should raise KongNotFoundError for missing upstream."""
        with pytest.raises(KongNotFoundError):
            upstream_manager.get("nonexistent-upstream")

    def test_exists_returns_true_for_existing(
        self,
        upstream_manager: UpstreamManager,
    ) -> None:
        """exists should return True for existing upstream."""
        assert upstream_manager.exists("test-upstream") is True

    def test_exists_returns_false_for_missing(
        self,
        upstream_manager: UpstreamManager,
    ) -> None:
        """exists should return False for missing upstream."""
        assert upstream_manager.exists("nonexistent") is False


@pytest.mark.integration
@pytest.mark.kong
class TestUpstreamTargets:
    """Test upstream target operations."""

    def test_list_targets(
        self,
        upstream_manager: UpstreamManager,
    ) -> None:
        """list_targets should return targets for upstream."""
        targets, _ = upstream_manager.list_targets("test-upstream")

        assert len(targets) >= 1
        assert any("httpbin.org" in t.target for t in targets)

    def test_list_targets_with_weight(
        self,
        upstream_manager: UpstreamManager,
    ) -> None:
        """list_targets should include weight information."""
        targets, _ = upstream_manager.list_targets("test-upstream")

        for target in targets:
            # All targets should have a weight
            assert target.weight is not None
            assert target.weight >= 0

    def test_list_targets_nonexistent_upstream(
        self,
        upstream_manager: UpstreamManager,
    ) -> None:
        """list_targets for nonexistent upstream should raise error."""
        with pytest.raises(KongNotFoundError):
            upstream_manager.list_targets("nonexistent-upstream")


@pytest.mark.integration
@pytest.mark.kong
class TestUpstreamHealth:
    """Test upstream health operations."""

    def test_get_upstream_health(
        self,
        upstream_manager: UpstreamManager,
    ) -> None:
        """get_health should return health status."""
        health = upstream_manager.get_health("test-upstream")

        assert health is not None
        # Health data contains per-target health information
        assert health.data is not None
        assert len(health.data) >= 1
        # Each target should have health status
        for target_health in health.data:
            assert target_health.get("health") in ("HEALTHY", "UNHEALTHY", "HEALTHCHECKS_OFF")

    def test_get_targets_health(
        self,
        upstream_manager: UpstreamManager,
    ) -> None:
        """get_targets_health should return target health data."""
        targets_health = upstream_manager.get_targets_health("test-upstream")

        assert isinstance(targets_health, list)
        # Should have at least one target
        assert len(targets_health) >= 1

    def test_get_health_nonexistent_upstream(
        self,
        upstream_manager: UpstreamManager,
    ) -> None:
        """get_health for nonexistent upstream should raise error."""
        with pytest.raises(KongNotFoundError):
            upstream_manager.get_health("nonexistent-upstream")


@pytest.mark.integration
@pytest.mark.kong
class TestUpstreamCount:
    """Test upstream count operations."""

    def test_count_upstreams(
        self,
        upstream_manager: UpstreamManager,
    ) -> None:
        """count should return total number of upstreams."""
        count = upstream_manager.count()

        assert count >= 1  # At least test-upstream
