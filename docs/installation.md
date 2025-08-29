# Installation Guide

This guide covers the installation and initial setup of the System Control CLI.

## Prerequisites

### System Requirements

- **Operating System**: Linux, macOS, or Windows
- **Python**: 3.8 or higher
- **Memory**: 512 MB RAM minimum, 1 GB recommended
- **Disk Space**: 100 MB for installation, additional space for logs and configuration

### Required Tools

- **Git**: For version control and repository management
- **SSH Client**: For remote server management (OpenSSH recommended)
- **Docker** (optional): For containerized deployments
- **kubectl** (optional): For Kubernetes integration

## Installation Methods

### Method 1: PyPI Installation (Recommended)

```bash
# Install the latest stable version
pip install system-control-cli

# Install with optional dependencies
pip install "system-control-cli[kubernetes,monitoring,vault]"

# Install development version
pip install --pre system-control-cli
```

### Method 2: Installation from Source

```bash
# Clone the repository
git clone https://github.com/yourusername/system-control.git
cd system-control

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Install with all optional dependencies
pip install -e ".[all]"
```

### Method 3: Docker Installation

```bash
# Pull the official image
docker pull systemcontrol/cli:latest

# Create an alias for convenience
echo 'alias sysctl="docker run --rm -it -v $(pwd):/workspace systemcontrol/cli"' >> ~/.bashrc
source ~/.bashrc

# Run commands
sysctl --version
```

## Optional Dependencies

### Kubernetes Integration

```bash
pip install "system-control-cli[kubernetes]"
# Installs: kubernetes, kubectl-wrapper
```

### Monitoring Integration

```bash
pip install "system-control-cli[monitoring]"
# Installs: prometheus-client, grafana-api
```

### Secret Management

```bash
pip install "system-control-cli[vault]"
# Installs: hvac (HashiCorp Vault client)
```

### All Optional Dependencies

```bash
pip install "system-control-cli[all]"
```

## Initial Setup

### 1. Verify Installation

```bash
# Check version
sysctl --version

# View help
sysctl --help

# Check system requirements
sysctl doctor
```

### 2. Initialize Configuration

```bash
# Create default configuration
sysctl init

# Initialize with specific profile
sysctl init --profile production

# Interactive setup
sysctl init --interactive
```

This creates the following configuration structure:

```text
~/.config/system-control/
├── config.yaml              # Main configuration
├── profiles/                 # Profile-specific configs
│   ├── development.yaml
│   ├── staging.yaml
│   └── production.yaml
├── plugins/                  # Plugin configurations
├── secrets/                  # Encrypted secrets (if using local storage)
└── logs/                     # Application logs
```

### 3. Configure Profiles

Edit the configuration files or use the CLI:

```bash
# Set default profile
sysctl config set-profile development

# Configure environment-specific settings
sysctl config set deployment.strategy blue-green --profile production
sysctl config set monitoring.enabled true --profile production

# View current configuration
sysctl config show
sysctl config show --profile production
```

## Platform-Specific Setup

### Linux/macOS

```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv git openssh-client

# Install system dependencies (CentOS/RHEL/Fedora)
sudo yum install -y python3-pip git openssh-clients
# or
sudo dnf install -y python3-pip git openssh-clients

# macOS with Homebrew
brew install python3 git openssh

# Add shell completion
echo 'eval "$(_SYSCTL_COMPLETE=bash_source sysctl)"' >> ~/.bashrc
# or for zsh
echo 'eval "$(_SYSCTL_COMPLETE=zsh_source sysctl)"' >> ~/.zshrc
```

### Windows

```powershell
# Install Python from python.org or Microsoft Store
# Install Git from git-scm.com

# Install using pip
pip install system-control-cli

# Add to PATH (if needed)
# Add Python Scripts directory to system PATH

# PowerShell completion
# Add to PowerShell profile
Register-ArgumentCompleter -Native -CommandName sysctl -ScriptBlock {
    param($commandName, $wordToComplete, $cursorPosition)
    sysctl completion powershell | ForEach-Object {
        [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
    }
}
```

## Environment Configuration

### Environment Variables

Common environment variables:

```bash
# Configuration directory
export SYSCTL_CONFIG_DIR="$HOME/.config/system-control"

# Default profile
export SYSCTL_PROFILE="development"

# Log level
export SYSCTL_LOG_LEVEL="INFO"

# Disable colors (for scripting)
export SYSCTL_NO_COLOR="1"

# API server settings
export SYSCTL_API_HOST="localhost"
export SYSCTL_API_PORT="8080"
```

### Configuration File

Basic `~/.config/system-control/config.yaml`:

```yaml
# Global settings
default_profile: "development"
log_level: "INFO"
color_output: true
confirm_destructive_operations: true

# Plugin settings
plugins:
  enabled:
    - "kubernetes"
    - "monitoring"
    - "deployment"
  directories:
    - "~/.config/system-control/plugins"
    - "/usr/local/share/system-control/plugins"

# API server settings
api:
  enabled: false
  host: "localhost"
  port: 8080
  auth:
    enabled: false

# Integration settings
integrations:
  kubernetes:
    config_path: "~/.kube/config"
    context: ""

  vault:
    url: "https://vault.example.com:8200"
    auth_method: "token"

  monitoring:
    prometheus_url: "http://prometheus.example.com:9090"
    grafana_url: "http://grafana.example.com:3000"
```

## Verification

### Basic Functionality Test

```bash
# Test configuration
sysctl config validate

# Test plugin loading
sysctl plugins list

# Test connectivity (if integrations configured)
sysctl test connectivity

# View system status
sysctl status
```

### Integration Tests

```bash
# Test Kubernetes integration
sysctl k8s test-connection

# Test monitoring integration
sysctl monitoring test-connection

# Test vault integration
sysctl vault test-connection
```

## Troubleshooting

### Common Issues

#### 1. Command Not Found

```bash
# Check if installed
pip show system-control-cli

# Check PATH
which sysctl

# Reinstall if needed
pip uninstall system-control-cli
pip install system-control-cli
```

#### 2. Permission Errors

```bash
# Install for user only
pip install --user system-control-cli

# Fix permissions
chmod +x ~/.local/bin/sysctl
```

#### 3. Configuration Issues

```bash
# Reset configuration
sysctl init --reset

# Validate configuration
sysctl config validate --verbose

# Check logs
sysctl logs show
```

#### 4. Plugin Loading Errors

```bash
# List available plugins
sysctl plugins available

# Check plugin status
sysctl plugins status

# Reload plugins
sysctl plugins reload
```

### Debug Mode

Enable debug mode for detailed troubleshooting:

```bash
# Set log level
export SYSCTL_LOG_LEVEL="DEBUG"

# Run with debug flag
sysctl --debug command

# View debug logs
sysctl logs show --level debug
```

### Getting Help

If you encounter issues:

1. **Check Documentation**: Review relevant documentation sections
2. **Search Issues**: Check [GitHub issues](../../issues) for similar problems
3. **Enable Debug Mode**: Use `--debug` flag for detailed output
4. **Check Logs**: Review logs in `~/.config/system-control/logs/`
5. **Report Bugs**: Create a new issue with debug information

## Upgrading

### Upgrade from PyPI

```bash
# Upgrade to latest version
pip install --upgrade system-control-cli

# Upgrade with all optional dependencies
pip install --upgrade "system-control-cli[all]"
```

### Backup Before Upgrade

```bash
# Backup configuration
cp -r ~/.config/system-control ~/.config/system-control.backup

# After upgrade, migrate if needed
sysctl config migrate
```

## Uninstallation

```bash
# Uninstall package
pip uninstall system-control-cli

# Remove configuration (optional)
rm -rf ~/.config/system-control

# Remove completion (if added manually)
# Remove sysctl completion lines from shell configuration
```

## Next Steps

After installation:

1. **[Configure Profiles](configuration/profiles.md)** - Set up environment-specific configurations
2. **[Learn Basic Commands](commands/)** - Explore core functionality
3. **[Set Up Integrations](integrations/)** - Connect external tools
4. **[Try Examples](examples/basic-usage.md)** - Follow guided tutorials
