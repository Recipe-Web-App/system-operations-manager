"""Tests for target sync functionality in sync push and sync pull commands."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kong.models.unified import UnifiedEntityList
from system_operations_manager.integrations.kong.models.upstream import Target
from system_operations_manager.plugins.kong.commands.sync import (
    _pull_targets_for_upstreams,
    _push_targets_for_upstreams,
)


@pytest.mark.unit
class TestPushTargetsForUpstreams:
    """Tests for _push_targets_for_upstreams helper."""

    def test_push_targets_creates_gateway_only_targets(
        self,
        mock_unified_service: MagicMock,
        mock_konnect_upstream_manager: MagicMock,
        sample_gateway_only_targets: UnifiedEntityList[Target],
    ) -> None:
        """Test that targets only in Gateway are created in Konnect."""
        mock_unified_service.list_targets_for_upstream.return_value = sample_gateway_only_targets

        created, updated, errors = _push_targets_for_upstreams(
            unified_service=mock_unified_service,
            upstreams=["backend-upstream"],
            konnect_upstream_manager=mock_konnect_upstream_manager,
            dry_run=False,
        )

        assert created == 2
        assert updated == 0
        assert errors == 0
        assert mock_konnect_upstream_manager.add_target.call_count == 2

    def test_push_targets_dry_run_no_changes(
        self,
        mock_unified_service: MagicMock,
        mock_konnect_upstream_manager: MagicMock,
        sample_gateway_only_targets: UnifiedEntityList[Target],
    ) -> None:
        """Test that dry run doesn't create targets."""
        mock_unified_service.list_targets_for_upstream.return_value = sample_gateway_only_targets

        created, updated, errors = _push_targets_for_upstreams(
            unified_service=mock_unified_service,
            upstreams=["backend-upstream"],
            konnect_upstream_manager=mock_konnect_upstream_manager,
            dry_run=True,
        )

        assert created == 2
        assert updated == 0
        assert errors == 0
        mock_konnect_upstream_manager.add_target.assert_not_called()

    def test_push_targets_handles_errors(
        self,
        mock_unified_service: MagicMock,
        mock_konnect_upstream_manager: MagicMock,
        sample_gateway_only_targets: UnifiedEntityList[Target],
    ) -> None:
        """Test that errors during target creation are counted."""
        mock_unified_service.list_targets_for_upstream.return_value = sample_gateway_only_targets
        mock_konnect_upstream_manager.add_target.side_effect = Exception("API error")

        created, updated, errors = _push_targets_for_upstreams(
            unified_service=mock_unified_service,
            upstreams=["backend-upstream"],
            konnect_upstream_manager=mock_konnect_upstream_manager,
            dry_run=False,
        )

        assert created == 0
        assert updated == 0
        assert errors == 2

    def test_push_targets_handles_fetch_error(
        self,
        mock_unified_service: MagicMock,
        mock_konnect_upstream_manager: MagicMock,
    ) -> None:
        """Test that errors fetching targets are handled gracefully."""
        mock_unified_service.list_targets_for_upstream.side_effect = Exception("Fetch error")

        created, updated, errors = _push_targets_for_upstreams(
            unified_service=mock_unified_service,
            upstreams=["backend-upstream"],
            konnect_upstream_manager=mock_konnect_upstream_manager,
            dry_run=False,
        )

        assert created == 0
        assert updated == 0
        assert errors == 0  # Fetch errors are not counted as errors

    def test_push_targets_multiple_upstreams(
        self,
        mock_unified_service: MagicMock,
        mock_konnect_upstream_manager: MagicMock,
        sample_gateway_only_targets: UnifiedEntityList[Target],
    ) -> None:
        """Test that targets are pushed for multiple upstreams."""
        mock_unified_service.list_targets_for_upstream.return_value = sample_gateway_only_targets

        created, _updated, _errors = _push_targets_for_upstreams(
            unified_service=mock_unified_service,
            upstreams=["upstream-1", "upstream-2"],
            konnect_upstream_manager=mock_konnect_upstream_manager,
            dry_run=False,
        )

        assert created == 4  # 2 targets per upstream
        assert mock_unified_service.list_targets_for_upstream.call_count == 2


@pytest.mark.unit
class TestPullTargetsForUpstreams:
    """Tests for _pull_targets_for_upstreams helper."""

    def test_pull_targets_creates_konnect_only_targets(
        self,
        mock_unified_service: MagicMock,
        mock_gateway_upstream_manager: MagicMock,
        sample_konnect_only_targets: UnifiedEntityList[Target],
    ) -> None:
        """Test that targets only in Konnect are created in Gateway."""
        mock_unified_service.list_targets_for_upstream.return_value = sample_konnect_only_targets

        created, updated, errors = _pull_targets_for_upstreams(
            unified_service=mock_unified_service,
            upstreams=["backend-upstream"],
            gateway_upstream_manager=mock_gateway_upstream_manager,
            dry_run=False,
        )

        assert created == 2
        assert updated == 0
        assert errors == 0
        assert mock_gateway_upstream_manager.add_target.call_count == 2

    def test_pull_targets_dry_run_no_changes(
        self,
        mock_unified_service: MagicMock,
        mock_gateway_upstream_manager: MagicMock,
        sample_konnect_only_targets: UnifiedEntityList[Target],
    ) -> None:
        """Test that dry run doesn't create targets."""
        mock_unified_service.list_targets_for_upstream.return_value = sample_konnect_only_targets

        created, updated, errors = _pull_targets_for_upstreams(
            unified_service=mock_unified_service,
            upstreams=["backend-upstream"],
            gateway_upstream_manager=mock_gateway_upstream_manager,
            dry_run=True,
        )

        assert created == 2
        assert updated == 0
        assert errors == 0
        mock_gateway_upstream_manager.add_target.assert_not_called()

    def test_pull_targets_handles_errors(
        self,
        mock_unified_service: MagicMock,
        mock_gateway_upstream_manager: MagicMock,
        sample_konnect_only_targets: UnifiedEntityList[Target],
    ) -> None:
        """Test that errors during target creation are counted."""
        mock_unified_service.list_targets_for_upstream.return_value = sample_konnect_only_targets
        mock_gateway_upstream_manager.add_target.side_effect = Exception("API error")

        created, updated, errors = _pull_targets_for_upstreams(
            unified_service=mock_unified_service,
            upstreams=["backend-upstream"],
            gateway_upstream_manager=mock_gateway_upstream_manager,
            dry_run=False,
        )

        assert created == 0
        assert updated == 0
        assert errors == 2

    def test_pull_targets_passes_correct_parameters(
        self,
        mock_unified_service: MagicMock,
        mock_gateway_upstream_manager: MagicMock,
        sample_konnect_only_targets: UnifiedEntityList[Target],
    ) -> None:
        """Test that target parameters are correctly passed to Gateway manager."""
        mock_unified_service.list_targets_for_upstream.return_value = sample_konnect_only_targets

        _pull_targets_for_upstreams(
            unified_service=mock_unified_service,
            upstreams=["backend-upstream"],
            gateway_upstream_manager=mock_gateway_upstream_manager,
            dry_run=False,
        )

        # Check first call parameters
        call_args = mock_gateway_upstream_manager.add_target.call_args_list[0]
        assert call_args[0][0] == "backend-upstream"
        assert call_args[1]["target"] == "konnect-server1.local:8080"
        assert call_args[1]["weight"] == 50
