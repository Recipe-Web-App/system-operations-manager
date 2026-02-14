"""Fixtures for manifest command tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from system_operations_manager.services.kubernetes.manifest_manager import (
    ApplyResult,
    DiffResult,
    ValidationResult,
)


@pytest.fixture
def sample_valid_manifest() -> dict[str, object]:
    """A valid Kubernetes manifest dict."""
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "test-app", "namespace": "default"},
        "spec": {
            "replicas": 1,
            "selector": {"matchLabels": {"app": "test-app"}},
            "template": {
                "metadata": {"labels": {"app": "test-app"}},
                "spec": {"containers": [{"name": "app", "image": "nginx:latest"}]},
            },
        },
    }


@pytest.fixture
def sample_validation_ok() -> ValidationResult:
    """A passing validation result."""
    return ValidationResult(
        file="test.yaml",
        resource="Deployment/test-app",
        valid=True,
    )


@pytest.fixture
def sample_validation_fail() -> ValidationResult:
    """A failing validation result."""
    return ValidationResult(
        file="bad.yaml",
        resource="Unknown/unnamed",
        valid=False,
        errors=["Missing required field: apiVersion"],
    )


@pytest.fixture
def sample_apply_created() -> ApplyResult:
    """An apply result for a newly created resource."""
    return ApplyResult(
        resource="Deployment/test-app",
        action="created",
        namespace="default",
        success=True,
        message="",
    )


@pytest.fixture
def sample_apply_failed() -> ApplyResult:
    """An apply result for a failed resource."""
    return ApplyResult(
        resource="Deployment/bad-app",
        action="failed",
        namespace="default",
        success=False,
        message="Forbidden",
    )


@pytest.fixture
def sample_diff_changed() -> DiffResult:
    """A diff result showing changes."""
    return DiffResult(
        resource="Deployment/test-app",
        namespace="default",
        diff="--- live/Deployment/test-app\n+++ local/Deployment/test-app\n@@ -1 +1 @@\n- replicas: 1\n+ replicas: 3",
        exists_on_cluster=True,
        identical=False,
    )


@pytest.fixture
def sample_diff_identical() -> DiffResult:
    """A diff result showing no changes."""
    return DiffResult(
        resource="Deployment/test-app",
        namespace="default",
        diff="",
        exists_on_cluster=True,
        identical=True,
    )


@pytest.fixture
def tmp_manifest_file(tmp_path: Path) -> Path:
    """Create a temporary YAML manifest file."""
    manifest = tmp_path / "deployment.yaml"
    manifest.write_text(
        "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: test-app\nspec:\n  replicas: 1\n"
    )
    return manifest
