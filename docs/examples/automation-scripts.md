# Automation Scripts

Production-ready automation scripts for common system administration tasks, deployment workflows,
and operational procedures.

## Deployment Automation

### Complete Deployment Pipeline

```bash
#!/bin/bash
# deploy-pipeline.sh - Complete deployment pipeline with validation and rollback
set -euo pipefail

# Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly CONFIG_FILE="${SCRIPT_DIR}/deploy-config.yaml"
readonly LOG_FILE="/var/log/deployment-$(date +%Y%m%d-%H%M%S).log"

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

info() {
    log "${BLUE}[INFO]${NC} $*"
}

success() {
    log "${GREEN}[SUCCESS]${NC} $*"
}

warning() {
    log "${YELLOW}[WARNING]${NC} $*"
}

error() {
    log "${RED}[ERROR]${NC} $*"
}

# Error handling
cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        error "Deployment failed with exit code $exit_code"
        rollback_deployment
    fi
    exit $exit_code
}

trap cleanup EXIT

# Configuration validation
validate_config() {
    info "Validating configuration..."

    # Check required environment variables
    local required_vars=("ENVIRONMENT" "VERSION" "SERVICES")
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            error "Required environment variable $var is not set"
            return 1
        fi
    done

    # Validate environment
    if ! sysctl env exists "$ENVIRONMENT"; then
        error "Environment $ENVIRONMENT does not exist"
        return 1
    fi

    # Validate services
    IFS=',' read -ra SERVICE_ARRAY <<< "$SERVICES"
    for service in "${SERVICE_ARRAY[@]}"; do
        if ! sysctl service exists "$service"; then
            error "Service $service does not exist"
            return 1
        fi
    done

    success "Configuration validation passed"
}

# Pre-deployment checks
pre_deployment_checks() {
    info "Running pre-deployment checks..."

    # Check system resources
    if ! sysctl resources check --env "$ENVIRONMENT" --required-for-deployment; then
        error "Insufficient resources for deployment"
        return 1
    fi

    # Check maintenance window (for production)
    if [ "$ENVIRONMENT" = "production" ]; then
        if ! sysctl maintenance-window check; then
            error "Not in approved maintenance window"
            return 1
        fi
    fi

    # Validate configuration files
    if ! sysctl config validate --env "$ENVIRONMENT"; then
        error "Configuration validation failed"
        return 1
    fi

    # Check external dependencies
    if ! sysctl dependencies check --external --env "$ENVIRONMENT"; then
        warning "Some external dependencies are unavailable"
        if [ "$ENVIRONMENT" = "production" ]; then
            error "Cannot deploy to production with unavailable dependencies"
            return 1
        fi
    fi

    success "Pre-deployment checks passed"
}

# Create backup
create_backup() {
    info "Creating system backup..."

    local backup_name="pre-deploy-$(date +%Y%m%d-%H%M%S)"

    # Database backup
    if ! sysctl backup create database --name "$backup_name" --env "$ENVIRONMENT"; then
        error "Database backup failed"
        return 1
    fi

    # Configuration backup
    if ! sysctl config backup --name "$backup_name" --env "$ENVIRONMENT"; then
        error "Configuration backup failed"
        return 1
    fi

    # State snapshot
    if ! sysctl snapshot create --name "$backup_name" --env "$ENVIRONMENT"; then
        error "State snapshot failed"
        return 1
    fi

    # Store backup name for rollback
    echo "$backup_name" > "${SCRIPT_DIR}/.last_backup"

    success "Backup created: $backup_name"
}

# Deploy services
deploy_services() {
    info "Starting deployment of services: $SERVICES"

    local deployment_strategy="${DEPLOYMENT_STRATEGY:-rolling}"
    local timeout="${DEPLOYMENT_TIMEOUT:-600}"

    # Deploy each service
    IFS=',' read -ra SERVICE_ARRAY <<< "$SERVICES"
    for service in "${SERVICE_ARRAY[@]}"; do
        info "Deploying service: $service"

        if ! sysctl deploy "$service" \
            --env "$ENVIRONMENT" \
            --image-tag "$VERSION" \
            --strategy "$deployment_strategy" \
            --timeout "$timeout"; then
            error "Failed to deploy service: $service"
            return 1
        fi

        # Wait for service to be healthy
        if ! sysctl health-check "$service" --env "$ENVIRONMENT" --wait --timeout 300; then
            error "Service $service failed health check"
            return 1
        fi

        success "Successfully deployed service: $service"
    done

    success "All services deployed successfully"
}

# Post-deployment validation
post_deployment_validation() {
    info "Running post-deployment validation..."

    # Health checks
    if ! sysctl health-check --all --env "$ENVIRONMENT" --timeout 300; then
        error "Post-deployment health checks failed"
        return 1
    fi

    # Smoke tests
    if ! sysctl test smoke --env "$ENVIRONMENT" --timeout 600; then
        error "Smoke tests failed"
        return 1
    fi

    # Performance validation (for production)
    if [ "$ENVIRONMENT" = "production" ]; then
        if ! sysctl test performance --baseline --env "$ENVIRONMENT" --timeout 900; then
            warning "Performance tests failed, but deployment continues"
        fi
    fi

    # Integration tests
    if ! sysctl test integration --env "$ENVIRONMENT" --timeout 1200; then
        error "Integration tests failed"
        return 1
    fi

    success "Post-deployment validation passed"
}

# Rollback deployment
rollback_deployment() {
    if [ ! -f "${SCRIPT_DIR}/.last_backup" ]; then
        error "No backup information found, cannot rollback"
        return 1
    fi

    local backup_name
    backup_name=$(cat "${SCRIPT_DIR}/.last_backup")

    error "Rolling back deployment using backup: $backup_name"

    # Rollback services
    IFS=',' read -ra SERVICE_ARRAY <<< "$SERVICES"
    for service in "${SERVICE_ARRAY[@]}"; do
        warning "Rolling back service: $service"
        sysctl rollback "$service" --env "$ENVIRONMENT" --to-snapshot "$backup_name" || true
    done

    # Restore database if needed
    if [ "$ROLLBACK_DATABASE" = "true" ]; then
        warning "Restoring database from backup"
        sysctl backup restore database --backup "$backup_name" --env "$ENVIRONMENT" || true
    fi

    # Restore configuration
    warning "Restoring configuration from backup"
    sysctl config restore "$backup_name" --env "$ENVIRONMENT" || true

    error "Rollback completed"
}

# Notification functions
send_notification() {
    local status="$1"
    local message="$2"

    # Send to Slack
    if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$status: $message\"}" \
            "$SLACK_WEBHOOK_URL" || true
    fi

    # Send to email
    if [ -n "${NOTIFICATION_EMAIL:-}" ]; then
        echo "$message" | mail -s "$status: Deployment $ENVIRONMENT" "$NOTIFICATION_EMAIL" || true
    fi

    # Create incident if deployment failed
    if [ "$status" = "FAILED" ] && [ "$ENVIRONMENT" = "production" ]; then
        sysctl incident create "Production deployment failed" \
            --severity high \
            --description "$message" \
            --assignee oncall || true
    fi
}

# Main deployment function
main() {
    info "Starting deployment pipeline"
    info "Environment: $ENVIRONMENT"
    info "Version: $VERSION"
    info "Services: $SERVICES"

    # Validate configuration
    validate_config

    # Pre-deployment checks
    pre_deployment_checks

    # Create backup
    create_backup

    # Deploy services
    deploy_services

    # Post-deployment validation
    post_deployment_validation

    # Cleanup
    rm -f "${SCRIPT_DIR}/.last_backup"

    success "Deployment completed successfully!"
    send_notification "SUCCESS" "Deployment to $ENVIRONMENT completed successfully. Version: $VERSION"
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Check dependencies
    command -v sysctl >/dev/null 2>&1 || { error "sysctl command not found"; exit 1; }

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --env)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --version)
                VERSION="$2"
                shift 2
                ;;
            --services)
                SERVICES="$2"
                shift 2
                ;;
            --strategy)
                DEPLOYMENT_STRATEGY="$2"
                shift 2
                ;;
            --rollback-db)
                ROLLBACK_DATABASE="true"
                shift
                ;;
            --help)
                echo "Usage: $0 --env ENVIRONMENT --version VERSION --services SERVICES [OPTIONS]"
                echo "Options:"
                echo "  --env ENVIRONMENT          Target environment"
                echo "  --version VERSION          Version to deploy"
                echo "  --services SERVICES        Comma-separated list of services"
                echo "  --strategy STRATEGY        Deployment strategy (rolling, blue-green, canary)"
                echo "  --rollback-db             Enable database rollback on failure"
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Validate required parameters
    if [ -z "${ENVIRONMENT:-}" ] || [ -z "${VERSION:-}" ] || [ -z "${SERVICES:-}" ]; then
        error "Missing required parameters. Use --help for usage information."
        exit 1
    fi

    # Run main function
    main
fi
```

### Blue-Green Deployment Script

```bash
#!/bin/bash
# blue-green-deploy.sh - Blue-green deployment automation
set -euo pipefail

readonly ENVIRONMENT="${1:-production}"
readonly VERSION="${2:-latest}"
readonly SERVICE="${3:-api}"

# Configuration
readonly BLUE_ENV="${ENVIRONMENT}-blue"
readonly GREEN_ENV="${ENVIRONMENT}-green"
readonly CURRENT_ENV_FILE="/tmp/current-${ENVIRONMENT}-env"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

get_current_environment() {
    if [ -f "$CURRENT_ENV_FILE" ]; then
        cat "$CURRENT_ENV_FILE"
    else
        echo "$BLUE_ENV"  # Default to blue
    fi
}

get_inactive_environment() {
    local current
    current=$(get_current_environment)
    if [ "$current" = "$BLUE_ENV" ]; then
        echo "$GREEN_ENV"
    else
        echo "$BLUE_ENV"
    fi
}

deploy_to_inactive() {
    local inactive_env
    inactive_env=$(get_inactive_environment)

    log "Deploying $SERVICE version $VERSION to inactive environment: $inactive_env"

    # Deploy to inactive environment
    sysctl deploy "$SERVICE" \
        --env "$inactive_env" \
        --image-tag "$VERSION" \
        --strategy rolling \
        --timeout 600

    # Wait for service to be healthy
    sysctl health-check "$SERVICE" \
        --env "$inactive_env" \
        --wait \
        --timeout 300

    # Warm up the service
    sysctl service warm-up "$SERVICE" \
        --env "$inactive_env" \
        --duration 120

    log "Service deployed and healthy in $inactive_env"
}

validate_inactive_environment() {
    local inactive_env
    inactive_env=$(get_inactive_environment)

    log "Validating inactive environment: $inactive_env"

    # Run smoke tests
    if ! sysctl test smoke --env "$inactive_env" --timeout 300; then
        log "Smoke tests failed in $inactive_env"
        return 1
    fi

    # Run health checks
    if ! sysctl health-check --all --env "$inactive_env" --timeout 180; then
        log "Health checks failed in $inactive_env"
        return 1
    fi

    # Performance check
    if ! sysctl test performance --env "$inactive_env" --quick; then
        log "Performance check failed in $inactive_env"
        return 1
    fi

    log "Validation passed for $inactive_env"
}

switch_traffic() {
    local current_env inactive_env
    current_env=$(get_current_environment)
    inactive_env=$(get_inactive_environment)

    log "Switching traffic from $current_env to $inactive_env"

    # Switch load balancer to point to inactive environment
    sysctl traffic switch \
        --from "$current_env" \
        --to "$inactive_env" \
        --service "$SERVICE"

    # Verify traffic is flowing correctly
    sleep 30
    if ! sysctl traffic verify --env "$inactive_env" --duration 60; then
        log "Traffic verification failed, switching back"
        sysctl traffic switch --from "$inactive_env" --to "$current_env" --service "$SERVICE"
        return 1
    fi

    # Update current environment marker
    echo "$inactive_env" > "$CURRENT_ENV_FILE"

    log "Traffic switched successfully to $inactive_env"
}

cleanup_old_environment() {
    local old_env

    # The old environment is now the inactive one after the switch
    old_env=$(get_inactive_environment)

    log "Cleaning up old environment: $old_env"

    # Scale down old environment (but don't destroy completely for rollback)
    sysctl scale "$SERVICE" --env "$old_env" --replicas 1

    log "Old environment $old_env scaled down"
}

rollback() {
    local current_env inactive_env
    current_env=$(get_current_environment)
    inactive_env=$(get_inactive_environment)

    log "Rolling back from $current_env to $inactive_env"

    # Switch traffic back
    sysctl traffic switch \
        --from "$current_env" \
        --to "$inactive_env" \
        --service "$SERVICE"

    # Scale up the old environment
    sysctl scale "$SERVICE" --env "$inactive_env" --replicas auto

    # Update current environment marker
    echo "$inactive_env" > "$CURRENT_ENV_FILE"

    log "Rollback completed"
}

main() {
    log "Starting blue-green deployment"
    log "Environment: $ENVIRONMENT"
    log "Service: $SERVICE"
    log "Version: $VERSION"

    current_env=$(get_current_environment)
    inactive_env=$(get_inactive_environment)

    log "Current active environment: $current_env"
    log "Deploying to inactive environment: $inactive_env"

    # Deploy to inactive environment
    if ! deploy_to_inactive; then
        log "Deployment to inactive environment failed"
        exit 1
    fi

    # Validate inactive environment
    if ! validate_inactive_environment; then
        log "Validation of inactive environment failed"
        exit 1
    fi

    # Switch traffic
    if ! switch_traffic; then
        log "Traffic switch failed"
        exit 1
    fi

    # Cleanup old environment
    cleanup_old_environment

    log "Blue-green deployment completed successfully!"
}

# Rollback function (can be called separately)
if [ "${1:-}" = "rollback" ]; then
    rollback
    exit 0
fi

main
```

## Monitoring and Alerting Automation

### Comprehensive Health Check Script

```bash
#!/bin/bash
# health-monitor.sh - Comprehensive system health monitoring
set -euo pipefail

readonly CONFIG_FILE="/etc/sysctl/health-config.yaml"
readonly STATE_FILE="/var/lib/sysctl/health-state.json"
readonly LOG_FILE="/var/log/sysctl-health.log"

# Load configuration
load_config() {
    if [ -f "$CONFIG_FILE" ]; then
        # Parse YAML config (simplified)
        ENVIRONMENTS=$(sysctl config get monitoring.environments)
        SERVICES=$(sysctl config get monitoring.services)
        CHECK_INTERVAL=$(sysctl config get monitoring.check_interval || echo "60")
        ALERT_CHANNELS=$(sysctl config get monitoring.alert_channels)
    else
        # Default configuration
        ENVIRONMENTS="production,staging"
        SERVICES="api,worker,database,redis"
        CHECK_INTERVAL="60"
        ALERT_CHANNELS="slack,email"
    fi
}

# Logging function
log_event() {
    local level="$1"
    local message="$2"
    local timestamp
    timestamp=$(date -Iseconds)

    echo "{\"timestamp\":\"$timestamp\",\"level\":\"$level\",\"message\":\"$message\"}" >> "$LOG_FILE"

    # Also log to console if running interactively
    if [ -t 1 ]; then
        echo "[$timestamp] [$level] $message"
    fi
}

# Health check functions
check_service_health() {
    local service="$1"
    local environment="$2"

    if sysctl health-check "$service" --env "$environment" --quiet; then
        return 0
    else
        return 1
    fi
}

check_system_resources() {
    local environment="$1"

    # Check CPU usage
    local cpu_usage
    cpu_usage=$(sysctl metrics get cpu_usage --env "$environment" --avg)
    if (( $(echo "$cpu_usage > 90" | bc -l) )); then
        log_event "WARNING" "High CPU usage in $environment: $cpu_usage%"
        return 1
    fi

    # Check memory usage
    local memory_usage
    memory_usage=$(sysctl metrics get memory_usage --env "$environment" --avg)
    if (( $(echo "$memory_usage > 85" | bc -l) )); then
        log_event "WARNING" "High memory usage in $environment: $memory_usage%"
        return 1
    fi

    # Check disk space
    local disk_usage
    disk_usage=$(sysctl metrics get disk_usage --env "$environment" --avg)
    if (( $(echo "$disk_usage > 80" | bc -l) )); then
        log_event "WARNING" "High disk usage in $environment: $disk_usage%"
        return 1
    fi

    return 0
}

check_network_connectivity() {
    local environment="$1"

    # Check internal connectivity
    if ! sysctl network test --internal --env "$environment" --quiet; then
        log_event "ERROR" "Internal network connectivity failed in $environment"
        return 1
    fi

    # Check external dependencies
    if ! sysctl network test --external --env "$environment" --quiet; then
        log_event "WARNING" "External network connectivity issues in $environment"
        return 1
    fi

    return 0
}

check_database_health() {
    local environment="$1"

    # Connection test
    if ! sysctl database ping --env "$environment" --quiet; then
        log_event "ERROR" "Database connection failed in $environment"
        return 1
    fi

    # Performance check
    local query_time
    query_time=$(sysctl database performance --env "$environment" --metric avg_query_time)
    if (( $(echo "$query_time > 100" | bc -l) )); then
        log_event "WARNING" "Slow database queries in $environment: ${query_time}ms average"
        return 1
    fi

    # Connection pool check
    local active_connections
    active_connections=$(sysctl database connections --env "$environment" --count)
    local max_connections
    max_connections=$(sysctl database connections --env "$environment" --max)

    if (( active_connections > max_connections * 80 / 100 )); then
        log_event "WARNING" "High database connection usage in $environment: $active_connections/$max_connections"
        return 1
    fi

    return 0
}

# Alert functions
send_alert() {
    local severity="$1"
    local message="$2"
    local environment="$3"

    log_event "$severity" "$message"

    # Send to configured channels
    IFS=',' read -ra CHANNELS <<< "$ALERT_CHANNELS"
    for channel in "${CHANNELS[@]}"; do
        case "$channel" in
            "slack")
                send_slack_alert "$severity" "$message" "$environment"
                ;;
            "email")
                send_email_alert "$severity" "$message" "$environment"
                ;;
            "pagerduty")
                send_pagerduty_alert "$severity" "$message" "$environment"
                ;;
        esac
    done
}

send_slack_alert() {
    local severity="$1"
    local message="$2"
    local environment="$3"

    local webhook_url
    webhook_url=$(sysctl config get alerts.slack.webhook_url)

    if [ -n "$webhook_url" ]; then
        local color="danger"
        case "$severity" in
            "INFO") color="good" ;;
            "WARNING") color="warning" ;;
            "ERROR"|"CRITICAL") color="danger" ;;
        esac

        curl -X POST -H 'Content-type: application/json' \
            --data "{
                \"attachments\": [{
                    \"color\": \"$color\",
                    \"title\": \"Health Check Alert - $environment\",
                    \"text\": \"$message\",
                    \"fields\": [{
                        \"title\": \"Environment\",
                        \"value\": \"$environment\",
                        \"short\": true
                    }, {
                        \"title\": \"Severity\",
                        \"value\": \"$severity\",
                        \"short\": true
                    }],
                    \"timestamp\": $(date +%s)
                }]
            }" \
            "$webhook_url" > /dev/null 2>&1 || true
    fi
}

send_email_alert() {
    local severity="$1"
    local message="$2"
    local environment="$3"

    local email_recipients
    email_recipients=$(sysctl config get alerts.email.recipients)

    if [ -n "$email_recipients" ]; then
        {
            echo "Subject: [$severity] Health Check Alert - $environment"
            echo "From: sysctl-monitor@company.com"
            echo "To: $email_recipients"
            echo ""
            echo "Environment: $environment"
            echo "Severity: $severity"
            echo "Time: $(date)"
            echo ""
            echo "Message:"
            echo "$message"
            echo ""
            echo "---"
            echo "System Control Health Monitor"
        } | sendmail "$email_recipients" 2>/dev/null || true
    fi
}

send_pagerduty_alert() {
    local severity="$1"
    local message="$2"
    local environment="$3"

    # Only send to PagerDuty for critical issues in production
    if [ "$environment" = "production" ] && [ "$severity" = "CRITICAL" ]; then
        local routing_key
        routing_key=$(sysctl config get alerts.pagerduty.routing_key)

        if [ -n "$routing_key" ]; then
            curl -X POST \
                -H 'Content-Type: application/json' \
                -d "{
                    \"routing_key\": \"$routing_key\",
                    \"event_action\": \"trigger\",
                    \"payload\": {
                        \"summary\": \"Health Check Alert - $environment\",
                        \"severity\": \"critical\",
                        \"source\": \"sysctl-health-monitor\",
                        \"component\": \"$environment\",
                        \"custom_details\": {
                            \"message\": \"$message\",
                            \"environment\": \"$environment\"
                        }
                    }
                }" \
                'https://events.pagerduty.com/v2/enqueue' > /dev/null 2>&1 || true
        fi
    fi
}

# State management
load_state() {
    if [ -f "$STATE_FILE" ]; then
        cat "$STATE_FILE"
    else
        echo "{}"
    fi
}

save_state() {
    local state="$1"
    echo "$state" > "$STATE_FILE"
}

update_service_state() {
    local service="$1"
    local environment="$2"
    local status="$3"

    local state
    state=$(load_state)

    # Update state (simplified JSON manipulation)
    local key="${environment}.${service}"
    state=$(echo "$state" | jq --arg key "$key" --arg status "$status" --arg timestamp "$(date -Iseconds)" \
        '.[$key] = {status: $status, last_check: $timestamp}')

    save_state "$state"
}

get_service_previous_state() {
    local service="$1"
    local environment="$2"

    local state
    state=$(load_state)
    local key="${environment}.${service}"

    echo "$state" | jq -r --arg key "$key" '.[$key].status // "unknown"'
}

# Main health check loop
run_health_checks() {
    local overall_health="healthy"

    IFS=',' read -ra ENV_ARRAY <<< "$ENVIRONMENTS"
    IFS=',' read -ra SERVICE_ARRAY <<< "$SERVICES"

    for environment in "${ENV_ARRAY[@]}"; do
        log_event "INFO" "Starting health checks for environment: $environment"

        # Check system resources
        if ! check_system_resources "$environment"; then
            overall_health="degraded"
        fi

        # Check network connectivity
        if ! check_network_connectivity "$environment"; then
            overall_health="degraded"
        fi

        # Check database health
        if ! check_database_health "$environment"; then
            overall_health="degraded"
        fi

        # Check individual services
        for service in "${SERVICE_ARRAY[@]}"; do
            local previous_state
            previous_state=$(get_service_previous_state "$service" "$environment")

            if check_service_health "$service" "$environment"; then
                update_service_state "$service" "$environment" "healthy"

                # Alert on recovery
                if [ "$previous_state" != "healthy" ] && [ "$previous_state" != "unknown" ]; then
                    send_alert "INFO" "Service $service in $environment has recovered" "$environment"
                fi
            else
                update_service_state "$service" "$environment" "unhealthy"
                overall_health="unhealthy"

                # Alert on failure (only if state changed)
                if [ "$previous_state" = "healthy" ] || [ "$previous_state" = "unknown" ]; then
                    local severity="ERROR"
                    if [ "$environment" = "production" ]; then
                        severity="CRITICAL"
                    fi
                    send_alert "$severity" "Service $service in $environment is unhealthy" "$environment"
                fi
            fi
        done

        log_event "INFO" "Completed health checks for environment: $environment"
    done

    return 0
}

# Generate health report
generate_health_report() {
    local state
    state=$(load_state)

    echo "# System Health Report"
    echo "Generated: $(date)"
    echo ""

    IFS=',' read -ra ENV_ARRAY <<< "$ENVIRONMENTS"
    for environment in "${ENV_ARRAY[@]}"; do
        echo "## Environment: $environment"
        echo ""

        IFS=',' read -ra SERVICE_ARRAY <<< "$SERVICES"
        for service in "${SERVICE_ARRAY[@]}"; do
            local key="${environment}.${service}"
            local status
            local last_check

            status=$(echo "$state" | jq -r --arg key "$key" '.[$key].status // "unknown"')
            last_check=$(echo "$state" | jq -r --arg key "$key" '.[$key].last_check // "never"')

            local status_icon="❓"
            case "$status" in
                "healthy") status_icon="✅" ;;
                "unhealthy") status_icon="❌" ;;
                "degraded") status_icon="⚠️" ;;
            esac

            echo "- $status_icon **$service**: $status (last check: $last_check)"
        done
        echo ""
    done
}

# Daemon mode
run_daemon() {
    log_event "INFO" "Starting health monitor daemon (interval: ${CHECK_INTERVAL}s)"

    while true; do
        run_health_checks
        sleep "$CHECK_INTERVAL"
    done
}

# Main function
main() {
    local command="${1:-check}"

    # Load configuration
    load_config

    # Ensure directories exist
    mkdir -p "$(dirname "$STATE_FILE")"
    mkdir -p "$(dirname "$LOG_FILE")"

    case "$command" in
        "check")
            run_health_checks
            ;;
        "daemon")
            run_daemon
            ;;
        "report")
            generate_health_report
            ;;
        "state")
            load_state | jq .
            ;;
        *)
            echo "Usage: $0 {check|daemon|report|state}"
            exit 1
            ;;
    esac
}

# Check dependencies
command -v sysctl >/dev/null 2>&1 || { echo "sysctl command not found"; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "jq command not found"; exit 1; }

main "$@"
```

### Automated Backup Script

```bash
#!/bin/bash
# backup-automation.sh - Comprehensive backup automation
set -euo pipefail

readonly CONFIG_FILE="/etc/sysctl/backup-config.yaml"
readonly LOG_FILE="/var/log/sysctl-backup.log"
readonly LOCK_FILE="/var/run/sysctl-backup.lock"

# Configuration defaults
ENVIRONMENTS="production,staging"
BACKUP_TYPES="database,config,files,state"
RETENTION_DAYS="30"
S3_BUCKET=""
ENCRYPTION_KEY_FILE=""
COMPRESSION="gzip"
NOTIFICATION_CHANNELS="slack,email"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

error() {
    log "ERROR: $*" >&2
}

info() {
    log "INFO: $*"
}

success() {
    log "SUCCESS: $*"
}

# Lock management
acquire_lock() {
    if [ -f "$LOCK_FILE" ]; then
        local pid
        pid=$(cat "$LOCK_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            error "Backup already running (PID: $pid)"
            exit 1
        else
            rm -f "$LOCK_FILE"
        fi
    fi

    echo $$ > "$LOCK_FILE"
    trap 'rm -f "$LOCK_FILE"; exit' EXIT INT TERM
}

# Load configuration
load_config() {
    if [ -f "$CONFIG_FILE" ]; then
        ENVIRONMENTS=$(sysctl config get backup.environments || echo "$ENVIRONMENTS")
        BACKUP_TYPES=$(sysctl config get backup.types || echo "$BACKUP_TYPES")
        RETENTION_DAYS=$(sysctl config get backup.retention_days || echo "$RETENTION_DAYS")
        S3_BUCKET=$(sysctl config get backup.s3_bucket || echo "$S3_BUCKET")
        ENCRYPTION_KEY_FILE=$(sysctl config get backup.encryption_key || echo "$ENCRYPTION_KEY_FILE")
        COMPRESSION=$(sysctl config get backup.compression || echo "$COMPRESSION")
    fi

    info "Backup configuration loaded"
    info "Environments: $ENVIRONMENTS"
    info "Types: $BACKUP_TYPES"
    info "Retention: $RETENTION_DAYS days"
}

# Backup functions
backup_database() {
    local environment="$1"
    local backup_name="$2"

    info "Creating database backup for $environment"

    if sysctl backup create database \
        --env "$environment" \
        --name "$backup_name" \
        --compress \
        --verify; then
        success "Database backup created: $backup_name"
        return 0
    else
        error "Database backup failed for $environment"
        return 1
    fi
}

backup_config() {
    local environment="$1"
    local backup_name="$2"

    info "Creating configuration backup for $environment"

    if sysctl config backup \
        --env "$environment" \
        --name "$backup_name" \
        --include-secrets; then
        success "Configuration backup created: $backup_name"
        return 0
    else
        error "Configuration backup failed for $environment"
        return 1
    fi
}

backup_files() {
    local environment="$1"
    local backup_name="$2"

    info "Creating file system backup for $environment"

    # Define important directories to backup
    local backup_dirs="/etc/sysctl /var/lib/sysctl /opt/application/data"

    local backup_file="/tmp/${backup_name}-files.tar.gz"

    if tar czf "$backup_file" $backup_dirs 2>/dev/null; then
        # Upload to storage
        if upload_backup "$backup_file" "files/$environment/$backup_name.tar.gz"; then
            success "File system backup created: $backup_name"
            rm -f "$backup_file"
            return 0
        fi
    fi

    error "File system backup failed for $environment"
    rm -f "$backup_file"
    return 1
}

backup_state() {
    local environment="$1"
    local backup_name="$2"

    info "Creating state snapshot for $environment"

    if sysctl snapshot create \
        --env "$environment" \
        --name "$backup_name" \
        --include-volumes; then
        success "State snapshot created: $backup_name"
        return 0
    else
        error "State snapshot failed for $environment"
        return 1
    fi
}

# Upload backup to storage
upload_backup() {
    local local_file="$1"
    local remote_path="$2"

    if [ -n "$S3_BUCKET" ]; then
        # Encrypt if key provided
        if [ -n "$ENCRYPTION_KEY_FILE" ] && [ -f "$ENCRYPTION_KEY_FILE" ]; then
            local encrypted_file="${local_file}.enc"
            if openssl enc -aes-256-cbc -salt -in "$local_file" -out "$encrypted_file" -pass file:"$ENCRYPTION_KEY_FILE"; then
                local_file="$encrypted_file"
            fi
        fi

        # Upload to S3
        if aws s3 cp "$local_file" "s3://${S3_BUCKET}/${remote_path}"; then
            info "Backup uploaded to s3://${S3_BUCKET}/${remote_path}"
            return 0
        else
            error "Failed to upload backup to S3"
            return 1
        fi
    else
        info "No S3 bucket configured, keeping backup locally"
        return 0
    fi
}

# Cleanup old backups
cleanup_old_backups() {
    local environment="$1"

    info "Cleaning up old backups for $environment (older than $RETENTION_DAYS days)"

    # Cleanup local backups
    sysctl backup cleanup \
        --env "$environment" \
        --older-than "${RETENTION_DAYS}d" \
        --confirm

    # Cleanup S3 backups if configured
    if [ -n "$S3_BUCKET" ]; then
        local cutoff_date
        cutoff_date=$(date -d "$RETENTION_DAYS days ago" '+%Y-%m-%d')

        aws s3 ls "s3://${S3_BUCKET}/" --recursive | while read -r line; do
            local file_date file_name
            file_date=$(echo "$line" | awk '{print $1}')
            file_name=$(echo "$line" | awk '{print $4}')

            if [[ "$file_date" < "$cutoff_date" ]]; then
                aws s3 rm "s3://${S3_BUCKET}/${file_name}"
                info "Deleted old backup: $file_name"
            fi
        done
    fi

    success "Cleanup completed for $environment"
}

# Verify backup integrity
verify_backups() {
    local environment="$1"
    local backup_name="$2"

    info "Verifying backup integrity for $backup_name"

    # Test database backup restore (to temporary location)
    if sysctl backup verify database \
        --backup "$backup_name" \
        --env "$environment" \
        --test-restore; then
        success "Database backup verified: $backup_name"
    else
        error "Database backup verification failed: $backup_name"
        return 1
    fi

    return 0
}

# Notification functions
send_notification() {
    local status="$1"
    local message="$2"

    IFS=',' read -ra CHANNELS <<< "$NOTIFICATION_CHANNELS"
    for channel in "${CHANNELS[@]}"; do
        case "$channel" in
            "slack")
                send_slack_notification "$status" "$message"
                ;;
            "email")
                send_email_notification "$status" "$message"
                ;;
        esac
    done
}

send_slack_notification() {
    local status="$1"
    local message="$2"

    local webhook_url
    webhook_url=$(sysctl config get notifications.slack.webhook_url 2>/dev/null || true)

    if [ -n "$webhook_url" ]; then
        local color="good"
        case "$status" in
            "FAILED") color="danger" ;;
            "WARNING") color="warning" ;;
        esac

        curl -X POST -H 'Content-type: application/json' \
            --data "{
                \"attachments\": [{
                    \"color\": \"$color\",
                    \"title\": \"Backup Status: $status\",
                    \"text\": \"$message\",
                    \"timestamp\": $(date +%s)
                }]
            }" \
            "$webhook_url" >/dev/null 2>&1 || true
    fi
}

send_email_notification() {
    local status="$1"
    local message="$2"

    local email_recipients
    email_recipients=$(sysctl config get notifications.email.recipients 2>/dev/null || true)

    if [ -n "$email_recipients" ]; then
        {
            echo "Subject: Backup Status: $status"
            echo "From: backup@company.com"
            echo "To: $email_recipients"
            echo ""
            echo "$message"
            echo ""
            echo "Time: $(date)"
            echo "Host: $(hostname)"
        } | sendmail "$email_recipients" 2>/dev/null || true
    fi
}

# Main backup function
run_backup() {
    local backup_date
    backup_date=$(date '+%Y%m%d-%H%M%S')

    local overall_success=true
    local backup_summary=""

    IFS=',' read -ra ENV_ARRAY <<< "$ENVIRONMENTS"

    for environment in "${ENV_ARRAY[@]}"; do
        info "Starting backup for environment: $environment"

        local env_success=true
        local backup_name="${environment}-backup-${backup_date}"

        IFS=',' read -ra TYPE_ARRAY <<< "$BACKUP_TYPES"

        for backup_type in "${TYPE_ARRAY[@]}"; do
            case "$backup_type" in
                "database")
                    if ! backup_database "$environment" "$backup_name"; then
                        env_success=false
                        overall_success=false
                    fi
                    ;;
                "config")
                    if ! backup_config "$environment" "$backup_name"; then
                        env_success=false
                        overall_success=false
                    fi
                    ;;
                "files")
                    if ! backup_files "$environment" "$backup_name"; then
                        env_success=false
                        overall_success=false
                    fi
                    ;;
                "state")
                    if ! backup_state "$environment" "$backup_name"; then
                        env_success=false
                        overall_success=false
                    fi
                    ;;
            esac
        done

        # Verify backups
        if [ "$env_success" = true ]; then
            if verify_backups "$environment" "$backup_name"; then
                backup_summary="${backup_summary}✅ $environment: SUCCESS\n"
            else
                backup_summary="${backup_summary}⚠️ $environment: BACKUP OK, VERIFICATION FAILED\n"
                overall_success=false
            fi
        else
            backup_summary="${backup_summary}❌ $environment: FAILED\n"
        fi

        # Cleanup old backups
        cleanup_old_backups "$environment"

        info "Completed backup for environment: $environment"
    done

    # Send notification
    if [ "$overall_success" = true ]; then
        send_notification "SUCCESS" "All backups completed successfully:\n\n$backup_summary"
        success "All backups completed successfully"
    else
        send_notification "FAILED" "Some backups failed:\n\n$backup_summary"
        error "Some backups failed"
    fi

    return $([ "$overall_success" = true ] && echo 0 || echo 1)
}

# Generate backup report
generate_backup_report() {
    info "Generating backup report"

    echo "# Backup Status Report"
    echo "Generated: $(date)"
    echo ""

    IFS=',' read -ra ENV_ARRAY <<< "$ENVIRONMENTS"

    for environment in "${ENV_ARRAY[@]}"; do
        echo "## Environment: $environment"
        echo ""

        # List recent backups
        echo "### Recent Backups"
        sysctl backup list --env "$environment" --limit 10 --format table
        echo ""

        # Backup statistics
        echo "### Statistics"
        local total_backups
        total_backups=$(sysctl backup list --env "$environment" --count)
        echo "- Total backups: $total_backups"

        local last_backup
        last_backup=$(sysctl backup list --env "$environment" --limit 1 --format json | jq -r '.[0].created_at // "never"')
        echo "- Last backup: $last_backup"

        local backup_size
        backup_size=$(sysctl backup list --env "$environment" --limit 1 --format json | jq -r '.[0].size // "unknown"')
        echo "- Last backup size: $backup_size"
        echo ""
    done
}

# Main function
main() {
    local command="${1:-backup}"

    # Acquire lock
    acquire_lock

    # Load configuration
    load_config

    case "$command" in
        "backup")
            run_backup
            ;;
        "report")
            generate_backup_report
            ;;
        "cleanup")
            IFS=',' read -ra ENV_ARRAY <<< "$ENVIRONMENTS"
            for environment in "${ENV_ARRAY[@]}"; do
                cleanup_old_backups "$environment"
            done
            ;;
        "verify")
            local environment="${2:-production}"
            local backup_name="${3:-latest}"
            verify_backups "$environment" "$backup_name"
            ;;
        *)
            echo "Usage: $0 {backup|report|cleanup|verify [env] [backup_name]}"
            exit 1
            ;;
    esac
}

# Check dependencies
for cmd in sysctl aws openssl jq; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        error "Required command not found: $cmd"
        exit 1
    fi
done

main "$@"
```

## Maintenance and Operations Scripts

### System Maintenance Script

```bash
#!/bin/bash
# system-maintenance.sh - Automated system maintenance tasks
set -euo pipefail

readonly LOG_FILE="/var/log/system-maintenance.log"
readonly CONFIG_FILE="/etc/sysctl/maintenance-config.yaml"

# Default configuration
ENVIRONMENTS="production,staging"
MAINTENANCE_TASKS="cleanup,optimize,security-scan,update-check"
DRY_RUN="false"
NOTIFICATION_ENABLED="true"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

load_config() {
    if [ -f "$CONFIG_FILE" ]; then
        ENVIRONMENTS=$(sysctl config get maintenance.environments || echo "$ENVIRONMENTS")
        MAINTENANCE_TASKS=$(sysctl config get maintenance.tasks || echo "$MAINTENANCE_TASKS")
        DRY_RUN=$(sysctl config get maintenance.dry_run || echo "$DRY_RUN")
    fi

    log "Maintenance configuration loaded"
}

# Cleanup tasks
cleanup_old_logs() {
    local environment="$1"

    log "Cleaning up old logs for $environment"

    if [ "$DRY_RUN" = "true" ]; then
        log "DRY RUN: Would clean logs older than 30 days"
        return 0
    fi

    # Clean application logs
    sysctl logs cleanup --env "$environment" --older-than 30d

    # Clean system logs
    find /var/log -name "*.log" -mtime +30 -delete 2>/dev/null || true

    log "Log cleanup completed for $environment"
}

cleanup_unused_images() {
    local environment="$1"

    log "Cleaning up unused Docker images for $environment"

    if [ "$DRY_RUN" = "true" ]; then
        sysctl cleanup images --env "$environment" --dry-run
        return 0
    fi

    sysctl cleanup images --env "$environment" --unused --older-than 7d

    log "Image cleanup completed for $environment"
}

cleanup_old_backups() {
    local environment="$1"

    log "Cleaning up old backups for $environment"

    if [ "$DRY_RUN" = "true" ]; then
        sysctl backup cleanup --env "$environment" --older-than 30d --dry-run
        return 0
    fi

    sysctl backup cleanup --env "$environment" --older-than 30d

    log "Backup cleanup completed for $environment"
}

# Optimization tasks
optimize_database() {
    local environment="$1"

    log "Optimizing database for $environment"

    if [ "$DRY_RUN" = "true" ]; then
        log "DRY RUN: Would optimize database tables and indexes"
        return 0
    fi

    # Analyze tables
    sysctl database analyze --env "$environment" --all-tables

    # Optimize tables
    sysctl database optimize --env "$environment" --all-tables

    # Update statistics
    sysctl database update-stats --env "$environment"

    log "Database optimization completed for $environment"
}

optimize_application_cache() {
    local environment="$1"

    log "Optimizing application cache for $environment"

    if [ "$DRY_RUN" = "true" ]; then
        log "DRY RUN: Would clear expired cache entries"
        return 0
    fi

    # Clear expired cache entries
    sysctl cache cleanup --env "$environment" --expired

    # Warm up critical cache entries
    sysctl cache warm-up --env "$environment" --critical-keys

    log "Cache optimization completed for $environment"
}

# Security tasks
security_scan() {
    local environment="$1"

    log "Running security scan for $environment"

    # Vulnerability scan
    local scan_result
    if scan_result=$(sysctl security scan --env "$environment" --format json); then
        local vulnerability_count
        vulnerability_count=$(echo "$scan_result" | jq '.vulnerabilities | length')

        if [ "$vulnerability_count" -gt 0 ]; then
            log "WARNING: Found $vulnerability_count vulnerabilities in $environment"

            # Generate security report
            sysctl security report --env "$environment" --output "/tmp/security-report-${environment}.html"

            # Send alert for critical vulnerabilities
            local critical_count
            critical_count=$(echo "$scan_result" | jq '[.vulnerabilities[] | select(.severity == "critical")] | length')

            if [ "$critical_count" -gt 0 ]; then
                send_alert "CRITICAL" "Found $critical_count critical vulnerabilities in $environment" "$environment"
            fi
        else
            log "No vulnerabilities found in $environment"
        fi
    else
        log "Security scan failed for $environment"
        return 1
    fi

    log "Security scan completed for $environment"
}

update_check() {
    local environment="$1"

    log "Checking for updates in $environment"

    # Check for system updates
    if sysctl updates check --env "$environment" --security-only; then
        local updates
        updates=$(sysctl updates list --env "$environment" --security-only --format json)

        local update_count
        update_count=$(echo "$updates" | jq '. | length')

        if [ "$update_count" -gt 0 ]; then
            log "Found $update_count security updates available for $environment"

            if [ "$environment" != "production" ]; then
                log "Auto-applying security updates to $environment"
                sysctl updates apply --env "$environment" --security-only --auto-approve
            else
                log "Security updates available for production - manual approval required"
                send_alert "WARNING" "$update_count security updates available for $environment" "$environment"
            fi
        else
            log "No security updates available for $environment"
        fi
    else
        log "Update check failed for $environment"
        return 1
    fi

    log "Update check completed for $environment"
}

# Resource optimization
optimize_resources() {
    local environment="$1"

    log "Optimizing resources for $environment"

    # Check resource utilization
    local cpu_usage memory_usage disk_usage
    cpu_usage=$(sysctl metrics get cpu_usage --env "$environment" --avg)
    memory_usage=$(sysctl metrics get memory_usage --env "$environment" --avg)
    disk_usage=$(sysctl metrics get disk_usage --env "$environment" --avg)

    log "Current resource usage - CPU: $cpu_usage%, Memory: $memory_usage%, Disk: $disk_usage%"

    # Auto-scale based on usage
    if (( $(echo "$cpu_usage < 30" | bc -l) )) && [ "$environment" != "production" ]; then
        log "Low CPU usage detected, considering scale-down"
        if [ "$DRY_RUN" = "false" ]; then
            sysctl scale --env "$environment" --optimize --safe-only
        fi
    elif (( $(echo "$cpu_usage > 80" | bc -l) )); then
        log "High CPU usage detected, considering scale-up"
        if [ "$DRY_RUN" = "false" ]; then
            sysctl scale --env "$environment" --optimize --increase-capacity
        fi
    fi

    # Cleanup unused resources
    if [ "$DRY_RUN" = "false" ]; then
        sysctl resources cleanup --env "$environment" --unused --safe-only
    fi

    log "Resource optimization completed for $environment"
}

# Health check and monitoring
system_health_check() {
    local environment="$1"

    log "Running system health check for $environment"

    # Comprehensive health check
    if ! sysctl health-check --all --env "$environment" --comprehensive; then
        log "Health check failed for $environment"
        send_alert "ERROR" "System health check failed for $environment" "$environment"
        return 1
    fi

    # Performance check
    if ! sysctl test performance --env "$environment" --quick; then
        log "Performance check failed for $environment"
        send_alert "WARNING" "Performance degradation detected in $environment" "$environment"
        return 1
    fi

    log "System health check passed for $environment"
}

# Notification function
send_alert() {
    local severity="$1"
    local message="$2"
    local environment="$3"

    if [ "$NOTIFICATION_ENABLED" = "true" ]; then
        sysctl alert send "$message" --severity "$severity" --environment "$environment" --channel slack,email
    fi
}

# Generate maintenance report
generate_maintenance_report() {
    log "Generating maintenance report"

    local report_file="/tmp/maintenance-report-$(date +%Y%m%d).html"

    {
        echo "<html><head><title>System Maintenance Report</title></head><body>"
        echo "<h1>System Maintenance Report</h1>"
        echo "<p>Generated: $(date)</p>"
        echo "<h2>Summary</h2>"

        IFS=',' read -ra ENV_ARRAY <<< "$ENVIRONMENTS"
        for environment in "${ENV_ARRAY[@]}"; do
            echo "<h3>Environment: $environment</h3>"
            echo "<ul>"

            # System status
            if sysctl health-check --all --env "$environment" --quiet; then
                echo "<li>✅ System Health: OK</li>"
            else
                echo "<li>❌ System Health: Issues detected</li>"
            fi

            # Resource usage
            local cpu_usage memory_usage disk_usage
            cpu_usage=$(sysctl metrics get cpu_usage --env "$environment" --avg)
            memory_usage=$(sysctl metrics get memory_usage --env "$environment" --avg)
            disk_usage=$(sysctl metrics get disk_usage --env "$environment" --avg)

            echo "<li>📊 Resource Usage: CPU $cpu_usage%, Memory $memory_usage%, Disk $disk_usage%</li>"

            # Last backup
            local last_backup
            last_backup=$(sysctl backup list --env "$environment" --limit 1 --format json | jq -r '.[0].created_at // "never"')
            echo "<li>💾 Last Backup: $last_backup</li>"

            echo "</ul>"
        done

        echo "</body></html>"
    } > "$report_file"

    log "Maintenance report generated: $report_file"

    # Email report if configured
    local email_recipients
    email_recipients=$(sysctl config get notifications.email.recipients 2>/dev/null || true)
    if [ -n "$email_recipients" ]; then
        {
            echo "Subject: System Maintenance Report - $(date +%Y-%m-%d)"
            echo "From: maintenance@company.com"
            echo "To: $email_recipients"
            echo "Content-Type: text/html"
            echo ""
            cat "$report_file"
        } | sendmail "$email_recipients" 2>/dev/null || true
    fi
}

# Main maintenance function
run_maintenance() {
    log "Starting system maintenance"

    local overall_success=true

    IFS=',' read -ra ENV_ARRAY <<< "$ENVIRONMENTS"
    IFS=',' read -ra TASK_ARRAY <<< "$MAINTENANCE_TASKS"

    for environment in "${ENV_ARRAY[@]}"; do
        log "Running maintenance for environment: $environment"

        for task in "${TASK_ARRAY[@]}"; do
            case "$task" in
                "cleanup")
                    cleanup_old_logs "$environment" || overall_success=false
                    cleanup_unused_images "$environment" || overall_success=false
                    cleanup_old_backups "$environment" || overall_success=false
                    ;;
                "optimize")
                    optimize_database "$environment" || overall_success=false
                    optimize_application_cache "$environment" || overall_success=false
                    optimize_resources "$environment" || overall_success=false
                    ;;
                "security-scan")
                    security_scan "$environment" || overall_success=false
                    ;;
                "update-check")
                    update_check "$environment" || overall_success=false
                    ;;
                "health-check")
                    system_health_check "$environment" || overall_success=false
                    ;;
            esac
        done

        log "Maintenance completed for environment: $environment"
    done

    # Generate report
    generate_maintenance_report

    if [ "$overall_success" = true ]; then
        log "All maintenance tasks completed successfully"
        send_alert "INFO" "System maintenance completed successfully" "all"
    else
        log "Some maintenance tasks failed"
        send_alert "WARNING" "Some maintenance tasks failed - check logs" "all"
    fi

    return $([ "$overall_success" = true ] && echo 0 || echo 1)
}

# Main function
main() {
    local command="${1:-maintenance}"

    # Load configuration
    load_config

    case "$command" in
        "maintenance")
            run_maintenance
            ;;
        "report")
            generate_maintenance_report
            ;;
        "dry-run")
            DRY_RUN="true"
            run_maintenance
            ;;
        *)
            echo "Usage: $0 {maintenance|report|dry-run}"
            exit 1
            ;;
    esac
}

# Check dependencies
for cmd in sysctl jq bc; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "Required command not found: $cmd" >&2
        exit 1
    fi
done

main "$@"
```

These automation scripts provide comprehensive coverage of deployment, monitoring, backup, and
maintenance tasks, incorporating error handling, logging, notifications, and rollback capabilities
essential for production environments.
