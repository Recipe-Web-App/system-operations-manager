"""Fixtures for kustomize command tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from system_operations_manager.services.kubernetes.kustomize_manager import (
    KustomizeBuildOutput,
    OverlayInfo,
)
from system_operations_manager.services.kubernetes.manifest_manager import (
    ApplyResult,
    DiffResult,
)


@pytest.fixture
def sample_build_success() -> KustomizeBuildOutput:
    """Successful build result."""
    return KustomizeBuildOutput(
        path="/test/base",
        rendered_yaml="apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: test\n",
        success=True,
    )


@pytest.fixture
def sample_build_failure() -> KustomizeBuildOutput:
    """Failed build result."""
    return KustomizeBuildOutput(
        path="/test/base",
        rendered_yaml="",
        success=False,
        error="Invalid kustomization.yaml",
    )


@pytest.fixture
def sample_apply_created() -> ApplyResult:
    """An apply result for a newly created resource."""
    return ApplyResult(
        resource="ConfigMap/test",
        action="created",
        namespace="default",
        success=True,
        message="",
    )


@pytest.fixture
def sample_apply_failed() -> ApplyResult:
    """An apply result for a failed resource."""
    return ApplyResult(
        resource="ConfigMap/test",
        action="failed",
        namespace="default",
        success=False,
        message="Forbidden",
    )


@pytest.fixture
def sample_diff_changed() -> DiffResult:
    """A diff result showing changes."""
    return DiffResult(
        resource="ConfigMap/test",
        namespace="default",
        diff="--- live\n+++ local\n@@ -1 +1 @@\n- value: old\n+ value: new",
        exists_on_cluster=True,
        identical=False,
    )


@pytest.fixture
def sample_diff_identical() -> DiffResult:
    """A diff result showing no changes."""
    return DiffResult(
        resource="ConfigMap/test",
        namespace="default",
        diff="",
        exists_on_cluster=True,
        identical=True,
    )


@pytest.fixture
def sample_overlay_info() -> list[OverlayInfo]:
    """Sample overlay info list."""
    return [
        OverlayInfo(
            name="base",
            path="/test/base",
            valid=True,
            resources=["ConfigMap/app-config"],
        ),
        OverlayInfo(
            name="dev",
            path="/test/overlays/dev",
            valid=True,
            resources=["ConfigMap/app-config", "Deployment/app"],
        ),
    ]


@pytest.fixture
def tmp_kustomization_dir(tmp_path: Path) -> Path:
    """Create a temp directory with kustomization.yaml."""
    d = tmp_path / "base"
    d.mkdir()
    (d / "kustomization.yaml").write_text(
        "apiVersion: kustomize.config.k8s.io/v1beta1\nkind: Kustomization\n"
    )
    return d
