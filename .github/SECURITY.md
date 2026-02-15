# Security Policy

## Supported Versions

We release security updates for the following versions:

| Version  | Supported          |
| -------- | ------------------ |
| latest   | :white_check_mark: |
| < latest | :x:                |

We recommend always running the latest version for security patches.

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

### Private Reporting (Preferred)

Report security vulnerabilities using [GitHub Security Advisories](https://github.com/Recipe-Web-App/system-control/security/advisories/new).

This allows us to:

- Discuss the vulnerability privately
- Develop and test a fix
- Coordinate disclosure timing
- Issue a CVE if necessary

### What to Include

When reporting a vulnerability, please include:

1. **Description** - Clear description of the vulnerability
2. **Impact** - What can an attacker achieve?
3. **Reproduction Steps** - Step-by-step instructions to reproduce
4. **Affected Components** - Which parts of the CLI are affected
5. **Suggested Fix** - If you have ideas for remediation
6. **Environment** - Version, configuration, deployment details
7. **Proof of Concept** - Code or commands demonstrating the issue (if safe to share)

### Example Report

```text
Title: Command Injection via Config File

Description: User-controlled input in config file is passed to shell
without proper sanitization...

Impact: An attacker can execute arbitrary commands with the user's
privileges...

Steps to Reproduce:
1. Create a config file with malicious value in 'command' field
2. Run 'ops execute --config malicious.yml'
3. Observe shell command execution

Affected: src/system_operations_manager/core/executor.py line 145

Suggested Fix: Use subprocess with shell=False and proper argument handling

Environment: v0.1.0, uv installation
```

## Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Varies by severity (critical: days, high: weeks, medium: months)

## Severity Levels

### Critical

- Remote code execution
- Privilege escalation
- Credential exposure (API keys, passwords)
- Mass data exposure

### High

- Command injection
- Path traversal with file access
- Unauthorized access to sensitive data
- Denial of service affecting all users

### Medium

- Information disclosure (limited)
- Configuration bypass
- Rate limiting bypass
- Insecure defaults

### Low

- Verbose error messages
- Best practice violations
- Minor information leakage

## Security Features

This CLI implements multiple security layers:

### Input Validation

- **Configuration Validation** - Pydantic models for all configuration
- **Path Sanitization** - Protection against path traversal attacks
- **Command Sanitization** - Safe execution of shell commands

### Credential Security

- **Environment Variables** - Secrets via environment (never in code)
- **Secure Storage** - Integration with system keyring where available
- **No Logging of Secrets** - Sensitive data redacted from logs

### Plugin Security

- **Plugin Isolation** - Plugins run with limited permissions
- **Signature Verification** - Optional plugin signing (when enabled)
- **Sandboxed Execution** - Restricted access to system resources

### Infrastructure

- **Audit Logging** - Comprehensive action logging with structlog
- **Health Monitoring** - Built-in health check commands
- **Secure Defaults** - Conservative default configuration

## Security Best Practices

### For Users

1. **Keep Updated** - Always run the latest version
2. **Review Configs** - Check configuration files for unexpected values
3. **Limit Permissions** - Run with minimal required privileges
4. **Secure Credentials** - Use environment variables for secrets
5. **Monitor Logs** - Watch for suspicious patterns
6. **Verify Plugins** - Only install plugins from trusted sources

### For Developers

1. **Never Commit Secrets** - Use `.env.local` (gitignored)
2. **Validate Inputs** - Sanitize all user inputs
3. **Use subprocess Safely** - Avoid shell=True, use argument lists
4. **Handle Errors Securely** - Don't leak sensitive info in errors
5. **Run Security Checks** - Use `bandit` before committing
6. **Review Dependencies** - Check for known vulnerabilities
7. **Test Security** - Include security test cases

## Security Checklist

Before deploying:

- [ ] Secrets in environment variables (not code/config files)
- [ ] Configuration validated
- [ ] Plugins from trusted sources only
- [ ] Logging configured (secrets redacted)
- [ ] Dependencies updated
- [ ] Security scan passed
- [ ] File permissions reviewed

## Disclosure Policy

We follow **coordinated disclosure**:

1. Vulnerability reported privately
2. We confirm and develop fix
3. Fix tested and released
4. Public disclosure after fix is deployed
5. Credit given to reporter (if desired)

## Security Updates

Subscribe to:

- [GitHub Security Advisories](https://github.com/Recipe-Web-App/system-control/security/advisories)
- [Release Notes](https://github.com/Recipe-Web-App/system-control/releases)
- Watch repository for security patches

## Contact

For security concerns: Use [GitHub Security Advisories](https://github.com/Recipe-Web-App/system-control/security/advisories/new)

For general questions: See [SUPPORT.md](SUPPORT.md)

## Acknowledgments

We thank security researchers who responsibly disclose vulnerabilities. Contributors will be acknowledged (with
permission) in:

- Security advisories
- Release notes
- This document

Thank you for helping keep this project secure!
