# Support

Thank you for using System Control CLI! This document provides resources to help you get support.

## Documentation

Before asking for help, please check our documentation:

### Primary Documentation

- **[README.md](../README.md)** - Complete feature overview, setup instructions, and usage examples
- **[CLAUDE.md](../CLAUDE.md)** - Development commands, architecture overview, and developer guide
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines and development workflow
- **[SECURITY.md](SECURITY.md)** - Security features, best practices, and vulnerability reporting

### Configuration

- **[pyproject.toml](../pyproject.toml)** - Package configuration and dependencies
- **Configuration Hierarchy** - Default -> System -> User -> Project -> Environment -> CLI args

## Getting Help

### 1. Search Existing Resources

Before creating a new issue, please search:

- [Existing Issues](https://github.com/Recipe-Web-App/system-control/issues) - Someone may have already asked
- [Closed Issues](https://github.com/Recipe-Web-App/system-control/issues?q=is%3Aissue+is%3Aclosed) - Your question
  may already be answered
- [Discussions](https://github.com/Recipe-Web-App/system-control/discussions) - Community Q&A

### 2. GitHub Discussions (Recommended for Questions)

For general questions, use [GitHub Discussions](https://github.com/Recipe-Web-App/system-control/discussions):

**When to use Discussions:**

- "How do I...?" questions
- Configuration help
- Best practice advice
- Plugin development questions
- Integration questions
- Architecture discussions
- Troubleshooting (non-bug)

**Categories:**

- **Q&A** - Ask questions and get answers
- **Ideas** - Share feature ideas and proposals
- **Show and Tell** - Share your plugins and integrations
- **General** - Everything else

### 3. GitHub Issues (For Bugs and Features)

Use [GitHub Issues](https://github.com/Recipe-Web-App/system-control/issues/new/choose) for:

- Bug reports
- Feature requests
- Performance issues
- Documentation problems
- Security vulnerabilities (low severity - use Security Advisories for critical)

**Issue Templates:**

- **Bug Report** - Report unexpected behavior
- **Feature Request** - Suggest new functionality
- **Performance Issue** - Report performance problems
- **Documentation** - Documentation improvements
- **Security Vulnerability** - Low-severity security issues

### 4. Security Issues

**IMPORTANT:** For security vulnerabilities, use:

- [GitHub Security Advisories](https://github.com/Recipe-Web-App/system-control/security/advisories/new) (private)
- See [SECURITY.md](SECURITY.md) for details

**Never report security issues publicly through issues or discussions.**

## Common Questions

### Setup and Configuration

**Q: How do I get started?**
A: See the Quick Start section in [README.md](../README.md#quick-start)

**Q: How do I install the CLI?**
A: Install with pipx: `pipx install . --python python3.14` (for development, use `poetry install`)

**Q: Where does the CLI look for configuration?**
A: Configuration is loaded in order: `~/.config/ops/config.yml` -> project `ops.yml` -> environment variables -> CLI arguments

**Q: How do I enable shell completions?**
A: After installing via pipx, run `ops --install-completion` to set up completions for your shell

### CLI Usage

**Q: What commands are available?**
A: Run `poetry run ops --help` for a complete list of commands

**Q: How do I check the CLI version?**
A: Run `poetry run ops --version`

**Q: How do I get help for a specific command?**
A: Run `poetry run ops <command> --help`

### Plugin Development

**Q: How do I create a custom plugin?**
A: Plugins inherit from the `Plugin` base class. See [CLAUDE.md](../CLAUDE.md) for the plugin architecture

**Q: How do I register a plugin?**
A: Define entry points in `pyproject.toml` under `[tool.poetry.plugins."system_operations_manager.plugins"]`

**Q: What hooks are available for plugins?**
A: Plugins can implement `initialize()`, `register_commands()`, and `cleanup()` methods

### Troubleshooting

**Q: CLI fails to start?**

- Check Python version: `python --version` (requires 3.14+)
- Verify installation: `poetry install`
- Check configuration: `poetry run ops config validate`
- Review logs in `~/.config/ops/logs/`

**Q: Command not found?**

- Ensure `~/.local/bin` is on your PATH (pipx's default bin directory)
- Verify installation: `pipx list | grep system-operations-cli`
- Reinstall if needed: `pipx install . --python python3.14 --force`

**Q: Configuration not loading?**

- Check file permissions
- Validate YAML syntax
- Review configuration hierarchy

### Development

**Q: How do I contribute?**
A: See [CONTRIBUTING.md](CONTRIBUTING.md) for complete guidelines

**Q: How do I run tests?**
A: Run `poetry run pytest` or see [CLAUDE.md](../CLAUDE.md) for test commands

**Q: What's the code structure?**
A: See Architecture section in [CLAUDE.md](../CLAUDE.md)

## Response Times

We aim to:

- Acknowledge issues/discussions within 48 hours
- Respond to questions within 1 week
- Fix critical bugs as priority
- Review PRs within 1-2 weeks

Note: This is a community project. Response times may vary.

## Community Guidelines

When asking for help:

- **Be specific** - Include exact error messages, versions, configurations
- **Provide context** - What were you trying to do? What happened instead?
- **Include details** - Python version, OS, installation method, relevant logs
- **Be patient** - Maintainers and community volunteers help in their free time
- **Be respectful** - Follow the [Code of Conduct](CODE_OF_CONDUCT.md)
- **Search first** - Check if your question was already answered
- **Give back** - Help others when you can

## Bug Report Best Practices

When reporting bugs, include:

- Python version
- CLI version (`ops --version`)
- Operating system
- Installation method (pipx/Poetry)
- Exact error messages
- Steps to reproduce
- Expected vs actual behavior
- Relevant configuration (redact secrets!)
- Logs (redact sensitive info!)

Use the Bug Report Template - it helps ensure you provide all needed information.

## Additional Resources

### Python Resources

- [Python Documentation](https://docs.python.org/3/)
- [Poetry Documentation](https://python-poetry.org/docs/)
- [Typer Documentation](https://typer.tiangolo.com/)

### Related Projects

- [Typer](https://github.com/tiangolo/typer) - CLI framework
- [Rich](https://github.com/Textualize/rich) - Terminal formatting
- [Pydantic](https://github.com/pydantic/pydantic) - Data validation
- [structlog](https://github.com/hynek/structlog) - Structured logging

## Still Need Help?

If you can't find an answer:

1. Check [Discussions](https://github.com/Recipe-Web-App/system-control/discussions)
2. Ask a new question in [Q&A](https://github.com/Recipe-Web-App/system-control/discussions/new?category=q-a)
3. For bugs, create an [Issue](https://github.com/Recipe-Web-App/system-control/issues/new/choose)

We're here to help!
