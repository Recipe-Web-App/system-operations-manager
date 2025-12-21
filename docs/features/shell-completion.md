# Shell Completion

Advanced shell completion support for bash, zsh, fish, and PowerShell, providing
intelligent auto-completion for commands, options, and arguments.

## Overview

Shell completion features:

- **Multi-Shell Support**: Native completion for bash, zsh, fish, PowerShell
- **Context-Aware**: Intelligent suggestions based on current context
- **Dynamic Completion**: Real-time completion for services, environments, etc.
- **Custom Completions**: Extensible completion system for plugins
- **Fuzzy Matching**: Smart matching for partial inputs
- **Help Integration**: Inline help text during completion

## Installation

### Bash Completion

```bash
# Generate completion script
sysctl completion bash > ~/.local/share/bash-completion/completions/sysctl

# Or add to .bashrc
echo 'eval "$(sysctl completion bash)"' >> ~/.bashrc
source ~/.bashrc

# For system-wide installation
sudo sysctl completion bash > /etc/bash_completion.d/sysctl
```

### Zsh Completion

```bash
# Generate completion script
sysctl completion zsh > ~/.zsh/completions/_sysctl

# Or add to .zshrc
echo 'eval "$(sysctl completion zsh)"' >> ~/.zshrc
source ~/.zshrc

# For oh-my-zsh users
sysctl completion zsh > ~/.oh-my-zsh/completions/_sysctl
```

### Fish Completion

```bash
# Generate completion script
sysctl completion fish > ~/.config/fish/completions/sysctl.fish

# Or install directly
sysctl completion fish --install
```

### PowerShell Completion

```powershell
# Generate completion script
sysctl completion powershell > $PROFILE

# Or add to profile
Add-Content $PROFILE "`nRegister-ArgumentCompleter -Native -CommandName sysctl `
  -ScriptBlock {`n$(sysctl completion powershell)`n}"

# Reload profile
. $PROFILE
```

## Basic Usage

### Command Completion

```bash
# Complete commands
sysctl dep[TAB]
deploy  dependencies

# Complete subcommands
sysctl deploy [TAB]
api     worker  database  scheduler  --all

# Complete options
sysctl deploy api --[TAB]
--env           --image         --strategy      --dry-run
--environment   --replicas      --timeout       --force
```

### Argument Completion

```bash
# Environment completion
sysctl deploy api --env [TAB]
development  staging  production

# Service name completion
sysctl status [TAB]
api  worker  database  redis  scheduler  monitoring

# File path completion
sysctl config update --file [TAB]
configs/api.yaml  configs/worker.yaml  templates/

# Strategy completion
sysctl deploy api --strategy [TAB]
rolling  blue-green  canary  recreate
```

## Dynamic Completions

### Service Discovery

```bash
# Complete with running services
sysctl restart [TAB]
# Queries actual running services:
api-v2.1.0  worker-v1.5.0  database-primary  redis-cache

# Complete with healthy services only
sysctl deploy [TAB]
# Shows only healthy services ready for deployment
```

### Configuration Keys

```bash
# Complete configuration keys
sysctl config get [TAB]
api.timeout  api.retries  database.pool_size  logging.level

# Nested configuration
sysctl config get api.[TAB]
api.timeout  api.retries  api.max_connections  api.cache_ttl
```

### Git-Style Completion

```bash
# Complete git-like references
sysctl rollback --to [TAB]
HEAD  HEAD~1  HEAD~2  v2.1.0  v2.0.5  stable  production

# Branch/tag completion
sysctl deploy --ref [TAB]
main  develop  feature/new-api  release/v2.1.0  hotfix/bug-123
```

## Advanced Features

### Fuzzy Matching

```bash
# Fuzzy match service names
sysctl status ap[TAB]
api  api-gateway  application-server

# Fuzzy match commands
sysctl depl[TAB]
deploy  deployment-status  deployment-history

# Case-insensitive matching
sysctl status API[TAB]
api  api-gateway
```

### Contextual Suggestions

```bash
# Context-aware environment suggestions
cd ~/projects/production
sysctl deploy api --env [TAB]
# Suggests 'production' first based on directory

# Previous command context
sysctl deploy api --env staging
sysctl rollback [TAB]
# Suggests 'api' as it was just deployed
```

### Multi-Value Completion

```bash
# Complete multiple values
sysctl deploy --services [TAB]
api,worker,database  api,worker  all

# Complete comma-separated lists
sysctl monitor --metrics [TAB]
cpu,memory  cpu,memory,disk  cpu  memory  network
```

## Custom Completions

### Plugin Completions

```python
# plugins/custom_plugin.py
from system_operations_manager.completion import CompletionProvider

class CustomCompletions(CompletionProvider):
    def get_completions(self, word, context):
        """Return completions for custom plugin commands."""

        if context.command == "custom-deploy":
            if context.current_option == "--template":
                return self.get_template_names()
            elif context.current_option == "--profile":
                return self.get_profile_names()

        return []

    def get_template_names(self):
        # Return available templates
        return ["web-app", "microservice", "batch-job", "api-gateway"]

    def get_profile_names(self):
        # Return available profiles
        return ["fast", "balanced", "thorough", "custom"]
```

### Registering Custom Completions

```yaml
# plugins/completion-config.yaml
completions:
  custom_plugin:
    commands:
      - name: "custom-deploy"
        options:
          --template:
            type: "dynamic"
            provider: "get_template_names"
          --profile:
            type: "choice"
            choices: ["fast", "balanced", "thorough"]

      - name: "custom-scale"
        arguments:
          service:
            type: "dynamic"
            provider: "get_service_names"
          replicas:
            type: "range"
            min: 1
            max: 100
```

## Completion Configuration

### Shell Configuration

```yaml
# config/completion.yaml
completion:
  # General settings
  enabled: true
  case_sensitive: false
  fuzzy_matching: true
  show_descriptions: true

  # Shell-specific settings
  bash:
    show_help: true
    group_options: true

  zsh:
    menu_complete: true
    auto_description: true
    color_output: true

  fish:
    abbreviations: true

  powershell:
    validate_input: true

  # Performance settings
  cache:
    enabled: true
    ttl: 60 # seconds

  # Dynamic completion settings
  dynamic:
    timeout: 2 # seconds
    max_results: 50
    async: true
```

### Completion Aliases

```bash
# Define completion aliases
sysctl completion alias d=deploy
sysctl completion alias s=status
sysctl completion alias r=rollback

# Use aliases
sysctl d[TAB]  # Expands to 'deploy'
sysctl d api --env prod[TAB]  # Completes as deploy command
```

## Interactive Features

### Help During Completion

```bash
# Show help for options (zsh with descriptions)
sysctl deploy api --[TAB]
--env            -- Target environment for deployment
--image          -- Container image to deploy
--strategy       -- Deployment strategy (rolling, blue-green, canary)
--replicas       -- Number of replicas to deploy
--timeout        -- Maximum time to wait for deployment
```

### Preview Mode

```bash
# Preview command effect (fish shell)
sysctl deploy api --env production [TAB]
# Shows preview: "Will deploy api:latest to production environment"
```

### Completion History

```bash
# Recent completions (with fzf integration)
sysctl [CTRL+R]
# Shows searchable history of recent commands

# Frequently used completions
sysctl deploy api --env [TAB]
# Shows frequently used environments first
```

## Advanced Shell Integration

### Bash Advanced Features

```bash
# .bashrc additions for enhanced completion
# Enable programmable completion
shopt -s progcomp

# Custom completion function
_sysctl_custom() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    # Custom logic here
    if [[ "$prev" == "--env" ]]; then
        # Get environments from config
        opts=$(sysctl environments list --format simple 2>/dev/null)
        COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
    fi
}

# Register custom completion
complete -F _sysctl_custom sysctl
```

### Zsh Advanced Features

```zsh
# .zshrc additions for enhanced completion
# Enable menu selection
zstyle ':completion:*:sysctl:*' menu select

# Group completions by category
zstyle ':completion:*:sysctl:*' group-name ''
zstyle ':completion:*:sysctl:*:descriptions' format '%B%d%b'

# Cache completions
zstyle ':completion:*:sysctl:*' use-cache on
zstyle ':completion:*:sysctl:*' cache-path ~/.zsh/cache

# Fuzzy matching
zstyle ':completion:*:sysctl:*' matcher-list 'm:{a-z}={A-Z}' 'r:|[._-]=* r:|=*' 'l:|=* r:|=*'
```

### Fish Advanced Features

```fish
# config.fish additions
# Abbreviations for common commands
abbr -a sd 'sysctl deploy'
abbr -a ss 'sysctl status'
abbr -a sr 'sysctl rollback'

# Custom completion function
function __fish_sysctl_environments
    sysctl environments list --format simple 2>/dev/null
end

# Register completion
complete -c sysctl -n "__fish_seen_subcommand_from deploy" \
         -l env -d "Environment" \
         -a "(__fish_sysctl_environments)"
```

## Troubleshooting

### Debug Completion

```bash
# Test completion generation
sysctl completion debug --shell bash

# Verbose completion output
export SYSCTL_COMPLETION_DEBUG=1
sysctl deploy [TAB]

# Check completion installation
sysctl completion check

# Reinstall completions
sysctl completion install --force
```

### Common Issues

```bash
# Completions not working
# 1. Check if completion is sourced
type _sysctl  # Bash
which _sysctl  # Zsh

# 2. Reload shell configuration
source ~/.bashrc  # or ~/.zshrc

# 3. Check completion paths
echo $BASH_COMPLETION_USER_DIR  # Bash
echo $fpath  # Zsh

# Slow completions
# Enable caching
sysctl config set completion.cache.enabled true

# Reduce dynamic completion timeout
sysctl config set completion.dynamic.timeout 1
```

## Performance Optimization

### Caching Strategy

```yaml
# Completion cache configuration
cache:
  strategies:
    static_commands:
      ttl: 3600 # 1 hour

    dynamic_services:
      ttl: 60 # 1 minute

    file_paths:
      ttl: 10 # 10 seconds

    git_refs:
      ttl: 300 # 5 minutes

  preload:
    - commands
    - common_options
    - environments
```

### Async Completion

```python
# Async completion provider
import asyncio
from typing import List

class AsyncCompletionProvider:
    async def get_completions_async(self, prefix: str) -> List[str]:
        """Fetch completions asynchronously."""
        tasks = [
            self.fetch_services(prefix),
            self.fetch_environments(prefix),
            self.fetch_recent_history(prefix)
        ]

        results = await asyncio.gather(*tasks)
        return self.merge_results(results)
```

## Best Practices

### Completion Design

1. **Fast Response**: Keep completion under 100ms
2. **Relevant Suggestions**: Limit to 10-20 most relevant items
3. **Clear Descriptions**: Add help text for complex options
4. **Smart Defaults**: Suggest common values first
5. **Error Prevention**: Validate input during completion

### User Experience

```yaml
best_practices:
  performance:
    - cache_static_completions
    - async_dynamic_lookups
    - limit_result_count

  usability:
    - provide_descriptions
    - group_related_options
    - support_fuzzy_matching

  maintenance:
    - version_completion_scripts
    - test_completion_logic
    - document_custom_completions
```

### Security Considerations

```bash
# Avoid exposing sensitive data in completions
# Bad: Complete with actual passwords
sysctl secret set --value [TAB]  # Should NOT show secrets

# Good: Complete with secret names only
sysctl secret get [TAB]
database_password  api_key  jwt_secret  # Names only

# Mask sensitive completions
export SYSCTL_COMPLETION_MASK_SECRETS=1
```
