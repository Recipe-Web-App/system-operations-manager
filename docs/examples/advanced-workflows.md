# Advanced Workflows

Complex automation patterns and sophisticated workflows for enterprise-grade system management and orchestration.

## Multi-Environment CI/CD Pipeline

### Advanced Deployment Pipeline

```yaml
# workflows/deployment-pipeline.yaml
name: Advanced Deployment Pipeline
description: Multi-stage deployment with validation gates

stages:
  - name: validation
    description: Pre-deployment validation
    steps:
      - name: config-validation
        command: sysctl config validate --env ${TARGET_ENV}

      - name: dependency-check
        command: sysctl dependencies check --all

      - name: security-scan
        command: sysctl security scan --severity medium
        condition: env == 'production'

      - name: capacity-check
        command: sysctl resources capacity-check --required ${REQUIRED_RESOURCES}
        condition: env == 'production'

  - name: backup
    description: Create system backup
    steps:
      - name: database-backup
        command: sysctl backup create database --name pre-deploy-${TIMESTAMP}

      - name: config-backup
        command: sysctl config backup --name pre-deploy-${TIMESTAMP}

      - name: state-snapshot
        command: sysctl snapshot create --name pre-deploy-${TIMESTAMP}

  - name: deployment
    description: Execute deployment
    parallel: false
    steps:
      - name: deploy-database
        command: sysctl deploy database --strategy maintenance --env ${TARGET_ENV}

      - name: migrate-database
        command: sysctl database migrate --env ${TARGET_ENV}
        depends_on: [deploy-database]

      - name: deploy-backend
        command: sysctl deploy api worker --strategy blue-green --env ${TARGET_ENV}
        depends_on: [migrate-database]

      - name: deploy-frontend
        command: sysctl deploy frontend --strategy canary --percentage 25 --env ${TARGET_ENV}
        depends_on: [deploy-backend]

  - name: validation-post
    description: Post-deployment validation
    steps:
      - name: health-checks
        command: sysctl health-check --all --env ${TARGET_ENV} --timeout 300

      - name: smoke-tests
        command: sysctl test smoke --env ${TARGET_ENV} --timeout 600

      - name: performance-check
        command: sysctl test performance --baseline --env ${TARGET_ENV}

      - name: security-verify
        command: sysctl security verify --runtime --env ${TARGET_ENV}

  - name: traffic-migration
    description: Gradually migrate traffic
    condition: deployment.strategy == 'canary'
    steps:
      - name: canary-25
        command: sysctl deploy canary-update frontend --percentage 25 --env ${TARGET_ENV}

      - name: monitor-metrics
        command: sysctl metrics monitor --duration 300 --threshold-file thresholds.yaml

      - name: canary-50
        command: sysctl deploy canary-update frontend --percentage 50 --env ${TARGET_ENV}
        condition: monitor-metrics.success

      - name: monitor-metrics-2
        command: sysctl metrics monitor --duration 300 --threshold-file thresholds.yaml

      - name: canary-100
        command: sysctl deploy canary-update frontend --percentage 100 --env ${TARGET_ENV}
        condition: monitor-metrics-2.success

  - name: cleanup
    description: Post-deployment cleanup
    steps:
      - name: cleanup-old-images
        command: sysctl cleanup images --older-than 7d

      - name: cleanup-old-backups
        command: sysctl backup cleanup --older-than 30d

      - name: update-documentation
        command: sysctl docs update --deployment-info --env ${TARGET_ENV}

# Error handling
on_failure:
  - name: rollback-deployment
    command: sysctl rollback --all --to-snapshot pre-deploy-${TIMESTAMP} --env ${TARGET_ENV}

  - name: restore-database
    command: sysctl backup restore database --backup pre-deploy-${TIMESTAMP}

  - name: send-alert
    command: sysctl alert send "Deployment failed in ${TARGET_ENV}" --severity critical --channel pagerduty

  - name: create-incident
    command: sysctl incident create "Deployment failure" --severity high --assignee oncall

# Success handling
on_success:
  - name: cleanup-old-versions
    command: sysctl cleanup versions --keep 5

  - name: update-status-page
    command: sysctl status-page update "Successfully deployed ${VERSION} to ${TARGET_ENV}"

  - name: notify-team
    command: sysctl notify team "Deployment completed successfully" --channel slack
```

### Pipeline Execution

```bash
# Execute pipeline with parameters
sysctl workflow run deployment-pipeline \
  --param TARGET_ENV=production \
  --param VERSION=v2.1.0 \
  --param REQUIRED_RESOURCES=16GB \
  --timeout 3600

# Execute with approval gates
sysctl workflow run deployment-pipeline \
  --param TARGET_ENV=production \
  --require-approval \
  --approval-timeout 1800

# Dry run pipeline
sysctl workflow run deployment-pipeline \
  --param TARGET_ENV=staging \
  --dry-run \
  --show-plan

# Resume failed pipeline
sysctl workflow resume deployment-pipeline-20240115-143022 \
  --from-stage deployment
```

## Blue-Green Deployment with Database Migration

### Complex Blue-Green Strategy

```yaml
# workflows/blue-green-database.yaml
name: Blue-Green with Database Migration
description: Safe blue-green deployment handling database schema changes

variables:
  - name: BLUE_ENV
    value: "${TARGET_ENV}-blue"
  - name: GREEN_ENV
    value: "${TARGET_ENV}-green"
  - name: MIGRATION_TIMEOUT
    value: 1800

phases:
  - name: preparation
    steps:
      - name: create-green-environment
        command: sysctl env clone ${BLUE_ENV} ${GREEN_ENV}

      - name: validate-migration
        command: sysctl database migration validate --from-env ${BLUE_ENV} --to-env ${GREEN_ENV}

      - name: backup-blue-database
        command: sysctl backup create database --env ${BLUE_ENV} --name blue-pre-migration-${TIMESTAMP}

  - name: migration
    steps:
      - name: put-blue-in-maintenance
        command: sysctl maintenance enable --env ${BLUE_ENV} --message "Database migration in progress"

      - name: stop-blue-writers
        command: sysctl database readonly --env ${BLUE_ENV}

      - name: sync-database
        command: sysctl database sync --from ${BLUE_ENV} --to ${GREEN_ENV} --timeout ${MIGRATION_TIMEOUT}

      - name: run-migrations
        command: sysctl database migrate --env ${GREEN_ENV} --timeout ${MIGRATION_TIMEOUT}

      - name: verify-migration
        command: sysctl database verify --env ${GREEN_ENV}

  - name: deployment
    steps:
      - name: deploy-green
        command: sysctl deploy --all --env ${GREEN_ENV} --image-tag ${VERSION}

      - name: warm-up-green
        command: sysctl service warm-up --all --env ${GREEN_ENV} --duration 300

      - name: health-check-green
        command: sysctl health-check --all --env ${GREEN_ENV} --timeout 300

  - name: traffic-switch
    steps:
      - name: switch-traffic
        command: sysctl traffic switch --from ${BLUE_ENV} --to ${GREEN_ENV} --percentage 100

      - name: verify-traffic
        command: sysctl traffic verify --env ${GREEN_ENV} --duration 300

      - name: disable-blue-maintenance
        command: sysctl maintenance disable --env ${BLUE_ENV}

  - name: finalization
    steps:
      - name: update-primary-alias
        command: sysctl env alias set primary ${GREEN_ENV}

      - name: cleanup-blue
        command: sysctl env cleanup ${BLUE_ENV} --delay 3600

on_failure:
  - name: rollback-traffic
    command: sysctl traffic switch --from ${GREEN_ENV} --to ${BLUE_ENV} --percentage 100

  - name: rollback-database
    command: sysctl backup restore database --backup blue-pre-migration-${TIMESTAMP} --env ${BLUE_ENV}

  - name: cleanup-green
    command: sysctl env destroy ${GREEN_ENV}

  - name: disable-maintenance
    command: sysctl maintenance disable --env ${BLUE_ENV}
```

## Multi-Region Deployment Orchestration

### Global Deployment Strategy

```yaml
# workflows/multi-region-deployment.yaml
name: Multi-Region Global Deployment
description: Coordinated deployment across multiple regions with failover

regions:
  - name: us-east-1
    priority: 1
    capacity: primary

  - name: us-west-2
    priority: 2
    capacity: primary

  - name: eu-west-1
    priority: 3
    capacity: secondary

  - name: ap-southeast-1
    priority: 4
    capacity: secondary

deployment_strategy:
  type: rolling-by-region
  max_simultaneous_regions: 2
  wait_between_regions: 300

phases:
  - name: pre-deployment
    scope: global
    steps:
      - name: validate-global-config
        command: sysctl config validate --all-regions

      - name: check-cross-region-dependencies
        command: sysctl dependencies check --cross-region

      - name: create-global-snapshot
        command: sysctl snapshot create --global --name global-pre-deploy-${TIMESTAMP}

  - name: primary-regions
    scope: regions
    filter: capacity == 'primary'
    parallel: true
    max_parallel: 1
    steps:
      - name: region-backup
        command: sysctl backup create --region ${REGION} --name region-backup-${TIMESTAMP}

      - name: deploy-region
        command: sysctl deploy --all --region ${REGION} --strategy blue-green

      - name: validate-region
        command: sysctl health-check --all --region ${REGION} --timeout 600

      - name: traffic-test
        command: sysctl traffic test --region ${REGION} --duration 300

      - name: enable-region
        command: sysctl traffic enable --region ${REGION}

  - name: secondary-regions
    scope: regions
    filter: capacity == 'secondary'
    depends_on: [primary-regions]
    parallel: true
    max_parallel: 2
    steps:
      - name: region-backup
        command: sysctl backup create --region ${REGION} --name region-backup-${TIMESTAMP}

      - name: deploy-region
        command: sysctl deploy --all --region ${REGION} --strategy rolling

      - name: validate-region
        command: sysctl health-check --all --region ${REGION} --timeout 400

      - name: enable-region
        command: sysctl traffic enable --region ${REGION}

  - name: global-validation
    scope: global
    steps:
      - name: cross-region-connectivity
        command: sysctl network test --cross-region --timeout 300

      - name: global-load-balance-test
        command: sysctl traffic test --global --duration 600

      - name: failover-test
        command: sysctl failover test --duration 300 --validate

on_region_failure:
  - name: isolate-failed-region
    command: sysctl traffic disable --region ${FAILED_REGION}

  - name: redistribute-traffic
    command: sysctl traffic rebalance --exclude ${FAILED_REGION}

  - name: rollback-failed-region
    command: sysctl rollback --all --region ${FAILED_REGION} --to-snapshot region-backup-${TIMESTAMP}

  - name: alert-oncall
    command: sysctl alert send "Region ${FAILED_REGION} deployment failed" --severity critical
```

## Database Migration with Zero Downtime

### Complex Migration Workflow

```yaml
# workflows/zero-downtime-migration.yaml
name: Zero Downtime Database Migration
description: Sophisticated database migration with dual-write strategy

variables:
  - name: OLD_SCHEMA
    value: "v1"
  - name: NEW_SCHEMA
    value: "v2"
  - name: MIGRATION_TIMEOUT
    value: 3600

phases:
  - name: preparation
    steps:
      - name: create-migration-schema
        command: sysctl database schema create ${NEW_SCHEMA} --from ${OLD_SCHEMA}

      - name: validate-migration-scripts
        command: sysctl database migration validate --from ${OLD_SCHEMA} --to ${NEW_SCHEMA}

      - name: setup-dual-write
        command: sysctl database dual-write enable --old-schema ${OLD_SCHEMA} --new-schema ${NEW_SCHEMA}

      - name: backup-database
        command: sysctl backup create database --full --name migration-backup-${TIMESTAMP}

  - name: schema-migration
    steps:
      - name: run-schema-migration
        command: sysctl database migrate schema --to ${NEW_SCHEMA} --timeout ${MIGRATION_TIMEOUT}

      - name: verify-schema
        command: sysctl database verify schema --schema ${NEW_SCHEMA}

      - name: create-indexes
        command: sysctl database index create --schema ${NEW_SCHEMA} --concurrently

      - name: update-statistics
        command: sysctl database analyze --schema ${NEW_SCHEMA}

  - name: data-migration
    parallel: true
    steps:
      - name: migrate-user-data
        command: sysctl database migrate data --table users --to-schema ${NEW_SCHEMA} --batch-size 10000

      - name: migrate-order-data
        command: sysctl database migrate data --table orders --to-schema ${NEW_SCHEMA} --batch-size 5000

      - name: migrate-product-data
        command: sysctl database migrate data --table products --to-schema ${NEW_SCHEMA} --batch-size 2000

      - name: verify-data-integrity
        command: sysctl database verify data --compare-schemas ${OLD_SCHEMA} ${NEW_SCHEMA}

  - name: application-cutover
    steps:
      - name: deploy-dual-read-version
        command: sysctl deploy api --image ${APP_IMAGE}:dual-read-${VERSION} --strategy rolling

      - name: validate-dual-read
        command: sysctl test integration --dual-read --duration 600

      - name: switch-primary-read
        command: sysctl database primary-read switch --to-schema ${NEW_SCHEMA}

      - name: monitor-performance
        command: sysctl metrics monitor database --duration 900 --alert-on-degradation

  - name: finalization
    steps:
      - name: deploy-single-schema-version
        command: sysctl deploy api --image ${APP_IMAGE}:${VERSION} --strategy rolling

      - name: disable-dual-write
        command: sysctl database dual-write disable

      - name: cleanup-old-schema
        command: sysctl database schema drop ${OLD_SCHEMA} --delay 86400

      - name: optimize-new-schema
        command: sysctl database optimize --schema ${NEW_SCHEMA}

on_failure:
  - name: switch-back-to-old-schema
    command: sysctl database primary-read switch --to-schema ${OLD_SCHEMA}

  - name: rollback-application
    command: sysctl rollback api --to-previous

  - name: disable-dual-write
    command: sysctl database dual-write disable

  - name: restore-from-backup
    command: sysctl backup restore database --backup migration-backup-${TIMESTAMP}
```

## Microservices Orchestration

### Complex Service Dependencies

```yaml
# workflows/microservices-deployment.yaml
name: Microservices Orchestration
description: Coordinated deployment of interdependent microservices

services:
  - name: user-service
    dependencies: []
    deployment_order: 1

  - name: auth-service
    dependencies: [user-service]
    deployment_order: 2

  - name: product-service
    dependencies: []
    deployment_order: 1

  - name: inventory-service
    dependencies: [product-service]
    deployment_order: 2

  - name: order-service
    dependencies: [user-service, auth-service, inventory-service]
    deployment_order: 3

  - name: payment-service
    dependencies: [user-service, auth-service]
    deployment_order: 3

  - name: notification-service
    dependencies: [user-service, order-service]
    deployment_order: 4

  - name: api-gateway
    dependencies: [user-service, auth-service, product-service, order-service]
    deployment_order: 5

phases:
  - name: dependency-analysis
    steps:
      - name: validate-dependency-graph
        command: sysctl dependencies validate --services ${ALL_SERVICES}

      - name: calculate-deployment-order
        command: sysctl dependencies order --services ${ALL_SERVICES}

      - name: check-backward-compatibility
        command: sysctl compatibility check --services ${ALL_SERVICES} --version ${VERSION}

  - name: infrastructure-preparation
    steps:
      - name: scale-infrastructure
        command: sysctl resources scale --prepare-for-deployment --services ${ALL_SERVICES}

      - name: setup-service-mesh
        command: sysctl service-mesh configure --services ${ALL_SERVICES}

      - name: configure-circuit-breakers
        command: sysctl circuit-breakers configure --services ${ALL_SERVICES}

  - name: phased-deployment
    steps:
      - name: deploy-order-1
        command: sysctl deploy user-service product-service --strategy blue-green --wait-for-health

      - name: deploy-order-2
        command: sysctl deploy auth-service inventory-service --strategy blue-green --wait-for-health
        depends_on: [deploy-order-1]

      - name: deploy-order-3
        command: sysctl deploy order-service payment-service --strategy canary --percentage 25
        depends_on: [deploy-order-2]

      - name: validate-order-3
        command: sysctl test integration --services order-service,payment-service --timeout 600
        depends_on: [deploy-order-3]

      - name: promote-order-3
        command: sysctl deploy canary-promote order-service payment-service
        depends_on: [validate-order-3]
        condition: validate-order-3.success

      - name: deploy-order-4
        command: sysctl deploy notification-service --strategy rolling
        depends_on: [promote-order-3]

      - name: deploy-order-5
        command: sysctl deploy api-gateway --strategy blue-green --final
        depends_on: [deploy-order-4]

  - name: system-integration
    steps:
      - name: end-to-end-tests
        command: sysctl test e2e --full-system --timeout 1800

      - name: performance-validation
        command: sysctl test performance --baseline --duration 900

      - name: security-scan
        command: sysctl security scan runtime --all-services

      - name: chaos-testing
        command: sysctl chaos test --duration 600 --mild

on_service_failure:
  - name: isolate-failed-service
    command: sysctl service-mesh isolate ${FAILED_SERVICE}

  - name: rollback-failed-service
    command: sysctl rollback ${FAILED_SERVICE} --to-previous

  - name: check-dependent-services
    command: sysctl dependencies check-health --dependents-of ${FAILED_SERVICE}

  - name: adjust-traffic-routing
    command: sysctl traffic route --around ${FAILED_SERVICE} --temporary
```

## Disaster Recovery Orchestration

### Comprehensive DR Workflow

```yaml
# workflows/disaster-recovery.yaml
name: Disaster Recovery Orchestration
description: Complete disaster recovery with cross-region failover

trigger_conditions:
  - primary_region_failure
  - database_corruption
  - security_breach
  - manual_activation

phases:
  - name: assessment
    timeout: 300
    steps:
      - name: assess-damage
        command: sysctl disaster assess --primary-region ${PRIMARY_REGION}

      - name: verify-dr-readiness
        command: sysctl disaster verify-readiness --dr-region ${DR_REGION}

      - name: calculate-rto-rpo
        command: sysctl disaster calculate-impact --last-backup-age

      - name: notify-stakeholders
        command: sysctl alert send "Disaster recovery initiated" --severity critical --all-channels

  - name: data-recovery
    timeout: 1800
    steps:
      - name: activate-dr-database
        command: sysctl database failover --to-region ${DR_REGION}

      - name: verify-data-integrity
        command: sysctl database verify --region ${DR_REGION} --comprehensive

      - name: restore-missing-data
        command: sysctl backup restore --latest --region ${DR_REGION} --fill-gaps

      - name: sync-active-sessions
        command: sysctl sessions recover --from-region ${PRIMARY_REGION} --to-region ${DR_REGION}

  - name: service-recovery
    timeout: 900
    parallel: true
    steps:
      - name: deploy-critical-services
        command: sysctl deploy --critical-only --region ${DR_REGION} --fast-start
        priority: 1

      - name: deploy-supporting-services
        command: sysctl deploy --supporting --region ${DR_REGION}
        priority: 2
        depends_on: [deploy-critical-services]

      - name: deploy-optional-services
        command: sysctl deploy --optional --region ${DR_REGION}
        priority: 3
        depends_on: [deploy-supporting-services]

  - name: traffic-redirection
    timeout: 300
    steps:
      - name: update-dns-records
        command: sysctl dns failover --primary-region ${PRIMARY_REGION} --dr-region ${DR_REGION}

      - name: update-load-balancers
        command: sysctl load-balancer redirect --from-region ${PRIMARY_REGION} --to-region ${DR_REGION}

      - name: verify-traffic-flow
        command: sysctl traffic verify --region ${DR_REGION} --timeout 180

      - name: enable-cdn-redirect
        command: sysctl cdn redirect --to-region ${DR_REGION}

  - name: validation
    timeout: 600
    steps:
      - name: health-check-all
        command: sysctl health-check --all --region ${DR_REGION} --timeout 300

      - name: functional-testing
        command: sysctl test smoke --region ${DR_REGION} --timeout 300

      - name: performance-validation
        command: sysctl test performance --region ${DR_REGION} --reduced-load

      - name: security-verification
        command: sysctl security verify --region ${DR_REGION}

  - name: monitoring-setup
    steps:
      - name: activate-dr-monitoring
        command: sysctl monitoring activate --region ${DR_REGION} --enhanced

      - name: setup-alerts
        command: sysctl alerts configure --dr-mode --region ${DR_REGION}

      - name: notify-success
        command: sysctl alert send "Disaster recovery completed successfully" --severity info --all-channels

recovery_validation:
  - name: primary-region-recovery
    condition: primary_region_restored
    steps:
      - name: validate-primary-region
        command: sysctl disaster validate-primary --region ${PRIMARY_REGION}

      - name: sync-data-back
        command: sysctl database sync --from-region ${DR_REGION} --to-region ${PRIMARY_REGION}

      - name: failback-traffic
        command: sysctl disaster failback --from-region ${DR_REGION} --to-region ${PRIMARY_REGION}

      - name: cleanup-dr-resources
        command: sysctl disaster cleanup --region ${DR_REGION} --preserve-data
```

## Performance Optimization Workflow

### Automated Performance Tuning

```yaml
# workflows/performance-optimization.yaml
name: Automated Performance Optimization
description: ML-driven performance optimization with A/B testing

phases:
  - name: baseline-establishment
    steps:
      - name: collect-baseline-metrics
        command: sysctl metrics collect --all-services --duration 3600 --baseline

      - name: analyze-performance-patterns
        command: sysctl analytics patterns --historical-data 30d

      - name: identify-bottlenecks
        command: sysctl performance analyze --identify-bottlenecks

      - name: generate-optimization-plan
        command: sysctl performance plan --ml-recommendations --confidence-threshold 0.8

  - name: optimization-testing
    steps:
      - name: create-test-environment
        command: sysctl env clone production performance-test

      - name: apply-optimizations
        command: sysctl performance apply --recommendations ${OPTIMIZATION_PLAN} --env performance-test

      - name: load-test-optimized
        command: sysctl test load --env performance-test --duration 1800 --realistic-load

      - name: compare-performance
        command: sysctl performance compare --baseline production --optimized performance-test

  - name: gradual-rollout
    condition: performance_improvement > 10%
    steps:
      - name: canary-optimization
        command: sysctl performance deploy --canary --percentage 10 --optimizations ${APPROVED_OPTIMIZATIONS}

      - name: monitor-canary-metrics
        command: sysctl metrics monitor --canary-group --duration 1800 --alert-on-regression

      - name: expand-canary
        command: sysctl performance deploy --canary --percentage 50
        condition: canary_performance_good

      - name: full-rollout
        command: sysctl performance deploy --full --optimizations ${APPROVED_OPTIMIZATIONS}
        condition: expanded_canary_success

  - name: continuous-monitoring
    steps:
      - name: setup-performance-monitoring
        command: sysctl monitoring setup-performance --enhanced --all-services

      - name: configure-regression-alerts
        command: sysctl alerts configure --performance-regression --threshold 15%

      - name: schedule-optimization-review
        command: sysctl schedule create --weekly --task performance-review
```

## Execution Examples

### Running Advanced Workflows

```bash
# Execute multi-environment pipeline
sysctl workflow run deployment-pipeline \
  --param TARGET_ENV=production \
  --param VERSION=v3.2.0 \
  --approval-required \
  --timeout 7200

# Monitor workflow progress
sysctl workflow status deployment-pipeline-20240115-143022 \
  --follow \
  --show-logs

# Execute disaster recovery
sysctl workflow run disaster-recovery \
  --param PRIMARY_REGION=us-east-1 \
  --param DR_REGION=us-west-2 \
  --emergency-mode \
  --skip-confirmations

# Performance optimization workflow
sysctl workflow run performance-optimization \
  --param CONFIDENCE_THRESHOLD=0.85 \
  --param MAX_CANARY_DURATION=3600 \
  --auto-approve-safe

# Multi-region deployment
sysctl workflow run multi-region-deployment \
  --param VERSION=v2.5.0 \
  --param REGIONS="us-east-1,us-west-2,eu-west-1" \
  --parallel-regions 2

# Complex database migration
sysctl workflow run zero-downtime-migration \
  --param OLD_SCHEMA=v3 \
  --param NEW_SCHEMA=v4 \
  --param MIGRATION_TIMEOUT=7200 \
  --validate-only  # Dry run first
```

These advanced workflows demonstrate sophisticated automation patterns for enterprise-scale system
management, providing robust error handling, monitoring, and rollback capabilities.

---

## Kong Gateway Workflows

Advanced workflows for managing Kong Gateway API infrastructure.

### Complete API Onboarding Workflow

Full workflow for onboarding a new API service to Kong Gateway with security, rate limiting,
and observability.

**Prerequisites:**

- Kong Gateway running and accessible
- `ops kong status` returns healthy
- Backend service deployed and accessible

**Steps:**

```bash
#!/bin/bash
# api-onboarding.sh - Complete API onboarding workflow
set -e

SERVICE_NAME="payment-api"
BACKEND_HOST="payment.internal.example.com"
BACKEND_PORT="8080"
API_PATH="/api/v1/payments"

echo "=== Step 1: Create the upstream service ==="
ops kong services create \
  --name "$SERVICE_NAME" \
  --host "$BACKEND_HOST" \
  --port "$BACKEND_PORT" \
  --protocol http \
  --tag production \
  --tag payments

echo "=== Step 2: Add route for public access ==="
ops kong routes create \
  --name "${SERVICE_NAME}-route" \
  --service "$SERVICE_NAME" \
  --path "$API_PATH" \
  --method GET \
  --method POST \
  --method PUT \
  --method DELETE \
  --strip-path

echo "=== Step 3: Enable API key authentication ==="
ops kong security key-auth enable \
  --service "$SERVICE_NAME" \
  --hide-credentials

echo "=== Step 4: Create consumer and API key ==="
ops kong consumers create \
  --username "${SERVICE_NAME}-client" \
  --tag automated

API_KEY=$(uuidgen)
ops kong security key-auth create-key "${SERVICE_NAME}-client" \
  --key "$API_KEY"

echo "=== Step 5: Add rate limiting ==="
ops kong traffic rate-limit enable \
  --service "$SERVICE_NAME" \
  --minute 100 \
  --hour 1000 \
  --policy local

echo "=== Step 6: Enable logging ==="
ops kong observability logs http enable \
  --service "$SERVICE_NAME" \
  --http-endpoint "https://logs.example.com/kong" \
  --method POST

echo "=== Step 7: Verify configuration ==="
ops kong services get "$SERVICE_NAME"
ops kong routes list --service "$SERVICE_NAME"
ops kong plugins list --service "$SERVICE_NAME"

echo ""
echo "=== API Onboarding Complete ==="
echo "Service: $SERVICE_NAME"
echo "Endpoint: https://api.example.com$API_PATH"
echo "API Key: $API_KEY"
echo ""
echo "Test with:"
echo "  curl -H 'apikey: $API_KEY' https://api.example.com$API_PATH"
```

### Security Hardening Workflow

Steps to harden security on an existing Kong API.

**Prerequisites:**

- Existing service and route configured
- Admin access to Kong

**Steps:**

```bash
#!/bin/bash
# security-hardening.sh - Security hardening workflow
set -e

SERVICE_NAME="${1:-my-api}"

echo "=== Security Hardening for $SERVICE_NAME ==="

echo "Step 1: Audit current plugins..."
ops kong plugins list --service "$SERVICE_NAME" --output json > /tmp/current-plugins.json
echo "Current plugins saved to /tmp/current-plugins.json"

echo "Step 2: Enable IP restriction (if not already)..."
ops kong security ip-restriction enable \
  --service "$SERVICE_NAME" \
  --allow "10.0.0.0/8" \
  --allow "172.16.0.0/12" \
  --allow "192.168.0.0/16" || true

echo "Step 3: Add request size limits..."
ops kong traffic request-size enable \
  --service "$SERVICE_NAME" \
  --size 1048576  # 1MB max

echo "Step 4: Configure CORS if needed..."
ops kong security cors enable \
  --service "$SERVICE_NAME" \
  --origins "https://app.example.com" \
  --methods GET \
  --methods POST \
  --methods PUT \
  --methods DELETE \
  --headers "Authorization" \
  --headers "Content-Type" \
  --max-age 3600

echo "Step 5: Add security headers via response transformer..."
ops kong traffic response-transformer enable \
  --service "$SERVICE_NAME" \
  --add-header "X-Frame-Options:DENY" \
  --add-header "X-Content-Type-Options:nosniff" \
  --add-header "X-XSS-Protection:1; mode=block" \
  --add-header "Strict-Transport-Security:max-age=31536000; includeSubDomains"

echo "Step 6: Verify final configuration..."
ops kong plugins list --service "$SERVICE_NAME"

echo ""
echo "=== Security Hardening Complete ==="
```

### Configuration Promotion Workflow

Promote Kong configuration from development to production safely.

**Prerequisites:**

- Configuration exported from development environment
- Access to both dev and prod Kong instances

**Steps:**

```bash
#!/bin/bash
# config-promotion.sh - Promote configuration from dev to prod
set -e

DEV_CONFIG="${1:-kong-dev.yaml}"
PROD_KONG_URL="${PROD_KONG_URL:-https://kong-admin.prod.example.com}"

echo "=== Kong Configuration Promotion Workflow ==="
echo "Source config: $DEV_CONFIG"
echo "Target: $PROD_KONG_URL"
echo ""

# Step 1: Export current dev state
echo "Step 1: Exporting current development configuration..."
ops kong config export "$DEV_CONFIG" --only services,routes,plugins

# Step 2: Validate the configuration
echo "Step 2: Validating configuration..."
ops kong config validate "$DEV_CONFIG"
if [ $? -ne 0 ]; then
  echo "ERROR: Configuration validation failed!"
  exit 1
fi

# Step 3: Switch context to production
echo "Step 3: Switching to production environment..."
export OPS_KONG_BASE_URL="$PROD_KONG_URL"

# Step 4: Show differences
echo "Step 4: Showing differences between config and production state..."
ops kong config diff "$DEV_CONFIG"

# Step 5: Prompt for confirmation
echo ""
read -p "Do you want to apply these changes to production? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
  echo "Aborted."
  exit 0
fi

# Step 6: Create backup
echo "Step 6: Creating production backup..."
BACKUP_FILE="kong-prod-backup-$(date +%Y%m%d-%H%M%S).yaml"
ops kong config export "$BACKUP_FILE"
echo "Backup saved to: $BACKUP_FILE"

# Step 7: Apply configuration
echo "Step 7: Applying configuration to production..."
ops kong config apply "$DEV_CONFIG" --confirm

# Step 8: Verify health
echo "Step 8: Verifying Kong health..."
ops kong status

# Step 9: Quick smoke test
echo "Step 9: Running smoke tests..."
ops kong services list --limit 5
ops kong routes list --limit 5

echo ""
echo "=== Configuration Promotion Complete ==="
echo "Backup file: $BACKUP_FILE"
echo ""
echo "If issues occur, rollback with:"
echo "  ops kong config apply $BACKUP_FILE --confirm"
```

### Blue-Green Deployment Workflow

Zero-downtime deployment using Kong upstreams.

```bash
#!/bin/bash
# blue-green-deploy.sh - Blue-green deployment workflow
set -e

UPSTREAM_NAME="${1:-api-cluster}"
NEW_TARGET="${2:-green.internal:8080}"
OLD_TARGET="${3:-blue.internal:8080}"

echo "=== Blue-Green Deployment ==="
echo "Upstream: $UPSTREAM_NAME"
echo "Current (blue): $OLD_TARGET"
echo "New (green): $NEW_TARGET"
echo ""

# Step 1: Add green target with weight 0
echo "Step 1: Adding green target (weight 0)..."
GREEN_ID=$(ops kong upstreams targets add "$UPSTREAM_NAME" \
  --target "$NEW_TARGET" \
  --weight 0 \
  --output json | jq -r '.id')
echo "Green target ID: $GREEN_ID"

# Step 2: Get blue target ID
BLUE_ID=$(ops kong upstreams targets list "$UPSTREAM_NAME" --output json | \
  jq -r --arg target "$OLD_TARGET" '.data[] | select(.target == $target) | .id')
echo "Blue target ID: $BLUE_ID"

# Step 3: Canary - 10% to green
echo "Step 3: Canary deployment (10% to green)..."
ops kong upstreams targets update "$UPSTREAM_NAME" "$BLUE_ID" --weight 90
ops kong upstreams targets update "$UPSTREAM_NAME" "$GREEN_ID" --weight 10

echo "Waiting 30 seconds to monitor..."
sleep 30
ops kong upstreams health "$UPSTREAM_NAME"

# Step 4: Increase to 50%
read -p "Continue to 50%? (yes/no): " CONTINUE
if [ "$CONTINUE" == "yes" ]; then
  echo "Step 4: Increasing to 50%..."
  ops kong upstreams targets update "$UPSTREAM_NAME" "$BLUE_ID" --weight 50
  ops kong upstreams targets update "$UPSTREAM_NAME" "$GREEN_ID" --weight 50

  sleep 30
  ops kong upstreams health "$UPSTREAM_NAME"
fi

# Step 5: Full cutover
read -p "Complete cutover to green? (yes/no): " CUTOVER
if [ "$CUTOVER" == "yes" ]; then
  echo "Step 5: Full cutover to green..."
  ops kong upstreams targets update "$UPSTREAM_NAME" "$BLUE_ID" --weight 0
  ops kong upstreams targets update "$UPSTREAM_NAME" "$GREEN_ID" --weight 100

  echo ""
  echo "=== Deployment Complete ==="
  ops kong upstreams health "$UPSTREAM_NAME"
  echo ""
  echo "To rollback:"
  echo "  ops kong upstreams targets update $UPSTREAM_NAME $BLUE_ID --weight 100"
  echo "  ops kong upstreams targets update $UPSTREAM_NAME $GREEN_ID --weight 0"
else
  echo "Cutover aborted. Rolling back..."
  ops kong upstreams targets update "$UPSTREAM_NAME" "$BLUE_ID" --weight 100
  ops kong upstreams targets update "$UPSTREAM_NAME" "$GREEN_ID" --weight 0
  ops kong upstreams targets delete "$UPSTREAM_NAME" "$GREEN_ID" --force
fi
```

### Emergency Rollback Workflow

Quick rollback procedure when issues are detected.

```bash
#!/bin/bash
# emergency-rollback.sh - Emergency configuration rollback
set -e

BACKUP_FILE="${1}"

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: $0 <backup-file.yaml>"
  echo ""
  echo "Available backups:"
  ls -la kong-*-backup-*.yaml 2>/dev/null || echo "No backup files found"
  exit 1
fi

echo "=== EMERGENCY ROLLBACK ==="
echo "Restoring from: $BACKUP_FILE"
echo ""
echo "WARNING: This will overwrite current Kong configuration!"
read -p "Are you sure? (type 'ROLLBACK' to confirm): " CONFIRM

if [ "$CONFIRM" != "ROLLBACK" ]; then
  echo "Aborted."
  exit 1
fi

# Apply the backup
echo "Applying backup configuration..."
ops kong config apply "$BACKUP_FILE" --no-confirm

# Verify
echo "Verifying Kong status..."
ops kong status

echo ""
echo "=== Rollback Complete ==="
echo "Verify services are healthy:"
echo "  ops kong services list"
echo "  ops kong upstreams health <upstream-name>"
```

These Kong workflows provide production-ready patterns for API lifecycle management, security hardening,
deployment automation, and emergency procedures.
