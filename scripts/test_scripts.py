import subprocess
import sys


def _run_process(cmd: list[str]) -> None:
    """Run a process with additional arguments."""
    # Allow passing additional arguments to pytest
    # sys.argv[0] is the script name
    extra_args = sys.argv[1:]

    try:
        subprocess.check_call(cmd + extra_args)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)


def coverage() -> None:
    """Run unit tests with coverage report."""
    base_cmd = [
        sys.executable,
        "-m",
        "pytest",
        "--cov=system_operations_manager",
        "--cov-report=term-missing",
        "./tests/unit/",
    ]

    _run_process(base_cmd)


def e2e() -> None:
    """Run end-to-end tests."""
    base_cmd = [
        sys.executable,
        "-m",
        "pytest",
        "./tests/e2e/",
    ]

    _run_process(base_cmd)


def integration() -> None:
    """Run integration tests."""
    base_cmd = [
        sys.executable,
        "-m",
        "pytest",
        "./tests/integration/",
    ]

    _run_process(base_cmd)


def unit() -> None:
    """Run unit tests."""
    base_cmd = [
        sys.executable,
        "-m",
        "pytest",
        "./tests/unit/",
    ]

    _run_process(base_cmd)
