# Basic Usage Examples

Step-by-step examples demonstrating fundamental operations and workflows
for system control management.

## Getting Started

### Initial Setup

```bash
# Initialize system control in your project
cd /path/to/your/project
sysctl init

# Configure basic settings
sysctl config set project_name "my-distributed-system"
sysctl config set default_environment "development"
sysctl config set log_level "info"

# Verify configuration
sysctl config list
```

### Environment Configuration

```bash
# Create environment profiles
sysctl env create development
sysctl env create staging
sysctl env create production

# Configure development environment
sysctl config set --env development database.host "localhost"
sysctl config set --env development database.port "5432"
sysctl config set --env development replicas.default 1

# Configure production environment
sysctl config set --env production database.host "prod-db.company.com"
sysctl config set --env production database.port "5432"
sysctl config set --env production replicas.default 3
```

## Service Management

### Defining Services

```yaml
# config/services.yaml
services:
  api:
    image: "myapp/api:latest"
    ports:
      - "8080:8080"
    environment:
      DATABASE_URL: "${DATABASE_URL}"
      REDIS_URL: "${REDIS_URL}"
    health_check:
      endpoint: "/health"
      interval: 30

  worker:
    image: "myapp/worker:latest"
    environment:
      QUEUE_URL: "${QUEUE_URL}"
    replicas: 2

  database:
    image: "postgres:13"
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: "myapp"
      POSTGRES_USER: "myapp"
      POSTGRES_PASSWORD: "${DB_PASSWORD}"
    volumes:
      - "db_data:/var/lib/postgresql/data"
```

### Basic Service Operations

```bash
# Deploy a single service
sysctl deploy api

# Deploy with specific image
sysctl deploy api --image myapp/api:v1.2.0

# Deploy to specific environment
sysctl deploy api --env production

# Check service status
sysctl status api

# View service logs
sysctl logs api --tail 50 --follow

# Scale service
sysctl scale api --replicas 3

# Stop service
sysctl stop api

# Restart service
sysctl restart api
```

### System-Wide Operations

```bash
# Deploy all services
sysctl deploy --all

# Check system status
sysctl status

# Deploy specific services
sysctl deploy api worker --env production

# Stop all services
sysctl stop --all

# System health check
sysctl health-check --verbose
```

## Configuration Management

### Working with Secrets

```bash
# Set a secret
sysctl secret set DATABASE_PASSWORD --prompt
Enter secret value: ********

# Set secret from file
sysctl secret set API_KEY --from-file api-key.txt

# List secrets (names only)
sysctl secret list

# Use secrets in configuration
sysctl config set database.password "secret://DATABASE_PASSWORD"
```

### Configuration Profiles

```yaml
# config/profiles/development.yaml
profile: development
replicas:
  default: 1
  api: 2
logging:
  level: debug
features:
  debug_mode: true
  hot_reload: true
```

```yaml
# config/profiles/production.yaml
profile: production
replicas:
  default: 3
  api: 5
  worker: 10
logging:
  level: info
features:
  debug_mode: false
  hot_reload: false
security:
  ssl_required: true
  rate_limiting: true
```

```bash
# Apply profile
sysctl profile apply development

# Switch between profiles
sysctl profile switch production

# List available profiles
sysctl profile list
```

## Deployment Strategies

### Rolling Updates

```bash
# Rolling update with default settings
sysctl deploy api --strategy rolling

# Rolling update with custom settings
sysctl deploy api --strategy rolling \
  --max-unavailable 25% \
  --max-surge 1 \
  --timeout 600

# Monitor rolling update
sysctl deploy status api --follow
```

### Blue-Green Deployment

```bash
# Start blue-green deployment
sysctl deploy api --strategy blue-green --image myapp/api:v2.0.0

# Check deployment status
sysctl deploy status api

# Switch traffic to green environment
sysctl deploy promote api

# Rollback if needed
sysctl rollback api
```

### Canary Deployment

```bash
# Deploy canary with 10% traffic
sysctl deploy api --strategy canary \
  --percentage 10 \
  --image myapp/api:v2.0.0

# Gradually increase traffic
sysctl deploy canary-update api --percentage 25
sysctl deploy canary-update api --percentage 50
sysctl deploy canary-update api --percentage 100

# Finalize canary deployment
sysctl deploy finalize api
```

## Monitoring and Observability

### Basic Monitoring

```bash
# View real-time metrics
sysctl metrics api --real-time

# Get specific metrics
sysctl metrics api --metric cpu_usage --period 1h

# System overview dashboard
sysctl dashboard --service api --duration 6h

# Generate monitoring report
sysctl monitor report --services api,worker --format pdf
```

### Health Checks

```bash
# Manual health check
sysctl health-check api

# Health check all services
sysctl health-check --all

# Continuous health monitoring
sysctl health-check --monitor --interval 60

# Health check with custom endpoint
sysctl health-check api --endpoint /api/health --timeout 10
```

### Log Management

```bash
# View recent logs
sysctl logs api

# Follow logs in real-time
sysctl logs api --follow

# Filter logs by level
sysctl logs api --level error --since 2h

# Search logs
sysctl logs api --grep "database connection"

# Export logs
sysctl logs api --since 24h --output logs.txt
```

## Backup and Restore

### Database Backups

```bash
# Create database backup
sysctl backup create database --name daily-backup-$(date +%Y%m%d)

# List available backups
sysctl backup list database

# Restore from backup
sysctl backup restore database --backup daily-backup-20240115

# Schedule automatic backups
sysctl backup schedule database --cron "0 2 * * *" --retain 30
```

### Configuration Backups

```bash
# Backup current configuration
sysctl config backup --name pre-deployment-backup

# List configuration backups
sysctl config backup list

# Restore configuration
sysctl config restore pre-deployment-backup

# Compare configurations
sysctl config diff current pre-deployment-backup
```

## Environment Management

### Development Workflow

```bash
# Set up development environment
sysctl env setup development
sysctl profile apply development
sysctl deploy --all --env development

# Make configuration changes
sysctl config set api.debug_mode true
sysctl config set logging.level debug

# Test changes
sysctl deploy api --env development
sysctl health-check api --env development

# View development logs
sysctl logs api --env development --level debug
```

### Staging Deployment

```bash
# Promote to staging
sysctl env promote development staging

# Deploy to staging with validation
sysctl deploy --all --env staging --validate

# Run staging tests
sysctl test smoke --env staging

# Monitor staging deployment
sysctl status --env staging --monitor
```

### Production Deployment

```bash
# Pre-production checklist
sysctl deploy validate --env production --check-requirements

# Deploy to production with approval
sysctl deploy --all --env production --require-approval

# Monitor production deployment
sysctl status --env production --alerts

# Verify production health
sysctl health-check --all --env production
```

## Troubleshooting

### Common Issues

```bash
# Service won't start
sysctl diagnose api
sysctl logs api --level error --since 30m

# Performance issues
sysctl metrics api --metric cpu,memory --period 1h
sysctl profile performance api

# Connectivity problems
sysctl network test api database
sysctl network trace api --external

# Configuration issues
sysctl config validate --env production
sysctl config debug api
```

### Service Recovery

```bash
# Restart failed service
sysctl restart api --force

# Rollback to previous version
sysctl rollback api --to-previous

# Emergency recovery
sysctl emergency-mode enable
sysctl deploy api --image myapp/api:last-known-good --force

# Restore from backup
sysctl backup restore system --backup emergency-backup
```

## Interactive Mode

### Using the REPL

```bash
# Start interactive mode
sysctl interactive

# Interactive session example
>>> status api
Service: api
Status: running
Health: healthy
Replicas: 3/3

>>> deploy worker --image myapp/worker:v1.1.0
Deploying worker with image myapp/worker:v1.1.0...
Deployment completed successfully.

>>> metrics api --metric cpu_usage
CPU Usage (api): 45.2%

>>> exit
```

### Command History

```bash
# View command history
sysctl history

# Repeat previous command
sysctl history repeat 5

# Search command history
sysctl history search "deploy api"

# Export command history
sysctl history export --since 7d --output commands.log
```

## Automation Examples

### Simple Deployment Script

```bash
#!/bin/bash
# deploy.sh - Simple deployment script

set -e

echo "Starting deployment to $1 environment..."

# Validate environment
sysctl config validate --env $1

# Create backup
sysctl backup create system --name "pre-deploy-$(date +%Y%m%d-%H%M)"

# Deploy services
sysctl deploy api --env $1 --image $2
sysctl deploy worker --env $1

# Health check
sysctl health-check --all --env $1

# Monitor for 5 minutes
timeout 300 sysctl status --env $1 --monitor --interval 30

echo "Deployment completed successfully!"
```

### Configuration Update Script

```bash
#!/bin/bash
# update-config.sh - Update configuration across environments

CONFIG_FILE=$1
ENVIRONMENTS="development staging production"

for env in $ENVIRONMENTS; do
    echo "Updating configuration for $env..."

    # Backup current config
    sysctl config backup --env $env --name "pre-update-$(date +%Y%m%d)"

    # Apply new configuration
    sysctl config apply --env $env --file $CONFIG_FILE

    # Validate configuration
    if sysctl config validate --env $env; then
        echo "Configuration updated successfully for $env"

        # Restart affected services if needed
        sysctl restart api worker --env $env

    else
        echo "Configuration validation failed for $env"

        # Rollback configuration
        sysctl config restore "pre-update-$(date +%Y%m%d)" --env $env
        exit 1
    fi
done
```

### Health Monitoring Script

```bash
#!/bin/bash
# monitor.sh - Continuous health monitoring

SERVICES="api worker database redis"
LOG_FILE="/var/log/system-control-monitor.log"

while true; do
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    for service in $SERVICES; do
        if sysctl health-check $service --quiet; then
            echo "$timestamp - $service: OK" >> $LOG_FILE
        else
            echo "$timestamp - $service: FAILED" >> $LOG_FILE

            # Send alert
            sysctl alert send "Service $service health check failed" \
                --severity critical \
                --channel slack

            # Attempt restart
            sysctl restart $service
        fi
    done

    sleep 60
done
```

## Best Practices

### Configuration Management Best Practices

1. **Use Profiles**: Organize settings by environment using profiles
2. **Secure Secrets**: Never store secrets in plain text, use the secret management system
3. **Validate Changes**: Always validate configuration before applying to production
4. **Version Control**: Keep configuration files in version control
5. **Documentation**: Document configuration changes and their purpose

### Deployment Best Practices

1. **Gradual Rollouts**: Use canary or blue-green deployments for production
2. **Health Checks**: Always verify service health after deployment
3. **Monitoring**: Monitor key metrics during and after deployment
4. **Rollback Plan**: Have a rollback strategy ready for every deployment
5. **Testing**: Test deployments in non-production environments first

### Monitoring and Alerting

1. **Set Baselines**: Establish normal operating ranges for key metrics
2. **Alert Fatigue**: Configure alerts thoughtfully to avoid noise
3. **Response Procedures**: Document response procedures for common alerts
4. **Regular Reviews**: Regularly review and update monitoring configurations
5. **Incident Learning**: Learn from incidents to improve monitoring

### Security Practices

1. **Principle of Least Privilege**: Grant minimal necessary permissions
2. **Regular Updates**: Keep system and dependencies updated
3. **Secret Rotation**: Regularly rotate secrets and credentials
4. **Access Logging**: Log and monitor administrative actions
5. **Security Scanning**: Regularly scan for vulnerabilities
