# Installation Guide

This guide covers the installation and initial setup of the System Control CLI.

## Prerequisites

### System Requirements

- **Operating System**: Linux, macOS, or Windows
- **Python**: 3.14 or higher
- **pipx**: For isolated CLI installation ([install pipx](https://pipx.pypa.io/stable/installation/))
- **Memory**: 512 MB RAM minimum, 1 GB recommended
- **Disk Space**: 100 MB for installation, additional space for logs and configuration

### Required Tools

- **Git**: For version control and repository management
- **SSH Client**: For remote server management (OpenSSH recommended)
- **Docker** (optional): For containerized deployments
- **kubectl** (optional): For Kubernetes integration

## Installation Methods

### Method 1: pipx Installation (Recommended)

pipx installs `ops` in an isolated virtual environment and makes it available globally
without affecting your system Python or other projects.

```bash
# Install from local source
pipx install . --python python3.14

# Install with optional dependencies
pipx install ".[kubernetes,monitoring,vault]" --python python3.14

# Install with all optional dependencies
pipx install ".[all]" --python python3.14

# Install in editable/development mode (code changes take effect immediately)
pipx install -e . --python python3.14
```

### Method 2: Poetry (For Development)

Use Poetry for contributing to the project or running tests:

```bash
# Clone the repository
git clone https://github.com/Recipe-Web-App/system-control.git
cd system-control

# Install dependencies
poetry install

# Install with all optional dependencies
poetry install --all-extras

# Run commands via Poetry
poetry run ops --version
poetry run ops status
```

### Method 3: Docker Installation

```bash
# Pull the official image
docker pull systemcontrol/cli:latest

# Create an alias for convenience
echo 'alias ops="docker run --rm -it -v $(pwd):/workspace systemcontrol/cli"' >> ~/.bashrc
source ~/.bashrc

# Run commands
ops --version
```

## Optional Dependencies

### Kubernetes Integration

```bash
pipx install ".[kubernetes]" --python python3.14
# Installs: kubernetes, kr8s, ruamel-yaml
```

### Monitoring Integration

```bash
pipx install ".[monitoring]" --python python3.14
# Installs: prometheus-client, grafana-api, elasticsearch, opentelemetry
```

### Secret Management

```bash
pipx install ".[vault]" --python python3.14
# Installs: hvac (HashiCorp Vault), boto3, azure-keyvault, google-cloud-secret-manager
```

### All Optional Dependencies

```bash
pipx install ".[all]" --python python3.14
```

## Initial Setup

### 1. Verify Installation

```bash
# Check version
ops --version

# View help
ops --help
```

### 2. Install Shell Completion

```bash
# Auto-detect shell and install completion
ops --install-completion
```

### 3. Initialize Configuration

```bash
# Create default configuration
ops init

# Initialize with specific profile
ops init --profile production

# Overwrite existing configuration
ops init --force
```

This creates the following configuration structure:

```text
~/.config/ops/
├── config.yaml              # Main configuration
├── profiles/                 # Profile-specific configs
│   ├── development.yaml
│   ├── staging.yaml
│   └── production.yaml
├── plugins/                  # Plugin configurations
├── secrets/                  # Encrypted secrets (if using local storage)
└── logs/                     # Application logs
```

### 4. Configure Profiles

Edit the configuration files or use the CLI:

```bash
# View current configuration
ops config show
ops config show --profile production
```

## Upgrading

```bash
# Upgrade to latest version
pipx upgrade system-operations-cli

# Force reinstall
pipx install . --python python3.14 --force
```

### Backup Before Upgrade

```bash
# Backup configuration
cp -r ~/.config/ops ~/.config/ops.backup
```

## Uninstallation

```bash
# Uninstall the CLI
pipx uninstall system-operations-cli

# Remove configuration (optional)
rm -rf ~/.config/ops
```

## Troubleshooting

### Common Issues

#### 1. Command Not Found

```bash
# Check if installed via pipx
pipx list | grep system-operations-cli

# Ensure ~/.local/bin is on your PATH
echo $PATH | tr ':' '\n' | grep local/bin

# Reinstall if needed
pipx install . --python python3.14 --force
```

#### 2. Python Version Error

The CLI requires Python 3.14+. Check your available Python versions:

```bash
python3 --version
python3.14 --version
```

#### 3. Plugin Loading Errors

```bash
# List available plugins
ops plugins list

# Check plugin status
ops plugins status
```

### Debug Mode

Enable debug mode for detailed troubleshooting:

```bash
# Run with debug flag
ops --debug status

# Run with verbose output
ops --verbose status
```

### Getting Help

If you encounter issues:

1. **Check Documentation**: Review relevant documentation sections
2. **Search Issues**: Check [GitHub issues](https://github.com/Recipe-Web-App/system-control/issues) for similar problems
3. **Enable Debug Mode**: Use `--debug` flag for detailed output
4. **Report Bugs**: Create a new issue with debug information

## Next Steps

After installation:

1. **[Configure Profiles](configuration/profiles.md)** - Set up environment-specific configurations
2. **[Learn Basic Commands](commands/)** - Explore core functionality
3. **[Set Up Integrations](integrations/)** - Connect external tools
4. **[Try Examples](examples/basic-usage.md)** - Follow guided tutorials
