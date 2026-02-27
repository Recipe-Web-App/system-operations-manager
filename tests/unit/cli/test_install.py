"""Tests for CLI install module."""

from __future__ import annotations

import contextlib
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.cli.install import (
    _check_python_version,
    _cleanup_legacy_path_entry,
    _find_pipx,
    _find_python_for_pipx,
    _get_project_path,
    _install_shell_completion,
    _is_installed_via_pipx,
    install,
    uninstall,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# A minimal Typer app that exposes install/uninstall as commands so we can
# drive them through CliRunner without touching the real main app.
_test_app = typer.Typer()
_test_app.command("install")(install)
_test_app.command("uninstall")(uninstall)


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


# ---------------------------------------------------------------------------
# _check_python_version
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCheckPythonVersion:
    """Tests for _check_python_version helper."""

    def test_returns_true_when_version_meets_minimum(self) -> None:
        """Current interpreter satisfies or exceeds MIN_PYTHON_VERSION."""
        with patch.object(sys, "version_info", (3, 14, 0, "final", 0)):
            result = _check_python_version()
        assert result is True

    def test_returns_false_when_version_below_minimum(self) -> None:
        """Returns False and prints error for old Python."""
        with patch.object(sys, "version_info", (3, 11, 0, "final", 0)):
            result = _check_python_version()
        assert result is False

    def test_returns_true_for_higher_major_version(self) -> None:
        """Python 4.x should still satisfy >= 3.14."""
        with patch.object(sys, "version_info", (4, 0, 0, "final", 0)):
            result = _check_python_version()
        assert result is True


# ---------------------------------------------------------------------------
# _find_pipx
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFindPipx:
    """Tests for _find_pipx helper."""

    def test_returns_path_when_pipx_found(self) -> None:
        with patch(
            "system_operations_manager.cli.install.shutil.which", return_value="/usr/bin/pipx"
        ):
            result = _find_pipx()
        assert result == "/usr/bin/pipx"

    def test_returns_none_when_pipx_not_found(self) -> None:
        with patch("system_operations_manager.cli.install.shutil.which", return_value=None):
            result = _find_pipx()
        assert result is None


# ---------------------------------------------------------------------------
# _find_python_for_pipx
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFindPythonForPipx:
    """Tests for _find_python_for_pipx helper."""

    def _make_run_result(self, stdout: str) -> MagicMock:
        mock = MagicMock()
        mock.stdout = stdout
        return mock

    def test_returns_path_when_compatible_python_found(self) -> None:
        with (
            patch(
                "system_operations_manager.cli.install.shutil.which",
                return_value="/usr/bin/python3.14",
            ),
            patch(
                "system_operations_manager.cli.install.subprocess.run",
                return_value=self._make_run_result("3.14\n"),
            ),
        ):
            result = _find_python_for_pipx()
        assert result == "/usr/bin/python3.14"

    def test_returns_none_when_python_too_old(self) -> None:
        with (
            patch(
                "system_operations_manager.cli.install.shutil.which",
                return_value="/usr/bin/python3",
            ),
            patch(
                "system_operations_manager.cli.install.subprocess.run",
                return_value=self._make_run_result("3.11\n"),
            ),
        ):
            result = _find_python_for_pipx()
        assert result is None

    def test_returns_none_when_which_returns_nothing(self) -> None:
        with patch("system_operations_manager.cli.install.shutil.which", return_value=None):
            result = _find_python_for_pipx()
        assert result is None

    def test_skips_candidate_on_called_process_error(self) -> None:
        with (
            patch(
                "system_operations_manager.cli.install.shutil.which",
                return_value="/usr/bin/python3.14",
            ),
            patch(
                "system_operations_manager.cli.install.subprocess.run",
                side_effect=subprocess.CalledProcessError(1, "python3.14"),
            ),
        ):
            result = _find_python_for_pipx()
        assert result is None

    def test_skips_candidate_on_value_error(self) -> None:
        with (
            patch(
                "system_operations_manager.cli.install.shutil.which",
                return_value="/usr/bin/python3.14",
            ),
            patch(
                "system_operations_manager.cli.install.subprocess.run",
                return_value=self._make_run_result("not-a-version\n"),
            ),
        ):
            result = _find_python_for_pipx()
        assert result is None


# ---------------------------------------------------------------------------
# _get_project_path
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetProjectPath:
    """Tests for _get_project_path helper."""

    def test_returns_path_containing_pyproject_toml(self) -> None:
        result = _get_project_path()
        # The repo's pyproject.toml should be findable from the source file.
        assert isinstance(result, Path)
        # Either the result has pyproject.toml, or we fell back to cwd.
        assert result.exists()

    def test_falls_back_to_cwd_when_no_pyproject_found(self, tmp_path: Path) -> None:
        fake_file = tmp_path / "fake_install.py"
        fake_file.touch()
        with (
            patch.object(Path, "resolve", return_value=tmp_path / "a" / "b" / "c" / "install.py"),
            patch.object(Path, "exists", return_value=False),
        ):
            result = _get_project_path()
        assert isinstance(result, Path)


# ---------------------------------------------------------------------------
# _is_installed_via_pipx
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIsInstalledViaPipx:
    """Tests for _is_installed_via_pipx helper."""

    def _make_run_result(self, stdout: str) -> MagicMock:
        mock = MagicMock()
        mock.stdout = stdout
        return mock

    def test_returns_true_when_package_in_list(self) -> None:
        output = "system-operations-cli 1.0.0\nother-package 2.0.0\n"
        with patch(
            "system_operations_manager.cli.install.subprocess.run",
            return_value=self._make_run_result(output),
        ):
            assert _is_installed_via_pipx() is True

    def test_returns_false_when_package_not_in_list(self) -> None:
        with patch(
            "system_operations_manager.cli.install.subprocess.run",
            return_value=self._make_run_result("other-package 2.0.0\n"),
        ):
            assert _is_installed_via_pipx() is False

    def test_returns_false_on_called_process_error(self) -> None:
        with patch(
            "system_operations_manager.cli.install.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "pipx"),
        ):
            assert _is_installed_via_pipx() is False

    def test_returns_false_when_pipx_not_found(self) -> None:
        with patch(
            "system_operations_manager.cli.install.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            assert _is_installed_via_pipx() is False


# ---------------------------------------------------------------------------
# _cleanup_legacy_path_entry
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCleanupLegacyPathEntry:
    """Tests for _cleanup_legacy_path_entry helper."""

    def test_removes_legacy_block_when_present(self, tmp_path: Path) -> None:
        rc = tmp_path / ".zshrc"
        rc.write_text(
            "export PATH=$PATH:/usr/bin\n"
            "# system-operations-cli PATH\nexport PATH=$PATH:/old/ops/bin\n# system-operations-cli PATH END\n"
            "alias ll='ls -la'\n"
        )
        home_mock = MagicMock(return_value=tmp_path)
        with patch.object(Path, "home", home_mock):
            _cleanup_legacy_path_entry()
        content = rc.read_text()
        assert "system-operations-cli PATH" not in content
        assert "export PATH=$PATH:/usr/bin" in content
        assert "alias ll" in content

    def test_does_nothing_when_no_legacy_block(self, tmp_path: Path) -> None:
        rc = tmp_path / ".zshrc"
        original = "export PATH=$PATH:/usr/bin\n"
        rc.write_text(original)
        home_mock = MagicMock(return_value=tmp_path)
        with patch.object(Path, "home", home_mock):
            _cleanup_legacy_path_entry()
        assert rc.read_text() == original

    def test_skips_missing_rc_file(self, tmp_path: Path) -> None:
        # Neither .zshrc nor .bashrc exist — should not raise.
        home_mock = MagicMock(return_value=tmp_path)
        with patch.object(Path, "home", home_mock):
            _cleanup_legacy_path_entry()  # must not raise


# ---------------------------------------------------------------------------
# _install_shell_completion
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInstallShellCompletion:
    """Tests for _install_shell_completion helper."""

    def _run_result(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
        mock = MagicMock()
        mock.returncode = returncode
        mock.stdout = stdout
        mock.stderr = stderr
        return mock

    def test_returns_false_when_ops_not_on_path(self) -> None:
        with patch("system_operations_manager.cli.install.shutil.which", return_value=None):
            result = _install_shell_completion()
        assert result is False

    def test_returns_false_for_unsupported_shell(self) -> None:
        with (
            patch(
                "system_operations_manager.cli.install.shutil.which", return_value="/usr/bin/ops"
            ),
            patch.dict("os.environ", {"SHELL": "/bin/tcsh"}),
        ):
            result = _install_shell_completion()
        assert result is False

    def test_returns_false_when_shell_env_empty(self) -> None:
        with (
            patch(
                "system_operations_manager.cli.install.shutil.which", return_value="/usr/bin/ops"
            ),
            patch.dict("os.environ", {"SHELL": ""}),
        ):
            result = _install_shell_completion()
        assert result is False

    def test_returns_true_on_successful_completion_install(self) -> None:
        with (
            patch(
                "system_operations_manager.cli.install.shutil.which", return_value="/usr/bin/ops"
            ),
            patch.dict("os.environ", {"SHELL": "/bin/zsh"}),
            patch(
                "system_operations_manager.cli.install.subprocess.run",
                return_value=self._run_result(returncode=0),
            ),
        ):
            result = _install_shell_completion()
        assert result is True

    def test_returns_true_when_completion_already_installed(self) -> None:
        with (
            patch(
                "system_operations_manager.cli.install.shutil.which", return_value="/usr/bin/ops"
            ),
            patch.dict("os.environ", {"SHELL": "/bin/bash"}),
            patch(
                "system_operations_manager.cli.install.subprocess.run",
                return_value=self._run_result(returncode=1, stderr="already installed"),
            ),
        ):
            result = _install_shell_completion()
        assert result is True

    def test_returns_false_when_subprocess_run_fails(self) -> None:
        with (
            patch(
                "system_operations_manager.cli.install.shutil.which", return_value="/usr/bin/ops"
            ),
            patch.dict("os.environ", {"SHELL": "/usr/bin/fish"}),
            patch(
                "system_operations_manager.cli.install.subprocess.run",
                return_value=self._run_result(returncode=1, stderr="some error"),
            ),
        ):
            result = _install_shell_completion()
        assert result is False

    def test_returns_false_when_subprocess_raises_exception(self) -> None:
        with (
            patch(
                "system_operations_manager.cli.install.shutil.which", return_value="/usr/bin/ops"
            ),
            patch.dict("os.environ", {"SHELL": "/bin/zsh"}),
            patch(
                "system_operations_manager.cli.install.subprocess.run",
                side_effect=OSError("permission denied"),
            ),
        ):
            result = _install_shell_completion()
        assert result is False


# ---------------------------------------------------------------------------
# install() command — via CliRunner
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInstallCommand:
    """Integration-style tests for the install() Typer command."""

    def _patch_happy_path(
        self,
        *,
        python_version: tuple[int, int] = (3, 14),
        pipx_path: str = "/usr/bin/pipx",
        already_installed: bool = False,
        python_for_pipx: str = "/usr/bin/python3.14",
        pipx_run_side_effect: Exception | None = None,
    ) -> contextlib.ExitStack:
        """Return a context-manager stack with all external calls patched."""
        from contextlib import ExitStack

        stack = ExitStack()
        stack.enter_context(patch.object(sys, "version_info", (*python_version, 0, "final", 0)))
        stack.enter_context(
            patch("system_operations_manager.cli.install._cleanup_legacy_path_entry")
        )
        stack.enter_context(
            patch(
                "system_operations_manager.cli.install._find_pipx",
                return_value=pipx_path,
            )
        )
        stack.enter_context(
            patch(
                "system_operations_manager.cli.install._is_installed_via_pipx",
                return_value=already_installed,
            )
        )
        stack.enter_context(
            patch(
                "system_operations_manager.cli.install._find_python_for_pipx",
                return_value=python_for_pipx,
            )
        )
        stack.enter_context(
            patch(
                "system_operations_manager.cli.install._get_project_path",
                return_value=Path("/proj"),
            )
        )
        stack.enter_context(
            patch(
                "system_operations_manager.cli.install._install_shell_completion", return_value=True
            )
        )
        if pipx_run_side_effect:
            stack.enter_context(
                patch(
                    "system_operations_manager.cli.install.subprocess.run",
                    side_effect=pipx_run_side_effect,
                )
            )
        else:
            stack.enter_context(
                patch(
                    "system_operations_manager.cli.install.subprocess.run", return_value=MagicMock()
                )
            )
        return stack

    def test_successful_install(self, runner: CliRunner) -> None:
        with self._patch_happy_path():
            result = runner.invoke(_test_app, ["install"])
        assert result.exit_code == 0
        assert "Installation complete" in result.stdout

    def test_install_with_extras(self, runner: CliRunner) -> None:
        with self._patch_happy_path() as _:
            result = runner.invoke(_test_app, ["install", "--extras", "kubernetes,monitoring"])
        assert result.exit_code == 0
        assert "Installation complete" in result.stdout

    def test_install_editable_mode(self, runner: CliRunner) -> None:
        with self._patch_happy_path():
            result = runner.invoke(_test_app, ["install", "--editable"])
        assert result.exit_code == 0
        assert "editable mode" in result.stdout

    def test_install_with_explicit_python(self, runner: CliRunner) -> None:
        with self._patch_happy_path():
            result = runner.invoke(_test_app, ["install", "--python", "/usr/local/bin/python3.14"])
        assert result.exit_code == 0
        assert "Installation complete" in result.stdout

    def test_install_fails_when_python_too_old(self, runner: CliRunner) -> None:
        with patch.object(sys, "version_info", (3, 11, 0, "final", 0)):
            result = runner.invoke(_test_app, ["install"])
        assert result.exit_code == 1

    def test_install_fails_when_pipx_missing(self, runner: CliRunner) -> None:
        with (
            patch.object(sys, "version_info", (3, 14, 0, "final", 0)),
            patch("system_operations_manager.cli.install._cleanup_legacy_path_entry"),
            patch("system_operations_manager.cli.install._find_pipx", return_value=None),
        ):
            result = runner.invoke(_test_app, ["install"])
        assert result.exit_code == 1

    def test_install_already_installed_without_force(self, runner: CliRunner) -> None:
        with self._patch_happy_path(already_installed=True):
            result = runner.invoke(_test_app, ["install"])
        assert result.exit_code == 0
        assert "already installed" in result.stdout

    def test_install_already_installed_with_force(self, runner: CliRunner) -> None:
        with self._patch_happy_path(already_installed=True):
            result = runner.invoke(_test_app, ["install", "--force"])
        assert result.exit_code == 0
        assert "Installation complete" in result.stdout

    def test_install_fails_when_no_python_found(self, runner: CliRunner) -> None:
        with (
            patch.object(sys, "version_info", (3, 14, 0, "final", 0)),
            patch("system_operations_manager.cli.install._cleanup_legacy_path_entry"),
            patch("system_operations_manager.cli.install._find_pipx", return_value="/usr/bin/pipx"),
            patch(
                "system_operations_manager.cli.install._is_installed_via_pipx", return_value=False
            ),
            patch("system_operations_manager.cli.install._find_python_for_pipx", return_value=None),
        ):
            result = runner.invoke(_test_app, ["install"])
        assert result.exit_code == 1
        assert "Could not find Python" in result.stdout

    def test_install_fails_when_pipx_run_errors(self, runner: CliRunner) -> None:
        err = subprocess.CalledProcessError(1, "pipx")
        with self._patch_happy_path(pipx_run_side_effect=err):
            result = runner.invoke(_test_app, ["install"])
        assert result.exit_code == 1
        assert "pipx install failed" in result.stdout

    def test_install_force_flag_appends_force_to_cmd(self, runner: CliRunner) -> None:
        """Ensure --force causes subprocess.run to include '--force' in cmd."""
        captured_cmds: list[list[str]] = []

        def fake_run(cmd: list[str], **kwargs: object) -> MagicMock:
            captured_cmds.append(list(cmd))
            return MagicMock()

        with (
            patch.object(sys, "version_info", (3, 14, 0, "final", 0)),
            patch("system_operations_manager.cli.install._cleanup_legacy_path_entry"),
            patch("system_operations_manager.cli.install._find_pipx", return_value="/usr/bin/pipx"),
            patch(
                "system_operations_manager.cli.install._is_installed_via_pipx", return_value=False
            ),
            patch(
                "system_operations_manager.cli.install._find_python_for_pipx",
                return_value="/usr/bin/python3.14",
            ),
            patch(
                "system_operations_manager.cli.install._get_project_path",
                return_value=Path("/proj"),
            ),
            patch(
                "system_operations_manager.cli.install._install_shell_completion", return_value=True
            ),
            patch("system_operations_manager.cli.install.subprocess.run", side_effect=fake_run),
        ):
            result = runner.invoke(_test_app, ["install", "--force"])
        assert result.exit_code == 0
        assert "--force" in captured_cmds[0]


# ---------------------------------------------------------------------------
# uninstall() command — via CliRunner
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUninstallCommand:
    """Tests for the uninstall() Typer command."""

    def test_successful_uninstall(self, runner: CliRunner) -> None:
        with (
            patch("system_operations_manager.cli.install._find_pipx", return_value="/usr/bin/pipx"),
            patch(
                "system_operations_manager.cli.install._is_installed_via_pipx", return_value=True
            ),
            patch("system_operations_manager.cli.install.subprocess.run", return_value=MagicMock()),
        ):
            result = runner.invoke(_test_app, ["uninstall"])
        assert result.exit_code == 0
        assert "Uninstallation complete" in result.stdout

    def test_uninstall_fails_when_pipx_missing(self, runner: CliRunner) -> None:
        with patch("system_operations_manager.cli.install._find_pipx", return_value=None):
            result = runner.invoke(_test_app, ["uninstall"])
        assert result.exit_code == 1

    def test_uninstall_when_not_installed(self, runner: CliRunner) -> None:
        with (
            patch("system_operations_manager.cli.install._find_pipx", return_value="/usr/bin/pipx"),
            patch(
                "system_operations_manager.cli.install._is_installed_via_pipx", return_value=False
            ),
        ):
            result = runner.invoke(_test_app, ["uninstall"])
        assert result.exit_code == 0
        assert "not installed" in result.stdout

    def test_uninstall_fails_when_subprocess_errors(self, runner: CliRunner) -> None:
        with (
            patch("system_operations_manager.cli.install._find_pipx", return_value="/usr/bin/pipx"),
            patch(
                "system_operations_manager.cli.install._is_installed_via_pipx", return_value=True
            ),
            patch(
                "system_operations_manager.cli.install.subprocess.run",
                side_effect=subprocess.CalledProcessError(1, "pipx"),
            ),
        ):
            result = runner.invoke(_test_app, ["uninstall"])
        assert result.exit_code == 1
        assert "pipx uninstall failed" in result.stdout
