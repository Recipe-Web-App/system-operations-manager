# Contributing to System Control CLI

We welcome contributions to the System Control CLI! This document provides guidelines and
information for contributors.

## 🚀 Getting Started

### Prerequisites

- Python 3.14 or higher
- Git
- Poetry (`pip install poetry`)

### Development Setup

1. **Fork and clone the repository**

   ```bash
   git clone https://github.com/Recipe-Web-App/system-control.git
   cd system-control
   ```

2. **Install dependencies with Poetry**

   ```bash
   poetry install --all-extras
   ```

3. **Install pre-commit hooks**

   ```bash
   pre-commit install
   ```

4. **Verify installation**

   ```bash
   poetry run ops --version
   pytest
   ```

## 📁 Project Structure

```text
system-control/
├── src/
│   └── system_operations_manager/        # Main package
│       ├── cli/              # CLI command definitions
│       ├── core/             # Core engine and plugin system
│       ├── services/         # Business logic services
│       ├── integrations/     # External tool integrations
│       ├── plugins/          # Built-in plugins
│       └── utils/            # Utility functions
├── tests/                    # Test suite
├── docs/                     # Documentation
├── requirements/             # Dependency specifications
└── scripts/                  # Development and build scripts
```

## 🛠️ Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

Use descriptive branch names:

- `feature/add-kubernetes-integration`
- `bugfix/fix-deployment-rollback`
- `docs/update-api-documentation`

### 2. Development Guidelines

#### Code Style

- Follow PEP 8 Python style guidelines
- Use type hints for all function signatures
- Maximum line length: 88 characters (Black formatter)
- Use descriptive variable and function names

#### Code Quality Tools

- **Black**: Automatic code formatting
- **isort**: Import sorting
- **flake8**: Linting and style checking
- **mypy**: Static type checking
- **pre-commit**: Automated checks before commits

#### Run Quality Checks

```bash
# Format code
black src tests
isort src tests

# Lint code
flake8 src tests

# Type checking
mypy src

# Run all checks
pre-commit run --all-files
```

### 3. Testing

#### Test Categories

- **Unit Tests**: Test individual functions and classes
- **Integration Tests**: Test plugin integrations and external APIs
- **CLI Tests**: Test command-line interface functionality
- **End-to-End Tests**: Test complete workflows

#### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=system_operations_manager

# Run specific test file
pytest tests/test_deployment.py

# Run tests matching pattern
pytest -k "test_deployment"

# Run tests with verbose output
pytest -v
```

#### Writing Tests

- Use descriptive test names: `test_deployment_rollback_on_health_check_failure`
- Follow AAA pattern: Arrange, Act, Assert
- Use fixtures for common test data
- Mock external dependencies
- Test both success and error cases

Example:

```python
def test_service_deployment_success(mock_kubernetes_client):
    # Arrange
    service_config = ServiceConfig(name="test-service", image="nginx:latest")
    deployer = ServiceDeployer(mock_kubernetes_client)

    # Act
    result = deployer.deploy(service_config)

    # Assert
    assert result.success is True
    assert result.service_name == "test-service"
    mock_kubernetes_client.create_deployment.assert_called_once()
```

### 4. Documentation

#### Documentation Types

- **API Documentation**: Docstrings for all public functions/classes
- **User Guides**: Step-by-step instructions for features
- **Developer Guides**: Technical implementation details
- **Examples**: Real-world usage scenarios

#### Writing Documentation

- Use clear, concise language
- Include code examples
- Keep documentation up-to-date with code changes
- Use proper Markdown formatting

#### Building Documentation

```bash
# Build documentation locally
cd docs
make html

# Serve documentation locally
make serve
```

### 5. Plugin Development

#### Creating a New Plugin

1. **Create plugin directory**

   ```bash
   mkdir src/system_operations_manager/plugins/my_plugin
   touch src/system_operations_manager/plugins/my_plugin/__init__.py
   ```

2. **Implement plugin interface**

   ```python
   from system_operations_manager.core.plugin import SystemControlPlugin

   class MyPlugin(SystemControlPlugin):
       def initialize(self, config):
           # Plugin initialization
           pass

       def register_commands(self, cli):
           # Register CLI commands
           pass
   ```

3. **Add plugin entry point**
   Update `pyproject.toml`:

   ```toml
   [project.entry-points."system_operations_manager.plugins"]
   my_plugin = "system_operations_manager.plugins.my_plugin:MyPlugin"
   ```

4. **Write tests**

   ```python
   def test_my_plugin_initialization():
       plugin = MyPlugin()
       plugin.initialize(test_config)
       assert plugin.is_initialized
   ```

## 🔍 Code Review Process

### Pull Request Guidelines

1. **PR Title**: Use descriptive titles following conventional commits
   - `feat: add Kubernetes deployment support`
   - `fix: resolve configuration validation error`
   - `docs: update installation guide`

2. **PR Description**: Include:
   - Clear description of changes
   - Motivation and context
   - Testing performed
   - Screenshots (for UI changes)
   - Breaking changes (if any)

3. **PR Size**: Keep PRs focused and reasonably sized
   - Aim for < 500 lines changed
   - Split large features into multiple PRs
   - Each PR should address one concern

### Review Checklist

**For Contributors:**

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] Documentation updated
- [ ] No breaking changes (or clearly documented)
- [ ] Self-review completed

**For Reviewers:**

- [ ] Code is readable and maintainable
- [ ] Logic is sound and efficient
- [ ] Edge cases are handled
- [ ] Tests provide good coverage
- [ ] Documentation is accurate

### Review Process

1. **Automated Checks**: CI/CD pipeline runs automatically
2. **Peer Review**: At least one maintainer reviews code
3. **Testing**: Manual testing for complex features
4. **Approval**: Maintainer approves and merges PR

## 🐛 Bug Reports

### Before Reporting

1. Search existing issues
2. Try the latest version
3. Reproduce with minimal example

### Bug Report Template

```markdown
**Bug Description**
Clear description of the bug

**Steps to Reproduce**

1. Run command: `sysctl deploy service-name`
2. Observe error message
3. Check logs

**Expected Behavior**
What should happen

**Actual Behavior**
What actually happens

**Environment**

- OS: Ubuntu 20.04
- Python: 3.9.5
- System Control CLI: 1.0.0

**Additional Context**
Any other relevant information
```

## 💡 Feature Requests

### Feature Request Template

```markdown
**Feature Description**
Clear description of the proposed feature

**Use Case**
Why is this feature needed?

**Proposed Solution**
How should this be implemented?

**Alternatives Considered**
Other approaches you've considered

**Additional Context**
Mockups, examples, etc.
```

## 🚀 Release Process

### Versioning

We use [Semantic Versioning](https://semver.org/):

- **Major**: Breaking changes
- **Minor**: New features (backward compatible)
- **Patch**: Bug fixes (backward compatible)

### Release Steps

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create and push git tag
4. GitHub Actions handles PyPI publication
5. Create GitHub release with notes

## 🤝 Community Guidelines

### Code of Conduct

We follow the [Contributor Covenant](https://www.contributor-covenant.org/) code of conduct.
Please be respectful and inclusive in all interactions.

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Pull Requests**: Code contributions and reviews

### Recognition

We value all contributions! Contributors are recognized in:

- Release notes
- Contributors file
- GitHub contributors list

## 📚 Additional Resources

- [Architecture Documentation](ARCHITECTURE.md)
- [Plugin Development Guide](docs/plugins/development.md)
- [CLI Command Reference](docs/commands/)
- [Integration Guides](docs/integrations/)

## ❓ Getting Help

If you need help:

1. Check the [documentation](docs/)
2. Search [existing issues](../../issues)
3. Ask in [discussions](../../discussions)
4. Contact maintainers

Thank you for contributing to System Control CLI! 🎉
