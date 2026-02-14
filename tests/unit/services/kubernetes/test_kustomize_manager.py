"""Unit tests for KustomizeManager."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from system_operations_manager.integrations.kubernetes.kustomize_client import (
    KustomizeBuildResult,
)
from system_operations_manager.services.kubernetes.kustomize_manager import (
    KustomizeManager,
)


@pytest.fixture
def mock_k8s_client() -> MagicMock:
    """Create a mock Kubernetes client."""
    mock_client = MagicMock()
    mock_client.default_namespace = "default"
    return mock_client


@pytest.fixture
def mock_kustomize_client() -> MagicMock:
    """Create a mock KustomizeClient."""
    return MagicMock()


@pytest.fixture
def kustomize_manager(
    mock_k8s_client: MagicMock,
    mock_kustomize_client: MagicMock,
) -> KustomizeManager:
    """Create a KustomizeManager with mocked clients."""
    return KustomizeManager(mock_k8s_client, mock_kustomize_client)


SAMPLE_YAML = "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: test\n"


# ===========================================================================
# TestBuild
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestBuild:
    """Tests for KustomizeManager.build."""

    def test_build_success(
        self,
        kustomize_manager: KustomizeManager,
        mock_kustomize_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should build kustomization successfully."""
        d = tmp_path / "base"
        d.mkdir()

        mock_kustomize_client.build.return_value = KustomizeBuildResult(
            rendered_yaml=SAMPLE_YAML,
            kustomization_path=str(d),
            success=True,
        )

        result = kustomize_manager.build(d)

        assert result.success is True
        assert "ConfigMap" in result.rendered_yaml
        mock_kustomize_client.build.assert_called_once()

    def test_build_failure(
        self,
        kustomize_manager: KustomizeManager,
        mock_kustomize_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should return error on build failure."""
        d = tmp_path / "bad"

        mock_kustomize_client.build.return_value = KustomizeBuildResult(
            rendered_yaml="",
            kustomization_path=str(d),
            success=False,
            error="Invalid kustomization",
        )

        result = kustomize_manager.build(d)

        assert result.success is False
        assert result.error == "Invalid kustomization"

    def test_build_writes_to_file(
        self,
        kustomize_manager: KustomizeManager,
        mock_kustomize_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should write rendered YAML to file when output_file specified."""
        d = tmp_path / "base"
        output_file = tmp_path / "rendered.yaml"

        mock_kustomize_client.build.return_value = KustomizeBuildResult(
            rendered_yaml=SAMPLE_YAML,
            kustomization_path=str(d),
            success=True,
        )

        result = kustomize_manager.build(d, output_file=output_file)

        assert result.success is True
        assert output_file.exists()
        assert "ConfigMap" in output_file.read_text()
        assert result.output_file == str(output_file)

    def test_build_file_write_error(
        self,
        kustomize_manager: KustomizeManager,
        mock_kustomize_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should handle file write errors."""
        d = tmp_path / "base"
        output_file = tmp_path / "nonexistent_dir" / "out.yaml"

        mock_kustomize_client.build.return_value = KustomizeBuildResult(
            rendered_yaml=SAMPLE_YAML,
            kustomization_path=str(d),
            success=True,
        )

        result = kustomize_manager.build(d, output_file=output_file)

        assert result.success is False
        assert "Failed to write" in (result.error or "")

    def test_build_passes_helm_flag(
        self,
        kustomize_manager: KustomizeManager,
        mock_kustomize_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should pass enable_helm to kustomize client."""
        d = tmp_path / "base"

        mock_kustomize_client.build.return_value = KustomizeBuildResult(
            rendered_yaml=SAMPLE_YAML,
            kustomization_path=str(d),
            success=True,
        )

        kustomize_manager.build(d, enable_helm=True)

        call_kwargs = mock_kustomize_client.build.call_args
        assert call_kwargs.kwargs.get("enable_helm") is True


# ===========================================================================
# TestApply
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestApply:
    """Tests for KustomizeManager.apply."""

    def test_apply_build_failure_returns_error_result(
        self,
        kustomize_manager: KustomizeManager,
        mock_kustomize_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should return error ApplyResult when build fails."""
        d = tmp_path / "base"

        mock_kustomize_client.build.return_value = KustomizeBuildResult(
            rendered_yaml="",
            kustomization_path=str(d),
            success=False,
            error="Build error",
        )

        results = kustomize_manager.apply(d)

        assert len(results) == 1
        assert results[0].success is False
        assert results[0].resource == "kustomization"
        assert "Build error" in results[0].message

    @patch(
        "system_operations_manager.services.kubernetes.kustomize_manager.KustomizeManager._get_manifest_manager"
    )
    def test_apply_delegates_to_manifest_manager(
        self,
        mock_get_mm: MagicMock,
        kustomize_manager: KustomizeManager,
        mock_kustomize_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should build then delegate to ManifestManager.apply_manifests."""
        d = tmp_path / "base"

        mock_kustomize_client.build.return_value = KustomizeBuildResult(
            rendered_yaml=SAMPLE_YAML,
            kustomization_path=str(d),
            success=True,
        )

        mock_mm = MagicMock()
        mock_mm.apply_manifests.return_value = []
        mock_get_mm.return_value = mock_mm

        kustomize_manager.apply(d, namespace="production", dry_run=True)

        mock_mm.apply_manifests.assert_called_once()
        call_kwargs = mock_mm.apply_manifests.call_args.kwargs
        assert call_kwargs["namespace"] == "production"
        assert call_kwargs["dry_run"] is True

    @patch(
        "system_operations_manager.services.kubernetes.kustomize_manager.KustomizeManager._get_manifest_manager"
    )
    def test_apply_passes_force_and_server_dry_run(
        self,
        mock_get_mm: MagicMock,
        kustomize_manager: KustomizeManager,
        mock_kustomize_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should pass force and server_dry_run to ManifestManager."""
        d = tmp_path / "base"

        mock_kustomize_client.build.return_value = KustomizeBuildResult(
            rendered_yaml=SAMPLE_YAML,
            kustomization_path=str(d),
            success=True,
        )

        mock_mm = MagicMock()
        mock_mm.apply_manifests.return_value = []
        mock_get_mm.return_value = mock_mm

        kustomize_manager.apply(d, force=True, server_dry_run=True)

        call_kwargs = mock_mm.apply_manifests.call_args.kwargs
        assert call_kwargs["force"] is True
        assert call_kwargs["server_dry_run"] is True


# ===========================================================================
# TestDiff
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestDiff:
    """Tests for KustomizeManager.diff."""

    def test_diff_build_failure_returns_error_result(
        self,
        kustomize_manager: KustomizeManager,
        mock_kustomize_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should return error DiffResult when build fails."""
        d = tmp_path / "base"

        mock_kustomize_client.build.return_value = KustomizeBuildResult(
            rendered_yaml="",
            kustomization_path=str(d),
            success=False,
            error="Build error",
        )

        results = kustomize_manager.diff(d)

        assert len(results) == 1
        assert results[0].identical is False
        assert "Build error" in results[0].diff

    @patch(
        "system_operations_manager.services.kubernetes.kustomize_manager.KustomizeManager._get_manifest_manager"
    )
    def test_diff_delegates_to_manifest_manager(
        self,
        mock_get_mm: MagicMock,
        kustomize_manager: KustomizeManager,
        mock_kustomize_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should build then delegate to ManifestManager.diff_manifests."""
        d = tmp_path / "base"

        mock_kustomize_client.build.return_value = KustomizeBuildResult(
            rendered_yaml=SAMPLE_YAML,
            kustomization_path=str(d),
            success=True,
        )

        mock_mm = MagicMock()
        mock_mm.diff_manifests.return_value = []
        mock_get_mm.return_value = mock_mm

        kustomize_manager.diff(d, namespace="staging")

        mock_mm.diff_manifests.assert_called_once()
        call_kwargs = mock_mm.diff_manifests.call_args
        assert call_kwargs.kwargs.get("namespace") == "staging"


# ===========================================================================
# TestValidate
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestValidate:
    """Tests for KustomizeManager.validate."""

    def test_validate_delegates_to_client(
        self,
        kustomize_manager: KustomizeManager,
        mock_kustomize_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should delegate to KustomizeClient.validate_kustomization."""
        d = tmp_path / "base"
        mock_kustomize_client.validate_kustomization.return_value = (True, None)

        valid, error = kustomize_manager.validate(d)

        assert valid is True
        assert error is None
        mock_kustomize_client.validate_kustomization.assert_called_once_with(d)

    def test_validate_returns_error(
        self,
        kustomize_manager: KustomizeManager,
        mock_kustomize_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should return error from client validation."""
        d = tmp_path / "base"
        mock_kustomize_client.validate_kustomization.return_value = (False, "Invalid")

        valid, error = kustomize_manager.validate(d)

        assert valid is False
        assert error == "Invalid"


# ===========================================================================
# TestListOverlays
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestListOverlays:
    """Tests for KustomizeManager.list_overlays."""

    def test_discovers_overlays_directory(
        self,
        kustomize_manager: KustomizeManager,
        mock_kustomize_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should discover overlays in overlays/ directory."""
        root = tmp_path / "k8s"
        root.mkdir()
        overlays_dir = root / "overlays"
        overlays_dir.mkdir()

        for name in ("dev", "prod"):
            d = overlays_dir / name
            d.mkdir()
            (d / "kustomization.yaml").touch()

        mock_kustomize_client.validate_kustomization.return_value = (True, None)
        mock_kustomize_client.build.return_value = KustomizeBuildResult(
            rendered_yaml=SAMPLE_YAML,
            kustomization_path="",
            success=True,
        )

        result = kustomize_manager.list_overlays(root)

        names = {o.name for o in result}
        assert "dev" in names
        assert "prod" in names

    def test_discovers_base_directory(
        self,
        kustomize_manager: KustomizeManager,
        mock_kustomize_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should discover base/ directory."""
        root = tmp_path / "k8s"
        root.mkdir()
        base = root / "base"
        base.mkdir()
        (base / "kustomization.yaml").touch()

        mock_kustomize_client.validate_kustomization.return_value = (True, None)
        mock_kustomize_client.build.return_value = KustomizeBuildResult(
            rendered_yaml=SAMPLE_YAML,
            kustomization_path="",
            success=True,
        )

        result = kustomize_manager.list_overlays(root)

        names = {o.name for o in result}
        assert "base" in names

    def test_returns_empty_for_nonexistent_path(self, kustomize_manager: KustomizeManager) -> None:
        """Should return empty list for non-existent path."""
        result = kustomize_manager.list_overlays(Path("/nonexistent"))

        assert result == []

    def test_returns_empty_for_no_kustomizations(
        self, kustomize_manager: KustomizeManager, tmp_path: Path
    ) -> None:
        """Should return empty list when no kustomization files found."""
        root = tmp_path / "empty"
        root.mkdir()

        result = kustomize_manager.list_overlays(root)

        assert result == []

    def test_invalid_overlay_included(
        self,
        kustomize_manager: KustomizeManager,
        mock_kustomize_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should include invalid overlays with error info."""
        root = tmp_path / "k8s"
        root.mkdir()
        base = root / "base"
        base.mkdir()
        (base / "kustomization.yaml").touch()

        mock_kustomize_client.validate_kustomization.return_value = (
            False,
            "Bad kustomization",
        )

        result = kustomize_manager.list_overlays(root)

        assert len(result) == 1
        assert result[0].valid is False
        assert result[0].error == "Bad kustomization"


# ===========================================================================
# TestParseRenderedYaml
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestParseRenderedYaml:
    """Tests for KustomizeManager._parse_rendered_yaml."""

    def test_parses_single_document(self) -> None:
        """Should parse a single YAML document."""
        manifests = KustomizeManager._parse_rendered_yaml(SAMPLE_YAML, "/test")

        assert len(manifests) == 1
        assert manifests[0]["kind"] == "ConfigMap"
        assert manifests[0]["_source_file"] == "/test"

    def test_parses_multi_document(self) -> None:
        """Should parse multi-document YAML."""
        multi = (
            "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: a\n"
            "---\n"
            "apiVersion: v1\nkind: Secret\nmetadata:\n  name: b\n"
        )

        manifests = KustomizeManager._parse_rendered_yaml(multi, "/test")

        assert len(manifests) == 2
        assert manifests[0]["kind"] == "ConfigMap"
        assert manifests[1]["kind"] == "Secret"

    def test_filters_none_documents(self) -> None:
        """Should filter out None YAML documents."""
        yaml_with_empty = "---\napiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: a\n---\n"

        manifests = KustomizeManager._parse_rendered_yaml(yaml_with_empty, "/test")

        assert len(manifests) == 1

    def test_empty_string(self) -> None:
        """Should return empty list for empty string."""
        manifests = KustomizeManager._parse_rendered_yaml("", "/test")

        assert manifests == []
