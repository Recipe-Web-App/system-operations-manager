"""Unit tests for KustomizeClient."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from system_operations_manager.integrations.kubernetes.kustomize_client import (
    BUILD_TIMEOUT_SECONDS,
    KustomizeBinaryNotFoundError,
    KustomizeClient,
    KustomizeError,
)


@pytest.fixture
def kustomize_client() -> KustomizeClient:
    """Create a KustomizeClient with mocked binary detection."""
    with patch("shutil.which", return_value="/usr/local/bin/kustomize"):
        return KustomizeClient()


@pytest.fixture
def kustomization_dir(tmp_path: Path) -> Path:
    """Create a temp directory with a kustomization.yaml file."""
    d = tmp_path / "base"
    d.mkdir()
    (d / "kustomization.yaml").write_text(
        "apiVersion: kustomize.config.k8s.io/v1beta1\nkind: Kustomization\n"
    )
    return d


# ===========================================================================
# TestInit
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestInit:
    """Tests for KustomizeClient initialization."""

    def test_finds_binary_in_path(self) -> None:
        """Should find kustomize binary in PATH."""
        with patch("shutil.which", return_value="/usr/local/bin/kustomize"):
            client = KustomizeClient()
            assert client._binary == "/usr/local/bin/kustomize"

    def test_raises_when_binary_not_found(self) -> None:
        """Should raise KustomizeBinaryNotFoundError if not in PATH."""
        with patch("shutil.which", return_value=None), pytest.raises(KustomizeBinaryNotFoundError):
            KustomizeClient()

    def test_uses_explicit_binary_path(self, tmp_path: Path) -> None:
        """Should use explicit binary path when provided."""
        fake_binary = tmp_path / "kustomize"
        fake_binary.touch()

        client = KustomizeClient(binary_path=str(fake_binary))
        assert client._binary == str(fake_binary.resolve())

    def test_raises_when_explicit_path_not_found(self) -> None:
        """Should raise when explicit binary path does not exist."""
        with pytest.raises(KustomizeBinaryNotFoundError):
            KustomizeClient(binary_path="/nonexistent/kustomize")


# ===========================================================================
# TestGetVersion
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestGetVersion:
    """Tests for KustomizeClient.get_version."""

    @patch("subprocess.run")
    def test_parses_version_string(
        self, mock_run: MagicMock, kustomize_client: KustomizeClient
    ) -> None:
        """Should parse version from kustomize output."""
        mock_run.return_value = MagicMock(
            stdout="{kustomize/v5.8.0  2025-11-09T14:38:52Z  }\n",
            returncode=0,
        )

        version = kustomize_client.get_version()

        assert version == "v5.8.0"

    @patch("subprocess.run")
    def test_handles_simple_version_string(
        self, mock_run: MagicMock, kustomize_client: KustomizeClient
    ) -> None:
        """Should handle simple version format."""
        mock_run.return_value = MagicMock(stdout="v5.8.0\n", returncode=0)

        version = kustomize_client.get_version()

        assert version == "v5.8.0"

    @patch("subprocess.run")
    def test_raises_on_failure(
        self, mock_run: MagicMock, kustomize_client: KustomizeClient
    ) -> None:
        """Should raise KustomizeError on command failure."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd=["kustomize", "version"], stderr="error"
        )

        with pytest.raises(KustomizeError):
            kustomize_client.get_version()

    @patch("subprocess.run")
    def test_raises_on_timeout(
        self, mock_run: MagicMock, kustomize_client: KustomizeClient
    ) -> None:
        """Should raise KustomizeError on timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["kustomize"], timeout=5)

        with pytest.raises(KustomizeError, match="timed out"):
            kustomize_client.get_version()


# ===========================================================================
# TestBuild
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestBuild:
    """Tests for KustomizeClient.build."""

    @patch("subprocess.run")
    def test_build_success(
        self,
        mock_run: MagicMock,
        kustomize_client: KustomizeClient,
        kustomization_dir: Path,
    ) -> None:
        """Should return rendered YAML on successful build."""
        mock_run.return_value = MagicMock(
            stdout="apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: test\n",
            returncode=0,
        )

        result = kustomize_client.build(kustomization_dir)

        assert result.success is True
        assert "ConfigMap" in result.rendered_yaml
        assert result.kustomization_path == str(kustomization_dir)
        assert result.error is None

    def test_build_nonexistent_directory(self, kustomize_client: KustomizeClient) -> None:
        """Should fail for non-existent directory."""
        result = kustomize_client.build(Path("/nonexistent"))

        assert result.success is False
        assert "not found" in (result.error or "").lower()

    def test_build_missing_kustomization_file(
        self, kustomize_client: KustomizeClient, tmp_path: Path
    ) -> None:
        """Should fail when no kustomization file exists."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = kustomize_client.build(empty_dir)

        assert result.success is False
        assert "No kustomization file" in (result.error or "")

    @patch("subprocess.run")
    def test_build_with_enable_helm(
        self,
        mock_run: MagicMock,
        kustomize_client: KustomizeClient,
        kustomization_dir: Path,
    ) -> None:
        """Should pass --enable-helm flag."""
        mock_run.return_value = MagicMock(stdout="", returncode=0)

        kustomize_client.build(kustomization_dir, enable_helm=True)

        cmd = mock_run.call_args[0][0]
        assert "--enable-helm" in cmd

    @patch("subprocess.run")
    def test_build_with_enable_alpha_plugins(
        self,
        mock_run: MagicMock,
        kustomize_client: KustomizeClient,
        kustomization_dir: Path,
    ) -> None:
        """Should pass --enable-alpha-plugins flag."""
        mock_run.return_value = MagicMock(stdout="", returncode=0)

        kustomize_client.build(kustomization_dir, enable_alpha_plugins=True)

        cmd = mock_run.call_args[0][0]
        assert "--enable-alpha-plugins" in cmd

    @patch("subprocess.run")
    def test_build_captures_stderr_on_failure(
        self,
        mock_run: MagicMock,
        kustomize_client: KustomizeClient,
        kustomization_dir: Path,
    ) -> None:
        """Should capture stderr when build fails."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["kustomize", "build"],
            stderr="Error: missing resource entry\n",
        )

        result = kustomize_client.build(kustomization_dir)

        assert result.success is False
        assert "missing resource entry" in (result.error or "")

    @patch("subprocess.run")
    def test_build_handles_timeout(
        self,
        mock_run: MagicMock,
        kustomize_client: KustomizeClient,
        kustomization_dir: Path,
    ) -> None:
        """Should handle build timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["kustomize", "build"], timeout=BUILD_TIMEOUT_SECONDS
        )

        result = kustomize_client.build(kustomization_dir)

        assert result.success is False
        assert "timed out" in (result.error or "").lower()

    def test_build_detects_kustomization_yml(
        self, kustomize_client: KustomizeClient, tmp_path: Path
    ) -> None:
        """Should accept kustomization.yml (alternative extension)."""
        d = tmp_path / "alt"
        d.mkdir()
        (d / "kustomization.yml").write_text("apiVersion: kustomize.config.k8s.io/v1beta1\n")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="---\n", returncode=0)
            result = kustomize_client.build(d)

        assert result.success is True


# ===========================================================================
# TestValidateKustomization
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestValidateKustomization:
    """Tests for KustomizeClient.validate_kustomization."""

    def test_validate_nonexistent_directory(self, kustomize_client: KustomizeClient) -> None:
        """Should detect non-existent directory."""
        valid, error = kustomize_client.validate_kustomization(Path("/nonexistent"))

        assert valid is False
        assert "not found" in (error or "").lower()

    def test_validate_not_a_directory(
        self, kustomize_client: KustomizeClient, tmp_path: Path
    ) -> None:
        """Should detect non-directory path."""
        f = tmp_path / "file.txt"
        f.write_text("not a directory")

        valid, error = kustomize_client.validate_kustomization(f)

        assert valid is False
        assert "Not a directory" in (error or "")

    def test_validate_missing_kustomization_file(
        self, kustomize_client: KustomizeClient, tmp_path: Path
    ) -> None:
        """Should detect missing kustomization file."""
        empty = tmp_path / "empty"
        empty.mkdir()

        valid, error = kustomize_client.validate_kustomization(empty)

        assert valid is False
        assert "No kustomization file" in (error or "")

    @patch("subprocess.run")
    def test_validate_valid_kustomization(
        self,
        mock_run: MagicMock,
        kustomize_client: KustomizeClient,
        kustomization_dir: Path,
    ) -> None:
        """Should validate a proper kustomization directory."""
        mock_run.return_value = MagicMock(stdout="apiVersion: v1\nkind: ConfigMap\n", returncode=0)

        valid, error = kustomize_client.validate_kustomization(kustomization_dir)

        assert valid is True
        assert error is None

    @patch("subprocess.run")
    def test_validate_build_failure(
        self,
        mock_run: MagicMock,
        kustomize_client: KustomizeClient,
        kustomization_dir: Path,
    ) -> None:
        """Should fail validation when build fails."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["kustomize", "build"],
            stderr="Error: invalid kustomization\n",
        )

        valid, error = kustomize_client.validate_kustomization(kustomization_dir)

        assert valid is False
        assert "invalid kustomization" in (error or "")
