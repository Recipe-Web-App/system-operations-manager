"""Tests for merge utility functions."""

from __future__ import annotations

import pytest

from system_operations_manager.utils.merge import (
    MergeAnalysis,
    analyze_merge_potential,
    compute_auto_merge,
    validate_merged_state,
)


class TestAnalyzeMergePotential:
    """Tests for analyze_merge_potential function."""

    def test_non_overlapping_changes_can_auto_merge(self) -> None:
        """Test that non-overlapping changes can be auto-merged."""
        source = {"host": "new-host.com", "port": 8080}
        target = {"host": "old-host.com", "port": 9090}

        # Source changed host, target changed port (compared to baseline)
        baseline = {"host": "old-host.com", "port": 8080}

        analysis = analyze_merge_potential(source, target, baseline)

        assert analysis.can_auto_merge is True
        assert "host" in analysis.source_only_fields
        assert "port" in analysis.target_only_fields
        assert len(analysis.conflicting_fields) == 0

    def test_overlapping_changes_cannot_auto_merge(self) -> None:
        """Test that overlapping changes cannot be auto-merged."""
        source = {"host": "source-host.com", "port": 8080}
        target = {"host": "target-host.com", "port": 8080}
        baseline = {"host": "original-host.com", "port": 8080}

        analysis = analyze_merge_potential(source, target, baseline)

        assert analysis.can_auto_merge is False
        assert "host" in analysis.conflicting_fields

    def test_nested_fields_merge_at_leaf_level(self) -> None:
        """Test that nested objects are analyzed at leaf level."""
        source = {"config": {"timeout": 30, "retries": 3}}
        target = {"config": {"timeout": 60, "retries": 5}}
        baseline = {"config": {"timeout": 60, "retries": 3}}

        # Source changed config.retries (3->3 no change), target changed config.timeout (60->60 no change)
        # Actually: baseline timeout=60, source timeout=30 (changed), target timeout=60 (not changed)
        # baseline retries=3, source retries=3 (not changed), target retries=5 (changed)

        analysis = analyze_merge_potential(source, target, baseline)

        assert analysis.can_auto_merge is True
        assert "config.timeout" in analysis.source_only_fields
        assert "config.retries" in analysis.target_only_fields

    def test_arrays_always_conflict_when_both_changed(self) -> None:
        """Test that arrays changed on both sides always conflict."""
        source = {"tags": ["a", "b", "c"]}
        target = {"tags": ["x", "y"]}
        baseline = {"tags": ["original"]}

        analysis = analyze_merge_potential(source, target, baseline)

        # Both changed the tags array
        assert analysis.can_auto_merge is False
        assert "tags" in analysis.conflicting_fields

    def test_identifies_source_only_fields(self) -> None:
        """Test that source-only changes are correctly identified."""
        source = {"a": 1, "b": 2}
        target = {"a": 1, "b": 1}
        baseline = {"a": 1, "b": 1}

        analysis = analyze_merge_potential(source, target, baseline)

        assert "b" in analysis.source_only_fields
        assert len(analysis.target_only_fields) == 0

    def test_identifies_target_only_fields(self) -> None:
        """Test that target-only changes are correctly identified."""
        source = {"a": 1, "b": 1}
        target = {"a": 1, "b": 2}
        baseline = {"a": 1, "b": 1}

        analysis = analyze_merge_potential(source, target, baseline)

        assert "b" in analysis.target_only_fields
        assert len(analysis.source_only_fields) == 0

    def test_identifies_conflicting_fields(self) -> None:
        """Test that conflicting fields are correctly identified."""
        source = {"value": 100}
        target = {"value": 200}
        baseline = {"value": 0}

        analysis = analyze_merge_potential(source, target, baseline)

        assert "value" in analysis.conflicting_fields
        assert analysis.can_auto_merge is False


class TestComputeAutoMerge:
    """Tests for compute_auto_merge function."""

    def test_combines_non_overlapping_changes(self) -> None:
        """Test that non-overlapping changes are combined correctly."""
        source = {"host": "new-host.com", "port": 8080}
        target = {"host": "old-host.com", "port": 9090}

        analysis = MergeAnalysis(
            can_auto_merge=True,
            source_only_fields=["host"],
            target_only_fields=["port"],
            conflicting_fields=[],
        )

        merged = compute_auto_merge(source, target, analysis)

        # Should have source's host and target's port
        assert merged["host"] == "new-host.com"
        assert merged["port"] == 9090

    def test_preserves_unchanged_fields(self) -> None:
        """Test that unchanged fields are preserved."""
        source = {"a": 1, "b": 2, "unchanged": "same"}
        target = {"a": 1, "b": 1, "unchanged": "same"}

        analysis = MergeAnalysis(
            can_auto_merge=True,
            source_only_fields=["b"],
            target_only_fields=[],
            conflicting_fields=[],
        )

        merged = compute_auto_merge(source, target, analysis)

        assert merged["unchanged"] == "same"
        assert merged["b"] == 2  # From source

    def test_raises_on_conflicting_fields(self) -> None:
        """Test that merge raises when conflicting fields exist."""
        source = {"value": 100}
        target = {"value": 200}

        analysis = MergeAnalysis(
            can_auto_merge=False,
            source_only_fields=[],
            target_only_fields=[],
            conflicting_fields=["value"],
        )

        with pytest.raises(ValueError, match="Cannot auto-merge"):
            compute_auto_merge(source, target, analysis)

    def test_deep_merge_nested_objects(self) -> None:
        """Test that nested objects are merged at leaf level."""
        source = {"config": {"timeout": 30, "retries": 3}}
        target = {"config": {"timeout": 60, "retries": 5}}

        analysis = MergeAnalysis(
            can_auto_merge=True,
            source_only_fields=["config.timeout"],
            target_only_fields=["config.retries"],
            conflicting_fields=[],
        )

        merged = compute_auto_merge(source, target, analysis)

        assert merged["config"]["timeout"] == 30  # From source
        assert merged["config"]["retries"] == 5  # From target

    def test_handles_empty_dicts(self) -> None:
        """Test that empty dicts are handled correctly."""
        source = {"a": 1}
        target: dict[str, int] = {}

        analysis = MergeAnalysis(
            can_auto_merge=True,
            source_only_fields=["a"],
            target_only_fields=[],
            conflicting_fields=[],
        )

        merged = compute_auto_merge(source, target, analysis)

        assert merged["a"] == 1


class TestValidateMergedState:
    """Tests for validate_merged_state function."""

    def test_valid_state_passes(self) -> None:
        """Test that valid state passes validation."""
        merged = {"name": "my-service", "host": "api.example.com", "port": 8080}

        result = validate_merged_state(merged, "services")

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_missing_required_field_fails(self) -> None:
        """Test that missing required field fails validation."""
        merged = {"port": 8080}  # Missing 'name' and 'host'

        result = validate_merged_state(merged, "services")

        assert result.is_valid is False
        assert any("name" in err for err in result.errors)
        assert any("host" in err for err in result.errors)

    def test_type_mismatch_fails(self) -> None:
        """Test that type mismatch fails validation."""
        merged = {"name": "my-service", "host": "api.example.com", "port": "not-a-number"}

        result = validate_merged_state(merged, "services")

        assert result.is_valid is False
        assert any("port" in err and "Type mismatch" in err for err in result.errors)

    def test_unknown_fields_warn(self) -> None:
        """Test that unknown fields generate warnings."""
        merged = {
            "name": "my-service",
            "host": "api.example.com",
            "unknown_field": "value",
        }
        source = {"name": "my-service", "host": "api.example.com"}
        target = {"name": "my-service", "host": "old.example.com"}

        result = validate_merged_state(merged, "services", source, target)

        assert result.is_valid is True  # Unknown fields are warnings, not errors
        assert any("unknown_field" in warn for warn in result.warnings)

    def test_entity_specific_validation(self) -> None:
        """Test that entity-specific required fields are checked."""
        # Route requires 'name'
        route_merged = {"paths": ["/api"]}

        result = validate_merged_state(route_merged, "routes")

        assert result.is_valid is False
        assert any("name" in err for err in result.errors)

        # Consumer requires 'username'
        consumer_merged = {"custom_id": "123"}

        result = validate_merged_state(consumer_merged, "consumers")

        assert result.is_valid is False
        assert any("username" in err for err in result.errors)
