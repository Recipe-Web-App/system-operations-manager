# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

System Control CLI is a Python-based CLI framework for managing distributed systems, deployments, monitoring, and infrastructure operations.

## Development Commands

```bash
# Install globally with pipx (recommended for end users)
pipx install . --python python3.14          # Production install
pipx install -e . --python python3.14       # Editable/dev install
pipx install ".[all]" --python python3.14   # With all extras
pipx uninstall system-operations-cli        # Uninstall

# Install with Poetry (for development)
poetry install                      # Core dependencies
poetry install --all-extras         # All optional dependencies

# Install pre-commit hooks
pre-commit install

# Run tests
pytest                              # All tests
pytest tests/unit/test_version.py   # Single file
pytest -k "test_status"             # Pattern match
pytest -v                           # Verbose
pytest --cov=system_operations_manager         # With coverage

# Code quality (using ruff + mypy)
ruff check src tests                # Lint
ruff format src tests               # Format
mypy src                            # Type check
pre-commit run --all-files          # All checks

# CLI commands
poetry run ops --version            # Show version
poetry run ops status               # Show system status
poetry run ops init                 # Initialize project config
```

## Architecture

The system uses a layered architecture:

```
User Interface (CLI/REPL/REST API)
        ↓
Command Processing (Router, Validation, Error Handling)
        ↓
Core Engine (Plugin Manager, Config Manager, State Management)
        ↓
Service Layer (Deployment, Monitoring, System Control)
        ↓
Integration Layer (External APIs, File System, SSH)
```

### Key Patterns

- **Plugin System**: Hot-loadable plugins using `pluggy`. Plugins inherit from `Plugin` base class with `initialize()`, `register_commands()`, and `cleanup()` methods. Entry points defined in `pyproject.toml` under `[tool.poetry.plugins."system_operations_manager.plugins"]`.

- **Configuration Hierarchy** (lowest to highest precedence):
  1. Default → 2. System → 3. User → 4. Project → 5. Environment vars → 6. CLI args

- **Profile Inheritance**: Profiles in YAML can inherit from other profiles via `inherits: ["base", "security"]`.

### Source Structure

```
src/system_operations_manager/
├── cli/            # CLI command definitions (Typer)
├── core/           # Core engine and plugin system
├── logging/        # Structured logging with structlog
├── services/       # Business logic services
├── integrations/   # External tool integrations
├── plugins/        # Built-in plugins
└── utils/          # Utility functions
```

## Testing

Test markers available: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`, `@pytest.mark.slow`, `@pytest.mark.kubernetes`, `@pytest.mark.vault`

Coverage target: 80%+

## Commit Conventions

Uses conventional commits with commitlint validation:

- **Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`
- **Scopes**: `adr`, `config`, `docs`, `examples`, `features`, `integrations`, `plugins`, `commands`, `deps`, `release`, `setup`
- **Format**: `type(scope): description` (header max 72 chars, body max 100 chars per line)

Example: `feat(plugins): add hot-reload support for custom plugins`

## Optional Dependency Groups

- `cli` - CLI enhancements (Cloup, Cement, Textual)
- `kubernetes` - K8s integration
- `monitoring` - Prometheus, Grafana, Elasticsearch
- `vault` - Secret management (HashiCorp Vault, AWS, Azure, GCP)
- `all` - All optional dependencies

## CLI Entry Point

The CLI is exposed as `ops` command via `system_operations_manager.cli.main:main`.
