import os
import subprocess
import sys

__BASE_CMD = [
    sys.executable,
    "-m",
    "pytest",
]
__DEFAULT_KONG_TEST_IMAGE = ("KONG_TEST_IMAGE", "kong/kong-gateway:latest")
__E2E_TESTS = "./tests/e2e/"
__INTEGRATION_TESTS = "./tests/integration/"
__UNIT_TESTS = "./tests/unit/"


def __get_kong_env() -> dict[str, str]:
    """Get environment variables for Kong tests."""
    env = os.environ.copy()
    env.setdefault(*__DEFAULT_KONG_TEST_IMAGE)
    return env


def __run_process(cmd: list[str], env: dict[str, str] | None = None) -> None:
    """Run a process with additional arguments."""
    # Allow passing additional arguments to pytest
    # sys.argv[0] is the script name
    extra_args = sys.argv[1:]

    try:
        subprocess.check_call(cmd + extra_args, env=env)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)


def coverage() -> None:
    """Run unit tests with coverage report."""
    cmd = [
        *__BASE_CMD,
        "--cov=system_operations_manager",
        "--cov-report=term-missing",
        __UNIT_TESTS,
    ]

    __run_process(cmd)


def e2e() -> None:
    """Run end-to-end tests."""
    cmd = [
        *__BASE_CMD,
        __E2E_TESTS,
    ]

    __run_process(cmd, env=__get_kong_env())


def integration() -> None:
    """Run integration tests."""
    cmd = [
        *__BASE_CMD,
        __INTEGRATION_TESTS,
    ]

    __run_process(cmd, env=__get_kong_env())


def unit() -> None:
    """Run unit tests."""
    cmd = [
        *__BASE_CMD,
        __UNIT_TESTS,
    ]

    __run_process(cmd)
