import subprocess
import sys


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

    # Allow passing additional arguments to pytest
    # sys.argv[0] is the script name
    extra_args = sys.argv[1:]

    try:
        subprocess.check_call(base_cmd + extra_args)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)


def unit() -> None:
    """Run unit tests."""
    base_cmd = [
        sys.executable,
        "-m",
        "pytest",
        "./tests/unit/",
    ]

    # Allow passing additional arguments to pytest
    # sys.argv[0] is the script name
    extra_args = sys.argv[1:]

    try:
        subprocess.check_call(base_cmd + extra_args)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
