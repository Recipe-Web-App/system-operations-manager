# Contributing to System Control CLI

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing
to this project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Code Style](#code-style)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Security](#security)

## Code of Conduct

This project adheres to a Code of Conduct. By participating, you are expected to uphold this code. Please report
unacceptable behavior through the project's issue tracker.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:

   ```bash
   git clone https://github.com/YOUR_USERNAME/system-control.git
   cd system-control
   ```

3. **Add upstream remote**:

   ```bash
   git remote add upstream https://github.com/Recipe-Web-App/system-control.git
   ```

## Development Setup

### Prerequisites

- Python 3.14 or higher
- uv (for dependency management)
- pre-commit (for git hooks)

### Initial Setup

1. **Install dependencies**:

   ```bash
   uv sync                         # Core dependencies
   uv sync --all-extras            # All optional dependencies
   ```

2. **Install pre-commit hooks**:

   ```bash
   pre-commit install
   ```

3. **Verify installation**:

   ```bash
   uv run ops --version
   ```

## Development Workflow

1. **Create a feature branch**:

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the code style guidelines

3. **Run tests frequently**:

   ```bash
   uv run pytest
   ```

4. **Commit your changes** following commit guidelines

5. **Keep your branch updated**:

   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

6. **Push to your fork**:

   ```bash
   git push origin feature/your-feature-name
   ```

## Testing

### Running Tests

```bash
# All tests
uv run pytest

# Unit tests only
uv run pytest -m unit

# Integration tests only
uv run pytest -m integration

# With coverage
uv run pytest --cov=system_operations_manager

# Verbose output
uv run pytest -v
```

### Writing Tests

- Write unit tests for all new functionality
- Integration tests for CLI commands and external integrations
- Aim for >80% code coverage
- Test edge cases and error conditions

### Test Guidelines

- Use pytest fixtures for test setup
- Use descriptive test names: `test_function_name_scenario_expected_behavior`
- Mock external dependencies
- Clean up resources in test teardown

## Code Style

### Python Code Standards

```bash
# Format code
uv run ruff format src tests

# Run linter
uv run ruff check src tests

# Run type checker
uv run mypy src

# Run all checks via pre-commit
pre-commit run --all-files
```

### Style Guidelines

- Follow PEP 8 conventions
- Use meaningful variable and function names
- Keep functions small and focused
- Document public functions and classes with docstrings
- Add comments for complex logic
- Use type hints for all function signatures

### Package Organization

```text
src/system_operations_manager/
├── cli/            # CLI command definitions (Typer)
├── core/           # Core engine and plugin system
├── logging/        # Structured logging with structlog
├── services/       # Business logic services
├── integrations/   # External tool integrations
├── plugins/        # Built-in plugins
└── utils/          # Utility functions
```

## Commit Guidelines

### Commit Message Format

```text
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Test additions or changes
- `chore`: Build process or auxiliary tool changes
- `security`: Security fixes
- `deps`: Dependency updates

### Scopes

- `cli`, `core`, `plugins`, `services`, `integrations`, `config`, `logging`, `docs`

### Examples

```text
feat(plugins): add hot-reload support for custom plugins

Implements dynamic plugin loading without requiring service restart.
Plugins are monitored for changes and automatically reloaded.

Fixes #123
```

```text
fix(cli): prevent crash when config file is missing

Added graceful fallback to default configuration when user
config file does not exist.

Fixes #456
```

## Pull Request Process

### Before Submitting

1. **Run all checks**:

   ```bash
   pre-commit run --all-files
   uv run pytest
   ```

2. **Update documentation** if needed:
   - README.md
   - CLAUDE.md
   - CLI help text
   - Code docstrings

3. **Ensure no secrets** are committed:
   - Check for API keys, tokens, passwords
   - Review `.env` files
   - Use `.gitignore` appropriately

### PR Requirements

- [ ] Clear description of changes
- [ ] Related issue linked
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] All CI checks passing
- [ ] No merge conflicts
- [ ] Commits follow convention
- [ ] No sensitive data committed

### Review Process

1. Maintainers will review your PR
2. Address feedback and requested changes
3. Keep PR updated with main branch
4. Once approved, maintainer will merge

### CI/CD Pipeline

PRs must pass:

- Python build
- Unit tests
- Linting (ruff)
- Type checking (mypy)
- Code formatting checks

## Security

### Reporting Vulnerabilities

**DO NOT** open public issues for security vulnerabilities.

Use [GitHub Security Advisories](https://github.com/Recipe-Web-App/system-control/security/advisories/new) to
report security issues privately.

### Security Guidelines

- Never commit secrets or credentials
- Validate all user inputs
- Use safe file operations (avoid path traversal)
- Be careful with shell command execution
- Follow secure coding practices

## Questions?

- Check the [README](../README.md)
- Review existing [issues](https://github.com/Recipe-Web-App/system-control/issues)
- Start a [discussion](https://github.com/Recipe-Web-App/system-control/discussions)
- See [SUPPORT.md](SUPPORT.md) for help resources

Thank you for contributing!
